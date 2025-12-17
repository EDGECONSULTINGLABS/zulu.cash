/**
 * Zulu Verification System - Type Definitions
 */

// ============================================================================
// Artifact Types
// ============================================================================

export enum ArtifactType {
  MODEL = 'MODEL',
  MEMORY = 'MEMORY',
  PLUGIN = 'PLUGIN',
  UI = 'UI',
}

export const CHUNK_SIZES: Record<ArtifactType, number> = {
  [ArtifactType.MODEL]: 1024 * 1024, // 1 MiB
  [ArtifactType.MEMORY]: 64 * 1024, // 64 KiB
  [ArtifactType.PLUGIN]: 256 * 1024, // 256 KiB
  [ArtifactType.UI]: 512 * 1024, // 512 KiB
};

// ============================================================================
// Commitment Strategy
// ============================================================================

export enum CommitmentStrategy {
  SIMPLE_CONCAT_V1 = 'SimpleConcatV1',
  BAO_MERKLE_V2 = 'BaoMerkleV2', // Future compatibility
}

export interface RootCommitment {
  strategy: CommitmentStrategy;
  root: Buffer;
  chunkHashes: Buffer[];
  metadata: {
    artifactType: ArtifactType;
    totalSize: number;
    chunkCount: number;
    timestamp: string;
  };
}

// ============================================================================
// Key Management
// ============================================================================

export interface BIP39Seed {
  mnemonic: string; // 12-24 words
  seed: Buffer; // 512-bit seed
  language: string;
}

export interface Ed25519KeyPair {
  publicKey: Buffer;
  privateKey: Buffer;
  path: string; // BIP-44 derivation path
}

export interface KeyMetadata {
  keyId: string; // hex(publicKey)
  type: 'team' | 'user';
  createdAt: string;
  expiresAt: string;
  revoked: boolean;
  revokedAt?: string;
}

// ============================================================================
// Receipts
// ============================================================================

export interface ArtifactReceipt {
  receiptHash: string; // SHA256(root || version || signer_pubkey)
  artifactId: string;
  version: string;
  root: Buffer;
  signerPubkey: Buffer;
  signature: Buffer;
  timestamp: string;
  metadata: {
    artifactType: ArtifactType;
    size: number;
    chunkCount: number;
    strategy: CommitmentStrategy;
  };
}

export interface SessionReceipt {
  receiptHash: string; // SHA256(root || session_id || signer_pubkey)
  sessionId: string;
  root: Buffer;
  signerPubkey: Buffer;
  signature: Buffer;
  timestamp: string;
  metadata: {
    duration: number;
    modelId: string;
    tokenCount: number;
    transcriptSize: number;
  };
}

// ============================================================================
// Trust Model
// ============================================================================

export enum TrustPolicy {
  STRICT = 'STRICT', // Only team keyring
  WARN = 'WARN', // User-approved keys
  BEST_EFFORT = 'BEST_EFFORT', // Dev mode
}

export interface TrustConfig {
  policy: TrustPolicy;
  teamKeyring: string[]; // Array of pubkey hex strings
  userApprovedKeys: string[];
  revokedKeys: string[];
  expiryWarningDays: number; // Default 30
}

// ============================================================================
// Verification Errors
// ============================================================================

export enum VerificationErrorCode {
  NETWORK_ERROR = 'NetworkError',
  STORAGE_ERROR = 'StorageError',
  MANIFEST_SIGNATURE_ERROR = 'ManifestSignatureError',
  UNTRUSTED_SIGNER_ERROR = 'UntrustedSignerError',
  CHUNK_HASH_MISMATCH_ERROR = 'ChunkHashMismatchError',
  ROOT_MISMATCH_ERROR = 'RootMismatchError',
  RESUME_STATE_CORRUPT_ERROR = 'ResumeStateCorruptError',
  KEY_EXPIRED_ERROR = 'KeyExpiredError',
  KEY_REVOKED_ERROR = 'KeyRevokedError',
  RECEIPT_COLLISION_ERROR = 'ReceiptCollisionError',
}

export class VerificationError extends Error {
  constructor(
    public code: VerificationErrorCode,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'VerificationError';
  }
}

// ============================================================================
// Manifest
// ============================================================================

export interface ArtifactManifest {
  version: '1.0';
  artifactId: string;
  artifactVersion: string;
  artifactType: ArtifactType;
  publisher: {
    name: string;
    pubkey: string; // hex
  };
  commitment: {
    strategy: CommitmentStrategy;
    root: string; // hex
    chunkHashes: string[]; // hex array
  };
  metadata: {
    size: number;
    chunkSize: number;
    chunkCount: number;
    createdAt: string;
    description?: string;
  };
  signature: string; // Ed25519 signature (hex)
}

// ============================================================================
// Resume State
// ============================================================================

export interface ResumeManifest {
  artifactId: string;
  expectedRoot: string; // hex
  verifiedChunks: number[]; // Array of verified chunk indices
  chunkHashes: string[]; // hex array
  lastVerifiedChunk: number;
  timestamp: string;
  checksum: string; // SHA256 of the above fields
}

// ============================================================================
// Plugin System
// ============================================================================

export interface PluginPermissions {
  filesystem?: {
    paths: string[];
    readonly: boolean;
  };
  network?: {
    allowedDomains: string[];
    rateLimit?: {
      requestsPerMinute: number;
    };
  };
  vault?: {
    tables: string[];
    operations: ('read' | 'write' | 'delete')[];
  };
  compute?: {
    maxMemoryMb: number;
    maxCpuSeconds: number;
  };
}

export interface PluginManifest {
  pluginId: string;
  version: string;
  name: string;
  description: string;
  permissions: PluginPermissions;
  publisher: {
    name: string;
    pubkey: string;
  };
  commitment: {
    strategy: CommitmentStrategy;
    root: string;
  };
  signature: string;
  createdAt: string;
}

// ============================================================================
// Verification Results
// ============================================================================

export interface VerificationResult {
  success: boolean;
  artifactId: string;
  root: string;
  verifiedChunks: number;
  totalChunks: number;
  error?: VerificationError;
  receipt?: ArtifactReceipt;
  timestamp: string;
}

export interface SessionExportBundle {
  sessionId: string;
  transcript: unknown; // Type depends on transcript format
  summary: string;
  entities: unknown[];
  embeddings: Float32Array;
  commitment: RootCommitment;
  receipt: SessionReceipt;
}

// ============================================================================
// Storage Schema
// ============================================================================

export interface ArtifactReceiptRow {
  receipt_hash: string; // PRIMARY KEY
  artifact_id: string;
  version: string;
  root: Buffer;
  signer_pubkey: Buffer;
  signature: Buffer;
  timestamp: string;
  metadata: string; // JSON
}

export interface SessionReceiptRow {
  receipt_hash: string; // PRIMARY KEY
  session_id: string;
  root: Buffer;
  signer_pubkey: Buffer;
  signature: Buffer;
  timestamp: string;
  metadata: string; // JSON
}

export interface VerificationLogRow {
  id: number;
  entity_type: 'artifact' | 'session';
  entity_id: string;
  timestamp: string;
  success: boolean;
  error_code?: string;
  error_message?: string;
  details: string; // JSON
}

export interface KeyMetadataRow {
  key_id: string; // PRIMARY KEY (hex pubkey)
  key_type: 'team' | 'user';
  pubkey: Buffer;
  created_at: string;
  expires_at: string;
  revoked: boolean;
  revoked_at?: string;
  metadata: string; // JSON
}
