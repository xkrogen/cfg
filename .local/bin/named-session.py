#!/usr/bin/env python3
"""Unified named session manager for Copilot, Antigravity, and Codex.

Supports:
  named-session.py <agent> upsert [NAME] [options]
  named-session.py <agent> new NAME [options]
  named-session.py <agent> resume NAME [options]
  named-session.py <agent> refresh
  named-session.py <agent> list
  named-session.py <agent> hook
  named-session.py <agent> native [options]
"""
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import uuid


class SessionError(RuntimeError):
    pass


UUID_RE = re.compile(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    r'[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
)


# ==============================================================================
# Herdr Integration
# ==============================================================================

def herdr(*args):
    binary = os.environ.get('HERDR_BIN_PATH') or 'herdr'
    output = subprocess.check_output([binary, *args], text=True, stderr=subprocess.PIPE, timeout=5)
    return json.loads(output) if output.strip() else {}


def in_herdr():
    return os.environ.get('HERDR_ENV') == '1' and bool(os.environ.get('HERDR_PANE_ID'))


def in_herdr_context():
    return in_herdr() or bool(os.environ.get('HERDR_SOCKET_PATH') or os.environ.get('HERDR_ACTIVE_PANE_ID'))


def report_herdr(pane_id, agent, identity, name, source=None, user_source=None):
    seq = time.time_ns()
    source = source or f'herdr:{agent}'
    user_source = user_source or f'user:{agent}-session-name'
    socket_path = os.environ.get('HERDR_SOCKET_PATH')
    if socket_path:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                client.connect(socket_path)
                req = {
                    'id': f'{source}:{seq}',
                    'method': 'pane.report_agent_session',
                    'params': {
                        'pane_id': pane_id,
                        'source': source,
                        'agent': agent,
                        'seq': seq,
                        'agent_session_id': identity,
                    },
                }
                client.sendall((json.dumps(req) + '\n').encode())
                client.recv(4096)
        except OSError:
            pass
    else:
        herdr('pane', 'report-agent-session', pane_id, '--source', source,
              '--agent', agent, '--agent-session-id', identity, '--seq', str(seq))

    if name:
        display = name[:60] + ('...' if len(name) > 60 else '')
        herdr('pane', 'report-metadata', pane_id, '--source', user_source,
              '--agent', agent, '--display-agent', display, '--seq', str(seq))
    else:
        herdr('pane', 'report-metadata', pane_id, '--source', user_source,
              '--agent', agent, '--clear-display-agent', '--seq', str(seq))


# ==============================================================================
# Copilot Adapter
# ==============================================================================

