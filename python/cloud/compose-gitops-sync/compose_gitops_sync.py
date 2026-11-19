"""Sync Git-hosted Compose projects, apply local overrides, scan images and redeploy.

Each project keeps its upstream repository under DOCKER_GIT_DIR and its own
compose.override.yml and .env under DOCKER_CONFIGS_DIR/<name>/, so a Git pull
never touches local customisation.

Environment variables:
    DOCKER_GIT_DIR         directory holding the cloned repositories
    DOCKER_CONFIGS_DIR     directory holding one folder per project
    DOCKER_SYNC_MANIFEST   path to the JSON manifest listing the projects

Usage:
    python compose_gitops_sync.py
    python compose_gitops_sync.py --apply [--allow-vulnerable]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BLOCKING_SEVERITIES = "HIGH,CRITICAL"


def scan_images(image_names: list[str]) -> list[str]:
    vulnerable_images = []
    for image_name in image_names:
        scan = subprocess.run(
            [
                "trivy", "image", "--quiet",
                "--severity", BLOCKING_SEVERITIES,
                "--ignore-unfixed",
                "--exit-code", "1",
                image_name,
            ],
            text=True,
            check=False,
        )
        # Trivy exits 1 when findings match the filter, anything higher is a scanner failure.
        if scan.returncode > 1:
            raise subprocess.CalledProcessError(scan.returncode, scan.args)
        if scan.returncode == 1:
            vulnerable_images.append(image_name)
    return vulnerable_images


def sync_project(project: dict, git_dir: Path, configs_dir: Path, apply: bool, allow_vulnerable: bool) -> bool:
    project_name = project["name"]
    repository_dir = git_dir / project["repository"]
    project_dir = configs_dir / project_name

    subprocess.run(["git", "-C", str(repository_dir), "fetch", "--quiet"], check=True)
    behind_count = int(subprocess.run(
        ["git", "-C", str(repository_dir), "rev-list", "--count", "HEAD..@{upstream}"],
        capture_output=True, text=True, check=True,
    ).stdout)
    print(f"[{project_name}] repository is {behind_count} commit(s) behind upstream")
    if apply and behind_count:
        subprocess.run(["git", "-C", str(repository_dir), "pull", "--ff-only", "--quiet"], check=True)

    # --project-directory makes relative paths in the override resolve against the configs folder.
    compose_command = [
        "docker", "compose",
        "--project-name", project_name,
        "--project-directory", str(project_dir),
        "--env-file", str(project_dir / ".env"),
        "-f", str(repository_dir / project["compose_file"]),
        "-f", str(project_dir / "compose.override.yml"),
    ]
    image_names = subprocess.run(
        compose_command + ["config", "--images"],
        capture_output=True, text=True, check=True,
    ).stdout.split()

    if apply:
        subprocess.run(compose_command + ["pull"], check=True)
    else:
        print(f"[{project_name}] would pull: {', '.join(image_names)}")

    vulnerable_images = scan_images(image_names)
    if vulnerable_images:
        print(f"[{project_name}] fixable {BLOCKING_SEVERITIES} findings in: {', '.join(vulnerable_images)}")

    if not apply:
        print(f"[{project_name}] would run: docker compose up -d --remove-orphans")
    elif vulnerable_images and not allow_vulnerable:
        print(f"[{project_name}] redeploy skipped, pass --allow-vulnerable to override")
    else:
        subprocess.run(compose_command + ["up", "-d", "--remove-orphans"], check=True)
        print(f"[{project_name}] deployed")
    return bool(vulnerable_images)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="pull the repositories and images and redeploy")
    parser.add_argument(
        "--allow-vulnerable",
        action="store_true",
        help=f"redeploy even when {BLOCKING_SEVERITIES} findings with a fix exist",
    )
    arguments = parser.parse_args()

    git_dir = Path(os.environ["DOCKER_GIT_DIR"])
    configs_dir = Path(os.environ["DOCKER_CONFIGS_DIR"])
    projects = json.loads(Path(os.environ["DOCKER_SYNC_MANIFEST"]).read_text(encoding="utf-8"))

    projects_with_findings = [
        project["name"]
        for project in projects
        if sync_project(project, git_dir, configs_dir, arguments.apply, arguments.allow_vulnerable)
    ]
    if projects_with_findings:
        print(f"Projects with vulnerable images: {', '.join(projects_with_findings)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
