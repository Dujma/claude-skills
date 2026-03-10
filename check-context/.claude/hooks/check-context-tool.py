#!/usr/bin/env python3
"""PostToolUse hook: soft nudge during long runs.

Fires after heavy tool calls (Read, Bash, Agent, WebFetch).
No counter — just checks every time (reading the JSONL is fast).
Uses the same turn-count dedup: only nudges on the first response
after a user message, so it won't re-nudge if Claude already got the message.
"""
import sys, json, os

sys.path.insert(0, os.path.join(os.getcwd(), '.claude', 'hooks'))
from context_lib import get_session_data, load_settings, DEFAULT_THRESHOLD


def main():
    data = get_session_data()
    if not data:
        sys.exit(0)

    # Already notified this turn
    if data['assistant_turns_since_user'] > 1:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = data['percent_used']
    used_k = round(data['used_tokens'] / 1000)
    total_k = round(data['total_tokens'] / 1000)

    if percent < threshold:
        sys.exit(0)

    # Critical: hard block mid-run
    if percent > 85:
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens). "
                f"Finish your immediate action, then STOP and tell the user:\n"
                f"- Context is at {percent}% — continuing risks losing conversation history\n"
                f"- Summarize what was accomplished and what remains\n"
                f"- Strongly recommend writing HANDOVER.md and starting a fresh session"
            )
        }))
    else:
        # At threshold: soft nudge
        print(json.dumps({
            "reason": (
                f"Context nudge: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
                f"Finish your current logical task, then pause and tell the user about context usage. "
                f"Offer to continue or create a HANDOVER.md."
            )
        }))

    sys.exit(0)


if __name__ == '__main__':
    main()
