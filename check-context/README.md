# check-context

A skill that gives Claude awareness of its own context window usage. When context reaches a configurable threshold, Claude winds down gracefully — summarizing progress and offering to create a handover document so a fresh session can continue seamlessly.

## Why

Claude Code has a finite context window (200k tokens). Without awareness of how much is used, Claude will keep working until auto-compaction kicks in, which can cause loss of conversation context and disoriented behavior. This skill makes Claude check its usage periodically and act responsibly when it's running low.

## Setup

### 1. Copy the skill into your project

```bash
# From your project root
mkdir -p .claude/skills
cp -r /path/to/claude-skills/check-context .claude/skills/check-context
```

Or clone and symlink:

```bash
git clone git@github.com:Dujma/claude-skills.git ~/claude-skills
mkdir -p .claude/skills
ln -s ~/claude-skills/check-context .claude/skills/check-context
```

### 2. Add instructions to your CLAUDE.md

Add the following block to your project's `CLAUDE.md` (or create one if it doesn't exist). This tells Claude when and how to use the skill:

````markdown
## Context Management

You have a context-checking skill available at `.claude/skills/check-context`.

### When to check
- After completing each logical unit of work (a feature, a bug fix, a refactor)
- Before starting a new large task
- When you notice the conversation has been going on for a while
- Roughly every 3-5 tool call rounds during extended work sessions

### How to check
Invoke the `/check-context` skill. It will report your current context usage
and guide your next action based on the configured threshold.

### Rules
- Do NOT ignore the threshold. When context is high, stop and summarize.
- Never power through low context hoping it will be fine.
- If you hit the critical zone (>85%), write the handover document immediately.
- When offering the user a choice, be clear about the tradeoffs:
  continuing risks context loss, handover preserves everything for a fresh session.
````

### 3. Configure the threshold (optional)

Edit `.claude/skills/check-context/settings.json`:

```json
{
  "threshold_percent": 60,
  "check_interval": "every 3-5 tool calls, or after completing a logical unit of work",
  "on_threshold": "complete_and_ask"
}
```

| Setting | Default | Description |
|---|---|---|
| `threshold_percent` | `60` | Context usage % at which Claude should wind down and ask the user |
| `check_interval` | `"every 3-5 tool calls..."` | Human-readable hint for how often to check (read by Claude, not enforced programmatically) |
| `on_threshold` | `"complete_and_ask"` | Behavior when threshold is reached: finish current work, summarize, and ask user |

Lower the threshold if you want more headroom for the handover conversation. Raise it if you prefer Claude to work longer before stopping.

## How it works

1. The skill runs `claude-context.py`, which reads the current session's JSONL file from `~/.claude/projects/`
2. It calculates total token usage as a percentage of the model's context window
3. Based on the threshold in `settings.json`, Claude either continues or winds down:
   - **Below threshold**: Keep working normally
   - **At threshold**: Complete current task, provide a summary, ask user to continue or create a handover
   - **Critical (>85%)**: Write `HANDOVER.md` immediately and stop

## Standalone usage

The Python script can also be run directly from the terminal:

```bash
# Auto-detect the latest session for the current project
python3 .claude/skills/check-context/claude-context.py

# Check a specific session
python3 .claude/skills/check-context/claude-context.py <session-id>
```

Example output:

```json
{
  "session_id": "abc123",
  "model": "claude-sonnet-4-6",
  "used_tokens": 87500,
  "total_tokens": 200000,
  "percent_used": 43.8,
  "last_input_tokens": 85000,
  "last_cache_creation": 1500,
  "last_cache_read": 1000,
  "total_output_tokens": 12000,
  "assistant_messages": 15
}
```

## File structure

```
check-context/
  README.md           # This file
  SKILL.md            # Skill definition (instructions Claude follows)
  settings.json       # Configurable threshold and behavior
  claude-context.py   # Python script that reads session token usage
```
