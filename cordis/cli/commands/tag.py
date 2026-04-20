import typer

from cordis.cli.commands.common import (
    get_client,
    get_registered_repo_id,
    handle_cli_errors,
    print_detail,
    print_success,
    print_table,
    prompt_required_text,
    run_async,
)

app = typer.Typer(help="Tag commands.")


@app.callback()
def tag() -> None:
    """Tag command group."""


@app.command("ls")
@handle_cli_errors
def list_tags(repo_id: int | None = typer.Option(None, "--repo-id", "-id")) -> None:
    items = run_async(get_client().list_tags(repository_id=get_registered_repo_id(repo_id)))
    print_table(
        "Tags",
        ["ID", "Name", "Version"],
        [[item["id"], item["name"], item["version_name"]] for item in items],
    )


@app.command("get")
@handle_cli_errors
def get_tag(
    name: str | None = typer.Option(None, "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Name")
    tag_item = run_async(get_client().get_tag(repository_id=get_registered_repo_id(repo_id), name=resolved_name))
    print_detail("Tag", {"ID": tag_item["id"], "Name": tag_item["name"], "Version": tag_item["version_name"]})


@app.command("create")
@handle_cli_errors
def create_tag(
    name: str | None = typer.Option(None, "--name"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Name")
    resolved_version_name = prompt_required_text(version_name, prompt="Version")
    tag_item = run_async(
        get_client().create_tag(
            repository_id=get_registered_repo_id(repo_id),
            version_name=resolved_version_name,
            name=resolved_name,
        )
    )
    print_detail("Tag", {"ID": tag_item["id"], "Name": tag_item["name"], "Version": tag_item["version_name"]})


@app.command("delete")
@handle_cli_errors
def delete_tag(
    name: str | None = typer.Option(None, "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Name")
    run_async(get_client().delete_tag(repository_id=get_registered_repo_id(repo_id), name=resolved_name))
    print_success(f"Tag {resolved_name} deleted")
