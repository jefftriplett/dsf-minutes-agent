#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "environs",
#     "pydantic-ai-slim[openai]>=2,<3",
#     "pydantic-ai-slim[web]>=2,<3",
#     "rich",
#     "typer",
#     "uvicorn",
# ]
# ///

import subprocess
import typer
import uvicorn

from environs import env
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from rich.console import Console

console = Console()

OPENAI_API_KEY: str = env.str("OPENAI_API_KEY")
OPENAI_MODEL_NAME: str = env.str("OPENAI_MODEL_NAME", default="openai:gpt-5.4-nano")

MINUTES_REPO_URL = "https://github.com/django/dsf-minutes.git"
MINUTES_DIR = Path(__file__).parent / "dsf-minutes"

SYSTEM_PROMPT = """
<system_context>

You are a board minutes assistant for the Django Software Foundation.
You have access to the DSF board meeting minutes and can answer questions about
past board decisions, discussions, attendees, and actions.

</system_context>

<behavior_guidelines>

- Answer questions based on the board meeting minutes provided.
- When referencing specific information, cite the meeting date.
- If information is not found in the minutes, say so clearly.
- Please warn the user that this is not official or legal advice.

</behavior_guidelines>
"""


class Output(BaseModel):
    answer: str = Field(description="The answer to our question")
    reasoning: str = Field(description="The reasoning and support for our answer based on the meeting minutes")
    meetings: list[str] = Field(description="Meeting dates referenced (YYYY-MM-DD format)")


def sync_minutes_repo() -> None:
    """Clone or pull the dsf-minutes repository."""
    if MINUTES_DIR.exists():
        subprocess.run(
            ["git", "-C", str(MINUTES_DIR), "pull", "--quiet"],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            ["git", "clone", "--quiet", MINUTES_REPO_URL, str(MINUTES_DIR)],
            check=True,
            capture_output=True,
        )


def load_minutes(year: int | None = None) -> str:
    """Load board meeting minutes from the repository.

    Args:
        year: If specified, only load minutes from that year.
              If None, load all minutes.
    """
    sync_minutes_repo()

    minutes_content: list[str] = []

    if year:
        year_dir = MINUTES_DIR / str(year)
        if not year_dir.exists():
            raise ValueError(f"No minutes found for year {year}")
        search_dirs = [year_dir]
    else:
        search_dirs = [d for d in MINUTES_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    for year_dir in sorted(search_dirs):
        for minutes_file in sorted(year_dir.glob("*.md")):
            if minutes_file.name == "template.md":
                continue
            content = minutes_file.read_text()
            minutes_content.append(f"<!-- Meeting: {minutes_file.name} -->\n{content}")

    return "\n\n---\n\n".join(minutes_content)


def get_agent(year: int | None = None, *, output_type=Output) -> Agent:
    """Create an agent with DSF board meeting minutes loaded."""
    minutes = load_minutes(year=year)

    agent = Agent(
        model=OPENAI_MODEL_NAME,
        output_type=output_type,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.instructions
    def add_board_minutes() -> str:
        return f"<board_minutes>\n\n{minutes}\n\n</board_minutes>"

    return agent


app = typer.Typer(
    help="DSF Minutes Agent - Ask questions about DSF board meeting minutes",
    no_args_is_help=True,
)


@app.command()
def ask(
    question: str,
    year: int | None = typer.Option(None, "--year", "-y", help="Filter minutes by year (e.g., 2025)"),
):
    """Ask questions about DSF board meeting minutes."""
    agent = get_agent(year=year)

    year_info = f" ({year} only)" if year else " (all years)"
    console.print(f"[dim]Loading minutes{year_info}...[/dim]\n")

    result = agent.run_sync(question)

    console.print(
        f"[green][bold]Answer:[/bold][/green] {result.output.answer}\n\n"
        f"[yellow][bold]Reasoning:[/bold][/yellow] {result.output.reasoning}\n"
    )

    if result.output.meetings:
        console.print("[cyan][bold]Meetings Referenced:[/bold][/cyan]")
        for meeting in result.output.meetings:
            console.print(f"  - {meeting}")


@app.command()
def web(
    year: int | None = typer.Option(None, "--year", "-y", help="Filter minutes by year (e.g., 2025)"),
    host: str = "127.0.0.1",
    port: int = 8080,
):
    """Launch the minutes agent as a web chat interface."""
    agent = get_agent(year=year, output_type=None)
    web_app = agent.to_web()

    console.print(f"[bold green]Starting web interface at http://{host}:{port}[/bold green]")
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def debug(
    year: int | None = typer.Option(None, "--year", "-y", help="Filter minutes by year (e.g., 2025)"),
):
    """Print the compiled system prompt for debugging."""
    minutes = load_minutes(year=year)

    console.print("[bold cyan]===== SYSTEM PROMPT =====[/bold cyan]\n")
    console.print(SYSTEM_PROMPT)
    console.print("\n[bold cyan]===== INSTRUCTIONS =====[/bold cyan]\n")
    console.print(f"<board_minutes>\n\n{minutes}\n\n</board_minutes>")
    console.print("\n[bold cyan]=========================[/bold cyan]")


if __name__ == "__main__":
    app()
