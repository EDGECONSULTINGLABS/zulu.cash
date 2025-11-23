/**
 * ZULU Live Agent - Memory Database Connection
 * Opens encrypted memory.db with SQLCipher
 */

import Database from "better-sqlite3";
import { existsSync } from "fs";
import { join } from "path";

const DB_PATH = join(process.cwd(), "storage", "memory.db");
const SCHEMA_PATH = join(process.cwd(), "storage", "schema_memory.sql");

/**
 * Open encrypted memory database
 * 
 * IMPORTANT: In production, get passphrase from OS keychain or user input
 * DO NOT hardcode passphrases!
 */
export function openMemoryDb(passphrase: string = "super-strong-passphrase-memory") {
  const db = new Database(DB_PATH);
  
  // Set encryption key
  db.pragma(`key = '${passphrase}'`);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  
  // Initialize schema if needed
  if (!existsSync(DB_PATH)) {
    console.log("[ZULU] Initializing memory.db schema...");
    const schema = require("fs").readFileSync(SCHEMA_PATH, "utf-8");
    db.exec(schema);
  }
  
  return db;
}

/**
 * Store session in memory database
 */
export function createSession(
  db: Database.Database,
  data: {
    title?: string;
    started_at: string;
    participants?: string[];
    external_id?: string;
  }
) {
  const stmt = db.prepare(`
    INSERT INTO sessions (title, started_at, participants, external_id)
    VALUES (?, ?, ?, ?)
  `);
  
  const result = stmt.run(
    data.title || null,
    data.started_at,
    data.participants ? JSON.stringify(data.participants) : null,
    data.external_id || null
  );
  
  return result.lastInsertRowid;
}

/**
 * Store note in memory database
 */
export function createNote(
  db: Database.Database,
  data: {
    session_id?: number;
    content: string;
    source: string;
    kind?: string;
    meta?: any;
  }
) {
  const stmt = db.prepare(`
    INSERT INTO notes (session_id, created_at, source, content, kind, meta)
    VALUES (?, datetime('now'), ?, ?, ?, ?)
  `);
  
  const result = stmt.run(
    data.session_id || null,
    data.source,
    data.content,
    data.kind || null,
    data.meta ? JSON.stringify(data.meta) : null
  );
  
  return result.lastInsertRowid;
}

/**
 * Create task from action item
 */
export function createTask(
  db: Database.Database,
  data: {
    session_id?: number;
    description: string;
    owner?: string;
    due_at?: string;
    tags?: string[];
  }
) {
  const stmt = db.prepare(`
    INSERT INTO tasks (session_id, created_at, description, owner, due_at, tags, status)
    VALUES (?, datetime('now'), ?, ?, ?, ?, 'open')
  `);
  
  const result = stmt.run(
    data.session_id || null,
    data.description,
    data.owner || "me",
    data.due_at || null,
    data.tags ? JSON.stringify(data.tags) : null
  );
  
  return result.lastInsertRowid;
}

/**
 * Get active tasks
 */
export function getActiveTasks(db: Database.Database) {
  const stmt = db.prepare(`
    SELECT * FROM active_tasks
    ORDER BY due_at ASC NULLS LAST
  `);
  
  return stmt.all();
}

/**
 * Get recent sessions
 */
export function getRecentSessions(db: Database.Database, limit: number = 10) {
  const stmt = db.prepare(`
    SELECT * FROM recent_sessions
    LIMIT ?
  `);
  
  return stmt.all(limit);
}

// Example usage
if (require.main === module) {
  const db = openMemoryDb();
  
  console.log("ZULU Memory DB connected (encrypted)");
  console.log("Tables:", db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all());
  
  db.close();
}
