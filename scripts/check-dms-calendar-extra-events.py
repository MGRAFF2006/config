#!/usr/bin/env python3
"""Exercise the actual calendar month grid with synthetic events in a private, throwaway desktop.

Uses the same private staging, launch-guard checks and isolated headless
desktop as check-dms-launcher-text.py; nothing reaches the running desktop,
its calendars, settings or services.
"""

import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, help="Pristine DMS UI; defaults to the running shell's dms.path")
    parser.add_argument("--unpatched", action="store_true", help="Reproduce the failure against pristine components")
    parser.add_argument("--evidence", type=Path, help="Save the rendered fixture as a PNG")
    parser.add_argument("--evidence-phase", type=int, default=0, help="Scenario to render as evidence: 0 cramped .. 4 roomy")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("launcher_check", Path(__file__).with_name("check-dms-launcher-text.py"))
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    module = helpers.load_configure()
    source = args.source_dir or helpers.running_ui_source()
    source = source.resolve(strict=True)
    original_hash = module.tree_digest(source)
    with tempfile.TemporaryDirectory(prefix="calendar-extra-events-check-") as directory:
        work = Path(directory)
        ui = helpers.prepare_ui(module, source, work, args.unpatched)
        version = (ui / "VERSION").read_text().strip()
        if not args.unpatched and not any(path.name.startswith("calendar-extra-events") for path in module.VERSION_PATCHES[version]):
            raise SystemExit(f"DMS {version} has no calendar extra-events patch; nothing to check.")
        env = {"DMS_CALENDAR_EVIDENCE": str(work / "evidence.png"), "DMS_CALENDAR_EVIDENCE_PHASE": str(args.evidence_phase)} if args.evidence else {}
        logs = helpers.run_isolated(work, ui, "calendar-extra-events.qml", env)
        if args.evidence and (work / "evidence.png").exists():
            shutil.copyfile(work / "evidence.png", args.evidence)
        for line in logs.splitlines():
            if "CALENDAR_EXTRA_EVENTS_INFO" in line:
                print(line.split("CALENDAR_EXTRA_EVENTS_INFO", 1)[1].strip())
        assert "CALENDAR_EXTRA_EVENTS_PASS" in logs, logs
        assert module.tree_digest(source) == original_hash, "Check changed the input UI"
        print(next(line for line in logs.splitlines() if "CALENDAR_EXTRA_EVENTS_PASS" in line))
        if not args.unpatched:
            print("PASS: renderer tamper/version fallback, repeat staging, unchanged input source")


if __name__ == "__main__":
    main()
