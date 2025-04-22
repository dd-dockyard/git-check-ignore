"""
.. include:: ../../README.md
"""

from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

import subprocess


class GitCheckIgnoreError(Exception):
    """Base class for all unique exceptions thrown by this module"""


class GitCheckIgnoreExitStatusError(GitCheckIgnoreError):
    """Thrown if `git check-ignore` exits with a status other than 0 or 1"""


class GitCheckIgnoreOutputError(GitCheckIgnoreError):
    """Thrown if `git check-ignore` does not produce any output"""


class GitCheckIgnoreMatch(NamedTuple):
    """Information about which `.gitignore` pattern matched a pathname"""

    source: str
    """The path of the `.gitignore` file containing the pattern"""

    linenum: int
    """The line number of the `.gitignore` file containing the pattern"""

    pattern: str
    """The pattern that matched the pathname"""


class GitCheckIgnoreResult(NamedTuple):
    """The result of running `git check-ignore` on a particular pathname"""

    pathname: str
    """The pathname that was evaluated"""

    ignored: bool
    """`True` if `git` will ignore the path; `False` otherwise."""

    match: GitCheckIgnoreMatch | None
    """Information about which, if any, `.gitignore` pattern matched the pathname.

    NOTE: If a pathname was matched by a negative pattern, `ignored` will be `False` but
    `match` will still contain the matching pattern.
    """


def git_check_ignore(*paths: str | Path) -> Iterable[GitCheckIgnoreResult]:
    """Pass a list of pathnames to `git check-ignore` and parse the results.

    This is the fully-featured version of the API; the result will be an iterator of
    :class:`GitCheckIgnoreResult` objects. Use this if you need to know which
    `.gitignore` pattern or file matched a particular pathname.

    This runs `git` in the current working directory. If your Git repository is
    somewhere else, it is your responsibility to point Git at it somehow, either by
    changing the working directory with [os.chdir](https://docs.python.org/3.13/library/os.html#os.chdir)
    or perhaps by setting some [environment variables](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables).

    Passing pathnames that are not contained within a repository will likely lead to
    a `GitCheckIgnoreExitStatusError`.

    :param paths: Pathnames to evaluate
    :raises GitCheckIgnoreExitStatusError: If `git check-ignore` exits with a status other than 0 or 1
    :raises GitCheckIgnoreOutputError: If `git check-ignore` did not produce any output
    :raises KeyError: If `git check-ignore` output is malformed
    :raises ValueError: If `git check-ignore` output is malformed
    :raises UnicodeDecodeError: If `git check-ignore` output is malformed
    """
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
    """Given a list of pathnames, iterate over those that `git` would ignore.

    Use this function over :func:`git_check_ignore` if you only need to determine
    which pathnames would be ignored, and you do not care which pattern is causing them
    to be ignored.

    This function is implemented on top of :func:`git_check_ignore`; please see the
    documentation for that function for additional usage notes and caveats.

    :param paths: Paths or pathnames to evaluate
    """
    for result in git_check_ignore(*paths):
        if result.ignored:
            yield result.pathname


def ignored_paths(*paths: str | Path) -> Iterable[Path]:
    """As :func:`ignored_pathnames`, but returns :class:`pathlib.Path` objects.

    Use this over :func:`ignored_pathnames` if you prefer an object-oriented
    approach to paths.

    This function is implemented on top of :func:`git_check_ignore`; please see the
    documentation for that function for additional usage notes and caveats.

    :param paths: Paths or pathnames to evaluate
    """
    return map(Path, ignored_pathnames(*paths))


def not_ignored_pathnames(*paths: str | Path) -> Iterable[str]:
    """Given a list of pathnames, iterate over those that `git` *WOULD NOT* ignore.

    The inverse of :func:`ignored_pathnames`

    This function is implemented on top of :func:`git_check_ignore`; please see the
    documentation for that function for additional usage notes and caveats.

    :param paths: Paths or pathnames to evaluate
    """
    for result in git_check_ignore(*paths):
        if not result.ignored:
            yield result.pathname


def not_ignored_paths(*paths: str | Path) -> Iterable[Path]:
    """As :func:`not_ignored_pathnames`, but returns :class:`pathlib.Path` objects.

    Use this over :func:`not_ignored_pathnames` if you prefer an object-oriented
    approach to paths.

    This function is implemented on top of :func:`git_check_ignore`; please see the
    documentation for that function for additional usage notes and caveats.

    :param paths: Paths or pathnames to evaluate
    """
    return map(Path, not_ignored_pathnames(*paths))
