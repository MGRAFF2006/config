// Regression check for wispr-input-region.cjs against the real patched bundle:
//   node test-input-region.cjs [pristine app.asar]
// The default path is the pristine archive that makepkg leaves in
// src/squashfs-root. The test applies repair-overlays.py to a temporary copy and
// drives the patched status renderer's report module (69096) and the patched
// main-process shape controller (76127) with a stand-in X11 helper.
// 1. If the helper exits before applying a region and the popup stays still,
//    the renderer sends no new report, yet the region must be applied again.
// 2. A helper that keeps exiting is restarted a bounded number of times.
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const pristine = path.resolve(process.argv[2] || path.join(__dirname, 'src/squashfs-root/usr/lib/wispr-flow/resources/app.asar'));
if (!fs.existsSync(pristine)) {
  console.error(`Pristine app.asar not found at ${pristine}; pass its path (it is extracted from the pinned AppImage).`);
  process.exit(1);
}
assert.strictEqual(process.platform, 'linux', 'the patched controller only uses the X11 helper on Linux');

const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'wispr-input-region-'));
const cleanup = () => fs.rmSync(directory, { recursive: true, force: true });

// Patch a copy exactly as the package does, then read the two bundles.
const archive = path.join(directory, 'app.asar');
fs.copyFileSync(pristine, archive);
execFileSync('python3', [path.join(__dirname, 'repair-overlays.py'), archive], { stdio: 'ignore' });
function readEntry(parts) {
  const data = fs.readFileSync(archive);
  const headerSize = data.readUInt32LE(4);
  const header = JSON.parse(data.subarray(16, 16 + data.readUInt32LE(12)).toString());
  const entry = parts.reduce((node, part) => node.files[part], header);
  const offset = 8 + headerSize + Number(entry.offset);
  return data.subarray(offset, offset + entry.size).toString();
}
const mainBundle = readEntry(['.webpack', 'main', 'index.js']);
const statusBundle = readEntry(['.webpack', 'renderer', 'status', 'index.js']);

// Evaluate one webpack module with stubbed dependencies.
function loadModule(bundle, id, dependencies) {
  const start = bundle.indexOf(`${id}(e,t,`);
  assert.ok(start > 0, `module ${id} not found`);
  const next = /\},\d+\(e,t,[a-z]\)\{/g;
  next.lastIndex = start;
  const end = next.exec(bundle).index;
  const factory = new Function('require', `return ({${bundle.slice(start, end)}}})`)(require)[id];
  const exports = {};
  const load = dependency => {
    assert.ok(dependency in dependencies, `module ${id} requires unexpected ${dependency}`);
    return dependencies[dependency];
  };
  load.d = (target, getters) => {
    for (const [name, get] of Object.entries(getters)) Object.defineProperty(target, name, { get, enumerable: true });
  };
  load.n = module => () => module;
  factory({ exports }, exports, load);
  return exports;
}

const quietLog = { warn() {}, info() {}, error() {} };
const electron = { app: { commandLine: { getSwitchValue: name => (name === 'ozone-platform' ? 'x11' : '') } } };
const shapes = loadModule(mainBundle, 76127, { 84157: electron, 69493: quietLog });

// Stand-in helper: logs applied reports; optionally exits before reading.
function helperDirectory(name, behaviour) {
  const release = path.join(directory, name, 'Release');
  fs.mkdirSync(release, { recursive: true });
  fs.copyFileSync(path.join(__dirname, 'wispr-input-region.cjs'), path.join(release, 'wispr-input-region.cjs'));
  const files = { applied: path.join(release, 'applied.jsonl'), starts: path.join(release, 'starts'), crashOnce: path.join(release, 'crash-once') };
  if (behaviour === 'crash-once') fs.writeFileSync(files.crashOnce, '');
  fs.writeFileSync(path.join(release, 'wispr-input-region.py'), `
import os, sys
with open(${JSON.stringify(files.starts)}, 'a') as starts:
    starts.write('.')
if ${JSON.stringify(behaviour)} == 'always-crash':
    sys.exit(0)
if os.path.exists(${JSON.stringify(files.crashOnce)}):
    os.remove(${JSON.stringify(files.crashOnce)})
    sys.exit(0)
with open(${JSON.stringify(files.applied)}, 'a') as applied:
    for line in sys.stdin:
        applied.write(line)
        applied.flush()
`);
  return {
    root: path.dirname(release),
    ...files,
    appliedRects: () => (fs.existsSync(files.applied) ? fs.readFileSync(files.applied, 'utf8').split('\n').filter(Boolean).map(line => JSON.parse(line).rects) : []),
    startCount: () => (fs.existsSync(files.starts) ? fs.readFileSync(files.starts, 'utf8').length : 0),
  };
}

