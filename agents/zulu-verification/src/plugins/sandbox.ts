/**
 * Plugin Sandbox with Permissions (Phase 3)
 */

import {
  PluginManifest,
  PluginPermissions,
  VerificationError,
  VerificationErrorCode,
} from '../types';
import { verifySignature } from '../crypto/ed25519';
import * as semver from 'semver';

export interface PluginContext {
  pluginId: string;
  permissions: PluginPermissions;
  resourceUsage: {
    memoryMb: number;
    cpuSeconds: number;
  };
}

/**
 * Verify plugin manifest and permissions
 */
export async function verifyPluginManifest(
  manifest: PluginManifest
): Promise<boolean> {
  try {
    const { signature, ...manifestWithoutSig } = manifest;
    const manifestData = Buffer.from(JSON.stringify(manifestWithoutSig), 'utf8');
    const signatureBuffer = Buffer.from(signature, 'hex');
    const pubkeyBuffer = Buffer.from(manifest.publisher.pubkey, 'hex');

    return await verifySignature(manifestData, signatureBuffer, pubkeyBuffer);
  } catch (error) {
    return false;
  }
}

/**
 * Check if permission is granted
 */
export function checkPermission(
  context: PluginContext,
  permission: keyof PluginPermissions,
  resource?: string
): boolean {
  const perms = context.permissions[permission];

  if (!perms) return false;

  switch (permission) {
    case 'filesystem': {
      const fsPerms = perms as { paths: string[]; readonly: boolean };
      if (resource && fsPerms.paths) {
        // Check if resource path is within allowed paths
        return fsPerms.paths.some((allowed: string) => resource.startsWith(allowed));
      }
      return Boolean(fsPerms.paths && fsPerms.paths.length > 0);
    }

    case 'network': {
      const netPerms = perms as { allowedDomains: string[]; rateLimit?: { requestsPerMinute: number } };
      if (resource && netPerms.allowedDomains) {
        return netPerms.allowedDomains.includes(resource);
      }
      return Boolean(netPerms.allowedDomains && netPerms.allowedDomains.length > 0);
    }

    case 'vault': {
      const vaultPerms = perms as { tables: string[]; operations: ('read' | 'write' | 'delete')[] };
      if (resource && vaultPerms.tables) {
        return vaultPerms.tables.includes(resource);
      }
      return Boolean(vaultPerms.tables && vaultPerms.tables.length > 0);
    }

    case 'compute': {
      const computePerms = perms as { maxMemoryMb?: number; maxCpuSeconds?: number };
      return Boolean(computePerms.maxMemoryMb || computePerms.maxCpuSeconds);
    }

    default:
      return false;
  }
}

/**
 * Enforce compute limits
 */
export function enforceComputeLimits(context: PluginContext): void {
  const limits = context.permissions.compute;
  if (!limits) return;

  if (
    limits.maxMemoryMb &&
    context.resourceUsage.memoryMb > limits.maxMemoryMb
  ) {
    throw new VerificationError(
      VerificationErrorCode.STORAGE_ERROR,
      `Plugin ${context.pluginId} exceeded memory limit: ${limits.maxMemoryMb}MB`
    );
  }

  if (
    limits.maxCpuSeconds &&
    context.resourceUsage.cpuSeconds > limits.maxCpuSeconds
  ) {
    throw new VerificationError(
      VerificationErrorCode.STORAGE_ERROR,
      `Plugin ${context.pluginId} exceeded CPU limit: ${limits.maxCpuSeconds}s`
    );
  }
}

/**
 * Verify plugin update with semantic versioning
 */
export function verifyPluginUpdate(
  currentVersion: string,
  newVersion: string,
  allowDowngrade = false
): {
  valid: boolean;
  reason?: string;
} {
  if (!semver.valid(currentVersion) || !semver.valid(newVersion)) {
    return {
      valid: false,
      reason: 'Invalid semantic version format',
    };
  }

  const comparison = semver.compare(newVersion, currentVersion);

  if (comparison < 0 && !allowDowngrade) {
    return {
      valid: false,
      reason: 'Cannot downgrade plugin version',
    };
  }

  if (comparison === 0) {
    return {
      valid: false,
      reason: 'Version unchanged',
    };
  }

  // Check for breaking changes
  const currentMajor = semver.major(currentVersion);
  const newMajor = semver.major(newVersion);

  if (newMajor > currentMajor) {
    return {
      valid: true,
      reason: 'Major version update (may contain breaking changes)',
    };
  }

  return { valid: true };
}

/**
 * Create plugin sandbox context
 */
export function createPluginContext(
  manifest: PluginManifest
): PluginContext {
  return {
    pluginId: manifest.pluginId,
    permissions: manifest.permissions,
    resourceUsage: {
      memoryMb: 0,
      cpuSeconds: 0,
    },
  };
}

/**
 * Request permission with user prompt
 */
export interface PermissionRequest {
  pluginId: string;
  permission: keyof PluginPermissions;
  resource?: string;
  reason?: string;
}

export interface PermissionDecision {
  granted: boolean;
  remember: boolean; // "Remember this decision" option
}

/**
 * Format permission request for UI
 */
export function formatPermissionRequest(request: PermissionRequest): string {
  const { pluginId, permission, resource } = request;

  switch (permission) {
    case 'filesystem':
      return `Plugin "${pluginId}" requests filesystem access to: ${resource || 'specified paths'}`;

    case 'network':
      return `Plugin "${pluginId}" requests network access to: ${resource || 'allowed domains'}`;

    case 'vault':
      return `Plugin "${pluginId}" requests vault access to table: ${resource || 'specified tables'}`;

    case 'compute':
      return `Plugin "${pluginId}" requests compute resources`;

    default:
      return `Plugin "${pluginId}" requests ${permission} permission`;
  }
}

/**
 * Validate plugin permissions are not overly broad
 */
export function validatePermissions(permissions: PluginPermissions): {
  valid: boolean;
  warnings: string[];
} {
  const warnings: string[] = [];

  // Check filesystem permissions
  if (permissions.filesystem) {
    if (
      permissions.filesystem.paths.some(
        p => p === '/' || p === 'C:\\' || p === '*'
      )
    ) {
      warnings.push('Filesystem permission too broad (root access requested)');
    }

    if (!permissions.filesystem.readonly) {
      warnings.push('Plugin has write access to filesystem');
    }
  }

  // Check network permissions
  if (permissions.network) {
    if (
      permissions.network.allowedDomains.includes('*') ||
      permissions.network.allowedDomains.length === 0
    ) {
      warnings.push('Network permission too broad (all domains allowed)');
    }
  }

  // Check vault permissions
  if (permissions.vault) {
    if (permissions.vault.tables.includes('*')) {
      warnings.push('Vault permission too broad (all tables accessible)');
    }

    if (permissions.vault.operations.includes('delete')) {
      warnings.push('Plugin can delete vault data');
    }
  }

  // Check compute limits
  if (permissions.compute) {
    if (
      !permissions.compute.maxMemoryMb ||
      permissions.compute.maxMemoryMb > 512
    ) {
      warnings.push('High memory limit requested (>512MB)');
    }

    if (
      !permissions.compute.maxCpuSeconds ||
      permissions.compute.maxCpuSeconds > 60
    ) {
      warnings.push('High CPU time limit requested (>60s)');
    }
  }

  return {
    valid: warnings.length === 0,
    warnings,
  };
}
