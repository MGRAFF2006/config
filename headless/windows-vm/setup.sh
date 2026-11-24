#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

[[ "$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["HostName"])')" == homelab-dev ]] || {
  echo "Run this on homelab-dev." >&2
  exit 1
}
mountpoint -q /srv/development
test -c /dev/kvm
test -c /dev/net/tun
# Reserve room for the Windows disk, installation media and host free space.
test "$(df --output=avail -B1 /srv/development | tail -1)" -gt 137438953472 || {
  echo "Need at least 128 GiB free on /srv/development." >&2
  exit 1
}
sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /srv/development/windows-vm
mkdir -p /srv/development/windows-vm/oem
cp oem/* /srv/development/windows-vm/oem/
agent_msi=/srv/development/windows-vm/oem/qemu-ga-x86_64.msi
agent_sha=19dcf8abc30f70c2eb6e87282601fd0476e4e0b19936f63d9c80be30db0796ed
if [[ ! -f "$agent_msi" ]] || ! printf '%s  %s\n' "$agent_sha" "$agent_msi" | sha256sum --check --status; then
  curl --fail --location --retry 3 --silent --show-error \
    https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-qemu-ga/qemu-ga-win-110.2.3-2.el10/qemu-ga-x86_64.msi \
    --output "$agent_msi.download"
  printf '%s  %s\n' "$agent_sha" "$agent_msi.download" | sha256sum --check --status
  mv -- "$agent_msi.download" "$agent_msi"
fi
if [[ ! -e .env ]]; then
  (umask 077; python3 -c 'import secrets; print("WINDOWS_PASSWORD=" + secrets.token_hex(20))' > .env)
fi
chmod 600 .env
docker compose config --quiet
docker compose up -d
sudo tailscale serve --bg --yes --set-path=/windows http://127.0.0.1:8006
echo 'Browser console: https://homelab-dev.tail03caec.ts.net/windows/'
