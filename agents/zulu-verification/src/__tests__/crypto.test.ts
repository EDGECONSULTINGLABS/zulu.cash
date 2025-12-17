/**
 * Crypto Unit Tests
 */

import { describe, test, expect } from '@jest/globals';
import {
  generateMnemonic,
  validateMnemonic,
  mnemonicToSeed,
  deriveKeyPair,
  signMessage,
  verifySignature,
  testDeterministicDerivation,
} from '../crypto/ed25519';
import { hashBuffer, verifyHash } from '../crypto/blake3';
import {
  createArtifactReceipt,
  verifyArtifactReceipt,
  createSessionReceipt,
  verifySessionReceipt,
  generateArtifactReceiptHash,
  generateSessionReceiptHash,
} from '../crypto/receipts';
import { ArtifactType, CommitmentStrategy } from '../types';

describe('BIP-39 Seed Generation', () => {
  test('generates valid 12-word mnemonic', async () => {
    const seed = await generateMnemonic(12);
    expect(seed.mnemonic.split(' ')).toHaveLength(12);
    expect(validateMnemonic(seed.mnemonic)).toBe(true);
    expect(seed.seed).toBeInstanceOf(Buffer);
    expect(seed.seed.length).toBe(64); // 512 bits
  });

  test('generates valid 24-word mnemonic', async () => {
    const seed = await generateMnemonic(24);
    expect(seed.mnemonic.split(' ')).toHaveLength(24);
    expect(validateMnemonic(seed.mnemonic)).toBe(true);
  });

  test('validates correct mnemonic', () => {
    const validMnemonic =
      'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
    expect(validateMnemonic(validMnemonic)).toBe(true);
  });

  test('rejects invalid mnemonic', () => {
    const invalidMnemonic = 'invalid mnemonic phrase that should fail';
    expect(validateMnemonic(invalidMnemonic)).toBe(false);
  });

  test('recovers same seed from mnemonic', async () => {
    const mnemonic =
      'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
    const seed1 = await mnemonicToSeed(mnemonic);
    const seed2 = await mnemonicToSeed(mnemonic);
    expect(seed1.equals(seed2)).toBe(true);
  });
});

describe('Ed25519 Key Derivation', () => {
  test('derives deterministic keypair from seed', async () => {
    const seed = await generateMnemonic(12);
    const key1 = await deriveKeyPair(seed.seed, 0, 0);
    const key2 = await deriveKeyPair(seed.seed, 0, 0);

    expect(key1.publicKey.equals(key2.publicKey)).toBe(true);
    expect(key1.privateKey.equals(key2.privateKey)).toBe(true);
    expect(key1.path).toBe(key2.path);
    expect(key1.path).toBe("m/44'/1337'/0'/0/0");
  });

  test('derives different keys for different indices', async () => {
    const seed = await generateMnemonic(12);
    const key1 = await deriveKeyPair(seed.seed, 0, 0);
    const key2 = await deriveKeyPair(seed.seed, 0, 1);

    expect(key1.publicKey.equals(key2.publicKey)).toBe(false);
    expect(key1.privateKey.equals(key2.privateKey)).toBe(false);
  });

  test('deterministic derivation is stable', async () => {
    const mnemonic =
      'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
    const result = await testDeterministicDerivation(mnemonic);
    expect(result).toBe(true);
  });
});

describe('Ed25519 Signing', () => {
  test('signs and verifies message', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);
    const message = Buffer.from('test message', 'utf8');

    const signature = await signMessage(message, keyPair.privateKey);
    const valid = await verifySignature(
      message,
      signature,
      keyPair.publicKey
    );

    expect(valid).toBe(true);
  });

  test('rejects invalid signature', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);
    const message = Buffer.from('test message', 'utf8');

    const signature = await signMessage(message, keyPair.privateKey);
    
    // Tamper with signature
    signature[0] ^= 1;

    const valid = await verifySignature(
      message,
      signature,
      keyPair.publicKey
    );

    expect(valid).toBe(false);
  });

  test('rejects signature with wrong public key', async () => {
    const seed = await generateMnemonic(12);
    const keyPair1 = await deriveKeyPair(seed.seed, 0, 0);
    const keyPair2 = await deriveKeyPair(seed.seed, 0, 1);
    const message = Buffer.from('test message', 'utf8');

    const signature = await signMessage(message, keyPair1.privateKey);
    const valid = await verifySignature(
      message,
      signature,
      keyPair2.publicKey
    );

    expect(valid).toBe(false);
  });
});

