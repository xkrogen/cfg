#!/usr/bin/env bash
# Install the official pinned jdtls distribution without selecting a JVM.
set -euo pipefail

version=1.61.0
archive_name=jdt-language-server-1.61.0-202609031315.tar.gz
digest=338e7e73d61836651ba2453919a0d34fa763eb4e7c03342092309bffb8934c64
base="$HOME/.local/share/jdtls"
dest="$base/$version"
complete() {
    [ -x "$1/bin/jdtls" ] && compgen -G "$1/plugins/org.eclipse.equinox.launcher_*.jar" >/dev/null
}
if complete "$dest"; then
    echo "jdtls $version already installed"
    exit 0
fi

mkdir -p "$base"
stage=$(mktemp -d "$base/.jdtls.XXXXXXXX")
archive=$(mktemp "$base/.jdtls-archive.XXXXXXXX")
backup=
cleanup() {
    rm -f -- "$archive"
    if [ -d "$stage" ]; then rm -r -- "$stage"; fi
}
trap cleanup EXIT
curl --http1.1 -fsSL --retry 2 --connect-timeout 15 --max-time 300 \
    "https://download.eclipse.org/jdtls/milestones/$version/$archive_name" -o "$archive"
python3 - "$archive" "$digest" <<'PY'
import hashlib
import sys

digest = hashlib.sha256()
with open(sys.argv[1], "rb") as archive:
    for chunk in iter(lambda: archive.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != sys.argv[2]:
    raise SystemExit("jdtls checksum mismatch; installed distribution is unchanged")
PY
tar -xzf "$archive" -C "$stage"
complete "$stage" || { echo "Incomplete official jdtls distribution" >&2; exit 1; }
if [ -e "$dest" ]; then
    backup=$(mktemp -d "$base/.jdtls-old.XXXXXXXX")
    rmdir "$backup"
    mv "$dest" "$backup"
fi
if ! mv "$stage" "$dest"; then
    if [ -n "$backup" ]; then mv "$backup" "$dest"; fi
    echo "Failed to publish jdtls distribution" >&2
    exit 1
fi
if [ -n "$backup" ]; then rm -r -- "$backup"; fi
echo "Installed jdtls $version in $dest"
