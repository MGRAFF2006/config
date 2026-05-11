#!/usr/bin/env bash
# audit-system.sh — Generate package/service reports for this machine
# Reports are written to reports/<hostname>/ (git-ignored)
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
report_dir="$repo_root/reports/$(hostname)"
mkdir -p "$report_dir"

echo "Generating reports for $(hostname) in $report_dir..."

pacman -Qqen > "$report_dir/explicit-native.txt"
echo "  explicit-native.txt ($(wc -l < "$report_dir/explicit-native.txt") packages)"

pacman -Qqem > "$report_dir/explicit-foreign.txt"
echo "  explicit-foreign.txt ($(wc -l < "$report_dir/explicit-foreign.txt") AUR packages)"

pacman -Qdtq > "$report_dir/orphans.txt" 2>/dev/null || echo "" > "$report_dir/orphans.txt"
echo "  orphans.txt ($(wc -l < "$report_dir/orphans.txt") orphans)"

systemctl --user list-unit-files --state=enabled > "$report_dir/user-services.txt"
echo "  user-services.txt"

systemctl list-unit-files --state=enabled > "$report_dir/system-services.txt"
echo "  system-services.txt"

printf '\nReports written to: %s\n' "$report_dir"
printf 'Compare explicit-native.txt with packages/common.txt to find drift.\n'
