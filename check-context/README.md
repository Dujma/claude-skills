# check-context

Gives Claude awareness of its context window and makes it communicate usage to the user. When context gets high, Claude automatically reports the status and recommends next steps — continue or hand over to a fresh session.

## Why

Claude Code has a 200k token context window. Without awareness, Claude will keep working until auto-compaction silently drops conversation history, leading to lost context and confused behavior. This skill makes Claude proactively tell the user when context is getting full, so the user can make an informed decision about whether to continue or start fresh.

## How it works

Two mechanisms work together:

1. **Stop hook** (automatic) — A hook runs after every Claude response. When context crosses the configured threshold, it interrupts Claude and forces it to report usage to the user with a recommendation.
2. **Skill** (manual) — The user or Claude can invoke `/check-context` at any time to see current usage.

The hook is the safety net. It fires automatically and cannot be skipped.

## Setup

### 1. Copy the `.claude` folder into your project

```bash
# From your project root — if you don't have a .claude directory yet
cp -r /path/to/claude-skills/check-context/.claude .claude
```

If your project already has a `.claude` directory, merge the pieces:

```bash
# Copy the skill
cp -r /path/to/claude-skills/check-context/.claude/skills/check-context .claude/skills/check-context

# Copy the hook
mkdir -p .claude/hooks
cp /path/to/claude-skills/check-context/.claude/hooks/check-context.py .claude/hooks/check-context.py
```

Then add the hook to your `.claude/settings.json` (create it if it doesn't exist):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-context.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

If you already have a `settings.json` with hooks, merge the `Stop` entry into your existing hooks.

### 2. Add instructions to your CLAUDE.md

Add the following block to your project's `CLAUDE.md`. This gives Claude the right mindset for managing context throughout the session:

````markdown
## Context Awareness

You are working within a finite context window. Be mindful of this at all times.

### Planning
- When the user asks for a large change, break it into smaller, independently committable steps.
- Present the plan to the user BEFORE starting. Let them prioritize what fits in this session.
- Prefer incremental progress over ambitious scope. It is better to complete 3 small tasks well than to get halfway through 1 large task and run out of context.
- If a task is too large for one session, say so upfront and propose a multi-session approach.

### During work
- Stay focused on the current task. Avoid reading files or exploring code that isn't directly relevant.
- Don't load entire large files when you only need a specific section.
- When you finish a unit of work, briefly tell the user what was done and what's next.

### Context hook
A hook monitors your context usage automatically. When it fires, it means context is getting high.
You MUST relay its message to the user honestly — do not downplay or skip it.
When context is high, always offer the user two clear options:
1. **Continue** — keep working, accepting the risk that context may run out
2. **Handover** — you write a HANDOVER.md capturing full session state so a new session can continue seamlessly

### Handover format
When writing a handover, create `HANDOVER.md` in the project root:
```
# Session Handover — <date>
## Completed
<what was accomplished, with file paths and commit hashes if applicable>
## In Progress
<what is partially done, current state>
## Remaining
<what still needs to be done>
## Key Decisions
<architectural or implementation decisions made>
## Context
<anything a fresh session needs to know to continue effectively>
```
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
| `threshold_percent` | `60` | Context usage % at which the hook starts reporting to the user |
| `check_interval` | `"every 3-5 tool calls..."` | Hint for manual checking frequency (read by Claude, not enforced) |
| `on_threshold` | `"complete_and_ask"` | Behavior: finish current work, report to user, offer options |

Lower the threshold for more headroom. Raise it if you prefer Claude to work longer before alerting.

## What the user sees

**Below threshold** — Nothing. Claude works normally.

**At threshold (default 60%)** — Claude pauses and tells the user:
> Context is at 62% (124k/200k tokens). I'd recommend finishing the current task. We can continue (with the risk of hitting limits) or I can write a HANDOVER.md so a fresh session picks up where we left off. What would you prefer?

**Critical (>85%)** — Claude stops and strongly recommends handover:
> Context is at 87%. Continuing risks losing conversation history. I've written HANDOVER.md with everything needed. I recommend starting a fresh session.

## Standalone usage

Check context from the terminal:

```bash
python3 .claude/skills/check-context/claude-context.py
```

Or invoke manually during a session:

```
/check-context
```

## File structure

```
check-context/
  README.md
  .claude/
    settings.json                        # Hook registration
    hooks/
      check-context.py                   # Stop hook (automatic context monitoring)
    skills/
      check-context/
        SKILL.md                         # Manual skill definition
        settings.json                    # Threshold configuration
        claude-context.py                # Context usage calculator
```
