import git_check_ignore
import pytest
import subprocess
import os
from pathlib import Path


@pytest.fixture(scope="session")
def test_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    parent_path = tmp_path_factory.mktemp("repo")
    repo_path = parent_path.joinpath("testrepo")

    subprocess.run(["git", "init", str(repo_path)], check=True)

    repo_path.joinpath("README.md").touch()
    repo_path.joinpath("ignore.txt").touch()
    repo_path.joinpath("subdir").mkdir()
    repo_path.joinpath("subdir", "ignore.txt").touch()
    repo_path.joinpath("subdir", "chicken.txt").touch()

    with open(repo_path.joinpath(".gitignore"), "w") as ignore_out:
        ignore_out.write("ignore.txt\n")

    with open(repo_path.joinpath("subdir", ".gitignore"), "w") as ignore_out:
        ignore_out.write("*\n")
        ignore_out.write("!.gitignore\n")

    return repo_path.resolve()


def test_git_check_ignore(test_repo: Path):
    os.chdir(test_repo)

    results = {
        result.pathname: result
        for result in git_check_ignore.git_check_ignore(
            "README.md",
            "ignore.txt",
            "subdir/chicken.txt",
            "subdir/ignore.txt",
            "subdir/.gitignore",
        )
    }

    assert "README.md" in results
    assert not results["README.md"].ignored
    assert results["README.md"].match is None

    assert "ignore.txt" in results
    assert results["ignore.txt"].ignored
    assert results["ignore.txt"].match is not None
    assert results["ignore.txt"].match.source == ".gitignore"
    assert results["ignore.txt"].match.linenum == 1
    assert results["ignore.txt"].match.pattern == "ignore.txt"

    assert "subdir/chicken.txt" in results
    assert results["subdir/chicken.txt"].ignored
    assert results["subdir/chicken.txt"].match is not None
    assert results["subdir/chicken.txt"].match.source == "subdir/.gitignore"
    assert results["subdir/chicken.txt"].match.linenum == 1
    assert results["subdir/chicken.txt"].match.pattern == "*"

    assert "subdir/ignore.txt" in results
    assert results["subdir/ignore.txt"].ignored
    assert results["subdir/ignore.txt"].ignored
    assert results["subdir/ignore.txt"].match is not None
    assert results["subdir/ignore.txt"].match.source == "subdir/.gitignore"
    assert results["subdir/ignore.txt"].match.linenum == 1
    assert results["subdir/ignore.txt"].match.pattern == "*"

    assert "subdir/.gitignore" in results
    assert not results["subdir/.gitignore"].ignored
    assert results["subdir/.gitignore"].match is not None
    assert results["subdir/.gitignore"].match.linenum == 2
    assert results["subdir/.gitignore"].match.source == "subdir/.gitignore"
    assert results["subdir/.gitignore"].match.pattern == "!.gitignore"


def test_ignored_pathnames(test_repo: Path):
    os.chdir(test_repo)

    results = list(
        git_check_ignore.ignored_pathnames(
            "README.md",
            "ignore.txt",
            "subdir/chicken.txt",
            "subdir/ignore.txt",
            "subdir/.gitignore",
        )
    )

    assert "README.md" not in results
    assert "ignore.txt" in results
    assert "subdir/chicken.txt" in results
    assert "subdir/ignore.txt" in results
    assert "subdir/.gitignore" not in results


def test_not_ignored_pathnames(test_repo: Path):
    os.chdir(test_repo)

    results = list(
        git_check_ignore.not_ignored_pathnames(
            "README.md",
            "ignore.txt",
            "subdir/chicken.txt",
            "subdir/ignore.txt",
            "subdir/.gitignore",
        )
    )

    assert "README.md" in results
    assert "ignore.txt" not in results
    assert "subdir/chicken.txt" not in results
    assert "subdir/ignore.txt" not in results
    assert "subdir/.gitignore" in results


def test_ignored_paths(test_repo: Path):
    os.chdir(test_repo)

    results = list(
        git_check_ignore.ignored_paths(
            "README.md",
            "ignore.txt",
            "subdir/chicken.txt",
            "subdir/ignore.txt",
            "subdir/.gitignore",
        )
    )

    assert Path("README.md") not in results
    assert Path("ignore.txt") in results
    assert Path("subdir/chicken.txt") in results
    assert Path("subdir/ignore.txt") in results
    assert Path("subdir/.gitignore") not in results


def test_not_ignored_paths(test_repo: Path):
    os.chdir(test_repo)

    results = list(
        git_check_ignore.not_ignored_paths(
            "README.md",
            "ignore.txt",
            "subdir/chicken.txt",
            "subdir/ignore.txt",
            "subdir/.gitignore",
        )
    )

    assert Path("README.md") in results
    assert Path("ignore.txt") not in results
    assert Path("subdir/chicken.txt") not in results
    assert Path("subdir/ignore.txt") not in results
    assert Path("subdir/.gitignore") in results
