/**
 * Core Verification System
 */

import {
  ArtifactManifest,
  VerificationResult,
  TrustPolicy,
  TrustConfig,
  ArtifactReceipt,
  SessionReceipt,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { VerificationDatabase } from '../storage/database';
import { KeychainManager } from '../storage/keychain';
import { TrustPolicyEngine, createDefaultTrustConfig } from '../trust/policy';
import { StreamingDownloader, DownloadOptions } from '../artifacts/downloader';
import { verifyManifestSignature } from '../artifacts/manifest';
import { verifyArtifactReceipt, verifySessionReceipt } from '../crypto/receipts';
import * as path from 'path';

export interface VerificationSystemConfig {
  dbPath: string;
  encryptionKey: string;
  tempDir?: string;
  trustConfig?: TrustConfig;
  enableKeychain?: boolean;
}

export class VerificationSystem {
  private db: VerificationDatabase;
  private keychain?: KeychainManager;
  private trustEngine: TrustPolicyEngine;
  private config: VerificationSystemConfig;
  private initialized = false;

  constructor(config: VerificationSystemConfig) {
    this.config = config;
    this.db = new VerificationDatabase(config.dbPath, config.encryptionKey);

    const trustConfig = config.trustConfig || createDefaultTrustConfig();
    this.trustEngine = new TrustPolicyEngine(trustConfig, this.db);
  }

  /**
   * Initialize the verification system
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Initialize keychain if enabled
    if (this.config.enableKeychain !== false) {
      try {
        this.keychain = await KeychainManager.create(this.db);
        console.log(
          `Keychain initialized (using ${
            this.keychain.isUsingFallback() ? 'SQLCipher fallback' : 'native OS keychain'
          })`
        );
      } catch (error) {
        console.warn('Keychain initialization failed:', error);
      }
    }

    this.initialized = true;
  }

  /**
   * Verify artifact with manifest
   */
  async verifyArtifact(
    artifactPath: string,
    manifest: ArtifactManifest,
    outputPath?: string
  ): Promise<VerificationResult> {
    await this.ensureInitialized();

    const startTime = Date.now();

    try {
      // Step 1: Verify manifest signature
      const signatureValid = await verifyManifestSignature(manifest);
      if (!signatureValid) {
        throw new VerificationError(
          VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
          'Invalid manifest signature'
        );
      }

      // Step 2: Check trust policy
      await this.trustEngine.enforceKeyExpiration(manifest.publisher.pubkey);
      const trustResult = await this.trustEngine.verifyKeyTrust(
        manifest.publisher.pubkey
      );

      if (!trustResult.trusted) {
        throw new VerificationError(
          VerificationErrorCode.UNTRUSTED_SIGNER_ERROR,
          trustResult.reason || 'Untrusted signer'
        );
      }

      if (trustResult.warning) {
        console.warn(`Trust warning: ${trustResult.warning}`);
      }

      // Step 3: Stream download and verify
      const downloader = new StreamingDownloader(manifest, {
        tempDir: this.config.tempDir,
      });

      const finalPath = outputPath || artifactPath;

      // Create chunk fetcher (reads from local file)
      const fs = await import('fs/promises');
      const fetchChunk = async (index: number): Promise<Buffer> => {
        const chunkSize = manifest.metadata.chunkSize;
        const offset = index * chunkSize;
        const fd = await fs.open(artifactPath, 'r');

        try {
          const buffer = Buffer.allocUnsafe(chunkSize);
          const { bytesRead } = await fd.read(buffer, 0, chunkSize, offset);
          return buffer.slice(0, bytesRead);
        } finally {
          await fd.close();
        }
      };

      const result = await downloader.download(fetchChunk, finalPath, {
        onChunkVerified: (current, total) => {
          if (current % 10 === 0 || current === total) {
            console.log(`Verified ${current}/${total} chunks`);
          }
        },
      });

      // Step 4: Log verification
      this.db.logVerification({
        entity_type: 'artifact',
        entity_id: manifest.artifactId,
        timestamp: new Date().toISOString(),
        success: result.success,
        error_code: result.error?.code,
        error_message: result.error?.message,
        details: JSON.stringify({
          version: manifest.artifactVersion,
          duration: Date.now() - startTime,
        }),
      });

      return result;
    } catch (error) {
      // Log failed verification
      this.db.logVerification({
        entity_type: 'artifact',
        entity_id: manifest.artifactId,
        timestamp: new Date().toISOString(),
        success: false,
        error_code:
          error instanceof VerificationError
            ? error.code
            : VerificationErrorCode.STORAGE_ERROR,
        error_message: (error as Error).message,
        details: JSON.stringify({ duration: Date.now() - startTime }),
      });

      throw error;
    }
  }

  /**
   * Store artifact receipt
   */
  async storeArtifactReceipt(receipt: ArtifactReceipt): Promise<void> {
    await this.ensureInitialized();

    // Verify receipt signature
    const valid = await verifyArtifactReceipt(receipt);
    if (!valid) {
      throw new VerificationError(
        VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
        'Invalid receipt signature'
      );
    }

    // Check for collision
    const existing = this.db.getArtifactReceipt(receipt.receiptHash);
    if (existing) {
      throw new VerificationError(
        VerificationErrorCode.RECEIPT_COLLISION_ERROR,
        `Receipt already exists: ${receipt.receiptHash}`
      );
    }

    this.db.insertArtifactReceipt(receipt);
  }

  /**
   * Store session receipt
   */
  async storeSessionReceipt(receipt: SessionReceipt): Promise<void> {
    await this.ensureInitialized();

    // Verify receipt signature
    const valid = await verifySessionReceipt(receipt);
    if (!valid) {
      throw new VerificationError(
        VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
        'Invalid receipt signature'
      );
    }

    this.db.insertSessionReceipt(receipt);
  }

  /**
   * Get artifact receipt
   */
  getArtifactReceipt(receiptHash: string): ArtifactReceipt | null {
    return this.db.getArtifactReceipt(receiptHash);
  }

  /**
   * Get session receipt
   */
  getSessionReceipt(receiptHash: string): SessionReceipt | null {
    return this.db.getSessionReceipt(receiptHash);
  }

  /**
   * Set trust policy
   */
  setTrustPolicy(policy: TrustPolicy): void {
    this.trustEngine.setPolicy(policy);
  }

  /**
   * Approve key
   */
  async approveKey(pubkeyHex: string): Promise<void> {
    await this.ensureInitialized();
    await this.trustEngine.approveKey(pubkeyHex);
  }

  /**
   * Revoke key
   */
  async revokeKey(pubkeyHex: string, reason: string): Promise<void> {
    await this.ensureInitialized();
    await this.trustEngine.revokeKey(pubkeyHex, reason);
  }

  /**
   * Get expiring keys
   */
  async getExpiringKeys(days?: number): Promise<Array<{
    keyId: string;
    type: 'team' | 'user';
    expiresAt: string;
  }>> {
    await this.ensureInitialized();
    return await this.trustEngine.getExpiringKeys(days);
  }

  /**
   * Get keychain manager
   */
  getKeychain(): KeychainManager | undefined {
    return this.keychain;
  }

  /**
   * Get database instance
   */
  getDatabase(): VerificationDatabase {
    return this.db;
  }

  /**
   * Close the system
   */
  close(): void {
    this.db.close();
    this.initialized = false;
  }

  /**
   * Ensure system is initialized
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
  }
}
