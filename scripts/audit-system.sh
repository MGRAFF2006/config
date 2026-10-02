#!/usr/bin/env bash
# Write read-only inventory/drift reports; never install or remove packages.
# Usage: bash scripts/audit-system.sh [laptop|desktop]
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
machine="${1:-${MACHINE_TYPE:-}}"
[[ $# -le 1 ]] || { echo "Usage: $0 [laptop|desktop]" >&2; exit 2; }
if [[ -z "$machine" ]] && command -v tailscale >/dev/null 2>&1; then
  machine="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["HostName"])' 2>/dev/null || true)"
fi
case "$machine" in
  laptop) profile=laptop-kde ;;
  desktop) profile=desktop-dwm ;;
  *) echo "Pass laptop|desktop explicitly (this audit uses pacman)" >&2; exit 2 ;;
esac
report_dir="$repo_root/reports/$machine"
mkdir -p "$report_dir"

pacman -Qqen > "$report_dir/explicit-native.txt"
pacman -Qqem > "$report_dir/explicit-foreign.txt"
pacman -Qq > "$report_dir/installed.txt"
# pacman returns 1 when there are no orphans.
if pacman -Qdtq > "$report_dir/orphans.txt"; then :
elif [[ $? -ne 1 ]]; then echo 'Failed to query orphans' >&2; exit 1; fi
systemctl --user list-unit-files --state=enabled > "$report_dir/user-services.txt"
systemctl list-unit-files --state=enabled > "$report_dir/system-services.txt"

lists=("$repo_root/packages/common.txt" "$repo_root/packages/$profile.txt"
       "$repo_root/packages/aur-common.txt" "$repo_root/packages/aur-$machine.txt")
# Include the optional session only if its compositor is actually installed.
if pacman -Q hyprland >/dev/null 2>&1; then lists+=("$repo_root/packages/hyprland-dms.txt"); fi
awk '{sub(/#.*/, ""); if (NF) print $1}' "${lists[@]}" | LC_ALL=C sort -u > "$report_dir/desired.txt"
LC_ALL=C sort -u "$report_dir/installed.txt" > "$report_dir/installed-sorted.txt"
cat "$report_dir/explicit-native.txt" "$report_dir/explicit-foreign.txt" | LC_ALL=C sort -u > "$report_dir/explicit-sorted.txt"
LC_ALL=C comm -23 "$report_dir/desired.txt" "$report_dir/installed-sorted.txt" > "$report_dir/missing.txt"
LC_ALL=C comm -23 "$report_dir/explicit-sorted.txt" "$report_dir/desired.txt" > "$report_dir/unlisted.txt"
bash "$repo_root/scripts/link-home.sh" "$machine" --check > "$report_dir/links.txt" 2>&1 || {
  status=$?
  [[ "$status" == 1 ]] || exit "$status"
}

printf 'Reports: %s\n' "$report_dir"
printf 'Missing desired packages: %s\n' "$(wc -l < "$report_dir/missing.txt")"
printf 'Explicit packages outside these profiles: %s\n' "$(wc -l < "$report_dir/unlisted.txt")"
printf 'Review missing.txt, unlisted.txt and links.txt. Unlisted packages are not a removal list.\n'
