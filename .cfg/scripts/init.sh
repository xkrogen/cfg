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
    echo "Backing up pre-existing dot files into $HOME/.cfg-bak"
    cfg checkout 2>&1 \
        | grep -E "\s+\." \
        | sed -e 's/^[[:space:]]*//' \
        | tr '\n' '\0' \
        | xargs -0 sh -c 'for f do echo "Moving \"$HOME/$f\" into \"$HOME/.cfg-bak/\" ..."; if [[ "$f" =~ / ]]; then mkdir -p "$(dirname "$HOME/$f")"; fi; echo "mv $f $HOME/.cfg-bak/"; done' _
fi
cfg checkout
cfg config status.showUntrackedFiles no
