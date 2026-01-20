set dotenv-load := false

export JUST_UNSTABLE := "true"

# List all available commands
@_default:
    just --list

# Ask the minutes agent a question (use --year/-y to filter by year)
@ask question *ARGS:
    uv --quiet run src/agent.py ask "{{ question }}" {{ ARGS }}

# Print the compiled system prompt for debugging
@debug *ARGS:
    uv --quiet run src/agent.py debug {{ ARGS }}

# Install pip and uv package management tools
@bootstrap *ARGS:
    pip install --upgrade pip uv

# Run a demo with a sample question (2025 minutes)
@demo:
    just ask "Who are the 2026 board officers?" --year 2025

# Format code using just's built-in formatter
@fmt:
    just --fmt

# Run pre-commit checks on files
@lint *ARGS="--all-files":
    uv --quiet tool run --with pre-commit-uv pre-commit run {{ ARGS }}

# Sync the dsf-minutes repository
@sync:
    cd dsf-minutes && git pull || git clone https://github.com/django/dsf-minutes.git
