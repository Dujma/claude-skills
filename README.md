# Claude Skills

Reusable skills for Claude Code.

## check-context

Checks Claude Code context window usage by reading session JSONL files. Reports token usage as a percentage and provides decision rules for when to restart sessions.

### Installation

Add to your project's `.claude/skills/` directory or reference from this repo:

```bash
# Copy into your project
cp -r check-context/ /path/to/your/project/.claude/skills/check-context/
```

### Usage

The skill reads the current session's JSONL file from `~/.claude/projects/` and outputs:
- Token usage (used / total)
- Percentage of context window consumed
- Per-message breakdown (input, cache, output tokens)

Can also be run standalone:

```bash
python3 check-context/claude-context.py              # auto-detect latest session
python3 check-context/claude-context.py <session-id> # specific session
```