class CopilotAdapter:
    agent = 'copilot'
    short_cmd = 'cplt'

    @staticmethod
    def home():
        return Path(os.environ.get('COPILOT_HOME') or Path.home() / '.copilot').expanduser()

    @staticmethod
    def parse_workspace_name(text):
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('name:'):
                rest = line[len('name:'):].strip()
                if rest in ('|-', '|', '>-', '>'):
                    i += 1
                    while i < len(lines) and (lines[i].startswith(' ') or not lines[i].strip()):
                        if lines[i].strip():
                            return lines[i].strip()
                        i += 1
                    return None
                return rest.strip('"').strip("'")
            i += 1
        return None

    @staticmethod
    def format_workspace_name(name):
        escaped = name.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'name: "{escaped}"\n'

    @classmethod
    def native_names(cls):
        names = {}
        session_root = cls.home() / 'session-state'
        if not session_root.is_dir():
            return names
        for entry in sorted(session_root.iterdir()):
            if not entry.is_dir():
                continue
            try:
                identity = str(uuid.UUID(entry.name))
            except ValueError:
                continue
            workspace = entry / 'workspace.yaml'
            try:
                name = cls.parse_workspace_name(workspace.read_text(encoding='utf-8'))
            except OSError:
                continue
            if isinstance(name, str) and name.strip():
                names[identity] = name
        return names

    @classmethod
    def resolve_name(cls, name, names):
        matches = [identity for identity, title in names.items() if title == name]
        if not matches:
            raise SessionError(f'No native Copilot session named {name!r}. Use cpltn to create it.')
        if len(matches) > 1:
            raise SessionError(
                f'Ambiguous native session name {name!r}; resume by UUID with copilot --resume: ' + ', '.join(matches)
            )
        return matches[0]

    @classmethod
    def binary(cls):
        override = os.environ.get('COPILOT_BIN')
        if override:
            return override
        copilot_bin_dir = (cls.home() / 'bin').resolve()
        path_dirs = []
        for entry in os.environ.get('PATH', '').split(os.pathsep):
            if not entry:
                continue
            try:
                if Path(entry).expanduser().resolve() == copilot_bin_dir:
                    continue
            except OSError:
                pass
            path_dirs.append(entry)
        found = shutil.which('copilot', path=os.pathsep.join(path_dirs))
        return found or 'copilot'

    @classmethod
    def validate_args(cls, args, *, mode):
        for arg in args:
            if arg == '--':
                break
            if arg in ('-r', '--resume', '--continue', '--session-id', '-n', '--name') or \
                    arg.startswith(('--resume=', '--session-id=', '--name=')):
                raise SessionError('A named session is already selected; do not combine it with resume or name selectors.')

    @classmethod
    def persist_name(cls, identity, name):
        session_dir = cls.home() / 'session-state' / identity
        session_dir.mkdir(parents=True, exist_ok=True)
        workspace = session_dir / 'workspace.yaml'
        if workspace.is_file():
            try:
                text = workspace.read_text(encoding='utf-8')
            except OSError:
                text = ''
            if cls.parse_workspace_name(text):
                return
            prefix = '' if (not text or text.endswith('\n')) else '\n'
            workspace.write_text(text + prefix + cls.format_workspace_name(name), encoding='utf-8')
        else:
            workspace.write_text(f'id: {identity}\n' + cls.format_workspace_name(name), encoding='utf-8')

    @classmethod
    def watch(cls, identity, name, parent):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                os.kill(parent, 0)
            except ProcessLookupError:
                return
            cls.persist_name(identity, name)
            if not in_herdr():
                return
            try:
                pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
                if pane.get('agent') == 'copilot':
                    report_herdr(pane['pane_id'], 'copilot', identity, name)
                    return
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                pass
            time.sleep(0.2)

    @classmethod
    def session_id_for_prefix(cls, prefix):
        session_root = cls.home() / 'session-state'
        if not session_root.is_dir():
            return None
        matches = []
        for entry in session_root.iterdir():
            if entry.is_dir() and UUID_RE.fullmatch(entry.name) and entry.name.startswith(prefix):
                matches.append(str(uuid.UUID(entry.name)))
        return matches[0] if len(matches) == 1 else None

    @classmethod
    def session_id_from_argv(cls, argv, names):
        selector = None
        i = 0
        while i < len(argv):
            arg = argv[i]
            if arg.startswith('--session-id='):
                selector = arg.split('=', 1)[1]
            elif arg == '--session-id' and i + 1 < len(argv):
                i += 1
                selector = argv[i]
            elif arg.startswith('--resume='):
                selector = arg.split('=', 1)[1]
            elif arg in ('-r', '--resume') and i + 1 < len(argv) and not argv[i + 1].startswith('-'):
                i += 1
                selector = argv[i]
            i += 1
        if not selector:
            return None
        if UUID_RE.fullmatch(selector):
            return str(uuid.UUID(selector))
        if re.fullmatch(r'[0-9a-fA-F]{7,}', selector):
            return cls.session_id_for_prefix(selector)
        matches = [uid for uid, title in names.items() if title == selector]
        return matches[0] if len(matches) == 1 else None

    @classmethod
    def pane_identity(cls, pane, names=None):
        session = pane.get('agent_session') or {}
        identity = session.get('value') if session.get('kind') == 'id' else None
        if identity:
            return str(uuid.UUID(identity))
        names = names if names is not None else cls.native_names()
        try:
            info = herdr('pane', 'process-info', '--pane', pane['pane_id'])
            for process in info['result']['process_info']['foreground_processes']:
                if process.get('name') != 'copilot':
                    continue
                resolved = cls.session_id_from_argv(process.get('argv') or [], names)
                if resolved:
                    return resolved
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        return None

    @classmethod
    def refresh(cls):
        if not in_herdr_context():
            raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
        names = cls.native_names()
        updated = 0
        for pane in herdr('pane', 'list')['result']['panes']:
            if pane.get('agent') != 'copilot':
                continue
            try:
                identity = cls.pane_identity(pane, names)
                if not identity:
                    continue
                report_herdr(pane['pane_id'], 'copilot', identity, names.get(identity, ''))
                updated += 1
            except (ValueError, KeyError, subprocess.SubprocessError) as exc:
                print(f'Copilot display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
        print(f'Copilot native names refreshed for {updated} pane(s).')

    @classmethod
    def launch_new(cls, name, args):
        home = cls.home()
        home.mkdir(parents=True, exist_ok=True)
        with (home / 'named-session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if name in cls.native_names().values():
                raise SessionError(f'A native Copilot session named {name!r} already exists. Use cpltr.')
            identity = str(uuid.uuid4())
            cls.persist_name(identity, name)
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), 'copilot', '_watch', identity, name, str(os.getpid())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f'Opening new Copilot session {name!r} ({identity})', file=sys.stderr)
        binary = cls.binary()
        os.execvp(binary, [binary, '--session-id', identity, '--name', name, *args])

    @classmethod
    def launch_resume(cls, name, args, identity):
        if in_herdr():
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), 'copilot', '_watch', identity, name, str(os.getpid())],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        print(f'Opening Copilot session {name!r} ({identity})', file=sys.stderr)
        binary = cls.binary()
        os.execvp(binary, [binary, '--resume', identity, *args])


