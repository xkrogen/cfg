#!/usr/bin/env python3
"""Named native Codex sessions and Codex-only Herdr metadata refresh."""
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time
import uuid


class SessionError(RuntimeError):
    pass


def codex_home():
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex').expanduser()


def native_names():
    """Read only the native name index; later records replace earlier renames."""
    names = {}
    try:
        with (codex_home() / 'session_index.jsonl').open() as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    identity = str(uuid.UUID(row['id']))
                    name = row.get('thread_name')
                    if isinstance(name, str):
                        names[identity] = name
                except (ValueError, KeyError, TypeError):
                    continue  # A concurrent final append may be incomplete.
    except FileNotFoundError:
        pass
    return names


def resolve_name(name, names):
    matches = [identity for identity, title in names.items() if title == name]
    if not matches:
        raise SessionError(f'No native Codex session named {name!r}. Use cdxn to create it.')
    if len(matches) > 1:
        raise SessionError(f'Ambiguous native session name {name!r}; resume by UUID with codex: ' + ', '.join(matches))
    return matches[0]


class AppServer:
    """Short-lived supported stdio RPC; never send a model turn or edit storage."""
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


def launch_cwd(args):
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


def herdr(*args):
    binary = os.environ.get('HERDR_BIN_PATH') or 'herdr'
    output = subprocess.check_output([binary, *args], text=True,
                                     stderr=subprocess.PIPE, timeout=5)
    return json.loads(output) if output.strip() else {}


def in_herdr():
    return os.environ.get('HERDR_ENV') == '1' and bool(os.environ.get('HERDR_PANE_ID'))


def in_herdr_context():
    return in_herdr() or bool(os.environ.get('HERDR_SOCKET_PATH') or os.environ.get('HERDR_ACTIVE_PANE_ID'))


def report(pane_id, identity, name):
    seq = time.time_ns()
    socket_path = os.environ.get('HERDR_SOCKET_PATH')
    if socket_path:
        try:
            import socket
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                client.connect(socket_path)
                req = {
                    'id': f'herdr:codex:{seq}',
                    'method': 'pane.report_agent_session',
                    'params': {
                        'pane_id': pane_id,
                        'source': 'herdr:codex',
                        'agent': 'codex',
                        'seq': seq,
                        'agent_session_id': identity,
                        'session_start_source': 'resume',
                    },
                }
                client.sendall((json.dumps(req) + '\n').encode())
                client.recv(4096)
        except OSError:
            pass
    else:
        herdr('pane', 'report-agent-session', pane_id, '--source', 'herdr:codex',
              '--agent', 'codex', '--agent-session-id', identity, '--seq', str(seq))
    if name:
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:codex-session-name',
              '--agent', 'codex', '--display-agent', name, '--seq', str(seq))
    else:
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:codex-session-name',
              '--agent', 'codex', '--clear-display-agent', '--seq', str(seq))


def watch(identity, name, parent):
    """Report after exec replaces the launcher and Herdr recognizes the TUI."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            os.kill(parent, 0)
        except ProcessLookupError:
            return
        try:
            pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
            if pane.get('agent') == 'codex':
                report(pane['pane_id'], identity, name)
                return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        time.sleep(0.2)


def pane_identity(pane, names=None):
    # 1. If Codex set terminal_title to "<thread_name> | <project>" and that
    # thread_name maps to a unique UUID in session_index.jsonl, use it first.
    # This handles `codex fork` / bare `codex` and guards against the shared
    # app-server daemon running SessionStart hooks with another pane's HERDR_PANE_ID.
    if names is not None:
        raw_title = (pane.get('terminal_title_stripped') or pane.get('terminal_title') or '').strip()
        if '|' in raw_title:
            parts = [p.strip() for p in raw_title.split('|') if p.strip()]
            if len(parts) >= 2:
                candidate = re.sub(r'^[\u2800-\u28ff\s]+', '', parts[-2]).strip()
                matches = [uid for uid, title in names.items() if title == candidate]
                if len(matches) == 1:
                    return matches[0]
    # 2. Check foreground codex resume process argv.
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
    # 3. Fall back to Herdr's recorded agent_session UUID.
    session = pane.get('agent_session') or {}
    identity = session.get('value') if session.get('kind') == 'id' else None
    if identity:
        return str(uuid.UUID(identity))
    return None


def refresh():
    if not in_herdr_context():
        raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
    names = native_names()
    updated = 0
    for pane in herdr('pane', 'list')['result']['panes']:
        if pane.get('agent') != 'codex':
            continue
        try:
            identity = pane_identity(pane, names)
            if not identity:
                continue
            report(pane['pane_id'], identity, names.get(identity, ''))
            updated += 1
        except (ValueError, KeyError, subprocess.SubprocessError) as exc:
            print(f'Codex display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
    print(f'Codex native names refreshed for {updated} pane(s).')


def hook():
    try:
        sys.stdin.read()
        if in_herdr_context():
            from contextlib import redirect_stdout
            with redirect_stdout(sys.stderr):
                refresh()
    except Exception:
        pass
    print('{}')


def main():
    if len(sys.argv) < 2:
        raise SessionError('Usage: named-session.py upsert|new|resume [NAME] [codex options], or refresh|list')
    mode = sys.argv[1]
    if mode == 'refresh':
        refresh()
        return
    if mode == 'list':
        for title in sorted(set(native_names().values())):
            print(title)
        return
    if mode == 'hook':
        hook()
        return
    if mode == '_watch':
        watch(sys.argv[2], sys.argv[3], int(sys.argv[4]))
        return
    if mode not in ('upsert', 'new', 'resume'):
        raise SessionError('Usage: cdx [session-name] [codex options] | cdxn|cdxr <session-name> [codex options]')
    if mode == 'upsert':
        if len(sys.argv) < 3:
            os.execvp('codex', ['codex'])
        if sys.argv[2] in ('-h', '--help'):
            print('Usage: cdx [session-name] [codex options]')
            return
        if sys.argv[2].startswith('-'):
            os.execvp('codex', ['codex', *sys.argv[2:]])
    elif len(sys.argv) < 3:
        raise SessionError('Usage: cdxn|cdxr <session-name> [codex options]')
    name, args = sys.argv[2], sys.argv[3:]
    if name in ('-h', '--help'):
        print('Usage: cdxn|cdxr <session-name> [codex options]')
        return
    if not name.strip() or name.startswith('-') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise SessionError('Session name must be nonempty printable text and must not start with a dash.')
    cwd = launch_cwd(args)
    names = native_names()
    if mode == 'upsert':
        matches = [identity for identity, title in names.items() if title == name]
        mode = 'resume' if matches else 'new'
    if mode == 'new':
        codex_home().mkdir(parents=True, exist_ok=True)
        with (codex_home() / 'named-session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if name in native_names().values():
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
    else:
        identity = resolve_name(name, names)
        if in_herdr():
            os.environ['CODEX_THREAD_ID'] = identity

    if in_herdr():
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_watch', identity,
                          name, str(os.getpid())], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    print(f'Opening Codex session {name!r} ({identity})', file=sys.stderr)
    os.execvp('codex', ['codex', 'resume', identity, *args])


if __name__ == '__main__':
    try:
        main()
    except (SessionError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'codex named sessions: {error}', file=sys.stderr)
        sys.exit(1)
