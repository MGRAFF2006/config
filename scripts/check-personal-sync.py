#!/usr/bin/env python3
"""Check that scope changes preserve personal files and can be rolled back."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.parse

spec = importlib.util.spec_from_file_location("personal_sync", Path(__file__).with_name("configure-personal-sync.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
POLICY = json.loads((sync.ROOT / "syncthing/personal-files.json").read_text())


class LocalAPI:
    def __init__(self, folders):
        self.folders = {f["id"]: deepcopy(f) for f in folders}
        self.ignores = {f["id"]: ["// local rule", "*.part"] for f in folders}
        self.calls = []
        self.fail_ignore_write = False

    def __call__(self, endpoint, data=None, method="GET"):
        self.calls.append((method, endpoint))
        if endpoint == "system/status":
            return {"myID": "test-device"}
        if endpoint == "config/folders":
            if method == "POST":
                self.folders[data["id"]] = deepcopy(data)
                return None
            return list(deepcopy(self.folders).values())
        if endpoint.startswith("config/folders/") and method == "DELETE":
            del self.folders[urllib.parse.unquote(endpoint.split("/")[-1])]
            return None
        if endpoint.startswith("db/ignores?"):
            folder_id = urllib.parse.parse_qs(urllib.parse.urlsplit(endpoint).query)["folder"][0]
            if method == "POST":
                if self.fail_ignore_write:
                    raise OSError("Simulated ignore write failure")
                self.ignores[folder_id] = deepcopy(data["ignore"])
                return None
            return {"ignore": deepcopy(self.ignores[folder_id])}
        raise AssertionError((method, endpoint))


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.folders = [{"id": name, "path": str(self.home / rel), "type": "sendreceive"}
                        for name, rel in [("projects", "Projects"), ("config", "Documents/config"),
                                          ("docs", "Documents"), ("pictures", "Pictures")]]
        self.api = LocalAPI(self.folders)

    def apply(self):
        sync.apply_scope(self.api, self.home, POLICY, self.home / "state", True)
        return next((self.home / "state/config").glob("*/scope.json"))

    def test_preview_does_not_change_configuration(self):
        sync.apply_scope(self.api, self.home, POLICY, self.home / "state", False)
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))
        self.assertFalse((self.home / "state").exists())

    def test_apply_preserves_personal_content_and_is_idempotent(self):
        personal = self.home / "Documents/Studium/report.txt"
        source = self.home / "Projects/demo/source.py"
        for path in (personal, source):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Keep this content")
        before = {path: path.read_bytes() for path in (personal, source)}
        backup = self.apply()
        self.assertEqual(set(self.api.folders), {"docs", "pictures"})
        rules = self.api.ignores["docs"]
        self.assertIn("/config", rules)
        self.assertIn("/3DPrinting/OrcaSlicer", rules)
        self.assertIn("MeshroomCache", rules)
        self.assertIn("*.part", rules)
        for forbidden in ("/Studium", "/Roadtrip", "/homelab-docs", "/Archive", "build", "*.pdf", ".git"):
            self.assertNotIn(forbidden, rules)
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(backup.parent.stat().st_mode & 0o777, 0o700)
        self.api.calls.clear()
        sync.apply_scope(self.api, self.home, POLICY, self.home / "state", True)
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))
        self.assertEqual(len(list(backup.parent.parent.glob("*/scope.json"))), 1)

    def test_restore_handles_partial_failure_without_overwriting_new_rules(self):
        original = deepcopy(self.api.folders), deepcopy(self.api.ignores)
        self.api.fail_ignore_write = True
        with self.assertRaises(OSError):
            self.apply()
        backup = next((self.home / "state/config").glob("*/scope.json"))
        self.api.fail_ignore_write = False
        sync.restore_scope(self.api, backup)
        self.assertEqual((self.api.folders, self.api.ignores), original)
        backup = self.apply()
        self.api.ignores["docs"].append("new-local-rule")
        self.api.calls.clear()
        with self.assertRaisesRegex(ValueError, "Ignore rules changed"):
            sync.restore_scope(self.api, backup)
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))

    def test_nested_code_shares_are_removed_without_removing_personal_parent(self):
        self.folders.append({"id": "nested", "path": str(self.home / "Projects/demo")})
        removed, retained = sync.scope_plan(self.folders, self.home, POLICY)
        self.assertEqual({f["id"] for f in removed}, {"projects", "config", "nested"})
        self.assertEqual({f["id"] for f, _ in retained}, {"docs", "pictures"})

    def test_symlinked_code_root_is_excluded(self):
        actual = self.home / "external-projects"
        actual.mkdir()
        (self.home / "Projects").symlink_to(actual, target_is_directory=True)
        removed, retained = sync.scope_plan(self.folders, self.home, POLICY)
        self.assertIn("projects", {f["id"] for f in removed})
        self.assertIn("docs", {f["id"] for f, _ in retained})

    def test_wrong_device_restore_does_not_mutate_configuration(self):
        backup = self.apply()
        snapshot = json.loads(backup.read_text())
        snapshot["device"] = "another-device"
        backup.write_text(json.dumps(snapshot))
        self.api.calls.clear()
        with self.assertRaisesRegex(ValueError, "another Syncthing device"):
            sync.restore_scope(self.api, backup)
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))

    def test_custom_escape_header_remains_valid_before_patterns(self):
        previous = ["// Device-specific escape character", "", "#escape=|",
                    "/archive/|[notes|].txt", "!keep.txt"]
        result = sync.managed_ignores(previous, ["node_modules"])
        significant = [line for line in result if line and not line.startswith("//")]
        self.assertEqual(significant[0], "#escape=|")
        self.assertIn("/archive/|[notes|].txt", significant)
        self.assertLess(significant.index("node_modules"), significant.index("!keep.txt"))
        self.assertEqual(sync.managed_ignores(result, ["node_modules"]), result)


if __name__ == "__main__":
    unittest.main()
