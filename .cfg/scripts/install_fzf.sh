#!/usr/bin/env bash
# Install the latest official, checksum-verified fzf release into ~/.local/bin.
#
# fzf is a standalone binary, so it lives under $HOME and survives rdev pod
# recreation, unlike Homebrew under /home/linuxbrew. Shell integration comes from
# `fzf --zsh` (fzf >= 0.48), which the oh-my-zsh fzf plugin uses whenever fzf is
# on PATH, so no separate install directory or FZF_BASE is required.
set -euo pipefail

case "$(uname -s):$(uname -m)" in
    Darwin:x86_64) platform=darwin_amd64 ;;
    Darwin:arm64) platform=darwin_arm64 ;;
    Linux:x86_64) platform=linux_amd64 ;;
    Linux:aarch64|Linux:arm64) platform=linux_arm64 ;;
    *) echo "Unsupported fzf platform: $(uname -s)/$(uname -m)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null || { echo "fzf installation requires Python 3" >&2; exit 1; }
command -v curl >/dev/null || { echo "fzf installation requires curl" >&2; exit 1; }
command -v tar >/dev/null || { echo "fzf installation requires tar" >&2; exit 1; }
bin="$HOME/.local/bin"
mkdir -p "$bin"
release=$(mktemp "$bin/.fzf-release.XXXXXXXX")
download=$(mktemp "$bin/.fzf-download.XXXXXXXX")
candidate=$(mktemp "$bin/.fzf-binary.XXXXXXXX")
trap 'rm -f -- "$release" "$download" "$candidate"' EXIT

# The GitHub release metadata carries each asset's SHA-256 digest, so no separate
# checksums file is needed. An installed binary is kept when the shared,
# unauthenticated API quota is exhausted; a missing binary still fails.
if ! curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 45 \
    https://api.github.com/repos/junegunn/fzf/releases/latest -o "$release"; then
    if [ -x "$bin/fzf" ]; then
        echo "WARN: could not query the latest fzf release; keeping the installed fzf." >&2
        exit 0
    fi
    echo "ERROR: could not query the latest fzf release and fzf is not installed." >&2
    exit 1
fi
read -r version asset digest < <(python3 - "$release" "$platform" <<'PY'
import json
import re
import sys

release = json.load(open(sys.argv[1]))
tag = release["tag_name"]
if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or release.get("prerelease") or release.get("draft"):
    raise SystemExit("Invalid latest stable fzf release")
asset = f"fzf-{tag[1:]}-{sys.argv[2]}.tar.gz"
matches = [item for item in release["assets"] if item["name"] == asset]
digest = (matches[0].get("digest") or "") if len(matches) == 1 else ""
if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
    raise SystemExit(f"Missing official fzf asset or SHA-256 digest for {tag}")
print(tag[1:], asset, digest[len("sha256:"):])
PY
)
url="https://github.com/junegunn/fzf/releases/download/v$version/$asset"
curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 180 "$url" -o "$download"
python3 - "$download" "$digest" <<'PY'
import hashlib
import sys

with open(sys.argv[1], "rb") as archive:
    actual = hashlib.sha256(archive.read()).hexdigest()
if actual != sys.argv[2]:
    raise SystemExit("fzf checksum mismatch; installed binary is unchanged")
PY

tar -xzOf "$download" fzf >"$candidate"
chmod 755 "$candidate"
# Reject releases too old for `fzf --zsh` before replacing a working binary.
"$candidate" --zsh >/dev/null

if [ -f "$bin/fzf" ] && cmp -s "$candidate" "$bin/fzf"; then
    echo "fzf $version already installed"
else
    mv -f "$candidate" "$bin/fzf"
    echo "Installed fzf $version in $bin"
fi
