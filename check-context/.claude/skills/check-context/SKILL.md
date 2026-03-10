---
name: check-context
description: Check context window usage. Invoke when context feels heavy or before deciding whether to restart.
user-invocable: true
---

## Current Context Usage

!`python3 .claude/skills/check-context/claude-context.py`

## Settings

Read settings from `.claude/skills/check-context/settings.json`:
- **threshold_percent**: The context usage percentage at which to wind down (default: 60)
- **on_threshold**: What to do when threshold is reached (default: "complete_and_ask")

## Decision Rules

Based on the percent_used from the script output and threshold_percent from settings:

### Below threshold (percent_used < threshold_percent)
Continue working normally. No action needed.

### At or above threshold (percent_used >= threshold_percent)
1. **Do NOT start new tasks.** Finish only the immediate, in-progress unit of work.
2. **Provide a summary** of what was accomplished in this session:
   - What was completed
   - What is still in progress or remaining
   - Any decisions made or issues encountered
3. **Ask the user** what they'd like to do next:
   - **Continue**: Keep working in this session (user accepts the risk of hitting context limits)
   - **Handover**: Document the full context into a handover file so a fresh session can pick up seamlessly

### Critical zone (percent_used > 85%)
Stop immediately after the current action. Provide the summary and strongly recommend the handover option. Do not wait for the user to decide — write the handover document proactively and inform the user it's ready.

### Auto-compaction detected
If Claude Code's auto-compaction triggers, treat it as an immediate signal that context is critically full. Write the handover document and stop.

## Handover Document Format

When writing a handover, create a file called `HANDOVER.md` in the project root with:

```markdown
# Session Handover

## Date
<current date>

## Summary
<what was accomplished>

## Current State
<what is in progress, what files were modified>

## Remaining Work
<what still needs to be done>

## Key Decisions
<any architectural or implementation decisions made>

## Notes
<anything the next session needs to know>
```
