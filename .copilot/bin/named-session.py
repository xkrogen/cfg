#!/usr/bin/env python3
"""Named GitHub Copilot CLI sessions and Copilot-only Herdr metadata refresh."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import socket
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


def copilot_home():
    return Path(os.environ.get('COPILOT_HOME') or Path.home() / '.copilot').expanduser()


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


def format_workspace_name(name):
    escaped = name.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'name: "{escaped}"\n'


def native_names():
    """Read native Copilot session names from ~/.copilot/session-state/<uuid>/workspace.yaml."""
    names = {}
    session_root = copilot_home() / 'session-state'
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
            name = parse_workspace_name(workspace.read_text(encoding='utf-8'))
        except OSError:
            continue
        if isinstance(name, str) and name.strip():
            names[identity] = name
    return names


def resolve_name(name, names):
    matches = [identity for identity, title in names.items() if title == name]
    if not matches:
        raise SessionError(f'No native Copilot session named {name!r}. Use cpltn to create it.')
    if len(matches) > 1:
        raise SessionError(
            f'Ambiguous native session name {name!r}; resume by UUID with copilot --resume: ' + ', '.join(matches)
        )
    return matches[0]


def validate_args(args):
    for arg in args:
        if arg == '--':
            break
        if arg in ('-r', '--resume', '--continue', '--session-id', '-n', '--name') or \
                arg.startswith(('--resume=', '--session-id=', '--name=')):
            raise SessionError('A named session is already selected; do not combine it with resume or name selectors.')


def copilot_binary():
    override = os.environ.get('COPILOT_BIN')
    if override:
        return override
    copilot_bin_dir = (copilot_home() / 'bin').resolve()
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


def herdr(*args):
    binary = os.environ.get('HERDR_BIN_PATH') or 'herdr'
    output = subprocess.check_output([binary, *args], text=True, stderr=subprocess.PIPE, timeout=5)
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
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                client.connect(socket_path)
                req = {
                    'id': f'herdr:copilot:{seq}',
                    'method': 'pane.report_agent_session',
                    'params': {
                        'pane_id': pane_id,
                        'source': 'herdr:copilot',
                        'agent': 'copilot',
                        'seq': seq,
                        'agent_session_id': identity,
                    },
                }
                client.sendall((json.dumps(req) + '\n').encode())
                client.recv(4096)
        except OSError:
            pass
    else:
        herdr('pane', 'report-agent-session', pane_id, '--source', 'herdr:copilot',
              '--agent', 'copilot', '--agent-session-id', identity, '--seq', str(seq))
    if name:
        display = name[:60] + ('...' if len(name) > 60 else '')
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:copilot-session-name',
              '--agent', 'copilot', '--display-agent', display, '--seq', str(seq))
    else:
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:copilot-session-name',
              '--agent', 'copilot', '--clear-display-agent', '--seq', str(seq))


def persist_name(identity, name):
    """Ensure workspace.yaml records the session name."""
    session_dir = copilot_home() / 'session-state' / identity
    session_dir.mkdir(parents=True, exist_ok=True)
    workspace = session_dir / 'workspace.yaml'
    if workspace.is_file():
        try:
            text = workspace.read_text(encoding='utf-8')
        except OSError:
            text = ''
        if parse_workspace_name(text):
            return
        prefix = '' if (not text or text.endswith('\n')) else '\n'
        workspace.write_text(text + prefix + format_workspace_name(name), encoding='utf-8')
    else:
        workspace.write_text(f'id: {identity}\n' + format_workspace_name(name), encoding='utf-8')


def watch(identity, name, parent):
    """Wait for copilot startup, ensure workspace.yaml has the name, and report to Herdr."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            os.kill(parent, 0)
        except ProcessLookupError:
            return
        persist_name(identity, name)
        if not in_herdr():
            return
        try:
            pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
            if pane.get('agent') == 'copilot':
                report(pane['pane_id'], identity, name)
                return
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
        time.sleep(0.2)


