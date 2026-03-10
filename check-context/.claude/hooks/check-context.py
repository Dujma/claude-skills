#!/usr/bin/env python3
"""Stop hook: hard safety net at the end of each Claude response.

If context is above threshold, blocks Claude and forces it to report
to the user. This catches anything the mid-run nudge didn't.
Also resets the tool call counter so the next run starts fresh.
"""
import sys, json, os

sys.path.insert(0, os.path.join(os.getcwd(), '.claude', 'hooks'))
from context_lib import get_context_usage, load_settings, reset_counter, DEFAULT_THRESHOLD


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

    # Below threshold: silent
    if percent < threshold:
        sys.exit(0)

    # Critical zone: block and force report
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

    # At threshold: block and report
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"CONTEXT CHECK: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
            f"Tell the user:\n"
            f"- Context window is at {percent}% capacity\n"
            f"- Recommend finishing the current task and pausing\n"
            f"- Offer two options: (1) continue working (risk of hitting limits), "
            f"or (2) create a HANDOVER.md to capture progress for a fresh session\n"
            f"- If the user chooses to continue, keep working but warn again at 85%"
        )
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
