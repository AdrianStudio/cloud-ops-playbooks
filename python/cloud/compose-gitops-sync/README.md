# Compose GitOps Sync

Syncs Git-hosted Docker Compose projects, layers a local override and `.env` on top, scans the images with Trivy and redeploys them.

## Problem
Self-hosters who run upstream Compose projects from Git and keep their own `compose.override.yml` outside the checkout have no tool that does this safely. Docker management UIs reset or ignore local files in synced repositories. The result is hand-written scripts for Git sync, image updates and vulnerability scanning.

## Prerequisites
- Python 3.12 (standard library only).
- `git` with non-interactive access to the repositories (for example an SSH key loaded in an agent), and `docker` with the Compose v2 plugin.
- `trivy` on the `PATH`. It needs network access to fetch its vulnerability database and to read the images.
- The user must be able to use the Docker socket (member of the `docker` group or root).
- `DOCKER_GIT_DIR`: directory containing the cloned repositories.
- `DOCKER_CONFIGS_DIR`: directory containing one folder per project, each with `compose.override.yml` and `.env`.
- `DOCKER_SYNC_MANIFEST`: path to a JSON file listing the projects.
- Relative paths in the override (`./cfg`, `./data`) resolve against `DOCKER_CONFIGS_DIR/<name>/`.

## Usage
```
# manifest.json
[{"name": "privatebin", "repository": "privatebin", "compose_file": "compose.yml"}]

export DOCKER_GIT_DIR=/docker/git
export DOCKER_CONFIGS_DIR=/docker/configs
export DOCKER_SYNC_MANIFEST=/docker/manifest.json

# Report only: fetch, list images, scan, print the planned actions
python compose_gitops_sync.py

# Fast-forward repositories, pull images, redeploy clean projects
python compose_gitops_sync.py --apply

# Redeploy even when fixable HIGH or CRITICAL findings exist
python compose_gitops_sync.py --apply --allow-vulnerable
```
- Exit code 1 means at least one project has fixable HIGH or CRITICAL findings.
