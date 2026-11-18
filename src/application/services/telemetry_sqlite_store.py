import os
import sqlite3
from typing import Any, Dict, List, Optional


def open_telemetry_conn(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA mmap_size = 268435456;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_telemetry_tables(db_path: str) -> None:
    try:
        with open_telemetry_conn(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queries (
                    id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, query TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL, tokens_saved INTEGER NOT NULL,
                    reduction_percentage REAL NOT NULL, sources_count INTEGER NOT NULL,
                    llm_provider TEXT NOT NULL, duration_ms REAL NOT NULL, created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, level TEXT NOT NULL,
                    module TEXT NOT NULL, message TEXT NOT NULL, metadata TEXT, created_at REAL NOT NULL
                )
                """
            )
            conn.commit()
    except Exception as e:
        print(f"Erro ao inicializar banco de consultas SQLite: {e}")


def load_telemetry_stats(db_path: str) -> Dict[str, Any]:
    stats = {"total_queries": 0, "total_tokens_used": 0, "total_tokens_saved": 0, "history": []}
    try:
        with open_telemetry_conn(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as total_q, COALESCE(SUM(tokens_used), 0) as total_used, "
                "COALESCE(SUM(tokens_saved), 0) as total_saved FROM queries"
            ).fetchone()
            if row:
                stats["total_queries"] = row["total_q"]
                stats["total_tokens_used"] = row["total_used"]
                stats["total_tokens_saved"] = row["total_saved"]
            rows = conn.execute("SELECT * FROM queries ORDER BY created_at DESC LIMIT 50").fetchall()
            stats["history"] = [
                {
                    "id": r["id"], "timestamp": r["timestamp"], "query": r["query"],
                    "tokens_used": r["tokens_used"], "tokens_saved": r["tokens_saved"],
                    "reduction_percentage": r["reduction_percentage"], "sources_count": r["sources_count"],
                    "llm_provider": r["llm_provider"], "duration_ms": round(r["duration_ms"], 1),
                }
                for r in reversed(rows)
            ]
    except Exception as e:
        print(f"Erro ao carregar estatísticas SQLite: {e}")
    return stats


def fetch_export_rows(db_path: str, limit: int, since: Optional[float]) -> List[Dict[str, Any]]:
    try:
        with open_telemetry_conn(db_path) as conn:
            if since is not None:
                rows = conn.execute(
                    "SELECT id, timestamp, query, tokens_used, tokens_saved, reduction_percentage, "
                    "sources_count, llm_provider, duration_ms FROM queries WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                    (since, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, timestamp, query, tokens_used, tokens_saved, reduction_percentage, "
                    "sources_count, llm_provider, duration_ms FROM queries ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def insert_system_log(db_path: str, entry: Dict[str, Any], created_at: float) -> None:
    import json
    try:
        with open_telemetry_conn(db_path) as conn:
            conn.execute(
                "INSERT INTO system_logs (id, timestamp, level, module, message, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entry["id"],
                    entry["timestamp"],
                    entry["level"],
                    entry["module"],
                    entry["message"],
                    json.dumps(entry.get("metadata") or {}),
                    created_at,
                ),
            )
            conn.commit()
    except Exception:
        pass


def insert_query_record(db_path: str, record: Dict[str, Any], sources_count: int, llm_provider: str, created_at: float) -> None:
    try:
        with open_telemetry_conn(db_path) as conn:
            conn.execute(
                "INSERT INTO queries (id, timestamp, query, tokens_used, tokens_saved, "
                "reduction_percentage, sources_count, llm_provider, duration_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["id"],
                    record["timestamp"],
                    record["query"],
                    record["tokens_used"],
                    record["tokens_saved"],
                    record["reduction_percentage"],
                    sources_count,
                    llm_provider,
                    record["duration_ms"],
                    created_at,
                ),
            )
            conn.commit()
    except Exception as e:
        print(f"Erro ao persistir consulta no SQLite: {e}")