describe('BLAKE3 Hashing', () => {
  test('hashes buffer consistently', () => {
    const data = Buffer.from('test data', 'utf8');
    const hash1 = hashBuffer(data);
    const hash2 = hashBuffer(data);

    expect(hash1.equals(hash2)).toBe(true);
    expect(hash1.length).toBe(32); // 256 bits
  });

  test('produces different hashes for different data', () => {
    const data1 = Buffer.from('test data 1', 'utf8');
    const data2 = Buffer.from('test data 2', 'utf8');

    const hash1 = hashBuffer(data1);
    const hash2 = hashBuffer(data2);

    expect(hash1.equals(hash2)).toBe(false);
  });

  test('verifies hash correctly', () => {
    const data = Buffer.from('test data', 'utf8');
    const hash = hashBuffer(data);

    expect(verifyHash(data, hash)).toBe(true);
    
    // Tamper with data
    const tamperedData = Buffer.from('test data!', 'utf8');
    expect(verifyHash(tamperedData, hash)).toBe(false);
  });
});

describe('Receipt Generation', () => {
  test('creates and verifies artifact receipt', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);

    const artifactId = 'test-model';
    const version = '1.0.0';
    const root = Buffer.from('a'.repeat(64), 'hex');

    const receipt = await createArtifactReceipt(
      artifactId,
      version,
      root,
      keyPair.privateKey,
      keyPair.publicKey,
      {
        artifactType: ArtifactType.MODEL,
        size: 1024,
        chunkCount: 1,
        strategy: CommitmentStrategy.SIMPLE_CONCAT_V1,
      }
    );

    const valid = await verifyArtifactReceipt(receipt);
    expect(valid).toBe(true);
  });

  test('creates and verifies session receipt', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);

    const sessionId = 'test-session-123';
    const root = Buffer.from('b'.repeat(64), 'hex');

    const receipt = await createSessionReceipt(
      sessionId,
      root,
      keyPair.privateKey,
      keyPair.publicKey,
      {
        duration: 3600,
        modelId: 'gpt-4',
        tokenCount: 1000,
        transcriptSize: 10000,
      }
    );

    const valid = await verifySessionReceipt(receipt);
    expect(valid).toBe(true);
  });

  test('generates content-addressed receipt hash', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);

    const artifactId = 'test-model';
    const version = '1.0.0';
    const root = Buffer.from('a'.repeat(64), 'hex');

    const hash1 = generateArtifactReceiptHash(root, version, keyPair.publicKey);
    const hash2 = generateArtifactReceiptHash(root, version, keyPair.publicKey);

    expect(hash1).toBe(hash2);
    expect(hash1).toMatch(/^[a-f0-9]{64}$/); // SHA-256 hex
  });

  test('prevents receipt collision', async () => {
    const seed = await generateMnemonic(12);
    const keyPair = await deriveKeyPair(seed.seed, 0, 0);

    const artifactId = 'test-model';
    const version = '1.0.0';
    const root = Buffer.from('a'.repeat(64), 'hex');

    // Same inputs should produce same receipt hash
    const receipt1 = await createArtifactReceipt(
      artifactId,
      version,
      root,
      keyPair.privateKey,
      keyPair.publicKey,
      {
        artifactType: ArtifactType.MODEL,
        size: 1024,
        chunkCount: 1,
        strategy: CommitmentStrategy.SIMPLE_CONCAT_V1,
      }
    );

    const receipt2 = await createArtifactReceipt(
      artifactId,
      version,
      root,
      keyPair.privateKey,
      keyPair.publicKey,
      {
        artifactType: ArtifactType.MODEL,
        size: 2048, // Different metadata
        chunkCount: 2,
        strategy: CommitmentStrategy.SIMPLE_CONCAT_V1,
      }
    );

    // Receipt hashes should be the same (content-addressed)
    expect(receipt1.receiptHash).toBe(receipt2.receiptHash);
  });
});
