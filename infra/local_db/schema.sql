-- ZULU Local Database Schema
-- SQLCipher Encrypted Storage

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Receivers (Identity Slots)
CREATE TABLE receivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    orchard_receiver TEXT UNIQUE NOT NULL,
    viewing_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memory Partitions
CREATE TABLE memory_partitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    partition_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (receiver_id) REFERENCES receivers(id) ON DELETE CASCADE,
    UNIQUE(receiver_id, partition_name)
);

-- Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    partition_id INTEGER NOT NULL,
    title TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    source TEXT, -- 'zoom', 'meet', 'discord', 'manual'
    FOREIGN KEY (receiver_id) REFERENCES receivers(id) ON DELETE CASCADE,
    FOREIGN KEY (partition_id) REFERENCES memory_partitions(id) ON DELETE CASCADE
);

-- Messages (Encrypted Content)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content_encrypted BLOB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Transcripts (Encrypted)
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    transcript_encrypted BLOB NOT NULL,
    duration_seconds INTEGER,
    word_count INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Embeddings (Vector References)
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    message_id INTEGER,
    vector_index_id TEXT NOT NULL, -- Reference to FAISS index
    embedding_model TEXT NOT NULL, -- 'phi3', 'llama3.1', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
);

-- Notes (Zcash Shielded Notes)
CREATE TABLE zcash_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    note_commitment TEXT UNIQUE NOT NULL,
    value_zatoshi INTEGER NOT NULL,
    memo_encrypted BLOB,
    block_height INTEGER NOT NULL,
    tx_hash TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (receiver_id) REFERENCES receivers(id) ON DELETE CASCADE
);

-- Action Items
CREATE TABLE action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    completed BOOLEAN DEFAULT 0,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Topics/Tags
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversation Topics (Many-to-Many)
CREATE TABLE conversation_topics (
    conversation_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    PRIMARY KEY (conversation_id, topic_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Indexes for Performance
CREATE INDEX idx_conversations_receiver ON conversations(receiver_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_transcripts_conversation ON transcripts(conversation_id);
CREATE INDEX idx_embeddings_conversation ON embeddings(conversation_id);
CREATE INDEX idx_zcash_notes_receiver ON zcash_notes(receiver_id);
CREATE INDEX idx_zcash_notes_block_height ON zcash_notes(block_height);
CREATE INDEX idx_action_items_conversation ON action_items(conversation_id);
CREATE INDEX idx_action_items_completed ON action_items(completed);

-- Triggers for Updated Timestamps
CREATE TRIGGER update_receivers_timestamp 
AFTER UPDATE ON receivers
BEGIN
    UPDATE receivers SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Views for Common Queries
CREATE VIEW active_conversations AS
SELECT 
    c.id,
    c.title,
    r.label as receiver_label,
    c.started_at,
    c.source,
    COUNT(m.id) as message_count
FROM conversations c
JOIN receivers r ON c.receiver_id = r.id
LEFT JOIN messages m ON c.conversation_id = m.conversation_id
WHERE c.ended_at IS NULL
GROUP BY c.id;

CREATE VIEW pending_action_items AS
SELECT 
    a.id,
    a.description,
    a.due_date,
    c.title as conversation_title,
    r.label as receiver_label
FROM action_items a
JOIN conversations c ON a.conversation_id = c.id
JOIN receivers r ON c.receiver_id = r.id
WHERE a.completed = 0
ORDER BY a.due_date ASC;
