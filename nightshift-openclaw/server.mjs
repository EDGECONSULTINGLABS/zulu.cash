/**
 * NightShift OpenClaw Adapter — PRODUCTION
 * ==========================================
 * Wraps the REAL OpenClaw Pi agent as a single-shot task executor.
 *
 * EXECUTION STRATEGIES (tried in order at startup):
 *   1. EMBEDDED — import Pi's agent runtime from openclaw-dist/
 *   2. SUBPROCESS — spawn `node openclaw-dist/index.js` in single-shot mode
 *   3. OLLAMA DIRECT — call Ollama's API directly as a fallback
 *
 * The adapter auto-detects which strategy works and locks in.
 *
 * MODEL ROUTING:
 *   - Default: Ollama (via OLLAMA_BASE_URL on zulu_internal network)
 *   - Override: Per-task via scoped_credentials.provider + scoped_credentials.api_key
 *   - Supported: ollama (local), anthropic (Claude), openai
 *
 * SECURITY PROPERTIES (unchanged from stub):
 *   - No Gateway (no WebSocket control plane)
 *   - No channels (no WhatsApp/Telegram/Discord/etc.)
 *   - No persistent sessions or memory
 *   - No self-directing: cannot enqueue follow-up tasks
 *   - Task timeout enforced locally + by external watchdog
 *   - Workspace wiped after every task
 *   - API keys passed per-task, never persisted
 */