# ==============================================================================
# Antigravity Adapter
# ==============================================================================

class AntigravityAdapter:
    agent = 'agy'
    short_cmd = 'agy'

    @staticmethod
    def home():
        return Path(os.environ.get('AGY_HOME') or Path.home() / '.gemini/antigravity-cli').expanduser()

    @staticmethod
    def parse_pbtxt_title(text):
        match = re.search(r'(?:^|\s)title\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if not match:
            return None
        raw = match.group(1)
        def unescape(m):
            seq = m.group(1)
            if seq == 'n':
                return '\n'
            if seq == 'r':
                return '\r'
            if seq == 't':
                return '\t'
            if seq in ('"', '\\', "'"):
                return seq
            if re.fullmatch(r'[0-7]{1,3}', seq):
                return chr(int(seq, 8))
            return seq
        if re.search(r'\\[0-7]{3}', raw):
            out = bytearray()
            i = 0
            while i < len(raw):
                if raw[i] == '\\' and i + 1 < len(raw):
                    m_oct = re.match(r'([0-7]{1,3})', raw[i + 1:])
                    if m_oct:
                        out.append(int(m_oct.group(1), 8))
                        i += 1 + len(m_oct.group(1))
                        continue
                    ch = raw[i + 1]
                    mapping = {'n': b'\n', 'r': b'\r', 't': b'\t', '"': b'"', '\\': b'\\', "'": b"'"}
                    out.extend(mapping.get(ch, ch.encode('utf-8')))
                    i += 2
                else:
                    out.extend(raw[i].encode('utf-8'))
                    i += 1
            return out.decode('utf-8', errors='replace')
        return re.sub(r'\\([nrt"\\\'])', unescape, raw)

    @staticmethod
    def format_pbtxt_title(name):
        escaped = name.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'title:"{escaped}"'

    @classmethod
    def native_names(cls):
        names = {}
        home = cls.home()
        db_path = home / 'conversation_summaries.db'
        if db_path.is_file():
            try:
                with closing(sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=2)) as conn:
                    for row_id, title in conn.execute('SELECT conversation_id, title FROM conversation_summaries'):
                        try:
                            identity = str(uuid.UUID(row_id))
                        except (ValueError, TypeError):
                            continue
                        if isinstance(title, str) and title.strip():
                            names[identity] = title
            except sqlite3.Error:
                pass

        annotations_dir = home / 'annotations'
        if annotations_dir.is_dir():
            for pbtxt in sorted(annotations_dir.glob('*.pbtxt')):
                try:
                    identity = str(uuid.UUID(pbtxt.stem))
                    title = cls.parse_pbtxt_title(pbtxt.read_text(encoding='utf-8'))
                except (OSError, ValueError, TypeError):
                    continue
                if isinstance(title, str) and title.strip():
                    names[identity] = title
        return names

    @classmethod
    def resolve_name(cls, name, names):
        matches = [identity for identity, title in names.items() if title == name]
        if not matches:
            raise SessionError(f'No native Antigravity session named {name!r}. Use agyn to create it.')
        if len(matches) > 1:
            raise SessionError(
                f'Ambiguous native session name {name!r}; resume by UUID with agy --conversation: ' + ', '.join(matches)
            )
        return matches[0]

    @classmethod
    def binary(cls):
        override = os.environ.get('AGY_BIN')
        if override:
            return override
        local_bin = (Path.home() / '.local/bin').resolve()
        path_dirs = []
        for entry in os.environ.get('PATH', '').split(os.pathsep):
            if not entry:
                continue
            try:
                if Path(entry).expanduser().resolve() == local_bin:
                    continue
            except OSError:
                pass
            path_dirs.append(entry)
        search_path = os.pathsep.join(path_dirs)
        for candidate in ('agy', 'antigravity'):
            found = shutil.which(candidate, path=search_path)
            if found:
                return found
        for fallback in ('/opt/homebrew/bin/agy', '/usr/local/bin/agy', '/home/linuxbrew/.linuxbrew/bin/agy'):
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                return fallback
        return 'agy'

    @classmethod
    def validate_args(cls, args, *, mode):
        for arg in args:
            if arg == '--':
                break
            if arg in ('-c', '--continue', '--conversation') or arg.startswith('--conversation='):
                raise SessionError('A named session is already selected; do not combine it with resume selectors.')

    @classmethod
    def persist_name(cls, identity, name):
        home = cls.home()
        annotations_dir = home / 'annotations'
        annotations_dir.mkdir(parents=True, exist_ok=True)
        pbtxt = annotations_dir / f'{identity}.pbtxt'
        if not pbtxt.exists():
            pbtxt.write_text(cls.format_pbtxt_title(name), encoding='utf-8')
        db_path = home / 'conversation_summaries.db'
        if db_path.is_file():
            try:
                with closing(sqlite3.connect(str(db_path), timeout=2)) as conn:
                    with conn:
                        conn.execute(
                            'UPDATE conversation_summaries SET title = ? WHERE conversation_id = ? AND (title = "" OR title IS NULL)',
                            (name, identity),
                        )
            except sqlite3.Error:
                pass

    @classmethod
    def existing_locks(cls):
        lock_dir = cls.home() / 'presence'
        if not lock_dir.is_dir():
            return set()
        locks = set()
        for lock_file in lock_dir.glob('*.lock'):
            try:
                locks.add(str(uuid.UUID(lock_file.stem)))
            except ValueError:
                continue
        return locks

    @classmethod
    def discover_child_session(cls, parent_pid, before_locks):
        lock_dir = cls.home() / 'presence'
        if lock_dir.is_dir():
            new_locks = []
            for lock_file in lock_dir.glob('*.lock'):
                try:
                    identity = str(uuid.UUID(lock_file.stem))
                except ValueError:
                    continue
                if identity not in before_locks:
                    new_locks.append(identity)
            if len(new_locks) == 1:
                return new_locks[0]
        if in_herdr():
            try:
                pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
                session = pane.get('agent_session') or {}
                if pane.get('agent') == 'agy' and session.get('kind') == 'id' and session.get('value'):
                    return str(uuid.UUID(session['value']))
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                pass
        return None

    @classmethod
    def watch(cls, identity, name, parent, before_locks_csv=''):
        before_locks = set(filter(None, before_locks_csv.split(',')))
        deadline = time.monotonic() + 30
        named = bool(identity)
        while time.monotonic() < deadline:
            try:
                os.kill(parent, 0)
            except ProcessLookupError:
                return
            if not identity:
                identity = cls.discover_child_session(parent, before_locks)
                if identity and not named:
                    cls.persist_name(identity, name)
                    named = True
            if identity and not in_herdr():
                return
            if identity and in_herdr():
                try:
                    pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
                    if pane.get('agent') == 'agy':
                        report_herdr(pane['pane_id'], 'agy', identity, name,
                                     source='herdr:antigravity_cli', user_source='user:agy-session-name')
                        return
                except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                    pass
            time.sleep(0.2)

    @classmethod
    def pane_identity(cls, pane):
        session = pane.get('agent_session') or {}
        identity = session.get('value') if session.get('kind') == 'id' else None
        if identity:
            return str(uuid.UUID(identity))
        info = herdr('pane', 'process-info', '--pane', pane['pane_id'])
        for process in info['result']['process_info']['foreground_processes']:
            if process.get('name') not in ('agy', 'antigravity'):
                continue
            args = process.get('argv') or []
            for index, arg in enumerate(args):
                if arg.startswith('--conversation='):
                    try:
                        return str(uuid.UUID(arg.split('=', 1)[1]))
                    except ValueError:
                        continue
                if arg == '--conversation' and index + 1 < len(args):
                    try:
                        return str(uuid.UUID(args[index + 1]))
                    except ValueError:
                        continue
        return None

    @classmethod
    def refresh(cls):
        if not in_herdr_context():
            raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
        names = cls.native_names()
        updated = 0
        for pane in herdr('pane', 'list')['result']['panes']:
            if pane.get('agent') != 'agy':
                continue
            try:
                identity = cls.pane_identity(pane)
                if not identity:
                    continue
                report_herdr(pane['pane_id'], 'agy', identity, names.get(identity, ''),
                             source='herdr:antigravity_cli', user_source='user:agy-session-name')
                updated += 1
            except (ValueError, KeyError, subprocess.SubprocessError) as exc:
                print(f'Antigravity display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
        print(f'Antigravity native names refreshed for {updated} pane(s).')

    @classmethod
    def hook(cls):
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        if isinstance(payload, dict) and payload.get('conversationId') and in_herdr():
            try:
                identity = str(uuid.UUID(payload['conversationId']))
                name = cls.native_names().get(identity, '')
                report_herdr(os.environ['HERDR_PANE_ID'], 'agy', identity, name,
                             source='herdr:antigravity_cli', user_source='user:agy-session-name')
            except Exception:
                pass
        print('{}')

    @classmethod
    def launch_new(cls, name, args):
        if name in cls.native_names().values():
            raise SessionError(f'A native Antigravity session named {name!r} already exists. Use agyr.')
        before = ','.join(sorted(cls.existing_locks()))
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), 'agy', '_watch', '', name, str(os.getpid()), before],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f'Opening new Antigravity session {name!r}', file=sys.stderr)
        binary = cls.binary()
        os.execvp(binary, [binary, *args])

    @classmethod
    def launch_resume(cls, name, args, identity):
        if in_herdr():
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), 'agy', '_watch', identity, name, str(os.getpid()), ''],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        print(f'Opening Antigravity session {name!r} ({identity})', file=sys.stderr)
        binary = cls.binary()
        os.execvp(binary, [binary, '--conversation', identity, *args])


