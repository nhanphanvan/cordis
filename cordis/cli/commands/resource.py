import typer

from cordis.cli.commands.common import (
    get_client,
    get_registered_repo_id,
    get_registered_version,
    handle_cli_errors,
    print_detail,
    print_path_summary,
    print_resource_table,
    print_success,
    prompt_required_text,
    run_async,
)

app = typer.Typer(help="Resource transfer commands.")


@app.callback()
def resource() -> None:
    """Resource command group."""


@app.command("ls")
@handle_cli_errors
def list_resources(
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    items = run_async(
        get_client().list_version_artifacts(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
        )
    )
    print_resource_table(
        "Resources",
        [[item["path"], item["checksum"], item["size"], item.get("public_url", "") or ""] for item in items],
    )


@app.command("download")
@handle_cli_errors
def download_resources(
    path: str | None = typer.Option(None, "--path", "-p"),
    force: bool = typer.Option(False, "--force"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    resolved_path = prompt_required_text(path, prompt="Path")
    result = run_async(
        get_client().download_version(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            save_dir=resolved_path,
            force=force,
        )
    )
    remote_count = len(result.get("downloaded", []))
    cache_count = len(result.get("from_cache", []))
    existing_count = len(result.get("existing", []))
    total_count = remote_count + cache_count + existing_count
    print_success(
        f"Download completed: {total_count} files resolved "
        f"({remote_count} remote, {cache_count} cache, {existing_count} already present)"
    )


@app.command("upload")
@handle_cli_errors
def upload_resources(
    path: str | None = typer.Option(None, "--path", "-p"),
    create_version: bool = typer.Option(False, "--create-version"),
    force: bool = typer.Option(False, "--force"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    resolved_path = prompt_required_text(path, prompt="Path")
    result = run_async(
        get_client().upload_directory(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            folder_path=resolved_path,
            create_version_if_missing=create_version,
            force=force,
        )
    )
    uploaded_count = len(result.get("uploaded", []))
    reused_count = len(result.get("reused", []))
    unchanged_count = len(result.get("unchanged", []))
    total_count = uploaded_count + reused_count + unchanged_count
    print_success(
        f"Upload completed: {total_count} files resolved "
        f"({uploaded_count} uploaded, {reused_count} reused, {unchanged_count} unchanged)"
    )


@app.command("upload-item")
@handle_cli_errors
def upload_item(
    source_path: str | None = typer.Option(None, "--source-path", "-p"),
    target_path: str | None = typer.Option(None, "--target-path"),
    create_version: bool = typer.Option(False, "--create-version"),
    force: bool = typer.Option(False, "--force"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    resolved_source_path = prompt_required_text(source_path, prompt="Source path")
    resolved_target_path = prompt_required_text(target_path, prompt="Target path")
    result = run_async(
        get_client().upload_item(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            source_path=resolved_source_path,
            target_path=resolved_target_path,
            create_version_if_missing=create_version,
            force=force,
        )
    )
    print_path_summary("Uploaded", [str(item) for item in result["uploaded"]])
    if result.get("reused"):
        print_path_summary("Reused", [str(item) for item in result["reused"]])
    if result.get("unchanged"):
        print_path_summary("Unchanged", [str(item) for item in result["unchanged"]])


@app.command("download-item")
@handle_cli_errors
def download_item(
    path: str | None = typer.Option(None, "--path", "-p"),
    save_path: str | None = typer.Option(None, "--save-path"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    resolved_path = prompt_required_text(path, prompt="Path")
    resolved_save_path = prompt_required_text(save_path, prompt="Save path")
    result = run_async(
        get_client().download_item(
            repository_id=get_registered_repo_id(repo_id),
            version_name=get_registered_version(version_name),
            path=resolved_path,
            save_path=resolved_save_path,
        )
    )
    print_detail("Download", {"URL": result["download_url"]})
