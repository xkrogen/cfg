# Unified named agent sessions (`cplt`, `agy`, `cdx`) and Herdr labels

Full names (`copilot`, `antigravity`, `codex`) run the native CLI without session-name
wrapper behavior (`antigravity` forwards to the underlying `agy` binary).

Short names (`cplt`, `agy`, `cdx`) provide unified named session commands in `~/.local/bin`:

```sh
# Upsert (no suffix): no arg starts unnamed; with <name>, resumes if exists else creates
cplt [session-name] [options]
agy [session-name] [options]
cdx [session-name] [options]

# Create new ('n' suffix): fails if <session-name> already exists
cpltn <session-name> [options]
agyn <session-name> [options]
cdxn <session-name> [options]

# Resume existing ('r' suffix): fails if <session-name> does not exist or is ambiguous
cpltr <session-name> [options]
agyr <session-name> [options]
cdxr <session-name> [options]
```

In interactive zsh, **Ctrl-S** invokes `fzf-agent-session-widget` (backed by
`~/.local/bin/agent-sessions`), which lists known sessions as `cplt <name>`,
`agy <name>`, and `cdx <name>` from native metadata (not shell history) and
immediately runs the fuzzy-matched selection.

## Native storage and implementation

Real tracked launchers live in `~/.local/bin/`; the helpers are
`~/.copilot/bin/named-session.py`, `~/.gemini/antigravity-cli/bin/named-session.py`,
and `~/.codex/bin/named-session.py`, all owned by personal bare cfg.
There are no runtime-to-cfg symlinks.

- **Copilot (`cplt*`)** reads `~/.copilot/session-state/<uuid>/workspace.yaml` (`COPILOT_HOME`).
- **Antigravity (`agy*`)** reads `~/.gemini/antigravity-cli/annotations/*.pbtxt` and
  `conversation_summaries.db` (`AGY_HOME`), resolving the underlying `agy` binary outside
  `~/.local/bin` so `~/.local/bin/agy` can serve as the short upsert wrapper.
- **Codex (`cdx*`)** reads `~/.codex/session_index.jsonl` (`CODEX_HOME`). New sessions
  use the supported stdio app-server methods `thread/start` and `thread/name/set`,
  then exec `codex resume <UUID>`. No `turn/start` or fabricated prompt is submitted.
  See [official app-server documentation](https://learn.chatgpt.com/docs/app-server).

No transcript/credential/database content is copied across agents. An advisory
`named-session.lock` serializes creation through the wrappers.

## Herdr integration

The built-in Codex Herdr integration is installed/current (v10 on Herdr 0.9.5).
Wrappers wait briefly in a detached helper for Herdr to recognize the foreground
Codex process, then report the native UUID and user display name to that exact
pane. Outside Herdr they simply open the native session.

**Ctrl+a, Shift+R** runs `~/.local/bin/herdr-resync-display-names`. It dispatches to
Copilot's existing work-owned refresher and the separate Codex metadata reader.
The two readers retain separate storage/context. The shared dispatcher does not
import or index either agent's transcripts. The keybinding was updated in both
cfg and cfgli because both already track the Herdr config file.

Codex refresh uses exact native UUIDs from Herdr, with recovery from live
`codex resume <UUID>` argv if ephemeral metadata was lost. It never matches by pane
title, working directory or another agent's names. Native `/rename` changes are
picked up on refresh; missing names clear stale wrapper display metadata. This also
repairs labels after a Herdr restart without relying on a new model turn.

The existing live config was reloaded successfully with no diagnostics. Other
pending UI/notification edits in that config were preserved and excluded from
these scoped commits. Existing Copilot wrapper/hooks were not modified.

## Verification

Ten automated tests passed: native create/name protocol and argument preservation,
resume/rename resolution, duplicate/missing/ambiguous failures, partial index tails,
Codex-only metadata routing, empty-success Herdr replies, exact process-UUID recovery,
help/no-argument behavior and selector rejection. Shell launchers passed syntax checks.

A disposable live Herdr pane verified real session creation, UUID resume, automatic
display-name reporting, native rename and the combined refresh dispatcher. No model
prompt ran. An initial agent-space launch displayed normal folder trust; no trust
approval was submitted by the agent. The resume/display test completed in the
existing homelab context. Only the test panes were closed, and the exact empty test
session was deleted with native `codex delete --force <test-UUID>` afterward.

Implementation committed and pushed: personal cfg `ada344d` (origin/main), and
existing work-overlay keybinding pointer `8fb688e` (origin/master). Agent-space
records are now pushed to its private origin/master; see the repository map.

Legacy panes started before the wrappers may lack both native identity reports and
UUID resume argv (for example, `codex "/rename mbox-init"`). Refresh intentionally
skips those rather than guessing. Associate a user-identified session once using
verified native metadata, or exit and resume with `cdxr NAME`. The running
mbox-init pane was repaired this way; no restart was necessary. On a future Herdr
restart, UUID argv from wrapper launches is the reliable recovery path.
