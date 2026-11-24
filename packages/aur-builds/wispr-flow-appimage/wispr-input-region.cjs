// Keep transparent areas click-through without changing the painted window shape.
const { spawn } = require('node:child_process');
const path = require('node:path');

// The helper may exit before applying queued writes. The status renderer only
// reports changed geometry, so waiting for its next report can leave a stale
// region while the popup stays still. Instead, resend each affected shape
// controller's current shape from its cached report. Retries back off and stop
// after RETRY_LIMIT helpers in a row exit within STABLE_MS of starting.
const RETRY_LIMIT = 3;
const RETRY_DELAY_MS = 500;
const STABLE_MS = 10000;

let helper = null;
let failures = 0;
let retryTimer = null;
const pending = new Set();

function resendAfterExit(controllers, lifetime) {
  if (lifetime >= STABLE_MS) failures = 0;
  failures += 1;
  for (const controller of controllers) {
    controller.lastShapeKey = null; // any later report resends, even an identical one
    pending.add(controller);
  }
  if (failures > RETRY_LIMIT) {
    if (failures === RETRY_LIMIT + 1) console.warn('[WisprInputRegion] Helper keeps exiting; waiting for the next shape report');
    pending.clear();
    return;
  }
  if (retryTimer) return;
  retryTimer = setTimeout(() => {
    retryTimer = null;
    const due = [...pending];
    pending.clear();
    for (const controller of due) controller.applyCurrentShape();
  }, RETRY_DELAY_MS * failures);
  retryTimer.unref?.();
}

module.exports = function setInputRegion(window, rectangles, controller) {
  if (!helper || helper.stdin.destroyed) {
    const child = spawn('/usr/bin/python3', [path.join(__dirname, 'wispr-input-region.py')], {
      stdio: ['pipe', 'ignore', 'inherit'],
    });
    const started = Date.now();
    child.controllers = new Set();
    helper = child;
    let ended = false;
    const reset = () => {
      if (ended) return; // exit, error and pipe errors can all report one failure
      ended = true;
      if (helper === child) helper = null;
      resendAfterExit(child.controllers, Date.now() - started);
      child.controllers.clear();
    };
    child.on('exit', reset);
    child.on('error', error => {
      console.warn('[WisprInputRegion] Helper failed:', error.message);
      reset();
    });
    child.stdin.on('error', error => {
      console.warn('[WisprInputRegion] Input pipe failed:', error.message);
      reset();
    });
  }
  if (controller) helper.controllers.add(controller);
  const bounds = window.getContentBounds();
  helper.stdin.write(JSON.stringify({
    window: window.getNativeWindowHandle().readUInt32LE(0),
    rects: rectangles,
    width: bounds.width,
    height: bounds.height,
  }) + '\n');
};
