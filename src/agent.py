#!/usr/bin/env -S uv --quiet run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "environs",
#     "fastmcp",
#     "pydantic-ai-slim[openai,web]>=2,<3",
#     "rich",
#     "typer",
#     "uvicorn",
# ]
# ///

import re
import subprocess
import typer
import uvicorn

from environs import env
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
from pydantic_ai import Agent
from rich.console import Console
from rich.table import Table

console = Console()

OPENAI_API_KEY: str = env.str("OPENAI_API_KEY")
PYDANTIC_AI_MODEL: str = env.str("PYDANTIC_AI_MODEL", default="openai:gpt-5.4-nano")

MINUTES_REPO_URL = "https://github.com/django/dsf-minutes.git"
MINUTES_DIR = Path(__file__).parent / "dsf-minutes"
SITE_URL = "https://django.github.io/dsf-minutes/"

# Meeting files are named YYYY-MM-DD.md. Anything else in a year directory
# (template.md, notes, drafts) is not a meeting.
MEETING_STEM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SYSTEM_PROMPT = """
<system_context>

You are a board minutes assistant for the Django Software Foundation.
You have access to the DSF board meeting minutes and can answer questions about
past board decisions, discussions, attendees, and actions.

</system_context>

<behavior_guidelines>

- Answer questions based only on the board meeting minutes provided.
- When referencing specific information, cite the meeting date.
- Prefer the most recent meeting when the question is about current state.
- If information is not found in the minutes, say so clearly rather than guessing.
- Please warn the user that this is not official or legal advice.

</behavior_guidelines>
"""


class Output(BaseModel):
    answer: str = Field(description="The answer to our question")
    reasoning: str = Field(description="The reasoning and support for our answer based on the meeting minutes")
    meetings: list[str] = Field(description="Meeting dates referenced (YYYY-MM-DD format)")


