#!/usr/bin/env python3
"""Context window monitor for Claude Code.

Two hooks, two thresholds:
  - UserPromptSubmit (arg: "prompt"): warns user when context >= warn_threshold.
    Fires once per user message. No loops.
  - PostToolUse (arg: "tool"): hard block when context >= critical_threshold.
    Emergency brake during long runs.

Below warn_threshold: completely silent.
"""
import os, sys, json, glob

MODEL_CONTEXT_WINDOWS = {
    'claude-opus-4-6': 200000,
    'claude-sonnet-4-6': 200000,
    'claude-haiku-4-5': 200000,
}
DEFAULT_CONTEXT_WINDOW = 200000
DEFAULT_WARN_THRESHOLD = 50
DEFAULT_CRITICAL_THRESHOLD = 75


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


def get_context_usage():
    session_dir = find_session_dir()
    if not session_dir:
        return None

    session_file = find_latest_session(session_dir)
    if not session_file or not os.path.exists(session_file):
        return None

    model = None
    last_usage = None

    with open(session_file) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get('type') == 'assistant':
                msg = obj.get('message', {})
                if not model:
                    model = msg.get('model')
                usage = msg.get('usage', {})
                if usage:
                    last_usage = usage

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
    }


def handle_prompt():
    """UserPromptSubmit: warn user when context is above warn_threshold."""
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    warn = settings.get('warn_threshold', DEFAULT_WARN_THRESHOLD)
    percent = usage['percent_used']
    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)

    if percent < warn:
        sys.exit(0)

    msg = (
        f"[CONTEXT: {percent}% used ({used_k}k/{total_k}k tokens)] "
        f"Inform the user that context is getting high. "
        f"Offer two options: (1) continue working, accepting the risk of hitting limits, "
        f"or (2) write a HANDOVER.md to capture progress for a fresh session."
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": msg,
        }
    }))
    sys.exit(0)


def handle_tool():
    """PostToolUse: hard block when context is above critical_threshold."""
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    critical = settings.get('critical_threshold', DEFAULT_CRITICAL_THRESHOLD)
    percent = usage['percent_used']
    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)

    if percent < critical:
        sys.exit(0)

    msg = (
        f"CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens). "
        f"STOP and tell the user:\n"
        f"- Context is at {percent}% — continuing risks losing conversation history\n"
        f"- Summarize what was accomplished and what remains\n"
        f"- Strongly recommend writing HANDOVER.md and starting a fresh session"
    )
    print(json.dumps({
        "decision": "block",
        "reason": msg,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }))
    sys.exit(0)


def main():
    hook_type = sys.argv[1] if len(sys.argv) > 1 else "prompt"

    if hook_type == "tool":
        handle_tool()
    else:
        handle_prompt()


if __name__ == '__main__':
    main()
