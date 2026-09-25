"""Focused fixtures for the persistent code-tool installers."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from io import BytesIO


SCRIPTS = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cfg-code-tools-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.fixtures = self.root / "fixtures"
        self.fixtures.mkdir()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "PATH": f"{self.tools}:{os.environ['PATH']}",
                    "FIXTURE_ROOT": str(self.fixtures)}
        self.write_tool("curl", """#!/bin/sh
out=
next=
for arg do
    if [ "$next" = yes ]; then out=$arg; next=; continue; fi
    if [ "$arg" = -o ]; then next=yes; continue; fi
    url=$arg
done
name=${url##*/}
if [ "${FAIL_ASSET:-}" = "$name" ]; then echo 'fixture download failed' >&2; exit 22; fi
cp "$FIXTURE_ROOT/$name" "$out"
""")
        self.write_tool("uname", """#!/bin/sh
if [ "$1" = -s ]; then echo "${TEST_SYSTEM:-Darwin}"; else echo "${TEST_ARCH:-arm64}"; fi
""")

    def write_tool(self, name, content):
        path = self.tools / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self, name, *, ok=True):
        result = subprocess.run(["bash", str(SCRIPTS / name)], env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=30)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def release(self, version="0.1.10", platform="darwin-arm64", *, checksum=None, duplicate=False):
        asset = f"px0-{version}-{platform}"
        data = f"fixture {version} {platform}".encode()
        (self.fixtures / asset).write_bytes(data)
        (self.fixtures / "latest").write_text(json.dumps({
            "tag_name": "v" + version, "draft": False, "prerelease": False,
            "assets": [{"name": asset}, {"name": "checksums.txt"}],
        }))
        line = f"{checksum or hashlib.sha256(data).hexdigest()}  {asset}\n"
        (self.fixtures / "checksums.txt").write_text(line * (2 if duplicate else 1))
        return data

    def test_px0_platforms_updates_and_identical_noop(self):
        for system, arch, platform in (("Darwin", "arm64", "darwin-arm64"),
                                       ("Darwin", "x86_64", "darwin-amd64"),
                                       ("Linux", "x86_64", "linux-amd64"),
                                       ("Linux", "aarch64", "linux-arm64")):
            with self.subTest(platform=platform):
                self.env.update(TEST_SYSTEM=system, TEST_ARCH=arch)
                first = self.release(platform=platform)
                self.run_script("install_px0.sh")
                installed = self.home / ".local/bin/px0"
                self.assertEqual(installed.read_bytes(), first)
                inode = installed.stat().st_ino
                self.run_script("install_px0.sh")
                self.assertEqual(installed.stat().st_ino, inode)
                updated = self.release("0.1.11", platform)
                self.run_script("install_px0.sh")
                self.assertEqual(installed.read_bytes(), updated)

    def test_px0_failures_preserve_existing_binary(self):
        self.env.update(TEST_SYSTEM="Linux", TEST_ARCH="x86_64")
        self.release(platform="linux-amd64")
        self.run_script("install_px0.sh")
        installed = self.home / ".local/bin/px0"
        original = installed.read_bytes()
        for kind in ("unsupported", "download", "checksum", "missing", "duplicate"):
            with self.subTest(kind=kind):
                self.release(platform="linux-amd64")
                self.env.pop("FAIL_ASSET", None)
                if kind == "unsupported":
                    self.env["TEST_ARCH"] = "mips"
                elif kind == "download":
                    self.env["FAIL_ASSET"] = "px0-0.1.10-linux-amd64"
                elif kind == "checksum":
                    (self.fixtures / "checksums.txt").write_text("0" * 64 + "  px0-0.1.10-linux-amd64\n")
                elif kind == "missing":
                    (self.fixtures / "checksums.txt").write_text("")
                elif kind == "duplicate":
                    self.release(platform="linux-amd64", duplicate=True)
                self.run_script("install_px0.sh", ok=False)
                self.assertEqual(installed.read_bytes(), original)
                self.env["TEST_ARCH"] = "x86_64"
        self.assertFalse(list((self.home / ".local/bin").glob(".px0-*")))

    def test_pyright_default_cached_only_and_launcher(self):
        volta = self.home / ".volta/bin/volta"
        volta.parent.mkdir(parents=True)
        self.write_tool("volta-shim", "#!/bin/sh\n")
        (volta.parent / "node").symlink_to(self.tools / "volta-shim")
        volta.write_text("""#!/bin/sh
case "$1 $2" in
  "list node") printf '%s\\n' "$NODE_LIST" ;;
  "list pyright") if [ -e "$HOME/.volta/installed" ]; then echo 'package pyright@1.1.414 / pyright, pyright-langserver / node@16.19.0 npm@built-in (default)'; fi ;;
  "install node@22") touch "$HOME/.volta/node-installed" ;;
  "install pyright") touch "$HOME/.volta/installed"; ln -sf "$HOME/.volta/bin/volta-shim" "$HOME/.volta/bin/pyright-langserver" ;;
  "run pyright-langserver") shift 2; printf 'cwd=%s args=%s stdin=' "$PWD" "$*"; cat ;;
  *) exit 2 ;;
