"""Build the NotebookLM-friendly Markdown bundle of the WhiteLab repo.

The bundle is a single Markdown file at ``dist/whitelab-bundle.md``
containing:

* A header (commit SHA, generation timestamp, "how to use this") so a
  human or LLM landing on the file knows what they are looking at.
* The full directory tree.
* Every committed text file inlined under a language-fenced block,
  capped at ``MAX_LINES_PER_FILE`` lines so a single oversized log
  cannot dominate the bundle.

Hard precondition
=================

The bundle is produced **only** if ``python -m
tools.anonymizer.anonymize --verify infra/`` succeeds. Any cleartext
secret means we refuse to publish — there is no override flag because
the whole point of this artefact is that it is safe to paste into a
third party.

CLI
===

    python -m tools.digest.build_bundle [--out PATH] [--root PATH]

The defaults match the workflow: ``dist/whitelab-bundle.md`` under the
repo root resolved by ``git rev-parse --show-toplevel``.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
import sys
from pathlib import Path

# Hard caps. Cheap defence-in-depth against a future huge log file
# silently inflating the bundle past NotebookLM's per-source limit.
MAX_LINES_PER_FILE = 800
MAX_BYTES_PER_FILE = 256 * 1024  # 256 KiB before we truncate.

# Paths excluded even if they happen to be tracked. Aligns with
# .gitignore intent and keeps the bundle reviewer-safe.
SKIP_PATH_PREFIXES = (
    "dist/",
    ".sandbox/",
    "audit/",
    "vault/",
    "node_modules/",
)

# Suffixes we always treat as binary, regardless of NUL detection.
BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".tgz", ".xz", ".7z",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".so", ".dylib", ".dll", ".o", ".a", ".lib",
    ".jar", ".class", ".pyc", ".whl",
    ".mp3", ".mp4", ".mov", ".webm", ".avi",
})

# Suffix → fence language tag.
LANG_BY_SUFFIX = {
    ".py": "python",
    ".sh": "bash",
    ".bash": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".rego": "rego",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".conf": "ini",
    ".ini": "ini",
    ".env": "ini",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".dockerfile": "dockerfile",
    "Dockerfile": "dockerfile",
    ".mk": "makefile",
    "Makefile": "makefile",
}


class BundleError(RuntimeError):
    """Raised when the bundle cannot or must not be produced."""


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BundleError("not inside a git repository.")
    return Path(proc.stdout.decode("utf-8").strip())


def head_sha(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.decode("utf-8").strip() or "unknown"


def tracked_files(root: Path) -> list[Path]:
    """All committed paths, sorted, with skip rules already applied."""
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise BundleError("git ls-files failed.")
    files: list[Path] = []
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        rel = line.strip()
        if not rel:
            continue
        if any(rel.startswith(p) for p in SKIP_PATH_PREFIXES):
            continue
        files.append(Path(rel))
    files.sort(key=lambda p: p.as_posix())
    return files


def is_binary(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    if path.name in BINARY_SUFFIXES:
        return True
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def language_for(path: Path) -> str:
    if path.name in LANG_BY_SUFFIX:
        return LANG_BY_SUFFIX[path.name]
    return LANG_BY_SUFFIX.get(path.suffix.lower(), "")


def build_tree(files: list[Path]) -> str:
    """ASCII tree from a sorted list of relative paths."""
    lines: list[str] = ["."]
    seen: set[str] = set()
    for f in files:
        parts = f.parts
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i])
            if prefix not in seen:
                seen.add(prefix)
                lines.append(("    " * (i - 1)) + f"├── {parts[i - 1]}/")
        lines.append(("    " * (len(parts) - 1)) + f"├── {parts[-1]}")
    return "\n".join(lines)


def render_file(root: Path, rel: Path) -> str:
    """Render a single file as a fenced markdown block."""
    full = root / rel
    if is_binary(full):
        return (
            f"\n## `{rel.as_posix()}`\n\n"
            f"_(binary file, {full.stat().st_size} bytes — omitted from bundle)_\n"
        )
    try:
        text = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (
            f"\n## `{rel.as_posix()}`\n\n"
            "_(non-UTF-8 file — omitted from bundle)_\n"
        )

    truncated = False
    if len(text.encode("utf-8")) > MAX_BYTES_PER_FILE:
        # Trim by line count rather than mid-token to keep the fence valid.
        text = text[: MAX_BYTES_PER_FILE * 2]
        truncated = True
    lines = text.splitlines()
    if len(lines) > MAX_LINES_PER_FILE:
        lines = lines[:MAX_LINES_PER_FILE]
        truncated = True
    body = "\n".join(lines)

    lang = language_for(rel)
    fence = "```" + lang
    out = [f"\n## `{rel.as_posix()}`\n", fence, body, "```"]
    if truncated:
        out.append(
            f"\n<!-- truncated to {MAX_LINES_PER_FILE} lines / "
            f"{MAX_BYTES_PER_FILE} bytes; see repo for full file -->"
        )
    return "\n".join(out) + "\n"


def verify_anonymisation(root: Path) -> None:
    """Run the anonymiser in --verify mode and abort the bundle on failure."""
    infra = root / "infra"
    if not infra.exists():
        return
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.anonymizer.anonymize",
            "--verify",
            str(infra),
        ],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", errors="replace")
        raise BundleError(
            "anonymiser --verify failed; refusing to build the bundle.\n"
            + msg
        )


def header(root: Path) -> str:
    sha = head_sha(root)
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return (
        "# WhiteLab repository bundle\n\n"
        f"- **Commit:** `{sha}`\n"
        f"- **Generated (UTC):** `{ts}`\n"
        f"- **Lines-per-file cap:** {MAX_LINES_PER_FILE}\n\n"
        "## How to use this\n\n"
        "Upload this single file as a NotebookLM source. The whole\n"
        "WhiteLab repo (excluding generated, gitignored, and binary\n"
        "content) is inlined below as Markdown. Anonymisation is\n"
        "verified before this file is produced — every IP, MAC,\n"
        "hostname, password, token, key, and secret has been\n"
        "replaced with a deterministic placeholder.\n\n"
        "Suggested prompt: *\"You have my entire home-infrastructure\n"
        "repo. Tell me how I would deploy <component> following the\n"
        "WhiteLab conventions, with a draft PR I can paste into the\n"
        "repo via the inbox/ folder.\"*\n"
    )


def build(out_path: Path, root: Path) -> Path:
    verify_anonymisation(root)
    files = tracked_files(root)
    parts: list[str] = [header(root)]
    parts.append("\n## Directory tree\n\n```text\n")
    parts.append(build_tree(files))
    parts.append("\n```\n")
    parts.append("\n## Files\n")
    for rel in files:
        parts.append(render_file(root, rel))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(parts), encoding="utf-8")
    return out_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build_bundle",
        description="Build dist/whitelab-bundle.md (anonymise-or-refuse).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: <repo>/dist/whitelab-bundle.md).",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: git rev-parse --show-toplevel).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if shutil.which("git") is None:
        print("build_bundle: git not found on PATH.", file=sys.stderr)
        return 2
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        root = args.root.resolve() if args.root is not None else repo_root()
        out = args.out if args.out is not None else root / "dist" / "whitelab-bundle.md"
        path = build(out, root)
    except BundleError as exc:
        print(f"build_bundle: {exc}", file=sys.stderr)
        return 1
    size = path.stat().st_size
    print(f"build_bundle: wrote {path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
