# Claude Skills

A collection of reusable skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Skills are self-contained modules that extend Claude's capabilities within a project. Each skill lives in its own directory with a `SKILL.md` definition, optional settings, and any supporting scripts.

## Available Skills

| Skill | Description |
|---|---|
| [check-context](./check-context/) | Context window awareness — monitors token usage and guides graceful session wind-down |

## Usage

Copy or symlink any skill into your project's `.claude/skills/` directory. See each skill's README for setup instructions.
