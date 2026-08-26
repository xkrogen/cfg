#!/usr/bin/env bash

# Install git-sprout and its PATH shim. Linux uses a local Cargo build because
# the upstream Homebrew bottle requires a newer glibc than our dev hosts.
set -euo pipefail

run_brew() {
    USER="$(id -un)" LOGNAME="$(id -un)" command brew "$@"
}

if ! command -v brew >/dev/null 2>&1; then
    echo "git-sprout setup requires Homebrew." >&2
    exit 1
fi

if ! run_brew list --versions git-sprout >/dev/null 2>&1; then
    run_brew install alltuner/tap/git-sprout
fi

if [ "$(uname)" = "Darwin" ]; then
    sprout_bin="$(command -v git-sprout)"
else
    brew_bin="$(run_brew --prefix)/bin"
    if [ ! -x "$brew_bin/cargo" ]; then
        run_brew install rust
    fi

    sprout_bin="$HOME/.local/bin/git-sprout"
    if [ ! -x "$sprout_bin" ]; then
        "$brew_bin/cargo" install git-sprout --version 0.1.0 --locked --root "$HOME/.local"
    fi
fi

shim_dir="$HOME/.local/bin"
shim="$shim_dir/git"
real_git="$(command -v git)"
if [ "$real_git" = "$shim" ]; then
    real_git="/usr/bin/git"
fi

mkdir -p "$shim_dir"
cat > "$shim" <<EOF
#!/bin/sh

if [ "\${GIT_SPROUT_BYPASS:-}" != 1 ] \\
    && [ "\${1:-}" = worktree ] \\
    && [ "\${2:-}" = add ]; then
    shift 2
    exec env GIT_SPROUT_BYPASS=1 "$sprout_bin" add "\$@"
fi

exec "$real_git" "\$@"
EOF
chmod 755 "$shim"
