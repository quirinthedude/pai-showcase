# PAI Showcase

**A compact demonstration of deterministic RAG retrieval, SQLite FTS5 search, and
system-controlled grounding.**

This repository is a sanitized showcase extracted from the larger **PAI - Personal AI
Orchestrator** system. The original project contains personal data, private memories,
conversation history, and more complex orchestration logic. This public version isolates one
reviewable technical slice: retrieval, reranking, and pre-LLM grounding decisions.

## What This Showcases

- **CLI-first architecture:** a small command-line entrypoint for ingestion and retrieval.
- **SQLite FTS5 retrieval:** native full-text search with exact phrase handling.
- **Deterministic reranking:** BM25 adjusted with phrase matches, token overlap, and a small
  length penalty.
- **System-controlled grounding:** `assess_evidence` classifies retrieved context as
  `GROUNDED`, `WEAKLY_GROUNDED`, or `INSUFFICIENT_CONTEXT` before any LLM call would happen.
- **Transparent debugging:** `--explain` prints the query plan, FTS5 query, scoring signals,
  and final grounding decision.

## What Is Intentionally Excluded

To protect private data and keep the review path short, this showcase omits:

- private memory stores, profile data, JSON archives, and conversation history
- personalization layers and identity-related prompt components
- live LLM integration, API keys, and local model dependencies
- multi-corpus routing and the broader orchestration layer

## Requirements

- Python 3.10+
- SQLite with FTS5 enabled, which is included in standard Python builds on most systems
- No runtime Python dependencies for the demo path

## Quick Start

The demo database is generated locally and ignored by git.

```bash
python3 tools/pai ingest demo/sample_corpus
```

## Demo Commands

Grounded query:

```bash
python3 tools/pai ask "what is in our control?" --dry-run
```

Graceful degradation for out-of-corpus questions:

```bash
python3 tools/pai ask "what is the recipe for chocolate cake?" --dry-run
```

Transparent debugger:

```bash
python3 tools/pai ask '"our control"' --explain
```

## Development Checks

The core tests can run with the Python standard library:

```bash
python3 -m unittest
```

Optional development tools are declared in `pyproject.toml`:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m ruff check .
```

The same checks are wired into GitHub Actions in `.github/workflows/ci.yml`.

## Architecture

For a deeper look at the retrieval and grounding pipeline, see
[docs/architecture.md](docs/architecture.md).
