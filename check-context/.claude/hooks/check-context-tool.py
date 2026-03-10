#!/usr/bin/env python3
"""PostToolUse hook: soft nudge during long runs.

Fires after heavy tool calls (Read, Bash, Agent, WebFetch).
Uses a counter to only check every N calls, avoiding overhead.
Also checks the notification guard so it won't re-nudge after
the user has already been informed at this context level.
"""
import sys, json, os

sys.path.insert(0, os.path.join(os.getcwd(), '.claude', 'hooks'))
from context_lib import (
    get_context_usage, load_settings, read_counter, write_counter,
    reset_counter, should_notify, write_last_notified, DEFAULT_THRESHOLD,
)

CHECK_EVERY_N = 10


def main():
    # Increment counter
    count = read_counter() + 1
    write_counter(count)

    # Only check every N tool calls
    if count < CHECK_EVERY_N:
        sys.exit(0)

    # Reset counter and do the check
    reset_counter()

    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = usage['percent_used']
    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)

    # Check if we should notify (handles dedup)
    if not should_notify(percent, threshold):
        sys.exit(0)

    # Record that we notified at this level
    write_last_notified(percent)

    # Critical: hard block
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
