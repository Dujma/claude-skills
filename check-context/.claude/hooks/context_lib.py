"""Shared context-checking logic used by both hooks."""
import os, json, glob

MODEL_CONTEXT_WINDOWS = {
    'claude-opus-4-6': 200000,
    'claude-sonnet-4-6': 200000,
    'claude-haiku-4-5': 200000,
}
DEFAULT_CONTEXT_WINDOW = 200000
DEFAULT_THRESHOLD = 60
COUNTER_FILE = '/tmp/claude-context-hook-counter'


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
        "used_tokens": used_tokens,
        "total_tokens": context_window,
        "percent_used": percent_used,
        "assistant_messages": message_count,
    }


def read_counter():
    try:
        with open(COUNTER_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_counter(n):
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(n))


def reset_counter():
    write_counter(0)
