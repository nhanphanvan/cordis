import typer

from cordis.cli.commands.common import (
    get_client,
    get_registered_repo_id,
    get_registered_version,
    print_detail,
    print_path_summary,
    print_table,
    run_async,
)

app = typer.Typer(help="Resource transfer commands.")


@app.callback()
def resource() -> None:
    """Resource command group."""


@app.command("ls")
def list_resources(
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    items = run_async(
        get_client().list_version_artifacts(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
        )
    )
    print_table(
        "Resources",
        ["Path", "Checksum", "Size"],
        [[item["path"], item["checksum"], item["size"]] for item in items],
    )


@app.command("download")
def download_resources(
    path: str = typer.Option(..., "--path"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().download_version(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            save_dir=path,
        )
    )
    print_path_summary("Downloaded", [str(item) for item in result["downloaded"]])


@app.command("upload")
def upload_resources(
    path: str = typer.Option(..., "--path"),
    create_version: bool = typer.Option(False, "--create-version"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().upload_directory(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            folder_path=path,
            create_version_if_missing=create_version,
        )
    )
    print_path_summary("Uploaded", [str(item) for item in result["uploaded"]])


@app.command("download-item")
def download_item(
    path: str = typer.Option(..., "--path"),
    save_path: str = typer.Option(..., "--save-path"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().download_item(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            path=path,
            save_path=save_path,
        )
    )
    print_detail("Download", {"URL": result["download_url"]})
