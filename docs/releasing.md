# Release Process

This document explains how to release the Metadata AI SDK. A single release publishes all components in parallel:

| Component | Registry | Package |
|-----------|----------|---------|
| Python SDK | [PyPI](https://pypi.org/project/ai-sdk/) | `ai-sdk` |
| TypeScript SDK | [npm](https://www.npmjs.com/package/@openmetadata/ai-sdk) | `@openmetadata/ai-sdk` |
| Java SDK | [Maven Central](https://central.sonatype.com/) | `io.openmetadata:ai-sdk` |
| CLI | [GitHub Releases](https://github.com/open-metadata/metadata-ai-sdk/releases) | Pre-built binaries (6 platforms) |

## TL;DR

```bash
make bump-version V=0.3.0
git add -A && git commit -m "Bump version to 0.3.0"
git push
make release              # release from current branch
# or
make release B=main       # release from a specific branch
```

That's it. CI handles the rest.

## Step-by-Step

### 1. Bump the version

```bash
make bump-version V=0.3.0
```

This updates the `VERSION` file and propagates the new version to all SDK manifests:

| File | Field |
|------|-------|
| `VERSION` | File contents |
| `cli/Cargo.toml` | `version = "..."` |
| `python/pyproject.toml` | `version = "..."` |
| `typescript/package.json` | `"version": "..."` |
| `java/pom.xml` | `<version>...</version>` |
| `n8n-nodes-metadata/package.json` | `"version": "..."` |

After running the command, it automatically calls `make check-versions` to verify all files are in sync.

### 2. Verify the changes

```bash
git diff
```

Review that only version strings changed across the expected files.

### 3. Commit and push

```bash
git add -A && git commit -m "Bump version to 0.3.0"
git push
```

Wait for CI to pass on `main` before creating the release.

### 4. Create the GitHub Release

```bash
make release
```

By default this targets the **current branch**. To release from a specific branch:

```bash
make release B=main
```

This command:

1. Checks that `gh` (GitHub CLI) is installed
2. Validates all SDK versions match via `make check-versions`
3. Runs `gh release create "v0.3.0" --title "v0.3.0" --target <branch> --generate-notes`

The `--target` flag tells GitHub which branch (or commit) the tag should point to. The `--generate-notes` flag auto-generates release notes from commits since the last release.

### 5. CI takes over

Creating the GitHub Release triggers the `ai-sdk-release.yml` workflow, which:

1. **Validates** that the `VERSION` file and all SDK versions match the release tag
2. **Publishes all SDKs in parallel:**
   - **Python** &rarr; builds wheel/sdist, runs tests, publishes to PyPI via trusted publishing (OIDC)
   - **TypeScript** &rarr; runs tests, builds, publishes to npm with `--provenance`
   - **Java** &rarr; runs `mvn clean verify`, deploys to Maven Central with GPG signing
   - **CLI** &rarr; cross-compiles for 6 platforms, uploads binaries to the GitHub Release

Monitor progress in the **Actions** tab of the repository.

## How Version Management Works

The `VERSION` file at the repository root is the single source of truth. All version operations flow through the Makefile:

| Command | What it does |
|---------|-------------|
| `make version` | Print the current version |
| `make check-versions` | Verify all SDK manifests match `VERSION` |
| `make bump-version V=X.Y.Z` | Update `VERSION` and sync all SDKs |
| `make sync-versions` | Re-sync all SDK manifests to match `VERSION` (used internally by `bump-version`) |
| `make release` | Create a GitHub Release from the current branch |
| `make release B=main` | Create a GitHub Release from a specific branch |

If versions somehow drift out of sync, `make sync-versions` rewrites all manifests to match the `VERSION` file.

## Releasing a Single SDK

For hotfixes or out-of-band releases of an individual SDK, push an SDK-specific tag:

```bash
# Example: release only the Python SDK
make tag-python          # Creates annotated tag: python-v0.3.0
git push origin python-v0.3.0
```

Each SDK workflow listens for its own tag pattern:

| SDK | Tag pattern | Workflow |
|-----|-------------|----------|
| Python | `python-v*` | `ai-sdk-release-python.yml` |
| TypeScript | `typescript-v*` | `ai-sdk-release-typescript.yml` |
| Java | `java-v*` | `ai-sdk-release-java.yml` |
| CLI | `cli-v*` | `ai-sdk-release-cli.yml` |

To tag all SDKs at once:

```bash
make tag-all
git push origin --tags
```

Note: SDK-specific tags are **not required** for a unified release. The `make release` flow (which creates a `v*` tag via a GitHub Release) is the standard path.

## CI Workflow Architecture

```
GitHub Release published (tag: v0.3.0)
         │
         ▼
┌─────────────────────┐
│  ai-sdk-release.yml │  (orchestrator)
│  - validate version │
└────────┬────────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    ▼         ▼          ▼           ▼
 Python   TypeScript    Java        CLI
  │         │           │           │
  │ tests   │ tests     │ verify    │ build (6 targets)
  │ build   │ build     │ GPG sign  │ package
  │         │           │           │
  ▼         ▼           ▼           ▼
 PyPI      npm     Maven Central  GitHub Release
                                  (binary uploads)
```

Each SDK workflow can also run independently when triggered by its own tag.

## Validation Guards

Multiple safety checks prevent publishing mismatched versions:

1. **`make release`** runs `make check-versions` before creating the GitHub Release
2. **Orchestrator workflow** validates `VERSION` file matches the release tag
3. **Each SDK workflow** independently verifies its manifest version matches the expected version
4. **Tests run** in every SDK workflow before publishing

If any version mismatch is detected, the workflow fails with a clear error message telling you to run `make bump-version`.

## Required Infrastructure

### GitHub Secrets

| Secret | SDK | Notes |
|--------|-----|-------|
| `NPM_TOKEN` | TypeScript | npm access token with publish permission |
| `OSSRH_USERNAME` | Java | Sonatype OSSRH username (org secret) |
| `OSSRH_TOKEN` | Java | Sonatype OSSRH token (org secret) |
| `OSSRH_GPG_SECRET_KEY` | Java | GPG private key for JAR signing (org secret) |
| `OSSRH_GPG_SECRET_KEY_PASSWORD` | Java | GPG key passphrase (org secret) |
| `MAVEN_MASTER_PASSWORD` | Java | Maven `settings-security.xml` master password (org secret) |

`GITHUB_TOKEN` is provided automatically by GitHub Actions for CLI binary uploads.

The Python SDK uses **PyPI trusted publishing** (OIDC) and requires no secrets.

### GitHub Environment

A GitHub environment named **`publish`** must exist (**Settings > Environments > New environment**). All release workflows run in this environment. You can optionally add required reviewers for release approval.

### PyPI Trusted Publisher

The Python SDK authenticates to PyPI via OIDC (no API tokens). Configure the trusted publisher at [pypi.org](https://pypi.org/manage/project/ai-sdk/settings/publishing/):

- **Owner:** `open-metadata`
- **Repository:** `metadata-ai-sdk`
- **Workflow:** `ai-sdk-release-python.yml`
- **Environment:** `publish`

## CLI Binary Platforms

The CLI release builds binaries for 6 platform/architecture combinations:

| Platform | Architecture | Artifact |
|----------|-------------|----------|
| macOS | x86_64 (Intel) | `ai-sdk-macos-x86_64.tar.gz` |
| macOS | aarch64 (Apple Silicon) | `ai-sdk-macos-aarch64.tar.gz` |
| Linux | x86_64 | `ai-sdk-linux-x86_64.tar.gz` |
| Linux | aarch64 (ARM64) | `ai-sdk-linux-aarch64.tar.gz` |
| Windows | x86_64 | `ai-sdk-windows-x86_64.zip` |
| Windows | aarch64 (ARM64) | `ai-sdk-windows-aarch64.zip` |

These are uploaded as assets to the GitHub Release.

## Troubleshooting

### "VERSION file does not match release tag"

You forgot to bump the version before creating the release. Fix:

```bash
make bump-version V=0.3.0
git add -A && git commit -m "Bump version to 0.3.0"
git push
```

Then delete the failed release on GitHub and run `make release` again.

### "Version mismatches detected"

One or more SDK manifests are out of sync with the `VERSION` file. Fix:

```bash
make sync-versions
git diff  # verify changes
git add -A && git commit -m "Sync SDK versions"
git push
```

### A single SDK publish failed

If one SDK fails while others succeed, you can re-trigger it by pushing its SDK-specific tag:

```bash
make tag-python
git push origin python-v0.3.0
```

### `gh` CLI not installed

`make release` requires the [GitHub CLI](https://cli.github.com/). Install it:

```bash
# macOS
brew install gh

# Linux
sudo apt install gh

# Then authenticate
gh auth login
```
