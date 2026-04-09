import typer
from typer import Context

from cordis import __version__
from cordis.cli.commands.common import get_client, get_registered_repo_id, print_detail, print_success, run_async

app = typer.Typer(help="Version commands.", invoke_without_command=True)


@app.callback()
def version_group(ctx: Context) -> None:
    if ctx.invoked_subcommand is None:
        print_detail("Version", {"Cordis": __version__})


@app.command("get")
def get_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    version_item = run_async(get_client().get_version(repository_id=get_registered_repo_id(repo_id), name=name))
    print_detail("Version", {"ID": version_item["id"], "Name": version_item["name"]})


@app.command("create")
def create_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    version_item = run_async(get_client().create_version(repository_id=get_registered_repo_id(repo_id), name=name))
    print_detail("Version", {"ID": version_item["id"], "Name": version_item["name"]})


@app.command("delete")
def delete_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    run_async(get_client().delete_version(repository_id=get_registered_repo_id(repo_id), name=name))
    print_success(f"Version {name} deleted")
