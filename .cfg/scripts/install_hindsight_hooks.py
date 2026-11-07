#!/usr/bin/env python3
"""Register cfg's reminders while preserving machine-owned hook registrations."""
import json
from pathlib import Path

home = Path.home()
path = home / ".codex/hooks.json"
script = home / ".codex/hooks/hindsight_reminder.py"
if not script.is_file():
    raise SystemExit(f"Missing hook script: {script}")
data = json.loads(path.read_text()) if path.exists() else {}
command = '/usr/bin/python3 "' + str(script) + '"'
for event in ("SessionStart", "UserPromptSubmit"):
    groups = data.setdefault("hooks", {}).setdefault(event, [])
    if any(h.get("command") == command for g in groups for h in g.get("hooks", [])):
        continue
    groups.append({"hooks": [{"type": "command", "command": command,
                             "timeout": 5, "statusMessage": "Personal memory reminder"}]})
path.write_text(json.dumps(data, indent=2) + "\n")
print("Registered Hindsight reminders. Review and trust them in Codex /hooks or Settings > Hooks.")
