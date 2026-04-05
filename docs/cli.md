# CLI Guide

Cordis ships with a Typer-based CLI named `cordis`.

## Global Commands

- `cordis login --email <email> --password <password> [--endpoint <url>]`
- `cordis logout`
- `cordis clean-cache`

`login` stores the backend endpoint, access token, and email in the global CLI config.

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

## Common Workflows

### Authenticate and inspect the CLI

```bash
cordis login --email user@example.com --password password123 --endpoint http://127.0.0.1:8000
cordis user me
cordis repository ls
```

### Bind a workspace

```bash
cordis repository register --repo-id 7 --version v1
cordis repository current
```

### Create a version and tag it

```bash
cordis version create --name v2 --repo-id 7
cordis tag create --name stable --version v2 --repo-id 7
```

### Upload and download version contents

```bash
cordis resource upload --path ./payloads --create-version
cordis resource ls
cordis resource download --path ./downloads
cordis resource download-item --path models/file.bin --save-path ./downloads/file.bin
```

## Config and Cache Behavior

- global CLI state is stored under `~/.cordis` by default
- workspace registration is stored in `<cwd>/.cordis/config.json`
- cache cleanup is available through `cordis clean-cache`
- transfer helpers reuse cached file content when checksums match

Read [Configuration](./configuration.md) for the full path and environment details.
