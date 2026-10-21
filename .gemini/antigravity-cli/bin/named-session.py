#!/usr/bin/env python3
"""Named Antigravity CLI sessions and Antigravity-only Herdr metadata refresh."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import uuid


class SessionError(RuntimeError):
    pass


def agy_home():
    return Path(os.environ.get('AGY_HOME') or Path.home() / '.gemini/antigravity-cli').expanduser()


def parse_pbtxt_title(text):
    """Parse a pbtxt string field `title: "..."` or `title:"..."`."""
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
    # Decode octal byte sequences as UTF-8 if present, otherwise standard escapes.
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


def format_pbtxt_title(name):
    escaped = name.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f'title:"{escaped}"'


def native_names():
    """Read native Antigravity titles from conversation_summaries.db and annotations/*.pbtxt."""
    names = {}
    home = agy_home()
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
                title = parse_pbtxt_title(pbtxt.read_text(encoding='utf-8'))
            except (OSError, ValueError, TypeError):
                continue
            if isinstance(title, str) and title.strip():
                names[identity] = title
    return names


def resolve_name(name, names):
    matches = [identity for identity, title in names.items() if title == name]
    if not matches:
        raise SessionError(f'No native Antigravity session named {name!r}. Use agyn to create it.')
    if len(matches) > 1:
        raise SessionError(
            f'Ambiguous native session name {name!r}; resume by UUID with agy --conversation: ' + ', '.join(matches)
        )
    return matches[0]


def validate_args(args, *, mode):
    for arg in args:
        if arg == '--':
            break
        if arg in ('-c', '--continue', '--conversation') or arg.startswith('--conversation='):
            raise SessionError('A named session is already selected; do not combine it with resume selectors.')


def herdr(*args):
    output = subprocess.check_output(['herdr', *args], text=True, stderr=subprocess.PIPE, timeout=5)
    return json.loads(output) if output.strip() else {}


def in_herdr():
    return os.environ.get('HERDR_ENV') == '1' and bool(os.environ.get('HERDR_PANE_ID'))


def report(pane_id, identity, name):
    herdr('pane', 'report-agent-session', pane_id, '--source', 'herdr:antigravity_cli',
          '--agent', 'agy', '--agent-session-id', identity)
    if name:
        display = name[:60] + ('...' if len(name) > 60 else '')
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:agy-session-name',
              '--agent', 'agy', '--display-agent', display)
    else:
        herdr('pane', 'report-metadata', pane_id, '--source', 'user:agy-session-name',
              '--agent', 'agy', '--clear-display-agent')


def persist_name(identity, name):
    """Persist user-supplied title to annotations/<uuid>.pbtxt and conversation_summaries.db."""
    home = agy_home()
    annotations_dir = home / 'annotations'
    annotations_dir.mkdir(parents=True, exist_ok=True)
    pbtxt = annotations_dir / f'{identity}.pbtxt'
    if not pbtxt.exists():
        pbtxt.write_text(format_pbtxt_title(name), encoding='utf-8')
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


def discover_child_session(parent_pid, before_locks):
    """Find the conversation UUID created by the launched agy process."""
    lock_dir = agy_home() / 'presence'
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


def watch(identity, name, parent, before_locks_csv=''):
    """Wait for agy startup, persist the initial name if new, and report to Herdr."""
    before_locks = set(filter(None, before_locks_csv.split(',')))
    deadline = time.monotonic() + 30
    named = bool(identity)
    while time.monotonic() < deadline:
        try:
            os.kill(parent, 0)
        except ProcessLookupError:
            return
        if not identity:
            identity = discover_child_session(parent, before_locks)
            if identity and not named:
                persist_name(identity, name)
                named = True
        if identity and not in_herdr():
            return
        if identity and in_herdr():
            try:
                pane = herdr('pane', 'get', os.environ['HERDR_PANE_ID'])['result']['pane']
                if pane.get('agent') == 'agy':
                    report(pane['pane_id'], identity, name)
                    return
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                pass
        time.sleep(0.2)


def pane_identity(pane):
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


def refresh():
    if not in_herdr():
        raise SessionError('Herdr refresh requires a Herdr-managed pane (HERDR_ENV=1).')
    names = native_names()
    updated = 0
    for pane in herdr('pane', 'list')['result']['panes']:
        if pane.get('agent') != 'agy':
            continue
        try:
            identity = pane_identity(pane)
            if not identity:
                continue
            report(pane['pane_id'], identity, names.get(identity, ''))
            updated += 1
        except (ValueError, KeyError, subprocess.SubprocessError) as exc:
            print(f'Antigravity display refresh failed for {pane["pane_id"]}: {exc}', file=sys.stderr)
    print(f'Antigravity native names refreshed for {updated} pane(s).')


def existing_locks():
    lock_dir = agy_home() / 'presence'
    if not lock_dir.is_dir():
        return set()
    locks = set()
    for lock_file in lock_dir.glob('*.lock'):
        try:
            locks.add(str(uuid.UUID(lock_file.stem)))
        except ValueError:
            continue
    return locks


def main():
    if len(sys.argv) < 2:
        raise SessionError('Usage: named-session.py new|resume NAME [agy options], or refresh')
    mode = sys.argv[1]
    if mode == 'refresh':
        refresh()
        return
    if mode == '_watch':
        watch(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else '')
        return
    if mode not in ('new', 'resume') or len(sys.argv) < 3:
        raise SessionError('Usage: agyn|agyr <session-name> [agy options]')
    name, args = sys.argv[2], sys.argv[3:]
    if name in ('-h', '--help'):
        print('Usage: agyn|agyr <session-name> [agy options]')
        return
    if not name.strip() or name.startswith('-') or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise SessionError('Session name must be nonempty printable text and must not start with a dash.')
    validate_args(args, mode=mode)
    names = native_names()
    if mode == 'new':
        if name in names.values():
            raise SessionError(f'A native Antigravity session named {name!r} already exists. Use agyr.')
        before = ','.join(sorted(existing_locks()))
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), '_watch', '', name, str(os.getpid()), before],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f'Opening new Antigravity session {name!r}', file=sys.stderr)
        os.execvp('agy', ['agy', *args])
    else:
        identity = resolve_name(name, names)
        if in_herdr():
            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '_watch', identity, name, str(os.getpid()), ''],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        print(f'Opening Antigravity session {name!r} ({identity})', file=sys.stderr)
        os.execvp('agy', ['agy', '--conversation', identity, *args])


if __name__ == '__main__':
    try:
        main()
    except (SessionError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'agy named sessions: {error}', file=sys.stderr)
        sys.exit(1)
