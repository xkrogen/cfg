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
            # Clear any caller role so each test chooses its own (empty = no role).
            "RDEV_SETUP_ROLE": "",
            "PATH": f"{self.tools}:{os.environ['PATH']}",
        }

    def write(self, path, text, executable=False):
        path.write_text(text)
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def run_finish_setup(self, *args, **extra):
        return subprocess.run(
            ["bash", str(self.scripts / "rdev_finish_setup.sh"), *args],
            env={**self.env, **extra}, capture_output=True, text=True, timeout=60,
        )

    def record_git_calls(self):
        overlay_init = self.home / "ekrogen-cfg-overlay" / ".cfg" / "scripts" / "init_linkedin.sh"
        overlay_init.parent.mkdir(parents=True)
        self.write(overlay_init, "#!/bin/sh\nexit 0\n", executable=True)
        calls = self.root / "git_calls"
        self.write(self.tools / "git",
                   f"#!/bin/sh\necho \"$*\" >> '{calls}'\nexit 0\n", executable=True)
        return calls

    def archive_calls(self, calls):
        return calls.read_text() if calls.exists() else ""

    def test_services_role_never_clones_the_session_archive(self):
        calls = self.record_git_calls()

        result = self.run_finish_setup(RDEV_SETUP_ROLE="services")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("role services: skipping the shared session archive clone", result.stdout)
        self.assertNotIn("claude-session-archive", self.archive_calls(calls))

    def test_backup_role_never_clones_the_session_archive(self):
        calls = self.record_git_calls()

        result = self.run_finish_setup("--role", "backup")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("claude-session-archive", self.archive_calls(calls))

    def test_no_args_with_no_role_defers_the_archive_in_the_real_flow(self):
        calls = self.record_git_calls()

        result = self.run_finish_setup()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no role set: deferring the shared session archive", result.stdout)
        self.assertNotIn("claude-session-archive", self.archive_calls(calls))

    def test_explicit_main_role_clones_the_session_archive(self):
        calls = self.record_git_calls()

        result = self.run_finish_setup(RDEV_SETUP_ROLE="main")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("claude-session-archive", self.archive_calls(calls))

    def test_unknown_role_is_rejected_before_any_setup(self):
        result = self.run_finish_setup("--role", "legacy-host")

        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid role 'legacy-host'", result.stderr)
        self.assertNotIn("rdev_finish_setup starting", result.stdout)

    def test_role_flag_without_a_value_exits_usage_promptly(self):
        for args in (["--role"], ["--role", ""], ["--role="]):
            with self.subTest(args=args):
                result = subprocess.run(
                    ["bash", str(self.scripts / "rdev_finish_setup.sh"), *args],
                    env=self.env, capture_output=True, text=True, timeout=5,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("--role", result.stderr)

    def test_uses_overlay_checkout_when_base_layer_lacks_init_linkedin(self):
        overlay_init = self.home / "ekrogen-cfg-overlay" / ".cfg" / "scripts" / "init_linkedin.sh"
        overlay_init.parent.mkdir(parents=True)
        marker = self.home / "init_linkedin_ran"
        self.write(overlay_init, f"#!/bin/sh\ntouch '{marker}'\n", executable=True)

        result = self.run_finish_setup()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(marker.exists(), "overlay init_linkedin.sh was not executed")
        self.assertIn("rdev_finish_setup finished", result.stdout)

    def test_unauthenticated_github_stops_before_setup_with_login_command(self):
        self.write(self.tools / "gh", "#!/bin/sh\nexit 1\n", executable=True)
        overlay_init = self.home / "ekrogen-cfg-overlay" / ".cfg" / "scripts" / "init_linkedin.sh"
        overlay_init.parent.mkdir(parents=True)
        marker = self.home / "init_linkedin_ran"
        self.write(overlay_init, f"#!/bin/sh\ntouch '{marker}'\n", executable=True)

        result = self.run_finish_setup()

        self.assertEqual(result.returncode, 1)
        self.assertIn("gh auth login --git-protocol https --hostname github.com", result.stdout)
        self.assertFalse(marker.exists(), "init_linkedin.sh ran without a GitHub login")

    def test_fails_clearly_when_no_init_linkedin_is_available(self):
        result = self.run_finish_setup()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("init_linkedin.sh not found", result.stdout)
        self.assertNotIn("rdev_finish_setup finished", result.stdout)


if __name__ == "__main__":
    unittest.main()
