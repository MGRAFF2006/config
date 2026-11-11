const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const execFile = require('node:util').promisify(require('node:child_process').execFile);
async function photosStatus() {
  const raw = JSON.parse(await fs.readFile(path.join(os.homedir(), '.local/state/agent-life/google-photos-migration.json'), 'utf8'));
  // Allowlist only. Never publish account, paths, manifests or cleanup candidates.
  return { updatedAt: raw.updated_at || null, backupVerified: raw.verification?.backup_verified === true, verifiedAt: raw.verification?.verified_at || null,
    cleanupPaused: raw.cloud_cleanup?.state === 'paused_user_cannot_approve_now',
    cloudMediaChanged: raw.verification?.cloud_media_changed === true,
    subscriptionChanged: raw.verification?.google_one_changed === true,
    note: 'Checkpoint only. Cloud cleanup needs Mathis’s approval; do not resume automatically. Google One remains active when unchanged.' };
}
async function localHealth() {
  const services = {};
  for (const unit of ['agent-mail.service', 'agent-morning-brief.service', 'agent-morning-brief.timer', 'agent-morning-dashboard.service']) {
    try {
      const { stdout } = await execFile('systemctl', ['--user', 'show', unit, '--property=ActiveState,SubState,Result,UnitFileState,ExecMainExitTimestamp'], { timeout: 5000 });
      services[unit] = Object.fromEntries(stdout.trim().split('\n').map(l => { const i = l.indexOf('='); return [l.slice(0, i), l.slice(i + 1)]; }));
    } catch { services[unit] = { ActiveState: 'unavailable' }; }
  }
  return { scope: 'Local user services on homelab-dev only; not whole-homelab monitoring.', services };
}
module.exports = { photosStatus, localHealth };
