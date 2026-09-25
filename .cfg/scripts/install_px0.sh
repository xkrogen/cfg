#!/usr/bin/env bash
# Install the latest official, checksum-verified px0 release into the user home.
set -euo pipefail

case "$(uname -s):$(uname -m)" in
    Darwin:x86_64) platform=darwin-amd64 ;;
    Darwin:arm64) platform=darwin-arm64 ;;
    Linux:x86_64) platform=linux-amd64 ;;
    Linux:aarch64|Linux:arm64) platform=linux-arm64 ;;
    *) echo "Unsupported px0 platform: $(uname -s)/$(uname -m)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null || { echo "px0 installation requires Python 3" >&2; exit 1; }
command -v curl >/dev/null || { echo "px0 installation requires curl" >&2; exit 1; }
bin="$HOME/.local/bin"
mkdir -p "$bin"
release=$(mktemp "$bin/.px0-release.XXXXXXXX")
checksums=$(mktemp "$bin/.px0-checksums.XXXXXXXX")
download=$(mktemp "$bin/.px0-download.XXXXXXXX")
trap 'rm -f -- "$release" "$checksums" "$download"' EXIT

curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 45 \
    https://api.github.com/repos/px0-ai/px0/releases/latest -o "$release"
read -r version asset < <(python3 - "$release" "$platform" <<'PY'
import json
import re
import sys

release = json.load(open(sys.argv[1]))
tag = release["tag_name"]
if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or release.get("prerelease") or release.get("draft"):
    raise SystemExit("Invalid latest stable px0 release")
asset = f"px0-{tag[1:]}-{sys.argv[2]}"
names = [item["name"] for item in release["assets"]]
if names.count(asset) != 1 or names.count("checksums.txt") != 1:
    raise SystemExit(f"Missing or duplicate official px0 assets for {tag}")
print(tag[1:], asset)
PY
)
url="https://github.com/px0-ai/px0/releases/download/v$version"
curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 180 "$url/checksums.txt" -o "$checksums"
curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 180 "$url/$asset" -o "$download"
python3 - "$checksums" "$asset" "$download" <<'PY'
import hashlib
import re
import sys

lines = [line for line in open(sys.argv[1]).read().splitlines() if line.endswith("  " + sys.argv[2])]
if len(lines) != 1 or not re.fullmatch(r"[0-9a-fA-F]{64}  " + re.escape(sys.argv[2]), lines[0]):
    raise SystemExit("Missing, duplicate or malformed px0 checksum")
digest = hashlib.sha256()
with open(sys.argv[3], "rb") as binary:
    for chunk in iter(lambda: binary.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != lines[0][:64].lower():
    raise SystemExit("px0 checksum mismatch; installed binary is unchanged")
PY

if [ -f "$bin/px0" ] && cmp -s "$download" "$bin/px0"; then
    echo "px0 $version already installed"
else
    chmod 755 "$download"
    mv -f "$download" "$bin/px0"
    echo "Installed px0 $version in $bin"
fi
