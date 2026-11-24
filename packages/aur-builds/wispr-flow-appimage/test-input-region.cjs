// Regression check for wispr-input-region.cjs: run with `node test-input-region.cjs`.
// If the helper exits before applying a queued region, the next identical report
// must send that region again despite the shape controller's cache.
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'wispr-input-region-'));
const log = path.join(directory, 'applied.jsonl');
const crashOnce = path.join(directory, 'crash-once');
fs.copyFileSync(path.join(__dirname, 'wispr-input-region.cjs'), path.join(directory, 'wispr-input-region.cjs'));
// Stand-in helper: the first instance exits without reading its queued write.
fs.writeFileSync(path.join(directory, 'wispr-input-region.py'), `
import os, sys
if os.path.exists(${JSON.stringify(crashOnce)}):
    os.remove(${JSON.stringify(crashOnce)})
    sys.exit(0)
with open(${JSON.stringify(log)}, 'a') as applied:
    for line in sys.stdin:
        applied.write(line)
        applied.flush()
`);
fs.writeFileSync(crashOnce, '');
const setInputRegion = require(path.join(directory, 'wispr-input-region.cjs'));

// Mirrors the patched StatusInputShape.applyShape from repair-overlays.py.
const shapeKey = ({ x, y, width, height }) => `${x},${y},${width},${height}`;
const controller = {
  window: {
    isDestroyed: () => false,
    getContentBounds: () => ({ width: 512, height: 614 }),
    getNativeWindowHandle: () => { const handle = Buffer.alloc(4); handle.writeUInt32LE(0x1234); return handle; },
  },
  lastShapeKey: null,
  applyShape(rectangles) {
    const key = rectangles.map(shapeKey).join(';');
    if (key !== this.lastShapeKey) {
      setInputRegion(this.window, rectangles, this);
      this.lastShapeKey = key;
    }
  },
};

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const applied = () => fs.existsSync(log) ? fs.readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [];

(async () => {
  const region = [{ x: 10, y: 20, width: 120, height: 40 }];
  controller.applyShape(region);
  for (let i = 0; i < 50 && fs.existsSync(crashOnce); i++) await wait(20);
  await wait(200); // let the shim observe the helper exit
  controller.applyShape(region); // identical report after the lost write
  for (let i = 0; i < 50 && applied().length === 0; i++) await wait(20);
  const writes = applied();
  fs.rmSync(directory, { recursive: true, force: true });
  assert.deepStrictEqual(writes.map(write => write.rects), [region], 'identical report did not recover the lost region');
  console.log('ok: identical report re-applied the region after a helper exit');
  process.exit(0);
})().catch(error => {
  fs.rmSync(directory, { recursive: true, force: true });
  console.error(error.message);
  process.exit(1);
});
