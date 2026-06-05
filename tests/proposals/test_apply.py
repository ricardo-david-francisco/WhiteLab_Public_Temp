"""Tests for tools.proposals.apply."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tools.proposals import apply as proposals


# ----------------------------------------------------------------------
# validate_target
# ----------------------------------------------------------------------

def test_validate_target_accepts_allowed_paths():
    proposals.validate_target("docs/runbooks/foo.md")
    proposals.validate_target("tools/example/foo.py")
    proposals.validate_target("infra/lxc/ct-100-x/compose.yaml")
    proposals.validate_target("README.md")


def test_validate_target_rejects_path_traversal():
    with pytest.raises(proposals.ProposalError):
        proposals.validate_target("docs/../../etc/shadow")


def test_validate_target_rejects_absolute():
    with pytest.raises(proposals.ProposalError):
        proposals.validate_target("/etc/passwd")


def test_validate_target_rejects_outside_allowlist():
    with pytest.raises(proposals.ProposalError):
        proposals.validate_target("vault/anonmap.age")
    with pytest.raises(proposals.ProposalError):
        proposals.validate_target("audit/log.jsonl")
    with pytest.raises(proposals.ProposalError):
        proposals.validate_target(".env")


def test_validate_target_rejects_forbidden_subtrees():
    for bad in (
        ".github/workflows/ci.yml",
        ".github/CODEOWNERS",
        "tools/guards/no_ssh.sh",
        "tools/proposals/apply.py",
        "tools/anonymizer/anonymize.py",
        "policy/main.rego",
    ):
        with pytest.raises(proposals.ProposalError):
            proposals.validate_target(bad)


# ----------------------------------------------------------------------
# issue body parser
# ----------------------------------------------------------------------

def test_split_issue_body_single_target():
    body = dedent(
        """
        Some context.

        target: docs/runbooks/foo.md

        ```markdown
        # heading
        body
        ```
        """
    )
    writes = proposals._split_issue_body(body)
    assert len(writes) == 1
    assert writes[0].target == Path("docs/runbooks/foo.md")
    assert b"# heading" in writes[0].content


def test_split_issue_body_multiple_targets():
    body = dedent(
        """
        target: docs/a.md
        ```markdown
        A
        ```

        target: docs/b.md
        ```markdown
        B
        ```
        """
    )
    writes = proposals._split_issue_body(body)
    assert [w.target.as_posix() for w in writes] == ["docs/a.md", "docs/b.md"]


def test_split_issue_body_no_targets():
    with pytest.raises(proposals.ProposalError):
        proposals._split_issue_body("nothing actionable here")


def test_split_issue_body_target_without_fence():
    body = "target: docs/foo.md\nno code block here at all"
    with pytest.raises(proposals.ProposalError):
        proposals._split_issue_body(body)


# ----------------------------------------------------------------------
# inbox manifest parser
# ----------------------------------------------------------------------

def test_inbox_manifest_single(tmp_path: Path):
    slug = tmp_path / "add-foo"
    slug.mkdir()
    (slug / "foo.md").write_text("hello\n", encoding="utf-8")
    (slug / "manifest.yml").write_text(
        "target: docs/foo.md\nsource: foo.md\n", encoding="utf-8"
    )
    writes = proposals._parse_inbox_manifest(slug)
    assert len(writes) == 1
    assert writes[0].target == Path("docs/foo.md")
    assert writes[0].content == b"hello\n"


def test_inbox_manifest_multiple(tmp_path: Path):
    slug = tmp_path / "two-files"
    slug.mkdir()
    (slug / "a.md").write_text("A\n", encoding="utf-8")
    (slug / "b.md").write_text("B\n", encoding="utf-8")
    (slug / "manifest.yml").write_text(
        dedent(
            """
            files:
              - target: docs/a.md
                source: a.md
              - target: docs/b.md
                source: b.md
            """
        ).strip(),
        encoding="utf-8",
    )
    writes = proposals._parse_inbox_manifest(slug)
    assert [w.target.as_posix() for w in writes] == ["docs/a.md", "docs/b.md"]


def test_inbox_manifest_missing(tmp_path: Path):
    slug = tmp_path / "broken"
    slug.mkdir()
    with pytest.raises(proposals.ProposalError):
        proposals._parse_inbox_manifest(slug)


def test_inbox_manifest_source_escape(tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("evil\n", encoding="utf-8")
    slug = tmp_path / "evil"
    slug.mkdir()
    (slug / "manifest.yml").write_text(
        "target: docs/x.md\nsource: ../outside.txt\n", encoding="utf-8"
    )
    with pytest.raises(proposals.ProposalError):
        proposals._parse_inbox_manifest(slug)


# ----------------------------------------------------------------------
# secret refusal
# ----------------------------------------------------------------------

def test_apply_refuses_secret(tmp_path: Path):
    writes = [
        proposals.FileWrite(
            target=Path("docs/leak.md"),
            content=b'password = "Sup3rS3cretValue!"\n',
        )
    ]
    with pytest.raises(proposals.ProposalError):
        proposals.apply(writes, repo_root=tmp_path)
    # And no file ended up written.
    assert not (tmp_path / "docs" / "leak.md").exists()


def test_apply_writes_clean_snippet(tmp_path: Path):
    writes = [
        proposals.FileWrite(
            target=Path("docs/clean.md"),
            content=b"# perfectly clean text\n",
        )
    ]
    out = proposals.apply(writes, repo_root=tmp_path)
    assert (tmp_path / "docs" / "clean.md").exists()
    assert out[0].read_bytes() == b"# perfectly clean text\n"


def test_apply_rejects_target_before_writing(tmp_path: Path):
    writes = [
        proposals.FileWrite(
            target=Path("docs/clean.md"),
            content=b"# clean\n",
        ),
        proposals.FileWrite(
            target=Path("vault/anonmap.age"),
            content=b"ignored",
        ),
    ]
    with pytest.raises(proposals.ProposalError):
        proposals.apply(writes, repo_root=tmp_path)
    # The first file must NOT have been written, because validation is
    # done up-front.
    assert not (tmp_path / "docs" / "clean.md").exists()
