"""Shared utilities: logging, HTTP fetching, freshness checks."""

import sys
import time
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel

import config

# ── Console ────────────────────────────────────────────────────────────────
console      = Console()
err_console  = Console(stderr=True)

# ── File logger ───────────────────────────────────────────────────────────
_file_handler = logging.FileHandler(config.ERROR_LOG, encoding="utf-8")
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s — %(message)s")
)
error_logger = logging.getLogger("policy_optimiser")
error_logger.setLevel(logging.DEBUG)
error_logger.addHandler(_file_handler)


def log_error(context: str, exc: Exception | None = None, extra: str = "") -> None:
    """Write a timestamped error to errors.log and print to stderr."""
    msg = f"{context}"
    if extra:
        msg += f" | {extra}"
    if exc:
        msg += f" | {type(exc).__name__}: {exc}"
    error_logger.error(msg)
    if exc:
        error_logger.debug(traceback.format_exc())
    err_console.print(f"[bold red]ERROR:[/bold red] {msg}")


def fatal(context: str, exc: Exception | None = None, extra: str = "") -> None:
    """Log a fatal error and halt execution. Never silently continues."""
    log_error(context, exc, extra)
    err_console.print(
        Panel(
            f"[bold red]FATAL — execution halted[/bold red]\n{context}"
            + (f"\n{extra}" if extra else "")
            + (f"\n{type(exc).__name__}: {exc}" if exc else ""),
            title="[red]FATAL ERROR[/red]",
            border_style="red",
        )
    )
    sys.exit(1)


def fetch_json(url: str, params: dict | None = None, label: str = "") -> dict:
    """
    HTTP GET → JSON with retry logic.
    Halts (fatal) if all retries fail or response is not valid JSON.
    Prints source URL and retrieval timestamp on success.
    """
    tag = label or url
    for attempt in range(1, config.REQUEST_RETRIES + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=config.HEADERS,
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            console.print(
                f"[green]✓[/green] Fetched [cyan]{tag}[/cyan]\n"
                f"  URL      : {resp.url}\n"
                f"  Retrieved: {retrieved_at}"
            )
            return data
        except requests.exceptions.HTTPError as e:
            log_error(f"HTTP {e.response.status_code} fetching {tag}", e)
            if attempt < config.REQUEST_RETRIES:
                _sleep_retry(attempt)
            else:
                fatal(f"All {config.REQUEST_RETRIES} attempts failed for {tag}", e)
        except requests.exceptions.ConnectionError as e:
            log_error(f"Connection error fetching {tag}", e)
            if attempt < config.REQUEST_RETRIES:
                _sleep_retry(attempt)
            else:
                fatal(f"All {config.REQUEST_RETRIES} attempts failed for {tag}", e)
        except requests.exceptions.Timeout as e:
            log_error(f"Timeout fetching {tag}", e)
            if attempt < config.REQUEST_RETRIES:
                _sleep_retry(attempt)
            else:
                fatal(f"All {config.REQUEST_RETRIES} attempts failed for {tag}", e)
        except ValueError as e:
            fatal(f"Response from {tag} is not valid JSON", e)

    # Should never reach here
    fatal(f"Unexpected exit from retry loop for {tag}")


def _sleep_retry(attempt: int) -> None:
    wait = config.REQUEST_BACKOFF * attempt
    console.print(f"[yellow]  Retry {attempt} in {wait:.0f}s …[/yellow]")
    time.sleep(wait)


def check_data_freshness(data_date: datetime | str | None, source: str) -> None:
    """
    Warn if data is older than MAX_DATA_AGE_MONTHS.
    Prompts the user whether to continue; halts if they say no.
    """
    if data_date is None:
        console.print(f"[yellow]WARNING:[/yellow] Cannot determine data date for {source}.")
        return

    if isinstance(data_date, str):
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                data_date = datetime.strptime(data_date, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                pass
        else:
            console.print(f"[yellow]WARNING:[/yellow] Cannot parse data date '{data_date}' for {source}.")
            return

    now = datetime.now(timezone.utc)
    age_months = (now.year - data_date.year) * 12 + (now.month - data_date.month)

    if age_months > config.MAX_DATA_AGE_MONTHS:
        console.print(
            Panel(
                f"[bold yellow]DATA AGE WARNING[/bold yellow]\n"
                f"Source  : {source}\n"
                f"Data date: {data_date.strftime('%Y-%m-%d')}\n"
                f"Age     : ~{age_months} months (limit: {config.MAX_DATA_AGE_MONTHS})\n\n"
                f"Continue? [y/N]",
                title="[yellow]STALE DATA[/yellow]",
                border_style="yellow",
            )
        )
        answer = input("Continue with stale data? [y/N]: ").strip().lower()
        if answer != "y":
            fatal(f"User rejected stale data from {source} (age {age_months} months).")


def print_section(title: str) -> None:
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))


def print_summary(rows: list[tuple[str, str]]) -> None:
    """Print a key-value summary table."""
    console.print()
    for key, val in rows:
        console.print(f"  [bold]{key:<35}[/bold] {val}")
    console.print()
