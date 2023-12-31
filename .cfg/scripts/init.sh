#!/usr/bin/env bash

# Run the following command to initialize the dotfiles repo
# > sh -c "$(curl -fsSL https://raw.githubusercontent.com/xkrogen/cfg/master/.cfg/scripts/init.sh)"

git clone --bare git@github.com:xkrogen/cfg.git "$HOME/.cfg.git"

function cfg {
   git --git-dir="$HOME/.cfg.git/" --work-tree="$HOME" "$@"
}

mkdir -p "$HOME/.cfg-bak"

if cfg checkout; then
  echo "Checked out config.";
else
    echo ""
    echo "Checkout failed, backing up pre-existing dot files into ~/.cfg-bak ..."
    echo ""
    cfg checkout 2>&1 \
        | grep -E "\s+\." \
        | sed -e 's/^[[:space:]]*//' \
        | tr '\n' '\0' \
        | xargs -0 sh -c 'for f do echo "Moving \"~/$f\" into ~/.cfg-bak/ ..."; if [[ "$f" =~ / ]]; then target_dir="$(dirname "$HOME/.cfg-bak/$f")"; mkdir -p "$target_dir"; else target_dir="$HOME/.cfg-bak/"; fi; mv "$HOME/$f" "$target_dir"; done' _
    echo ""
    echo "Attempting checkout again..."
    echo ""
    cfg checkout
fi
cfg config status.showUntrackedFiles no
