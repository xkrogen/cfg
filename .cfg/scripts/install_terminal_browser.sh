#!/usr/bin/env bash
# Install a verified official bundle without stopping or replacing running browsers.
set -euo pipefail

version=v0.11.1
base="$HOME/.local/share/terminal-browser"
app="$base/app"
bin="$HOME/.local/bin"
launcher="$bin/terminal-browser"

if [ -x "$launcher" ]; then
    "$launcher" --version
    exit 0
fi

# Published by https://terminal-browser.sh/install for this release.
case "$(uname -s):$(uname -m)" in
    Darwin:arm64)
        platform=darwin-arm64
        digest=9b21729e47bcc07e969913223705ce1ae5bcaa8e49094d6c9705c4cca8311d90 ;;
    Darwin:x86_64)
        platform=darwin-x64
        digest=9454b1467402049e0d08d07a69eb76b67e94f3c4c60ca2b8aadf4158c193c0f4 ;;
    Linux:x86_64|Linux:amd64)
        platform=linux-x64
        digest=b08327655aa3190260cf34807294be7c7c6685aa2639a393055b7c649eeb3a4a ;;
    Linux:aarch64|Linux:arm64)
        platform=linux-arm64
        digest=ef34c68333c4352e5107d5bd6c5cf7fe840a05c9a48a37084b9fc65fc986385c ;;
    *) echo "Unsupported terminal-browser platform: $(uname -s)/$(uname -m)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null || { echo "terminal-browser installation requires Python 3" >&2; exit 1; }
command -v curl >/dev/null || { echo "terminal-browser installation requires curl" >&2; exit 1; }
mkdir -p "$base" "$bin"
stage=$(mktemp -d "$base/.terminal-browser.XXXXXXXX")
cleanup() {
    if [ -d "$stage" ]; then rm -r -- "$stage"; fi
}
trap cleanup EXIT

if [ ! -e "$app" ]; then
    archive="$stage/terminal-browser-$platform.tar.gz"
    curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 300 \
        "https://terminal-browser.sh/install/dl/stable/$version/terminal-browser-$platform.tar.gz" \
        -o "$archive"
    python3 - "$archive" "$digest" <<'PY'
import hashlib
import sys

digest = hashlib.sha256()
with open(sys.argv[1], "rb") as archive:
    for chunk in iter(lambda: archive.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != sys.argv[2]:
    raise SystemExit("terminal-browser checksum mismatch; installation was not changed")
PY
    mkdir "$stage/app"
    tar -xzf "$archive" -C "$stage/app" --strip-components 1
    "$stage/app/bin/terminal-browser" --version
    "$stage/app/agent-browser/bin/agent-browser" --version
    mv "$stage/app" "$app"
else
    # Recover a missing launcher only when the existing distribution still runs.
    "$app/bin/terminal-browser" --version
    "$app/agent-browser/bin/agent-browser" --version
fi

cat > "$stage/terminal-browser" <<'SH'
#!/bin/sh
exec "$HOME/.local/share/terminal-browser/app/bin/terminal-browser" "$@"
SH
chmod 755 "$stage/terminal-browser"
mv "$stage/terminal-browser" "$launcher"
echo "Installed terminal-browser in $bin"
