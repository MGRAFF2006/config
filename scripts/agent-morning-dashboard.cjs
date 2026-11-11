#!/usr/bin/env node
// Publish an explicit projection, never a filesystem browser or raw collector API.
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const { photosStatus, localHealth } = require('./agent-life-status.cjs');
const state = process.env.MORNING_STATE_DIR || path.join(os.homedir(), '.local/state/agent-life');
const assets = path.join(__dirname, '../web/morning');
const iso = () => new Date().toISOString();
function sanitizeReport(text) {
  return text.replace(/https?:\/\/[^\s<>"')\]]+/g, raw => {
    try {
      const url = new URL(raw);
      if (/auth|token|login|verify|unsubscribe|confirm/i.test(url.pathname)) return '[private link omitted]';
      for (const name of [...url.searchParams.keys()]) if (!['id', 'd'].includes(name) || !/^\d+$/.test(url.searchParams.get(name))) url.searchParams.delete(name);
      url.hash = '';
      return url.toString();
    } catch { return '[link omitted]'; }
  }).replace(/\b(?:Bearer|ApiKey)\s+\S+/gi, '[credential omitted]');
}
async function publish() {
  const reportPath = path.join(state, 'latest-brief.md');
  const [report, stat, snapshot] = await Promise.all([fs.readFile(reportPath, 'utf8'), fs.stat(reportPath), fs.readFile(path.join(state, 'snapshot.json'), 'utf8').then(JSON.parse)]);
  if (!report.trim() || report.length > 150000) throw new Error('Brief is empty or too large');
  const sources = Object.entries(snapshot.sources || {}).map(([name, source]) => ({ name, state: source.state, collectedAt: source.collectedAt || null, attemptedAt: source.attemptedAt || null }));
  const data = { publishedAt: iso(), report: sanitizeReport(report), reportUpdatedAt: stat.mtime.toISOString(), sourceCollectedAt: snapshot.collectedAt, date: snapshot.date, timeZone: 'Europe/Berlin', sources,
    garmin: snapshot.sources?.garmin || { state: 'not_connected' }, photos: snapshot.sources?.photoMigration?.data || null };
  // Garmin collector already projects only allowlisted health fields, without profile IDs or tokens.
  const target = path.join(state, 'dashboard.json');
  await fs.writeFile(`${target}.pending`, JSON.stringify(data), { mode: 0o600 });
  await fs.rename(`${target}.pending`, target);
}
function createServer() {
  return http.createServer(async (req, res) => {
    const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'", 'X-Frame-Options': 'DENY' };
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405, headers); return res.end(); }
    // Tailscale Serve removes /morning; support both for direct local verification.
    const route = req.url.split('?')[0].replace(/^\/morning(?=\/|$)/, '') || '/';
    const files = { '/': ['index.html', 'text/html; charset=utf-8'], '/index.html': ['index.html', 'text/html; charset=utf-8'], '/app.js': ['app.js', 'text/javascript; charset=utf-8'], '/style.css': ['style.css', 'text/css; charset=utf-8'] };
    try {
      let body, type;
      if (route === '/data') {
        let published;
        try { published = JSON.parse(await fs.readFile(path.join(state, 'dashboard.json'), 'utf8')); }
        catch { published = { report: null, error: 'No published brief available. Check the morning brief service on homelab-dev.' }; }
        const health = await localHealth();
        body = JSON.stringify({ ...published, health, servedAt: iso() }); type = 'application/json; charset=utf-8';
      } else if (files[route]) { const [file, mime] = files[route]; body = await fs.readFile(path.join(assets, file)); type = mime; }
      else { res.writeHead(404, headers); return res.end('Not found'); }
      res.writeHead(200, { ...headers, 'Content-Type': type }); res.end(req.method === 'HEAD' ? undefined : body);
    } catch { res.writeHead(503, headers); res.end('Dashboard temporarily unavailable'); }
  });
}
module.exports = { publish, createServer, sanitizeReport };
if (require.main === module) {
  process.umask(0o077);
  if (process.argv[2] === 'publish') publish().catch(() => { console.error('Dashboard publication failed; previous published brief retained.'); process.exitCode = 1; });
  else createServer().listen(Number(process.env.MORNING_PORT || 8787), '127.0.0.1', () => console.log('Morning dashboard listening on loopback.'));
}
