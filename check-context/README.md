# check-context

Monitors Claude's context window usage and tells the user when it's getting full. The user decides what to do — continue or hand over to a fresh session.

## Why

Claude Code has a 200k token context window. Without awareness, Claude keeps working until auto-compaction silently drops conversation history. This skill surfaces context usage to the user so they can make informed decisions.

## How it works

Two thresholds, two hooks, one script:

| Zone | Hook | Behavior |
|---|---|---|
| Below `warn_threshold` | — | Silent. Claude works normally. |
| >= `warn_threshold` | UserPromptSubmit | Warns user once per message. User decides to continue or hand over. |
| >= `critical_threshold` | PostToolUse | Injects critical warning after every heavy tool call. Claude is told to stop and report. |

**UserPromptSubmit** fires before Claude processes each user message. If context is above `warn_threshold`, it injects a note that Claude relays to the user. Fires once per user message — no loops. If the user says "continue", Claude works uninterrupted until the next user message.

**PostToolUse** fires after heavy tool calls (`Read`, `Bash`, `Agent`, `WebFetch`). Only activates at `critical_threshold`. Injects a critical warning into Claude's context after every matching tool call, pressing it to stop and report to the user.

## Setup

### 1. Copy the `.claude` folder into your project

```bash
# If you don't have a .claude directory yet
cp -r /path/to/claude-skills/check-context/.claude .claude
```

If your project already has a `.claude` directory, merge the pieces:

```bash
mkdir -p .claude/skills
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
            "command": "python3 .claude/skills/check-context/claude-context.py prompt",
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
            "command": "python3 .claude/skills/check-context/claude-context.py tool",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

That's it. No CLAUDE.md changes needed — the hooks handle everything.

### 2. Configure thresholds (optional)

Edit `.claude/skills/check-context/settings.json`:

```json
{
  "warn_threshold": 50,
  "critical_threshold": 75
}
```

| Setting | Default | Description |
|---|---|---|
| `warn_threshold` | `50` | Context % at which the user is warned (once per message) |
| `critical_threshold` | `75` | Context % at which Claude is urged to stop after every tool call |

## What the user sees

**Below `warn_threshold`** — Nothing. Claude works normally.

**At `warn_threshold`** — Before processing the user's message, Claude informs them:
> Context is at 52% (104k/200k tokens). We can continue working or I can write a HANDOVER.md so a fresh session picks up where we left off.

**At `critical_threshold`** — After every heavy tool call, Claude is urged to stop:
> Context is at 76%. Continuing risks losing conversation history. I strongly recommend writing a HANDOVER.md and starting a fresh session.

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
    skills/
      check-context/
        SKILL.md                         # Manual /check-context skill
        settings.json                    # Threshold configuration
        claude-context.py                # Single script for hooks + manual check
```
