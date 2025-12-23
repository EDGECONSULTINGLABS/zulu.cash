/**
 * SQLCipher Database for Receipts and Verification Logs
 */

import Database from 'better-sqlite3';
import {
  ArtifactReceiptRow,
  SessionReceiptRow,
  VerificationLogRow,
  KeyMetadataRow,
  VerificationError,
  VerificationErrorCode,
  ArtifactReceipt,
  SessionReceipt,
} from '../types';

export class VerificationDatabase {
  private db: Database.Database;

  constructor(dbPath: string, encryptionKey: string) {
    this.db = new Database(dbPath);

    // Enable SQLCipher encryption (escape single quotes to prevent SQL injection)
    const escapedKey = encryptionKey.replace(/'/g, "''");
    this.db.pragma(`key = '${escapedKey}'`);
    this.db.pragma('cipher_page_size = 4096');
    this.db.pragma('kdf_iter = 256000');
    this.db.pragma('cipher_hmac_algorithm = HMAC_SHA512');
    this.db.pragma('cipher_kdf_algorithm = PBKDF2_HMAC_SHA512');

    this.initializeSchema();
  }

  private initializeSchema(): void {
    // Artifact Receipts Table (content-addressed)
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS artifact_receipts (
        receipt_hash TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL,
        version TEXT NOT NULL,
        root BLOB NOT NULL,
        signer_pubkey BLOB NOT NULL,
        signature BLOB NOT NULL,
        timestamp TEXT NOT NULL,
        metadata TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_artifact_receipts_artifact
        ON artifact_receipts(artifact_id, version);
      
      CREATE INDEX IF NOT EXISTS idx_artifact_receipts_timestamp
        ON artifact_receipts(timestamp DESC);
    `);

    // Session Receipts Table (content-addressed)
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS session_receipts (
        receipt_hash TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        root BLOB NOT NULL,
        signer_pubkey BLOB NOT NULL,
        signature BLOB NOT NULL,
        timestamp TEXT NOT NULL,
        metadata TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_session_receipts_session
        ON session_receipts(session_id);
      
      CREATE INDEX IF NOT EXISTS idx_session_receipts_timestamp
        ON session_receipts(timestamp DESC);
    `);

    // Verification Log Table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS verification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        success INTEGER NOT NULL,
        error_code TEXT,
        error_message TEXT,
        details TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_verification_log_entity
        ON verification_log(entity_type, entity_id, timestamp DESC);
    `);

    // Key Metadata Table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS key_metadata (
        key_id TEXT PRIMARY KEY,
        key_type TEXT NOT NULL,
        pubkey BLOB NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0,
        revoked_at TEXT,
        metadata TEXT NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_key_metadata_type
        ON key_metadata(key_type);
      
      CREATE INDEX IF NOT EXISTS idx_key_metadata_expires
        ON key_metadata(expires_at);
    `);

    // Secrets Table (for SQLCipher fallback keychain)
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS secrets (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  // ============================================================================
  // Artifact Receipts
  // ============================================================================

  insertArtifactReceipt(receipt: ArtifactReceipt): void {
    const stmt = this.db.prepare(`
      INSERT INTO artifact_receipts (
        receipt_hash, artifact_id, version, root, signer_pubkey,
        signature, timestamp, metadata
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    try {
      stmt.run(
        receipt.receiptHash,
        receipt.artifactId,
        receipt.version,
        receipt.root,
        receipt.signerPubkey,
        receipt.signature,
        receipt.timestamp,
        JSON.stringify(receipt.metadata)
      );
    } catch (error) {
      if ((error as Error).message.includes('UNIQUE constraint failed')) {
        throw new VerificationError(
          VerificationErrorCode.RECEIPT_COLLISION_ERROR,
          `Receipt hash collision detected: ${receipt.receiptHash}`
        );
      }
      throw error;
    }
  }

  getArtifactReceipt(receiptHash: string): ArtifactReceipt | null {
    const stmt = this.db.prepare(`
      SELECT * FROM artifact_receipts WHERE receipt_hash = ?
    `);
    const row = stmt.get(receiptHash) as ArtifactReceiptRow | undefined;

    if (!row) return null;

    return {
      receiptHash: row.receipt_hash,
      artifactId: row.artifact_id,
      version: row.version,
      root: row.root,
      signerPubkey: row.signer_pubkey,
      signature: row.signature,
      timestamp: row.timestamp,
      metadata: JSON.parse(row.metadata),
    };
  }

  getArtifactReceiptsByArtifact(
    artifactId: string,
    version?: string
  ): ArtifactReceipt[] {
    let stmt;
    let rows;

    if (version) {
      stmt = this.db.prepare(`
        SELECT * FROM artifact_receipts
        WHERE artifact_id = ? AND version = ?
        ORDER BY timestamp DESC
      `);
      rows = stmt.all(artifactId, version) as ArtifactReceiptRow[];
    } else {
      stmt = this.db.prepare(`
        SELECT * FROM artifact_receipts
        WHERE artifact_id = ?
        ORDER BY timestamp DESC
      `);
      rows = stmt.all(artifactId) as ArtifactReceiptRow[];
    }

    return rows.map(row => ({
      receiptHash: row.receipt_hash,
      artifactId: row.artifact_id,
      version: row.version,
      root: row.root,
      signerPubkey: row.signer_pubkey,
      signature: row.signature,
      timestamp: row.timestamp,
      metadata: JSON.parse(row.metadata),
    }));
  }

  // ============================================================================
  // Session Receipts
  // ============================================================================

  insertSessionReceipt(receipt: SessionReceipt): void {
    const stmt = this.db.prepare(`
      INSERT INTO session_receipts (
        receipt_hash, session_id, root, signer_pubkey,
        signature, timestamp, metadata
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    try {
      stmt.run(
        receipt.receiptHash,
        receipt.sessionId,
        receipt.root,
        receipt.signerPubkey,
        receipt.signature,
        receipt.timestamp,
        JSON.stringify(receipt.metadata)
      );
    } catch (error) {
      if ((error as Error).message.includes('UNIQUE constraint failed')) {
        throw new VerificationError(
          VerificationErrorCode.RECEIPT_COLLISION_ERROR,
          `Receipt hash collision detected: ${receipt.receiptHash}`
        );
      }
      throw error;
    }
  }

  getSessionReceipt(receiptHash: string): SessionReceipt | null {
    const stmt = this.db.prepare(`
      SELECT * FROM session_receipts WHERE receipt_hash = ?
    `);
    const row = stmt.get(receiptHash) as SessionReceiptRow | undefined;

    if (!row) return null;

    return {
      receiptHash: row.receipt_hash,
      sessionId: row.session_id,
      root: row.root,
      signerPubkey: row.signer_pubkey,
      signature: row.signature,
      timestamp: row.timestamp,
      metadata: JSON.parse(row.metadata),
    };
  }

  getSessionReceiptsBySession(sessionId: string): SessionReceipt[] {
    const stmt = this.db.prepare(`
      SELECT * FROM session_receipts
      WHERE session_id = ?
      ORDER BY timestamp DESC
    `);
    const rows = stmt.all(sessionId) as SessionReceiptRow[];

    return rows.map(row => ({
      receiptHash: row.receipt_hash,
      sessionId: row.session_id,
      root: row.root,
      signerPubkey: row.signer_pubkey,
      signature: row.signature,
      timestamp: row.timestamp,
      metadata: JSON.parse(row.metadata),
    }));
  }

  // ============================================================================
  // Verification Log
  // ============================================================================

  logVerification(log: Omit<VerificationLogRow, 'id'>): void {
    const stmt = this.db.prepare(`
      INSERT INTO verification_log (
        entity_type, entity_id, timestamp, success,
        error_code, error_message, details
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      log.entity_type,
      log.entity_id,
      log.timestamp,
      log.success ? 1 : 0,
      log.error_code || null,
      log.error_message || null,
      log.details
    );
  }

  getVerificationLogs(
    entityType: string,
    entityId: string,
    limit = 100
  ): VerificationLogRow[] {
    const stmt = this.db.prepare(`
      SELECT * FROM verification_log
      WHERE entity_type = ? AND entity_id = ?
      ORDER BY timestamp DESC
      LIMIT ?
    `);

    return stmt.all(entityType, entityId, limit) as VerificationLogRow[];
  }

  // ============================================================================
  // Key Metadata
  // ============================================================================

  insertKeyMetadata(key: KeyMetadataRow): void {
    const stmt = this.db.prepare(`
      INSERT INTO key_metadata (
        key_id, key_type, pubkey, created_at, expires_at,
        revoked, revoked_at, metadata
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      key.key_id,
      key.key_type,
      key.pubkey,
      key.created_at,
      key.expires_at,
      key.revoked ? 1 : 0,
      key.revoked_at || null,
      key.metadata
    );
  }

  getKeyMetadata(keyId: string): KeyMetadataRow | null {
    const stmt = this.db.prepare(`
      SELECT * FROM key_metadata WHERE key_id = ?
    `);
    return stmt.get(keyId) as KeyMetadataRow | undefined || null;
  }

  revokeKey(keyId: string): void {
    const stmt = this.db.prepare(`
      UPDATE key_metadata
      SET revoked = 1, revoked_at = ?
      WHERE key_id = ?
    `);
    stmt.run(new Date().toISOString(), keyId);
  }

  getExpiringKeys(daysUntilExpiry: number): KeyMetadataRow[] {
    const expiryDate = new Date();
    expiryDate.setDate(expiryDate.getDate() + daysUntilExpiry);

    const stmt = this.db.prepare(`
      SELECT * FROM key_metadata
      WHERE expires_at <= ? AND revoked = 0
      ORDER BY expires_at ASC
    `);

    return stmt.all(expiryDate.toISOString()) as KeyMetadataRow[];
  }

  // ============================================================================
  // Secrets (Fallback Keychain)
  // ============================================================================

  async storeSecret(key: string, value: string): Promise<void> {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO secrets (key, value, created_at, updated_at)
      VALUES (?, ?, ?, ?)
    `);
    const now = new Date().toISOString();
    stmt.run(key, value, now, now);
  }

  async retrieveSecret(key: string): Promise<string | null> {
    const stmt = this.db.prepare(`
      SELECT value FROM secrets WHERE key = ?
    `);
    const row = stmt.get(key) as { value: string } | undefined;
    return row?.value || null;
  }

  async deleteSecret(key: string): Promise<boolean> {
    const stmt = this.db.prepare(`
      DELETE FROM secrets WHERE key = ?
    `);
    const result = stmt.run(key);
    return result.changes > 0;
  }

  async listSecrets(): Promise<string[]> {
    const stmt = this.db.prepare(`
      SELECT key FROM secrets ORDER BY key
    `);
    const rows = stmt.all() as { key: string }[];
    return rows.map(r => r.key);
  }

  // ============================================================================
  // Utility
  // ============================================================================

  close(): void {
    this.db.close();
  }

  vacuum(): void {
    this.db.exec('VACUUM');
  }
}
