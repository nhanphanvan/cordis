# Manual Testing Guide

This guide is for end-to-end manual testing of Cordis with:

- PostgreSQL in Docker
- MinIO in Docker
- the backend in Docker
- the CLI run locally from this repository

It is written as a repeatable operator runbook, not a high-level overview.

## What this covers

By the end of this guide, you will have manually verified:

- container startup, migrations, and health checks
- authentication and CLI local config
- repository creation and membership management
- version and tag workflows
- folder upload, single-file upload, and multipart transfer
- `.cordisignore` behavior
- same-version conflict rejection
- cross-version artifact reuse
- forced upload and forced download behavior
- download behavior, cache reuse, and destination-match skip behavior
- repository visibility differences
- provider-native `public_url` exposure for repositories that allow it
- expected authorization failures

## Assumptions

- You are running from the repository root.
- You have Docker, Docker Compose, Python 3.10+, and Poetry installed.
- You want the most reliable local path first: backend inside Compose, CLI on the host.

Capture the repository root once and reuse it for every later path:

```bash
export REPO_ROOT="$(pwd)"
```

## Test layout

This guide uses a local scratch area under `.manual-test/` so it does not interfere with your normal CLI state.

## 1. Install dependencies

```bash
make install
```

Optional quick confidence check before the manual pass:

```bash
make test
```

## 2. Prepare local scratch directories

```bash
mkdir -p .manual-test/{homes,workspaces,payloads,downloads}
mkdir -p .manual-test/workspaces/{admin,developer,viewer}
mkdir -p .manual-test/payloads/base/models
mkdir -p .manual-test/payloads/v2/models
mkdir -p .manual-test/payloads/public/docs
```

Create a realistic payload set, including one file larger than the shared `8 MiB` chunk size so multipart upload is exercised:

```bash
cat > .manual-test/payloads/base/README.md <<'EOF'
manual test payload
EOF

cat > .manual-test/payloads/base/models/config.json <<'EOF'
{"model":"alpha","version":1}
EOF

cat > .manual-test/payloads/base/.cordisignore <<'EOF'
*.tmp
ignored/
EOF

mkdir -p .manual-test/payloads/base/ignored
cat > .manual-test/payloads/base/ignored/skip.txt <<'EOF'
this file should never be uploaded
EOF

cat > .manual-test/payloads/base/temp.tmp <<'EOF'
this file should be ignored
EOF

python3 - <<'PY'
from pathlib import Path

large = Path(".manual-test/payloads/base/models/large.bin")
large.write_bytes((b"CORDIS-MANUAL-TEST-" * 600000)[:10 * 1024 * 1024])

Path(".manual-test/payloads/v2/README.md").write_text("manual test payload\n", encoding="utf-8")
Path(".manual-test/payloads/v2/models").mkdir(parents=True, exist_ok=True)
Path(".manual-test/payloads/v2/models/config.json").write_text(
    '{"model":"alpha","version":2}\n',
    encoding="utf-8",
)
Path(".manual-test/payloads/v2/models/new.txt").write_text("new file in v2\n", encoding="utf-8")

Path(".manual-test/payloads/public/docs/index.txt").write_text("public repo file\n", encoding="utf-8")
PY
```

## 3. Start the stack

Use the repository’s Compose assets:

```bash
cp .env.docker.example .env
docker compose up --build -d postgres minio backend
docker compose ps
```

Wait until all three services are healthy. If needed, watch logs:

```bash
docker compose logs -f postgres minio backend
```

## 4. Verify basic service health

Backend checks:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/v1/healthz
```

MinIO checks:

- API endpoint: `http://127.0.0.1:9000`
- console: `http://127.0.0.1:9001`
- default credentials from `compose.yml`: `minioadmin` / `minioadmin`

In the MinIO console, confirm:

- the `cordis-artifacts` bucket exists
- bucket versioning is enabled

