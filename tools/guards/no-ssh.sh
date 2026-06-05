#!/usr/bin/env bash
# tools/guards/no-ssh.sh
#
# Zero-trust invariant: SSH must not be reintroduced anywhere in the
# repo. Fails CI if any *added* line in the diff matches a forbidden
# pattern outside the documentation allow-list.
#
# Allow-list: paths where SSH may be discussed *as a deprecation*:
#   - docs/                  (all documentation — ADRs, runbooks,
#                            learning, contributions, roadmap, etc.
#                            describe the no-SSH policy; that text
#                            must not be blocked)
#   - tools/guards/no-ssh.sh (this guard itself, which lists the
#                            patterns it forbids)
#
# Real SSH re-introductions land in infra/, tools/, or
# .github/workflows/ — those are the surfaces this guard polices.

set -euo pipefail

PATTERNS=(
  '^[+].*Port[[:space:]]+22\b'
  '^[+].*sshd_config'
  '^[+].*ssh-rsa[[:space:]]'
  '^[+].*ssh-ed25519[[:space:]]'
  '^[+].*systemctl[[:space:]]+enable[[:space:]]+ssh'
  '^[+].*systemctl[[:space:]]+(start|unmask)[[:space:]]+ssh'
  '^[+].*service[[:space:]]+ssh[[:space:]]+(start|enable)'
)

ALLOWLIST_REGEX='^(docs/|tools/guards/no-ssh\.sh$)'

BASE_REF="${BASE_REF:-${GITHUB_BASE_REF:-origin/master}}"

# Resolve the diff range.
if git rev-parse --verify --quiet "$BASE_REF" >/dev/null; then
  RANGE="$BASE_REF...HEAD"
else
  echo "no-ssh: base ref '$BASE_REF' not found; falling back to HEAD~1" >&2
  RANGE="HEAD~1...HEAD"
fi

# Build the file list.
mapfile -t CHANGED < <(git diff --name-only --diff-filter=AM "$RANGE" \
                       | grep -Ev "$ALLOWLIST_REGEX" || true)

if [[ ${#CHANGED[@]} -eq 0 ]]; then
  echo "no-ssh: no candidate files in $RANGE."
  exit 0
fi

found=0
for f in "${CHANGED[@]}"; do
  [[ -f "$f" ]] || continue
  added="$(git diff "$RANGE" -- "$f")"
  for pat in "${PATTERNS[@]}"; do
    if grep -E -q "$pat" <<<"$added"; then
      echo "no-ssh: forbidden pattern '$pat' in $f" >&2
      grep -E -n "$pat" <<<"$added" >&2 || true
      found=1
    fi
  done
done

if (( found )); then
  cat >&2 <<'MSG'

------------------------------------------------------------
Zero-trust guard: SSH is permanently disabled (ADR-0002).
If you genuinely need to reference SSH in *documentation*,
place the change under docs/ (all subfolders are exempt).

If you believe this policy should change, file a Decision
issue using the .github/ISSUE_TEMPLATE/decision.yml template
and write a superseding ADR.
------------------------------------------------------------
MSG
  exit 1
fi

echo "no-ssh: clean (${#CHANGED[@]} files inspected)."
