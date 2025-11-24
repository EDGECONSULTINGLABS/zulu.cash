-- ZULU Ledger Agent - Transaction Database Schema
-- Use with SQLCipher after providing a key.
--
-- Example from CLI:
--   sqlite3 ledger.db
--   sqlite> PRAGMA key = 'another-strong-passphrase';
--   sqlite> .read schema_ledger.sql;

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Wallets (view-only, never spend keys!)
CREATE TABLE IF NOT EXISTS wallets (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  label           TEXT NOT NULL,
  view_key        TEXT NOT NULL,     -- incoming viewing key or UA fragment
  network         TEXT NOT NULL,     -- 'zcash-mainnet' / 'zcash-testnet'
  created_at      TEXT NOT NULL,
  meta            TEXT               -- JSON, NEVER store spend keys here
);

-- Transaction Events
CREATE TABLE IF NOT EXISTS tx_events (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  wallet_id       INTEGER NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
  txid            TEXT NOT NULL,
  direction       TEXT NOT NULL,     -- 'in' or 'out'
  timestamp       TEXT NOT NULL,
  amount_zec      REAL NOT NULL,
  memo_present    INTEGER NOT NULL DEFAULT 0,
  category        TEXT,              -- mining, staking, payment, self, etc.
  usd_value       REAL,              -- snapshot at tx time
  label           TEXT,              -- short human label
  raw_json        TEXT               -- raw parsed tx for audit
);

-- Ensure unique transactions per wallet
CREATE UNIQUE INDEX IF NOT EXISTS idx_tx_wallet_unique
ON tx_events(wallet_id, txid, direction);

-- Indexes for queries
CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON tx_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_tx_category ON tx_events(category);
CREATE INDEX IF NOT EXISTS idx_tx_wallet ON tx_events(wallet_id);

-- Export Records
CREATE TABLE IF NOT EXISTS exports (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at      TEXT NOT NULL,
  period_start    TEXT NOT NULL,
  period_end      TEXT NOT NULL,
  format          TEXT NOT NULL,      -- 'koinly', 'excel', 'bitwave'
  file_path       TEXT NOT NULL,
  notes           TEXT
);

-- Views for common queries
CREATE VIEW IF NOT EXISTS recent_transactions AS
SELECT 
  t.id,
  w.label as wallet_label,
  t.direction,
  t.amount_zec,
  t.category,
  t.timestamp,
  t.label
FROM tx_events t
JOIN wallets w ON t.wallet_id = w.id
ORDER BY t.timestamp DESC
LIMIT 100;

CREATE VIEW IF NOT EXISTS wallet_balances AS
SELECT 
  w.id,
  w.label,
  SUM(CASE WHEN t.direction = 'in' THEN t.amount_zec ELSE -t.amount_zec END) as balance_zec,
  COUNT(t.id) as tx_count
FROM wallets w
LEFT JOIN tx_events t ON w.id = t.wallet_id
GROUP BY w.id;
