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

## Personal Codex setup

Personal Codex instructions and skills are versioned under `.cfg/codex/`:

- `AGENTS.md`: personal/work separation, agent-space as the default notes home,
  and the agent-managed no-PR Git workflow.
- `skills/wrap-up`: combined session closeout and handoff.
- `skills/coding-guidelines`: substantive personal code changes and review.
- `skills/disk-cleanup`: scoped local cleanup with authorization and verification.

The tracked `.codex/AGENTS.md` and three `.codex/skills/` entries are relative
symlinks to these sources, so a cfg checkout restores the personal setup. To repair
or recreate links, run:

```sh
python3 "$HOME/.cfg/scripts/install_codex_personal.py"
```

The installer honors `CODEX_HOME`, can target another directory with `--codex-home`,
and refuses conflicting existing files/links or an active global override. It does
not alter Copilot, shared agent skills, credentials, or other Codex settings.
Start a new Codex session to load the global instructions and newly installed skills.

No distill-knowledge, writing, or multi-model-comparison skill is installed.
Hindsight is a separate user investigation for memory curation, not an installed
dependency. General decisions/journals remain in agent-space and project-specific
records in the project repo; cfg owns the deployed instructions and skill sources.

Run installer regression checks with:

```sh
python3 -B -m unittest discover -s "$HOME/.cfg/codex/tests" -v
```
