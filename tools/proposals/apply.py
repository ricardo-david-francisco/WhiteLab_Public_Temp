"""Snippet → draft-PR proposal engine.

This module powers two channels (issue body, inbox folder) for landing
small code snippets safely. Hard rules:

1. **No auto-merge.** This engine only ever produces a working tree;
   the caller (CI workflow or the operator) opens a *draft* PR.
2. **Path allow-list.** Snippets may only land under paths matching
   :data:`ALLOW_RE`. Anything else is rejected outright.
3. **Anonymisation gate.** The proposed bytes are run through every
   anonymiser regex rule. If any rule fires (i.e. plaintext secret
   detected) the proposal is refused.

These rules together turn the funnel into a *pull-mode delivery*
channel rather than a remote-code-execution primitive: the worst a
malicious paste can do is force a no-op draft PR, never modify code
outside the allow-list, never leak secrets, never auto-merge.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import List, Optional, Sequence

import yaml

# Paths that may be written by a proposal. Matched by re.match (anchored
# at the start). The complement of FORBID_RE inside ALLOW_RE is what
# the funnel is allowed to touch.
ALLOW_RE = re.compile(
    r"^(docs/|infra/|tools/|tests/|inbox/|README\.md|AGENTS\.md|CONTRIBUTING\.md)"
)

# Hard denylist — these paths control the security envelope of the
# repo and must NEVER be writable from a proposal, even if they match
# ALLOW_RE.
FORBID_RE = re.compile(
    r"^("
    r"\.github/workflows/|"            # CI cannot rewrite itself.
    r"\.github/CODEOWNERS|"
    r"\.pre-commit-config\.yaml|"
    r"tools/guards/|"                  # zero-trust guards.
    r"tools/proposals/|"               # this engine.
    r"tools/anonymizer/|"              # anonymiser.
    r"policy/|"                        # OPA policies.
    r"vault/|"                         # secrets.
    r"audit/"                          # signed log.
    r")"
)


class ProposalError(ValueError):
    """Raised when a proposal must be rejected."""


@dataclasses.dataclass(frozen=True)
class FileWrite:
    """A single (target, bytes) pair the engine wants to write."""

    target: Path
    content: bytes
    note: str = ""


def validate_target(target: str) -> Path:
    """Normalise and validate ``target``; raise on rejection."""
    if not target or target != target.strip():
        raise ProposalError(f"target path is empty or has whitespace: {target!r}")
    if ".." in target.split("/"):
        raise ProposalError(f"target path traversal not allowed: {target!r}")
    if target.startswith("/") or target.startswith("\\"):
        raise ProposalError(f"target must be repo-relative, not absolute: {target!r}")
    if not ALLOW_RE.match(target):
        raise ProposalError(f"target outside allow-list: {target!r}")
    if FORBID_RE.match(target):
        raise ProposalError(f"target is on the FORBID list: {target!r}")
    return Path(target)


def assert_no_secrets(content: bytes, rules: Sequence) -> None:
    """Refuse a snippet whose content trips any anonymiser rule."""
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Binary blobs can't be reviewed by humans either; bounce them.
        raise ProposalError("proposal content is not valid UTF-8") from None

    # Avoid heavy import unless this function is actually called.
    from tools.anonymizer import anonymize as _an

    hits: List[str] = []
    for rule in rules:
        if rule.pattern is None or rule.keep:
            continue
        for m in rule.pattern.finditer(text):
            value = m.group(rule.capture) if rule.capture else m.group(0)
            if _an._is_placeholder(value):
                continue
            if rule.validator is not None and not rule.validator(value):
                continue
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"line {line}: cleartext {rule.cls}: {value[:24]}...")

    if hits:
        raise ProposalError(
            "proposal contains plaintext secrets — refused.\n"
            + "\n".join(hits)
        )


def _split_issue_body(body: str) -> List[FileWrite]:
    """Parse an issue body for ``target:`` markers + fenced code blocks.

    Expected shape (one or more of)::

        target: tools/example/foo.py
        ```python
        ...code...
        ```
    """
    writes: List[FileWrite] = []
    # Find every ``target:`` line and the immediately following code block.
    target_re = re.compile(r"^\s*target\s*:\s*(\S+)\s*$", re.MULTILINE)
    for m in target_re.finditer(body):
        tail = body[m.end():]
        fence_match = re.search(r"```[A-Za-z0-9_-]*\n(.*?)```", tail, re.DOTALL)
        if not fence_match:
            raise ProposalError(
                f"target {m.group(1)!r} declared but no fenced code "
                "block followed it in the issue body."
            )
        writes.append(
            FileWrite(
                target=Path(m.group(1)),
                content=fence_match.group(1).encode("utf-8"),
                note=f"from-issue-body: {m.group(1)}",
            )
        )
    if not writes:
        raise ProposalError(
            "no `target: <path>` + fenced-code-block pairs found in body."
        )
    return writes


def _parse_inbox_manifest(slug_dir: Path) -> List[FileWrite]:
    """Parse ``inbox/<slug>/manifest.yml`` and read each declared file."""
    manifest_path = slug_dir / "manifest.yml"
    if not manifest_path.is_file():
        raise ProposalError(f"missing manifest: {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    entries = data.get("files")
    if entries is None and "target" in data and "source" in data:
        entries = [{"target": data["target"], "source": data["source"]}]
    if not isinstance(entries, list) or not entries:
        raise ProposalError(
            f"manifest {manifest_path}: expected 'files: [...]' or "
            "top-level 'target:'/'source:' keys."
        )
    writes: List[FileWrite] = []
    for ent in entries:
        if not isinstance(ent, dict):
            raise ProposalError(f"manifest entry must be a mapping: {ent!r}")
        target = ent.get("target")
        source = ent.get("source")
        if not target or not source:
            raise ProposalError(f"manifest entry missing target/source: {ent!r}")
        if "/" in str(source).replace("\\", "/").split("/")[0] and str(source).startswith("/"):
            raise ProposalError(f"source must be relative to slug dir: {source!r}")
        src_path = (slug_dir / source).resolve()
        if not str(src_path).startswith(str(slug_dir.resolve())):
            raise ProposalError(f"source escapes slug dir: {source!r}")
        if not src_path.is_file():
            raise ProposalError(f"source not found: {src_path}")
        writes.append(
            FileWrite(
                target=Path(target),
                content=src_path.read_bytes(),
                note=f"from-inbox: {slug_dir.name}/{source}",
            )
        )
    return writes


def parse(*, body: Optional[str] = None, inbox: Optional[Path] = None) -> List[FileWrite]:
    """Dispatch on channel: issue body or inbox folder."""
    if body is not None and inbox is not None:
        raise ProposalError("provide either body= or inbox=, not both.")
    if body is not None:
        return _split_issue_body(body)
    if inbox is not None:
        return _parse_inbox_manifest(inbox)
    raise ProposalError("nothing to parse: pass body= or inbox=.")


def apply(
    writes: Sequence[FileWrite],
    *,
    repo_root: Path,
) -> List[Path]:
    """Validate then write each FileWrite under ``repo_root``.

    Returns the list of resolved on-disk paths that were written.
    Raises :class:`ProposalError` on the first invalid entry without
    touching the working tree.
    """
    from tools.anonymizer import anonymize as _an

    rules, _ = _an.load_rules(_an.DEFAULT_RULES)

    # Validate everything first; only write once everything is OK.
    plan: List[FileWrite] = []
    for w in writes:
        validate_target(w.target.as_posix())
        assert_no_secrets(w.content, rules)
        plan.append(w)

    out: List[Path] = []
    for w in plan:
        full = (repo_root / w.target).resolve()
        # Final guard: even after validation, ensure the resolved path
        # is still inside the repo root (no symlink trickery).
        if not str(full).startswith(str(repo_root.resolve())):
            raise ProposalError(f"resolved target escapes repo: {w.target}")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(w.content)
        out.append(full)
    return out
