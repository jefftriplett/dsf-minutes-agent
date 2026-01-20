# DSF Minutes Agent (Unofficial)

An AI Agent that helps answer questions about Django Software Foundation board meeting minutes.

Please note: This is not official or legal advice.

## Usage

You can use either the `just ask` command or run the agent directly. Use `--year` to filter by a specific year:

```shell
# Ask about all years
$ just ask "What is the DSF balance history?"

# Ask about a specific year
$ just ask "Who are the 2026 board officers?" --year 2025

# Ask about bylaws changes
$ just ask "Did the DSF change any bylaws in 2025?" --year 2025

# Or run the agent directly
$ uv run src/agent.py "Who attended the most recent meeting?" --year 2025
```

## Installation

```shell
$ just bootstrap  # Install required tools
```

## Development

```shell
$ just           # List all available commands
$ just demo      # Run a demo with a sample question
$ just sync      # Pull latest minutes from GitHub
$ just fmt       # Format code using ruff
$ just lint      # Run linting on all files
```

## Data Source

The agent pulls board meeting minutes from the official [django/dsf-minutes](https://github.com/django/dsf-minutes) repository. The repository is automatically synced when the agent runs.
