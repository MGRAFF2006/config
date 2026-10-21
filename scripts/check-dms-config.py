#!/usr/bin/env python3
"""Check fresh DMS setup, preserved preferences, and failure on corrupt input."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    script = Path(__file__).with_name("configure-dms-bar-panels.py")
    with tempfile.TemporaryDirectory(prefix="dms-config-check-") as directory:
        root = Path(directory)
        config = root / "config/DankMaterialShell"
        state = root / "state/DankMaterialShell"
        env = dict(os.environ, XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"))

        def run(*args, expected=0):
            result = subprocess.run(["python3", str(script), *args], env=env, capture_output=True, text=True)
            assert result.returncode == expected, result.stdout + result.stderr

        run(expected=1)
        assert not config.exists()
        run("--init")
        settings_path = config / "settings.json"
        plugin_path = config / "plugin_settings.json"
        settings = json.loads(settings_path.read_text())
        assert settings["customThemeFile"] == str(config / "theme_nord.json")
        assert settings["barConfigs"][0]["rightWidgets"].count("networkDiagnostics") == 1
        assert json.loads(plugin_path.read_text())["networkDiagnostics"]["enabled"] is True
        assert not state.exists()
        settings["currentThemeName"] = "blue"
        settings["myPreference"] = 42
        settings_path.write_text(json.dumps(settings))
        run("--init")
        assert json.loads(settings_path.read_text())["currentThemeName"] == "blue"
        assert json.loads(settings_path.read_text())["myPreference"] == 42
        previous = settings_path.read_bytes()
        run()
        assert settings_path.read_bytes() == previous
        plugin_path.write_text("{corrupt")
        run(expected=1)
        assert settings_path.read_bytes() == previous
        assert plugin_path.read_text() == "{corrupt"
        plugin_path.write_text("[]")
        run(expected=1)
        assert settings_path.read_bytes() == previous
    print("PASS: DMS first setup, existing preferences, idempotency, corrupt input preserved, no session required")


if __name__ == "__main__":
    main()
