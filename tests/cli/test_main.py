import json
from pathlib import Path

from typer.testing import CliRunner

from cordis.cli.errors import ApiError, UploadPreflightError
from cordis.cli.main import app


def test_version_command_prints_project_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "Version" in result.stdout
    assert "0.1.0" in result.stdout


def test_help_lists_available_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "version" in result.stdout
    assert "login" in result.stdout
    assert "repository" in result.stdout
    assert "resource" in result.stdout
    assert "tag" in result.stdout
    assert "user" in result.stdout


def test_login_persists_token_and_email(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def login(self, *, email: str, password: str) -> str:
            assert email == "user@example.com"
            assert password == "password123"
            return "token-123"

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(app, ["login", "--email", "user@example.com", "--password", "password123"])

    assert result.exit_code == 0
    assert "Success" in result.stdout
    assert "Login successfully" in result.stdout
    config_path = tmp_path / ".cordis-home" / "config.json"
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "email": "user@example.com",
        "token": "token-123",
    }


def test_logout_clears_token(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / ".cordis-home"
    monkeypatch.setenv("CORDIS_HOME", str(home))
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.json").write_text(
        json.dumps({"email": "user@example.com", "token": "token-123"}),
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["logout"])

    assert result.exit_code == 0
    assert "Success" in result.stdout
    assert "Logout successfully" in result.stdout
    assert json.loads((home / "config.json").read_text(encoding="utf-8")) == {"email": "user@example.com"}


def test_repository_register_and_unregister_manage_project_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        register_result = runner.invoke(app, ["repository", "register", "-id", "7", "-v", "v1"])
        project_config_path = Path.cwd() / ".cordis" / "config.json"
        assert register_result.exit_code == 0
        assert "Repository registered" in register_result.stdout
        assert json.loads(project_config_path.read_text(encoding="utf-8")) == {"repo_id": 7, "version": "v1"}

        unregister_result = runner.invoke(app, ["repository", "unregister"])
        assert unregister_result.exit_code == 0
        assert "Repository unregistered" in unregister_result.stdout
        assert not project_config_path.exists()


def test_clean_cache_recreates_empty_cache_dir(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / ".cordis-home"
    cache_dir = home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "cached.bin").write_text("payload", encoding="utf-8")
    monkeypatch.setenv("CORDIS_HOME", str(home))
    runner = CliRunner()

    result = runner.invoke(app, ["clean-cache"])

    assert result.exit_code == 0
    assert "Cache cleaned" in result.stdout
    assert cache_dir.exists()
    assert list(cache_dir.iterdir()) == []


def test_user_me_uses_sdk_client(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def get_me(self) -> dict[str, object]:
            return {"id": 3, "email": "user@example.com"}

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(app, ["user", "me"])

    assert result.exit_code == 0
    assert "User" in result.stdout
    assert "user@example.com" in result.stdout
    assert "ID" in result.stdout


def test_repository_ls_uses_sdk_client(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def list_my_repositories(self) -> list[dict[str, object]]:
            return [{"repository_id": 7, "repository_name": "repo-one", "role_name": "developer"}]

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(app, ["repository", "ls"])

    assert result.exit_code == 0
    assert "Repositories" in result.stdout
    assert "repo-one" in result.stdout
    assert "developer" in result.stdout


def test_repository_users_renders_registered_repository_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["repository", "users"])

    assert result.exit_code == 1
    assert "Error" in result.stdout
    assert "Repository is not registered in this directory" in result.stdout
    assert "CONFIG" in result.stdout


def test_user_me_renders_backend_api_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def get_me(self) -> dict[str, object]:
            raise ApiError(
                http_status=401,
                app_status_code=1002,
                status_message="Invalid bearer token",
                user_message="Please login again",
            )

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(app, ["user", "me"])

    assert result.exit_code == 1
    assert "Error" in result.stdout
    assert "Please login again" in result.stdout
    assert "HTTP 401" in result.stdout
    assert "APP 1002" in result.stdout


def test_repository_create_prints_created_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def create_repository(
            self,
            *,
            name: str,
            visibility: str,
            allow_public_object_urls: bool,
        ) -> dict[str, object]:
            assert name == "repo-two"
            assert visibility == "authenticated"
            assert allow_public_object_urls is True
            return {
                "id": 8,
                "name": "repo-two",
                "visibility": "authenticated",
                "allow_public_object_urls": True,
            }

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["repository", "create", "--name", "repo-two", "--visibility", "authenticated", "--allow-public-object-urls"],
    )

    assert result.exit_code == 0
    assert "Repository" in result.stdout
    assert "repo-two" in result.stdout
    assert "8" in result.stdout


