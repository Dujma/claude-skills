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
NOTIFIED_FILE = '/tmp/claude-context-hook-notified'
RENOTIFY_INCREMENT = 10  # only notify again after this many % more usage


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


def read_last_notified():
    """Read the percentage at which we last notified."""
    try:
        with open(NOTIFIED_FILE) as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0.0


def write_last_notified(percent):
    with open(NOTIFIED_FILE, 'w') as f:
        f.write(str(percent))


def should_notify(current_percent, threshold):
    """Check if we should notify based on last notification.

    Returns True if:
    - We haven't notified yet and we're above threshold
    - Context has grown by RENOTIFY_INCREMENT since last notification
    - We're in the critical zone (>85%) and haven't notified for this zone
    """
    last = read_last_notified()

    if current_percent < threshold:
        return False

    # Never notified above threshold yet
    if last < threshold:
        return True

    # Context grew by the increment since last notification
    if current_percent >= last + RENOTIFY_INCREMENT:
        return True

    return False
