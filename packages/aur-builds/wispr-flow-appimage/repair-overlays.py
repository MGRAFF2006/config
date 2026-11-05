#!/usr/bin/env python3
"""Repair the pinned Linux bundle without changing ASAR entry offsets."""
import hashlib
import json
import struct
import sys
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def replace_once(data, old, new):
    require(data.count(old) == 1, 'Unexpected bundle signature: ' + old[:80].decode())
    return data.replace(old, new)


def pad(original, patched):
    missing = len(original) - len(patched)
    require(missing >= 0, f'Patch exceeds original entry by {-missing} bytes')
    return patched + (b'\n' + b' ' * (missing - 1) if missing else b'')


def main_bundle(original):
    compact = b'return(/*WISPR_LINUX_STATUS_COMPACT*/"linux"===process.platform)?{x:u+(h-200)/2,y:p+m-110,width:200,height:110}:{x:u+(h-l)/2,y:p+m-o,width:l,height:o}'
    patched = replace_once(original, compact, b'return/*WISPR_LINUX_FULL_CANVAS*/{x:u+(h-l)/2,y:p+m-o,width:l,height:o}')
    start = patched.index(b'72413(e,t,n){')
    end = patched.index(b'},58601(e,t,n){', start)
    module = patched[start:end]
    require(b'$X' not in module, 'Input-shape flag name is already in use')
    module = replace_once(module, b'const Q=new f.s0;', b'const $X=M.H8||("linux"===process.platform&&"x11"===i.app.commandLine.getSwitchValue("ozone-platform"));const Q=new f.s0;')
    for old, new in (
        (b'M.H8?Q.replaceWindow(r)', b'$X?Q.replaceWindow(r)'),
        (b'M.H8&&e&&(Q.', b'$X&&e&&(Q.'),
        (b'M.H8&&!r.isDestroyed()', b'$X&&!r.isDestroyed()'),
        (b'M.H8&&!ne&&Q.', b'$X&&!ne&&Q.'),
        (b'if(ne=!1,M.H8){Q.', b'if(ne=!1,$X){Q.'),
        (b'M.H8&&t&&(Q.', b'$X&&t&&(Q.'),
        (b'else if(M.H8){const e=n.getContentBounds()', b'else if($X){const e=n.getContentBounds()'),
    ):
        module = replace_once(module, old, new)
    require(module.count(b'M.H8&&Q.') == 4, 'Unexpected shape-controller guards')
    module = module.replace(b'M.H8&&Q.', b'$X&&Q.')
    module = replace_once(module, b'e&&!e.isDestroyed()&&($=(0,g.Bi)(e))', b'e&&!e.isDestroyed()&&(M.H8||!$X?($=(0,g.Bi)(e)):(e.setIgnoreMouseEvents(!1),Q.lastShapeKey=null,Q.applyCurrentShape()))')
    patched = patched[:start] + module + patched[end:]
    patched = replace_once(patched, b'this.enabled?this.applyShape(this.latestRects):', b'this.enabled?this.applyShape(this.latestRects.length?this.latestRects:o):')
    patched = replace_once(patched, b't.setShape(e),this.lastShapeKey=n', b'("linux"===process.platform&&"x11"===r.app.commandLine.getSwitchValue("ozone-platform")?require(require("path").join(process.resourcesPath,"Release","wispr-input-region.cjs"))(t,e):t.setShape(e)),this.lastShapeKey=n')
    prefix_end = patched.index(b';(function () {')
    prefix = patched[:prefix_end]
    prefix = b''.join(line for line in prefix.splitlines(keepends=True) if not line.startswith(b'//'))
    patched = prefix + patched[prefix_end:]
    print('Main patch size change:', len(patched) - len(original))
    return pad(original, patched)


def renderer_bundle(original):
    start = original.index(b'69096(e,t,o){')
    end = original.index(b'},82889(e,t,o){', start)
    module = original[start:end]
    require(module.count(b'a.H8') == 3, 'Unexpected renderer shape-report guards')
    module = module.replace(b'a.H8', b'true')
    return pad(original, original[:start] + module + original[end:])


def repair_archive(archive):
    with archive.open('r+b') as stream:
        header_size = struct.unpack('<II', stream.read(8))[1]
        raw_header = stream.read(header_size)
        json_size = struct.unpack('<I', raw_header[4:8])[0]
        header_bytes = raw_header[8:8 + json_size]
        header = json.loads(header_bytes)
        changes = []
        for parts, transform in (
            (('.webpack', 'main', 'index.js'), main_bundle),
            (('.webpack', 'renderer', 'status', 'index.js'), renderer_bundle),
        ):
            entry = header
            for part in parts:
                entry = entry['files'][part]
            offset = 8 + header_size + int(entry['offset'])
            stream.seek(offset)
            original = stream.read(entry['size'])
            integrity = entry['integrity']
            require(integrity['algorithm'] == 'SHA256', 'Unsupported archive integrity')
            block_size = integrity['blockSize']
            def hashes(data):
                return [hashlib.sha256(data[i:i + block_size]).hexdigest() for i in range(0, len(data), block_size)]
            require(integrity['hash'] == hashlib.sha256(original).hexdigest(), 'Archive digest mismatch')
            require(integrity['blocks'] == hashes(original), 'Archive block digest mismatch')
            patched = transform(original)
            updated = dict(integrity, hash=hashlib.sha256(patched).hexdigest(), blocks=hashes(patched))
            old_json = json.dumps(integrity, separators=(',', ':')).encode()
            new_json = json.dumps(updated, separators=(',', ':')).encode()
            require(header_bytes.count(old_json) == 1, 'Ambiguous archive integrity entry')
            header_bytes = header_bytes.replace(old_json, new_json)
            changes.append((offset, patched))
        require(len(header_bytes) == json_size, 'Archive header size changed')
        for offset, data in changes:
            stream.seek(offset)
            stream.write(data)
        stream.seek(16)
        stream.write(header_bytes)
    print('Repaired full canvas and XWayland control-region input; archive integrity updated')


repair_archive(Path(sys.argv[1]))

if len(sys.argv) > 2:
    launcher=Path(sys.argv[2])
    text=launcher.read_text()
    anchor='# Handle --doctor before anything else.\n'
    assert text.count(anchor)==1,'Unexpected launcher; refusing to modify'
    backend='''# XWayland supports the full transparent popup canvas and input shaping.
wispr_desktop="${XDG_CURRENT_DESKTOP:-}"
if [[ "${wispr_desktop,,}" == *hyprland* && "${WISPR_USE_WAYLAND:-}" != "1" ]]; then
    export WISPR_USE_X11="${WISPR_USE_X11:-1}"
fi

'''
    launcher.write_text(text.replace(anchor,backend+anchor))
    print('Defaulted Hyprland to XWayland while preserving explicit overrides')