def test_tag_commands_use_registered_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 7}), encoding="utf-8")

        class FakeClient:
            async def get_tag(self, *, repository_id: int, name: str) -> dict[str, object]:
                assert repository_id == 7
                assert name == "stable"
                return {"id": "tag-1", "name": "stable", "version_name": "v1"}

            async def list_tags(self, *, repository_id: int) -> list[dict[str, object]]:
                assert repository_id == 7
                return [{"id": "tag-1", "name": "stable", "version_name": "v1"}]

            async def create_tag(self, *, repository_id: int, version_name: str, name: str) -> dict[str, object]:
                assert repository_id == 7
                assert version_name == "v1"
                assert name == "stable"
                return {"id": "tag-1", "name": "stable", "version_name": "v1"}

            async def delete_tag(self, *, repository_id: int, name: str) -> None:
                assert repository_id == 7
                assert name == "stable"

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        ls_result = runner.invoke(app, ["tag", "ls"])
        get_result = runner.invoke(app, ["tag", "get", "--name", "stable"])
        create_result = runner.invoke(app, ["tag", "create", "--name", "stable", "-v", "v1", "-id", "7"])
        delete_result = runner.invoke(app, ["tag", "delete", "--name", "stable"])

        assert ls_result.exit_code == 0
        assert "Tags" in ls_result.stdout
        assert "stable" in ls_result.stdout
        assert get_result.exit_code == 0
        assert "Tag" in get_result.stdout
        assert "v1" in get_result.stdout
        assert create_result.exit_code == 0
        assert "Tag" in create_result.stdout
        assert "stable" in create_result.stdout
        assert delete_result.exit_code == 0
        assert "deleted" in delete_result.stdout


def test_resource_download_item_uses_registered_repository_and_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 9, "version": "v2"}), encoding="utf-8")

        class FakeClient:
            async def download_item(
                self,
                *,
                repository_id: int,
                version_name: str,
                path: str,
                save_path: str,
            ) -> dict[str, object]:
                assert repository_id == 9
                assert version_name == "v2"
                assert path == "models/file.bin"
                assert save_path == "downloads/file.bin"
                return {"download_url": "https://download.invalid/file"}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(
            app,
            [
                "resource",
                "download-item",
                "-p",
                "models/file.bin",
                "--save-path",
                "downloads/file.bin",
            ],
        )

        assert result.exit_code == 0
        assert "Download" in result.stdout
        assert "download.invalid/file" in result.stdout


def test_repository_versions_and_users_use_registered_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 12}), encoding="utf-8")

        class FakeClient:
            async def list_repository_versions(self, *, repository_id: int) -> list[dict[str, object]]:
                assert repository_id == 12
                return [{"id": "version-1", "name": "v1"}]

            async def list_repository_members(self, *, repository_id: int) -> list[dict[str, object]]:
                assert repository_id == 12
                return [{"email": "user@example.com", "role": "developer"}]

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        versions_result = runner.invoke(app, ["repository", "versions"])
        users_result = runner.invoke(app, ["repository", "users"])

        assert versions_result.exit_code == 0
        assert "Versions" in versions_result.stdout
        assert "v1" in versions_result.stdout
        assert users_result.exit_code == 0
        assert "Members" in users_result.stdout
        assert "user@example.com" in users_result.stdout
        assert "developer" in users_result.stdout


