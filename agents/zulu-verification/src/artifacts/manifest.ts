/**
 * Artifact Manifest Management
 */

import {
  ArtifactManifest,
  ArtifactType,
  CommitmentStrategy,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { verifySignature } from '../crypto/ed25519';

/**
 * Create artifact manifest
 */
export async function createManifest(
  artifactId: string,
  version: string,
  artifactType: ArtifactType,
  publisherName: string,
  publisherPubkey: Buffer,
  root: Buffer,
  chunkHashes: Buffer[],
  strategy: CommitmentStrategy,
  metadata: {
    size: number;
    chunkSize: number;
    description?: string;
  },
  privateKey: Buffer
): Promise<ArtifactManifest> {
  const manifest: Omit<ArtifactManifest, 'signature'> = {
    version: '1.0',
    artifactId,
    artifactVersion: version,
    artifactType,
    publisher: {
      name: publisherName,
      pubkey: publisherPubkey.toString('hex'),
    },
    commitment: {
      strategy,
      root: root.toString('hex'),
      chunkHashes: chunkHashes.map(h => h.toString('hex')),
    },
    metadata: {
      ...metadata,
      chunkCount: chunkHashes.length,
      createdAt: new Date().toISOString(),
    },
  };

  // Sign the manifest
  const manifestData = Buffer.from(JSON.stringify(manifest), 'utf8');
  const ed = await import('../crypto/ed25519');
  const signature = await ed.signMessage(manifestData, privateKey);

  return {
    ...manifest,
    signature: signature.toString('hex'),
  };
}

/**
 * Verify manifest signature
 */
export async function verifyManifestSignature(
  manifest: ArtifactManifest
): Promise<boolean> {
  try {
    const { signature, ...manifestWithoutSig } = manifest;
    const manifestData = Buffer.from(JSON.stringify(manifestWithoutSig), 'utf8');
    const signatureBuffer = Buffer.from(signature, 'hex');
    const pubkeyBuffer = Buffer.from(manifest.publisher.pubkey, 'hex');

    return await verifySignature(manifestData, signatureBuffer, pubkeyBuffer);
  } catch (error) {
    return false;
  }
}

/**
 * Validate manifest structure
 */
export function validateManifest(manifest: unknown): manifest is ArtifactManifest {
  if (typeof manifest !== 'object' || manifest === null) {
    return false;
  }

  const m = manifest as Record<string, unknown>;

  // Check required fields
  if (
    m.version !== '1.0' ||
    typeof m.artifactId !== 'string' ||
    typeof m.artifactVersion !== 'string' ||
    typeof m.artifactType !== 'string' ||
    typeof m.publisher !== 'object' ||
    typeof m.commitment !== 'object' ||
    typeof m.metadata !== 'object' ||
    typeof m.signature !== 'string'
  ) {
    return false;
  }

  // Check publisher structure
  const pub = m.publisher as Record<string, unknown>;
  if (typeof pub.name !== 'string' || typeof pub.pubkey !== 'string') {
    return false;
  }

  // Check commitment structure
  const comm = m.commitment as Record<string, unknown>;
  if (
    typeof comm.strategy !== 'string' ||
    typeof comm.root !== 'string' ||
    !Array.isArray(comm.chunkHashes)
  ) {
    return false;
  }

  // Check metadata structure
  const meta = m.metadata as Record<string, unknown>;
  if (
    typeof meta.size !== 'number' ||
    typeof meta.chunkSize !== 'number' ||
    typeof meta.chunkCount !== 'number' ||
    typeof meta.createdAt !== 'string'
  ) {
    return false;
  }

  return true;
}

/**
 * Parse manifest from JSON
 */
export function parseManifest(json: string): ArtifactManifest {
  let parsed: unknown;

  try {
    parsed = JSON.parse(json);
  } catch (error) {
    throw new VerificationError(
      VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
      'Invalid manifest JSON'
    );
  }

  if (!validateManifest(parsed)) {
    throw new VerificationError(
      VerificationErrorCode.MANIFEST_SIGNATURE_ERROR,
      'Invalid manifest structure'
    );
  }

  return parsed;
}

/**
 * Export manifest to JSON string
 */
export function exportManifest(manifest: ArtifactManifest): string {
  return JSON.stringify(manifest, null, 2);
}

/**
 * Load manifest from file
 */
export async function loadManifestFromFile(filePath: string): Promise<ArtifactManifest> {
  const fs = await import('fs/promises');
  const content = await fs.readFile(filePath, 'utf8');
  return parseManifest(content);
}

/**
 * Save manifest to file
 */
export async function saveManifestToFile(
  manifest: ArtifactManifest,
  filePath: string
): Promise<void> {
  const fs = await import('fs/promises');
  const json = exportManifest(manifest);
  await fs.writeFile(filePath, json, 'utf8');
}

/**
 * Verify manifest matches artifact
 */
export function verifyManifestIntegrity(
  manifest: ArtifactManifest,
  actualChunkHashes: Buffer[],
  actualRoot: Buffer
): boolean {
  // Check chunk count
  if (manifest.commitment.chunkHashes.length !== actualChunkHashes.length) {
    return false;
  }

  // Verify each chunk hash
  for (let i = 0; i < manifest.commitment.chunkHashes.length; i++) {
    const manifestHash = Buffer.from(manifest.commitment.chunkHashes[i], 'hex');
    if (!manifestHash.equals(actualChunkHashes[i])) {
      return false;
    }
  }

  // Verify root
  const manifestRoot = Buffer.from(manifest.commitment.root, 'hex');
  return manifestRoot.equals(actualRoot);
}

/**
 * Get manifest summary
 */
export function getManifestSummary(manifest: ArtifactManifest): {
  id: string;
  version: string;
  type: string;
  publisher: string;
  size: string;
  chunks: number;
  created: string;
} {
  const sizeMB = (manifest.metadata.size / (1024 * 1024)).toFixed(2);

  return {
    id: manifest.artifactId,
    version: manifest.artifactVersion,
    type: manifest.artifactType,
    publisher: manifest.publisher.name,
    size: `${sizeMB} MB`,
    chunks: manifest.metadata.chunkCount,
    created: manifest.metadata.createdAt,
  };
}
