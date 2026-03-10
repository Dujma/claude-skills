---
name: check-context
description: Check context window usage and report to the user.
user-invocable: true
---

## Current Context Usage

!`python3 .claude/skills/check-context/claude-context.py`

## What to do with this information

Read settings from `.claude/skills/check-context/settings.json` to get the threshold_percent (default: 60).

Report the context usage to the user clearly and concisely. Include:
- Current usage as a percentage and token count
- How much room is left
- A recommendation based on the level:

**Below threshold**: "Context is healthy at X%. Plenty of room to continue."

**At or above threshold**: "Context is at X%. I'd recommend we wrap up the current task. We can either continue (with the risk of hitting limits) or I can write a HANDOVER.md capturing everything so a fresh session can pick up right where we left off."

**Above 85%**: "Context is critically high at X%. I strongly recommend we stop here. Let me write a HANDOVER.md with everything needed for a fresh session to continue."

Always let the user make the final decision.
