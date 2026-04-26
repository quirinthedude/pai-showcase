import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def open_db(path: Path) -> sqlite3.Connection:
    """Opens a SQLite connection and initializes the FTS5 schema."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    
    # Performance pragmas
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA temp_store=MEMORY;")

    # Standard table for storing chunk metadata and content
    con.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            source TEXT,
            path TEXT,
            text TEXT
        );
    """)

    # FTS5 Virtual Table for full-text search
    con.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(title, text, content='chunks', content_rowid='id');
    """)
    con.commit()
    return con

def db_has_rows(con: sqlite3.Connection) -> bool:
    try:
        row = con.execute("SELECT COUNT(*) FROM chunks;").fetchone()
        return bool(row and row[0] and int(row[0]) > 0)
    except Exception:
        return False

def rebuild_fts(con: sqlite3.Connection, chunks: List[Dict[str, Any]]) -> None:
    """Rebuilds the database tables and populates them with new chunks."""
    print("[INFO] Rebuilding FTS index...", flush=True)
    con.execute("DELETE FROM chunks;")
    con.execute("DELETE FROM chunks_fts;")

    for i, c in enumerate(chunks, start=1):
        title = c.get("doc_title") or c.get("title") or c.get("doc") or "doc"
        src = c.get("source") or ""
        path = c.get("pdf_path") or c.get("path") or c.get("txt_path") or ""
        text = c.get("text") or ""
        
        con.execute(
            "INSERT INTO chunks(id, title, source, path, text) VALUES(?,?,?,?,?)",
            (i, title, src, path, text)
        )

    # Rebuild the FTS index from the chunks table
    con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild');")
    con.commit()
    print(f"[OK] Indexed {len(chunks)} chunks.")
