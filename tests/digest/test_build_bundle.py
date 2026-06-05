"""Tests for tools.digest.build_bundle."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.digest import build_bundle


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    """Initialise a tiny self-contained git repo for bundle tests."""
    _git(tmp_path, "init", "-q", "-b", "master")
    _git(tmp_path, "config", "user.email", "t@e.x")
    _git(tmp_path, "config", "user.name", "tester")
    (tmp_path / "README.md").write_text("# fake\n", encoding="utf-8")
    (tmp_path / "tools.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "leftover.md").write_text("ignore me\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_tracked_files_skips_dist(fake_repo: Path):
    files = build_bundle.tracked_files(fake_repo)
    rels = {f.as_posix() for f in files}
    assert "README.md" in rels
    assert "tools.py" in rels
    assert "image.png" in rels
    # dist/* must be filtered.
    assert all(not r.startswith("dist/") for r in rels)


def test_is_binary_detects_png(fake_repo: Path):
    assert build_bundle.is_binary(fake_repo / "image.png")
    assert not build_bundle.is_binary(fake_repo / "README.md")


def test_render_file_text(fake_repo: Path):
    out = build_bundle.render_file(fake_repo, Path("tools.py"))
    assert "## `tools.py`" in out
    assert "```python" in out
    assert "print('hi')" in out


def test_render_file_binary_omitted(fake_repo: Path):
    out = build_bundle.render_file(fake_repo, Path("image.png"))
    assert "binary file" in out
    assert "```" not in out


def test_render_file_truncates(tmp_path: Path):
    big = tmp_path / "big.py"
    big.write_text("\n".join(f"x = {i}" for i in range(2000)), encoding="utf-8")
    out = build_bundle.render_file(tmp_path, Path("big.py"))
    assert "truncated" in out
    # The body should not contain x = 1500.
    assert "x = 1999" not in out


def test_build_writes_bundle(fake_repo: Path):
    out = fake_repo / "dist" / "whitelab-bundle.md"
    build_bundle.build(out, fake_repo)
    text = out.read_text(encoding="utf-8")
    assert "# WhiteLab repository bundle" in text
    assert "## Directory tree" in text
    assert "## `README.md`" in text
    assert "## `tools.py`" in text
    # Binary file rendered with notice, not contents.
    assert "binary file" in text


def test_build_refuses_when_anonymisation_dirty(fake_repo: Path):
    # Plant a fake infra/ tree with a real-looking secret.
    infra = fake_repo / "infra"
    infra.mkdir()
    (infra / "leak.conf").write_text(
        'password = "Sup3rS3cretValue!"\n', encoding="utf-8"
    )
    _git(fake_repo, "add", "-A")
    _git(fake_repo, "commit", "-q", "-m", "leak")

    out = fake_repo / "dist" / "whitelab-bundle.md"
    with pytest.raises(build_bundle.BundleError):
        build_bundle.build(out, fake_repo)
    assert not out.exists()