If MinIO is up but the bucket is missing, the backend likely failed storage initialization. Check `docker compose logs backend`.

## 5. Seed the baseline roles and users

Cordis now bootstraps the first admin user during backend startup when the database is empty. Before you start the stack, make sure `.env` contains:

- `CORDIS_BOOTSTRAP_ADMIN_EMAIL`
- `CORDIS_BOOTSTRAP_ADMIN_PASSWORD`
- `CORDIS_BOOTSTRAP_ADMIN_NAME`

The default `.env.docker.example` already includes a bootstrap admin:

- `admin@example.com` / `password123`

On every startup, the backend also ensures the default repository roles exist:

- `owner`
- `developer`
- `viewer`

For the rest of this guide, create the non-admin users through the normal admin API after logging in as the bootstrap admin.

## 6. Define a reusable local CLI command

The repository prefers module-based execution. Use this shell variable for the rest of the guide:

```bash
CLI="python3 -m poetry run python -m cordis.cli"
```

Use isolated CLI homes so you can switch between users without touching your real `~/.cordis` state:

```bash
export ADMIN_HOME="$REPO_ROOT/.manual-test/homes/admin"
export DEVELOPER_HOME="$REPO_ROOT/.manual-test/homes/developer"
export VIEWER_HOME="$REPO_ROOT/.manual-test/homes/viewer"
```

## 7. Verify auth and CLI config behavior

### 7.1 Admin login

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI login \
  --endpoint http://127.0.0.1:8000 \
  --email admin@example.com \
  --password password123

CORDIS_HOME="$ADMIN_HOME" $CLI user me
```

Expected result:

- login succeeds
- `user me` shows `admin@example.com`
- the global config is written under `.manual-test/homes/admin/config.json`

### 7.2 Invalid login

```bash
CORDIS_HOME="$VIEWER_HOME" $CLI login \
  --endpoint http://127.0.0.1:8000 \
  --email viewer@example.com \
  --password wrong-password
```

Expected result:

- command fails cleanly
- the CLI shows a handled auth error instead of a traceback

### 7.3 Non-admin login

Create the two non-admin users from the bootstrap admin session:

```bash
TOKEN="$(
  curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"admin@example.com","password":"password123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

curl -sS -X POST http://127.0.0.1:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","name":"Developer User","password":"password123","is_active":true,"is_admin":false}'

curl -sS -X POST http://127.0.0.1:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"viewer@example.com","name":"Viewer User","password":"password123","is_active":true,"is_admin":false}'
```

Then log in with those users:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI login \
  --endpoint http://127.0.0.1:8000 \
  --email developer@example.com \
  --password password123

CORDIS_HOME="$VIEWER_HOME" $CLI login \
  --endpoint http://127.0.0.1:8000 \
  --email viewer@example.com \
  --password password123
```

## 8. Create the main private test repository

Create a private repository as the admin:

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI repository create \
  --name manual-private \
  --visibility private

CORDIS_HOME="$ADMIN_HOME" $CLI repository ls
```

From the list output, note the repository ID for `manual-private`. In the rest of this guide, replace `<PRIVATE_REPO_ID>` with that value.

Register the admin workspace against that repository and `v1`:

```bash
cd "$REPO_ROOT/.manual-test/workspaces/admin"
CORDIS_HOME="$ADMIN_HOME" $CLI repository register \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
CORDIS_HOME="$ADMIN_HOME" $CLI repository current
```

Expected result:

- `.manual-test/workspaces/admin/.cordis/config.json` exists
- the current workspace shows repository `<PRIVATE_REPO_ID>` and version `v1`

## 9. Add repository members and verify access boundaries

As admin, add the seeded users to the repository:

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI repository add-user \
  --repo-id <PRIVATE_REPO_ID> \
  --email developer@example.com \
  --role developer

CORDIS_HOME="$ADMIN_HOME" $CLI repository add-user \
  --repo-id <PRIVATE_REPO_ID> \
  --email viewer@example.com \
  --role viewer

CORDIS_HOME="$ADMIN_HOME" $CLI repository users --repo-id <PRIVATE_REPO_ID>
```