// A status window wired as module 72413 does: validated reports from its
// webContents go to the shape controller's applyReport.
function statusWindow() {
  const webContents = {};
  const window = {
    webContents,
    isDestroyed: () => false,
    getContentBounds: () => ({ x: 0, y: 0, width: 512, height: 614 }),
    getNativeWindowHandle: () => { const handle = Buffer.alloc(4); handle.writeUInt32LE(0x1234); return handle; },
    setIgnoreMouseEvents() {},
    setShape() { throw new Error('the X11 path must not change the painted shape'); },
  };
  const controller = new shapes.s0();
  controller.replaceWindow(window);
  controller.setEnabled(true);
  let reports = 0;
  const send = (channel, wait, payload) => {
    assert.strictEqual(channel, 'status:reportAlphaCatchRects');
    reports += 1;
    const report = structuredClone(payload);
    if (shapes.xZ(report)) controller.applyReport(webContents, report);
  };
  // Renderer globals used by the report module.
  let observed = null;
  globalThis.window = { innerWidth: 512, innerHeight: 614, addEventListener() {}, removeEventListener() {} };
  globalThis.ResizeObserver = class { constructor(callback) { observed = callback; } observe() {} disconnect() {} };
  const renderer = loadModule(statusBundle, 69096, {
    81794: { useLayoutEffect: effect => effect(), useEffect() {} },
    56961: { H8: false },
    26291: { EB: { ReportAlphaCatchRects: 'status:reportAlphaCatchRects' } },
    82889: { $: send },
  });
  return { renderer, remeasure: () => observed([]), reports: () => reports };
}

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const until = async (condition, milliseconds) => {
  for (const deadline = Date.now() + milliseconds; !condition() && Date.now() < deadline;) await wait(20);
};

async function staleRegionRecovers() {
  const helper = helperDirectory('crash-once', 'crash-once');
  process.resourcesPath = helper.root;
  const status = statusWindow();
  const region = { x: 10, y: 20, width: 120, height: 40 };
  const button = { current: { getBoundingClientRect: () => ({ left: region.x, top: region.y, width: region.width, height: region.height }) } };
  status.renderer.Yh('button', button, null); // the renderer's measured-control hook
  await until(() => status.reports() === 1, 1000);
  assert.strictEqual(status.reports(), 1, 'renderer did not report the control');
  await until(() => !fs.existsSync(helper.crashOnce), 2000);
  await wait(100); // the first helper has exited without applying anything
  status.remeasure(); // identical geometry: the renderer must stay quiet
  await wait(50);
  assert.strictEqual(status.reports(), 1, 'renderer unexpectedly re-reported identical geometry');
  await until(() => helper.appliedRects().length > 0, 3000);
  assert.deepStrictEqual(helper.appliedRects().at(-1), [region], 'the lost region was not applied again without a new report');
  console.log('ok: a region lost with the helper is applied again although the renderer stays quiet');
}

async function retriesAreBounded() {
  const helper = helperDirectory('always-crash', 'always-crash');
  process.resourcesPath = helper.root;
  const status = statusWindow();
  const button = { current: { getBoundingClientRect: () => ({ left: 5, top: 5, width: 50, height: 30 }) } };
  status.renderer.Yh('button', button, null);
  await wait(500 + 1000 + 1500 + 2000); // all back-off delays plus margin
  assert.strictEqual(helper.startCount(), 4, `expected the initial helper and 3 retries, saw ${helper.startCount()} starts`);
  console.log('ok: a helper that keeps exiting is restarted 3 times, then left until the next report');
}

(async () => {
  await staleRegionRecovers();
  await retriesAreBounded();
  cleanup();
  process.exit(0);
})().catch(error => {
  cleanup();
  console.error(error.message);
  process.exit(1);
});
