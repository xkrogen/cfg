# dotfiles
Dotfiles stored using the bare git repository setup.

See [this guide for more information](https://www.atlassian.com/git/tutorials/dotfiles).

`~/.cfg/scripts/setup.sh` installs Pyright through Volta, the latest stable
checksum-verified native px0 release into `~/.local/bin`, and jdtls through
Homebrew. Pyright's `~/.local/bin/pyright-langserver` launcher works from
non-login shells without a Homebrew-managed Node on PATH. Existing compatible
Volta Node defaults are preserved. Re-running setup updates these tools;
running `~/.cfg/scripts/install_px0.sh` or
`~/.cfg/scripts/install_pyright.sh` updates just one tool. The px0 installer
supports macOS and Linux on amd64/arm64 and replaces the binary only after
verifying the official release checksum.

Set `CFG_SKIP_JDTLS=1` when another setup layer provides Java language-server
configuration. `~/.cfg/scripts/install_jdtls.sh` separately installs the
checksum-verified jdtls 1.61.0 distribution under `~/.local/share/jdtls`
for a custom launcher; it does not configure a JVM. For the ordinary Homebrew
installation, use `brew upgrade jdtls` to update an existing installation.

Standard setup also installs the official terminal-browser v0.11.1 bundle into
`~/.local/share/terminal-browser`, with a launcher in `~/.local/bin`. Run
`~/.cfg/scripts/install_terminal_browser.sh` to install only this tool. Fresh
installs support macOS and Linux on x64/arm64 and verify the published archive
checksum and both bundled executables before publishing the installation.
Existing installations are left at their current version; upgrades are a
separate, explicit operation. The installer does not stop browser processes,
run terminal configuration, install system libraries, or require Node on PATH.

## Agent instruction and skill layout

cfg is a bare Git repository with `$HOME` as its worktree. Track actual files
where the tools read them; do not install agent configuration as symlinks into
`.cfg`. The bare checkout restores tracked files directly; no installer is needed.

- `~/.agents/AGENTS.md`: canonical shared personal global instruction file tracked
  in cfg, symlinked from `~/.codex/AGENTS.md` and `~/.gemini/AGENTS.md`.
- `~/.agents/skills`: real shared skill directories tracked in personal cfg,
  symlinked from `~/.gemini/config/skills` and `~/.gemini/antigravity-cli/skills`.
  Includes wrap-up, coding-guidelines, disk-cleanup, gh-stack, herdr,
  make-pages-interactive, transcription, skill-simplifier, and oss.
- `~/.codex/skills`: personal-only skills; `~/.copilot/skills`: work-only skills
  owned by cfgli/the work overlay. Shared implementations belong in personal cfg.
- `~/.cfg/dotfiles/.agents -> ../../.agents`,
  `~/.cfg/dotfiles/.codex -> ../../.codex`,
  `~/.cfg/dotfiles/.copilot -> ../../.copilot`, and
  `~/.cfg/dotfiles/.gemini -> ../../.gemini`: parent-directory browsing references,
  following the existing dotfiles convention. These links do not imply tracking
  every file in those runtime directories. Stage only intended configuration paths.

Sharing methods does not share work/personal data, accounts or authorization.
Credentials, transcripts, caches, indexes and runtime state stay outside Git.
No duplicate approved skills remain in Copilot/Codex-specific roots. The standalone
handoff and its combined behavior are removed; wrap-up only closes out docs,
session records and authorized Git work. Diagramming remains work-only; public-docs
was not selected for sharing.

OSS preserves xkrogen per-command authentication and personal-fork behavior with
generic enterprise boundaries. Interactive-page work conventions remain in cfgli's
`.copilot/skill-overlays`.

The `transcription` skill (`~/.agents/skills/transcription/SKILL.md`) is fully
on-device and uses FluidVoice only. Meeting questions use the bundled `fv-serve`
helper in `/Applications/FluidVoice.app/Contents/Helpers`, which requires FluidMeet
sharing to be enabled. Authorized local audio files are transcribed through
FluidVoice's loopback API at `http://127.0.0.1:47733/v1/transcribe`; enable it with
the `LocalAPIEnabled` preference. It does not require a separate transcription
helper on PATH. Raw transcripts and run artifacts stay under
`~/.local/state/transcription/`, outside Git.

The former `install_codex_personal.py` and its link-installer tests were retired
when configuration moved to real runtime paths. General personal records remain
in agent-space; project-specific records stay in their project. No distill-knowledge,
writing, or multi-model-comparison skill was selected. Hindsight is configured for shared personal memory; see below.

## Personal USPS integration

The machine-wide USPS skill lives at `~/.agents/skills/agent-mailbox/SKILL.md`.
Its portable commands use the locally installed release under `~/.local/lib/usps/current`
and private routing config `~/.config/usps/profiles/personal/hooks/codex-machine.json`.
The private config, credentials, and `~/.codex/hooks.json` are not tracked. Configure
the required USPS hooks locally without replacing existing Herdr hooks. Review and
trust their definitions through Codex's `/hooks` UI before use.

Delivery uses native queue with the verified Codex CLI 0.163.0-alpha.11 contract.
Only the USPS SessionStart binding hook remains; existing Herdr hooks are preserved.
The Mac hook is enabled/trusted and a real USPS message woke an idle Codex thread,
which read the exact message and recorded read_reported. The shared skill and private
routing config keep the same locations. Homelab also has the supported runtime and
native source; account sign-in is completed through its device-login flow. Its
repository owns daemon operational details (`docs/usps.md`).

## Codex configuration

`~/.codex/config.toml` and `~/.codex/hooks.json` are machine-local, ignored, and
not managed by cfg. Existing local files retain their notification, plugin,
runtime, permission, and hook settings. Configure these files on each machine;
cfg does not generate or synchronize them.

Shared instructions, skills, and named-session tooling remain tracked separately.
The personal USPS integration requires its private machine profile and locally
configured hooks; pulling cfg does not enable it.

## Named Copilot, Antigravity, and Codex sessions and Herdr

Full names (`copilot`, `antigravity`, `codex`) run the native CLI directly without
session-name wrapper behavior (`antigravity` forwards to the underlying `agy` binary).

Short names (`cplt`, `agy`, `cdx`) unify named session management across all three agents:

- `cplt`, `agy`, `cdx` (no suffix): with no arguments, starts a session without a name.
  With `<session-name> [options]`, resumes the matching session if one exists, or
  creates a new named session if none exists (upsert).
- `cpltn`, `agyn`, `cdxn` (`n` suffix): creates a new named
  session, failing if a session with that name already exists.
- `cpltr`, `agyr`, `cdxr` (`r` suffix): resumes an existing
  named session by exact UUID, failing if none exists or if the name is ambiguous.
- **Ctrl-S in zsh** (`fzf-agent-session-widget`, backed by `~/.local/bin/agent-sessions`):
  fuzzy-matches known session commands (`cplt <name>`, `agy <name>`, `cdx <name>`)
  from native agent metadata and executes the selected command.

Names with spaces must be quoted. Native names come from each agent's own metadata
(`~/.copilot/session-state/*/workspace.yaml` for Copilot; `annotations/*.pbtxt` and
`conversation_summaries.db` for Antigravity; `session_index.jsonl` for Codex).
Runtime state is not tracked; no transcript or credential is copied.

Full contracts: `.cfg/docs/named-sessions.md`. Real launchers and the unified helper live in `.local/bin`
(`.local/bin/named-session.py`). No extra permission flags are added. The local Codex
wrappers use the supported stdio app-server create/name API then launch native resume;
remote/worktree startup uses native Codex instead. New Codex wrapper sessions require
Codex's app-server API.

Herdr's Ctrl+a, Shift+R binding invokes `.local/bin/herdr-resync-display-names`,
which dispatches to independent Copilot, Codex, and Antigravity refreshers.
Session names/UUIDs are reported automatically on wrapper launch; refresh picks up
native renames and recovers metadata after restarts using known native identities
or UUID argv. Copilot's existing work-owned refresher remains separate.

Run targeted regression checks with:

```sh
python3 -B -m unittest discover -s "$HOME/.cfg/tests" -p "test_*_named_sessions.py" -v
```

## Shared Hindsight memory

`~/.agents/AGENTS.md` defines proactive recall and verified retention of curated
personal knowledge for Codex and Antigravity. `~/.agents/mcp_config.json` owns the
MCP JSON definition; `~/.gemini/config/mcp_config.json` links to it. Codex retains
its native TOML entry. Both use bank `xkrogen`; OAuth credentials remain separate
and untracked. No automatic transcript ingestion is installed.
