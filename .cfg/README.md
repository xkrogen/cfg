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

- `~/.agents/skills`: real shared skill directories tracked in personal cfg.
  Includes wrap-up, coding-guidelines, disk-cleanup, gh-stack,
  make-pages-interactive, voice-transcription, skill-simplifier, and oss.
- `~/.codex/AGENTS.md`: real personal global instruction file tracked in cfg.
- `~/.codex/skills`: personal-only skills; `~/.copilot/skills`: work-only skills
  owned by cfgli/the work overlay. Shared implementations belong in personal cfg.
- `~/.cfg/dotfiles/.agents -> ../../.agents` and
  `~/.cfg/dotfiles/.codex -> ../../.codex`: parent-directory browsing references,
  following the existing dotfiles convention. These links do not imply tracking
  every file in either runtime directory. Stage only intended configuration paths.

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
