import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.release_version import allocate, git, releases_for_push


@pytest.fixture(name="repository")
def temporary_repository(tmp_path):
    git("init", "--initial-branch=main", cwd=tmp_path)
    git("config", "user.name", "Version test", cwd=tmp_path)
    git("config", "user.email", "version@example.invalid", cwd=tmp_path)
    return tmp_path


def commit(repository, message="change"):
    git("commit", "--allow-empty", "-m", message, cwd=repository)
    return git("rev-parse", "HEAD", cwd=repository)


def test_first_release_and_retry(repository):
    commit(repository)
    head = commit(repository)
    expected = [{"commit": head, "version": "1.0.0"}]
    assert allocate(cwd=repository) == expected
    assert allocate(cwd=repository) == expected
    assert git("tag", cwd=repository) == "v1.0.0"


def test_every_commit_in_push_gets_patch_version(repository):
    commit(repository)
    allocate(cwd=repository)
    first = commit(repository, "feat: still only a patch")
    second = commit(repository, "BREAKING CHANGE: still only a patch")
    assert allocate(cwd=repository) == [
        {"commit": first, "version": "1.0.1"},
        {"commit": second, "version": "1.0.2"},
    ]
    assert allocate(first, cwd=repository) == [{"commit": first, "version": "1.0.1"}]


def test_explicit_minor_tag_sets_next_patch(repository):
    commit(repository)
    git("tag", "v1.2.0", cwd=repository)
    head = commit(repository)
    assert allocate(cwd=repository) == [{"commit": head, "version": "1.2.1"}]


def test_side_branch_commits_are_not_released(repository):
    commit(repository)
    allocate(cwd=repository)
    git("checkout", "-b", "feature", cwd=repository)
    feature = commit(repository)
    git("checkout", "main", cwd=repository)
    git("merge", "--no-ff", "feature", "-m", "merge", cwd=repository)
    releases = allocate(cwd=repository)
    assert len(releases) == 1
    assert releases[0]["commit"] != feature


def test_colliding_tag_fails_without_partial_allocation(repository):
    commit(repository)
    allocate(cwd=repository)
    git("checkout", "-b", "feature", cwd=repository)
    commit(repository, "side branch release")
    git("tag", "v1.0.2", cwd=repository)
    git("checkout", "main", cwd=repository)
    commit(repository)
    commit(repository)
    with pytest.raises(ValueError, match="already exists"):
        allocate(cwd=repository)
    assert "v1.0.1" not in git("tag", cwd=repository)


def test_invalid_target_creates_no_tag(repository):
    commit(repository)
    with pytest.raises(subprocess.CalledProcessError):
        allocate("missing", cwd=repository)
    assert git("tag", cwd=repository) == ""


def test_retry_republishes_all_versions_in_original_push(repository):
    before = commit(repository)
    allocate(cwd=repository)
    commit(repository)
    target = commit(repository)
    expected = releases_for_push(target, before, cwd=repository)
    assert len(expected) == 2
    assert releases_for_push(target, before, cwd=repository) == expected


def test_publication_contract():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/publish-version.yml").read_text())
    trigger = workflow.get("on", workflow.get(True))
    assert trigger["push"] == {"branches": ["main"]}
    assert workflow["concurrency"]["queue"] == "max"
    assert workflow["concurrency"]["cancel-in-progress"] is False
    jobs = workflow["jobs"]
    assert jobs["version"]["permissions"] == {"contents": "write"}
    assert jobs["containers"]["permissions"] == {"contents": "read", "id-token": "write"}
    components = jobs["containers"]["strategy"]["matrix"]["component"]
    assert {component["image"] for component in components} == {
        "web-chat", "staging/defender-mcp", "staging/anomaly-mcp"}
    for component in components:
        dockerfile = (root / component["context"] / "Dockerfile").read_text()
        assert "ARG APP_VERSION=0.0.0-dev" in dockerfile
        assert "org.opencontainers.image.version=$APP_VERSION" in dockerfile
        assert "org.opencontainers.image.revision=$GIT_SHA" in dockerfile
    publisher = jobs["containers"]["steps"][-1]["run"]
    assert '--image "$VERSION_IMAGE" --image "$SHA_IMAGE"' in publisher
    assert 'test "$DIGEST" = "$SHA_DIGEST"' in publisher
    assert "--write-enabled false --delete-enabled false" in publisher
    assert "latest" not in publisher
    assert jobs["pages"]["needs"] == "version"
    assert "site.release_version" in (root / "docs/_includes/footer_custom.html").read_text()
    assert "VITE_APP_VERSION" in (root / "apps/web-chat/frontend/src/main.jsx").read_text()


def test_release_reuses_published_images_and_source_version():
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/deploy-and-evaluate.yml").read_text())
    staging = workflow["jobs"]["deploy-staging"]
    assert staging["steps"][0]["with"]["fetch-depth"] == 0
    resolver = next(step["run"] for step in staging["steps"] if step.get("id") == "build-mcp")
    assert "az acr build" not in resolver
    assert "git tag --points-at" in resolver
    assert 'test "$DIGEST" = "$SHA_DIGEST"' in resolver
    assert 'azd env set APP_VERSION "$APP_VERSION"' in resolver
    agent = yaml.safe_load((root / "azure.yaml").read_text())
    settings = agent["services"]["threat-assessment-agent"]["environmentVariables"]
    assert {"name": "APP_VERSION", "value": "${APP_VERSION}"} in settings