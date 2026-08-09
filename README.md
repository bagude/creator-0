# Creator-0 — Claude Code Harness v0.1

A small project-local Claude Code overlay implementing:

`Task -> Creator -> proposed HarnessSpec -> deterministic boundary/compiler -> authorized Harness -> optional child Creator`

## Install

```bash
python install.py /path/to/your/repository
```

Then start Claude Code in that repository and run:

```text
/creator-zero <task>
```

Fallback:

```text
@agent-creator-zero <task>
```

No Python package dependencies are required.

## Deterministic test suite

```bash
python -m unittest discover .creator-zero/tests -v
```

## Core invariant

`LLM output != typed intent != authorized topology != world transition`

Creator-0 may propose composition. It cannot rewrite the root rules that authorize composition.

## Maintenance

Normal Claude Code writes to Creator-0's root boundary/compiler files are blocked by a project `PreToolUse` hook. For deliberate maintenance, start Claude Code with `CREATOR_ZERO_MAINTENANCE=1`.
