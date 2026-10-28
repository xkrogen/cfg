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
sessions = named_session.CodexAdapter
ID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


class NamedSessionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='codex-wrapper-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, CODEX_HOME=str(self.root), HERDR_ENV='0',
                        PATH=str(self.root) + os.pathsep + os.environ['PATH'])
        self.mock = self.root / 'codex'
        self.mock.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
home=Path(os.environ['CODEX_HOME'])
if sys.argv[1:]==['app-server','--stdio']:
 for line in sys.stdin:
  msg=json.loads(line);method=msg['method'];params=msg.get('params',{})
  if 'id' not in msg:continue
  result={}
  if method=='thread/start':
   (home/'start.json').write_text(json.dumps(params))
   result={'thread':{'id':'11111111-1111-4111-8111-111111111111'}}
  if method=='thread/name/set':
   with (home/'session_index.jsonl').open('a') as f:
    f.write(json.dumps({'id':params['threadId'],'thread_name':params['name']})+'\\n')
  print(json.dumps({'method':'notification'}),flush=True)
  print(json.dumps({'id':msg['id'],'result':result}),flush=True)
else:
 (home/'launched.json').write_text(json.dumps(sys.argv[1:]))
''')
        self.mock.chmod(0o755)

    def index(self, rows):
        (self.root / 'session_index.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def launch(self, *args):
        return subprocess.run(['python3', '-B', str(SCRIPT), 'codex', *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_new_names_native_session_and_preserves_argv(self):
        name = 'garden "plan" ☀'
        args = ['-C', str(self.root), '-m', 'chosen-model', 'a prompt with $literal']
        result = self.launch('new', name, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root/'launched.json').read_text()), ['resume', ID, *args])
        self.assertEqual(json.loads((self.root/'start.json').read_text())['cwd'], str(self.root.resolve()))
        with patch.dict(os.environ, self.env):
            self.assertEqual(sessions.native_names()[ID], name)

    def test_resume_uses_native_uuid_and_rename_is_current(self):
        self.index([{'id':ID,'thread_name':'old'}, {'id':ID,'thread_name':'current'}])
        self.assertNotEqual(self.launch('resume','old').returncode, 0)
        result=self.launch('resume','current','--search')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.root/'launched.json').read_text()), ['resume',ID,'--search'])
        self.assertFalse((self.root/'start.json').exists())

    def test_upsert_no_arg_creates_new_and_resumes_existing(self):
        self.index([{'id': ID, 'thread_name': 'existing'}])
        # No arg starts native codex without session name
        result = self.launch('upsert')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), [])
        self.assertFalse((self.root / 'start.json').exists())
        # Existing name resumes by UUID without creating
        result = self.launch('upsert', 'existing', '--search')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), ['resume', ID, '--search'])
        self.assertFalse((self.root / 'start.json').exists())
        # Missing name creates and names via app-server then resumes by UUID
        result = self.launch('upsert', 'brand-new', '-m', 'chosen-model')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'launched.json').read_text()), ['resume', ID, '-m', 'chosen-model'])
        self.assertTrue((self.root / 'start.json').exists())

    def test_duplicate_missing_and_ambiguous_fail_without_launch(self):
        self.index([{'id':ID,'thread_name':'same'},{'id':OTHER,'thread_name':'same'}])
        for mode,name in [('new','same'),('resume','same'),('resume','missing')]:
            with self.subTest(mode=mode,name=name):
                self.assertNotEqual(self.launch(mode,name).returncode,0)
        self.assertFalse((self.root/'launched.json').exists())
        self.assertFalse((self.root/'start.json').exists())

    def test_incomplete_index_tail_is_ignored(self):
        self.index([{'id':ID,'thread_name':'kept'}])
        with (self.root/'session_index.jsonl').open('a') as f:f.write('{"id":')
        with patch.dict(os.environ,self.env):
            self.assertEqual(sessions.native_names(),{ID:'kept'})

    def test_refresh_only_codex_with_exact_native_identity(self):
        self.index([{'id':ID,'thread_name':'current'}])
        panes=[{'pane_id':'w1:p1','agent':'copilot','agent_session':{'kind':'id','value':ID}},
               {'pane_id':'w1:p2','agent':'codex','agent_session':{'kind':'id','value':ID}},
               {'pane_id':'w1:p3','agent':'codex','agent_session':{'kind':'id','value':OTHER}},
               {'pane_id':'w1:p4','agent':'codex','agent_session':{'kind':'id','value':'not-an-id'}}]
        with patch.dict(os.environ,dict(self.env,HERDR_ENV='1',HERDR_PANE_ID='w1:p2')), \
             patch('named_session.herdr',return_value={'result':{'panes':panes}}), \
             patch('named_session.report_herdr') as report:
            sessions.refresh()
            self.assertEqual(report.call_count,2)
            report.assert_any_call('w1:p2','codex',ID,'current')
            report.assert_any_call('w1:p3','codex',OTHER,'')

    def test_refresh_recovers_uuid_from_native_resume_process_only(self):
        data={'result':{'process_info':{'foreground_processes':[
            {'name':'unrelated','argv':['tool','resume',OTHER]},
            {'name':'codex','argv':['/path/codex','resume',ID]}]}}}
        with patch('named_session.herdr',return_value=data):
            self.assertEqual(sessions.pane_identity({'pane_id':'w1:p2'}), ID)
        data['result']['process_info']['foreground_processes']=[
            {'name':'codex','argv':['codex','resume']},
            {'name':'codex','argv':['codex','resume','ambiguous-name']}]
        with patch('named_session.herdr',return_value=data):
            self.assertIsNone(sessions.pane_identity({'pane_id':'w1:p2'}))

    def test_refresh_prefers_foreground_resume_uuid_over_stale_pane_session(self):
        pane = {'pane_id': 'w1:p2', 'agent': 'codex', 'agent_session': {'kind': 'id', 'value': OTHER}}
        data = {'result': {'process_info': {'foreground_processes': [
            {'name': 'codex', 'argv': ['codex', 'resume', ID]},
        ]}}}
        with patch('named_session.herdr', return_value=data):
            self.assertEqual(sessions.pane_identity(pane), ID)

    def test_refresh_resolves_unique_native_name_from_codex_terminal_title(self):
        names = {ID: 'homelab-vpn-external-setup', OTHER: 'other-session'}
        pane = {
            'pane_id': 'w1:p7',
            'agent': 'codex',
            'terminal_title': '⠏ homelab-vpn-external-setup | homelab',
            'terminal_title_stripped': 'homelab-vpn-external-setup | homelab',
        }
        data = {'result': {'process_info': {'foreground_processes': [
            {'name': 'codex', 'argv': ['codex', 'fork', 'homelab-init']},
        ]}}}
        with patch('named_session.herdr', return_value=data):
            self.assertEqual(sessions.pane_identity(pane, names), ID)

    def test_herdr_report_accepts_success_with_empty_stdout(self):
        with patch('named_session.subprocess.check_output', return_value=''):
            self.assertEqual(named_session.herdr('pane', 'report-metadata', 'w1:p1'), {})

    def test_help_and_missing_arguments_do_not_create_a_session(self):
        self.assertEqual(self.launch('new', '--help').returncode, 0)
        self.assertNotEqual(self.launch('new').returncode, 0)
        self.assertFalse((self.root/'start.json').exists())

    def test_resume_selection_flags_are_rejected(self):
        for arg in ('--last', '--all', '--include-non-interactive'):
            self.assertNotEqual(self.launch('new', 'local', arg).returncode, 0)
        self.assertFalse((self.root/'start.json').exists())

    def test_unknown_options_cannot_retarget_to_remote_or_worktree(self):
        for arg in ('--remote','--remote=unix:///tmp/elsewhere','--worktree'):
            with self.subTest(arg=arg):
                self.assertNotEqual(self.launch('new','local',arg).returncode,0)
        self.assertFalse((self.root/'start.json').exists())


if __name__ == '__main__':
    unittest.main()
