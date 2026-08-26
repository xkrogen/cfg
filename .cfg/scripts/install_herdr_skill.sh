#!/usr/bin/env bash

# The skills CLI requires Node 22.20+, while rdevs retain Node 20 as default.
set -euo pipefail

if [ -f "$HOME/.agents/skills/herdr/SKILL.md" ]; then
    exit 0
fi

if [ -x "$HOME/.volta/bin/volta" ]; then
    "$HOME/.volta/bin/volta" install node@22
    "$HOME/.volta/bin/volta" run --node 22 npx --yes skills add herdrdev/herdr --skill herdr -g -y
    exit 0
fi

node_major="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$node_major" -lt 22 ]; then
    USER="$(id -un)" LOGNAME="$(id -un)" command brew install node
    export PATH="$(brew --prefix)/bin:$PATH"
fi

npx --yes skills add herdrdev/herdr --skill herdr -g -y
