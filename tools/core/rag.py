import re
import sqlite3
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass, field

STOPWORDS = {
    # English
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with",
    # German
    "und", "oder", "ein", "eine", "einer", "einem", "einen", "der", "die", "das",
    "des", "dem", "den", "ist", "sind", "war", "waren", "wird", "werden", "wie",
    "als", "was", "wer", "wo", "warum", "weshalb", "wieso", "dass", "das", "von",
    "vom", "zu", "zum", "zur", "auf", "aus", "bei", "mit", "nach", "seit", "durch",
    "für", "gegen", "ohne", "um", "in", "im", "an", "am", "es", "er", "sie", "ihr",
    "wir", "ihnen", "mir", "mich", "dir", "dich", "sich", "mein", "dein", "sein",
    "nicht", "ja", "nein", "doch", "auch", "so", "nur", "noch", "schon", "aber", "hier",
    "dort", "dann", "wann", "weil", "wenn", "ob", "also", "diese", "dieser", "dieses",
    "jenes", "jener", "jede", "jeder", "jedes"
}

@dataclass
class QueryPlan:
    raw_query: str
    phrases: List[str] = field(default_factory=list)
    terms: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)

def extract_phrases(query: str) -> List[str]:
    phrases = []
    search_text = query

    # 1. Extract quoted phrases
    for match in re.finditer(r'"([^"]+)"', search_text):
        phrase = match.group(1).strip()
        if phrase:
            phrases.append(phrase.lower())
    search_text = re.sub(r'"[^"]+"', ' ', search_text)

    # 2. Extract Word + Number patterns (Preserving German Umlauts & ß)
    for match in re.finditer(r'\b([a-zA-ZäöüÄÖÜß]+)\s+(\d+)\b', search_text):
        phrases.append(f"{match.group(1).lower()} {match.group(2)}")

    return phrases

def build_query_plan(raw_query: str) -> QueryPlan:
    phrases = extract_phrases(raw_query)
    
    cleaned_text = re.sub(r'[^\w\s]', ' ', raw_query)
    cleaned_text = cleaned_text.replace('_', ' ')
    
    raw_tokens = cleaned_text.split()
    
    tokens = []
    terms = []
    seen = set()

    for token in raw_tokens:
        clean_token = token.lower()
        if not clean_token:
            continue
            
        tokens.append(clean_token)
        
        if clean_token in STOPWORDS:
            continue
        # Remove short tokens EXCEPT numbers
        if len(clean_token) <= 1 and not clean_token.isdigit():
            continue
            
        if clean_token not in seen:
            seen.add(clean_token)
            terms.append(clean_token)

    return QueryPlan(raw_query=raw_query, phrases=phrases, terms=terms, tokens=tokens)

def build_fts_query(plan: QueryPlan) -> str:
    phrase_fts = " AND ".join(f'"{p}"' for p in plan.phrases)
    term_fts = " AND ".join(plan.terms)

    if phrase_fts and term_fts:
        return f'{phrase_fts} OR ({term_fts})'
    elif phrase_fts:
        return phrase_fts
    elif term_fts:
        return term_fts
    
    return ""

def sanitize_fts_query(user_q: str) -> str:
    plan = build_query_plan(user_q)
    return build_fts_query(plan)

def retrieve(
    con: sqlite3.Connection,
    query: str,
    k: int,
) -> Tuple[str, List[Dict[str, Any]]]:
    # 1. Generate the structured plan and the exact string to query FTS
    plan = build_query_plan(query)
    fts_q = build_fts_query(plan)
    
    if not fts_q:
        return fts_q, []

    # 2. Fetch a deeper pool from SQLite to give the reranker swap-room
    fetch_limit = k * 3
    rows = con.execute(
        """
        SELECT
            c.title, c.source, c.path, c.text,
            bm25(chunks_fts) AS score
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
        """,
        (fts_q, fetch_limit)
    ).fetchall()

    results: List[Dict[str, Any]] = []
    for i, r in enumerate(rows):
        text = r[3] or ""
        text_lower = text.lower()
        
        # Calculate Signals
        term_overlap_count = sum(1 for t in plan.terms if t in text_lower)
        contains_exact_phrase = False
        if plan.phrases:
            contains_exact_phrase = any(p in text_lower for p in plan.phrases)

        # SQLite FTS5 bm25 is negative; invert it to positive (higher is better)
        base_score = abs(r[4] or 0.0)
        
        # 3. Apply Heuristic Adjustments
        # Phrase Boost (+30% multiplier)
        score = base_score * 1.3 if contains_exact_phrase else base_score
        
        # Term Overlap Boost (+0.05 flat addition per matched term)
        score += (term_overlap_count * 0.05)
        
        # Light Length Penalty (-0.0001 per char)
        score -= (len(text) * 0.0001)

        results.append({
            "doc_title": r[0],
            "source": r[1],
            "pdf_path": r[2],
            "text": text,
            "score": score,
            "fts_rank": i + 1,
            "fts_base_score": base_score,
            "contains_exact_phrase": contains_exact_phrase
        })
        
    # 4. Semantic Grouping: Exact phrase matches ALWAYS rank above partial matches.
    results.sort(key=lambda x: (x["contains_exact_phrase"], x["score"]), reverse=True)
    
    # Return sliced to the requested original `k` limit
    return fts_q, results[:k]

def assess_evidence(query: str, contexts: List[Dict[str, Any]], min_hits: int = 1) -> str:
    if not contexts:
        return "INSUFFICIENT_CONTEXT"

    toks = re.findall(r"[A-Za-z0-9ÄÖÜäöüß]+", query)
    fts_tokens = [t.lower() for t in toks if t.lower() not in STOPWORDS and (len(t) > 1 or t.isdigit())]
    detected_phrases = [m.group(0) for m in re.finditer(r"\b[A-Za-zÄÖÜäöüß]+\s+\d+\b", query)]

    term_overlap_max = 0
    exact_phrase_match = False
    single_token_max_freq = 0

    for c in contexts:
        text_lower = c.get("text", "").lower()
        
        if not exact_phrase_match:
            for p in detected_phrases:
                if p.lower() in text_lower:
                    exact_phrase_match = True

        overlap = 0
        freq = 0
        for t in fts_tokens:
            matches = len(re.findall(r'\b' + re.escape(t) + r'\b', text_lower))
            if matches > 0:
                overlap += 1
                freq += matches
                
        if overlap > term_overlap_max:
            term_overlap_max = overlap
            
        if len(fts_tokens) == 1 and freq > single_token_max_freq:
            single_token_max_freq = freq

    if term_overlap_max == 0:
        return "INSUFFICIENT_CONTEXT"

    if detected_phrases and not exact_phrase_match:
        return "WEAKLY_GROUNDED"

    required_overlap = max(1, len(fts_tokens) - 1)
    if len(fts_tokens) > 1 and term_overlap_max < required_overlap and not exact_phrase_match:
        return "WEAKLY_GROUNDED"

    if len(fts_tokens) == 1:
        return "WEAKLY_GROUNDED"

    if len(contexts) < min_hits:
        return "WEAKLY_GROUNDED"

    return "GROUNDED"
