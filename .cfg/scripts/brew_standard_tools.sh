#!/usr/bin/env bash

# Standard Homebrew formulae and casks. Source this file; it only defines
# functions. setup.sh and restore_rdev_brew.sh both use it so the package list
# has a single definition.
#
# On RDev pods /home/linuxbrew is overlayfs and disappears on pod recreation.
# Restoring Brew therefore runs only this phase, not the full setup.sh.

brew_install_list=(
    azure-cli
    bash
    bat
    cloc
    fd
    fzf
    gcc
    gh
    alltuner/tap/git-sprout
    googleworkspace-cli
    gradle-completion
    gron
    jenv
    pipx
    the_silver_searcher
    # Homebrew renamed the tldr client to tlrc (same `tldr` binary). An unknown
    # formula aborts the whole brew batch, so keep this name current.
    tlrc
    tree
    tmux
    worktrunk
    ripgrep
    walk
    wget
    ynqa/tap/jnv
    zsh
    zsh-autosuggestions
    zsh-syntax-highlighting
)

# Installs Homebrew only when `brew` is not on PATH. Callers that may find an
# existing Linuxbrew prefix outside PATH must export its shellenv first.
ensure_homebrew() {
    if command -v brew &>/dev/null; then
        return 0
    fi
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || return $?
    if [[ "$(uname)" != "Darwin" ]]; then
        eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"
    fi
}

# Returns nonzero when the formula batch or its completion-link cleanup fails.
# Completion pruning is non-fatal, matching the original setup.sh behavior.
brew_install_standard_formulas() {
    ensure_homebrew || return $?
    brew install "${brew_install_list[@]}" || return $?
    "$HOME/.cfg/scripts/prune_brew_completions.sh" || echo "WARN: pruning dangling brew zsh completions failed."
}

# Casks are skipped when their command already exists, either on PATH or as a
# user-local binary from the original installer. Returns nonzero if an
# attempted cask install fails.
brew_install_standard_casks() {
    local status=0
    export PATH="$(brew --prefix)/bin:$PATH"
    if ! command -v codex &>/dev/null && [ ! -x "$HOME/.local/bin/codex" ]; then
        brew install --cask codex || status=$?
    fi
    if ! command -v agy &>/dev/null && [ ! -x "$HOME/.local/bin/agy" ]; then
        brew install --cask antigravity-cli || status=$?
    fi
    return $status
}
