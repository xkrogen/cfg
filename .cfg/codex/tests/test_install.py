import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install_codex_personal.py'
SOURCE = INSTALLER.parent.parent / 'codex'


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(prefix='codex-personal-install-')
        self.addCleanup(self.sandbox.cleanup)
        self.target = Path(self.sandbox.name) / 'codex'
        self.target.mkdir()

    def run_installer(self):
        return subprocess.run([sys.executable, str(INSTALLER), '--codex-home', str(self.target)],
                              capture_output=True, text=True)

    def test_relative_links_are_correct_and_repeat_install_is_idempotent(self):
        for _ in range(2):
            result = self.run_installer()
            self.assertEqual(result.returncode, 0, result.stderr)
        links = {'AGENTS.md': SOURCE / 'AGENTS.md'}
        links.update(('skills/' + name, SOURCE / 'skills' / name)
                     for name in ('wrap-up', 'coding-guidelines', 'disk-cleanup'))
        for name, source in links.items():
            target = self.target / name
            self.assertTrue(target.is_symlink())
            self.assertFalse(os.path.isabs(os.readlink(target)))
            self.assertEqual(target.resolve(), source.resolve())

    def test_conflict_preserves_existing_data_and_prevents_partial_install(self):
        existing = self.target / 'skills/coding-guidelines'
        existing.mkdir(parents=True)
        sentinel = existing / 'keep.txt'
        sentinel.write_text('user data')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'user data')
        self.assertFalse((self.target / 'AGENTS.md').exists())
        self.assertFalse((self.target / 'skills/wrap-up').exists())

    def test_wrong_symlink_is_preserved(self):
        target = self.target / 'AGENTS.md'
        target.symlink_to('missing-user-target')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(os.readlink(target), 'missing-user-target')
        self.assertFalse((self.target / 'skills').exists())

    def test_existing_override_is_preserved_and_reported(self):
        override = self.target / 'AGENTS.override.md'
        override.write_text('user override')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('override', result.stderr)
        self.assertEqual(override.read_text(), 'user override')
        self.assertFalse((self.target / 'AGENTS.md').exists())


if __name__ == '__main__':
    unittest.main()
