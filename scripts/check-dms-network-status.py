#!/usr/bin/env python3
"""Exercise status semantics without accessing a network, credentials, or session."""

from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "home/.local/bin/dms-network-status"
LOADER = SourceFileLoader("dms_network_status", str(SOURCE))
STATUS = module_from_spec(spec_from_loader(LOADER.name, LOADER))
LOADER.exec_module(STATUS)


def main():
    commands = []
    devices = "wlan0:wifi:connected\nenp1s0:ethernet:connected"
    device_code = 0
    state = "full"
    connectivity_code = 0
    details_code = 0
    details = "\n".join((
        "GENERAL.CONNECTION:Wired", "GENERAL.HWADDR:aa\\:bb\\:cc\\:dd\\:ee\\:ff",
        "IP4.ADDRESS[1]:192.0.2.10/24", "IP4.GATEWAY:192.0.2.1", "IP4.DNS[1]:192.0.2.1",
    ))
    routes = [{"dev": "enp1s0", "metric": 100}, {"dev": "wlan0", "metric": 600}]

    def run(command, timeout=3):
        commands.append(command)
        assert "--show-secrets" not in command
        assert "check" not in command, "A status poll must not force NM connectivity checks"
        if command[0] == "ip":
            return (json.dumps(routes), 0)
        if command[0] == "/usr/bin/ping":
            return ("", 1)  # A blocked ICMP probe must not report Offline.
        if command[0] == "resolvectl":
            return ("", 1)
        assert command[0] == "nmcli", command
        if command[-2:] == ["device", "status"]:
            return devices, device_code
        if command[1:] == ["-g", "CONNECTIVITY", "general"]:
            return state, connectivity_code
        if "show" in command:
            assert "IP6.ADDRESS" in command[3]
            return details, details_code
        assert "wifi" in command
        return "*:Example:90:300 Mbit/s:WPA2", 0

    def sample(*args):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(STATUS, "run", side_effect=run), \
                patch.object(STATUS, "network_rates", return_value=(0, 0)):
            assert STATUS.main(list(args)) == 0
        result = json.loads(output.getvalue())
        assert "password" not in result
        return result

    result = sample()
    assert result["connected"] is True and result["connectivity"] == "full"
    assert result["interface"] == "enp1s0", "Prefer the default route over Wi-Fi"
    assert result["gatewayPingMs"] is None and result["internetPingMs"] is None
    assert result["dnsLookupMs"] is None
    assert ["/usr/bin/ping", "-n", "-c", "1", "-W", "1", "-I", "enp1s0", "192.0.2.1"] in commands
    assert all("-I" not in command for command in commands if command[-1] == "1.1.1.1")

    result = sample("--interface", "wlan0")
    assert result["connected"] is True and result["interface"] == "wlan0"
    result = sample("--interface", "missing0")
    assert result["connected"] is None and "missing0" in result["error"]

    for state in ("portal", "limited", "none", "unknown", "unexpected"):
        result = sample()
        assert result["connected"] is True
        assert result["connectivity"] == (state if state != "unexpected" else "unknown")
    state = "full"
    connectivity_code = 1
    assert sample()["connectivity"] == "unknown"
    connectivity_code = 0
    device_code = 1
    result = sample()
    assert result["connected"] is None and "NetworkManager" in result["error"]
    device_code = 0
    devices = "wlan0:wifi:disconnected\nenp1s0:ethernet:unavailable"
    assert sample()["connected"] is False

    devices = "wlan0:wifi:connected"
    routes = [{"dev": "wlan0", "metric": 100}]
    details = "\n".join((
        "GENERAL.CONNECTION:IPv6 WiFi", "IP4.GATEWAY:--", "IP6.ADDRESS[1]:2001\\:db8\\:\\:10/64",
        "IP6.GATEWAY:fe80\\:\\:1", "IP6.DNS[1]:2001\\:db8\\:\\:53",
    ))
    result = sample()
    assert result["connected"] is True and result["interface"] == "wlan0"
    assert result["addresses"] == ["2001:db8::10/64"]
    assert result["dnsServers"] == ["2001:db8::53"]
    assert result["gateway"] == "fe80::1"
    assert ["/usr/bin/ping", "-n", "-c", "1", "-W", "1", "-I", "wlan0", "fe80::1%wlan0"] in commands
    assert any(command[-1] == "2606:4700:4700::1111" for command in commands)
    assert all("-I" not in command for command in commands if command[-1] == "2606:4700:4700::1111")
    details_code = 1
    result = sample()
    assert result["connected"] is True and "details" in result["error"]
    assert "--show-secrets" not in SOURCE.read_text() and "wifi_password" not in SOURCE.read_text()

    with tempfile.TemporaryDirectory(prefix="dms-network-status-check-") as directory:
        root = Path(directory)
        counters = root / "net/wlan0/statistics"
        counters.mkdir(parents=True)
        (counters / "rx_bytes").write_text("20000")
        (counters / "tx_bytes").write_text("10000")
        cache = root / "sample.json"
        old = {"device": "wlan0", "time": 96, "rx": 16000, "tx": 8000}
        with patch.object(STATUS, "SAMPLE_PATH", cache), patch.object(STATUS, "NET_PATH", root / "net"), \
                patch.object(STATUS.time, "monotonic", return_value=100):
            cache.write_text(json.dumps(old))
            assert STATUS.network_rates("wlan0") == (1000, 500)
            for change in ({"device": "enp1s0"}, {"time": "invalid"}, {"time": float("nan")},
                           {"time": 0}, {"time": 101}, {"rx": 30000}, {"tx": None}):
                cache.write_text(json.dumps(old | change))
                assert STATUS.network_rates("wlan0") == (0, 0), change
                assert json.loads(cache.read_text())["device"] == "wlan0"
            cache.write_text("{invalid")
            assert STATUS.network_rates("wlan0") == (0, 0)
    print("PASS: NM link/connectivity semantics, ICMP timeout, IPv6, route selection, rate reset, no secrets")


if __name__ == "__main__":
    main()
