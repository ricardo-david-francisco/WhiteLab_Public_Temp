"""CLI driver for the proposal funnel.

Two modes::

    python -m tools.proposals.cli --issue-body-file path/to/body.md
    python -m tools.proposals.cli --inbox inbox/<slug>

Both validate, optionally write, and print one ``write: <path>`` line
per file the workflow should subsequently ``git add`` and commit. Exit
code 0 = success; 1 = parse / validation failure; 2 = bad usage.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from tools.proposals.apply import (
    FileWrite,
    ProposalError,
    apply,
    parse,
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / "Makefile").exists():
            return parent
    return Path.cwd()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="proposals.cli")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--issue-body-file", type=Path)
    src.add_argument("--inbox", type=Path)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only; do not write any files.",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (defaults to git toplevel).",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = args.root.resolve() if args.root is not None else _repo_root()

    try:
        if args.issue_body_file is not None:
            body = args.issue_body_file.read_text(encoding="utf-8")
            writes: List[FileWrite] = parse(body=body)
        else:
            writes = parse(inbox=args.inbox)

        if args.dry_run:
            # Still run validation to surface errors.
            from tools.proposals.apply import (
                assert_no_secrets,
                validate_target,
            )
            from tools.anonymizer import anonymize as _an

            rules, _ = _an.load_rules(_an.DEFAULT_RULES)
            for w in writes:
                validate_target(w.target.as_posix())
                assert_no_secrets(w.content, rules)
                print(f"plan: {w.target.as_posix()}  ({w.note})")
            return 0

        out = apply(writes, repo_root=root)
        for p in out:
            print(f"write: {p.relative_to(root).as_posix()}")
        return 0

    except ProposalError as exc:
        print(f"proposals.cli: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
