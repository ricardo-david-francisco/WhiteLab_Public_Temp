# 01 — Branch + Diary Workflow

This is the day-to-day procedure for any change to the repo.

## TL;DR

```text
git checkout master
git pull --ff-only
git checkout -b feature/<short-topic>
# ... work, commit, repeat ...
# Update PROJECT_HISTORY.md with a new dated entry summarizing the branch.
git push -u origin feature/<short-topic>
# Open PR in GitHub UI -> review -> merge (squash or fast-forward).
```

## Branch naming

- `feature/<topic>` — design, docs, tooling.
- `audit/<device>-<yyyy-mm-dd>` — review of a specific device snapshot.
- `change/<device>-<topic>` — proposed device-side change with rollback plan.
- `incident/<yyyy-mm-dd>-<short>` — anything that touched secrets or required
  a force-push purge. Always documented.

## Commit messages

Conventional-commit-ish, scoped to area:

```text
docs(architecture): propose anonymization pipeline
infra(opnsense): add sanitized snapshot 2026-05-04
tools(anonymize): add opnsense profile
chore: bump pre-commit hook versions
```

Keep commits small and focused. Reviewers read every line on this repo.

## `PROJECT_HISTORY.md` entry — required on every merging branch

Append (at the top, under the date) a bullet per merged branch:

```text
## 2026-05-04
- (feature/architecture-plan) Initial repo layout, security policy, and design docs.
```

If multiple branches merge on the same date, group bullets under that one
date heading.

## Pre-merge checklist (reviewer)

- [ ] Diff contains no secrets, no real IPs, no real MACs, no real hostnames.
- [ ] Files in `infra/<device>/exports/` are clearly suffixed `.sanitized.<ext>`.
- [ ] `vault/` is untouched and not referenced by any tracked file path.
- [ ] `PROJECT_HISTORY.md` updated.
- [ ] CI/pre-commit `verify.py` passed (once implemented).

## Merging

- Default: **squash merge** to keep `master` linear and each diary entry
  matches exactly one commit.
- Exception: a multi-commit branch where each commit is independently
  meaningful → fast-forward only, no merge commits.
- Never use the GitHub "create a merge commit" button on this repo.
