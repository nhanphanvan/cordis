# CLI Guide

Cordis ships with a Typer-based CLI named `cordis`.

The CLI uses a shared presentation layer for human-friendly terminal output:

- tables for list-style results
- labeled detail views for single records
- success panels for mutations and cache/auth actions
- error panels for expected API, config, and transport failures
- Rich progress for streamed remote downloads triggered by `cordis resource download`

Common short aliases are available for the highest-frequency shared options:

- `-p` for `--path`
- `-id` for `--repo-id`
- `-v` for `--version`
- `-e` for `--email`

Several commands now support interactive fallback for required text inputs. If you omit a required value such as login credentials, repository names, version names, tag names, or upload paths, the CLI prompts for it instead of exiting during argument parsing.

## Global Commands

- `cordis login [--email|-e <email>] [--password|-p <password>] [--endpoint <url>]`
- `cordis logout`
- `cordis clean-cache`

`login` stores the backend endpoint, access token, and email in the global CLI config.
If `--email` or `--password` is omitted, `login` prompts for the missing value. Password entry stays hidden.

If login fails because of backend auth or connectivity problems, the CLI renders an error panel with a short status line rather than a raw traceback.

## User Commands

- `cordis user me`
- `cordis user ls`
- `cordis user info [--email|-e <email>]`

These commands cover current-user inspection and admin-facing user lookup/listing workflows.

## Repository Commands

- `cordis repository register --repo-id <id> [--version <name>]`
- `cordis repository unregister`
- `cordis repository current`
- `cordis repository ls`
- `cordis repository create [--name <name>] [--visibility <private|authenticated>] [--allow-public-object-urls]`
- `cordis repository update [--repo-id <id>] [--visibility <private|authenticated>] [--allow-public-object-urls]`
- `cordis repository delete [--repo-id <id>]`
- `cordis repository versions [--repo-id <id>]`
- `cordis repository create-version [--name <name>] [--repo-id <id>]`
- `cordis repository delete-version [--name <name>] [--repo-id <id>]`
- `cordis repository users [--repo-id <id>]`
- `cordis repository add-user [--email|-e <email>] [--role <role>] [--repo-id <id>]`
- `cordis repository update-user [--email|-e <email>] [--role <role>] [--repo-id <id>]`
- `cordis repository delete-user [--email|-e <email>] [--repo-id <id>]`

Many repository commands can use the workspace registration stored in `.cordis/config.json`.
If a repository-scoped command runs without a registered repository and no `--repo-id`, the CLI renders a configuration error panel.
For `repository create`, `create-version`, `delete-version`, and repository member mutations, omitted required text values are prompted interactively.

## Version Commands

- `cordis version`
- `cordis version get [--name <name>] [--repo-id <id>]`
- `cordis version create [--name <name>] [--repo-id <id>]`
- `cordis version delete [--name <name>] [--repo-id <id>]`

Running `cordis version` without a subcommand prints the CLI package version.

## Tag Commands

- `cordis tag ls [--repo-id <id>]`
- `cordis tag get [--name <name>] [--repo-id <id>]`
- `cordis tag create [--name <name>] [--version <version-name>] [--repo-id <id>]`
- `cordis tag delete [--name <name>] [--repo-id <id>]`

## Resource Commands

- `cordis resource ls [--repo-id <id>] [--version <name>]`
- `cordis resource upload [--path|-p <folder>] [--create-version] [--force] [--repo-id <id>] [--version <name>]`
- `cordis resource upload-item [--source-path|-p <local-file>] [--target-path <artifact-path>] [--create-version] [--force] [--repo-id <id>] [--version <name>]`
- `cordis resource download [--path|-p <folder>] [--force] [--repo-id <id>] [--version <name>]`
- `cordis resource download-item [--path|-p <artifact-path>] [--save-path <local-path>] [--repo-id <id>] [--version <name>]`

