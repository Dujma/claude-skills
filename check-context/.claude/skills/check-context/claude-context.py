#!/usr/bin/env python3
"""Context window monitor for Claude Code.

Usage:
    python3 claude-context.py                # manual check (rich JSON output)
    python3 claude-context.py prompt         # UserPromptSubmit hook
    python3 claude-context.py tool           # PostToolUse hook
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


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
    settings_path = os.path.join(SCRIPT_DIR, 'settings.json')
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

    session_id = os.path.splitext(os.path.basename(session_file))[0]
    model = None
    last_usage = None
    total_output = 0
    message_count = 0

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
        "session_id": session_id,
        "model": model,
        "used_tokens": used_tokens,
        "total_tokens": context_window,
        "percent_used": percent_used,
        "last_input_tokens": input_tokens,
        "last_cache_creation": cache_creation,
        "last_cache_read": cache_read,
        "total_output_tokens": total_output,
        "assistant_messages": message_count,
    }


def handle_manual():
    """Manual /check-context invocation — rich JSON output."""
    usage = get_context_usage()
    if not usage:
        print(json.dumps({"error": "no_data", "message": "No session data found."}))
        sys.exit(1)
    print(json.dumps(usage, indent=2))


def handle_prompt():
    """UserPromptSubmit hook: warn user when context >= warn_threshold."""
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    warn = settings.get('warn_threshold', DEFAULT_WARN_THRESHOLD)
    percent = usage['percent_used']

    if percent < warn:
        sys.exit(0)

    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)
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
    """PostToolUse hook: inject critical warning when context >= critical_threshold."""
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    critical = settings.get('critical_threshold', DEFAULT_CRITICAL_THRESHOLD)
    percent = usage['percent_used']

    if percent < critical:
        sys.exit(0)

    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)
    msg = (
        f"[CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens)] "
        f"STOP what you are doing and tell the user:\n"
        f"- Context is at {percent}% — continuing risks losing conversation history\n"
        f"- Summarize what was accomplished and what remains\n"
        f"- Strongly recommend writing HANDOVER.md and starting a fresh session"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }))
    sys.exit(0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None

    if mode == "prompt":
        handle_prompt()
    elif mode == "tool":
        handle_tool()
    else:
        handle_manual()


if __name__ == '__main__':
    main()
