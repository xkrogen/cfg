#!/usr/bin/env bash

git clone --bare org-132020694@github.com:linkedin-sandbox/ekrogen-cfg-overlay.git "$HOME/.cfg.li.git"

function cfgli {
   git --git-dir="$HOME/.cfg.li.git/" --work-tree="$HOME" "$@"
}

mkdir -p "$HOME/.cfg.li-bak"

if cfgli checkout; then
  echo "Checked out config.";
else
    echo ""
    echo "Checkout failed, backing up pre-existing dot files into ~/.cfg.li-bak ..."
    echo ""
    cfgli checkout 2>&1 \
        | grep -E "\s+\." \
        | sed -e 's/^[[:space:]]*//' \
        | tr '\n' '\0' \
        | xargs -0 sh -c 'for f do echo "Moving \"~/$f\" into ~/.cfg.li-bak/ ..."; if [[ "$f" =~ / ]]; then target_dir="$(dirname "$HOME/.cfg.li-bak/$f")"; mkdir -p "$target_dir"; else target_dir="$HOME/.cfg.li-bak/"; fi; mv "$HOME/$f" "$target_dir"; done' _
    echo ""
    echo "Attempting checkout again..."
    echo ""
    cfgli checkout
fi
cfgli config status.showUntrackedFiles no
