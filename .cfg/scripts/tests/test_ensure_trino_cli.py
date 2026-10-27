"""Behavior tests for ensure_trino_cli.sh with stubbed sudo and binary dirs."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
TRINO_OK = "#!/bin/sh\nexit 0\n"
TRINO_BROKEN = "#!/bin/sh\nexit 1\n"


class EnsureTrinoCliTests(unittest.TestCase):
    """Runs the real script. Scratch files live under tests/.work, not /tmp."""

    def setUp(self):
        self.root = SCRIPTS / "tests" / ".work" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = self.root / "home"
        self.home.mkdir(parents=True)
        self.canonical = self.root / "canonical"
        self.shim_dir = self.root / "shim"
        self.shim_dir.mkdir(parents=True)
        self.calls = self.root / "sudo-calls.log"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.write(self.bin_dir / "sudo", self.sudo_stub(), executable=True)

    def sudo_stub(self):
        # Installs a working trino into the canonical dir only when FAKE_INSTALL=1.
        return (
            "#!/bin/sh\n"
            f'echo "$@" >> "{self.calls}"\n'
            'case "$*" in *LNKD-trino-cli*) ;; *) exit 1 ;; esac\n'
            'if [ "${FAKE_INSTALL:-0}" = 1 ]; then\n'
            f'  mkdir -p "{self.canonical}"\n'
            f'  printf \'{TRINO_OK}\' > "{self.canonical}/trino"\n'
            f'  chmod +x "{self.canonical}/trino"\n'
            "fi\n"
            'exit "${SUDO_RC:-0}"\n'
        )

    def write(self, path, text, executable=False):
        path.write_text(text)
        if executable:
            path.chmod(0o755)

    def run_script(self, **extra):
        env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "TRINO_CLI_BIN_DIRS": str(self.canonical),
            **extra,
        }
        return subprocess.run(
            ["bash", str(SCRIPTS / "ensure_trino_cli.sh")],
            env=env,
            capture_output=True,
            text=True,
        )

    def install_calls(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_usable_canonical_binary_skips_install(self):
        self.canonical.mkdir()
        self.write(self.canonical / "trino", TRINO_OK, executable=True)

        result = self.run_script()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.install_calls(), [])

    def test_missing_binary_installs_and_verifies_canonical_path(self):
        result = self.run_script(FAKE_INSTALL="1")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.install_calls(), ["-n dnf install -y LNKD-trino-cli"])

    def test_failed_install_exits_nonzero(self):
        result = self.run_script(SUDO_RC="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("install LNKD-trino-cli failed", result.stderr)

    def test_install_that_leaves_no_canonical_binary_fails(self):
        result = self.run_script(FAKE_INSTALL="0")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("still missing or unusable", result.stderr)

    def test_broken_canonical_binary_is_reinstalled(self):
        self.canonical.mkdir()
        self.write(self.canonical / "trino", TRINO_BROKEN, executable=True)

        result = self.run_script(FAKE_INSTALL="1")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.install_calls()), 1)

    def test_shim_on_path_does_not_count_as_installed(self):
        # A trino elsewhere on PATH must not satisfy the check.
        self.write(self.shim_dir / "trino", TRINO_OK, executable=True)
        env_path = f"{self.shim_dir}:{os.environ['PATH']}"

        result = self.run_script(FAKE_INSTALL="0", PATH=f"{self.bin_dir}:{env_path}")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.install_calls()), 1)


if __name__ == "__main__":
    unittest.main()