def test_version_commands_use_registered_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 14}), encoding="utf-8")

        class FakeClient:
            async def get_version(self, *, repository_id: int, name: str) -> dict[str, object]:
                assert repository_id == 14
                assert name == "v1"
                return {"id": "version-1", "name": "v1"}

            async def create_version(self, *, repository_id: int, name: str) -> dict[str, object]:
                assert repository_id == 14
                assert name == "v2"
                return {"id": "version-2", "name": "v2"}

            async def delete_version(self, *, repository_id: int, name: str) -> None:
                assert repository_id == 14
                assert name == "v2"

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        get_result = runner.invoke(app, ["version", "get", "--name", "v1", "-id", "14"])
        create_result = runner.invoke(app, ["version", "create", "--name", "v2"])
        delete_result = runner.invoke(app, ["version", "delete", "--name", "v2"])

        assert get_result.exit_code == 0
        assert "Version" in get_result.stdout
        assert "version-1" in get_result.stdout
        assert create_result.exit_code == 0
        assert "Version" in create_result.stdout
        assert "version-2" in create_result.stdout
        assert delete_result.exit_code == 0
        assert "deleted" in delete_result.stdout


def test_resource_ls_uses_registered_repository_and_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 9, "version": "v2"}), encoding="utf-8")

        class FakeClient:
            async def list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, object]]:
                assert repository_id == 9
                assert version_name == "v2"
                return [
                    {
                        "id": "artifact-1",
                        "path": "models/file.bin",
                        "checksum": "sha256:file",
                        "size": 64,
                        "public_url": "https://storage.invalid/9/models/file.bin",
                    },
                    {
                        "id": "artifact-2",
                        "path": "README.md",
                        "checksum": "sha256:readme",
                        "size": 10,
                        "public_url": None,
                    },
                ]

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "ls", "-id", "9", "-v", "v2"])

        assert result.exit_code == 0
        assert "Resources" in result.stdout
        assert "models/file.bin" in result.stdout
        assert "README.md" in result.stdout
        assert "Public URL" in result.stdout
        assert "storage.invalid" in result.stdout


def test_repository_member_mutation_commands_use_registered_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 21}), encoding="utf-8")

        class FakeClient:
            async def add_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, object]:
                assert repository_id == 21
                assert email == "user@example.com"
                assert role == "developer"
                return {"email": email, "role": role}

            async def update_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, object]:
                assert repository_id == 21
                assert email == "user@example.com"
                assert role == "viewer"
                return {"email": email, "role": role}

            async def delete_repository_member(self, *, repository_id: int, email: str) -> dict[str, object]:
                assert repository_id == 21
                assert email == "user@example.com"
                return {"email": email, "role": "viewer"}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        add_result = runner.invoke(
            app,
            ["repository", "add-user", "--email", "user@example.com", "--role", "developer"],
        )
        update_result = runner.invoke(
            app,
            ["repository", "update-user", "--email", "user@example.com", "--role", "viewer"],
        )
        delete_result = runner.invoke(
            app,
            ["repository", "delete-user", "--email", "user@example.com"],
        )

        assert add_result.exit_code == 0
        assert "Member" in add_result.stdout
        assert "user@example.com" in add_result.stdout
        assert "developer" in add_result.stdout
        assert update_result.exit_code == 0
        assert "Member" in update_result.stdout
        assert "viewer" in update_result.stdout
        assert delete_result.exit_code == 0
        assert "removed" in delete_result.stdout


def test_user_listing_and_info_commands_use_sdk_client(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))

    class FakeClient:
        async def list_users(self) -> list[dict[str, object]]:
            return [
                {"id": 1, "email": "admin@example.com", "is_admin": True},
                {"id": 2, "email": "user@example.com", "is_admin": False},
            ]

        async def get_user_by_email(self, *, email: str) -> dict[str, object]:
            assert email == "user@example.com"
            return {"id": 2, "email": "user@example.com", "is_admin": False}

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    ls_result = runner.invoke(app, ["user", "ls"])
    info_result = runner.invoke(app, ["user", "info", "--email", "user@example.com"])

    assert ls_result.exit_code == 0
    assert "Users" in ls_result.stdout
    assert "admin@example.com" in ls_result.stdout
    assert "user@example.com" in ls_result.stdout
    assert info_result.exit_code == 0
    assert "User" in info_result.stdout
    assert "user@example.com" in info_result.stdout
    assert "False" in info_result.stdout


