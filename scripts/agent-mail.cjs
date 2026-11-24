#!/usr/bin/env node
// Use the existing bridge's local discovery; never copy or print its token.
const path = require('node:path');
const fs = require('node:fs');
const centralConnection = path.join(process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`, 'agent-mail/thunderbird-mcp/connection.json');
if (!process.env.THUNDERBIRD_MCP_CONNECTION_FILE && fs.existsSync(centralConnection)) {
  process.env.THUNDERBIRD_MCP_CONNECTION_FILE = centralConnection;
}
process.env.THUNDERBIRD_MCP_NO_AUTOSTART = '1';
const bridge = require(process.env.THUNDERBIRD_BRIDGE_PATH || path.join(require('node:os').homedir(), 'Projects/thunderbird-mcp/mcp-bridge.cjs'));

async function call(name, args = {}) {
  const connection = bridge.readConnectionInfo();
  if (!connection) throw new Error('Thunderbird is unavailable; start its existing profile in the agent desktop.');
  const response = await fetch(`http://127.0.0.1:${connection.port}/`, {
    method: 'POST', signal: AbortSignal.timeout(45000),
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${connection.token}` },
    body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: name === 'tools/list' ? name : 'tools/call',
      params: name === 'tools/list' ? {} : { name, arguments: args } }),
  });
  if (!response.ok) throw new Error(`Thunderbird returned HTTP ${response.status}.`);
  const rpc = await response.json();
  if (rpc.error || rpc.result?.isError) throw new Error('Thunderbird rejected the operation; check its tool schema and account state.');
  if (name === 'tools/list') return rpc.result.tools;
  const text = rpc.result?.content?.filter(block => block.type === 'text').map(block => block.text).join('\n');
  try { return JSON.parse(text); } catch { return { text }; }
}

module.exports = { call };
if (require.main === module) {
  const [name, raw = '{}'] = process.argv.slice(2);
  if (!name) { console.error('Usage: agent-mail.cjs TOOL_NAME [JSON_ARGUMENTS]'); process.exitCode = 2; }
  else Promise.resolve().then(() => call(name, JSON.parse(raw))).then(result => {
    console.log(JSON.stringify(result, null, 2));
  }).catch(error => { console.error(error.message); process.exitCode = 1; });
}
