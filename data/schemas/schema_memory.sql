-- ZULU Live Agent - Memory Database Schema
-- Use with SQLCipher after providing a key.
--
-- Example from CLI:
--   sqlite3 memory.db
--   sqlite> PRAGMA key = 'your-strong-passphrase-here';
--   sqlite> .read schema_memory.sql;

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Sessions (calls, meetings, conversations)
CREATE TABLE IF NOT EXISTS sessions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id   TEXT,                 -- e.g. Zoom ID / calendar ID
  started_at    TEXT NOT NULL,        -- ISO8601 UTC
  ended_at      TEXT,
  title         TEXT,
  participants  TEXT                  -- JSON string
);

-- Notes (summaries, decisions, ideas)
CREATE TABLE IF NOT EXISTS notes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
  created_at    TEXT NOT NULL,
  source        TEXT NOT NULL,        -- 'live', 'manual', 'system'
  content       TEXT NOT NULL,        -- human-readable note
  kind          TEXT,                 -- 'summary', 'decision', 'action', 'idea'
  meta          TEXT                  -- JSON blob for extra fields
);

-- Tasks (action items)
CREATE TABLE IF NOT EXISTS tasks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
  created_at    TEXT NOT NULL,
  due_at        TEXT,                 -- optional
  owner         TEXT,                 -- "me" / "other name"
  description   TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'open',  -- open, done, dropped
  tags          TEXT                  -- comma list or JSON
);

-- Embeddings (for semantic search)
CREATE TABLE IF NOT EXISTS embeddings (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  note_id       INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  created_at    TEXT NOT NULL,
  model         TEXT NOT NULL,
  vector        BLOB NOT NULL         -- serialized float32[]
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_notes_session ON notes(session_id);
CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_at);
CREATE INDEX IF NOT EXISTS idx_embeddings_note ON embeddings(note_id);

-- Views for common queries
CREATE VIEW IF NOT EXISTS active_tasks AS
SELECT 
  t.id,
  t.description,
  t.due_at,
  t.owner,
  t.tags,
  s.title as session_title
FROM tasks t
LEFT JOIN sessions s ON t.session_id = s.id
WHERE t.status = 'open'
ORDER BY t.due_at ASC NULLS LAST;

CREATE VIEW IF NOT EXISTS recent_sessions AS
SELECT 
  s.id,
  s.title,
  s.started_at,
  s.ended_at,
  COUNT(n.id) as note_count
FROM sessions s
LEFT JOIN notes n ON s.id = n.session_id
GROUP BY s.id
ORDER BY s.started_at DESC
LIMIT 50;
