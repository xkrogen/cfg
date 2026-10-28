# Unify cplt, agy, and cdx session wrappers and Ctrl-S fzf picker

## Outcome

- Unified coding agent wrappers in personal `cfg` (`c618b63`, pushed to `origin/main`):
  - Full names (`copilot`, `antigravity`, `codex`) run the native CLI without session-name wrapper behavior (`~/.local/bin/antigravity` forwards to the underlying `agy` binary).
  - Short names without suffix (`cplt`, `agy`, `cdx`): with no arguments, start a session without a name; with `<session-name> [options]`, resume the matching session if one exists or create a new named session if none exists (upsert).
  - `n` suffix (`cpltn`, `agyn`, `cdxn`): create a new named session, erroring if the name already exists.
  - `r` suffix (`cpltr`, `agyr`, `cdxr`): resume an existing named session by UUID, erroring if none exists or if the name is ambiguous.
- Added `~/.local/bin/agent-sessions` and wired `fzf-agent-session-widget` to `Ctrl-S` (`^S`, with `stty -ixon`) in `~/.zshrc`. Pressing `Ctrl-S` fuzzy-matches known session commands (`cplt <name>`, `agy <name>`, `cdx <name>`) from native metadata and executes the selected command immediately.
- Verified with 27 unit tests across `test_agy_named_sessions.py`, `test_codex_named_sessions.py`, and `test_copilot_named_sessions.py`, plus interactive zsh keybinding verification.
