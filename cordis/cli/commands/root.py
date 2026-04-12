import typer

from cordis.cli.client import get_client
from cordis.cli.commands.common import handle_cli_errors, print_success, run_async
from cordis.cli.commands.repository import app as repository_app
from cordis.cli.commands.resource import app as resource_app
from cordis.cli.commands.tag import app as tag_app
from cordis.cli.commands.user import app as user_app
from cordis.cli.commands.version import app as version_app
from cordis.cli.config import clean_cache, get_global_config_path, remove_config_value, update_config_value

app = typer.Typer(help="Cordis command line interface.")


@app.callback()
def main() -> None:
    """Cordis command group."""


@app.command()
@handle_cli_errors
def login(
    email: str = typer.Option(..., "--email", "-e"),
    password: str = typer.Option(..., "--password", "-p", hide_input=True),
    endpoint: str | None = typer.Option(None, "--endpoint"),
) -> None:
    if endpoint is not None:
        update_config_value(get_global_config_path(), "endpoint", endpoint)
    client = get_client()
    token = str(run_async(client.login(email=email, password=password)))
    update_config_value(get_global_config_path(), "token", token)
    update_config_value(get_global_config_path(), "email", email)
    print_success("Login successfully")


@app.command()
@handle_cli_errors
def logout() -> None:
    remove_config_value(get_global_config_path(), "token")
    print_success("Logout successfully")


@app.command("clean-cache")
@handle_cli_errors
def clean_cache_command() -> None:
    clean_cache()
    print_success("Cache cleaned")


app.add_typer(user_app, name="user")
app.add_typer(repository_app, name="repository")
app.add_typer(resource_app, name="resource")
app.add_typer(tag_app, name="tag")
app.add_typer(version_app, name="version")
