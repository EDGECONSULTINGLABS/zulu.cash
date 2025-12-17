/**
 * Deterministic Chunking with Adaptive Sizes
 */

import * as fs from 'fs/promises';
import { ArtifactType, CHUNK_SIZES } from '../types';
import { hashBuffer } from '../crypto/blake3';

export interface Chunk {
  index: number;
  data: Buffer;
  hash: Buffer;
  offset: number;
  size: number;
}

/**
 * Get chunk size for artifact type
 */
export function getChunkSize(artifactType: ArtifactType): number {
  return CHUNK_SIZES[artifactType];
}

/**
 * Split buffer into deterministic chunks
 */
export function chunkBuffer(
  data: Buffer,
  chunkSize: number
): Chunk[] {
  const chunks: Chunk[] = [];
  let offset = 0;
  let index = 0;

  while (offset < data.length) {
    const size = Math.min(chunkSize, data.length - offset);
    const chunkData = data.slice(offset, offset + size);
    const hash = hashBuffer(chunkData);

    chunks.push({
      index,
      data: chunkData,
      hash,
      offset,
      size,
    });

    offset += size;
    index++;
  }

  return chunks;
}

/**
 * Stream file into chunks without loading entire file into memory
 */
export async function* streamFileChunks(
  filePath: string,
  chunkSize: number
): AsyncGenerator<Chunk> {
  const fd = await fs.open(filePath, 'r');
  let offset = 0;
  let index = 0;

  try {
    const buffer = Buffer.allocUnsafe(chunkSize);

    while (true) {
      const result = await fd.read(buffer, 0, chunkSize, offset);
      
      if (result.bytesRead === 0) {
        break;
      }

      const chunkData = buffer.slice(0, result.bytesRead);
      const hash = hashBuffer(chunkData);

      yield {
        index,
        data: chunkData,
        hash,
        offset,
        size: result.bytesRead,
      };

      offset += result.bytesRead;
      index++;
    }
  } finally {
    await fd.close();
  }
}

/**
 * Get chunk hashes without loading chunk data
 */
export async function getChunkHashes(
  filePath: string,
  chunkSize: number
): Promise<Buffer[]> {
  const hashes: Buffer[] = [];

  for await (const chunk of streamFileChunks(filePath, chunkSize)) {
    hashes.push(chunk.hash);
  }

  return hashes;
}

/**
 * Verify chunk hash matches expected
 */
export function verifyChunkHash(
  chunk: Buffer,
  expectedHash: Buffer
): boolean {
  const actualHash = hashBuffer(chunk);
  return actualHash.equals(expectedHash);
}

/**
 * Read specific chunk from file
 */
export async function readChunk(
  filePath: string,
  chunkIndex: number,
  chunkSize: number
): Promise<Chunk> {
  const fd = await fs.open(filePath, 'r');
  const offset = chunkIndex * chunkSize;
  const buffer = Buffer.allocUnsafe(chunkSize);

  try {
    const result = await fd.read(buffer, 0, chunkSize, offset);
    const chunkData = buffer.slice(0, result.bytesRead);
    const hash = hashBuffer(chunkData);

    return {
      index: chunkIndex,
      data: chunkData,
      hash,
      offset,
      size: result.bytesRead,
    };
  } finally {
    await fd.close();
  }
}

/**
 * Calculate total chunks for file
 */
export async function calculateChunkCount(
  filePath: string,
  chunkSize: number
): Promise<number> {
  const stat = await fs.stat(filePath);
  return Math.ceil(stat.size / chunkSize);
}

/**
 * Validate chunk alignment (all chunks except last are full size)
 */
export function validateChunkAlignment(
  chunks: Chunk[],
  expectedChunkSize: number
): boolean {
  for (let i = 0; i < chunks.length - 1; i++) {
    if (chunks[i].size !== expectedChunkSize) {
      return false;
    }
  }
  return true;
}
