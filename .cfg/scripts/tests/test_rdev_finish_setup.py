"""Regression fixtures for rdev_finish_setup's cfgli bootstrap step."""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
STUB = "#!/bin/sh\nexit 0\n"


class FinishSetupOverlayBootstrapTests(unittest.TestCase):
    """Runs the real script with stubbed external commands.

    The scratch tree lives under tests/.work rather than a system temp dir.
    The script derives its scripts directory from its own location, so it is
    copied to <root>/base/scripts/ to mirror the rdev base-layer layout.
    """

    def setUp(self):
        self.root = SCRIPTS / "tests" / ".work" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = self.root / "home"
        self.home.mkdir(parents=True)
        self.scripts = self.root / "base" / "scripts"
        self.scripts.mkdir(parents=True)
        shutil.copy(SCRIPTS / "rdev_finish_setup.sh", self.scripts)
        self.write(self.scripts / "ensure_rdev_dbus.sh", STUB)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        for name in ("gh", "git", "curl", "flock"):
            self.write(self.tools / name, STUB, executable=True)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "RDEV_ID": "test-rdev",
            "PATH": f"{self.tools}:{os.environ['PATH']}",
        }

    def write(self, path, text, executable=False):
        path.write_text(text)
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def run_finish_setup(self):
        return subprocess.run(
            ["bash", str(self.scripts / "rdev_finish_setup.sh")],
            env=self.env, capture_output=True, text=True, timeout=60,
        )

    def test_uses_overlay_checkout_when_base_layer_lacks_init_linkedin(self):
        overlay_init = self.home / "ekrogen-cfg-overlay" / ".cfg" / "scripts" / "init_linkedin.sh"
        overlay_init.parent.mkdir(parents=True)
        marker = self.home / "init_linkedin_ran"
        self.write(overlay_init, f"#!/bin/sh\ntouch '{marker}'\n", executable=True)

        result = self.run_finish_setup()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(marker.exists(), "overlay init_linkedin.sh was not executed")
        self.assertIn("rdev_finish_setup finished", result.stdout)

    def test_fails_clearly_when_no_init_linkedin_is_available(self):
        result = self.run_finish_setup()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("init_linkedin.sh not found", result.stdout)
        self.assertNotIn("rdev_finish_setup finished", result.stdout)


if __name__ == "__main__":
    unittest.main()
