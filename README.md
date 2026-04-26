# PAI Showcase (V1)

**A 2-minute demonstration of deterministic RAG architecture, SQLite FTS5 search, and system-controlled grounding.**

This repository is a sanitized, minimal showcase extracted from the larger "PAI – Personal AI Orchestrator" system. It focuses purely on the mathematical heuristics of retrieval and grounding, completely isolating the retrieval layer from the LLM. 

## What This Showcases
- **CLI-First Architecture:** A clean, procedural entrypoint.
- **SQLite FTS5 Mastery:** Leveraging native database full-text search with exact phrase tracking.
- **Deterministic Reranking:** BM25 scoring adjusted with term overlap math and phrase-match multipliers.
- **System-Controlled Grounding:** The `assess_evidence` algorithm that programmatically determines if the retrieved context is `GROUNDED`, `WEAKLY_GROUNDED`, or `INSUFFICIENT_CONTEXT` *before* hitting an LLM.

## What is Intentionally Excluded
To protect private data and maintain a 2-minute reviewability constraint, the following elements of the real PAI system are completely omitted:
- **Private Data & Memories:** The JSON archiving, personal memory stores, and conversational histories.
- **Private personalization layers:** Removed all personal profile, memory, and identity-related prompt components.
- **LLM Integration:** V1 is strictly a "dry-run" showcase. No API keys or local Ollama instances are required to test the retrieval logic.
- **Complex Routing:** Multi-corpus routing has been simplified to a single demo corpus.

## Setup & Ingestion
The showcase relies on a generated SQLite database. You must build it first.
```bash
# Ingest the public domain philosophical texts into FTS5
python tools/pai ingest demo/sample_corpus
```

## Demo Commands

### 1. Grounded Query (Dry-Run)
Test the retrieval on a valid topic:
```bash
python tools/pai ask "what is in our control?" --dry-run
```

### 2. Graceful Degradation (Insufficient Context)
Test the system's refusal to hallucinate:
```bash
python tools/pai ask "what is the recipe for chocolate cake?" --dry-run
```

### 3. The Transparent Debugger (`--explain`)
To see the exact math and logic happening under the hood, use the explain flag. This outputs the query parsing, FTS5 SQL, BM25 scoring adjustments, and final grounding decision.
```bash
python tools/pai ask '"our control"' --explain
```

## Architecture Pipeline
For a deeper dive into how the query flows through the system, please see [docs/architecture.md](docs/architecture.md).
