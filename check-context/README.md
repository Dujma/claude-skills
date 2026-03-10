# check-context

Gives Claude awareness of its context window and makes it communicate usage to the user. Uses two layers — a mid-run nudge during long tool call chains and a hard check at the end of each response — so context issues are caught early and reported honestly.

## Why

Claude Code has a 200k token context window. Without awareness, Claude will keep working until auto-compaction silently drops conversation history, leading to lost context and confused behavior. This skill makes Claude proactively tell the user when context is getting full, so the user can make an informed decision about whether to continue or start fresh.

## How it works

Two hooks work as layers:

### Layer 1: Mid-run nudge (PostToolUse)
Fires after heavy tool calls (`Read`, `Bash`, `Agent`, `WebFetch`) — the tools that inflate context. Uses a counter to only check every 10 calls, keeping overhead minimal.

- **Below threshold**: Silent. No output.
- **At threshold**: Soft nudge. Claude sees a message telling it to finish its current logical task, then pause and report to the user. Claude decides when the right moment is — it won't cut off mid-operation.
- **Critical (>85%)**: Hard block. Claude must finish its immediate action and stop.

### Layer 2: End-of-response safety net (Stop)
Fires after every Claude response. If context is above threshold and Claude didn't act on the mid-run nudge, this catches it with a hard block.

- **Below threshold**: Silent.
- **At threshold**: Block. Claude must report to the user before continuing.
- **Critical (>85%)**: Block. Claude must stop and recommend handover.

### The skill (manual)
The user or Claude can also invoke `/check-context` at any time for an on-demand status check.

## Setup

### 1. Copy the `.claude` folder into your project

```bash
# From your project root — if you don't have a .claude directory yet
cp -r /path/to/claude-skills/check-context/.claude .claude
```

If your project already has a `.claude` directory, merge the pieces:

```bash
# Copy the skill
mkdir -p .claude/skills
cp -r /path/to/claude-skills/check-context/.claude/skills/check-context .claude/skills/check-context

# Copy the hooks
mkdir -p .claude/hooks
cp /path/to/claude-skills/check-context/.claude/hooks/*.py .claude/hooks/
```

Then merge the hook config into your `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read|Bash|Agent|WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/check-context-tool.py",
            "timeout": 10
          }
        ]
      }
    ],
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

### Context hooks
Two hooks monitor your context usage automatically:
- A **mid-run nudge** fires periodically during tool calls. When you see it, finish your current logical task (don't stop mid-operation), then pause and report to the user.
- An **end-of-response check** fires after each response. If context is high, you MUST report before continuing.

You MUST relay context messages to the user honestly — do not downplay or skip them.
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
  "on_threshold": "complete_and_ask"
}
```

| Setting | Default | Description |
|---|---|---|
| `threshold_percent` | `60` | Context usage % at which hooks start reporting to the user |
| `on_threshold` | `"complete_and_ask"` | Behavior: finish current work, report to user, offer options |

The mid-run nudge checks every 10 heavy tool calls (configurable in `check-context-tool.py`).

## What the user sees

**Below threshold** — Nothing. Claude works normally.

**Mid-run nudge at threshold** — Claude finishes what it's doing, then:
> Context is at 62% (124k/200k tokens). I'd recommend we wrap up the current task. We can continue (with the risk of hitting limits) or I can write a HANDOVER.md so a fresh session picks up where we left off. What would you prefer?

**Critical (>85%)** — Claude stops as soon as safely possible:
> Context is at 87%. Continuing risks losing conversation history. I strongly recommend I write HANDOVER.md and we start a fresh session.

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
    settings.json                        # Hook registration (PostToolUse + Stop)
    hooks/
      context_lib.py                     # Shared logic (session detection, settings, counter)
      check-context.py                   # Stop hook (end-of-response safety net)
      check-context-tool.py              # PostToolUse hook (mid-run nudge)
    skills/
      check-context/
        SKILL.md                         # Manual skill definition
        settings.json                    # Threshold configuration
        claude-context.py                # Context usage calculator (standalone)
```
