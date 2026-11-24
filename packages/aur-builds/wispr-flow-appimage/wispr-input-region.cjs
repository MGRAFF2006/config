// Keep transparent areas click-through without changing the painted window shape.
const { spawn } = require('node:child_process');
const path = require('node:path');
let helper = null;

module.exports = function setInputRegion(window, rectangles, controller) {
  if (!helper || helper.stdin.destroyed) {
    const child = spawn('/usr/bin/python3', [path.join(__dirname, 'wispr-input-region.py')], {
      stdio: ['pipe', 'ignore', 'inherit'],
    });
    const controllers = new Set();
    child.controllers = controllers;
    helper = child;
    const reset = () => {
      // The helper may exit before applying queued writes. Clear the shape
      // controllers' cache so their next report, even an identical one, resends.
      for (const sender of controllers) sender.lastShapeKey = null;
      controllers.clear();
      if (helper === child) helper = null;
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
