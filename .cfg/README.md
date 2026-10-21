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
  make-pages-interactive, voice-transcription, skill-simplifier, and oss.
- `~/.codex/skills`: personal-only skills; `~/.copilot/skills`: work-only skills
  owned by cfgli/the work overlay. Shared implementations belong in personal cfg.
- `~/.cfg/dotfiles/.agents -> ../../.agents`,
  `~/.cfg/dotfiles/.codex -> ../../.codex`, and
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
generic enterprise boundaries. Voice transcription uses the existing executable
on PATH and local storage; this layout change does not relocate its helper,
recordings, authentication, ledger or transcripts. Interactive-page work conventions
remain in cfgli's `.copilot/skill-overlays`.

The former `install_codex_personal.py` and its link-installer tests were retired
when configuration moved to real runtime paths. General personal records remain
in agent-space; project-specific records stay in their project. No distill-knowledge,
writing, or multi-model-comparison skill was selected. Hindsight is a pending
user investigation.

## Named Codex and Antigravity sessions and Herdr

`codexn <session-name> [codex options]` creates a native named Codex session;
`codexr <session-name> [codex options]` resumes its exact UUID. Likewise,
`agyn <session-name> [agy options]` creates a named Antigravity CLI session and
`agyr <session-name> [agy options]` resumes its exact conversation UUID via
`agy --conversation <uuid>`. Names with spaces must be quoted. Existing names on
creation, and missing/ambiguous resume names, fail rather than silently choosing
another session. Native names come from each agent's own metadata (`session_index.jsonl`
for Codex; `annotations/*.pbtxt` and `conversation_summaries.db` for Antigravity).
Runtime state is not tracked; no transcript or credential is copied.

Real launchers live in `.local/bin`; the implementations are
`.codex/bin/named-session.py` and `.gemini/antigravity-cli/bin/named-session.py`.
No extra permission flags are added. The local Codex wrappers use the supported
stdio app-server create/name API then launch native resume; remote/worktree
startup uses native Codex instead. New Codex wrapper sessions require Codex's
app-server API.

Herdr's Ctrl+a, Shift+R binding invokes `.local/bin/herdr-resync-display-names`,
which dispatches to independent Copilot, Codex, and Antigravity refreshers.
Session names/UUIDs are reported automatically on wrapper launch; refresh picks up
native renames and recovers metadata after restarts using known native identities
or UUID argv. Copilot's existing work-owned refresher remains separate.

Run targeted regression checks with:

```sh
python3 -B -m unittest discover -s "$HOME/.cfg/tests" -p "test_*_named_sessions.py" -v
```
