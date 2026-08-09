from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

HOOK = {
    "matcher": "Write|Edit",
    "hooks": [{
        "type": "command",
        "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/protect_creator_zero.py\"",
    }],
}

def copy_tree(src: Path, dst: Path, force: bool):
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            if out.exists() and not force:
                raise SystemExit(f"Refusing to overwrite: {out}. Use --force after review.")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, out)

def merge_settings(path: Path):
    data = json.loads(path.read_text()) if path.exists() else {}
    pre = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
    marker = "protect_creator_zero.py"
    if marker not in json.dumps(pre):
        pre.append(HOOK)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default=".")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    target = Path(args.target).resolve()
    copy_tree(here/"payload/.creator-zero", target/".creator-zero", args.force)
    for child in (here/"payload/.claude").iterdir():
        if child.is_dir():
            copy_tree(child, target/".claude"/child.name, args.force)
    merge_settings(target/".claude/settings.json")
    print(f"Installed Creator-0 into {target}")
    print("Run: python -m unittest discover .creator-zero/tests -v")
    print("Then in Claude Code: /creator-zero <task>")

if __name__ == "__main__":
    main()
