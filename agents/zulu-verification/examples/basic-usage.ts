/**
 * Basic Usage Example - Zulu Verification System
 */

import {
  VerificationSystem,
  generateMnemonic,
  deriveKeyPair,
  ArtifactType,
  TrustPolicy,
} from '../src';

async function basicExample() {
  console.log('🔐 Zulu Verification System - Basic Usage\n');

  // ============================================================================
  // Step 1: Initialize Verification System
  // ============================================================================
  
  console.log('1️⃣ Initializing verification system...');
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
    enableKeychain: true,
  });

  await verifier.initialize();
  console.log('✅ System initialized\n');

  // ============================================================================
  // Step 2: Generate BIP-39 Seed Phrase
  // ============================================================================
  
  console.log('2️⃣ Generating BIP-39 seed phrase...');
  const seed = await generateMnemonic(12);
  console.log(`Mnemonic: ${seed.mnemonic}`);
  console.log('⚠️  Store this securely! This is your master key.\n');

  // Store in keychain
  const keychain = verifier.getKeychain();
  if (keychain) {
    await keychain.storeSeedPhrase('demo-user', seed.mnemonic);
    console.log('✅ Seed phrase stored in keychain\n');
  }

  // ============================================================================
  // Step 3: Derive Device Keys
  // ============================================================================
  
  console.log('3️⃣ Deriving device keys from seed...');
  const deviceKey0 = await deriveKeyPair(seed.seed, 0, 0); // First device
  const deviceKey1 = await deriveKeyPair(seed.seed, 0, 1); // Second device
  
  console.log(`Device 0 Public Key: ${deviceKey0.publicKey.toString('hex').substring(0, 16)}...`);
  console.log(`Device 0 Path: ${deviceKey0.path}`);
  console.log(`Device 1 Public Key: ${deviceKey1.publicKey.toString('hex').substring(0, 16)}...`);
  console.log(`Device 1 Path: ${deviceKey1.path}\n`);

  // Store private keys in keychain
  if (keychain) {
    const keyId0 = deviceKey0.publicKey.toString('hex');
    await keychain.storePrivateKey(keyId0, deviceKey0.privateKey.toString('hex'));
    console.log('✅ Device keys stored in keychain\n');
  }

  // ============================================================================
  // Step 4: Approve Keys (Trust Management)
  // ============================================================================
  
  console.log('4️⃣ Setting up trust model...');
  const pubkeyHex = deviceKey0.publicKey.toString('hex');
  await verifier.approveKey(pubkeyHex);
  console.log(`✅ Approved key: ${pubkeyHex.substring(0, 16)}...\n`);

  // ============================================================================
  // Step 5: Verify Artifact (Example)
  // ============================================================================
  
  console.log('5️⃣ Ready to verify artifacts!');
  console.log('Example workflow:');
  console.log('  • Create manifest with publisher signature');
  console.log('  • Download and verify artifact chunks');
  console.log('  • Store verified receipt in database');
  console.log('  • Export/import session data with commitments\n');

  // ============================================================================
  // Step 6: Check Expiring Keys
  // ============================================================================
  
  console.log('6️⃣ Checking key expiration...');
  const expiringKeys = await verifier.getExpiringKeys(180); // Next 180 days
  console.log(`Keys expiring soon: ${expiringKeys.length}\n`);

  // ============================================================================
  // Cleanup
  // ============================================================================
  
  console.log('✅ Basic example completed!');
  console.log('\nNext steps:');
  console.log('  • See whisper-model-example.ts for artifact verification');
  console.log('  • See session-export-example.ts for memory export/import');
  console.log('  • See plugin-sandbox-example.ts for plugin management');
  
  verifier.close();
}

// Run example
basicExample().catch(console.error);