esac
""")
        volta.chmod(0o755)
        self.env["NODE_LIST"] = "runtime node@16.19.0 (default)\nruntime node@22.21.0"
        self.run_script("install_pyright.sh")
        self.assertFalse((self.home / ".volta/node-installed").exists())
        self.assertTrue((volta.parent / "volta-shim").is_file())
        launcher = self.home / ".local/bin/pyright-langserver"
        result = subprocess.run([str(launcher), "--stdio", "extra"], input="payload", env=self.env,
                                cwd=self.fixtures, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"cwd={self.fixtures.resolve()} args=--stdio extra stdin=payload")
        self.env["NODE_LIST"] = "runtime node@22.21.0"
        (volta.parent / "volta-shim").unlink()
        self.run_script("install_pyright.sh")
        self.assertTrue((self.home / ".volta/node-installed").exists())
        self.env["NODE_LIST"] = "runtime node@12.22.0 (default)"
        self.assertIn("Node >=14", self.run_script("install_pyright.sh", ok=False).stderr)
        self.assertTrue(launcher.is_file())
        (self.home / ".volta/installed").unlink()
        result = subprocess.run([str(launcher), "--stdio"], env=self.env, cwd=self.fixtures,
                                capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Pyright is missing", result.stderr)

    def test_system_volta_migrator_and_shim_become_persistent(self):
        self.write_tool("volta", """#!/bin/sh
case "$1 $2" in
  "list node") echo 'runtime node@20.19.1 (default)' ;;
  "list pyright") echo 'package pyright@1.1.414 / pyright-langserver (default)' ;;
  "install pyright") ln -s "$HOME/.volta/bin/volta-shim" "$HOME/.volta/bin/pyright-langserver" ;;
  *) exit 2 ;;
