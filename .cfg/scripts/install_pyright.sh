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
