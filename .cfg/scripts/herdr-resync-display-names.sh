#!/bin/sh
# Re-registers every visible Copilot pane's native session identity and
# display name without waiting for a sessionStart/stop hook to fire.
#
# display_agent is EPHEMERAL server-side pane metadata: it lives only in the
# running herdr server's memory, not in anything persisted to disk. It gets
# set in exactly two moments -- (1) the `copilot` wrapper's own immediate
# report at process launch and (2) the Copilot hooks after an activity event.
# A handoff can leave a still-running pane without either report. The live
# Copilot argv is the recovery proof: this script accepts a UUID selector, or
# a resume name with exactly one saved native ID. It never derives identity
# from a display name or title.
set -eu

command -v python3 >/dev/null 2>&1 || exit 0
command -v herdr >/dev/null 2>&1 || exit 0

python3 - <<'PY'
import json
import os
import re
import socket
import subprocess
import time

session_root = os.path.expanduser("~/.copilot/session-state")
uuid_re = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

def name_for_session_id(session_id):
    path = os.path.join(session_root, session_id, "workspace.yaml")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("name:"):
            rest = line[len("name:"):].strip()
            if rest in ("|-", "|", ">-", ">"):
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                    if lines[i].strip():
                        return lines[i].strip()
                    i += 1
                return None
            return rest.strip('"').strip("'")
        i += 1
    return None

def session_id_for_name(wanted_name):
    matches = []
    try:
        session_ids = os.listdir(session_root)
    except OSError:
        return None
    for session_id in session_ids:
        if not uuid_re.fullmatch(session_id):
            continue
        if name_for_session_id(session_id) == wanted_name:
            matches.append(session_id)
    return matches[0] if len(matches) == 1 else None

def session_id_for_prefix(prefix):
    try:
        matches = [
            session_id for session_id in os.listdir(session_root)
            if uuid_re.fullmatch(session_id) and session_id.startswith(prefix)
        ]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None

def session_id_from_argv(argv):
    selector = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--session-id="):
            selector = arg.split("=", 1)[1]
        elif arg == "--session-id" and i + 1 < len(argv):
            i += 1
            selector = argv[i]
        elif arg.startswith("--resume="):
            selector = arg.split("=", 1)[1]
        elif arg == "--resume" and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            i += 1
            selector = argv[i]
        i += 1

    if not selector:
        return None
    if uuid_re.fullmatch(selector):
        return selector
    if re.fullmatch(r"[0-9a-fA-F]{7,}", selector):
        return session_id_for_prefix(selector)
    return session_id_for_name(selector)

def session_id_from_process(pane_id):
    try:
        out = subprocess.run(
            ["herdr", "pane", "process-info", "--pane", pane_id],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        processes = json.loads(out)["result"]["process_info"]["foreground_processes"]
    except Exception:
        return None
    for process in processes:
        if process.get("name") == "copilot":
            return session_id_from_argv(process.get("argv") or [])
    return None

def report_session(pane_id, session_id):
    socket_path = os.environ.get("HERDR_SOCKET_PATH")
    if not socket_path:
        return False
    request = {
        "id": f"herdr:copilot:resync:{time.time_ns()}",
        "method": "pane.report_agent_session",
        "params": {
            "pane_id": pane_id,
            "source": "herdr:copilot",
            "agent": "copilot",
            "agent_session_id": session_id,
            "seq": time.time_ns(),
        },
    }
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(0.5)
        client.connect(socket_path)
        client.sendall((json.dumps(request) + "\n").encode())
        response = json.loads(client.recv(4096))
        client.close()
        return "result" in response
    except Exception:
        return False

try:
    out = subprocess.run(["herdr", "pane", "list"], capture_output=True, text=True, check=True).stdout
    panes = json.loads(out)["result"]["panes"]
except Exception as exc:
    print(f"herdr-resync-display-names: failed to list panes: {exc}")
    raise SystemExit(0)

registered = 0
renamed = 0
for pane in panes:
    if pane.get("agent") != "copilot":
        continue
    session = pane.get("agent_session") or {}
    session_id = session.get("value")
    if not session_id:
        session_id = session_id_from_process(pane["pane_id"])
    if not session_id or not uuid_re.fullmatch(session_id):
        continue
    if report_session(pane["pane_id"], session_id):
        registered += 1
    name = name_for_session_id(session_id)
    if not name:
        continue
    name = name[:60] + ("..." if len(name) > 60 else "")
    if pane.get("display_agent") == name:
        continue
    pane_id = pane["pane_id"]
    subprocess.run(
        [
            "herdr", "pane", "report-metadata", pane_id,
            "--source", "user:copilot-session-name",
            "--agent", "copilot",
            "--display-agent", name,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    renamed += 1
    print(f"resynced {pane_id}: {name}")

print(f"herdr-resync-display-names: registered {registered}, renamed {renamed} pane(s)")
PY
