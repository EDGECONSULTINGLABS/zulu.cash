/**
 * Receipt Generation and Verification
 */

import { createHash } from 'crypto';
import { ArtifactReceipt, SessionReceipt, VerificationError, VerificationErrorCode } from '../types';
import { signMessage, verifySignature } from './ed25519';

/**
 * Generate artifact receipt hash (content-addressed)
 * receipt_hash = SHA256(root || version || signer_pubkey)
 */
export function generateArtifactReceiptHash(
  root: Buffer,
  version: string,
  signerPubkey: Buffer
): string {
  const data = Buffer.concat([
    root,
    Buffer.from('|'),
    Buffer.from(version, 'utf8'),
    Buffer.from('|'),
    signerPubkey,
  ]);
  return createHash('sha256').update(data).digest('hex');
}

/**
 * Generate session receipt hash (content-addressed)
 * receipt_hash = SHA256(root || session_id || signer_pubkey)
 */
export function generateSessionReceiptHash(
  root: Buffer,
  sessionId: string,
  signerPubkey: Buffer
): string {
  const data = Buffer.concat([
    root,
    Buffer.from('|'),
    Buffer.from(sessionId, 'utf8'),
    Buffer.from('|'),
    signerPubkey,
  ]);
  return createHash('sha256').update(data).digest('hex');
}

/**
 * Create and sign artifact receipt
 */
export async function createArtifactReceipt(
  artifactId: string,
  version: string,
  root: Buffer,
  privateKey: Buffer,
  publicKey: Buffer,
  metadata: ArtifactReceipt['metadata']
): Promise<ArtifactReceipt> {
  // Generate canonical message to sign
  const message = Buffer.concat([
    Buffer.from(artifactId, 'utf8'),
    Buffer.from('|'),
    Buffer.from(version, 'utf8'),
    Buffer.from('|'),
    root,
  ]);

  const signature = await signMessage(message, privateKey);
  const receiptHash = generateArtifactReceiptHash(root, version, publicKey);

  return {
    receiptHash,
    artifactId,
    version,
    root,
    signerPubkey: publicKey,
    signature,
    timestamp: new Date().toISOString(),
    metadata,
  };
}

/**
 * Verify artifact receipt signature
 */
export async function verifyArtifactReceipt(
  receipt: ArtifactReceipt
): Promise<boolean> {
  // Reconstruct canonical message
  const message = Buffer.concat([
    Buffer.from(receipt.artifactId, 'utf8'),
    Buffer.from('|'),
    Buffer.from(receipt.version, 'utf8'),
    Buffer.from('|'),
    receipt.root,
  ]);

  // Verify signature
  const signatureValid = await verifySignature(
    message,
    receipt.signature,
    receipt.signerPubkey
  );

  if (!signatureValid) {
    return false;
  }

  // Verify receipt hash
  const expectedHash = generateArtifactReceiptHash(
    receipt.root,
    receipt.version,
    receipt.signerPubkey
  );

  return receipt.receiptHash === expectedHash;
}

/**
 * Create and sign session receipt
 */
export async function createSessionReceipt(
  sessionId: string,
  root: Buffer,
  privateKey: Buffer,
  publicKey: Buffer,
  metadata: SessionReceipt['metadata']
): Promise<SessionReceipt> {
  // Generate canonical message to sign
  const message = Buffer.concat([
    Buffer.from(sessionId, 'utf8'),
    Buffer.from('|'),
    root,
  ]);

  const signature = await signMessage(message, privateKey);
  const receiptHash = generateSessionReceiptHash(root, sessionId, publicKey);

  return {
    receiptHash,
    sessionId,
    root,
    signerPubkey: publicKey,
    signature,
    timestamp: new Date().toISOString(),
    metadata,
  };
}

/**
 * Verify session receipt signature
 */
export async function verifySessionReceipt(
  receipt: SessionReceipt
): Promise<boolean> {
  // Reconstruct canonical message
  const message = Buffer.concat([
    Buffer.from(receipt.sessionId, 'utf8'),
    Buffer.from('|'),
    receipt.root,
  ]);

  // Verify signature
  const signatureValid = await verifySignature(
    message,
    receipt.signature,
    receipt.signerPubkey
  );

  if (!signatureValid) {
    return false;
  }

  // Verify receipt hash
  const expectedHash = generateSessionReceiptHash(
    receipt.root,
    receipt.sessionId,
    receipt.signerPubkey
  );

  return receipt.receiptHash === expectedHash;
}

/**
 * Detect receipt collision attempts
 */
export function detectReceiptCollision(
  existingHashes: Set<string>,
  newHash: string
): boolean {
  return existingHashes.has(newHash);
}

/**
 * Validate receipt hash format
 */
export function validateReceiptHash(hash: string): boolean {
  // SHA-256 produces 64-character hex string
  return /^[a-f0-9]{64}$/i.test(hash);
}
