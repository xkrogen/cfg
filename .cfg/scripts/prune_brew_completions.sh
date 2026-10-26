#!/usr/bin/env bash

# Removes dangling zsh completion links from Homebrew's site-functions. When two
# brew installs race for the same bottle, one can link a completion into a Cellar
# keg that was never moved in; compinit then reports the broken link on every
# login shell. Only links whose targets are missing are removed.

set -euo pipefail

site_functions="$(brew --prefix)/share/zsh/site-functions"
[ -d "$site_functions" ] || exit 0

find "$site_functions" -maxdepth 1 -type l ! -exec test -e {} \; -print -exec rm -f -- {} \;
