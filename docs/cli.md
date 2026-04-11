# CLI Guide

Cordis ships with a Typer-based CLI named `cordis`.

The CLI uses a shared presentation layer for human-friendly terminal output:

- tables for list-style results
- labeled detail views for single records
- success panels for mutations and cache/auth actions
- error panels for expected API, config, and transport failures
- Rich progress for streamed remote downloads

Common short aliases are available for the highest-frequency shared options:

- `-p` for `--path`
- `-id` for `--repo-id`
- `-v` for `--version`

## Global Commands

- `cordis login --email <email> --password <password> [--endpoint <url>]`
- `cordis logout`
- `cordis clean-cache`

`login` stores the backend endpoint, access token, and email in the global CLI config.

If login fails because of backend auth or connectivity problems, the CLI renders an error panel with a short status line rather than a raw traceback.

## User Commands

- `cordis user me`
- `cordis user ls`
- `cordis user info --email <email>`

These commands cover current-user inspection and admin-facing user lookup/listing workflows.

## Repository Commands

- `cordis repository register --repo-id <id> [--version <name>]`
- `cordis repository unregister`
- `cordis repository current`
- `cordis repository ls`
- `cordis repository create --name <name> [--public]`
- `cordis repository update [--repo-id <id>] [--public]`
- `cordis repository delete [--repo-id <id>]`
- `cordis repository versions [--repo-id <id>]`
- `cordis repository create-version --name <name> [--repo-id <id>]`
- `cordis repository delete-version --name <name> [--repo-id <id>]`
- `cordis repository users [--repo-id <id>]`
- `cordis repository add-user --email <email> --role <role> [--repo-id <id>]`
- `cordis repository update-user --email <email> --role <role> [--repo-id <id>]`
- `cordis repository delete-user --email <email> [--repo-id <id>]`

Many repository commands can use the workspace registration stored in `.cordis/config.json`.
If a repository-scoped command runs without a registered repository and no `--repo-id`, the CLI renders a configuration error panel.

## Version Commands

- `cordis version`
- `cordis version get --name <name> [--repo-id <id>]`
- `cordis version create --name <name> [--repo-id <id>]`
- `cordis version delete --name <name> [--repo-id <id>]`

Running `cordis version` without a subcommand prints the CLI package version.

## Tag Commands

- `cordis tag ls [--repo-id <id>]`
- `cordis tag get --name <name> [--repo-id <id>]`
- `cordis tag create --name <name> --version <version-name> [--repo-id <id>]`
- `cordis tag delete --name <name> [--repo-id <id>]`

## Resource Commands

- `cordis resource ls [--repo-id <id>] [--version <name>]`
- `cordis resource upload --path <folder> [--create-version] [--repo-id <id>] [--version <name>]`
- `cordis resource download --path <folder> [--repo-id <id>] [--version <name>]`
- `cordis resource download-item --path <artifact-path> --save-path <local-path> [--repo-id <id>] [--version <name>]`

Resource commands use the registered repository and version when explicit values are not provided.
`cordis resource upload` reads `.cordisignore` from the upload root and skips matching files using Gitignore-style rules.
Uploads are session-based and use sequential resumable multipart transfer with a shared `8 MiB` chunk size.
Before uploading, the CLI checks whether the same repository already has an artifact at the same path with the same checksum and size; if so, it reuses that artifact for the target version instead of uploading the file again.
Remote downloads stream through the shared HTTP transport with retry and resume behavior, while cached file copies stay local and quiet.
Read [Transfer Workflows](./transfer-workflows.md) for the full end-to-end upload and download sequence, including cache behavior, upload sessions, and mediated download URLs.

## Common Workflows

### Authenticate and inspect the CLI

```bash
cordis login --email user@example.com --password password123 --endpoint http://127.0.0.1:8000
cordis user me
cordis repository ls
```

### Bind a workspace

```bash
cordis repository register -id 7 -v v1
cordis repository current
```

### Create a version and tag it

```bash
cordis version create --name v2 -id 7
cordis tag create --name stable -v v2 -id 7
```

### Upload and download version contents

```bash
cordis resource upload -p ./payloads --create-version
cordis resource ls -id 7 -v v2
cordis resource download -p ./downloads -id 7 -v v2
cordis resource download-item -p models/file.bin --save-path ./downloads/file.bin -id 7 -v v2
```

### Exclude local files from upload

Create a `.cordisignore` file in the folder you upload:

```gitignore
*.tmp
build/
!build/keep.bin
```

Cordis always skips `.cordis/` metadata and `.cordisignore` itself during upload traversal.

### Understand the full transfer pipeline

For a deeper explanation of:

- how `resource upload` creates or resumes upload sessions
- how multipart upload chunks are skipped on resume
- how completion creates artifacts and attaches them to versions
- how `resource download` reuses cache and then streams through the shared HTTP transport
- how `resource download-item` differs from full file download

read [Transfer Workflows](./transfer-workflows.md).

## Config and Cache Behavior

- global CLI state is stored under `~/.cordis` by default
- workspace registration is stored in `<cwd>/.cordis/config.json`
- cache cleanup is available through `cordis clean-cache`
- transfer helpers reuse cached file content when checksums match
- upload traversal honors `.cordisignore` using Gitignore-style matching rules
- uploads use sequential resumable multipart transfer with a shared `8 MiB` chunk size
- remote artifact downloads stream through the shared HTTP transport with retry, resume, and Rich progress

## Error Behavior

The CLI normalizes expected failures into a shared error surface.

- backend app-status responses are parsed into typed CLI API errors
- missing local registration state is rendered as a CLI configuration error
- connection and timeout issues are rendered as transport errors
- expected failures exit with status code `1` and do not dump raw Python exceptions by default

Read [Configuration](./configuration.md) for the full path and environment details.
