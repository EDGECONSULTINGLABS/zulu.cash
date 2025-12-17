/**
 * BLAKE3 Hashing using blake3-bao package (pure JS with Bao support)
 */

// @ts-ignore - blake3-bao has types but needs moduleResolution adjustment
import { hash, Hasher } from 'blake3-bao/blake3';

/**
 * Hash a buffer using BLAKE3
 */
export function hashBuffer(data: Buffer): Buffer {
  return Buffer.from(hash(data));
}

/**
 * Hash multiple buffers sequentially (for commitment roots)
 */
export function hashBuffers(buffers: Buffer[]): Buffer {
  const hasher = new Hasher();
  for (const buf of buffers) {
    hasher.update(buf);
  }
  return Buffer.from(hasher.finalize());
}

/**
 * Create a keyed hash (for MAC operations)
 * Note: blake3 package doesn't support keyed hashing, using regular hash
 */
export function keyedHash(key: Buffer, data: Buffer): Buffer {
  // Concatenate key and data as fallback
  const combined = Buffer.concat([key, data]);
  return hashBuffer(combined);
}

/**
 * Derive a key using BLAKE3 in KDF mode
 * Note: blake3 package doesn't support context, using regular hash
 */
export function deriveKey(context: string, keyMaterial: Buffer, outputLength = 32): Buffer {
  const contextBuf = Buffer.from(context, 'utf8');
  const combined = Buffer.concat([contextBuf, keyMaterial]);
  const fullHash = hashBuffer(combined);
  return fullHash.slice(0, outputLength);
}

/**
 * Stream hasher for large files
 */
export class BLAKE3StreamHasher {
  private hasher: Hasher;

  constructor() {
    this.hasher = new Hasher();
  }

  update(chunk: Buffer): void {
    this.hasher.update(chunk);
  }

  finalize(): Buffer {
    return Buffer.from(this.hasher.finalize());
  }

  reset(): void {
    this.hasher = new Hasher();
  }
}

/**
 * Compute BLAKE3 hash of file in chunks
 */
export async function hashFile(
  filePath: string,
  chunkSize = 1024 * 1024
): Promise<Buffer> {
  const fs = require('fs').promises;
  const hasher = new BLAKE3StreamHasher();

  const fd = await fs.open(filePath, 'r');
  try {
    const buffer = Buffer.allocUnsafe(chunkSize);
    let bytesRead: number;

    while ((bytesRead = (await fd.read(buffer, 0, chunkSize)).bytesRead) > 0) {
      hasher.update(buffer.slice(0, bytesRead));
    }

    return hasher.finalize();
  } finally {
    await fd.close();
  }
}

/**
 * Verify BLAKE3 hash matches expected value
 */
export function verifyHash(data: Buffer, expectedHash: Buffer): boolean {
  const actualHash = hashBuffer(data);
  return actualHash.equals(expectedHash);
}

/**
 * Convert hash to hex string
 */
export function hashToHex(hash: Buffer): string {
  return hash.toString('hex');
}

/**
 * Convert hex string to hash buffer
 */
export function hexToHash(hex: string): Buffer {
  return Buffer.from(hex, 'hex');
}
