#!/usr/bin/env bash
# Idempotently create the labels referenced by .github/ISSUE_TEMPLATE/*.yml
# and the roadmap-sync workflow.
#
# Safe to re-run: gh label create --force updates the colour/description
# in place if the label already exists.

set -euo pipefail

REPO="${REPO:-${GITHUB_REPOSITORY:-ricardo-david-francisco/WhiteLab}}"

# Format: name|color|description
labels=(
  # Type
  "shower-thought|FBCA04|Captured on mobile, not yet triaged"
  "bug|D73A4A|Something is broken"
  "incident|B60205|Live operational incident"
  "chore|C2E0C6|Maintenance / cleanup"
  "infra|0E8A16|Infrastructure / IaC change"
  "rfc|5319E7|Design proposal / RFC"
  "docs|0075CA|Documentation only"
  "security|EE0701|Security-relevant"

  # Status (lifecycle on the Project board)
  "status:inbox|EDEDED|Captured, not yet triaged"
  "status:next|FEF2C0|Will be worked next"
  "status:in-progress|1D76DB|Actively being worked (WIP=1)"
  "status:blocked|E99695|Blocked on something external"
  "status:done|0E8A16|Closed and shipped"

  # Priority
  "p0|B60205|Now — drop everything"
  "p1|D93F0B|Soon"
  "p2|FBCA04|Scheduled"
  "p3|C5DEF5|Someday / nice-to-have"

  # Misc operational labels referenced by workflows
  "docs-skip|EDEDED|Bypass docs-up-to-date check (use sparingly)"
  "wontfix|FFFFFF|Closed without action"

  # PR #20 — holy-grail funnel
  "critique|5319E7|NotebookLM critique finding (auto-imported)"
  "decision|0E8A16|Architectural decision record link"
  "stale|EDEDED|No activity for 30 days; will not be auto-closed"
  "pinned|FEF2C0|Pinned to repo home (digest, etc.)"
)

for entry in "${labels[@]}"; do
  IFS='|' read -r name color desc <<<"$entry"
  echo "==> $name"
  gh label create "$name" \
    --repo "$REPO" \
    --color "$color" \
    --description "$desc" \
    --force
done

echo "Done."
