from collections.abc import Iterable, Sequence
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from cordis.cli.errors import CordisCliError


def _get_console() -> Console:
    return Console(color_system=None, force_terminal=False, highlight=False, soft_wrap=True)


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def print_success(message: str) -> None:
    _get_console().print(Panel.fit(message, title="Success", box=box.ASCII))


def print_error(error: CordisCliError) -> None:
    message = error.user_message
    if error.status_line:
        message = f"{message}\n\n{error.status_line}"
    _get_console().print(Panel.fit(message, title="Error", box=box.ASCII))


def print_detail(title: str, values: dict[str, Any]) -> None:
    table = Table(title=title, box=box.ASCII, show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for key, value in values.items():
        table.add_row(key, _format_value(value))
    _get_console().print(table)


def print_table(title: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    table = Table(title=title, box=box.ASCII)
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*[_format_value(value) for value in row])
    _get_console().print(table)


def print_path_summary(title: str, items: Sequence[str]) -> None:
    print_table(title=title, columns=["Path"], rows=[[item] for item in items])


def create_download_progress() -> Progress:
    return Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=_get_console(),
        transient=True,
    )