Register the developer and viewer workspaces to the same repository:

```bash
cd "$REPO_ROOT/.manual-test/workspaces/developer"
CORDIS_HOME="$DEVELOPER_HOME" $CLI repository register \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1

cd "$REPO_ROOT/.manual-test/workspaces/viewer"
CORDIS_HOME="$VIEWER_HOME" $CLI repository register \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Now verify the role boundaries:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI user me
CORDIS_HOME="$VIEWER_HOME" $CLI user me

CORDIS_HOME="$DEVELOPER_HOME" $CLI repository current
CORDIS_HOME="$VIEWER_HOME" $CLI repository current

CORDIS_HOME="$VIEWER_HOME" $CLI repository users --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$DEVELOPER_HOME" $CLI repository add-user \
  --repo-id <PRIVATE_REPO_ID> \
  --email viewer@example.com \
  --role developer
```

Expected result:

- `user me` and `repository current` succeed for both users
- `repository users` fails for the viewer
- `repository add-user` fails for the developer

## 10. Create and inspect the first version

From the admin workspace:

```bash
cd "$REPO_ROOT/.manual-test/workspaces/admin"
CORDIS_HOME="$ADMIN_HOME" $CLI version get --name v1 --repo-id <PRIVATE_REPO_ID>
```

Expected result:

- if `v1` does not exist yet, this fails
- that confirms version lookup is real and not implicit

Create it:

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI version create --name v1 --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$ADMIN_HOME" $CLI repository versions --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$ADMIN_HOME" $CLI version get --name v1 --repo-id <PRIVATE_REPO_ID>
```

Also verify that a viewer can read versions but not create them:

```bash
CORDIS_HOME="$VIEWER_HOME" $CLI repository versions --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$VIEWER_HOME" $CLI version create --name viewer-should-fail --repo-id <PRIVATE_REPO_ID>
```

Expected result:

- repository version listing works for the viewer
- version creation fails for the viewer

## 11. Upload the first payload with folder upload

Use the developer account for the main write-path test.

```bash
cd "$REPO_ROOT/.manual-test/workspaces/developer"
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/base" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Then inspect version contents:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource ls \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Expected result:

- upload succeeds
- `README.md`, `models/config.json`, and `models/large.bin` are present
- `.cordisignore`, `temp.tmp`, and `ignored/skip.txt` are not present
- the large file upload exercises multipart behavior

While this is running, it is worth watching backend logs once:

```bash
docker compose logs -f backend
```

You should see upload-session activity rather than one monolithic file post.

## 12. Verify same-version unchanged detection

Run the exact same upload again:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/base" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Expected result:

- the CLI reports unchanged behavior rather than re-uploading everything
- no new content appears in `resource ls`

## 13. Verify same-version conflict rejection

Mutate one file in the same source folder:

```bash
cat > "$REPO_ROOT/.manual-test/payloads/base/models/config.json" <<'EOF'
{"model":"alpha","version":999}
EOF
```

Retry the upload into the same repository version:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/base" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Expected result:

- the whole upload is rejected before mutation
- existing version contents remain unchanged

Confirm the version still has the original file set:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource ls \
  --repo-id <PRIVATE_REPO_ID> \
  --version v1
```

Restore the base file so later checks stay clean:

```bash
cat > "$REPO_ROOT/.manual-test/payloads/base/models/config.json" <<'EOF'
{"model":"alpha","version":1}
EOF
```

## 14. Create `v2` and verify cross-version reuse

Create a second version:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI version create --name v2 --repo-id <PRIVATE_REPO_ID>
```

Upload the mixed `v2` payload:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/v2" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Inspect it:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource ls \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- `README.md` should be reusable from `v1` because it is unchanged at the same repository path
- `models/config.json` should be a new artifact because its content changed
- `models/new.txt` should be new

