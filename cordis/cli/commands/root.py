import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import typer
from typer import Context

from cordis import __version__
from cordis.cli.config import (
    clear_project_registration,
    get_global_config_path,
    get_project_config_path,
    read_config,
    remove_config_value,
    update_config_value,
)
from cordis.cli.sdk import get_client
from cordis.cli.transfer import clean_cache as clean_transfer_cache

app = typer.Typer(help="Cordis command line interface.")
user_app = typer.Typer(help="User commands.")
repository_app = typer.Typer(help="Repository commands.")
resource_app = typer.Typer(help="Resource transfer commands.")
tag_app = typer.Typer(help="Tag commands.")
version_app = typer.Typer(help="Version commands.", invoke_without_command=True)
T = TypeVar("T")


def run_async(awaitable: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(awaitable)


@app.callback()
def main() -> None:
    """Cordis command group."""


@version_app.callback()
def version_group(ctx: Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(f"cordis {__version__}")


@app.command()
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
    typer.echo("Login successfully")


@app.command()
def logout() -> None:
    remove_config_value(get_global_config_path(), "token")
    typer.echo("Logout successfully")


@app.command("clean-cache")
def clean_cache_command() -> None:
    clean_transfer_cache()
    typer.echo("Cache cleaned")


@user_app.callback()
def user() -> None:
    """User command group."""


@repository_app.callback()
def repository() -> None:
    """Repository command group."""


@resource_app.callback()
def resource() -> None:
    """Resource command group."""


@tag_app.callback()
def tag() -> None:
    """Tag command group."""


@user_app.command("me")
def user_me() -> None:
    me = run_async(get_client().get_me())
    typer.echo(f"{me['id']} {me['email']}")


@user_app.command("ls")
def list_users_command() -> None:
    items = run_async(get_client().list_users())
    for item in items:
        typer.echo(f"{item['id']} {item['email']} admin={item['is_admin']}")


@user_app.command("info")
def get_user_info(email: str = typer.Option(..., "--email")) -> None:
    item = run_async(get_client().get_user_by_email(email=email))
    typer.echo(f"{item['id']} {item['email']} admin={item['is_admin']}")


@repository_app.command("register")
def register_repository(
    repo_id: int = typer.Option(..., "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    config_path = get_project_config_path()
    update_config_value(config_path, "repo_id", repo_id)
    if version_name is not None:
        update_config_value(config_path, "version", version_name)
    typer.echo("Repository registered")


@repository_app.command("unregister")
def unregister_repository() -> None:
    clear_project_registration()
    typer.echo("Repository unregistered")


@repository_app.command("current")
def current_registration() -> None:
    typer.echo(str(read_config(get_project_config_path())))


def _get_registered_repo_id(explicit_repo_id: int | None = None) -> int:
    if explicit_repo_id is not None:
        return explicit_repo_id
    config = read_config(get_project_config_path())
    repo_id = config.get("repo_id")
    if repo_id is None:
        raise typer.BadParameter("Repository is not registered in this directory")
    return int(repo_id)


def _get_registered_version(explicit_version: str | None = None) -> str:
    if explicit_version is not None:
        return explicit_version
    config = read_config(get_project_config_path())
    registered_version = config.get("version")
    if registered_version is None:
        raise typer.BadParameter("Version is not registered in this directory")
    return str(registered_version)


@repository_app.command("ls")
def list_repositories() -> None:
    items = run_async(get_client().list_my_repositories())
    for item in items:
        typer.echo(f"{item['repository_id']} {item['repository_name']} {item['role_name']}")


@repository_app.command("create")
def create_repository(
    name: str = typer.Option(..., "--name"),
    public: bool = typer.Option(False, "--public"),
) -> None:
    created = run_async(get_client().create_repository(name=name, is_public=public))
    typer.echo(f"{created['id']} {created['name']} public={created['is_public']}")


@repository_app.command("update")
def update_repository_command(
    public: bool = typer.Option(False, "--public"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    item = run_async(
        get_client().update_repository(
            repository_id=_get_registered_repo_id(repo_id),
            is_public=public,
        )
    )
    typer.echo(f"{item['id']} {item['name']} public={item['is_public']}")


@repository_app.command("delete")
def delete_repository_command(repo_id: int | None = typer.Option(None, "--repo-id")) -> None:
    item = run_async(get_client().delete_repository(repository_id=_get_registered_repo_id(repo_id)))
    typer.echo(f"{item['id']} {item['name']} deleted")


@repository_app.command("versions")
def repository_versions(repo_id: int | None = typer.Option(None, "--repo-id")) -> None:
    items = run_async(get_client().list_repository_versions(repository_id=_get_registered_repo_id(repo_id)))
    for item in items:
        typer.echo(f"{item['id']} {item['name']}")


@repository_app.command("create-version")
def repository_create_version(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    version_item = run_async(get_client().create_version(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"{version_item['id']} {version_item['name']}")


@repository_app.command("delete-version")
def repository_delete_version(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    run_async(get_client().delete_version(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"Version {name} deleted")


@repository_app.command("users")
def repository_users(repo_id: int | None = typer.Option(None, "--repo-id")) -> None:
    items = run_async(get_client().list_repository_members(repository_id=_get_registered_repo_id(repo_id)))
    for item in items:
        typer.echo(f"{item['email']} {item['role']}")


@repository_app.command("add-user")
def repository_add_user(
    email: str = typer.Option(..., "--email"),
    role: str = typer.Option(..., "--role"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    item = run_async(
        get_client().add_repository_member(
            repository_id=_get_registered_repo_id(repo_id),
            email=email,
            role=role,
        )
    )
    typer.echo(f"{item['email']} {item['role']}")


@repository_app.command("update-user")
def repository_update_user(
    email: str = typer.Option(..., "--email"),
    role: str = typer.Option(..., "--role"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    item = run_async(
        get_client().update_repository_member(
            repository_id=_get_registered_repo_id(repo_id),
            email=email,
            role=role,
        )
    )
    typer.echo(f"{item['email']} {item['role']}")


@repository_app.command("delete-user")
def repository_delete_user(
    email: str = typer.Option(..., "--email"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    item = run_async(
        get_client().delete_repository_member(
            repository_id=_get_registered_repo_id(repo_id),
            email=email,
        )
    )
    typer.echo(f"{item['email']} removed")


@tag_app.command("ls")
def list_tags(repo_id: int | None = typer.Option(None, "--repo-id")) -> None:
    items = run_async(get_client().list_tags(repository_id=_get_registered_repo_id(repo_id)))
    for item in items:
        typer.echo(f"{item['id']} {item['name']} {item['version_name']}")


@tag_app.command("get")
def get_tag(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    tag_item = run_async(get_client().get_tag(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"{tag_item['id']} {tag_item['name']} {tag_item['version_name']}")


@tag_app.command("create")
def create_tag(
    name: str = typer.Option(..., "--name"),
    version_name: str = typer.Option(..., "--version"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    tag_item = run_async(
        get_client().create_tag(
            repository_id=_get_registered_repo_id(repo_id),
            version_name=version_name,
            name=name,
        )
    )
    typer.echo(f"{tag_item['id']} {tag_item['name']} {tag_item['version_name']}")


@tag_app.command("delete")
def delete_tag(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    run_async(get_client().delete_tag(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"Tag {name} deleted")


@resource_app.command("ls")
def list_resources(
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    items = run_async(
        get_client().list_version_artifacts(
            repository_id=_get_registered_repo_id(repo_id),
            version_name=_get_registered_version(version_name),
        )
    )
    for item in items:
        typer.echo(f"{item['path']} {item['checksum']} {item['size']}")


@resource_app.command("download")
def download_resources(
    path: str = typer.Option(..., "--path"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().download_version(
            repository_id=_get_registered_repo_id(repo_id),
            version_name=_get_registered_version(version_name),
            save_dir=path,
        )
    )
    for item in result["downloaded"]:
        typer.echo(item)


@resource_app.command("upload")
def upload_resources(
    path: str = typer.Option(..., "--path"),
    create_version: bool = typer.Option(False, "--create-version"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().upload_directory(
            repository_id=_get_registered_repo_id(repo_id),
            version_name=_get_registered_version(version_name),
            folder_path=path,
            create_version_if_missing=create_version,
        )
    )
    for item in result["uploaded"]:
        typer.echo(item)


@resource_app.command("download-item")
def download_item(
    path: str = typer.Option(..., "--path"),
    save_path: str = typer.Option(..., "--save-path"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
    version_name: str | None = typer.Option(None, "--version"),
) -> None:
    result = run_async(
        get_client().download_item(
            repository_id=_get_registered_repo_id(repo_id),
            version_name=_get_registered_version(version_name),
            path=path,
            save_path=save_path,
        )
    )
    typer.echo(result["download_url"])


@version_app.command("get")
def get_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    version_item = run_async(get_client().get_version(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"{version_item['id']} {version_item['name']}")


@version_app.command("create")
def create_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    version_item = run_async(get_client().create_version(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"{version_item['id']} {version_item['name']}")


@version_app.command("delete")
def delete_version_command(
    name: str = typer.Option(..., "--name"),
    repo_id: int | None = typer.Option(None, "--repo-id"),
) -> None:
    run_async(get_client().delete_version(repository_id=_get_registered_repo_id(repo_id), name=name))
    typer.echo(f"Version {name} deleted")


app.add_typer(user_app, name="user")
app.add_typer(repository_app, name="repository")
app.add_typer(resource_app, name="resource")
app.add_typer(tag_app, name="tag")
app.add_typer(version_app, name="version")
