#!/usr/bin/env bash
# Install the official Boat CLI without rewriting managed shell files or logging in.
set -euo pipefail

case "$(uname -s)" in
  Linux) boat_os=linux ;;
  Darwin) boat_os=darwin ;;
  *) echo "Boat installation supports Linux and macOS." >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) boat_arch=x64 ;;
  arm64|aarch64) boat_arch=arm64 ;;
  *) echo "Unsupported Boat architecture: $(uname -m)" >&2; exit 1 ;;
esac

boat_destination="$HOME/.local/bin/boat"
mkdir -p "$(dirname "$boat_destination")"
if [[ -L "$boat_destination" ]]; then
  echo "Refusing to replace an existing symlink: $boat_destination" >&2
  exit 1
fi
if [[ -e "$boat_destination" ]]; then
  "$boat_destination" --version | head -1 | command grep -Eq '^boat [0-9]+\.' || {
    echo "Refusing to overwrite a different program: $boat_destination" >&2
    exit 1
  }
fi

boat_download=$(mktemp "${boat_destination}.download.XXXXXX")
trap 'rm -f "$boat_download"' EXIT
curl --fail --silent --show-error --location \
  "https://boat.dev/api/boat/cli/download?platform=${boat_os}-${boat_arch}&channel=prod" \
  --output "$boat_download"
chmod 0755 "$boat_download"
"$boat_download" --version
mv "$boat_download" "$boat_destination"
echo "Installed $boat_destination. Sign in separately with: $boat_destination login"
