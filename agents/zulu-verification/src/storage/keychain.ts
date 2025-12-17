/**
 * OS Keychain Integration with SQLCipher Fallback
 * Supports: macOS Keychain, Windows Credential Manager, Linux Secret Service
 */

import * as keytar from 'keytar';
import { VerificationError, VerificationErrorCode } from '../types';

const SERVICE_NAME = 'zulu.verification';

export interface KeychainAdapter {
  store(key: string, value: string): Promise<void>;
  retrieve(key: string): Promise<string | null>;
  delete(key: string): Promise<boolean>;
  list(): Promise<string[]>;
}

/**
 * OS Native Keychain Adapter
 */
export class NativeKeychainAdapter implements KeychainAdapter {
  async store(key: string, value: string): Promise<void> {
    try {
      await keytar.setPassword(SERVICE_NAME, key, value);
    } catch (error) {
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        `Failed to store key in native keychain: ${(error as Error).message}`
      );
    }
  }

  async retrieve(key: string): Promise<string | null> {
    try {
      return await keytar.getPassword(SERVICE_NAME, key);
    } catch (error) {
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        `Failed to retrieve key from native keychain: ${(error as Error).message}`
      );
    }
  }

  async delete(key: string): Promise<boolean> {
    try {
      return await keytar.deletePassword(SERVICE_NAME, key);
    } catch (error) {
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        `Failed to delete key from native keychain: ${(error as Error).message}`
      );
    }
  }

  async list(): Promise<string[]> {
    try {
      const credentials = await keytar.findCredentials(SERVICE_NAME);
      return credentials.map(c => c.account);
    } catch (error) {
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        `Failed to list keys from native keychain: ${(error as Error).message}`
      );
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      // Try to perform a simple operation to check availability
      await keytar.findCredentials(SERVICE_NAME);
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * SQLCipher Fallback Adapter (implemented in database.ts)
 */
export class SQLCipherKeychainAdapter implements KeychainAdapter {
  private db: any; // Will be SQLCipherDatabase instance

  constructor(db: any) {
    this.db = db;
  }

  async store(key: string, value: string): Promise<void> {
    const encrypted = await this.encrypt(value);
    await this.db.storeSecret(key, encrypted);
  }

  async retrieve(key: string): Promise<string | null> {
    const encrypted = await this.db.retrieveSecret(key);
    if (!encrypted) return null;
    return await this.decrypt(encrypted);
  }

  async delete(key: string): Promise<boolean> {
    return await this.db.deleteSecret(key);
  }

  async list(): Promise<string[]> {
    return await this.db.listSecrets();
  }

  private async encrypt(value: string): Promise<string> {
    // Encryption handled by SQLCipher at database level
    return value;
  }

  private async decrypt(value: string): Promise<string> {
    // Decryption handled by SQLCipher at database level
    return value;
  }
}

/**
 * Unified Keychain Manager with automatic fallback
 */
export class KeychainManager {
  private adapter: KeychainAdapter;
  private fallbackAdapter?: KeychainAdapter;
  private usingFallback = false;

  private constructor(
    adapter: KeychainAdapter,
    fallbackAdapter?: KeychainAdapter
  ) {
    this.adapter = adapter;
    this.fallbackAdapter = fallbackAdapter;
  }

  static async create(
    fallbackDb?: any
  ): Promise<KeychainManager> {
    const nativeAdapter = new NativeKeychainAdapter();
    const isAvailable = await nativeAdapter.isAvailable();

    if (isAvailable) {
      const fallbackAdapter = fallbackDb
        ? new SQLCipherKeychainAdapter(fallbackDb)
        : undefined;

      return new KeychainManager(nativeAdapter, fallbackAdapter);
    } else if (fallbackDb) {
      const manager = new KeychainManager(
        new SQLCipherKeychainAdapter(fallbackDb)
      );
      manager.usingFallback = true;
      return manager;
    } else {
      throw new VerificationError(
        VerificationErrorCode.STORAGE_ERROR,
        'No keychain storage available (native or fallback)'
      );
    }
  }

  async store(key: string, value: string): Promise<void> {
    try {
      await this.adapter.store(key, value);
    } catch (error) {
      if (this.fallbackAdapter && !this.usingFallback) {
        console.warn('Native keychain failed, using fallback:', error);
        this.adapter = this.fallbackAdapter;
        this.usingFallback = true;
        await this.adapter.store(key, value);
      } else {
        throw error;
      }
    }
  }

  async retrieve(key: string): Promise<string | null> {
    try {
      return await this.adapter.retrieve(key);
    } catch (error) {
      if (this.fallbackAdapter && !this.usingFallback) {
        console.warn('Native keychain failed, using fallback:', error);
        this.adapter = this.fallbackAdapter;
        this.usingFallback = true;
        return await this.adapter.retrieve(key);
      }
      throw error;
    }
  }

  async delete(key: string): Promise<boolean> {
    return await this.adapter.delete(key);
  }

  async list(): Promise<string[]> {
    return await this.adapter.list();
  }

  isUsingFallback(): boolean {
    return this.usingFallback;
  }

  async storeSeedPhrase(
    userId: string,
    mnemonic: string
  ): Promise<void> {
    const key = `seed_phrase:${userId}`;
    await this.store(key, mnemonic);
  }

  async retrieveSeedPhrase(userId: string): Promise<string | null> {
    const key = `seed_phrase:${userId}`;
    return await this.retrieve(key);
  }

  async deleteSeedPhrase(userId: string): Promise<boolean> {
    const key = `seed_phrase:${userId}`;
    return await this.delete(key);
  }

  async storePrivateKey(
    keyId: string,
    privateKeyHex: string
  ): Promise<void> {
    const key = `private_key:${keyId}`;
    await this.store(key, privateKeyHex);
  }

  async retrievePrivateKey(keyId: string): Promise<string | null> {
    const key = `private_key:${keyId}`;
    return await this.retrieve(key);
  }

  async deletePrivateKey(keyId: string): Promise<boolean> {
    const key = `private_key:${keyId}`;
    return await this.delete(key);
  }
}
