#!/usr/bin/env python3
"""Context window monitor for Claude Code.

Used by two hooks:
  - UserPromptSubmit (arg: "prompt"): injects context status before Claude
    processes each user message. No loop — fires once per user turn.
  - PostToolUse (arg: "tool"): mid-run nudge during long tool call chains.
    Soft nudge at threshold, hard block only at critical (>85%).
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
    """UserPromptSubmit: inject context status before Claude processes the prompt.

    Returns additionalContext that Claude sees alongside the user's message.
    Cannot loop — fires exactly once per user message.
    """
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = usage['percent_used']
    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)

    if percent < threshold:
        sys.exit(0)

    if percent > 85:
        msg = (
            f"[CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens)] "
            f"Before doing anything else, tell the user that context is critically high. "
            f"Summarize what has been accomplished so far and what remains. "
            f"Strongly recommend writing a HANDOVER.md and starting a fresh session. "
            f"Only continue if the user explicitly asks you to."
        )
    else:
        msg = (
            f"[CONTEXT: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%)] "
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
    """PostToolUse: mid-run nudge during long tool call chains.

    Soft nudge at threshold (Claude finishes current task then reports).
    Hard block only at critical (>85%).
    """
    usage = get_context_usage()
    if not usage:
        sys.exit(0)

    settings = load_settings()
    threshold = settings.get('threshold_percent', DEFAULT_THRESHOLD)
    percent = usage['percent_used']
    used_k = round(usage['used_tokens'] / 1000)
    total_k = round(usage['total_tokens'] / 1000)

    if percent < threshold:
        sys.exit(0)

    if percent > 85:
        msg = (
            f"CONTEXT CRITICAL: {percent}% used ({used_k}k/{total_k}k tokens). "
            f"Finish your immediate action, then STOP and tell the user:\n"
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
    else:
        msg = (
            f"Context nudge: {percent}% used ({used_k}k/{total_k}k tokens, threshold: {threshold}%). "
            f"Finish your current logical task, then pause and tell the user about context usage. "
            f"Offer to continue or create a HANDOVER.md."
        )
        print(json.dumps({
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
