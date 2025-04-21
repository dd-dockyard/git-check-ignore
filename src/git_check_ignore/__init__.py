from collections.abc import Iterable
from pathlib import Path
from sys import path_hooks
from typing import NamedTuple

import subprocess


class GitCheckIgnoreError(Exception):
    pass


class GitCheckIgnoreExitStatusError(GitCheckIgnoreError):
    pass


class GitCheckIgnoreOutputError(GitCheckIgnoreError):
    pass


class GitCheckIgnoreMatch(NamedTuple):
    source: str
    linenum: int
    pattern: str


class GitCheckIgnoreResult(NamedTuple):
    pathname: str
    ignored: bool
    match: GitCheckIgnoreMatch | None


def git_check_ignore(*paths: str | Path) -> Iterable[GitCheckIgnoreResult]:
    input_paths = b"\x00".join(map(lambda x: str(x).encode(), paths)) + b"\x00"

    command = subprocess.run(
        ["git", "check-ignore", "-n", "-v", "-z", "--stdin"],
        check=False,
        input=input_paths,
        stdout=subprocess.PIPE,
    )

    if command.returncode not in (0, 1):
        raise GitCheckIgnoreExitStatusError(
            f"Unexpected exit status from git: {command.returncode}", command.returncode
        )

    output_paths = command.stdout[:-1]
    if not len(output_paths):
        raise GitCheckIgnoreOutputError("No output from git")

    output_fields: list[bytes] = output_paths.split(b"\x00")
    for i in range(0, len(output_fields), 4):
        if len(output_fields[i]):
            match = GitCheckIgnoreMatch(
                output_fields[i].decode(),
                int(output_fields[i + 1].decode()),
                output_fields[i + 2].decode().strip(),
            )
        else:
            match = None

        yield GitCheckIgnoreResult(
            output_fields[i + 3].decode(),
            match is not None and not match.pattern.startswith("!"),
            match,
        )


def ignored_pathnames(*paths: str | Path) -> Iterable[str]:
    for result in git_check_ignore(*paths):
        if result.ignored:
            yield result.pathname


def ignored_paths(*paths: str | Path) -> Iterable[Path]:
    for result in ignored_pathnames(*paths):
        yield Path(result)


def not_ignored_pathnames(*paths: str | Path) -> Iterable[str]:
    for result in git_check_ignore(*paths):
        if not result.ignored:
            yield result.pathname


def not_ignored_paths(*paths: str | Path) -> Iterable[Path]:
    for result in not_ignored_pathnames(*paths):
        yield Path(result)
