/**
 * ZULU Ledger Agent - Transaction Database Connection
 * Opens encrypted ledger.db with SQLCipher
 */

import Database from "better-sqlite3";
import { existsSync } from "fs";
import { join } from "path";

const DB_PATH = join(process.cwd(), "storage", "ledger.db");
const SCHEMA_PATH = join(process.cwd(), "storage", "schema_ledger.sql");

/**
 * Open encrypted ledger database
 * 
 * IMPORTANT: In production, get passphrase from OS keychain or user input
 * DO NOT hardcode passphrases!
 * Use DIFFERENT passphrase than memory.db for separation!
 */
export function openLedgerDb(passphrase: string = "another-strong-passphrase-ledger") {
  const db = new Database(DB_PATH);
  
  // Set encryption key
  db.pragma(`key = '${passphrase}'`);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  
  // Initialize schema if needed
  if (!existsSync(DB_PATH)) {
    console.log("[ZULU] Initializing ledger.db schema...");
    const schema = require("fs").readFileSync(SCHEMA_PATH, "utf-8");
    db.exec(schema);
  }
  
  return db;
}

/**
 * Add wallet (viewing key only!)
 */
export function addWallet(
  db: Database.Database,
  data: {
    label: string;
    view_key: string;
    network: string;
    meta?: any;
  }
) {
  const stmt = db.prepare(`
    INSERT INTO wallets (label, view_key, network, created_at, meta)
    VALUES (?, ?, ?, datetime('now'), ?)
  `);
  
  const result = stmt.run(
    data.label,
    data.view_key,
    data.network,
    data.meta ? JSON.stringify(data.meta) : null
  );
  
  return result.lastInsertRowid;
}

/**
 * Record transaction event
 */
export function recordTransaction(
  db: Database.Database,
  data: {
    wallet_id: number;
    txid: string;
    direction: "in" | "out";
    timestamp: string;
    amount_zec: number;
    memo_present?: boolean;
    category?: string;
    usd_value?: number;
    label?: string;
    raw_json?: any;
  }
) {
  const stmt = db.prepare(`
    INSERT INTO tx_events (
      wallet_id, txid, direction, timestamp, amount_zec,
      memo_present, category, usd_value, label, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (wallet_id, txid, direction) DO NOTHING
  `);
  
  const result = stmt.run(
    data.wallet_id,
    data.txid,
    data.direction,
    data.timestamp,
    data.amount_zec,
    data.memo_present ? 1 : 0,
    data.category || null,
    data.usd_value || null,
    data.label || null,
    data.raw_json ? JSON.stringify(data.raw_json) : null
  );
  
  return result.lastInsertRowid;
}

/**
 * Get recent transactions
 */
export function getRecentTransactions(db: Database.Database, limit: number = 50) {
  const stmt = db.prepare(`
    SELECT * FROM recent_transactions
    LIMIT ?
  `);
  
  return stmt.all(limit);
}

/**
 * Get wallet balances
 */
export function getWalletBalances(db: Database.Database) {
  const stmt = db.prepare(`
    SELECT * FROM wallet_balances
  `);
  
  return stmt.all();
}

/**
 * Record export
 */
export function recordExport(
  db: Database.Database,
  data: {
    period_start: string;
    period_end: string;
    format: string;
    file_path: string;
    notes?: string;
  }
) {
  const stmt = db.prepare(`
    INSERT INTO exports (created_at, period_start, period_end, format, file_path, notes)
    VALUES (datetime('now'), ?, ?, ?, ?, ?)
  `);
  
  const result = stmt.run(
    data.period_start,
    data.period_end,
    data.format,
    data.file_path,
    data.notes || null
  );
  
  return result.lastInsertRowid;
}

// Example usage
if (require.main === module) {
  const db = openLedgerDb();
  
  console.log("ZULU Ledger DB connected (encrypted)");
  console.log("Tables:", db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all());
  
  db.close();
}
