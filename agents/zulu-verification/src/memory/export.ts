/**
 * Memory Export/Import with Session Commitments (Phase 2)
 */

import {
  SessionExportBundle,
  SessionReceipt,
  RootCommitment,
  ArtifactType,
  CommitmentStrategy,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { chunkBuffer } from '../chunking/deterministic';
import { createRootCommitment } from '../chunking/commitment';
import { createSessionReceipt, verifySessionReceipt } from '../crypto/receipts';
import { CHUNK_SIZES } from '../types';
import * as fs from 'fs/promises';

export interface SessionData {
  sessionId: string;
  transcript: unknown;
  summary: string;
  entities: unknown[];
  embeddings: Float32Array;
  metadata: {
    duration: number;
    modelId: string;
    tokenCount: number;
  };
}

/**
 * Export session with verified commitment
 */
export async function exportSession(
  sessionData: SessionData,
  privateKey: Buffer,
  publicKey: Buffer
): Promise<SessionExportBundle> {
  // Serialize session data
  const serialized = Buffer.from(
    JSON.stringify({
      transcript: sessionData.transcript,
      summary: sessionData.summary,
      entities: sessionData.entities,
      embeddings: Array.from(sessionData.embeddings),
    }),
    'utf8'
  );

  // Chunk the data
  const chunkSize = CHUNK_SIZES[ArtifactType.MEMORY];
  const chunks = chunkBuffer(serialized, chunkSize);

  // Create commitment
  const commitment = createRootCommitment(
    chunks,
    ArtifactType.MEMORY,
    CommitmentStrategy.SIMPLE_CONCAT_V1
  );

  // Create receipt
  const receipt = await createSessionReceipt(
    sessionData.sessionId,
    commitment.root,
    privateKey,
    publicKey,
    {
      duration: sessionData.metadata.duration,
      modelId: sessionData.metadata.modelId,
      tokenCount: sessionData.metadata.tokenCount,
      transcriptSize: serialized.length,
    }
  );

  return {
    sessionId: sessionData.sessionId,
    transcript: sessionData.transcript,
    summary: sessionData.summary,
    entities: sessionData.entities,
    embeddings: sessionData.embeddings,
    commitment,
    receipt,
  };
}

/**
 * Import and verify session bundle
 */
export async function importSession(
  bundle: SessionExportBundle
): Promise<{
  success: boolean;
  error?: VerificationError;
}> {
  try {
    // Step 1: Verify receipt signature
    const receiptValid = await verifySessionReceipt(bundle.receipt);
    if (!receiptValid) {
      throw new VerificationError(
        VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
        'Invalid session receipt signature'
      );
    }

    // Step 2: Re-serialize and verify commitment
    const serialized = Buffer.from(
      JSON.stringify({
        transcript: bundle.transcript,
        summary: bundle.summary,
        entities: bundle.entities,
        embeddings: Array.from(bundle.embeddings),
      }),
      'utf8'
    );

    const chunkSize = CHUNK_SIZES[ArtifactType.MEMORY];
    const chunks = chunkBuffer(serialized, chunkSize);

    const commitment = createRootCommitment(
      chunks,
      ArtifactType.MEMORY,
      CommitmentStrategy.SIMPLE_CONCAT_V1
    );

    // Verify root matches
    if (!commitment.root.equals(bundle.commitment.root)) {
      throw new VerificationError(
        VerificationErrorCode.ROOT_MISMATCH_ERROR,
        'Session commitment root mismatch'
      );
    }

    // Verify chunk count matches
    if (commitment.chunkHashes.length !== bundle.commitment.chunkHashes.length) {
      throw new VerificationError(
        VerificationErrorCode.CHUNK_HASH_MISMATCH_ERROR,
        'Session chunk count mismatch'
      );
    }

    // Shard-level validation
    for (let i = 0; i < commitment.chunkHashes.length; i++) {
      if (!commitment.chunkHashes[i].equals(bundle.commitment.chunkHashes[i])) {
        throw new VerificationError(
          VerificationErrorCode.CHUNK_HASH_MISMATCH_ERROR,
          `Session shard ${i} hash mismatch`
        );
      }
    }

    return { success: true };
  } catch (error) {
    if (error instanceof VerificationError) {
      return { success: false, error };
    }
    throw error;
  }
}

/**
 * Save export bundle to file
 */
export async function saveExportBundle(
  bundle: SessionExportBundle,
  filePath: string
): Promise<void> {
  const json = JSON.stringify(
    {
      sessionId: bundle.sessionId,
      transcript: bundle.transcript,
      summary: bundle.summary,
      entities: bundle.entities,
      embeddings: Array.from(bundle.embeddings),
      commitment: {
        strategy: bundle.commitment.strategy,
        root: bundle.commitment.root.toString('hex'),
        chunkHashes: bundle.commitment.chunkHashes.map(h => h.toString('hex')),
        metadata: bundle.commitment.metadata,
      },
      receipt: {
        ...bundle.receipt,
        root: bundle.receipt.root.toString('hex'),
        signerPubkey: bundle.receipt.signerPubkey.toString('hex'),
        signature: bundle.receipt.signature.toString('hex'),
      },
    },
    null,
    2
  );

  await fs.writeFile(filePath, json, 'utf8');
}

/**
 * Load export bundle from file
 */
export async function loadExportBundle(
  filePath: string
): Promise<SessionExportBundle> {
  const content = await fs.readFile(filePath, 'utf8');
  const json = JSON.parse(content);

  return {
    sessionId: json.sessionId,
    transcript: json.transcript,
    summary: json.summary,
    entities: json.entities,
    embeddings: new Float32Array(json.embeddings),
    commitment: {
      strategy: json.commitment.strategy,
      root: Buffer.from(json.commitment.root, 'hex'),
      chunkHashes: json.commitment.chunkHashes.map((h: string) =>
        Buffer.from(h, 'hex')
      ),
      metadata: json.commitment.metadata,
    },
    receipt: {
      ...json.receipt,
      root: Buffer.from(json.receipt.root, 'hex'),
      signerPubkey: Buffer.from(json.receipt.signerPubkey, 'hex'),
      signature: Buffer.from(json.receipt.signature, 'hex'),
    },
  };
}

/**
 * Get session integrity status
 */
export function getSessionIntegrityStatus(bundle: SessionExportBundle): {
  hasReceipt: boolean;
  hasCommitment: boolean;
  chunkCount: number;
  rootHash: string;
  signer: string;
  timestamp: string;
} {
  return {
    hasReceipt: Boolean(bundle.receipt),
    hasCommitment: Boolean(bundle.commitment),
    chunkCount: bundle.commitment.chunkHashes.length,
    rootHash: bundle.commitment.root.toString('hex'),
    signer: bundle.receipt.signerPubkey.toString('hex'),
    timestamp: bundle.receipt.timestamp,
  };
}