def sync_minutes_repo() -> None:
    """Clone or pull the dsf-minutes repository.

    Syncing is best effort: if the minutes are already on disk, a network or git
    problem should not stop the agent from answering with what it has.
    """
    # Check for .git, not just the directory. A contentful directory without .git makes
    # `git -C` resolve to the *parent* repo — which pulls this agent's own repository.
    if (MINUTES_DIR / ".git").exists():
        try:
            subprocess.run(
                ["git", "-C", str(MINUTES_DIR), "pull", "--quiet"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as error:
            console.print(f"[yellow]Could not update the minutes, using the local copy: {error}[/yellow]")
    elif MINUTES_DIR.exists():
        # Files are present but this is not a clone, so there is nothing to sync and
        # cloning into a non-empty directory would fail. Use what is on disk.
        console.print(f"[yellow]{MINUTES_DIR} is not a git clone — using the files as they are.[/yellow]")
    else:
        subprocess.run(
            ["git", "clone", "--quiet", MINUTES_REPO_URL, str(MINUTES_DIR)],
            check=True,
            capture_output=True,
        )


def meeting_url(minutes_file: Path) -> str:
    """Public URL for a meeting on the published minutes site."""
    date = minutes_file.stem
    return f"{SITE_URL}{date[:4]}/{date}/"


def discover_meetings(year: int | None = None) -> list[Path]:
    """Find meeting minutes on disk, newest first.

    Args:
        year: If specified, only look at that year's directory.
    """
    if year:
        year_dir = MINUTES_DIR / str(year)
        if not year_dir.exists():
            raise ValueError(f"No minutes found for year {year}")
        search_dirs = [year_dir]
    else:
        search_dirs = [d for d in MINUTES_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    meetings = [
        minutes_file
        for year_dir in search_dirs
        for minutes_file in year_dir.glob("*.md")
        if MEETING_STEM_RE.match(minutes_file.stem)
    ]

    # Stems are ISO dates, so a plain string sort is a date sort.
    return sorted(meetings, key=lambda minutes_file: minutes_file.stem, reverse=True)


def load_minutes(year: int | None = None, *, limit: int | None = None) -> str:
    """Load board meeting minutes from the repository.

    Args:
        year: If specified, only load minutes from that year.
              If None, load all minutes.
        limit: If specified, only load the N most recent meetings.
    """
    sync_minutes_repo()

    meetings = discover_meetings(year=year)
    if limit:
        meetings = meetings[:limit]

    # Discovery is newest first for --limit; feed the model oldest first so the
    # minutes read chronologically.
    return "\n\n---\n\n".join(
        f"<!-- Meeting: {minutes_file.stem} ({meeting_url(minutes_file)}) -->\n{minutes_file.read_text()}"
        for minutes_file in sorted(meetings, key=lambda minutes_file: minutes_file.stem)
    )


def get_agent(year: int | None = None, *, limit: int | None = None, output_type=Output) -> Agent:
    """Create an agent with DSF board meeting minutes loaded."""
    minutes = load_minutes(year=year, limit=limit)

    agent = Agent(
        model=PYDANTIC_AI_MODEL,
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


year_option = typer.Option(None, "--year", "-y", help="Filter minutes by year (e.g., 2025)")
limit_option = typer.Option(None, "--limit", "-n", help="Only load the N most recent meetings")


@app.command()
def ask(
    question: str,
    year: int | None = year_option,
    limit: int | None = limit_option,
):
    """Ask questions about DSF board meeting minutes."""
    scope = f"{year} only" if year else "all years"
    if limit:
        scope += f", {limit} most recent"
    console.print(f"[dim]Loading minutes ({scope})...[/dim]\n")

    agent = get_agent(year=year, limit=limit)
    result = agent.run_sync(question)

    console.print(
        f"[green][bold]Answer:[/bold][/green] {result.output.answer}\n\n"
        f"[yellow][bold]Reasoning:[/bold][/yellow] {result.output.reasoning}\n"
    )

    if result.output.meetings:
        console.print("[cyan][bold]Meetings Referenced:[/bold][/cyan]")
        for meeting in result.output.meetings:
            console.print(f"  - {meeting}")


@app.command(name="list")
def list_meetings(year: int | None = year_option):
    """List the board meetings available in the local minutes checkout."""
    sync_minutes_repo()
    meetings = discover_meetings(year=year)

    table = Table(title=f"DSF Board Meetings ({len(meetings)} total)")
    table.add_column("Date", style="cyan")
    table.add_column("URL", style="dim")

    for minutes_file in meetings:
        table.add_row(minutes_file.stem, meeting_url(minutes_file))

    console.print(table)


@app.command()
def sync():
    """Clone or update the local dsf-minutes checkout."""
    sync_minutes_repo()
    meetings = discover_meetings()

    console.print(f"[green]{len(meetings)} meetings available in {MINUTES_DIR}[/green]")


@app.command()
def web(
    year: int | None = year_option,
    limit: int | None = limit_option,
    host: str = "127.0.0.1",
    port: int = 8080,
):
    """Launch the minutes agent as a web chat interface."""
    # output_type=str keeps replies conversational. Pydantic AI v2 rejects None here —
    # it reads it as "no output types provided" and raises UserError.
    agent = get_agent(year=year, limit=limit, output_type=str)
    web_app = agent.to_web()

    console.print(f"[bold green]Starting web interface at http://{host}:{port}[/bold green]")
    uvicorn.run(web_app, host=host, port=port)


@app.command()
def debug(
    year: int | None = year_option,
    limit: int | None = limit_option,
):
    """Print the compiled system prompt for debugging."""
    minutes = load_minutes(year=year, limit=limit)

    console.print("[bold cyan]===== SYSTEM PROMPT =====[/bold cyan]\n")
    console.print(SYSTEM_PROMPT)
    console.print("\n[bold cyan]===== INSTRUCTIONS =====[/bold cyan]\n")
    console.print(f"<board_minutes>\n\n{minutes}\n\n</board_minutes>")
    console.print("\n[bold cyan]=========================[/bold cyan]")


@app.command()
def mcp(
    year: int | None = typer.Option(None, "--year", "-y", help="Filter minutes by year (e.g., 2025)"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Only load the N most recent meetings"),
    transport: str = typer.Option("stdio", help="MCP transport: stdio or http"),
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """Serve this agent as an MCP server so other agents can ask it questions.

    Pydantic AI is an MCP client, not a server, so FastMCP handles the server side.
    """
    from fastmcp import FastMCP

    server = FastMCP("dsf-minutes-agent")
    cached = {}

    def build_agent():
        """Build on first use — loading the documents up front would stall the handshake."""
        if "agent" not in cached:
            cached["agent"] = get_agent(year=year, limit=limit)
        return cached["agent"]

    @server.tool
    async def dsf_minutes_question(question: str) -> Output:
        """Answer a question about DSF board meeting minutes."""
        result = await build_agent().run(question)
        return result.output

    # stdio transport speaks JSON-RPC on stdout — log to stderr so we don't corrupt it.
    Console(stderr=True).print(f"[bold green]Serving MCP over {transport}[/bold green]")

    if transport == "http":
        server.run(transport="http", host=host, port=port)
    else:
        server.run()


# Maps a pydantic-ai model prefix to the env var holding that provider's key, so
# doctor notices when the model points at a provider you have no credentials for.
DOCTOR_PROVIDER_KEYS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "cohere": "CO_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "google": "GEMINI_API_KEY",
    "google-gla": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openai": "OPENAI_API_KEY",
}

DOCTOR_OPTIONAL_ENV: list[str] = []


def doctor_mask(value: str) -> str:
    """Show enough of a secret to recognize it, never enough to use it."""
    if len(value) <= 8:
        return "set"
    return f"{value[:4]}...{value[-4:]}"


def run_doctor(probe: bool = True) -> bool:
    """Report config/credential/connectivity status. Returns False on any failure."""
    results: list[tuple[str, str, str]] = []

    results.append(("pass", "Model", PYDANTIC_AI_MODEL))

    provider = PYDANTIC_AI_MODEL.split(":", 1)[0] if ":" in PYDANTIC_AI_MODEL else ""
    expected_key = DOCTOR_PROVIDER_KEYS.get(provider)
    if expected_key is None:
        results.append(
            ("warn", "Provider", f"unrecognized provider {provider!r}; cannot check its key")
        )
    elif value := env.str(expected_key, default=""):
        results.append(("pass", expected_key, doctor_mask(value)))
    else:
        results.append(("fail", expected_key, f"not set -- add {expected_key} to .env"))

    for name in DOCTOR_OPTIONAL_ENV:
        if value := env.str(name, default=""):
            results.append(("pass", name, doctor_mask(value)))
        else:
            results.append(("warn", name, "not set (optional; some features disabled)"))

    if probe:
        try:
            Agent(model=PYDANTIC_AI_MODEL).run_sync("Reply with: ok")
            results.append(("pass", "Live probe", "backend reachable and responding"))
        except Exception as exc:
            results.append(("fail", "Live probe", f"{type(exc).__name__}: {exc}"))
    else:
        results.append(("warn", "Live probe", "skipped (--no-probe)"))

    console.print("\n[bold]Doctor[/bold]\n")
    styles = {"pass": "green", "warn": "yellow", "fail": "red"}
    for status, label, detail in results:
        console.print(
            f"[{styles[status]}]{status.upper():<4}[/{styles[status]}] {label:<18} {detail}"
        )

    failed = sum(1 for status, _, _ in results if status == "fail")
    warned = sum(1 for status, _, _ in results if status == "warn")
    if failed:
        console.print(f"\n[red]{failed} failed[/red], {warned} warning(s)\n")
        return False
    console.print(f"\n[green]All checks passed[/green] ({warned} warning(s))\n")
    return True


@app.command()
def doctor(probe: bool = True):
    """Check configuration and credentials, then probe the LLM backend."""
    if not run_doctor(probe=probe):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
