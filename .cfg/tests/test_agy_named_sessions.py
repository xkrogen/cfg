from contextlib import closing
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path.home() / '.gemini/antigravity-cli/bin/named-session.py'
spec = importlib.util.spec_from_file_location('agy_named_sessions', SCRIPT)
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)
ID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


class AgyNamedSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='agy-wrapper-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.mock = self.root / 'agy'
        self.mock.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
home = Path(os.environ['AGY_HOME'])
(home / 'launched.json').write_text(json.dumps(sys.argv[1:]))
''')
        self.mock.chmod(0o755)
        self.env = dict(os.environ, AGY_HOME=str(self.root), AGY_BIN=str(self.mock), HERDR_ENV='0',
                        PATH=str(self.root) + os.pathsep + os.environ['PATH'])

    def create_db(self, rows):
        db = self.root / 'conversation_summaries.db'
        with closing(sqlite3.connect(str(db))) as conn:
            with conn:
                conn.execute('CREATE TABLE conversation_summaries (conversation_id text PRIMARY KEY, title text)')
                conn.executemany('INSERT INTO conversation_summaries VALUES (?, ?)', rows)

    def write_annotation(self, identity, title):
        ann = self.root / 'annotations'
        ann.mkdir(parents=True, exist_ok=True)
        (ann / f'{identity}.pbtxt').write_text(sessions.format_pbtxt_title(title), encoding='utf-8')

    def launch(self, *args):
        return subprocess.run(['python3', '-B', str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_native_names_merges_db_and_annotations_override(self):
        self.create_db([(ID, 'db-title'), (OTHER, 'second')])
        self.write_annotation(ID, 'renamed "title" ☀')
        with patch.dict(os.environ, self.env):
            names = sessions.native_names()
        self.assertEqual(names[ID], 'renamed "title" ☀')
        self.assertEqual(names[OTHER], 'second')

    def test_resume_uses_native_uuid_and_annotation_rename_is_current(self):
        self.create_db([(ID, 'old')])
        self.write_annotation(ID, 'current')
        self.assertNotEqual(self.launch('resume', 'old').returncode, 0)
        result = self.launch('resume', 'current', '--sandbox')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()),
                         ['--conversation', ID, '--sandbox'])

    def test_new_launches_agy_and_rejects_existing_name(self):
        self.create_db([(ID, 'existing')])
        self.assertNotEqual(self.launch('new', 'existing').returncode, 0)
        self.assertFalse((self.root / 'launched.json').exists())
        result = self.launch('new', 'fresh-session', '--mode', 'auto')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), ['--mode', 'auto'])

    def test_upsert_no_arg_creates_new_and_resumes_existing(self):
        self.create_db([(ID, 'existing')])
        # No arg starts native agy without session name
        result = self.launch('upsert')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), [])
        # Existing name resumes by UUID
        result = self.launch('upsert', 'existing', '--sandbox')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()),
                         ['--conversation', ID, '--sandbox'])
        # Missing name creates new named session
        result = self.launch('upsert', 'brand-new', '--mode', 'auto')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), ['--mode', 'auto'])
        # Native passthrough mode forwards everything untouched
        result = self.launch('native', '-c')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), ['-c'])

    def test_persist_name_writes_pbtxt_and_updates_empty_db_title(self):
        self.create_db([(ID, '')])
        with patch.dict(os.environ, self.env):
            sessions.persist_name(ID, 'my-session')
            self.assertEqual(sessions.native_names()[ID], 'my-session')
        with closing(sqlite3.connect(str(self.root / 'conversation_summaries.db'))) as conn:
            title = conn.execute('SELECT title FROM conversation_summaries WHERE conversation_id = ?', (ID,)).fetchone()[0]
        self.assertEqual(title, 'my-session')

    def test_duplicate_missing_and_ambiguous_fail_without_launch(self):
        self.create_db([(ID, 'same'), (OTHER, 'same')])
        for mode, name in [('new', 'same'), ('resume', 'same'), ('resume', 'missing')]:
            with self.subTest(mode=mode, name=name):
                self.assertNotEqual(self.launch(mode, name).returncode, 0)
        self.assertFalse((self.root / 'launched.json').exists())

    def test_refresh_only_agy_with_exact_native_identity(self):
        self.create_db([(ID, 'current')])
        panes = [
            {'pane_id': 'w1:p1', 'agent': 'codex', 'agent_session': {'kind': 'id', 'value': ID}},
            {'pane_id': 'w1:p2', 'agent': 'agy', 'agent_session': {'kind': 'id', 'value': ID}},
            {'pane_id': 'w1:p3', 'agent': 'agy', 'agent_session': {'kind': 'id', 'value': OTHER}},
            {'pane_id': 'w1:p4', 'agent': 'agy', 'agent_session': {'kind': 'id', 'value': 'not-an-id'}},
        ]
        with patch.dict(os.environ, dict(self.env, HERDR_ENV='1', HERDR_PANE_ID='w1:p2')), \
             patch.object(sessions, 'herdr', return_value={'result': {'panes': panes}}), \
             patch.object(sessions, 'report') as report:
            sessions.refresh()
            self.assertEqual(report.call_count, 2)
            report.assert_any_call('w1:p2', ID, 'current')
            report.assert_any_call('w1:p3', OTHER, '')

    def test_refresh_recovers_uuid_from_conversation_argv_only(self):
        data = {'result': {'process_info': {'foreground_processes': [
            {'name': 'unrelated', 'argv': ['tool', '--conversation', OTHER]},
            {'name': 'antigravity', 'argv': ['agy', '--conversation', ID]},
        ]}}}
        with patch.object(sessions, 'herdr', return_value=data):
            self.assertEqual(sessions.pane_identity({'pane_id': 'w1:p2'}), ID)
        data['result']['process_info']['foreground_processes'] = [
            {'name': 'antigravity', 'argv': ['agy', '-c']},
            {'name': 'antigravity', 'argv': ['agy', '--conversation=not-a-uuid']},
        ]
        with patch.object(sessions, 'herdr', return_value=data):
            self.assertIsNone(sessions.pane_identity({'pane_id': 'w1:p2'}))

    def test_resume_selection_flags_are_rejected(self):
        for arg in ('-c', '--continue', '--conversation', f'--conversation={ID}'):
            self.assertNotEqual(self.launch('new', 'local', arg).returncode, 0)
        self.assertFalse((self.root / 'launched.json').exists())

    def test_hook_syncs_current_pane_display_agent(self):
        self.create_db([(ID, 'hooked-title')])
        with patch.dict(os.environ, dict(self.env, HERDR_ENV='1', HERDR_PANE_ID='w1:p2')), \
             patch.object(sessions, 'report') as report, \
             patch('sys.stdin', io.StringIO(json.dumps({'conversationId': ID}))):
            sessions.hook()
            report.assert_called_once_with('w1:p2', ID, 'hooked-title')


if __name__ == '__main__':
    unittest.main()
