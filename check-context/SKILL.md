---
name: check-context
description: Check context window usage. Invoke when context feels heavy or before deciding whether to restart.
user-invocable: true
---

## Current Context Usage

!`python3 check-context/claude-context.py`

## Decision Rules

Read context_restart_percent from pipeline.config.json if it exists (default 90).

- **percent_used > context_restart_percent**: Stop at a clean boundary. Restart session.
- **percent_used > 70**: Be aware. Avoid loading large files. Finish current task, then restart.
- **percent_used < 70**: Continue normally.

If auto-compaction triggers, treat it as an immediate signal to wrap up and restart.
Do NOT power through when context is running low.
