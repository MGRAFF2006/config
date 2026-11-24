#!/usr/bin/env python3
"""Exercise real Gio file events during rapid atomic DMS state replacement."""

import os
from pathlib import Path
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def wait_for(predicate, process):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("Watcher exited before handling file events")
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("Watcher missed an atomic replacement")


def main():
    with tempfile.TemporaryDirectory(prefix="greeter-watch-check-") as directory:
        root = Path(directory)
        inputs = [root / "config/dms/settings.json", root / "state/dms/session.json", root / "cache/dms/dms-colors.json"]
        for path in inputs:
            path.parent.mkdir(parents=True)
            path.write_text("{}")
            path.chmod(0o600)
        runner = root / "fixture.py"
        # Native synchronization is the external boundary. The real Gio monitor
        # must retain events while this repair is still busy after granting read.
        runner.write_text('''import importlib.machinery, importlib.util, sys, time
from pathlib import Path
loader = importlib.machinery.SourceFileLoader("watcher", sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
watcher = importlib.util.module_from_spec(spec)
loader.exec_module(watcher)
root = Path(sys.argv[2])
def repair():
    for path in [root / "config/dms/settings.json", root / "state/dms/session.json", root / "cache/dms/dms-colors.json"]:
        path.chmod(0o640)
    with (root / "repairs").open("a") as stream:
        stream.write("synced\\n")
    time.sleep(0.08)
watcher.main(repair)
''')
        env = dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"), XDG_CACHE_HOME=str(root / "cache"))
        env.pop("NOTIFY_SOCKET", None)
        with (root / "watcher.log").open("w") as log:
            process = subprocess.Popen(["/usr/bin/python3", str(runner), str(ROOT / "home/.local/bin/dms-greeter-theme-watch"), str(root)], env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                wait_for(lambda: (root / "repairs").exists(), process)
                for index in range(12):
                    target = inputs[index % len(inputs)]
                    fd, name = tempfile.mkstemp(dir=target.parent)
                    with os.fdopen(fd, "w") as stream:
                        stream.write('{"revision": ' + str(index) + '}')
                    os.replace(name, target)
                    wait_for(lambda: target.stat().st_mode & 0o040, process)
                # Metadata repair itself must not cause an endless sync loop.
                time.sleep(0.2)
                count = (root / "repairs").read_text().count("synced")
                time.sleep(0.3)
                assert (root / "repairs").read_text().count("synced") == count
                assert all(path.stat().st_mode & 0o040 for path in inputs)
            finally:
                process.terminate()
                process.wait(timeout=5)
    print("PASS: Gio retains atomic settings/session/color replacements during busy sync; metadata repair does not loop")


if __name__ == "__main__":
    main()
