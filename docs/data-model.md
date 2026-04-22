# Data Model

Cordis revolves around repositories, versioned content, and transfer sessions.

## Core Entities

### User

A user can authenticate, access repositories, and perform CLI or API workflows. Users can also be marked as admins.

### Role

Roles define repository-scoped access levels. In practice the main access levels are viewer, developer, and owner, with admin as a system-level override.

### Repository

A repository is the main ownership and authorization boundary. It has a name, optional description, a Cordis API `visibility` policy (`private` or `authenticated`), and an `allow_public_object_urls` flag for provider-native raw object exposure.
`visibility` controls Cordis API reads. `allow_public_object_urls` is a separate storage-facing control that lets the backend expose `public_url` values and synchronize public object-read access for the repository's storage prefix.

### Repository Membership

A repository membership links a user to a repository with a role. Membership controls read and write access within that repository, and one membership row exists per repository-user pair.

### Version

A version is a named snapshot-like grouping of artifact associations within a repository. Versions are repository-scoped and are the main unit for upload and download workflows.

### Version Tag

A version tag binds a stable name to a repository-scoped version.

### Artifact

An artifact represents file content metadata such as path, checksum, size, and repository ownership.
Artifacts are repository-scoped and path-sensitive: the same repository path can be reused across multiple versions when checksum and size match exactly. Stored objects use immutable keys derived from repository ID, artifact ID, and artifact path, so the artifact record itself is the durable identity for the underlying blob. When a repository enables `allow_public_object_urls`, an artifact also has one stable provider-native `public_url`, shared across every Cordis version that attaches that artifact. Public raw-object exposure is prefix-scoped within the shared storage bucket, not a bucket-wide public mode.

### Version Artifact

A version-artifact link associates an artifact to a specific version. This is what makes content visible as part of a version’s downloadable contents.

### Upload Session

An upload session tracks an in-progress or completed content upload for a target version and path. It stores workflow state, expected checksum, size, and storage-side upload identifiers.

### Upload Session Part

An upload session part records uploaded multipart progress for resumable uploads.

## Relationship Summary

- a repository has many versions
- a repository has many members
- a repository has many artifacts
- a version belongs to one repository
- a tag belongs to one repository and points to one version
- a version can have many artifacts through version-artifact associations
- an upload session belongs to one repository/version target and can have many uploaded parts
- a repository membership is identified by the `(repository_id, user_id)` pair

## Why the Boundaries Matter

- repository boundaries drive authorization
- version boundaries drive content lifecycle and retrieval
- artifact metadata lets content be reasoned about independently from transfer transport while still mapping cleanly to one immutable storage object
- repository-scoped artifact reuse lets unchanged files at the same path be attached to later versions without re-uploading
- upload sessions make large-file workflows explicit and resumable
