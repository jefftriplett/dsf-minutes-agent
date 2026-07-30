# DSF Minutes Agent (Unofficial)

An AI Agent that helps answer questions about Django Software Foundation board meeting minutes.

Please note: This is not official or legal advice.

## Usage

```shell
# Ask about all years
just ask "What is the DSF balance history?"

# Ask about a specific year
just ask "Who are the 2026 board officers?" --year 2025

# Only load the most recent meetings (faster and cheaper)
just ask "What grants were approved recently?" --limit 5

# Or use uv directly
uv run src/agent.py ask "Who attended the most recent meeting?" --limit 1
```

## Available Commands

| Command | Description |
|---------|-------------|
| `just` | List all available commands |
| `just ask "<question>" [--year YYYY] [--limit N]` | Ask the minutes agent a question |
| `just list [--year YYYY]` | List the board meetings in the local checkout |
| `just web [--year YYYY] [--limit N]` | Launch the agent as a web chat interface |
| `just debug [--year YYYY] [--limit N]` | Print the compiled system prompt for debugging |
| `just demo` | Run a demo with a sample question |
| `just sync` | Clone or update the local minutes checkout |
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
