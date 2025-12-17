/**
 * Ed25519 Key Management and Signing
 */

import * as ed from '@noble/ed25519';
import { sha512 } from '@noble/hashes/sha512';
import * as bip39 from 'bip39';
import { derivePath } from 'ed25519-hd-key';
import { BIP39Seed, Ed25519KeyPair, VerificationError, VerificationErrorCode } from '../types';

// Set hash function for @noble/ed25519
ed.etc.sha512Sync = (...m: Uint8Array[]) => sha512(ed.etc.concatBytes(...m));

/**
 * Generate BIP-39 mnemonic seed phrase
 */
export async function generateMnemonic(
  wordCount: 12 | 15 | 18 | 21 | 24 = 12,
  language = 'english'
): Promise<BIP39Seed> {
  const strength = (wordCount / 3) * 32; // 128, 160, 192, 224, 256 bits
  const mnemonic = bip39.generateMnemonic(strength);
  const seed = await bip39.mnemonicToSeed(mnemonic);

  return {
    mnemonic,
    seed: Buffer.from(seed),
    language,
  };
}

/**
 * Validate BIP-39 mnemonic
 */
export function validateMnemonic(mnemonic: string, language = 'english'): boolean {
  return bip39.validateMnemonic(mnemonic);
}

/**
 * Recover seed from mnemonic
 */
export async function mnemonicToSeed(mnemonic: string): Promise<Buffer> {
  if (!validateMnemonic(mnemonic)) {
    throw new VerificationError(
      VerificationErrorCode.STORAGE_ERROR,
      'Invalid BIP-39 mnemonic phrase'
    );
  }
  const seed = await bip39.mnemonicToSeed(mnemonic);
  return Buffer.from(seed);
}

/**
 * Derive Ed25519 keypair from BIP-39 seed using BIP-44 path
 * Default path: m/44'/1337'/0'/0/N
 * 
 * IMPORTANT: Pass the raw seed Buffer from mnemonicToSeed(), NOT hex-encoded
 */
export async function deriveKeyPair(
  seed: Buffer,
  accountIndex = 0,
  keyIndex = 0
): Promise<Ed25519KeyPair> {
  // BIP-44 path: m / purpose' / coin_type' / account' / change / address_index
  // Using coin_type 1337 for Zulu
  // Note: ed25519-hd-key uses "m/" prefix format
  const path = `m/44'/1337'/${accountIndex}'/0'/${keyIndex}'`;

  // derivePath expects hex-encoded seed string
  const { key } = derivePath(path, seed.toString('hex'));
  const privateKey = Buffer.from(key);

  // Derive public key from private key
  const publicKey = Buffer.from(await ed.getPublicKeyAsync(privateKey));

  return {
    publicKey,
    privateKey,
    path,
  };
}

/**
 * Sign message with Ed25519 private key
 */
export async function signMessage(
  message: Buffer,
  privateKey: Buffer
): Promise<Buffer> {
  const signature = await ed.signAsync(message, privateKey);
  return Buffer.from(signature);
}

/**
 * Verify Ed25519 signature
 */
export async function verifySignature(
  message: Buffer,
  signature: Buffer,
  publicKey: Buffer
): Promise<boolean> {
  try {
    return await ed.verifyAsync(signature, message, publicKey);
  } catch (error) {
    return false;
  }
}

/**
 * Get key ID from public key (hex representation)
 */
export function getKeyId(publicKey: Buffer): string {
  return publicKey.toString('hex');
}

/**
 * Export keypair to JSON (WARNING: exposes private key)
 */
export function exportKeyPair(keyPair: Ed25519KeyPair): Record<string, unknown> {
  return {
    publicKey: keyPair.publicKey.toString('hex'),
    privateKey: keyPair.privateKey.toString('hex'),
    path: keyPair.path,
  };
}

/**
 * Import keypair from JSON
 */
export function importKeyPair(json: Record<string, unknown>): Ed25519KeyPair {
  return {
    publicKey: Buffer.from(json.publicKey as string, 'hex'),
    privateKey: Buffer.from(json.privateKey as string, 'hex'),
    path: json.path as string,
  };
}

/**
 * Deterministic key derivation test
 */
export async function testDeterministicDerivation(
  mnemonic: string
): Promise<boolean> {
  const seed1 = await mnemonicToSeed(mnemonic);
  const seed2 = await mnemonicToSeed(mnemonic);

  const key1 = await deriveKeyPair(seed1, 0, 0);
  const key2 = await deriveKeyPair(seed2, 0, 0);

  return (
    key1.publicKey.equals(key2.publicKey) &&
    key1.privateKey.equals(key2.privateKey) &&
    key1.path === key2.path
  );
}
