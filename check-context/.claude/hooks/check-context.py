#!/usr/bin/env python3
"""Context window monitor for Claude Code.

Used by both hooks:
  - PostToolUse (arg: "tool"): soft nudge mid-run, hard block at critical
  - Stop (arg: "stop"): hard block at threshold, safety net

Dedup: counts assistant turns since last user message in the session JSONL.
If >1, we already notified this turn — stay silent.
"""
import os, sys, json, glob

MODEL_CONTEXT_WINDOWS = {
    'claude-opus-4-6': 200000,
    'claude-sonnet-4-6': 200000,
    'claude-haiku-4-5': 200000,
}
DEFAULT_CONTEXT_WINDOW = 200000
DEFAULT_THRESHOLD = 60


def find_session_dir():
    cwd = os.getcwd()
    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.isdir(projects_dir):
        return None
    expected_name = cwd.replace('/', '-').replace('.', '-')
    candidate = os.path.join(projects_dir, expected_name)
    if os.path.isdir(candidate):
        return candidate
    for name in os.listdir(projects_dir):
        candidate = os.path.join(projects_dir, name)
        if os.path.isdir(candidate) and expected_name.endswith(name):
            return candidate
    return None


def find_latest_session(session_dir):
    sessions = glob.glob(os.path.join(session_dir, '*.jsonl'))
    if not sessions:
        return None
    return max(sessions, key=os.path.getmtime)


def load_settings():
    settings_path = os.path.join(
        os.getcwd(), '.claude', 'skills', 'check-context', 'settings.json'
    )
    try:
        with open(settings_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_session_data():
    session_dir = find_session_dir()
    if not session_dir:
        return None

    session_file = find_latest_session(session_dir)
    if not session_file or not os.path.exists(session_file):
        return None

    model = None
    last_usage = None
    total_output = 0
    message_count = 0
    assistant_turns_since_user = 0

    with open(session_file) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get('type')
            if msg_type in ('human', 'user'):
                assistant_turns_since_user = 0
            if msg_type == 'assistant':
                assistant_turns_since_user += 1
                msg = obj.get('message', {})
                if not model:
                    model = msg.get('model')
                usage = msg.get('usage', {})
                if usage:
                    last_usage = usage
                    message_count += 1
                    total_output += usage.get('output_tokens', 0)

    if not last_usage or not model:
        return None

    input_tokens = last_usage.get('input_tokens', 0)
    cache_creation = last_usage.get('cache_creation_input_tokens', 0)
    cache_read = last_usage.get('cache_read_input_tokens', 0)
    used_tokens = input_tokens + cache_creation + cache_read
    context_window = MODEL_CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW)
    percent_used = round((used_tokens / context_window) * 100, 1)

    return {
        "used_tokens": used_tokens,
        "total_tokens": context_window,
        "percent_used": percent_used,
        "assistant_messages": message_count,
        "assistant_turns_since_user": assistant_turns_since_user,
    }


def main():
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "stop"

    data = get_session_data()
    if not data:
        sys.exit(0)

    if data['assistant_turns_since_user'] > 1:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = data['percent_used']
    used_k = round(data['used_tokens'] / 1000)
    total_k = round(data['total_tokens'] / 1000)

    if percent < threshold:
        sys.exit(0)

    # Critical (>85%): always hard block
    if percent > 85:
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens). "
                f"Finish your immediate action, then STOP and tell the user:\n"
                f"- Context is at {percent}% — continuing risks losing conversation history\n"
                f"- Summarize what was accomplished and what remains\n"
                f"- Offer to write a HANDOVER.md so a fresh session can continue\n"
                f"- Strongly recommend starting a new session"
            )
        }))
        sys.exit(0)

    # At threshold: tool hook nudges, stop hook blocks
    if hook_type == "tool":
        print(json.dumps({
            "reason": (
                f"Context nudge: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
                f"Finish your current logical task, then pause and tell the user about context usage. "
                f"Offer to continue or create a HANDOVER.md."
            )
        }))
    else:
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
