# DSF Minutes Agent (Unofficial)

An AI Agent that helps answer questions about Django Software Foundation board meeting minutes.

Please note: This is not official or legal advice.

## Usage

```shell
# Ask about all years
just ask "What is the DSF balance history?"

# Ask about a specific year
just ask "Who are the 2026 board officers?" --year 2025

# Or use uv directly
uv run src/agent.py ask "Who attended the most recent meeting?" --year 2025
```

## Available Commands

| Command | Description |
|---------|-------------|
| `just` | List all available commands |
| `just ask "<question>" [--year YYYY]` | Ask the minutes agent a question |
| `just debug [--year YYYY]` | Print the compiled system prompt for debugging |
| `just demo` | Run a demo with a sample question |
| `just sync` | Pull latest minutes from GitHub |
| `just bootstrap` | Install pip and uv |
| `just fmt` | Format code |
| `just lint` | Run pre-commit hooks on all files |
| `just lint-autoupdate` | Update pre-commit hooks to latest versions |

## Data Source

The agent pulls board meeting minutes from the official [django/dsf-minutes](https://github.com/django/dsf-minutes) repository. The repository is automatically synced when the agent runs.

## Requirements

- Python 3.12+
- OpenAI API key (set `OPENAI_API_KEY` environment variable)

## Installation

```shell
just bootstrap
```
