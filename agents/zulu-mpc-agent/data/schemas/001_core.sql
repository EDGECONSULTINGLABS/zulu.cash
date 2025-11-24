-- ZULU MPC Agent - Core Schema
-- SQLCipher encrypted database for local-only storage

-- Sessions: One per call/meeting
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  title TEXT NOT NULL,
  summary TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  metadata_json TEXT,  -- Stores attention scores, custom fields
  audio_path TEXT,     -- Reference to original audio file
  duration_seconds REAL,
  language TEXT DEFAULT 'en'
);

-- Utterances: Individual speech segments with speaker labels
CREATE TABLE IF NOT EXISTS utterances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  speaker_label TEXT NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  text TEXT NOT NULL,
  confidence REAL,  -- Transcription confidence
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- MPC Feature Index: Maps local features to Nillion handles
-- NO raw text, NO user IDs, NO PII
CREATE TABLE IF NOT EXISTS mpc_feature_index (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  feature_kind TEXT NOT NULL,   -- e.g. "embedding", "attention_score"
  feature_hash TEXT NOT NULL,   -- SHA256 of feature vector (for local verification)
  nillion_handle TEXT NOT NULL, -- Handle/ID from Nillion network
  feature_dim INTEGER,          -- Dimensionality of the feature
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  computation_result TEXT,      -- JSON of MPC computation results
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Action Items: Extracted from call summaries
CREATE TABLE IF NOT EXISTS action_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  owner_speaker TEXT NOT NULL,  -- Speaker label (e.g., SPK_1)
  item TEXT NOT NULL,
  due_date TEXT,
  status TEXT DEFAULT 'pending', -- pending, completed, cancelled
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT,
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Decisions: Key decisions from calls
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  context TEXT,
  timestamp_in_call REAL, -- When in the call this was discussed
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_utterances_session ON utterances(session_id);
CREATE INDEX IF NOT EXISTS idx_utterances_speaker ON utterances(speaker_label);
CREATE INDEX IF NOT EXISTS idx_utterances_time ON utterances(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_mpc_features_session ON mpc_feature_index(session_id);
CREATE INDEX IF NOT EXISTS idx_mpc_features_kind ON mpc_feature_index(feature_kind);
CREATE INDEX IF NOT EXISTS idx_action_items_session ON action_items(session_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(status);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(session_id);

-- Triggers for updated_at
CREATE TRIGGER IF NOT EXISTS sessions_updated_at
AFTER UPDATE ON sessions
BEGIN
  UPDATE sessions SET updated_at = datetime('now') WHERE id = NEW.id;
END;