esac
""")
        self.write_tool("volta-shim", "#!/bin/sh\n")
        self.write_tool("volta-migrate", "#!/bin/sh\n")
        self.run_script("install_pyright.sh")
        for name in ("volta", "volta-shim", "volta-migrate"):
            self.assertTrue((self.home / ".volta/bin" / name).is_file())

    def test_jdtls_complete_reuse_and_bad_archive_preserves(self):
        dest = self.home / ".local/share/jdtls/1.61.0"
        (dest / "bin").mkdir(parents=True)
        (dest / "plugins").mkdir()
        (dest / "bin/jdtls").write_text("working")
        (dest / "bin/jdtls").chmod(0o755)
        (dest / "plugins/org.eclipse.equinox.launcher_1.jar").touch()
        self.assertIn("already installed", self.run_script("install_jdtls.sh").stdout)
        self.assertEqual((dest / "bin/jdtls").read_text(), "working")
        (dest / "plugins/org.eclipse.equinox.launcher_1.jar").unlink()
        (self.fixtures / "jdt-language-server-1.61.0-202609031315.tar.gz").write_bytes(b"bad archive")
        self.assertIn("checksum mismatch", self.run_script("install_jdtls.sh", ok=False).stderr)
        self.assertEqual((dest / "bin/jdtls").read_text(), "working")

    def test_jdtls_fresh_publish_and_repeat(self):
        archive = self.fixtures / "jdt-language-server-1.61.0-202609031315.tar.gz"
        with tarfile.open(archive, "w:gz") as output:
            for name, data, mode in (("bin/jdtls", b"#!/bin/sh\n", 0o755),
                                     ("plugins/org.eclipse.equinox.launcher_1.jar", b"jar", 0o644)):
                entry = tarfile.TarInfo(name)
                entry.size = len(data)
                entry.mode = mode
                output.addfile(entry, BytesIO(data))
        # Only the checksum verifier is stubbed here; the bad-digest case
        # above invokes the real verifier, and the real archive is checked
        # against its published digest during the installation smoke.
        self.write_tool("python3", "#!/bin/sh\nexit 0\n")
        self.run_script("install_jdtls.sh")
        jdtls = self.home / ".local/share/jdtls/1.61.0/bin/jdtls"
        self.assertTrue(jdtls.is_file())
        inode = jdtls.stat().st_ino
        self.run_script("install_jdtls.sh")
        self.assertEqual(jdtls.stat().st_ino, inode)

    def browser_archive(self, platform, *, broken_controller=False):
        archive = self.fixtures / f"terminal-browser-{platform}.tar.gz"
        with tarfile.open(archive, "w:gz") as output:
            for name, data in (
                ("bin/terminal-browser", b"#!/bin/sh\nprintf '<%s>\\n' \"$@\"\n"),
                ("agent-browser/bin/agent-browser",
                 b"#!/bin/sh\nexit 23\n" if broken_controller else b"#!/bin/sh\nexit 0\n"),
            ):
                entry = tarfile.TarInfo("terminal-browser/" + name)
                entry.size = len(data)
                entry.mode = 0o755
                output.addfile(entry, BytesIO(data))

    def test_terminal_browser_platforms_repeat_and_launcher_recovery(self):
        # As in the jdtls fixture, only the positive digest check is stubbed.
        # The mismatch test uses the real verifier; the official Linux bundle
        # is also exercised independently before publishing the installer.
        self.write_tool("python3", "#!/bin/sh\nexit 0\n")
        for system, arch, platform in (("Darwin", "arm64", "darwin-arm64"),
                                       ("Darwin", "x86_64", "darwin-x64"),
                                       ("Linux", "x86_64", "linux-x64"),
                                       ("Linux", "aarch64", "linux-arm64")):
            with self.subTest(platform=platform):
                home = self.home / platform
                home.mkdir()
                self.env.update(HOME=str(home), TEST_SYSTEM=system, TEST_ARCH=arch)
                self.browser_archive(platform)
                self.run_script("install_terminal_browser.sh")
                app = home / ".local/share/terminal-browser/app"
                launcher = home / ".local/bin/terminal-browser"
                inode = (app / "bin/terminal-browser").stat().st_ino
                result = subprocess.run([str(launcher), "argument with spaces", "--json"],
                                        env=self.env, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "<argument with spaces>\n<--json>\n")
                self.env["FAIL_ASSET"] = f"terminal-browser-{platform}.tar.gz"
                self.run_script("install_terminal_browser.sh")
                launcher.unlink()
                self.run_script("install_terminal_browser.sh")
                self.assertTrue(launcher.is_file())
                self.assertEqual((app / "bin/terminal-browser").stat().st_ino, inode)
                self.assertFalse(list(app.parent.glob(".terminal-browser.*")))
                self.env.pop("FAIL_ASSET")

    def test_terminal_browser_rejects_bad_downloads_and_unsupported_platforms(self):
        self.env.update(TEST_SYSTEM="Linux", TEST_ARCH="x86_64")
        self.browser_archive("linux-x64")
        self.assertIn("checksum mismatch",
                      self.run_script("install_terminal_browser.sh", ok=False).stderr)
        self.env["FAIL_ASSET"] = "terminal-browser-linux-x64.tar.gz"
        self.assertIn("fixture download failed",
                      self.run_script("install_terminal_browser.sh", ok=False).stderr)
        self.env["TEST_ARCH"] = "mips"
        self.assertIn("Unsupported terminal-browser platform",
                      self.run_script("install_terminal_browser.sh", ok=False).stderr)
        self.assertFalse((self.home / ".local/bin/terminal-browser").exists())
        self.assertFalse(list((self.home / ".local/share/terminal-browser").iterdir()))

    def test_terminal_browser_checks_controller_before_publishing(self):
        self.write_tool("python3", "#!/bin/sh\nexit 0\n")
        self.env.update(TEST_SYSTEM="Linux", TEST_ARCH="x86_64")
        self.browser_archive("linux-x64", broken_controller=True)
        result = self.run_script("install_terminal_browser.sh", ok=False)
        self.assertEqual(result.returncode, 23)
        self.assertFalse((self.home / ".local/bin/terminal-browser").exists())
        self.assertFalse((self.home / ".local/share/terminal-browser/app").exists())
        self.assertFalse(list((self.home / ".local/share/terminal-browser").iterdir()))

    def test_setup_propagates_required_jdtls_failure_without_changing_other_brew_failures(self):
        scripts = self.home / ".cfg/scripts"
        scripts.mkdir(parents=True)
        (scripts / "setup.sh").write_text((SCRIPTS / "setup.sh").read_text())
        for name in ("install_git_sprout.sh", "install_pyright.sh",
                     "install_herdr_skill.sh", "install_px0.sh", "install_terminal_browser.sh"):
            installer = scripts / name
            installer.write_text(f'#!/bin/sh\necho {name} >> "$FIXTURE_ROOT/installers"\n'
                                 f'if [ "${{FAIL_INSTALLER:-}}" = "{name}" ]; then exit 29; fi\n')
            installer.chmod(0o755)
        for directory in (".oh-my-zsh", ".tmux/plugins/tpm", ".local/bin"):
            (self.home / directory).mkdir(parents=True)
        (self.home / ".local/bin/herdr").touch(mode=0o755)
        prefix = self.fixtures / "prefix/opt/fzf"
        prefix.mkdir(parents=True)
        fzf_install = prefix / "install"
        fzf_install.write_text("#!/bin/sh\nexit 0\n")
        fzf_install.chmod(0o755)
        self.write_tool("volta", "#!/bin/sh\nexit 0\n")
        self.write_tool("jenv", "#!/bin/sh\nexit 0\n")
        self.write_tool("git", "#!/bin/sh\nexit 0\n")
        self.write_tool("brew", """#!/bin/sh
