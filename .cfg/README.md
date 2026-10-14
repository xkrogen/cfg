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

- `~/.agents/skills`: shared generic skills, versioned in personal cfg under
  `.cfg/agents/skills`. Includes wrap-up, coding-guidelines, disk-cleanup, gh-stack,
  make-pages-interactive, voice-transcription, skill-simplifier, and oss.
- `~/.copilot/skills`: work-specific skills, owned by cfgli/the work overlay.
- `~/.codex/skills`: personal-only skills, owned by personal cfg.
- `~/.codex/AGENTS.md`: personal global instructions sourced from `.cfg/codex/AGENTS.md`.

Tracked relative symlinks deploy the global Codex file and shared skill directories.
There are no duplicate installations of the shared skills in the Copilot or
Codex-specific roots. Sharing methods does not share work/personal data or accounts;
see `.cfg/agents/README.md`.

To recreate or repair links:

```sh
python3 "$HOME/.cfg/scripts/install_codex_personal.py"
```

The installer honors CODEX_HOME, supports `--codex-home` and `--skills-home` for
isolated/custom targets, and refuses conflicting files, links, or an active Codex
AGENTS.override.md. It migrates only recognized formerly managed Codex skill links;
it never deletes arbitrary work/personal skill directories. Copilot-copy removal
is separately tracked in the work overlay. Reload skills/start a new agent session
as needed for discovery.

No distill-knowledge, writing, or multi-model-comparison skill was installed.
Hindsight is a pending user investigation. General personal records remain in
agent-space and project-specific records with their project; cfg owns deployed
instructions and shared/personal skill sources.

Installer regression checks:

```sh
python3 -B -m unittest discover -s "$HOME/.cfg/codex/tests" -v
```