## 15. Verify `upload-item` and path-scoped `--force`

Create one replacement file:

```bash
cat > "$REPO_ROOT/.manual-test/payloads/v2/models/replacement.txt" <<'EOF'
replacement content
EOF
```

Upload it to a new path in `v2`:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload-item \
  --source-path "$REPO_ROOT/.manual-test/payloads/v2/models/replacement.txt" \
  --target-path models/replacement.txt \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Upload the same file again:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload-item \
  --source-path "$REPO_ROOT/.manual-test/payloads/v2/models/replacement.txt" \
  --target-path models/replacement.txt \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- the first call uploads or attaches the file
- the second call reports unchanged behavior

Now replace only that one target path:

```bash
cat > "$REPO_ROOT/.manual-test/payloads/v2/models/replacement.txt" <<'EOF'
replacement content v2
EOF

CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload-item \
  --source-path "$REPO_ROOT/.manual-test/payloads/v2/models/replacement.txt" \
  --target-path models/replacement.txt \
  --force \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- only `models/replacement.txt` is replaced
- other artifacts already attached to `v2` stay intact

## 16. Verify tags

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI tag create \
  --name stable \
  --version v2 \
  --repo-id <PRIVATE_REPO_ID>

CORDIS_HOME="$DEVELOPER_HOME" $CLI tag ls --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$DEVELOPER_HOME" $CLI tag get --name stable --repo-id <PRIVATE_REPO_ID>
```

Expected result:

- the tag resolves to `v2`

## 17. Verify download, cache reuse, and `--force`

Download `v2` into a fresh directory:

```bash
mkdir -p "$REPO_ROOT/.manual-test/downloads/v2-first"

CORDIS_HOME="$DEVELOPER_HOME" $CLI resource download \
  --path "$REPO_ROOT/.manual-test/downloads/v2-first" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- all files in `v2` are materialized locally
- downloaded content matches the repository version

Run the same download again into the same folder:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource download \
  --path "$REPO_ROOT/.manual-test/downloads/v2-first" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- destination-match skip behavior kicks in for files that already match
- the CLI should not re-download every file

Verify cache cleanup exists:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI clean-cache
```

Download again into a clean directory so remote transfer happens again:

```bash
mkdir -p "$REPO_ROOT/.manual-test/downloads/v2-second"

CORDIS_HOME="$DEVELOPER_HOME" $CLI resource download \
  --path "$REPO_ROOT/.manual-test/downloads/v2-second" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Test forced destination replacement:

```bash
mkdir -p "$REPO_ROOT/.manual-test/downloads/force-target"
cat > "$REPO_ROOT/.manual-test/downloads/force-target/extra.txt" <<'EOF'
this should be removed by forced download
EOF

CORDIS_HOME="$DEVELOPER_HOME" $CLI resource download \
  --path "$REPO_ROOT/.manual-test/downloads/force-target" \
  --force \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- `extra.txt` is removed
- the target folder contains only the downloaded version contents

## 18. Verify `download-item`

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource download-item \
  --path models/config.json \
  --save-path "$REPO_ROOT/.manual-test/downloads/item-config.json" \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- the command prints a mediated URL
- it does not stream the file itself

That behavior is current by design.

## 19. Verify `upload --force` clears a version before re-upload

Upload the `base` payload into `v2` with `--force`:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/base" \
  --force \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

List the result:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI resource ls \
  --repo-id <PRIVATE_REPO_ID> \
  --version v2
```

Expected result:

- `v2` now reflects only the contents of `base`
- earlier `v2`-only paths like `models/new.txt` are gone

## 20. Create an authenticated repository with public object URLs

This covers two distinct controls:

- `visibility=authenticated`
- `allow_public_object_urls=true`

Create the repository:

```bash
cd "$REPO_ROOT/.manual-test/workspaces/admin"
CORDIS_HOME="$ADMIN_HOME" $CLI repository create \
  --name manual-auth-public \
  --visibility authenticated \
  --allow-public-object-urls

