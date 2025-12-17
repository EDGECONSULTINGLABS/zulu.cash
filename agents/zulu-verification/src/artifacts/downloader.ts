/**
 * Streaming Artifact Downloader with Resume Integrity
 */

import * as fs from 'fs/promises';
import * as fsSync from 'fs';
import * as path from 'path';
import {
  ArtifactManifest,
  ResumeManifest,
  VerificationResult,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { verifyChunkHash } from '../chunking/deterministic';
import { hashBuffer } from '../crypto/blake3';
import { createHash } from 'crypto';

const RESUME_LAST_N_CHUNKS = 5; // Re-verify last N chunks on resume

export interface DownloadOptions {
  tempDir?: string;
  resumable?: boolean;
  onProgress?: (downloaded: number, total: number) => void;
  onChunkVerified?: (chunkIndex: number, totalChunks: number) => void;
}

export class StreamingDownloader {
  private manifest: ArtifactManifest;
  private tempDir: string;
  private resumable: boolean;

  constructor(manifest: ArtifactManifest, options: DownloadOptions = {}) {
    this.manifest = manifest;
    this.tempDir = options.tempDir || './temp';
    this.resumable = options.resumable ?? true;
  }

  /**
   * Download and verify artifact
   */
  async download(
    fetchChunk: (index: number) => Promise<Buffer>,
    outputPath: string,
    options: DownloadOptions = {}
  ): Promise<VerificationResult> {
    const startTime = Date.now();

    try {
      // Ensure temp directory exists
      await fs.mkdir(this.tempDir, { recursive: true });

      const tempPath = path.join(
        this.tempDir,
        `${this.manifest.artifactId}_${this.manifest.artifactVersion}.partial`
      );
      const resumeManifestPath = `${tempPath}.resume.json`;

      // Check for resume state
      let resumeManifest: ResumeManifest | null = null;
      if (this.resumable) {
        resumeManifest = await this.loadResumeManifest(resumeManifestPath);

        if (resumeManifest) {
          // Validate resume state integrity
          if (!this.validateResumeManifest(resumeManifest)) {
            console.warn('Resume state corrupted, starting fresh');
            resumeManifest = null;
            await fs.unlink(resumeManifestPath).catch(() => {});
            await fs.unlink(tempPath).catch(() => {});
          }
        }
      }

      const totalChunks = this.manifest.metadata.chunkCount;
      let verifiedChunks = resumeManifest?.verifiedChunks || [];
      let startChunk = 0;

      // If resuming, re-verify last N chunks to prevent poisoning
      if (resumeManifest && verifiedChunks.length > 0) {
        const reVerifyFrom = Math.max(
          0,
          verifiedChunks.length - RESUME_LAST_N_CHUNKS
        );
        
        console.log(
          `Resuming from chunk ${verifiedChunks.length}, re-verifying last ${
            verifiedChunks.length - reVerifyFrom
          } chunks`
        );

        // Re-verify last N chunks
        const tempFile = await fs.open(tempPath, 'r');
        try {
          for (let i = reVerifyFrom; i < verifiedChunks.length; i++) {
            const chunkIndex = verifiedChunks[i];
            const expectedHash = Buffer.from(
              this.manifest.commitment.chunkHashes[chunkIndex],
              'hex'
            );

            const chunkSize = this.manifest.metadata.chunkSize;
            const offset = chunkIndex * chunkSize;
            const buffer = Buffer.allocUnsafe(chunkSize);
            const { bytesRead } = await tempFile.read(
              buffer,
              0,
              chunkSize,
              offset
            );

            const chunkData = buffer.slice(0, bytesRead);
            if (!verifyChunkHash(chunkData, expectedHash)) {
              throw new VerificationError(
                VerificationErrorCode.RESUME_STATE_CORRUPT_ERROR,
                `Resume verification failed at chunk ${chunkIndex}`
              );
            }
          }
        } finally {
          await tempFile.close();
        }

        startChunk = verifiedChunks.length;
      } else {
        // Start fresh
        verifiedChunks = [];
      }

      // Open temp file for writing
      const flags = resumeManifest ? 'r+' : 'w';
      const tempFile = await fs.open(tempPath, flags);

      try {
        // Download and verify chunks
        for (let i = startChunk; i < totalChunks; i++) {
          // Fetch chunk
          let chunkData: Buffer;
          try {
            chunkData = await fetchChunk(i);
          } catch (error) {
            throw new VerificationError(
              VerificationErrorCode.NETWORK_ERROR,
              `Failed to fetch chunk ${i}: ${(error as Error).message}`
            );
          }

          // Verify chunk hash
          const expectedHash = Buffer.from(
            this.manifest.commitment.chunkHashes[i],
            'hex'
          );

          if (!verifyChunkHash(chunkData, expectedHash)) {
            throw new VerificationError(
              VerificationErrorCode.CHUNK_HASH_MISMATCH_ERROR,
              `Chunk ${i} hash mismatch`
            );
          }

          // Write chunk to temp file
          const offset = i * this.manifest.metadata.chunkSize;
          await tempFile.write(chunkData, 0, chunkData.length, offset);

          verifiedChunks.push(i);

          // Save resume state
          if (this.resumable && i < totalChunks - 1) {
            await this.saveResumeManifest(resumeManifestPath, verifiedChunks);
          }

          // Progress callback
          if (options.onChunkVerified) {
            options.onChunkVerified(i + 1, totalChunks);
          }

          if (options.onProgress) {
            const downloaded = (i + 1) * this.manifest.metadata.chunkSize;
            options.onProgress(
              Math.min(downloaded, this.manifest.metadata.size),
              this.manifest.metadata.size
            );
          }
        }
      } finally {
        await tempFile.close();
      }

      // Verify final root
      const finalRoot = Buffer.from(this.manifest.commitment.root, 'hex');
      const actualRoot = await this.calculateFileRoot(tempPath);

      if (!finalRoot.equals(actualRoot)) {
        throw new VerificationError(
          VerificationErrorCode.ROOT_MISMATCH_ERROR,
          'Final root hash mismatch'
        );
      }

      // Atomically move temp file to final location
      await this.atomicMove(tempPath, outputPath);

      // Clean up resume state
      if (this.resumable) {
        await fs.unlink(resumeManifestPath).catch(() => {});
      }

      const duration = Date.now() - startTime;
      console.log(
        `Download completed in ${duration}ms (${(
          this.manifest.metadata.size /
          (1024 * 1024)
        ).toFixed(2)} MB)`
      );

      return {
        success: true,
        artifactId: this.manifest.artifactId,
        root: this.manifest.commitment.root,
        verifiedChunks: totalChunks,
        totalChunks,
        timestamp: new Date().toISOString(),
      };
    } catch (error) {
      if (error instanceof VerificationError) {
        return {
          success: false,
          artifactId: this.manifest.artifactId,
          root: this.manifest.commitment.root,
          verifiedChunks: 0,
          totalChunks: this.manifest.metadata.chunkCount,
          error,
          timestamp: new Date().toISOString(),
        };
      }

      throw error;
    }
  }

  /**
   * Calculate root hash of file
   */
  private async calculateFileRoot(filePath: string): Promise<Buffer> {
    const chunkHashes: Buffer[] = [];
    const chunkSize = this.manifest.metadata.chunkSize;
    const fd = await fs.open(filePath, 'r');

    try {
      const buffer = Buffer.allocUnsafe(chunkSize);
      let offset = 0;

      while (true) {
        const { bytesRead } = await fd.read(buffer, 0, chunkSize, offset);
        if (bytesRead === 0) break;

        const chunkData = buffer.slice(0, bytesRead);
        chunkHashes.push(hashBuffer(chunkData));

        offset += bytesRead;
      }
    } finally {
      await fd.close();
    }

    // Calculate root using SimpleConcatV1
    const { calculateRootCommitment } = await import('../chunking/commitment');
    const { CommitmentStrategy } = await import('../types');

    return calculateRootCommitment(
      this.manifest.commitment.strategy as any,
      chunkHashes
    );
  }

  /**
   * Save resume manifest
   */
  private async saveResumeManifest(
    path: string,
    verifiedChunks: number[]
  ): Promise<void> {
    const manifest: ResumeManifest = {
      artifactId: this.manifest.artifactId,
      expectedRoot: this.manifest.commitment.root,
      verifiedChunks,
      chunkHashes: this.manifest.commitment.chunkHashes,
      lastVerifiedChunk: verifiedChunks[verifiedChunks.length - 1],
      timestamp: new Date().toISOString(),
      checksum: '', // Will be calculated
    };

    // Calculate checksum
    const data = JSON.stringify({
      artifactId: manifest.artifactId,
      expectedRoot: manifest.expectedRoot,
      verifiedChunks: manifest.verifiedChunks,
      lastVerifiedChunk: manifest.lastVerifiedChunk,
    });
    manifest.checksum = createHash('sha256').update(data).digest('hex');

    await fs.writeFile(path, JSON.stringify(manifest, null, 2), 'utf8');
  }

  /**
   * Load resume manifest
   */
  private async loadResumeManifest(
    path: string
  ): Promise<ResumeManifest | null> {
    try {
      const content = await fs.readFile(path, 'utf8');
      return JSON.parse(content);
    } catch {
      return null;
    }
  }

  /**
   * Validate resume manifest integrity
   */
  private validateResumeManifest(manifest: ResumeManifest): boolean {
    // Verify artifact ID matches
    if (manifest.artifactId !== this.manifest.artifactId) {
      return false;
    }

    // Verify expected root matches
    if (manifest.expectedRoot !== this.manifest.commitment.root) {
      return false;
    }

    // Verify checksum
    const data = JSON.stringify({
      artifactId: manifest.artifactId,
      expectedRoot: manifest.expectedRoot,
      verifiedChunks: manifest.verifiedChunks,
      lastVerifiedChunk: manifest.lastVerifiedChunk,
    });
    const calculatedChecksum = createHash('sha256').update(data).digest('hex');

    return calculatedChecksum === manifest.checksum;
  }

  /**
   * Atomic file move (handles cross-device moves)
   */
  private async atomicMove(source: string, dest: string): Promise<void> {
    try {
      // Try rename first (atomic on same filesystem)
      await fs.rename(source, dest);
    } catch (error) {
      // If rename fails (cross-device), copy and delete
      await fs.copyFile(source, dest);
      await fs.unlink(source);
    }
  }
}
