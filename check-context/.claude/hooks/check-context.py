#!/usr/bin/env python3
"""Stop hook: safety net at the end of each Claude response.

Only fires on Claude's first response after a user message.
If Claude already responded (turn count > 1), we already notified
this turn — stay silent to avoid looping.
"""
import sys, json, os

sys.path.insert(0, os.path.join(os.getcwd(), '.claude', 'hooks'))
from context_lib import get_session_data, load_settings, DEFAULT_THRESHOLD


def main():
    data = get_session_data()
    if not data:
        sys.exit(0)

    # Only notify on Claude's first response after the user spoke.
    # If we already notified and Claude responded again, stay silent.
    if data['assistant_turns_since_user'] > 1:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = data['percent_used']
    used_k = round(data['used_tokens'] / 1000)
    total_k = round(data['total_tokens'] / 1000)

    if percent < threshold:
        sys.exit(0)

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

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"CONTEXT CHECK: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
            f"Tell the user:\n"
            f"- Context window is at {percent}% capacity\n"
            f"- Recommend finishing the current task and pausing\n"
            f"- Offer two options: (1) continue working (risk of hitting limits), "
            f"or (2) create a HANDOVER.md to capture progress for a fresh session\n"
            f"- If the user chooses to continue, keep working — you will be notified again when usage grows"
        )
    }))
    sys.exit(0)


if __name__ == '__main__':
    main()
