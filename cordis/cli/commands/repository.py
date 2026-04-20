import typer

from cordis.cli.commands.common import (
    get_client,
    get_registered_repo_id,
    handle_cli_errors,
    print_detail,
    print_success,
    print_table,
    prompt_choice,
    prompt_required_text,
    run_async,
)
from cordis.cli.utils.files import clear_project_registration, get_project_config_path, read_config, update_config_value

app = typer.Typer(help="Repository commands.")


@app.callback()
def repository() -> None:
    """Repository command group."""


@app.command("register")
@handle_cli_errors
def register_repository(
    repo_id: int = typer.Option(..., "--repo-id", "-id"),
    version_name: str | None = typer.Option(None, "--version", "-v"),
) -> None:
    config_path = get_project_config_path()
    update_config_value(config_path, "repo_id", repo_id)
    if version_name is not None:
        update_config_value(config_path, "version", version_name)
    print_success("Repository registered")


@app.command("unregister")
@handle_cli_errors
def unregister_repository() -> None:
    clear_project_registration()
    print_success("Repository unregistered")


@app.command("current")
@handle_cli_errors
def current_registration() -> None:
    print_detail("Current Registration", read_config(get_project_config_path()))


@app.command("ls")
@handle_cli_errors
def list_repositories() -> None:
    items = run_async(get_client().list_my_repositories())
    print_table(
        "Repositories",
        ["Repository ID", "Repository", "Role"],
        [[item["repository_id"], item["repository_name"], item["role_name"]] for item in items],
    )


@app.command("create")
@handle_cli_errors
def create_repository(
    name: str | None = typer.Option(None, "--name"),
    visibility: str | None = typer.Option(None, "--visibility"),
    allow_public_object_urls: bool = typer.Option(False, "--allow-public-object-urls"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Repository name")
    resolved_visibility = prompt_choice(
        visibility,
        prompt="Visibility",
        choices=("private", "authenticated"),
    )
    created = run_async(
        get_client().create_repository(
            name=resolved_name,
            visibility=resolved_visibility,
            allow_public_object_urls=allow_public_object_urls,
        )
    )
    print_detail(
        "Repository",
        {
            "ID": created["id"],
            "Name": created["name"],
            "Visibility": created["visibility"],
            "Public Object URLs": created["allow_public_object_urls"],
        },
    )


@app.command("update")
@handle_cli_errors
def update_repository_command(
    visibility: str = typer.Option("private", "--visibility"),
    allow_public_object_urls: bool = typer.Option(False, "--allow-public-object-urls"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    item = run_async(
        get_client().update_repository(
            repository_id=get_registered_repo_id(repo_id),
            visibility=visibility,
            allow_public_object_urls=allow_public_object_urls,
        )
    )
    print_detail(
        "Repository",
        {
            "ID": item["id"],
            "Name": item["name"],
            "Visibility": item["visibility"],
            "Public Object URLs": item["allow_public_object_urls"],
        },
    )


@app.command("delete")
@handle_cli_errors
def delete_repository_command(repo_id: int | None = typer.Option(None, "--repo-id", "-id")) -> None:
    item = run_async(get_client().delete_repository(repository_id=get_registered_repo_id(repo_id)))
    print_success(f"Repository {item['name']} deleted")


@app.command("versions")
@handle_cli_errors
def repository_versions(repo_id: int | None = typer.Option(None, "--repo-id", "-id")) -> None:
    items = run_async(get_client().list_repository_versions(repository_id=get_registered_repo_id(repo_id)))
    print_table(
        "Versions",
        ["ID", "Name"],
        [[item["id"], item["name"]] for item in items],
    )


@app.command("create-version")
@handle_cli_errors
def repository_create_version(
    name: str | None = typer.Option(None, "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Name")
    version_item = run_async(
        get_client().create_version(repository_id=get_registered_repo_id(repo_id), name=resolved_name)
    )
    print_detail("Version", {"ID": version_item["id"], "Name": version_item["name"]})


@app.command("delete-version")
@handle_cli_errors
def repository_delete_version(
    name: str | None = typer.Option(None, "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_name = prompt_required_text(name, prompt="Name")
    run_async(get_client().delete_version(repository_id=get_registered_repo_id(repo_id), name=resolved_name))
    print_success(f"Version {resolved_name} deleted")


@app.command("users")
@handle_cli_errors
def repository_users(repo_id: int | None = typer.Option(None, "--repo-id", "-id")) -> None:
    items = run_async(get_client().list_repository_members(repository_id=get_registered_repo_id(repo_id)))
    print_table(
        "Members",
        ["Email", "Role"],
        [[item["email"], item["role"]] for item in items],
    )


@app.command("add-user")
@handle_cli_errors
def repository_add_user(
    email: str | None = typer.Option(None, "--email", "-e"),
    role: str | None = typer.Option(None, "--role"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_email = prompt_required_text(email, prompt="Email")
    resolved_role = prompt_required_text(role, prompt="Role")
    item = run_async(
        get_client().add_repository_member(
            repository_id=get_registered_repo_id(repo_id),
            email=resolved_email,
            role=resolved_role,
        )
    )
    print_detail("Member", {"Email": item["email"], "Role": item["role"]})


@app.command("update-user")
@handle_cli_errors
def repository_update_user(
    email: str | None = typer.Option(None, "--email", "-e"),
    role: str | None = typer.Option(None, "--role"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_email = prompt_required_text(email, prompt="Email")
    resolved_role = prompt_required_text(role, prompt="Role")
    item = run_async(
        get_client().update_repository_member(
            repository_id=get_registered_repo_id(repo_id),
            email=resolved_email,
            role=resolved_role,
        )
    )
    print_detail("Member", {"Email": item["email"], "Role": item["role"]})


@app.command("delete-user")
@handle_cli_errors
def repository_delete_user(
    email: str | None = typer.Option(None, "--email", "-e"),
    repo_id: int | None = typer.Option(None, "--repo-id", "-id"),
) -> None:
    resolved_email = prompt_required_text(email, prompt="Email")
    item = run_async(
        get_client().delete_repository_member(
            repository_id=get_registered_repo_id(repo_id),
            email=resolved_email,
        )
    )
    print_success(f"Member {item['email']} removed")
