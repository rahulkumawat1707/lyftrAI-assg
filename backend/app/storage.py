import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Storage:
    def __init__(self, url):
        if not url.startswith('sqlite:///'):
            raise ValueError('DATABASE_URL must use sqlite:///')
        self.path = url[len('sqlite:///'):]
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY, system_prompt TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, metadata TEXT, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def healthy(self):
        with self.connect() as db:
            db.execute('SELECT 1').fetchone()

    def session(self, session_id):
        with self.connect() as db:
            row = db.execute('SELECT system_prompt FROM sessions WHERE session_id=?', (session_id,)).fetchone()
            return row['system_prompt'] if row else None

    def messages(self, session_id):
        with self.connect() as db:
            rows = db.execute('SELECT role,content,metadata FROM messages WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
        return [dict(role=r['role'], content=r['content'], **({'metadata': json.loads(r['metadata'])} if r['metadata'] else {})) for r in rows]

    def save_turn(self, session_id, prompt, message, reply, metadata):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            db.execute('INSERT INTO sessions VALUES (?,?) ON CONFLICT(session_id) DO UPDATE SET system_prompt=excluded.system_prompt', (session_id, prompt))
            db.executemany('INSERT INTO messages(session_id,role,content,metadata,created_at) VALUES (?,?,?,?,?)', [
                (session_id, 'user', message, None, now),
                (session_id, 'assistant', reply, json.dumps(metadata), now),
            ])
