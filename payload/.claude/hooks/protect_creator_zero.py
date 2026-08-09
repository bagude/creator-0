from __future__ import annotations
import json, os, sys
PROTECTED=(
"/.creator-zero/cz.py",
"/.creator-zero/contracts/root_contract.json",
"/.claude/hooks/protect_creator_zero.py",
"/.claude/skills/creator-zero/SKILL.md",
"/.claude/agents/creator-zero.md",
"/.claude/settings.json",
)
if os.environ.get("CREATOR_ZERO_MAINTENANCE")=="1": raise SystemExit(0)
try: d=json.load(sys.stdin)
except Exception: raise SystemExit(0)
if d.get("tool_name") in {"Write","Edit"}:
    p=str(d.get("tool_input",{}).get("file_path","")).replace("\\","/")
    if any(p.endswith(s) for s in PROTECTED):
        print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Creator-0 root law is protected. Launch with CREATOR_ZERO_MAINTENANCE=1 for deliberate maintenance."}}))
