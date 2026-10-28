from importlib.machinery import SourceFileLoader
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path.home() / '.local/bin/named-session.py'
if 'named_session' in sys.modules:
    named_session = sys.modules['named_session']
else:
    spec = importlib.util.spec_from_file_location('named_session', SCRIPT)
    named_session = importlib.util.module_from_spec(spec)
    sys.modules['named_session'] = named_session
    spec.loader.exec_module(named_session)
sessions = named_session.CopilotAdapter

AGENT_SESSIONS_SCRIPT = Path.home() / '.local/bin/agent-sessions'
as_loader = SourceFileLoader('agent_sessions', str(AGENT_SESSIONS_SCRIPT))
as_spec = importlib.util.spec_from_loader('agent_sessions', as_loader)
agent_sessions = importlib.util.module_from_spec(as_spec)
as_spec.loader.exec_module(agent_sessions)

ID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


class CopilotNamedSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='copilot-wrapper-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mock = self.root / 'copilot'
        self.mock.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
home = Path(os.environ['COPILOT_HOME'])
(home / 'launched.json').write_text(json.dumps(sys.argv[1:]))
''')
        self.mock.chmod(0o755)
        self.env = dict(os.environ, COPILOT_HOME=str(self.root), COPILOT_BIN=str(self.mock),
                        HERDR_ENV='0', PATH=str(self.root) + os.pathsep + os.environ['PATH'])

    def write_session(self, identity, name):
        session_dir = self.root / 'session-state' / identity
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / 'workspace.yaml').write_text(f'id: {identity}\nname: "{name}"\n', encoding='utf-8')

    def launch(self, *args):
        return subprocess.run(['python3', '-B', str(SCRIPT), 'copilot', *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_new_creates_session_and_rejects_existing_name(self):
        self.write_session(ID, 'existing')
        self.assertNotEqual(self.launch('new', 'existing').returncode, 0)
        self.assertFalse((self.root / 'launched.json').exists())
        result = self.launch('new', 'fresh-session', '--allow-all-tools')
        self.assertEqual(result.returncode, 0, result.stderr)
        launched = json.loads((self.root / 'launched.json').read_text())
        self.assertEqual(launched[0], '--session-id')
        self.assertEqual(launched[2:], ['--name', 'fresh-session', '--allow-all-tools'])
        with patch.dict(os.environ, self.env):
            self.assertEqual(sessions.native_names()[launched[1]], 'fresh-session')

    def test_resume_uses_exact_uuid_and_rejects_missing_or_ambiguous(self):
        self.write_session(ID, 'my-work')
        self.assertNotEqual(self.launch('resume', 'missing').returncode, 0)
        result = self.launch('resume', 'my-work', '--model', 'gpt-4o')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()),
                         ['--resume', ID, '--model', 'gpt-4o'])
        self.write_session(OTHER, 'my-work')
        self.assertNotEqual(self.launch('resume', 'my-work').returncode, 0)

    def test_upsert_no_arg_creates_new_and_resumes_existing(self):
        self.write_session(ID, 'existing')
        result = self.launch('upsert')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), [])
        result = self.launch('upsert', 'existing', '--flag')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()),
                         ['--resume', ID, '--flag'])
        result = self.launch('upsert', 'created-by-upsert')
        self.assertEqual(result.returncode, 0, result.stderr)
        launched = json.loads((self.root / 'launched.json').read_text())
        self.assertEqual(launched[0], '--session-id')
        self.assertEqual(launched[2:], ['--name', 'created-by-upsert'])

    def test_agent_sessions_formats_commands_across_all_three_agents(self):
        class FakeMod:
            def __init__(self, data):
                self._data = data
            def native_names(self):
                return self._data

        fake_adapters = (
            ('cplt', FakeMod({ID: 'cplt-one', OTHER: 'cplt two'})),
            ('agy', FakeMod({ID: 'agy-session'})),
            ('cdx', FakeMod({ID: 'cdx-session'})),
        )
        with patch.object(agent_sessions, 'AGENTS', fake_adapters):
            cmds = agent_sessions.collect_commands()
        self.assertEqual(cmds, [
            "cplt 'cplt two'",
            'cplt cplt-one',
            'agy agy-session',
            'cdx cdx-session',
        ])


if __name__ == '__main__':
    unittest.main()
