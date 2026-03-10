#!/usr/bin/env python3
"""Read Claude Code session JSONL to compute context usage.

Usage:
    python3 claude-context.py              # auto-detect latest session
    python3 claude-context.py <session-id> # specific session
"""
import os, sys, json, glob

MODEL_CONTEXT_WINDOWS = {
    'claude-opus-4-6': 200000,
    'claude-sonnet-4-6': 200000,
    'claude-haiku-4-5': 200000,
}
DEFAULT_CONTEXT_WINDOW = 200000


def find_session_dir():
    """Find the Claude project session directory for the current working directory."""
    cwd = os.getcwd()
    projects_dir = os.path.expanduser('~/.claude/projects')
    if not os.path.isdir(projects_dir):
        return None
    # Claude stores project dirs by replacing '/' and '.' with '-' in the path
    expected_name = cwd.replace('/', '-').replace('.', '-')
    candidate = os.path.join(projects_dir, expected_name)
    if os.path.isdir(candidate):
        return candidate
    # Fallback: try matching against all project directories
    for name in os.listdir(projects_dir):
        candidate = os.path.join(projects_dir, name)
        if os.path.isdir(candidate) and expected_name.endswith(name):
            return candidate
    return None


def find_latest_session(session_dir):
    """Find the most recently modified session JSONL in the directory."""
    sessions = glob.glob(os.path.join(session_dir, '*.jsonl'))
    if not sessions:
        return None
    return max(sessions, key=os.path.getmtime)


def main():
    session_dir = find_session_dir()
    if not session_dir:
        print(json.dumps({"error": "no_project", "message": "No Claude session directory found."}))
        sys.exit(1)

    if len(sys.argv) > 1:
        session_file = os.path.join(session_dir, f'{sys.argv[1]}.jsonl')
    else:
        session_file = find_latest_session(session_dir)

    if not session_file or not os.path.exists(session_file):
        print(json.dumps({"error": "no_session", "message": "No session file found."}))
        sys.exit(1)

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
        print(json.dumps({"error": "no_data", "message": "No assistant messages with usage data found."}))
        sys.exit(1)

    input_tokens = last_usage.get('input_tokens', 0)
    cache_creation = last_usage.get('cache_creation_input_tokens', 0)
    cache_read = last_usage.get('cache_read_input_tokens', 0)
    used_tokens = input_tokens + cache_creation + cache_read

    context_window = MODEL_CONTEXT_WINDOWS.get(model, DEFAULT_CONTEXT_WINDOW)
    percent_used = round((used_tokens / context_window) * 100, 1)

    result = {
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

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
