// Keep transparent areas click-through without changing the painted window shape.
const { spawn } = require('node:child_process');
const path = require('node:path');
let helper = null;

module.exports = function setInputRegion(window, rectangles) {
  if (!helper || helper.stdin.destroyed) {
    const child = spawn('/usr/bin/python3', [path.join(__dirname, 'wispr-input-region.py')], {
      stdio: ['pipe', 'ignore', 'inherit'],
    });
    helper = child;
    const reset = () => { if (helper === child) helper = null; };
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
  const bounds = window.getContentBounds();
  helper.stdin.write(JSON.stringify({
    window: window.getNativeWindowHandle().readUInt32LE(0),
    rects: rectangles,
    width: bounds.width,
    height: bounds.height,
  }) + '\n');
};
