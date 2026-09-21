use std::path::Path;
use std::sync::{Arc, Mutex};
use rusqlite::{params, Connection, Result};

pub struct AppDb {
    conn: Arc<Mutex<Connection>>,
}

#[derive(Clone, Debug)]
pub struct DbToken {
    pub id: String,
    pub project_name: String,
    pub token: String,
    pub token_mask: String,
    pub created_at: String,
    pub is_active: bool,
}

#[derive(Clone, Debug)]
pub struct DbHistory {
    pub timestamp: String,
    pub mode_badge: String,
    pub query_title: String,
    pub chunks_count: String,
    pub tokens_saved: String,
    pub latency: String,
    pub saved_count: usize,
    pub latency_ms: u128,
}

impl AppDb {
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        if let Some(parent) = path.as_ref().parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let conn = Connection::open(path)?;
        conn.pragma_update(None, "journal_mode", "WAL")?;
        conn.pragma_update(None, "synchronous", "NORMAL")?;

        let db = Self { conn: Arc::new(Mutex::new(conn)) };
        db.init_tables()?;
        Ok(db)
    }

    fn init_tables(&self) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS mcp_tokens (
                id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                token_mask TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mode_badge TEXT NOT NULL,
                query_title TEXT NOT NULL,
                chunks_count TEXT NOT NULL,
                tokens_saved TEXT NOT NULL,
                latency TEXT NOT NULL,
                saved_count INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );"
        )?;
        Ok(())
    }

    pub fn list_tokens(&self) -> Result<Vec<DbToken>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT id, project_name, token, token_mask, created_at, is_active FROM mcp_tokens ORDER BY rowid DESC")?;
        let rows = stmt.query_map([], |row| {
            Ok(DbToken {
                id: row.get(0)?,
                project_name: row.get(1)?,
                token: row.get(2)?,
                token_mask: row.get(3)?,
                created_at: row.get(4)?,
                is_active: row.get::<_, i64>(5)? != 0,
            })
        })?;
        let mut tokens = Vec::new();
        for r in rows { tokens.push(r?); }
        Ok(tokens)
    }

    pub fn insert_token(&self, t: &DbToken) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT OR REPLACE INTO mcp_tokens (id, project_name, token, token_mask, created_at, is_active) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![t.id, t.project_name, t.token, t.token_mask, t.created_at, if t.is_active { 1 } else { 0 }],
        )?;
        Ok(())
    }

    pub fn delete_token(&self, id: &str) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute("DELETE FROM mcp_tokens WHERE id = ?1", params![id])?;
        Ok(())
    }

    pub fn list_history(&self, limit: usize) -> Result<Vec<DbHistory>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT timestamp, mode_badge, query_title, chunks_count, tokens_saved, latency, saved_count, latency_ms FROM query_history ORDER BY id DESC LIMIT ?1")?;
        let rows = stmt.query_map(params![limit], |row| {
            Ok(DbHistory {
                timestamp: row.get(0)?,
                mode_badge: row.get(1)?,
                query_title: row.get(2)?,
                chunks_count: row.get(3)?,
                tokens_saved: row.get(4)?,
                latency: row.get(5)?,
                saved_count: row.get::<_, i64>(6)? as usize,
                latency_ms: row.get::<_, i64>(7)? as u128,
            })
        })?;
        let mut hist = Vec::new();
        for r in rows { hist.push(r?); }
        Ok(hist)
    }

    pub fn insert_history(&self, h: &DbHistory) -> Result<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO query_history (timestamp, mode_badge, query_title, chunks_count, tokens_saved, latency, saved_count, latency_ms) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![h.timestamp, h.mode_badge, h.query_title, h.chunks_count, h.tokens_saved, h.latency, h.saved_count as i64, h.latency_ms as i64],
        )?;
        Ok(())
    }

    pub fn get_metrics_summary(&self) -> Result<(usize, usize, u128)> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT COUNT(*), COALESCE(SUM(saved_count), 0), COALESCE(SUM(latency_ms), 0) FROM query_history")?;
        let row = stmt.query_row([], |r| {
            let count: i64 = r.get(0)?;
            let saved: i64 = r.get(1)?;
            let lat: i64 = r.get(2)?;
            Ok((count as usize, saved as usize, lat as u128))
        })?;
        Ok(row)
    }
}