def test_repository_create_and_delete_version_commands_use_registered_repository(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 15}), encoding="utf-8")

        class FakeClient:
            async def create_version(self, *, repository_id: int, name: str) -> dict[str, object]:
                assert repository_id == 15
                assert name == "v3"
                return {"id": "version-3", "name": "v3"}

            async def delete_version(self, *, repository_id: int, name: str) -> None:
                assert repository_id == 15
                assert name == "v3"

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        create_result = runner.invoke(app, ["repository", "create-version", "--name", "v3"])
        delete_result = runner.invoke(app, ["repository", "delete-version", "--name", "v3"])

        assert create_result.exit_code == 0
        assert "Version" in create_result.stdout
        assert "version-3" in create_result.stdout
        assert delete_result.exit_code == 0
        assert "deleted" in delete_result.stdout


def test_repository_update_and_delete_use_registered_repository(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 31}), encoding="utf-8")

        class FakeClient:
            async def update_repository(
                self,
                *,
                repository_id: int,
                visibility: str,
                allow_public_object_urls: bool,
            ) -> dict[str, object]:
                assert repository_id == 31
                assert visibility == "authenticated"
                assert allow_public_object_urls is True
                return {
                    "id": 31,
                    "name": "repo-31",
                    "visibility": "authenticated",
                    "allow_public_object_urls": True,
                }

            async def delete_repository(self, *, repository_id: int) -> dict[str, object]:
                assert repository_id == 31
                return {"id": 31, "name": "repo-31"}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        update_result = runner.invoke(
            app,
            ["repository", "update", "--visibility", "authenticated", "--allow-public-object-urls"],
        )
        delete_result = runner.invoke(app, ["repository", "delete"])

        assert update_result.exit_code == 0
        assert "Repository" in update_result.stdout
        assert "repo-31" in update_result.stdout
        assert "authenticated" in update_result.stdout
        assert "True" in update_result.stdout
        assert delete_result.exit_code == 0
        assert "repo-31" in delete_result.stdout
        assert "deleted" in delete_result.stdout


def test_resource_upload_uses_registered_repository_and_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 41, "version": "v5"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file.txt").write_text("hello", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 41
                assert version_name == "v5"
                assert folder_path == "payloads"
                assert create_version_if_missing is False
                assert force is False
                return {"uploaded": ["file.txt"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "upload", "-p", "payloads", "-id", "41", "-v", "v5"])

        assert result.exit_code == 0
        assert "Uploaded" in result.stdout
        assert "file.txt" in result.stdout


