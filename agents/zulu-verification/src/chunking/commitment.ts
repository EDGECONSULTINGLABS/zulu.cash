/**
 * Root Commitment Strategies
 */

import { CommitmentStrategy, RootCommitment, ArtifactType, VerificationError, VerificationErrorCode } from '../types';
import { hashBuffers } from '../crypto/blake3';
import { Chunk } from './deterministic';

/**
 * SimpleConcatV1: Concatenate all chunk hashes and hash the result
 * root = BLAKE3(hash_0 || hash_1 || ... || hash_n)
 */
export function calculateSimpleConcatV1Root(chunkHashes: Buffer[]): Buffer {
  if (chunkHashes.length === 0) {
    throw new VerificationError(
      VerificationErrorCode.CHUNK_HASH_MISMATCH_ERROR,
      'Cannot calculate root from zero chunks'
    );
  }

  return hashBuffers(chunkHashes);
}

/**
 * BaoMerkleV2: Future Merkle tree implementation placeholder
 * API compatible interface for future upgrade
 */
export function calculateBaoMerkleV2Root(chunkHashes: Buffer[]): Buffer {
  // TODO: Implement BAO (BLAKE3 Authenticated Output) Merkle tree
  // For now, throw error to maintain API compatibility
  throw new VerificationError(
    VerificationErrorCode.STORAGE_ERROR,
    'BaoMerkleV2 not yet implemented'
  );
}

/**
 * Calculate root commitment using specified strategy
 */
export function calculateRootCommitment(
  strategy: CommitmentStrategy,
  chunkHashes: Buffer[]
): Buffer {
  switch (strategy) {
    case CommitmentStrategy.SIMPLE_CONCAT_V1:
      return calculateSimpleConcatV1Root(chunkHashes);
    case CommitmentStrategy.BAO_MERKLE_V2:
      return calculateBaoMerkleV2Root(chunkHashes);
    default:
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        `Unknown commitment strategy: ${strategy}`
      );
  }
}

/**
 * Create full root commitment from chunks
 */
export function createRootCommitment(
  chunks: Chunk[],
  artifactType: ArtifactType,
  strategy: CommitmentStrategy = CommitmentStrategy.SIMPLE_CONCAT_V1
): RootCommitment {
  const chunkHashes = chunks.map(c => c.hash);
  const root = calculateRootCommitment(strategy, chunkHashes);
  const totalSize = chunks.reduce((sum, c) => sum + c.size, 0);

  return {
    strategy,
    root,
    chunkHashes,
    metadata: {
      artifactType,
      totalSize,
      chunkCount: chunks.length,
      timestamp: new Date().toISOString(),
    },
  };
}

/**
 * Verify chunk hashes match commitment
 */
export function verifyCommitment(
  commitment: RootCommitment,
  actualChunkHashes: Buffer[]
): boolean {
  // Check chunk count matches
  if (commitment.chunkHashes.length !== actualChunkHashes.length) {
    return false;
  }

  // Verify each chunk hash
  for (let i = 0; i < commitment.chunkHashes.length; i++) {
    if (!commitment.chunkHashes[i].equals(actualChunkHashes[i])) {
      return false;
    }
  }

  // Recalculate and verify root
  const calculatedRoot = calculateRootCommitment(
    commitment.strategy,
    actualChunkHashes
  );

  return commitment.root.equals(calculatedRoot);
}

/**
 * Export commitment to JSON-serializable format
 */
export function exportCommitment(commitment: RootCommitment): Record<string, unknown> {
  return {
    strategy: commitment.strategy,
    root: commitment.root.toString('hex'),
    chunkHashes: commitment.chunkHashes.map(h => h.toString('hex')),
    metadata: commitment.metadata,
  };
}

/**
 * Import commitment from JSON
 */
export function importCommitment(json: Record<string, unknown>): RootCommitment {
  return {
    strategy: json.strategy as CommitmentStrategy,
    root: Buffer.from(json.root as string, 'hex'),
    chunkHashes: (json.chunkHashes as string[]).map(h => Buffer.from(h, 'hex')),
    metadata: json.metadata as RootCommitment['metadata'],
  };
}

/**
 * Verify root matches expected value
 */
export function verifyRoot(
  actualRoot: Buffer,
  expectedRoot: Buffer
): boolean {
  return actualRoot.equals(expectedRoot);
}

/**
 * Calculate incremental root (useful for streaming verification)
 */
export function calculateIncrementalRoot(
  strategy: CommitmentStrategy,
  verifiedChunkHashes: Buffer[],
  newChunkHash: Buffer
): Buffer {
  const allHashes = [...verifiedChunkHashes, newChunkHash];
  return calculateRootCommitment(strategy, allHashes);
}
