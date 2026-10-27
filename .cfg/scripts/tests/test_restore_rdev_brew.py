"""Restore of Homebrew and standard Brew tools after RDev pod recreation."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
HELPER = SCRIPTS / "restore_rdev_brew.sh"

# Real advisory locking for the helper's inherited fd 9, matching flock(1).
FLOCK_MOCK = f"""#!{sys.executable}
import fcntl, sys
flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if "-n" in sys.argv else 0)
try:
    fcntl.flock(int(sys.argv[-1]), flags)
except BlockingIOError:
    sys.exit(1)
"""

BREW_MOCK = """#!/bin/bash
echo "brew $*" >> "$CALLS"
case "$1" in
    --prefix) echo "$HOME/brew" ;;
    shellenv) ;;
    install)
        if [ "${MOCK_BREW_FAIL:-}" = 1 ]; then exit 1; fi
        ;;
esac
"""

CURL_MOCK = """#!/bin/bash
echo "curl $*" >> "$CALLS"
echo "exit 3"
"""

PRUNE_STUB = """#!/bin/bash
echo "prune" >> "$CALLS"
"""


class RestoreRdevBrewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="rdev-brew-restore-")
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        (self.home / ".cfg/scripts").mkdir(parents=True)
        self.calls = self.home / "calls"
        self.sentinel = self.home / "sentinel"
        self.stamp = self.home / "attempt"
        self.write(self.home / ".cfg/scripts/prune_brew_completions.sh", PRUNE_STUB)
        self.write(self.bin / "flock", FLOCK_MOCK)
        self.write(self.bin / "curl", CURL_MOCK)
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("RDEV_ID", "FORCE", "MOCK_BREW_FAIL")}
        self.env.update(HOME=str(self.home), PATH=f"{self.bin}:/usr/bin:/bin",
                        CALLS=str(self.calls), RDEV_ID="rdev-test",
                        RDEV_BREW_RESTORE_SENTINEL=str(self.sentinel),
                        RDEV_BREW_RESTORE_ATTEMPT_STAMP=str(self.stamp))

    def write(self, path, content):
        path.write_text(content)
        path.chmod(0o755)

    def install_brew(self):
        self.write(self.bin / "brew", BREW_MOCK)

    def run_helper(self, **extra):
        env = dict(self.env, **extra)
        return subprocess.run(["bash", str(HELPER)], env=env, cwd=self.home,
                              capture_output=True, text=True, timeout=30)

    def recorded(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def log(self):
        path = self.home / ".rdev_brew_restore.log"
        return path.read_text() if path.exists() else ""

    def test_sentinel_present_is_a_no_op(self):
        self.install_brew()
        self.sentinel.write_text("done\n")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.recorded(), [])

    def test_fresh_pod_restores_standard_formulas_and_casks(self):
        self.install_brew()
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.recorded()
        formula_install = next(c for c in calls if c.startswith("brew install azure-cli"))
        self.assertIn("alltuner/tap/git-sprout", formula_install.split())
        self.assertIn("worktrunk", formula_install.split())
        self.assertIn("brew install --cask codex", calls)
        self.assertIn("brew install --cask antigravity-cli", calls)
        self.assertFalse(any("jdtls" in c for c in calls))
        self.assertIn("prune", calls)
        self.assertTrue(self.sentinel.exists())

    def test_missing_brew_with_failed_bootstrap_retries_only_after_cooldown(self):
        result = self.run_helper()
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.sentinel.exists())
        self.assertTrue(self.stamp.exists())
        self.assertEqual(sum(c.startswith("curl") for c in self.recorded()), 1)

        retry = self.run_helper()
        self.assertEqual(retry.returncode, 0)
        self.assertEqual(sum(c.startswith("curl") for c in self.recorded()), 1)
        self.assertIn("within 30 minutes", self.log())

    def test_failed_formula_install_leaves_sentinel_absent(self):
        self.install_brew()
        result = self.run_helper(MOCK_BREW_FAIL="1")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.sentinel.exists())
        self.assertIn("standard Brew restore failed", self.log())

    def hold_lock(self, name):
        holder = subprocess.Popen(
            [sys.executable, "-c",
             "import fcntl,sys,time; f=open(sys.argv[1],'w'); "
             "fcntl.flock(f, fcntl.LOCK_EX); print('locked', flush=True); time.sleep(20)",
             str(self.home / name)],
            stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.wait)
        self.addCleanup(holder.kill)
        self.addCleanup(holder.stdout.close)
        self.assertEqual(holder.stdout.readline().strip(), "locked")

    def test_overlapping_run_coalesces_on_held_lock(self):
        self.install_brew()
        self.hold_lock(".rdev_brew_restore.lock")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.recorded(), [])
        self.assertIn("coalescing", self.log())

    def test_defers_while_finish_setup_holds_its_lock(self):
        self.install_brew()
        self.hold_lock(".rdev_finish_setup.lock")
        result = self.run_helper()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.recorded(), [])
        self.assertIn("rdev_finish_setup is running", self.log())
        self.assertFalse(self.sentinel.exists())

if __name__ == "__main__":
    unittest.main()
