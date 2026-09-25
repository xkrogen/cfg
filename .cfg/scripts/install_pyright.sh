#!/usr/bin/env bash
# Install Pyright with Volta and expose its LSP to non-login processes.
set -euo pipefail

volta="$HOME/.volta/bin/volta"
if [ ! -x "$volta" ]; then
    source=$(command -v volta || :)
    if [ -z "$source" ]; then
        echo "Volta is required; run ~/.cfg/scripts/setup.sh first" >&2
        exit 1
    fi
    mkdir -p "$HOME/.volta/bin"
    install -m 755 "$source" "$volta"
    migrator="$(dirname "$source")/volta-migrate"
    if [ -x "$migrator" ] && [ ! -x "$HOME/.volta/bin/volta-migrate" ]; then
        install -m 755 "$migrator" "$HOME/.volta/bin/volta-migrate"
    fi
fi

# Volta's package shims point into its home. A system-provided Volta can
# create those links without placing the shim executable on persistent storage.
if [ ! -x "$HOME/.volta/bin/volta-shim" ]; then
    shim=$(command -v volta-shim || :)
    if [ -z "$shim" ] && [ -L "$HOME/.volta/bin/node" ]; then
        shim=$(readlink "$HOME/.volta/bin/node")
    fi
    if [ ! -x "$shim" ]; then
        echo "Volta shim is missing; run ~/.cfg/scripts/setup.sh first" >&2
        exit 1
    fi
    install -m 755 "$shim" "$HOME/.volta/bin/volta-shim"
fi

# Query defaults from HOME: a project's volta pin is not the global default.
nodes=$(cd "$HOME" && "$volta" list node --format plain)
if [[ "$nodes" =~ node@([0-9]+)(\.[0-9]+)*[[:space:]]+\(default\) ]]; then
    if (( ${BASH_REMATCH[1]} < 14 )); then
        echo "Pyright requires Node >=14; update the existing Volta default explicitly" >&2
        exit 1
    fi
else
    "$volta" install node@22
fi

"$volta" install pyright
if ! (cd "$HOME" && "$volta" list pyright --format plain) | grep -q '^package pyright@' \
    || [ ! -x "$HOME/.volta/bin/pyright-langserver" ]; then
    echo "Volta did not install the Pyright language-server package" >&2
    exit 1
fi

mkdir -p "$HOME/.local/bin"
launcher=$(mktemp "$HOME/.local/bin/.pyright-langserver.XXXXXXXX")
trap 'rm -f -- "$launcher"' EXIT
cat > "$launcher" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
volta="$HOME/.volta/bin/volta"
if [ ! -x "$volta" ] || [ ! -x "$HOME/.volta/bin/pyright-langserver" ] \
    || ! (cd "$HOME" && "$volta" list pyright --format plain) | grep -q '^package pyright@'; then
    echo "Pyright is missing; run ~/.cfg/scripts/install_pyright.sh" >&2
    exit 1
fi
exec "$volta" run pyright-langserver "$@"
SH
chmod 755 "$launcher"
mv -f "$launcher" "$HOME/.local/bin/pyright-langserver"
echo "Installed Pyright and ~/.local/bin/pyright-langserver"
