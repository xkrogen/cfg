import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[2] / 'scripts/install_codex_personal.py'
SOURCE = INSTALLER.parent.parent / 'codex'
SHARED_SOURCE = INSTALLER.parent.parent / 'agents/skills'


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory(prefix='codex-personal-install-')
        self.addCleanup(self.sandbox.cleanup)
        self.target = Path(self.sandbox.name) / 'codex'
        self.target.mkdir()
        self.skills = Path(self.sandbox.name) / 'agents/skills'

    def run_installer(self):
        return subprocess.run([sys.executable, str(INSTALLER), '--codex-home', str(self.target),
                               '--skills-home', str(self.skills)],
                              capture_output=True, text=True)

    def test_relative_links_are_correct_and_repeat_install_is_idempotent(self):
        for _ in range(2):
            result = self.run_installer()
            self.assertEqual(result.returncode, 0, result.stderr)
        links = [(self.target / 'AGENTS.md', SOURCE / 'AGENTS.md')]
        links.extend((self.skills / name, SHARED_SOURCE / name)
                     for name in ('wrap-up', 'coding-guidelines', 'disk-cleanup', 'gh-stack',
                                  'make-pages-interactive', 'voice-transcription', 'skill-simplifier'))
        for target, source in links:
            self.assertTrue(target.is_symlink())
            self.assertFalse(os.path.isabs(os.readlink(target)))
            self.assertEqual(target.resolve(), source.resolve())

    def test_conflict_preserves_existing_data_and_prevents_partial_install(self):
        existing = self.skills / 'coding-guidelines'
        existing.mkdir(parents=True)
        sentinel = existing / 'keep.txt'
        sentinel.write_text('user data')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_text(), 'user data')
        self.assertFalse((self.target / 'AGENTS.md').exists())
        self.assertFalse((self.skills / 'wrap-up').exists())

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

    def test_migrates_only_recognized_old_codex_links(self):
        old = self.target / 'skills/wrap-up'
        old.parent.mkdir()
        old.symlink_to(SOURCE / 'skills/wrap-up')
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(old.is_symlink())
        self.assertEqual((self.skills / 'wrap-up').resolve(), (SHARED_SOURCE / 'wrap-up').resolve())

    def test_unmanaged_personal_copy_is_preserved_without_partial_install(self):
        old = self.target / 'skills/wrap-up'
        old.mkdir(parents=True)
        (old / 'SKILL.md').write_text('user-authored personal version')
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((old / 'SKILL.md').read_text(), 'user-authored personal version')
        self.assertFalse((self.target / 'AGENTS.md').exists())
        self.assertFalse(self.skills.exists())


if __name__ == '__main__':
    unittest.main()
