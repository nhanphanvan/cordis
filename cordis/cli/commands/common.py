import asyncio
import functools
import importlib
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar, cast

import typer

from cordis.cli.errors import ConfigurationError, CordisCliError
from cordis.cli.utils.files import get_project_config_path, read_config
from cordis.cli.utils.presentation import print_detail, print_error, print_path_summary, print_success, print_table
from cordis.sdk.errors import CordisError as SdkCordisError

T = TypeVar("T")
P = ParamSpec("P")


def run_async(awaitable: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(awaitable)


def get_client() -> Any:
    root: Any = importlib.import_module("cordis.cli.commands.root")
    return root.get_client()


def get_registered_repo_id(explicit_repo_id: int | None = None) -> int:
    if explicit_repo_id is not None:
        return explicit_repo_id
    config = read_config(get_project_config_path())
    repo_id = config.get("repo_id")
    if repo_id is None:
        raise ConfigurationError("Repository is not registered in this directory")
    return int(repo_id)


def get_registered_version(explicit_version: str | None = None) -> str:
    if explicit_version is not None:
        return explicit_version
    config = read_config(get_project_config_path())
    registered_version = config.get("version")
    if registered_version is None:
        raise ConfigurationError("Version is not registered in this directory")
    return str(registered_version)


def prompt_required_text(value: str | None, *, prompt: str, hide_input: bool = False) -> str:
    if value is not None:
        return value
    resolved = cast(str, typer.prompt(prompt, hide_input=hide_input)).strip()
    if not resolved:
        raise typer.BadParameter(f"{prompt} cannot be empty")
    return resolved


def prompt_choice(value: str | None, *, prompt: str, choices: tuple[str, ...]) -> str:
    if value is not None:
        return value
    resolved = cast(str, typer.prompt(prompt)).strip()
    if resolved not in choices:
        allowed = ", ".join(choices)
        raise typer.BadParameter(f"{prompt} must be one of: {allowed}")
    return resolved


def handle_cli_errors(function: Callable[P, None]) -> Callable[P, None]:
    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            function(*args, **kwargs)
        except (CordisCliError, SdkCordisError) as error:
            print_error(error)
            raise typer.Exit(code=1) from error

    return wrapper


__all__ = [
    "get_client",
    "get_registered_repo_id",
    "get_registered_version",
    "handle_cli_errors",
    "print_detail",
    "print_error",
    "print_path_summary",
    "prompt_choice",
    "prompt_required_text",
    "print_success",
    "print_table",
    "run_async",
]
