/**
 * Whisper Model Verification Example
 * Demonstrates verified model download with receipt generation
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import {
  VerificationSystem,
  generateMnemonic,
  deriveKeyPair,
  createManifest,
  ArtifactType,
  CommitmentStrategy,
  TrustPolicy,
  CHUNK_SIZES,
} from '../src';
import { streamFileChunks } from '../src/chunking/deterministic';
import { createRootCommitment } from '../src/chunking/commitment';
import { createArtifactReceipt } from '../src/crypto/receipts';

async function verifyWhisperModel() {
  console.log('🎤 Whisper Model Verification Example\n');

  // Initialize system
  const verifier = new VerificationSystem({
    dbPath: './data/verification.db',
    encryptionKey: 'demo-key-change-in-production',
    tempDir: './temp',
    trustConfig: {
      policy: TrustPolicy.WARN,
      teamKeyring: [],
      userApprovedKeys: [],
      revokedKeys: [],
      expiryWarningDays: 30,
    },
  });

  await verifier.initialize();

  // ============================================================================
  // Scenario: Zulu team publishes Whisper model
  // ============================================================================

  console.log('📦 Simulating Whisper model publication...\n');

  // Publisher's keys (Zulu team)
  const publisherSeed = await generateMnemonic(12);
  const publisherKey = await deriveKeyPair(publisherSeed.seed, 0, 0);

  // Approve Zulu team key
  await verifier.approveKey(publisherKey.publicKey.toString('hex'));

  // ============================================================================
  // Step 1: Create model file (simulated)
  // ============================================================================

  const modelDir = './data/models';
  await fs.mkdir(modelDir, { recursive: true });
  const modelPath = path.join(modelDir, 'whisper-tiny-en.gguf');

  // Create 10MB dummy model file
  console.log('Creating dummy model file (10MB)...');
  const modelSize = 10 * 1024 * 1024;
  const modelData = Buffer.alloc(modelSize);
  // Fill with pattern for deterministic content
  for (let i = 0; i < modelSize; i += 4) {
    modelData.writeUInt32LE(i & 0xffffffff, i);
  }
  await fs.writeFile(modelPath, modelData);

  // ============================================================================
  // Step 2: Chunk model and calculate commitment
  // ============================================================================

  console.log('Chunking model and calculating commitment...');
  const chunkSize = CHUNK_SIZES[ArtifactType.MODEL];
  const chunks: any[] = [];

  for await (const chunk of streamFileChunks(modelPath, chunkSize)) {
    chunks.push({
      index: chunk.index,
      hash: chunk.hash,
      size: chunk.size,
    });
  }

  const chunkHashes = chunks.map(c => c.hash);
  const commitment = createRootCommitment(
    chunks,
    ArtifactType.MODEL,
    CommitmentStrategy.SIMPLE_CONCAT_V1
  );

  console.log(`✅ Model chunked: ${chunks.length} chunks`);
  console.log(`✅ Root commitment: ${commitment.root.toString('hex').substring(0, 32)}...\n`);

  // ============================================================================
  // Step 3: Create signed manifest
  // ============================================================================

  console.log('Creating signed manifest...');
  const manifest = await createManifest(
    'whisper-tiny-en',
    '1.0.0',
    ArtifactType.MODEL,
    'Zulu Team',
    publisherKey.publicKey,
    commitment.root,
    chunkHashes,
    CommitmentStrategy.SIMPLE_CONCAT_V1,
    {
      size: modelSize,
      chunkSize,
      description: 'Whisper Tiny English model for local transcription',
    },
    publisherKey.privateKey
  );

  // Save manifest
  const manifestPath = path.join(modelDir, 'whisper-tiny-en.manifest.json');
  await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`✅ Manifest saved: ${manifestPath}\n`);

  // ============================================================================
  // Step 4: User downloads and verifies model
  // ============================================================================

  console.log('🔍 Verifying downloaded model...');
  const result = await verifier.verifyArtifact(
    modelPath,
    manifest,
    path.join(modelDir, 'whisper-tiny-en-verified.gguf')
  );

  if (result.success) {
    console.log('✅ Model verification PASSED');
    console.log(`   Verified ${result.verifiedChunks}/${result.totalChunks} chunks`);
    console.log(`   Root: ${result.root.substring(0, 32)}...\n`);
  } else {
    console.log('❌ Model verification FAILED');
    console.log(`   Error: ${result.error?.message}\n`);
    return;
  }

  // ============================================================================
  // Step 5: Generate and store receipt
  // ============================================================================

  console.log('📝 Generating receipt...');
  const receipt = await createArtifactReceipt(
    manifest.artifactId,
    manifest.artifactVersion,
    commitment.root,
    publisherKey.privateKey,
    publisherKey.publicKey,
    {
      artifactType: ArtifactType.MODEL,
      size: modelSize,
      chunkCount: chunks.length,
      strategy: CommitmentStrategy.SIMPLE_CONCAT_V1,
    }
  );

  await verifier.storeArtifactReceipt(receipt);
  console.log(`✅ Receipt stored: ${receipt.receiptHash.substring(0, 32)}...`);

  // Save receipt to file
  const receiptPath = path.join(modelDir, 'whisper-tiny-en.receipt.json');
  await fs.writeFile(
    receiptPath,
    JSON.stringify(
      {
        ...receipt,
        root: receipt.root.toString('hex'),
        signerPubkey: receipt.signerPubkey.toString('hex'),
        signature: receipt.signature.toString('hex'),
      },
      null,
      2
    )
  );
  console.log(`✅ Receipt exported: ${receiptPath}\n`);

  // ============================================================================
  // Summary
  // ============================================================================

  console.log('🎉 Whisper model verification complete!\n');
  console.log('Files created:');
  console.log(`  • Model: ${modelPath}`);
  console.log(`  • Manifest: ${manifestPath}`);
  console.log(`  • Receipt: ${receiptPath}`);
  console.log(`  • Verified: ${modelPath.replace('.gguf', '-verified.gguf')}\n`);

  console.log('Chain of custody established:');
  console.log(`  • Publisher: Zulu Team`);
  console.log(`  • Public Key: ${publisherKey.publicKey.toString('hex').substring(0, 32)}...`);
  console.log(`  • Receipt Hash: ${receipt.receiptHash.substring(0, 32)}...`);
  console.log(`  • Root Commitment: ${commitment.root.toString('hex').substring(0, 32)}...`);

  verifier.close();
}

// Run example
verifyWhisperModel().catch(console.error);
