"""The tracked Gemini usps hooks run only on Darwin with the original release present."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[2] / ".gemini" / "config" / "hooks.json"
MAC_ROOT = "/Users/xkrogen"
CLI = ".local/lib/usps/current/dist/src/cli.js"


class GeminiUspsHookTests(unittest.TestCase):
    """Runs the real command strings with the Mac root and node rewritten to a fixture.

    Only the root prefix changes, so the argv and config path are otherwise the tracked
    ones. A stub `uname` selects the platform, and a stub node records its argv.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gemini-usps-hook-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "mac-root"
        self.home = Path(self.temp.name) / "home"
        self.root.mkdir()
        self.home.mkdir()
        self.calls = Path(self.temp.name) / "node-argv.json"
        self.stub_dir = Path(self.temp.name) / "bin"
        self.stub_dir.mkdir()
        node = self.root / ".volta/bin/node"
        node.parent.mkdir(parents=True)
        node.write_text("#!/usr/bin/env python3\n"
                        "import json,os,pathlib,sys\n"
                        "pathlib.Path(os.environ['NODE_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
                        "sys.exit(int(os.environ.get('NODE_EXIT', '0')))\n")
        node.chmod(0o700)
        self.commands = {
            hook["command"].split("--event ")[1].split()[0]: hook["command"]
            for hook in json.loads(HOOKS.read_text())["usps"]["SessionStart"]
            + json.loads(HOOKS.read_text())["usps"]["PreInvocation"]
        }

    def write_stub(self, name, body):
        path = self.stub_dir / name
        path.write_text(body)
        path.chmod(0o700)

    def run_hook(self, event, uname="Darwin", node_exit="0"):
        self.write_stub("uname", f"#!/bin/sh\necho {uname}\n")
        command = self.commands[event].replace(MAC_ROOT, str(self.root))
        env = dict(os.environ, HOME=str(self.home), NODE_LOG=str(self.calls), NODE_EXIT=node_exit,
                   PATH=f"{self.stub_dir}:{os.environ['PATH']}")
        return subprocess.run(["sh", "-c", command], env=env, capture_output=True, text=True,
                              cwd=self.temp.name)

    def install_cli(self, base):
        cli = base / CLI
        cli.parent.mkdir(parents=True, exist_ok=True)
        cli.write_text("// fixture\n")

    def test_darwin_with_the_release_runs_with_the_tracked_arguments_and_exit_status(self):
        self.install_cli(self.root)
        result = self.run_hook("SessionStart", node_exit="3")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(self.calls.read_text()), [
            str(self.root / CLI), "--profile", "personal", "agy", "hooks", "event",
            "--event", "SessionStart", "--config",
            str(self.root / ".config/usps/profiles/personal/hooks/agy-krogbook-personal.json"),
        ])

    def test_darwin_without_the_release_is_a_silent_success(self):
        result = self.run_hook("PreInvocation")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())

    def test_linux_with_the_release_does_not_run_the_hook(self):
        self.install_cli(self.root)
        result = self.run_hook("SessionStart", uname="Linux")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())

    def test_a_release_under_home_alone_does_not_activate_the_mac_hook(self):
        self.install_cli(self.home)
        result = self.run_hook("SessionStart")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())


if __name__ == "__main__":
    unittest.main()