# ==============================================================================
# Codex Adapter
# ==============================================================================

class AppServer:
    def __enter__(self):
        env = dict(os.environ)
        for key in list(env):
            if key.startswith('HERDR_'):
                del env[key]
        self.process = subprocess.Popen(['codex', 'app-server', '--stdio'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=env)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.sequence = 0
        try:
            self.call('initialize', {'clientInfo': {'name': 'codex_named_sessions', 'version': '1'}})
            self.send({'method': 'initialized'})
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def send(self, value):
        self.process.stdin.write((json.dumps(value) + '\n').encode())
        self.process.stdin.flush()

    def call(self, method, params):
        self.sequence += 1
        identity = self.sequence
        self.send({'id': identity, 'method': method, 'params': params})
        deadline = time.monotonic() + 30
        while True:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                message = json.loads(line)
                if message.get('id') != identity:
                    continue
                if 'error' in message:
                    raise SessionError(f'{method}: {message["error"]}')
                return message['result']
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise SessionError(f'Timed out waiting for Codex {method}.')
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                raise SessionError(f'Codex app-server exited during {method}.')
            self.buffer += chunk

    def __exit__(self, *_):
        self.process.stdin.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()
        self.selector.close()


class CodexAdapter:
    agent = 'codex'
    short_cmd = 'cdx'

    @staticmethod
    def home():
        return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex').expanduser()

    @classmethod
    def native_names(cls):
        names = {}
        try:
            with (cls.home() / 'session_index.jsonl').open() as stream:
                for line in stream:
                    try:
                        row = json.loads(line)
                        identity = str(uuid.UUID(row['id']))
                        name = row.get('thread_name')
                        if isinstance(name, str):
                            names[identity] = name
                    except (ValueError, KeyError, TypeError):
                        continue
        except FileNotFoundError:
            pass
        return names

    @classmethod
    def resolve_name(cls, name, names):
        matches = [identity for identity, title in names.items() if title == name]
        if not matches:
            raise SessionError(f'No native Codex session named {name!r}. Use cdxn to create it.')
        if len(matches) > 1:
            raise SessionError(f'Ambiguous native session name {name!r}; resume by UUID with codex: ' + ', '.join(matches))
        return matches[0]

    @classmethod
    def binary(cls):
        return 'codex'

    @classmethod
    def validate_args(cls, args, *, mode):
        cwd = os.getcwd()
        index = 0
        while index < len(args):
            arg = args[index]
            if arg == '--':
                break
            if arg in ('--last', '--all', '--include-non-interactive'):
                raise SessionError('A named session is already selected; do not combine it with resume selectors.')
            if arg in ('--remote', '--worktree') or arg.startswith('--remote='):
                raise SessionError('Named-session wrappers support local sessions; use native codex for remote/worktree startup.')
            if arg in ('-C', '--cd'):
                index += 1
                if index == len(args):
                    raise SessionError(arg + ' requires a directory.')
                cwd = args[index]
            elif arg.startswith('--cd='):
                cwd = arg.split('=', 1)[1]
            elif arg in ('-c', '--config', '-m', '--model', '-p', '--profile', '-s', '--sandbox',
                         '-a', '--ask-for-approval', '-i', '--image', '--add-dir', '--enable', '--disable', '--local-provider'):
                index += 1
            index += 1
        path = Path(cwd).expanduser().resolve()
        if not path.is_dir():
            raise SessionError(f'Working directory does not exist: {path}')
        return str(path)

    @classmethod
    def watch(cls, identity, name, parent):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                os.kill(parent, 0)
            except ProcessLookupError:
                return
            try:
                pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
                if pane.get('agent') == 'codex':
                    report_herdr(pane['pane_id'], 'codex', identity, name)
                    return
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                pass
            time.sleep(0.2)

    @classmethod
    def pane_identity(cls, pane, names=None):
        if names is not None:
            raw_title = (pane.get('terminal_title_stripped') or pane.get('terminal_title') or '').strip()
            if '|' in raw_title:
                parts = [p.strip() for p in raw_title.split('|') if p.strip()]
                if len(parts) >= 2:
                    candidate = re.sub(r'^[\u2800-\u28ff\s]+', '', parts[-2]).strip()
                    matches = [uid for uid, title in names.items() if title == candidate]
                    if len(matches) == 1:
                        return matches[0]
        try:
            info = herdr('pane', 'process-info', '--pane', pane['pane_id'])
            for process in info['result']['process_info']['foreground_processes']:
                if process.get('name') != 'codex':
                    continue
                args = process.get('argv') or []
                for index, arg in enumerate(args[:-1]):
                    if arg == 'resume':
                        try:
                            return str(uuid.UUID(args[index + 1]))
                        except ValueError:
                            continue
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        session = pane.get('agent_session') or {}
        identity = session.get('value') if session.get('kind') == 'id' else None
        if identity:
            return str(uuid.UUID(identity))
        return None

    @classmethod
    def refresh(cls):
        if not in_herdr_context():
            raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
        names = cls.native_names()
        updated = 0
        for pane in herdr('pane', 'list')['result']['panes']:
            if pane.get('agent') != 'codex':
                continue
            try:
                identity = cls.pane_identity(pane, names)
                if not identity:
                    continue
                report_herdr(pane['pane_id'], 'codex', identity, names.get(identity, ''))
                updated += 1
            except (ValueError, KeyError, subprocess.SubprocessError) as exc:
                print(f'Codex display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
        print(f'Codex native names refreshed for {updated} pane(s).')

    @classmethod
    def hook(cls):
        try:
            sys.stdin.read()
            if in_herdr_context():
                from contextlib import redirect_stdout
                with redirect_stdout(sys.stderr):
                    cls.refresh()
        except Exception:
            pass
        print('{}')

    @classmethod
    def launch_new(cls, name, args):
        cwd = cls.validate_args(args, mode='new')
        home = cls.home()
        home.mkdir(parents=True, exist_ok=True)
        with (home / 'named-session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if name in cls.native_names().values():
                raise SessionError(f'A native Codex session named {name!r} already exists. Use cdxr.')
            with AppServer() as server:
                thread = server.call('thread/start', {'cwd': cwd, 'ephemeral': False})['thread']
                identity = thread['id']
                try:
                    server.call('thread/name/set', {'threadId': identity, 'name': name})
                except SessionError as exc:
                    raise SessionError(f'Created {identity}, but naming failed; recover with codex resume {identity}. {exc}') from exc
        if in_herdr():
            os.environ['CODEX_THREAD_ID'] = identity
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'codex', '_watch', identity,
                              name, str(os.getpid())], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        print(f'Opening Codex session {name!r} ({identity})', file=sys.stderr)
        os.execvp('codex', ['codex', 'resume', identity, *args])

    @classmethod
    def launch_resume(cls, name, args, identity):
        cls.validate_args(args, mode='resume')
        if in_herdr():
            os.environ['CODEX_THREAD_ID'] = identity
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'codex', '_watch', identity,
                              name, str(os.getpid())], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        print(f'Opening Codex session {name!r} ({identity})', file=sys.stderr)
        os.execvp('codex', ['codex', 'resume', identity, *args])


# ==============================================================================
# Adapter Registry & Main Dispatcher
# ==============================================================================

ADAPTERS = {
    'copilot': CopilotAdapter,
    'cplt': CopilotAdapter,
    'antigravity': AntigravityAdapter,
    'agy': AntigravityAdapter,
    'codex': CodexAdapter,
    'cdx': CodexAdapter,
}


def dispatch(adapter, mode, rest):
    if mode == 'refresh':
        adapter.refresh()
        return
    if mode == 'list':
        for title in sorted(set(adapter.native_names().values())):
            print(title)
        return
    if mode == 'hook':
        if hasattr(adapter, 'hook'):
            adapter.hook()
        return
    if mode == '_watch':
        if adapter.agent == 'agy':
            adapter.watch(rest[0], rest[1], int(rest[2]), rest[3] if len(rest) > 3 else '')
        else:
            adapter.watch(rest[0], rest[1], int(rest[2]))
        return
    if mode == 'native':
        binary = adapter.binary()
        os.execvp(binary, [binary, *rest])

    short = adapter.short_cmd
    if mode not in ('upsert', 'new', 'resume'):
        raise SessionError(f'Usage: {short} [session-name] [{adapter.agent} options] | {short}n|{short}r <session-name> [{adapter.agent} options]')

    if mode == 'upsert':
        if not rest:
            binary = adapter.binary()
            os.execvp(binary, [binary])
        if rest[0] in ('-h', '--help'):
            print(f'Usage: {short} [session-name] [{adapter.agent} options]')
            return
        if rest[0].startswith('-'):
            binary = adapter.binary()
            os.execvp(binary, [binary, *rest])
    elif not rest:
        raise SessionError(f'Usage: {short}n|{short}r <session-name> [{adapter.agent} options]')

    name, args = rest[0], rest[1:]
    if name in ('-h', '--help'):
        print(f'Usage: {short}n|{short}r <session-name> [{adapter.agent} options]')
        return
    if not name.strip() or name.startswith('-') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise SessionError('Session name must be nonempty printable text and must not start with a dash.')

    if hasattr(adapter, 'validate_args'):
        adapter.validate_args(args, mode=mode)

    names = adapter.native_names()
    if mode == 'upsert':
        matches = [uid for uid, title in names.items() if title == name]
        mode = 'resume' if matches else 'new'

    if mode == 'new':
        adapter.launch_new(name, args)
    else:
        identity = adapter.resolve_name(name, names)
        adapter.launch_resume(name, args, identity)


def main():
    if len(sys.argv) < 3:
        raise SessionError('Usage: named-session.py <agent: copilot|agy|codex> <mode: upsert|new|resume|refresh|list|hook|native> [args...]')
    agent_name = sys.argv[1].lower()
    adapter = ADAPTERS.get(agent_name)
    if not adapter:
        raise SessionError(f'Unknown agent {agent_name!r}. Supported agents: copilot, agy, codex')
    mode = sys.argv[2]
    rest = sys.argv[3:]
    dispatch(adapter, mode, rest)


if __name__ == '__main__':
    try:
        main()
    except (SessionError, OSError, ValueError, subprocess.SubprocessError) as error:
        agent_tag = sys.argv[1] if len(sys.argv) > 1 else 'agent'
        print(f'{agent_tag} named sessions: {error}', file=sys.stderr)
        sys.exit(1)