if [ "$1" = --prefix ]; then echo "$FIXTURE_ROOT/prefix"; exit 0; fi
echo "$*" >> "$FIXTURE_ROOT/brew_calls"
if [ "$1" = install ]; then
    case " $* " in *" jdtls "*) [ "${FAIL_JDTLS:-0}" != 1 ] || exit 17 ;; esac
    if [ "$#" -gt 2 ] && [ "${FAIL_BULK:-0}" = 1 ]; then exit 19; fi
fi
""")

        def run_setup(**overrides):
            result = subprocess.run(["bash", str(scripts / "setup.sh")],
                                    env={**self.env, **overrides}, cwd=self.home,
                                    capture_output=True, text=True, timeout=30)
            calls = (self.fixtures / "brew_calls").read_text().splitlines()
            (self.fixtures / "brew_calls").unlink()
            return result, calls

        failed, calls = run_setup(FAIL_JDTLS="1")
        self.assertEqual(failed.returncode, 17, failed.stdout + failed.stderr)
        self.assertTrue(any("jdtls" in call for call in calls))
        self.assertNotIn("Upon first time running tmux", failed.stdout)

        skipped, calls = run_setup(FAIL_JDTLS="1", CFG_SKIP_JDTLS="1")
        self.assertEqual(skipped.returncode, 0, skipped.stdout + skipped.stderr)
        self.assertFalse(any("jdtls" in call for call in calls))
        self.assertIn("install_pyright.sh", (self.fixtures / "installers").read_text())
        self.assertIn("install_px0.sh", (self.fixtures / "installers").read_text())
        self.assertIn("install_terminal_browser.sh", (self.fixtures / "installers").read_text())

        browser_failed, _ = run_setup(FAIL_INSTALLER="install_terminal_browser.sh")
        self.assertEqual(browser_failed.returncode, 29, browser_failed.stdout + browser_failed.stderr)
        self.assertNotIn("Upon first time running tmux", browser_failed.stdout)

        best_effort, calls = run_setup(FAIL_BULK="1")
        self.assertEqual(best_effort.returncode, 0, best_effort.stdout + best_effort.stderr)
        self.assertTrue(any("jdtls" in call for call in calls))


if __name__ == "__main__":
    unittest.main()
