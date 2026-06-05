#!/usr/bin/env bash
# tools/critique/sync-critique-findings.sh
#
# Idempotently mirror the top-level "## N. <title>" findings of
# unified-critique.md into GitHub issues.
#
# - Dedup key: a hidden HTML comment in the issue body of the form
#       <!-- critique-anchor: <slug> -->
#   The slug is the GitHub-rendered fragment of the heading
#   (lower-case, non-alphanum -> -, runs collapsed, edges trimmed).
# - First/recurrent run creates the issue with labels
#   `critique`, `status:inbox` and a body that quotes the section.
# - On a subsequent run, if the section text changed, the issue body
#   is edited in place (single edit, no comment spam).
# - If any ADR under docs/decisions/ lists the slug in its front-matter
#   `related-critique:` block, the issue is closed with the comment
#   "Adopts ADR-NNNN" and labelled `decision`.
#
# Skipped sections (numeric prefix in the SKIP_SECTIONS list) are not
# imported. By default we skip the executive summary, the meta
# remediation roadmap and the cross-references section.
#
# Usage:
#   GH_TOKEN=...  REPO=ricardo-david-francisco/WhiteLab \
#     bash tools/critique/sync-critique-findings.sh [--print-only]

set -euo pipefail

REPO="${REPO:-${GITHUB_REPOSITORY:-ricardo-david-francisco/WhiteLab}}"
CRITIQUE_FILE="${CRITIQUE_FILE:-docs/contributions/running summary of unified contributions/unified critique/unified-critique.md}"
ADR_DIR="${ADR_DIR:-docs/decisions}"
PRINT_ONLY=0
SKIP_SECTIONS="${SKIP_SECTIONS:-1 10 11}"   # exec summary, roadmap, xrefs

for arg in "$@"; do
  case "$arg" in
    --print-only) PRINT_ONLY=1 ;;
    -h|--help)
      sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [[ ! -f "$CRITIQUE_FILE" ]]; then
  echo "critique file not found: $CRITIQUE_FILE" >&2
  exit 1
fi

# --- helpers --------------------------------------------------------

slugify() {
  # Match GitHub heading anchor algorithm closely enough for our use:
  # lowercase, drop punctuation except dashes/spaces, collapse spaces
  # to dashes.
  python3 - "$1" <<'PY'
import re, sys
s = sys.argv[1].lower()
s = re.sub(r"[^a-z0-9\s-]", "", s)
s = re.sub(r"\s+", "-", s).strip("-")
print(s)
PY
}

adr_supersedes_anchor() {
  # Returns the ADR id (e.g. "ADR-0002") if any ADR file lists $1 in
  # `related-critique:`. Empty string otherwise.
  local anchor="$1"
  local f
  shopt -s nullglob
  for f in "$ADR_DIR"/ADR-*.md; do
    # Only consider Accepted ADRs.
    if grep -qE '^status:[[:space:]]*Accepted' "$f" \
       && grep -qE "^[[:space:]]*-[[:space:]]*\"#${anchor}\"" "$f" 2>/dev/null; then
      basename "$f" | sed -E 's/^(ADR-[0-9]+).*/\1/'
      return 0
    fi
  done
  echo ""
}

# --- parse critique into per-section files -------------------------

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

awk -v outdir="$WORK" '
  /^## [0-9]+\. / {
    if (current) { close(current) }
    n = $2; sub(/\./, "", n)
    title = $0; sub(/^## [0-9]+\. /, "", title)
    fname = outdir "/section-" n ".md"
    print n "|" title > outdir "/index.txt"
    current = fname
    print "## " n ". " title > current
    next
  }
  /^## [^0-9]/ { if (current) { close(current); current = "" } }
  current { print >> current }
' "$CRITIQUE_FILE"

# --- per-section import --------------------------------------------

while IFS='|' read -r num title; do
  [[ -z "$num" ]] && continue
  case " $SKIP_SECTIONS " in *" $num "*) continue ;; esac

  slug="${num}-$(slugify "$title")"
  body_file="$WORK/section-${num}.md"
  issue_title="[critique #${num}] ${title}"

  # Build the issue body.
  issue_body_file="$WORK/issue-${num}.md"
  {
    echo "<!-- critique-anchor: ${slug} -->"
    echo
    echo "**Auto-imported from \`unified-critique.md\`.** Do not edit"
    echo "this issue body manually — re-run \`tools/critique/sync-critique-findings.sh\`"
    echo "to refresh."
    echo
    echo "**Disposition path.** To reject or adapt this finding, open"
    echo "an issue using the *Decision* template; it will land here as"
    echo "an ADR under \`docs/decisions/\`. The next importer run will"
    echo "auto-close this issue with the ADR id."
    echo
    echo "---"
    echo
    cat "$body_file"
  } > "$issue_body_file"

  adr_id="$(adr_supersedes_anchor "$slug")"

  if (( PRINT_ONLY )); then
    echo "[dry-run] section ${num} slug=${slug} adr=${adr_id:-none}"
    continue
  fi

  # Locate an existing issue by anchor.
  existing="$(gh issue list \
    --repo "$REPO" \
    --state all \
    --search "in:body \"critique-anchor: ${slug}\"" \
    --json number,state \
    --jq '.[0]')"

  number="$(jq -r '.number // empty' <<<"$existing")"
  state="$(jq -r '.state // empty' <<<"$existing")"

  if [[ -z "$number" ]]; then
    echo "==> create #${slug}"
    create_url="$(gh issue create --repo "$REPO" \
      --title "$issue_title" \
      --body-file "$issue_body_file" \
      --label "critique" --label "status:inbox")"
    # gh prints the issue URL on stdout; extract the trailing number.
    number="${create_url##*/}"
    if ! [[ "$number" =~ ^[0-9]+$ ]]; then
      echo "could not parse issue number from: $create_url" >&2
      exit 1
    fi
  else
    echo "==> update #${number} (${slug})"
    gh issue edit "$number" --repo "$REPO" \
      --body-file "$issue_body_file" >/dev/null
  fi

  # If a superseding ADR exists, mark + close. Re-evaluate state from
  # GH (the search-by-anchor lookup above may have been served from a
  # stale index when the issue was just created).
  if [[ -n "$adr_id" ]]; then
    cur_state="$(gh issue view "$number" --repo "$REPO" \
      --json state --jq '.state' 2>/dev/null || echo "")"
    if [[ "$cur_state" != "CLOSED" ]]; then
      echo "==> close #${number} as adopted by ${adr_id}"
      gh issue edit "$number" --repo "$REPO" \
        --add-label "decision" >/dev/null
      gh issue close "$number" --repo "$REPO" \
        --comment "Adopts ${adr_id}. Closing automatically." >/dev/null
    fi
  fi
done < "$WORK/index.txt"

echo "Done."
