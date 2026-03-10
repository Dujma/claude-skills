#!/usr/bin/env python3
"""Stop hook: safety net at the end of each Claude response.

If context is above threshold and we haven't already notified at this level,
blocks Claude and forces it to report to the user. Remembers the last
notification level so it won't fire again until context grows significantly.
Also resets the tool call counter so the next run starts fresh.
"""
import sys, json, os

sys.path.insert(0, os.path.join(os.getcwd(), '.claude', 'hooks'))
from context_lib import (
    get_context_usage, load_settings, reset_counter,
    should_notify, write_last_notified, DEFAULT_THRESHOLD,
)


def main():
    # Reset tool call counter at end of each response
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

    # Critical zone
    if percent > 85:
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens). "
                f"You MUST stop and tell the user:\n"
                f"- Context is at {percent}% — continuing risks losing conversation history\n"
                f"- Summarize what was accomplished and what remains\n"
                f"- Offer to write a HANDOVER.md so a fresh session can continue\n"
                f"- Strongly recommend starting a new session"
            )
        }))
        sys.exit(0)

    # At threshold
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"CONTEXT CHECK: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
            f"Tell the user:\n"
            f"- Context window is at {percent}% capacity\n"
            f"- Recommend finishing the current task and pausing\n"
            f"- Offer two options: (1) continue working (risk of hitting limits), "
            f"or (2) create a HANDOVER.md to capture progress for a fresh session\n"
            f"- If the user chooses to continue, keep working but warn again when usage grows significantly"
        )
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