def test_resource_upload_can_create_missing_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 43, "version": "v7"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file.txt").write_text("hello", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 43
                assert version_name == "v7"
                assert folder_path == "payloads"
                assert create_version_if_missing is True
                assert force is False
                return {"uploaded": ["file.txt"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(
            app,
            ["resource", "upload", "-p", "payloads", "-id", "43", "-v", "v7", "--create-version"],
        )

        assert result.exit_code == 0
        assert "Uploaded" in result.stdout
        assert "file.txt" in result.stdout


def test_resource_upload_renders_uploaded_and_reused_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 43, "version": "v7"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file-a.txt").write_text("same", encoding="utf-8")
        (upload_dir / "file-b.txt").write_text("new", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 43
                assert version_name == "v7"
                assert folder_path == "payloads"
                assert create_version_if_missing is False
                assert force is False
                return {"uploaded": ["file-b.txt"], "reused": ["file-a.txt"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "upload", "-p", "payloads", "-id", "43", "-v", "v7"])

        assert result.exit_code == 0
        assert "Uploaded" in result.stdout
        assert "file-b.txt" in result.stdout
        assert "Reused" in result.stdout
        assert "file-a.txt" in result.stdout


def test_resource_upload_renders_uploaded_reused_and_unchanged_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 43, "version": "v7"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file-a.txt").write_text("same", encoding="utf-8")
        (upload_dir / "file-b.txt").write_text("new", encoding="utf-8")
        (upload_dir / "file-c.txt").write_text("keep", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 43
                assert version_name == "v7"
                assert folder_path == "payloads"
                assert create_version_if_missing is False
                assert force is False
                return {"uploaded": ["file-b.txt"], "reused": ["file-a.txt"], "unchanged": ["file-c.txt"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "upload", "-p", "payloads", "-id", "43", "-v", "v7"])

        assert result.exit_code == 0
        assert "Uploaded" in result.stdout
        assert "file-b.txt" in result.stdout
        assert "Reused" in result.stdout
        assert "file-a.txt" in result.stdout
        assert "Unchanged" in result.stdout
        assert "file-c.txt" in result.stdout


def test_resource_upload_renders_preflight_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 43, "version": "v7"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file-c.txt").write_text("new", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                raise UploadPreflightError(conflicts=["file-c.txt", "file-d.txt"])

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "upload", "-p", "payloads", "-id", "43", "-v", "v7"])

        assert result.exit_code == 1
        assert "Error" in result.stdout
        assert "No files were uploaded" in result.stdout
        assert "file-c.txt" in result.stdout
        assert "file-d.txt" in result.stdout


def test_resource_download_uses_registered_repository_and_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 42, "version": "v6"}), encoding="utf-8")

        class FakeClient:
            async def download_version(
                self,
                *,
                repository_id: int,
                version_name: str,
                save_dir: str,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 42
                assert version_name == "v6"
                assert save_dir == "downloads"
                assert force is False
                return {"downloaded": ["models/a.bin", "README.md"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "download", "-p", "downloads", "-id", "42", "-v", "v6"])

    assert result.exit_code == 0
    assert "Downloaded" in result.stdout
    assert "models/a.bin" in result.stdout
    assert "README.md" in result.stdout


def test_resource_upload_force_passes_force_flag(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 44, "version": "v8"}), encoding="utf-8")
        upload_dir = Path("payloads")
        upload_dir.mkdir()
        (upload_dir / "file.txt").write_text("hello", encoding="utf-8")

        class FakeClient:
            async def upload_directory(
                self,
                *,
                repository_id: int,
                version_name: str,
                folder_path: str,
                create_version_if_missing: bool,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 44
                assert version_name == "v8"
                assert folder_path == "payloads"
                assert create_version_if_missing is False
                assert force is True
                return {"uploaded": ["file.txt"], "reused": [], "unchanged": []}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "upload", "-p", "payloads", "-id", "44", "-v", "v8", "--force"])

        assert result.exit_code == 0
        assert "Uploaded" in result.stdout


def test_resource_download_force_passes_force_flag(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        config_dir = Path.cwd() / ".cordis"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(json.dumps({"repo_id": 45, "version": "v9"}), encoding="utf-8")

        class FakeClient:
            async def download_version(
                self,
                *,
                repository_id: int,
                version_name: str,
                save_dir: str,
                force: bool = False,
            ) -> dict[str, object]:
                assert repository_id == 45
                assert version_name == "v9"
                assert save_dir == "downloads"
                assert force is True
                return {"downloaded": ["models/a.bin"]}

        monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())

        result = runner.invoke(app, ["resource", "download", "-p", "downloads", "-id", "45", "-v", "v9", "--force"])

        assert result.exit_code == 0
        assert "Downloaded" in result.stdout


def test_login_command_awaits_async_client_call(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CORDIS_HOME", str(tmp_path / ".cordis-home"))
    calls: list[tuple[str, str]] = []

    class FakeClient:
        async def login(self, *, email: str, password: str) -> str:
            calls.append((email, password))
            return "token-async"

    monkeypatch.setattr("cordis.cli.commands.root.get_client", lambda: FakeClient())
    runner = CliRunner()

    result = runner.invoke(app, ["login", "--email", "async@example.com", "--password", "secret"])

    assert result.exit_code == 0
    assert "Login successfully" in result.stdout
    assert calls == [("async@example.com", "secret")]
