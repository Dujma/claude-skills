# check-context

Monitors Claude's context window usage and tells the user when it's getting full. The user decides what to do — continue or hand over to a fresh session.

## Why

Claude Code has a 200k token context window. Without awareness, Claude keeps working until auto-compaction silently drops conversation history. This skill surfaces context usage to the user so they can make informed decisions.

## How it works

Two hooks, one script:

**UserPromptSubmit** — Fires before Claude processes each user message. If context is above threshold, it injects a note that Claude sees and relays to the user. Fires once per user message — no loops.

**PostToolUse** — Fires after heavy tool calls (`Read`, `Bash`, `Agent`, `WebFetch`). Catches context growth during long runs where the user isn't sending messages. Soft nudge at threshold, hard block at critical (>85%).

## Setup

### 1. Copy the `.claude` folder into your project

```bash
# If you don't have a .claude directory yet
cp -r /path/to/claude-skills/check-context/.claude .claude
```

If your project already has a `.claude` directory, merge the pieces:

```bash
mkdir -p .claude/hooks .claude/skills
cp /path/to/claude-skills/check-context/.claude/hooks/check-context.py .claude/hooks/
cp -r /path/to/claude-skills/check-context/.claude/skills/check-context .claude/skills/
```

Then merge the hook config into your `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-context.py prompt",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Read|Bash|Agent|WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-context.py tool",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### 2. Configure the threshold (optional)

Edit `.claude/skills/check-context/settings.json`:

```json
{
  "threshold_percent": 60,
  "on_threshold": "complete_and_ask"
}
```

| Setting | Default | Description |
|---|---|---|
| `threshold_percent` | `60` | Context usage % at which the hooks start reporting |
| `on_threshold` | `"complete_and_ask"` | Behavior: report to user, offer continue or handover |

That's it. No CLAUDE.md changes needed — the hooks handle everything.

## What the user sees

**Below threshold** — Nothing. Claude works normally.

**At threshold** — Claude informs the user:
> Context is at 62% (124k/200k tokens). We can continue (with the risk of hitting limits) or I can write a HANDOVER.md so a fresh session picks up where we left off. What would you prefer?

**Critical (>85%)** — Claude stops and recommends handover:
> Context is at 87%. Continuing risks losing conversation history. I strongly recommend writing a HANDOVER.md and starting a fresh session.

## Manual check

Invoke during a session:

```
/check-context
```

Or from the terminal:

```bash
python3 .claude/skills/check-context/claude-context.py
```

## File structure

```
check-context/
  README.md
  .claude/
    settings.json                        # Hook registration
    hooks/
      check-context.py                   # Single script for both hooks
    skills/
      check-context/
        SKILL.md                         # Manual /check-context skill
        settings.json                    # Threshold configuration
        claude-context.py                # Standalone context calculator
```
