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
