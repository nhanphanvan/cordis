import typer

from cordis.cli.commands.common import (
    get_client,
    get_registered_repo_id,
    handle_cli_errors,
    print_detail,
    print_success,
    print_table,
    run_async,
)

app = typer.Typer(help="Tag commands.")


@app.callback()
def tag() -> None:
    """Tag command group."""


@app.command("ls")
@handle_cli_errors
def list_tags(repo_id: int | None = typer.Option(None, "--repo-id")) -> None:
    items = run_async(get_client().list_tags(repository_id=get_registered_repo_id(repo_id)))
    print_table(
        "Tags",
        ["ID", "Name", "Version"],
        [[item["id"], item["name"], item["version_name"]] for item in items],
    )


@app.command("get")
@handle_cli_errors
def get_tag(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    tag_item = run_async(get_client().get_tag(repository_id=get_registered_repo_id(repo_id), name=name))
    print_detail("Tag", {"ID": tag_item["id"], "Name": tag_item["name"], "Version": tag_item["version_name"]})


@app.command("create")
@handle_cli_errors
def create_tag(
    name: str = typer.Option(..., "--name"),
    version_name: str = typer.Option(..., "--version"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    tag_item = run_async(
        get_client().create_tag(
            repository_id=get_registered_repo_id(repo_id),
            version_name=version_name,
            name=name,
        )
    )
    print_detail("Tag", {"ID": tag_item["id"], "Name": tag_item["name"], "Version": tag_item["version_name"]})


@app.command("delete")
@handle_cli_errors
def delete_tag(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    run_async(get_client().delete_tag(repository_id=get_registered_repo_id(repo_id), name=name))
    print_success(f"Tag {name} deleted")