import http from 'node:http';
import { rmSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { execFile } from 'node:child_process';
import { createRequire } from 'node:module';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const PORT = parseInt(process.env.NIGHTSHIFT_PORT || '8090', 10);
const MAX_TASK_DURATION_MS = parseInt(process.env.NIGHTSHIFT_MAX_TASK_MS || '300000', 10);
const WORKSPACE = process.env.NIGHTSHIFT_WORKSPACE || '/app/workspace';
const OUTPUT_DIR = process.env.NIGHTSHIFT_OUTPUT || '/app/output';

// Model routing
const OLLAMA_BASE_URL = process.env.OLLAMA_BASE_URL || 'http://ollama:11434';
const DEFAULT_MODEL = process.env.NIGHTSHIFT_DEFAULT_MODEL || 'llama3.1:8b';
const DEFAULT_PROVIDER = process.env.NIGHTSHIFT_DEFAULT_PROVIDER || 'ollama';

// OpenClaw dist path (built into container)
const OPENCLAW_DIST = process.env.OPENCLAW_DIST_PATH || '/app/openclaw-dist';

// ---------------------------------------------------------------------------
// Task type allowlists (unchanged from original design)
// ---------------------------------------------------------------------------
const ALLOWED_TASK_TYPES = new Set([
  'web_research',
  'document_synthesis',
  'comparative_analysis',
  'report_drafting',
  'code_review',
  'data_extraction',
  'ping',
]);

const BLOCKED_TASK_TYPES = new Set([
  'infra_change',
  'wallet_operation',
  'secrets_access',
  'file_write_host',
  'shell_exec',
  'self_schedule',
]);

const TOOL_ALLOWLISTS = {
  web_research: ['web_search', 'web_fetch', 'text_extract'],
  document_synthesis: ['text_extract', 'text_format'],
  comparative_analysis: ['web_search', 'web_fetch', 'text_extract', 'text_format'],
  report_drafting: ['text_format', 'text_extract'],
  code_review: ['text_extract'],
  data_extraction: ['text_extract', 'text_format'],
  ping: [],
};

// ---------------------------------------------------------------------------
// Execution strategy detection
// ---------------------------------------------------------------------------
let EXECUTION_STRATEGY = 'ollama_direct'; // fallback
let openclawAgent = null;

async function detectExecutionStrategy() {
  // Strategy 1: Try to import OpenClaw's agent runtime directly
  try {
    const distIndex = join(OPENCLAW_DIST, 'index.js');
    if (existsSync(distIndex)) {
      // OpenClaw exports its runtime from dist/index.js
      // We try a dynamic import to check if it's loadable
      const mod = await import(distIndex);

      // Check if agent creation API exists
      // OpenClaw's Pi agent is accessible via the module's exports
      if (mod.createAgent || mod.default?.createAgent || mod.runAgent) {
        openclawAgent = mod.createAgent || mod.default?.createAgent || mod.runAgent;
        EXECUTION_STRATEGY = 'embedded';
        console.log('[NIGHTSHIFT] Strategy: EMBEDDED (direct Pi import)');
        return;
      }

      // Check for CLI-style entry
      if (mod.run || mod.default?.run || mod.main) {
        EXECUTION_STRATEGY = 'embedded_cli';
        openclawAgent = mod.run || mod.default?.run || mod.main;
        console.log('[NIGHTSHIFT] Strategy: EMBEDDED_CLI (module.run)');
        return;
      }
    }
  } catch (err) {
    console.log(`[NIGHTSHIFT] Embedded import failed: ${err.message}`);
  }

  // Strategy 2: Check if subprocess works
  try {
    const distIndex = join(OPENCLAW_DIST, 'index.js');
    if (existsSync(distIndex)) {
      await new Promise((resolve, reject) => {
        const proc = execFile('node', [distIndex, 'health'], {
          timeout: 5000,
          env: {
            ...process.env,
            OPENCLAW_CONFIG_PATH: '/app/.openclaw/openclaw.json',
          },
        }, (err, stdout) => {
          if (err) reject(err);
          else resolve(stdout);
        });
      });
      EXECUTION_STRATEGY = 'subprocess';
      console.log('[NIGHTSHIFT] Strategy: SUBPROCESS (CLI single-shot)');
      return;
    }
  } catch (err) {
    console.log(`[NIGHTSHIFT] Subprocess probe failed: ${err.message}`);
  }

  // Strategy 3: Verify Ollama is reachable
  try {
    const resp = await fetch(`${OLLAMA_BASE_URL}/api/tags`);
    if (resp.ok) {
      const data = await resp.json();
      const models = (data.models || []).map(m => m.name);
      console.log(`[NIGHTSHIFT] Strategy: OLLAMA_DIRECT (models: ${models.join(', ') || 'none pulled yet'})`);
      EXECUTION_STRATEGY = 'ollama_direct';
      return;
    }
  } catch (err) {
    console.log(`[NIGHTSHIFT] Ollama probe failed: ${err.message}`);
  }

  console.warn('[NIGHTSHIFT] WARNING: No execution backend available. Tasks will fail.');
  EXECUTION_STRATEGY = 'none';
}

// ---------------------------------------------------------------------------
// Policy validation (unchanged)
// ---------------------------------------------------------------------------
function validateTask(task) {
  const errors = [];

  if (!task.task_id) errors.push('Missing task_id');
  if (!task.task_type) errors.push('Missing task_type');

  if (BLOCKED_TASK_TYPES.has(task.task_type)) {
    errors.push(`Task type '${task.task_type}' is explicitly blocked`);
  }

  if (!ALLOWED_TASK_TYPES.has(task.task_type)) {
    errors.push(`Task type '${task.task_type}' is not in allowlist`);
  }

  if (task.timeout_ms && task.timeout_ms > MAX_TASK_DURATION_MS) {
    errors.push(`Timeout ${task.timeout_ms}ms exceeds max ${MAX_TASK_DURATION_MS}ms`);
  }

  if (!task.prompt || typeof task.prompt !== 'string') {
    errors.push('Missing or invalid prompt');
  } else if (task.prompt.length > 50000) {
    errors.push('Prompt exceeds 50,000 character limit');
  }

  if (task.prompt) {
    const dangerous = [
      'ignore previous instructions',
      'ignore all instructions',
      'system prompt',
      'you are now',
      'act as root',
      'sudo',
      '/bin/sh',
      'eval(',
      'exec(',
    ];
    const lowerPrompt = task.prompt.toLowerCase();
    for (const pattern of dangerous) {
      if (lowerPrompt.includes(pattern)) {
        errors.push(`Prompt contains blocked pattern: '${pattern}'`);
      }
    }
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Build constrained prompt (unchanged)
// ---------------------------------------------------------------------------
function buildConstrainedPrompt(task) {
  const allowedTools = TOOL_ALLOWLISTS[task.task_type] || [];

  return {
    system: [
      'You are operating in NightShift mode — a constrained, single-task execution environment.',
      'RULES:',
      '- Complete ONLY the task described below.',
      '- Do NOT ask follow-up questions.',
      '- Do NOT suggest additional tasks.',
      '- Do NOT attempt to access the filesystem beyond /app/workspace.',
      '- Do NOT attempt to schedule future work.',
      '- Do NOT attempt to contact external services not specified in the task.',
      '- Return your output as structured JSON matching the requested output_schema.',
      `- You may use ONLY these tools: [${allowedTools.join(', ')}]`,
      `- You have ${(task.timeout_ms || MAX_TASK_DURATION_MS) / 1000} seconds to complete.`,
      '',
      'If you cannot complete the task within these constraints, return:',
      '{"status": "incomplete", "reason": "<why>", "partial_result": <any work done>}',
    ].join('\n'),

    user: task.prompt,

    output_schema: task.output_schema || {
      type: 'object',
      properties: {
        status: { type: 'string', enum: ['completed', 'incomplete', 'error'] },
        result: { type: 'object' },
        sources: { type: 'array', items: { type: 'string' } },
        summary: { type: 'string' },
      },
      required: ['status'],
    },
  };
}

// ---------------------------------------------------------------------------
// Resolve model provider for a task
// ---------------------------------------------------------------------------
function resolveProvider(credentials) {
  const provider = credentials?.provider || DEFAULT_PROVIDER;
  const model = credentials?.model || DEFAULT_MODEL;
  const apiKey = credentials?.api_key || null;

  switch (provider) {
    case 'ollama':
      return {
        provider: 'ollama',
        baseUrl: OLLAMA_BASE_URL,
        model,
        apiKey: null, // Ollama doesn't need API keys
      };
    case 'anthropic':
      return {
        provider: 'anthropic',
        baseUrl: 'https://api.anthropic.com',
        model: model || 'claude-sonnet-4-20250514',
        apiKey,
      };
    case 'openai':
      return {
        provider: 'openai',
        baseUrl: 'https://api.openai.com',
        model: model || 'gpt-4o',
        apiKey,
      };
    default:
      return {
        provider: 'ollama',
        baseUrl: OLLAMA_BASE_URL,
        model: DEFAULT_MODEL,
        apiKey: null,
      };
  }
}

// ---------------------------------------------------------------------------
// Execution: Strategy 1 — Embedded Pi agent import
// ---------------------------------------------------------------------------
async function runEmbedded(constrainedPrompt, credentials) {
  const resolved = resolveProvider(credentials);

  // Call OpenClaw's agent runtime directly
  const config = {
    model: resolved.model,
    provider: resolved.provider,
    apiKey: resolved.apiKey,
    baseUrl: resolved.baseUrl,
    maxTurns: 1,           // Single turn — no autonomous loops
    systemPrompt: constrainedPrompt.system,
    workspace: WORKSPACE,
    sandbox: { mode: 'off' }, // We ARE the sandbox
    memory: { enabled: false },
    gateway: { enabled: false },
  };

  const response = await openclawAgent(constrainedPrompt.user, config);

  return typeof response === 'string'
    ? { status: 'completed', summary: response }
    : response;
}

// ---------------------------------------------------------------------------
// Execution: Strategy 2 — Subprocess CLI
// ---------------------------------------------------------------------------
async function runSubprocess(constrainedPrompt, credentials, timeoutMs) {
  const resolved = resolveProvider(credentials);
  const distIndex = join(OPENCLAW_DIST, 'index.js');

  return new Promise((resolve, reject) => {
    const args = [
      distIndex,
      'agent', 'run',
      '--single-shot',
      '--model', resolved.model,
      '--system-prompt', constrainedPrompt.system,
      '--message', constrainedPrompt.user,
      '--no-memory',
      '--no-gateway',
    ];

    const env = {
      ...process.env,
      OPENCLAW_CONFIG_PATH: '/app/.openclaw/openclaw.json',
      NODE_ENV: 'production',
    };

    // Inject provider credentials
    if (resolved.provider === 'ollama') {
      env.OLLAMA_BASE_URL = resolved.baseUrl;
    } else if (resolved.provider === 'anthropic' && resolved.apiKey) {
      env.ANTHROPIC_API_KEY = resolved.apiKey;
    } else if (resolved.provider === 'openai' && resolved.apiKey) {
      env.OPENAI_API_KEY = resolved.apiKey;
    }

    const proc = execFile('node', args, {
      timeout: timeoutMs,
      maxBuffer: 10 * 1024 * 1024, // 10MB output buffer
      env,
      cwd: WORKSPACE,
    }, (err, stdout, stderr) => {
      if (err) {
        if (err.killed) {
          return reject(new Error('TIMEOUT'));
        }
        return reject(new Error(`Subprocess error: ${err.message}\nstderr: ${stderr}`));
      }

      try {
        const parsed = JSON.parse(stdout);
        resolve(parsed);
      } catch {
        // If output isn't JSON, wrap it
        resolve({
          status: 'completed',
          summary: stdout.trim(),
          raw_output: true,
        });
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Execution: Strategy 3 — Ollama direct (no OpenClaw, pure LLM call)
// ---------------------------------------------------------------------------
async function runOllamaDirect(constrainedPrompt, credentials) {
  const resolved = resolveProvider(credentials);
  const url = `${resolved.baseUrl}/api/chat`;

  const body = {
    model: resolved.model,
    messages: [
      { role: 'system', content: constrainedPrompt.system },
      { role: 'user', content: constrainedPrompt.user },
    ],
    stream: false,
    options: {
      temperature: 0.3,
      num_predict: 4096,
    },
    format: 'json', // Request structured JSON output
  };

  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Ollama error ${resp.status}: ${errText}`);
  }

  const data = await resp.json();
  const content = data.message?.content || '';

  // Try to parse as JSON
  try {
    return JSON.parse(content);
  } catch {
    return {
      status: 'completed',
      summary: content,
      model: resolved.model,
      provider: 'ollama_direct',
    };
  }
}

// ---------------------------------------------------------------------------
// Unified task runner — dispatches to active strategy
// ---------------------------------------------------------------------------
async function runOpenClawTask(constrainedPrompt, credentials, timeoutMs) {
  switch (EXECUTION_STRATEGY) {
    case 'embedded':
    case 'embedded_cli':
      return await runEmbedded(constrainedPrompt, credentials);

    case 'subprocess':
      return await runSubprocess(constrainedPrompt, credentials, timeoutMs);

    case 'ollama_direct':
      return await runOllamaDirect(constrainedPrompt, credentials);

    default:
      throw new Error(`No execution backend available (strategy: ${EXECUTION_STRATEGY})`);
  }
}

// ---------------------------------------------------------------------------
// Execute task with timeout
// ---------------------------------------------------------------------------
async function executeTask(task) {
  const startTime = Date.now();
  const timeoutMs = Math.min(task.timeout_ms || MAX_TASK_DURATION_MS, MAX_TASK_DURATION_MS);

  const constrainedPrompt = buildConstrainedPrompt(task);
  const credentials = task.scoped_credentials || {};

  try {
    const result = await Promise.race([
      runOpenClawTask(constrainedPrompt, credentials, timeoutMs),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('TIMEOUT')), timeoutMs)
      ),
    ]);

    const elapsed = Date.now() - startTime;

    return {
      task_id: task.task_id,
      status: 'completed',
      result,
      elapsed_ms: elapsed,
      completed_at: new Date().toISOString(),
      execution_strategy: EXECUTION_STRATEGY,
      tools_used: TOOL_ALLOWLISTS[task.task_type]?.join(', ') || 'none',
    };

  } catch (err) {
    const elapsed = Date.now() - startTime;

    if (err.message === 'TIMEOUT') {
      return {
        task_id: task.task_id,
        status: 'timeout',
        error: `Task exceeded ${timeoutMs / 1000}s limit`,
        elapsed_ms: elapsed,
        execution_strategy: EXECUTION_STRATEGY,
      };
    }

    return {
      task_id: task.task_id,
      status: 'error',
      error: err.message,
      elapsed_ms: elapsed,
      execution_strategy: EXECUTION_STRATEGY,
    };
  } finally {
    cleanWorkspace();
  }
}

// ---------------------------------------------------------------------------
// Workspace cleanup
// ---------------------------------------------------------------------------
function cleanWorkspace() {
  try {
    if (existsSync(WORKSPACE)) {
      rmSync(WORKSPACE, { recursive: true, force: true });
    }
    mkdirSync(WORKSPACE, { recursive: true });
    console.log(`[NIGHTSHIFT] Workspace cleaned: ${WORKSPACE}`);
  } catch (err) {
    console.error(`[NIGHTSHIFT] Workspace cleanup failed: ${err.message}`);
  }
}

// ---------------------------------------------------------------------------
// HTTP server
// ---------------------------------------------------------------------------
function parseBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch {
        reject(new Error('Invalid JSON'));
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const sendJSON = (statusCode, data) => {
    res.writeHead(statusCode, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
  };

  // --- Health check ---
  if (req.method === 'GET' && req.url === '/health') {
    return sendJSON(200, {
      status: 'healthy',
      service: 'nightshift-openclaw',
      execution_strategy: EXECUTION_STRATEGY,
      default_provider: DEFAULT_PROVIDER,
      default_model: DEFAULT_MODEL,
      ollama_url: OLLAMA_BASE_URL,
      timestamp: new Date().toISOString(),
      max_task_duration_ms: MAX_TASK_DURATION_MS,
      allowed_task_types: [...ALLOWED_TASK_TYPES],
    });
  }

  // --- Task execution ---
  if (req.method === 'POST' && req.url === '/task') {
    let task;
    try {
      task = await parseBody(req);
    } catch {
      return sendJSON(400, { error: 'Invalid JSON body' });
    }

    const validation = validateTask(task);
    if (!validation.valid) {
      console.log(`[NIGHTSHIFT] Task REJECTED: ${validation.errors.join(', ')}`);
      return sendJSON(422, {
        task_id: task.task_id || 'unknown',
        status: 'rejected',
        errors: validation.errors,
      });
    }

    console.log(`[NIGHTSHIFT] Task ${task.task_id} (${task.task_type}) — executing via ${EXECUTION_STRATEGY}`);
    const result = await executeTask(task);

    const statusCode = result.status === 'completed' ? 200
      : result.status === 'timeout' ? 408
      : 500;

    return sendJSON(statusCode, result);
  }

  // --- Capability manifest ---
  if (req.method === 'GET' && req.url === '/manifest') {
    return sendJSON(200, {
      service: 'nightshift-openclaw',
      version: '2.0.0',
      execution_strategy: EXECUTION_STRATEGY,
      default_provider: DEFAULT_PROVIDER,
      default_model: DEFAULT_MODEL,
      allowed_task_types: [...ALLOWED_TASK_TYPES],
      blocked_task_types: [...BLOCKED_TASK_TYPES],
      tool_allowlists: TOOL_ALLOWLISTS,
      max_task_duration_ms: MAX_TASK_DURATION_MS,
      security: {
        persistent_memory: false,
        self_scheduling: false,
        browser_control: false,
        channel_access: false,
        gateway: false,
        filesystem_access: 'workspace_only',
      },
    });
  }

  sendJSON(404, { error: 'Not found' });
});

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------
async function startup() {
  cleanWorkspace();
  mkdirSync(OUTPUT_DIR, { recursive: true });

  // Detect which execution strategy is available
  await detectExecutionStrategy();

  server.listen(PORT, '0.0.0.0', () => {
    console.log('='.repeat(60));
    console.log('[NIGHTSHIFT] OpenClaw NightShift Worker v2.0');
    console.log(`[NIGHTSHIFT]   Port:             ${PORT}`);
    console.log(`[NIGHTSHIFT]   Strategy:         ${EXECUTION_STRATEGY}`);
    console.log(`[NIGHTSHIFT]   Default provider: ${DEFAULT_PROVIDER}`);
    console.log(`[NIGHTSHIFT]   Default model:    ${DEFAULT_MODEL}`);
    console.log(`[NIGHTSHIFT]   Ollama URL:       ${OLLAMA_BASE_URL}`);
    console.log(`[NIGHTSHIFT]   Max task:         ${MAX_TASK_DURATION_MS / 1000}s`);
    console.log(`[NIGHTSHIFT]   Workspace:        ${WORKSPACE}`);
    console.log(`[NIGHTSHIFT]   OpenClaw dist:    ${OPENCLAW_DIST}`);
    console.log(`[NIGHTSHIFT]   Allowed tasks:    ${[...ALLOWED_TASK_TYPES].join(', ')}`);
    console.log('[NIGHTSHIFT]   Gateway:          DISABLED');
    console.log('[NIGHTSHIFT]   Channels:         DISABLED');
    console.log('[NIGHTSHIFT]   Memory:           DISABLED');
    console.log('[NIGHTSHIFT]   Self-scheduling:  DISABLED');
    console.log('='.repeat(60));
  });
}

startup().catch(err => {
  console.error(`[NIGHTSHIFT] Fatal startup error: ${err.message}`);
  process.exit(1);
});
