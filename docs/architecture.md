# PAI System Architecture

This document provides a concise overview of the exact data flow in the PAI RAG pipeline. The architecture is explicitly designed to be deterministic, observable, and strictly grounded.

## The Pipeline

1. **User Query:** The user inputs a natural language query via the CLI (`pai ask`).
2. **Query Planning (`build_query_plan`):**
   - The query is stripped of stop words.
   - Exact phrases (wrapped in quotes) and specific conceptual patterns (like "Word + Number") are extracted.
   - A structured `QueryPlan` object is generated containing phrases and loose terms.
3. **SQLite FTS5 Retrieval (`retrieve`):**
   - A specific `MATCH` string is built for the SQLite FTS5 engine (e.g., `"exact phrase" OR (loose AND terms)`).
   - A deeper pool of candidates (k * 3) is fetched to allow room for semantic reranking.
   - The native FTS5 BM25 score is extracted.
4. **Deterministic Scoring:**
   - The base BM25 score is multiplied by 1.3 (+30%) if the chunk contains an exact phrase match.
   - A flat boost (+0.05) is added for every query term that appears in the chunk (Token Overlap).
   - A slight penalty (-0.0001 per char) is applied for length to favor concise chunks.
   - The chunks are definitively sorted, placing chunks with exact phrase matches at the very top.
5. **System-Controlled Grounding (`assess_evidence`):**
   - Before the LLM is ever invoked, a programmatic check evaluates the top contexts.
   - If there is 0 overlap between the query tokens and the retrieved text -> `INSUFFICIENT_CONTEXT`.
   - If there is partial overlap but critical exact phrases are missing -> `WEAKLY_GROUNDED`.
   - If overlap is high and phrases match -> `GROUNDED`.
6. **Response Contract (Dry-Run / Final Output):**
   - If the state is `INSUFFICIENT_CONTEXT`, the pipeline HALTS and refuses to call the LLM to prevent hallucination.
   - If the state is `WEAKLY_GROUNDED`, a hardcoded warning is injected into the prompt forcing the LLM to acknowledge the context is weak.
   - In this V1 Showcase, the pipeline intentionally halts at this step to output the `GROUNDING STATUS` via the `--explain` debugger.
