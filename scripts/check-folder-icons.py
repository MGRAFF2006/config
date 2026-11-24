#!/usr/bin/env python3
"""Verify folder palette changes retain artwork, aliases and inherited app icons."""

import importlib.util
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET


def main():
    spec = importlib.util.spec_from_file_location("folder_icons", Path(__file__).with_name("theme-folder-icons.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="folder-icons-check-") as directory:
        root = Path(directory)
        system, output = root / "system", root / "output"
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:#5294e2;opacity:0.8" d="M 1,2 L 3,4"/><path fill="#1d344f" d="M 2,3 L 4,5"/><path fill="#e4e4e4" d="M 0,1"/></svg>'
        for base in ("Papirus", "Papirus-Dark"):
            theme = system / base
            theme.mkdir(parents=True)
            (theme / "index.theme").write_text("[Icon Theme]\nName=" + base + "\n")
            for size in module.SIZES:
                places = theme / f"{size}x{size}/places"
                places.mkdir(parents=True)
                (places / "folder-blue.svg").write_text(svg)
                (places / "folder.svg").symlink_to("folder-blue.svg")
                (places / "folder-documents.svg").symlink_to("folder-blue.svg")
                (places / "folder-red.svg").write_text(svg.replace("#5294e2", "#ff0000"))
        module.generate({"primary": "#aabbcc", "on_primary": "#112233"}, output, system)
        for base in ("Papirus", "Papirus-Dark"):
            theme = output / ("DMS-" + base)
            assert "Inherits=" + base in (theme / "index.theme").read_text()
            assert not list(theme.glob("*/apps/*"))
            for size in module.SIZES:
                icon = theme / f"{size}x{size}/places/folder.svg"
                result = icon.read_text()
                assert "#aabbcc" in result and "#112233" in result
                assert "#e4e4e4" in result and "opacity:0.8" in result
                assert [node.attrib.get("d") for node in ET.fromstring(result)] == [node.attrib.get("d") for node in ET.fromstring(svg)]
                assert (icon.parent / "folder-documents.svg").exists()
                assert not (icon.parent / "folder-red.svg").exists()
        module.generate({"primary": "#334455", "on_primary": "#ddeeff"}, output, system)
        assert "#334455" in (output / "DMS-Papirus/48x48/places/folder.svg").read_text()
        assert "#aabbcc" not in (output / "DMS-Papirus/48x48/places/folder.svg").read_text()
    print("PASS: folder palette changes, all sizes, alias resolution, artwork/opacity/neutral preservation, app inheritance")


if __name__ == "__main__":
    main()