CORDIS_HOME="$ADMIN_HOME" $CLI repository ls
```

Note the repository ID for `manual-auth-public` and replace `<AUTH_REPO_ID>` below.

Create a version and upload a small payload:

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI version create --name public-v1 --repo-id <AUTH_REPO_ID>

CORDIS_HOME="$ADMIN_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/public" \
  --repo-id <AUTH_REPO_ID> \
  --version public-v1
```

Now verify read behavior as the non-member viewer:

```bash
CORDIS_HOME="$VIEWER_HOME" $CLI resource ls \
  --repo-id <AUTH_REPO_ID> \
  --version public-v1
```

Expected result:

- the viewer can read the repository contents even without membership because visibility is `authenticated`
- the default output includes a `public_url`

Optional extra check:

- copy the printed `public_url`
- open it in a browser or `curl` it directly
- confirm the object is reachable from MinIO

Now verify the viewer still cannot mutate it:

```bash
CORDIS_HOME="$VIEWER_HOME" $CLI version create --name should-fail --repo-id <AUTH_REPO_ID>
CORDIS_HOME="$VIEWER_HOME" $CLI resource upload \
  --path "$REPO_ROOT/.manual-test/payloads/public" \
  --repo-id <AUTH_REPO_ID> \
  --version public-v1
```

Expected result:

- both mutation commands fail

## 21. Delete the tag, versions, and repositories

Clean up through the normal product surface:

```bash
CORDIS_HOME="$DEVELOPER_HOME" $CLI tag delete --name stable --repo-id <PRIVATE_REPO_ID>

CORDIS_HOME="$ADMIN_HOME" $CLI version delete --name v1 --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$ADMIN_HOME" $CLI version delete --name v2 --repo-id <PRIVATE_REPO_ID>
CORDIS_HOME="$ADMIN_HOME" $CLI repository delete --repo-id <PRIVATE_REPO_ID>

CORDIS_HOME="$ADMIN_HOME" $CLI version delete --name public-v1 --repo-id <AUTH_REPO_ID>
CORDIS_HOME="$ADMIN_HOME" $CLI repository delete --repo-id <AUTH_REPO_ID>
```

Expected result:

- all deletes succeed
- later lookups for those repositories and versions fail cleanly

## 22. Verify logout and local cleanup behavior

```bash
CORDIS_HOME="$ADMIN_HOME" $CLI logout
CORDIS_HOME="$DEVELOPER_HOME" $CLI logout
CORDIS_HOME="$VIEWER_HOME" $CLI logout

CORDIS_HOME="$ADMIN_HOME" $CLI clean-cache
CORDIS_HOME="$DEVELOPER_HOME" $CLI clean-cache
CORDIS_HOME="$VIEWER_HOME" $CLI clean-cache
```

Expected result:

- auth state is removed from each isolated CLI home
- cache directories are cleaned

## 23. Shut down the stack

```bash
docker compose down -v
```

Use `-v` only if you want to remove the database and MinIO volumes too.

## Failure triage notes

If something fails, narrow it quickly:

- backend does not start:
  check `docker compose logs backend`
- migrations fail:
  check `docker compose logs migrate`
- login fails for seeded users:
  rerun the seed script, then retry
- upload fails at completion:
  check MinIO health, bucket existence, and bucket versioning
- CLI cannot find repository or version context:
  check `.cordis/config.json` inside the relevant workspace
- CLI behaves like the wrong user:
  check which `CORDIS_HOME` is active

## Recommended evidence to capture

For a serious manual pass, save:

- `docker compose ps`
- `docker compose logs backend`
- the exact commands that failed
- screenshots or copied output for:
  - login success and invalid login failure
  - repository membership listing
  - resource listing with and without `public_url`
  - conflict rejection
  - successful download
