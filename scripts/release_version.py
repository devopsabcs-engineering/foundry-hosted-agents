import argparse
import json
from pathlib import Path
import re
import subprocess


VERSION_TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def git(*arguments, cwd=None):
    return subprocess.check_output(
        ["git", *arguments], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


def allocate(target="HEAD", cwd=None):
    target = git("rev-parse", "--verify", f"{target}^{{commit}}", cwd=cwd)
    history = git("rev-list", "--first-parent", target, cwd=cwd).splitlines()
    tags = {}
    for tag in git("tag", "--list", "v*", cwd=cwd).splitlines():
        match = VERSION_TAG.fullmatch(tag)
        if match:
            commit = git("rev-parse", f"{tag}^{{commit}}", cwd=cwd)
            if commit in tags:
                raise ValueError(f"Multiple release tags on {commit}")
            tags[commit] = (tag, tuple(map(int, match.groups())))
    if target in tags:
        return [{"commit": target, "version": tags[target][0][1:]}]
    previous = next((commit for commit in history if commit in tags), None)
    if previous is None:
        if tags:
            raise ValueError("Release tags exist outside the target first-parent history")
        pending = [target]
        major, minor, patch = 1, 0, -1
    else:
        pending = list(reversed(history[:history.index(previous)]))
        major, minor, patch = tags[previous][1]
    releases = []
    existing = {tag for tag, _ in tags.values()}
    for commit in pending:
        patch += 1
        version = f"{major}.{minor}.{patch}"
        if f"v{version}" in existing:
            raise ValueError(f"Release tag v{version} already exists on another commit")
        releases.append({"commit": commit, "version": version})
    for release in releases:
        git("tag", f"v{release['version']}", release["commit"], cwd=cwd)
    return releases


def releases_for_push(target="HEAD", before=None, cwd=None):
    releases = allocate(target, cwd=cwd)
    if not before or set(before) == {"0"}:
        return releases
    commits = git("rev-list", "--first-parent", "--reverse", f"{before}..{target}", cwd=cwd).splitlines()
    result = []
    for commit in commits:
        tags = [tag for tag in git("tag", "--points-at", commit, cwd=cwd).splitlines()
                if VERSION_TAG.fullmatch(tag)]
        if tags:
            result.append({"commit": commit, "version": tags[0][1:]})
    return result or releases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="HEAD")
    parser.add_argument("--before")
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    releases = releases_for_push(options.target, options.before)
    payload = json.dumps(releases)
    if options.output:
        options.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()