Resource commands use the registered repository and version when explicit values are not provided.
For the commands above, omitted required paths are prompted interactively. Missing registered repository or version context still produces the same configuration error as before.
`cordis resource upload` reads `.cordisignore` from the upload root and skips matching files using Gitignore-style rules.
`cordis resource upload` now preflights the entire folder before mutating anything in the target version.
During preflight, files already present in the target version with identical content are treated as `Unchanged`, files reusable from other versions are staged for direct attach, and any target-version path conflict with different metadata aborts the whole upload before later files are attached or uploaded.
`cordis resource upload --force` clears the target version contents first by deleting only `version_artifact` associations, then runs the normal upload flow against the empty version.
`cordis resource upload-item` uploads one local file to one explicit repository artifact path. It reports `Unchanged` for exact same-content matches already present in the target version, reuses an existing repository artifact at the same repository path when checksum and size match, and otherwise falls through to the normal upload-session flow.
`cordis resource upload-item --force` is path-scoped: it removes only the target version association for `--target-path` before running the single-file upload logic.
When preflight succeeds, uploads are session-based and use sequential resumable multipart transfer with a shared `8 MiB` chunk size.
When artifact responses include `public_url`, `cordis resource ls` shows that raw provider-native URL in the default table output.
Remote version downloads first check whether the destination file already exists and exactly matches the artifact checksum. Matching destination files are left in place and skipped entirely. For the remaining artifacts, cached file copies stay local and quiet, and cache misses stream through the shared SDK HTTP transport with retry, resume, and Rich progress behavior. `cordis resource download --force` wipes the destination root before downloading. `cordis resource download-item` still resolves and prints the mediated URL only.
Read [Transfer Workflows](./transfer-workflows.md) for the full end-to-end upload and download sequence, including cache behavior, upload sessions, and mediated download URLs.

## Common Workflows

### Authenticate and inspect the CLI

```bash
cordis login --email user@example.com --password password123 --endpoint http://127.0.0.1:8000
cordis login --endpoint http://127.0.0.1:8000
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
cordis resource upload -p ./payloads --force -id 7 -v v2
cordis resource upload-item --source-path ./dist/model.bin --target-path models/model.bin -id 7 -v v2
cordis resource upload-item --source-path ./dist/model.bin --target-path models/model.bin --force -id 7 -v v2
cordis resource ls -id 7 -v v2
cordis resource download -p ./downloads -id 7 -v v2
cordis resource download -p ./downloads --force -id 7 -v v2
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

- how `resource upload` preflights a folder and aborts atomically on conflicts
- how `resource upload --force` clears version contents before upload
- how `resource upload-item` differs from folder upload and reuses the same session pipeline
- how `resource upload` creates or resumes upload sessions after preflight succeeds
- how multipart upload chunks are skipped on resume
- how completion creates artifacts and attaches them to versions
- how `resource download` skips exact destination matches, reuses cache, and then streams through the shared HTTP transport
- how `resource download --force` wipes the destination root first
- how `resource download-item` differs from full file download

read [Transfer Workflows](./transfer-workflows.md).

## Config and Cache Behavior

- global CLI state is stored under `~/.cordis` by default
- workspace registration is stored in `<cwd>/.cordis/config.json`
- cache cleanup is available through `cordis clean-cache`
- transfer helpers reuse cached file content when checksums match
- upload traversal honors `.cordisignore` using Gitignore-style matching rules
- upload preflight is atomic at the CLI workflow level: conflicting same-version paths abort the whole folder before mutation
- `resource upload --force` clears the target version contents before upload by removing only version associations
- `resource upload-item --force` replaces only the target version path rather than clearing the full version
- uploads use sequential resumable multipart transfer with a shared `8 MiB` chunk size
- `resource download` skips work when the destination file already matches the artifact checksum
- `resource download --force` wipes the destination root before downloading
- remote version downloads stream through the shared HTTP transport with retry, resume, and Rich progress
- `resource download-item` still prints the mediated URL rather than streaming the file

## Error Behavior

The CLI normalizes expected failures into a shared error surface.

- backend app-status responses are parsed into typed CLI API errors
- missing local registration state is rendered as a CLI configuration error
- connection and timeout issues are rendered as transport errors
- expected failures exit with status code `1` and do not dump raw Python exceptions by default

Read [Configuration](./configuration.md) for the full path and environment details.
