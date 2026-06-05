#!/usr/bin/env bash
# digest-repo.sh — thin wrapper around tools/digest/build_bundle.py.
#
# Produces dist/whitelab-bundle.md (a single Markdown file ready fo
# NotebookLM, Claude, Gemini, Kiro, or any other context-window-bound
# tool). Refuses to publish if any committed file under infra/ still
# carries cleartext secrets.
#
# Kept as a shell wrapper so existing CI workflows and runbooks that
# reference digest-repo.sh continue to work unchanged.
set -eu

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

# Allow callers to pass through arguments (e.g. --out alt/path.md).
exec python3 -m tools.digest.build_bundle "$@"