def session_id_for_prefix(prefix):
    session_root = copilot_home() / 'session-state'
    if not session_root.is_dir():
        return None
    matches = []
    for entry in session_root.iterdir():
        if entry.is_dir() and UUID_RE.fullmatch(entry.name) and entry.name.startswith(prefix):
            matches.append(str(uuid.UUID(entry.name)))
    return matches[0] if len(matches) == 1 else None


def session_id_from_argv(argv, names):
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
        return session_id_for_prefix(selector)
    matches = [uid for uid, title in names.items() if title == selector]
    return matches[0] if len(matches) == 1 else None


def pane_identity(pane, names=None):
    session = pane.get('agent_session') or {}
    identity = session.get('value') if session.get('kind') == 'id' else None
    if identity:
        return str(uuid.UUID(identity))
    names = names if names is not None else native_names()
    try:
        info = herdr('pane', 'process-info', '--pane', pane['pane_id'])
        for process in info['result']['process_info']['foreground_processes']:
            if process.get('name') != 'copilot':
                continue
            resolved = session_id_from_argv(process.get('argv') or [], names)
            if resolved:
                return resolved
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        pass
    return None


def refresh():
    if not in_herdr_context():
        raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
    names = native_names()
    updated = 0
    for pane in herdr('pane', 'list')['result']['panes']:
        if pane.get('agent') != 'copilot':
            continue
        try:
            identity = pane_identity(pane, names)
            if not identity:
                continue
            report(pane['pane_id'], identity, names.get(identity, ''))
            updated += 1
        except (ValueError, KeyError, subprocess.SubprocessError) as exc:
            print(f'Copilot display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
    print(f'Copilot native names refreshed for {updated} pane(s).')


def main():
    if len(sys.argv) < 2:
        raise SessionError('Usage: named-session.py upsert|new|resume [NAME] [copilot options], or refresh|list')
    mode = sys.argv[1]
    if mode == 'refresh':
        refresh()
        return
    if mode == 'list':
        for title in sorted(set(native_names().values())):
            print(title)
        return
    if mode == '_watch':
        watch(sys.argv[2], sys.argv[3], int(sys.argv[4]))
        return
    if mode not in ('upsert', 'new', 'resume'):
        raise SessionError('Usage: cplt [session-name] [copilot options] | cpltn|cpltr <session-name> [copilot options]')
    binary = copilot_binary()
    if mode == 'upsert':
        if len(sys.argv) < 3:
            os.execvp(binary, [binary])
        if sys.argv[2] in ('-h', '--help'):
            print('Usage: cplt [session-name] [copilot options]')
            return
        if sys.argv[2].startswith('-'):
            os.execvp(binary, [binary, *sys.argv[2:]])
    elif len(sys.argv) < 3:
        raise SessionError('Usage: cpltn|cpltr <session-name> [copilot options]')
    name, args = sys.argv[2], sys.argv[3:]
    if name in ('-h', '--help'):
        print('Usage: cpltn|cpltr <session-name> [copilot options]')
        return
    if not name.strip() or name.startswith('-') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise SessionError('Session name must be nonempty printable text and must not start with a dash.')
    validate_args(args)
    names = native_names()
    if mode == 'upsert':
        matches = [uid for uid, title in names.items() if title == name]
        mode = 'resume' if matches else 'new'
    if mode == 'new':
        home = copilot_home()
        home.mkdir(parents=True, exist_ok=True)
        with (home / 'named-session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if name in native_names().values():
                raise SessionError(f'A native Copilot session named {name!r} already exists. Use cpltr.')
            identity = str(uuid.uuid4())
            persist_name(identity, name)
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), '_watch', identity, name, str(os.getpid())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f'Opening new Copilot session {name!r} ({identity})', file=sys.stderr)
        os.execvp(binary, [binary, '--session-id', identity, '--name', name, *args])
    else:
        identity = resolve_name(name, names)
        if in_herdr():
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '_watch', identity, name, str(os.getpid())],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        print(f'Opening Copilot session {name!r} ({identity})', file=sys.stderr)
        os.execvp(binary, [binary, '--resume', identity, *args])


if __name__ == '__main__':
    try:
        main()
    except (SessionError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'copilot named sessions: {error}', file=sys.stderr)
        sys.exit(1)
