#!/usr/bin/env node
// Configure the running desktop through T3's API, without opening its database.
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const mode = process.argv[2] ?? '--status';
if (!['--apply', '--remove', '--status'].includes(mode) || process.argv.length > 3) {
  throw new Error('Usage: node scripts/configure-npu-t3.mjs [--apply|--remove|--status]');
}
const base = process.env.T3CODE_HOME ?? join(homedir(), '.t3');
const cli = process.env.T3CODE_CLI_PATH ?? join(homedir(), '.t3/bin/t3');
const instanceId = 'laptop_npu';
// OpenCode 1.18 uses provider/npm/options; the v2 providers/package/settings shape is ignored.
// FLM Qwen3.5 maps reasoning none to off and low/medium/high equally to on.
const config = JSON.parse(readFileSync(new URL('../home/.config/opencode/laptop-npu.json', import.meta.url), 'utf8'));
const instance = {
  driver: 'opencode',
  displayName: 'Laptop NPU',
  enabled: true,
  environment: [
    ['OPENCODE_CONFIG_CONTENT', JSON.stringify(config)],
    ['OPENCODE_DISABLE_MODELS_FETCH', 'true'],
    ['OPENCODE_DISABLE_AUTOUPDATE', 'true'],
    ['OPENCODE_DISABLE_LSP_DOWNLOAD', 'true'],
    ['OPENCODE_DISABLE_DEFAULT_PLUGINS', 'true'],
    ['OPENCODE_DISABLE_PROJECT_CONFIG', 'true'],
    ['OPENCODE_DISABLE_SHARE', 'true'],
  ].map(([name, value]) => ({ name, value, sensitive: false })),
  config: { binaryPath: join(homedir(), '.opencode/bin/opencode'), customModels: [] },
};
const runtime = JSON.parse(readFileSync(join(base, 'userdata/server-runtime.json'), 'utf8'));
const origin = new URL(runtime.origin);
if (!['127.0.0.1', 'localhost', '[::1]'].includes(origin.hostname)) {
  throw new Error('This helper only configures the local T3 server.');
}
const descriptorResponse = await fetch(new URL('/.well-known/t3/environment', origin), { signal: AbortSignal.timeout(10000) });
if (!descriptorResponse.ok) throw new Error(`T3 descriptor returned HTTP ${descriptorResponse.status}`);
const descriptor = await descriptorResponse.json();
const session = JSON.parse(execFileSync(cli, [
  'auth', 'session', 'issue', '--base-dir', base, '--ttl', '5m', '--label', 'laptop-npu-provider-setup',
  '--scope', 'orchestration:read', '--scope', 'settings:write', '--scope', 'providers:manage', '--json',
], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }));
let socket;
try {
  const ticketResponse = await fetch(new URL('/api/auth/websocket-ticket', origin), {
    method: 'POST', headers: { authorization: `Bearer ${session.token}` }, signal: AbortSignal.timeout(10000),
  });
  if (!ticketResponse.ok) throw new Error(`T3 ticket returned HTTP ${ticketResponse.status}`);
  const { ticket } = await ticketResponse.json();
  const socketUrl = new URL('/ws', origin);
  socketUrl.protocol = origin.protocol === 'https:' ? 'wss:' : 'ws:';
  socketUrl.searchParams.set('wsTicket', ticket);
  socketUrl.searchParams.set('orchestrationProtocol', String(descriptor.orchestrationProtocolVersion ?? 1));
  socket = new WebSocket(socketUrl);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Timed out connecting to T3')), 10000);
    socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
    socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('T3 WebSocket connection failed')); }, { once: true });
  });
  let requestId = 0;
  function rpc(tag, payload) {
    const id = String(++requestId);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => finish(new Error(`T3 ${tag} timed out`)), 120000);
      function finish(error, value) {
        clearTimeout(timer);
        socket.removeEventListener('message', onMessage);
        socket.removeEventListener('close', onClose);
        error ? reject(error) : resolve(value);
      }
      function onClose() { finish(new Error(`T3 closed during ${tag}`)); }
      function onMessage(event) {
        const message = JSON.parse(event.data);
        if (message._tag !== 'Exit' || message.requestId !== id) return;
        if (message.exit._tag === 'Success') finish(null, message.exit.value);
        else finish(new Error(`T3 ${tag} failed: ${JSON.stringify(message.exit.cause)}`));
      }
      socket.addEventListener('message', onMessage);
      socket.addEventListener('close', onClose, { once: true });
      socket.send(JSON.stringify({ _tag: 'Request', id, tag, payload, headers: [] }));
    });
  }
  let server = await rpc('server.getConfig', {});
  const existing = server.settings.providerInstances[instanceId];
  if (existing && (existing.driver !== instance.driver || ![instance.displayName, 'Laptop NPU · offline'].includes(existing.displayName))) {
    throw new Error(`Refusing to replace unrelated provider ${instanceId}`);
  }
  if (mode === '--remove' && existing) {
    await rpc('server.updateSettings', { patch: {}, providerInstanceMutation: { operation: 'remove', instanceId } });
  } else if (mode === '--apply') {
    await rpc('server.updateSettings', { patch: {}, providerInstanceMutation: {
      operation: existing ? 'upsert' : 'create', instanceId, instance,
    } });
    await rpc('server.refreshProviders', { instanceId, refreshModels: true });
  }
  server = await rpc('server.getConfig', {});
  const saved = server.settings.providerInstances[instanceId];
  const provider = server.providers.find(p => p.instanceId === instanceId);
  console.log(JSON.stringify({ instanceId, configured: Boolean(saved), enabled: saved?.enabled,
    provider: provider ? { installed: provider.installed, status: provider.status, auth: provider.auth,
      models: provider.models, issues: provider.issues } : null }, null, 2));
  if (mode === '--apply') {
    const expected = Object.keys(config.provider.npu.models).map(model => `npu/${model}`);
    const actual = new Set(provider?.models?.map(model => model.slug));
    if (!saved || !provider?.installed || provider.status !== 'ready' || expected.some(model => !actual.has(model))) {
      throw new Error('T3 retained the configuration but could not discover both local models. Check OpenCode version and provider status.');
    }
  }
  if (mode === '--remove' && saved) throw new Error('T3 did not remove the NPU provider');
} finally {
  socket?.close();
  execFileSync(cli, ['auth', 'session', 'revoke', '--base-dir', base, session.sessionId], {
    encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
  });
}
