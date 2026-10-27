# Homelab cfg bootstrap and shell command fix

- Restored cfg on Ubuntu homelab as ~/.cfg.git with $HOME worktree; retained legacy main. Ran cfg setup after Ubuntu build-essential, official Linux agy, and Herdr installation.
- Found .bash_profile unconditionally execs zsh even in noninteractive bash -lc, discarding the requested agent command. Added interactive-shell guard. Verified bash -lc command prints the expected marker on homelab.
- Host-specific setup, authentication, hooks and Hindsight verification belong to homelab docs/agents.md and journal/sessions/2026-10-26-homelab-agents.md.
