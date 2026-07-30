# DSF Minutes Agent - Development Guide

## Commands
- `just` - List all available commands
- `just bootstrap` - Install pip and uv (Python package management)
- `just ask "<question>" [--year YYYY] [--limit N]` - Ask the agent a question
- `just list [--year YYYY]` - List the meetings in the local checkout
- `just sync` - Clone or update the local minutes checkout
- `just debug [--year YYYY] [--limit N]` - Print the compiled system prompt
- `just web` / `just mcp` - Serve the agent as a web chat or MCP server
- `just demo` - Run a demo with a sample question
- `just fmt` - Format the justfile using just's built-in formatter
- `just lint` - Run pre-commit hooks (prek) on all files

## Code Style Guidelines
- **Python version**: Target Python 3.12+
- **Line length**: 120 characters maximum
- **Linting**: Use ruff with E (pycodestyle) and F (pyflakes) rules
- **Formatting**: Follow PEP 8 conventions with ruff
- **Imports**: Sort imports with ruff
- **Type hints**: Use static typing throughout codebase
- **Error handling**: Use explicit try/except blocks with specific exception types
- **Naming**: Use snake_case for variables/functions, PascalCase for classes
- **Dependencies**: environs, fastmcp, pydantic-ai-slim[openai,web], rich, typer

## Project Structure
This tool uses OpenAI APIs to answer questions about DSF board meeting minutes.

Minutes are read from a local git checkout, never over the GitHub API:
- `sync_minutes_repo()` clones or pulls https://github.com/django/dsf-minutes into
  `src/dsf-minutes/`
- Syncing is best effort — a network or git failure falls back to the copy on disk
  rather than stopping the agent
- The guard checks for `src/dsf-minutes/.git`, not just the directory. A contentful
  directory without `.git` would make `git -C` resolve to *this* repo and pull the
  agent's own history
- `src/dsf-minutes/` is currently committed to this repo rather than gitignored, so
  `sync` prints a "not a git clone" warning and cannot pull. Loading still works

Meeting files are named `YYYY-MM-DD.md` under a year directory. `discover_meetings()`
matches that stem exactly, so templates and drafts in a year directory are skipped, and
returns newest-first so `--limit N` means "the N most recent". `load_minutes()` then
re-sorts chronologically before handing the documents to the model.

The agent is dependency-managed two ways: the PEP 723 header in `src/agent.py` (what
`uv run` actually uses) and `pyproject.toml`. Keep both lists in sync when adding a
dependency — only the header affects `just ask`, so a missing entry in `pyproject.toml`
breaks installs without ever failing locally.
