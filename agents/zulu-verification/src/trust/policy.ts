/**
 * Trust Policy Engine
 */

import {
  TrustPolicy,
  TrustConfig,
  KeyMetadata,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { VerificationDatabase } from '../storage/database';

export class TrustPolicyEngine {
  private config: TrustConfig;
  private db: VerificationDatabase;

  constructor(config: TrustConfig, db: VerificationDatabase) {
    this.config = config;
    this.db = db;
  }

  /**
   * Verify if a public key is trusted according to policy
   */
  async verifyKeyTrust(pubkeyHex: string): Promise<{
    trusted: boolean;
    reason?: string;
    warning?: string;
  }> {
    // Check if key is revoked
    if (this.config.revokedKeys.includes(pubkeyHex)) {
      return {
        trusted: false,
        reason: 'Key has been revoked',
      };
    }

    // Get key metadata from database
    const keyMetadata = this.db.getKeyMetadata(pubkeyHex);

    if (keyMetadata) {
      // Check expiration
      const now = new Date();
      const expiresAt = new Date(keyMetadata.expires_at);

      if (expiresAt < now) {
        return {
          trusted: false,
          reason: `Key expired on ${keyMetadata.expires_at}`,
        };
      }

      // Check for expiry warning
      const warningDate = new Date(expiresAt);
      warningDate.setDate(warningDate.getDate() - this.config.expiryWarningDays);

      let warning: string | undefined;
      if (now >= warningDate) {
        const daysUntilExpiry = Math.ceil(
          (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
        );
        warning = `Key expires in ${daysUntilExpiry} days`;
      }

      // Check database revocation status
      if (keyMetadata.revoked) {
        return {
          trusted: false,
          reason: `Key revoked on ${keyMetadata.revoked_at}`,
        };
      }

      // Apply trust policy
      switch (this.config.policy) {
        case TrustPolicy.STRICT:
          if (this.config.teamKeyring.includes(pubkeyHex)) {
            return { trusted: true, warning };
          }
          return {
            trusted: false,
            reason: 'STRICT policy: Only team keyring trusted',
          };

        case TrustPolicy.WARN:
          if (
            this.config.teamKeyring.includes(pubkeyHex) ||
            this.config.userApprovedKeys.includes(pubkeyHex)
          ) {
            return { trusted: true, warning };
          }
          return {
            trusted: false,
            reason: 'WARN policy: Key not in team keyring or user-approved list',
            warning: 'Consider approving this key if you trust the publisher',
          };

        case TrustPolicy.BEST_EFFORT:
          return {
            trusted: true,
            warning: warning || 'BEST_EFFORT policy: All keys accepted (dev mode)',
          };
      }
    }

    // Key not in database - apply policy for unknown keys
    switch (this.config.policy) {
      case TrustPolicy.STRICT:
        return {
          trusted: false,
          reason: 'Unknown key not trusted in STRICT mode',
        };

      case TrustPolicy.WARN:
        return {
          trusted: false,
          reason: 'Unknown key requires approval',
          warning: 'Add key to user-approved list to proceed',
        };

      case TrustPolicy.BEST_EFFORT:
        return {
          trusted: true,
          warning: 'Unknown key accepted in BEST_EFFORT mode (dev only)',
        };
    }
  }

  /**
   * Add key to user-approved list
   */
  async approveKey(pubkeyHex: string): Promise<void> {
    if (!this.config.userApprovedKeys.includes(pubkeyHex)) {
      this.config.userApprovedKeys.push(pubkeyHex);
    }

    // Create/update key metadata if not exists
    const existing = this.db.getKeyMetadata(pubkeyHex);
    if (!existing) {
      const now = new Date();
      const expiresAt = new Date(now);
      expiresAt.setMonth(expiresAt.getMonth() + 6); // 6 months for user keys

      this.db.insertKeyMetadata({
        key_id: pubkeyHex,
        key_type: 'user',
        pubkey: Buffer.from(pubkeyHex, 'hex'),
        created_at: now.toISOString(),
        expires_at: expiresAt.toISOString(),
        revoked: false,
        metadata: JSON.stringify({ approvedAt: now.toISOString() }),
      });
    }
  }

  /**
   * Revoke key
   */
  async revokeKey(pubkeyHex: string, reason: string): Promise<void> {
    if (!this.config.revokedKeys.includes(pubkeyHex)) {
      this.config.revokedKeys.push(pubkeyHex);
    }

    // Mark as revoked in database
    this.db.revokeKey(pubkeyHex);

    // Remove from user-approved list
    const index = this.config.userApprovedKeys.indexOf(pubkeyHex);
    if (index > -1) {
      this.config.userApprovedKeys.splice(index, 1);
    }
  }

  /**
   * Get keys expiring soon
   */
  async getExpiringKeys(daysUntilExpiry?: number): Promise<KeyMetadata[]> {
    const days = daysUntilExpiry || this.config.expiryWarningDays;
    const rows = this.db.getExpiringKeys(days);

    return rows.map(row => ({
      keyId: row.key_id,
      type: row.key_type as 'team' | 'user',
      createdAt: row.created_at,
      expiresAt: row.expires_at,
      revoked: Boolean(row.revoked),
      revokedAt: row.revoked_at,
    }));
  }

  /**
   * Update trust policy
   */
  setPolicy(policy: TrustPolicy): void {
    this.config.policy = policy;
  }

  /**
   * Get current policy
   */
  getPolicy(): TrustPolicy {
    return this.config.policy;
  }

  /**
   * Enforce key expiration on verification
   */
  async enforceKeyExpiration(pubkeyHex: string): Promise<void> {
    const keyMetadata = this.db.getKeyMetadata(pubkeyHex);

    if (!keyMetadata) {
      if (this.config.policy === TrustPolicy.STRICT) {
        throw new VerificationError(
          VerificationErrorCode.UNTRUSTED_SIGNER_ERROR,
          'Unknown key not trusted in STRICT mode'
        );
      }
      return;
    }

    const now = new Date();
    const expiresAt = new Date(keyMetadata.expires_at);

    if (expiresAt < now) {
      throw new VerificationError(
        VerificationErrorCode.KEY_EXPIRED_ERROR,
        `Key ${pubkeyHex} expired on ${keyMetadata.expires_at}`
      );
    }

    if (keyMetadata.revoked) {
      throw new VerificationError(
        VerificationErrorCode.KEY_REVOKED_ERROR,
        `Key ${pubkeyHex} was revoked on ${keyMetadata.revoked_at}`
      );
    }
  }

  /**
   * Initialize team keyring
   */
  async initializeTeamKeyring(teamKeys: Array<{
    pubkey: string;
    expiresAt: string;
  }>): Promise<void> {
    const now = new Date().toISOString();

    for (const key of teamKeys) {
      const existing = this.db.getKeyMetadata(key.pubkey);
      if (!existing) {
        this.db.insertKeyMetadata({
          key_id: key.pubkey,
          key_type: 'team',
          pubkey: Buffer.from(key.pubkey, 'hex'),
          created_at: now,
          expires_at: key.expiresAt,
          revoked: false,
          metadata: JSON.stringify({ team: true }),
        });
      }

      if (!this.config.teamKeyring.includes(key.pubkey)) {
        this.config.teamKeyring.push(key.pubkey);
      }
    }
  }

  /**
   * Export trust config
   */
  exportConfig(): TrustConfig {
    return { ...this.config };
  }
}

/**
 * Create default trust config
 */
export function createDefaultTrustConfig(): TrustConfig {
  return {
    policy: TrustPolicy.STRICT,
    teamKeyring: [],
    userApprovedKeys: [],
    revokedKeys: [],
    expiryWarningDays: 30,
  };
}
