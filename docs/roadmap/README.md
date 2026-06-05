# WhiteLab Roadmap & Operations

> **The roadmap is GitHub Issues + GitHub Projects. This file is the
> map to it.** Issues are the unit of capture; the Project board is
> the unit of prioritization; merged PRs (with the issues they close)
> are the unit of done. Everything else \u2014 critiques, RFCs, runbooks
> \u2014 references one of those three primitives.

## 1. Why this is centralized in GitHub (and free)

The repository is already the single source of truth for code,
configuration, and documentation. Putting issues and the roadmap in
the same place keeps every layer aligned and removes the "where did
I write that down" failure mode. It also costs nothing on a private
GitHub Free repository.

* **Issues** \u2014 capture (low friction, mobile-first, ADHD-friendly).
* **Projects (v2)** \u2014 prioritisation (Kanban board + roadmap view).
* **Pull requests** \u2014 execution (cryptographically gated).
* **Workflows** \u2014 enforcement (this directory + `.github/workflows/`).

No Google Keep, no Trello, no Jira, no Notion. The mobile capture
flow is the GitHub Mobile app, free, with biometrics and 2FA.

## 2. The four artifact types and where they live

| Type             | Captured as                       | Lives in                                                                                                                                                                 | Lifecycle                                                      |
| ---------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Shower thought   | Issue with `shower-thought` label | GitHub Issues                                                                                                                                                            | Triaged within the next session into Bug / RFC / Out-of-scope. |
| Bug / chore      | Issue with `bug` or `chore` label | GitHub Issues                                                                                                                                                            | Closed by a merging PR that links it.                          |
| RFC (design)     | Markdown file                     | [`docs/contributions/pending-RFCs/`](../contributions/pending-RFCs/) + Issue with `rfc` label                                                                            | Promoted to architecture doc on accept; archived on reject.    |
| Critique finding | Section in the unified critique   | [`docs/contributions/running summary of unified contributions/unified critique/`](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/) | Spawns one RFC per recommendation when scheduled.              |

## 3. The capture flow (mobile, two taps)

1. Open GitHub Mobile.
2. Tap `+` \u2192 `New issue` on `WhiteLab`.
3. Pick the **Shower thought** template
   ([`.github/ISSUE_TEMPLATE/shower-thought.yml`](../../.github/ISSUE_TEMPLATE/shower-thought.yml)).
4. Type the bullet, hit submit. Done.

The `shower-thought` template auto-applies the label and assigns the
issue to the maintainer, so it lands on the Project board's
`Inbox` column without further effort.

## 4. The triage flow (next-session, ten minutes)

When you sit down at the lab, work the `Inbox` column on the
Project board top-down:

* **Real action** \u2192 relabel `bug` / `chore` / `infra` and move to
  `Backlog` (or `Next` if it's small and you'll do it now).
* **Design needed** \u2192 relabel `rfc`, file a stub under
  `docs/contributions/pending-RFCs/RFC-NNNN-<slug>.md`, link it from
  the issue body, move to `RFC drafting`.
* **Already covered** \u2192 close with a comment linking to the existing
  artifact.
* **Out of scope** \u2014 close with `wontfix` and a one-line reason.

## 5. The single Project board

The board has six columns and a roadmap view:

* `Inbox` \u2014 untriaged issues. Goal: empty before each working session.
* `Backlog` \u2014 triaged, not yet scheduled.
* `Next` \u2014 the next 1\u20133 things you intend to do.
* `In progress` \u2014 limit one item at a time.
* `In review` \u2014 a PR is open, CI running.
* `Done` \u2014 PR merged + applied. Auto-archived weekly.

The **Roadmap view** groups by quarter using the `target` field
(`Q3-2026`, `Q4-2026`, …) and visualises the unified critique's
remediation order from
[`docs/contributions/running summary of unified contributions/unified critique/unified-critique.md` \u00a710](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md).

> Bootstrapping the Project: GitHub UI \u2192 your profile \u2192 Projects \u2192
> `New project` \u2192 `Board` template \u2192 link the `WhiteLab` repo \u2192
> rename columns to the six above. One-time setup.

## 6. The four current shower-thoughts (already captured as RFCs)

These are the four items the operator sketched on day one. Each is
filed as a pending RFC and tracked on the Project board:

| RFC                                                                       | Title                                                | Severity      | Hardware | Status  |
| ------------------------------------------------------------------------- | ---------------------------------------------------- | ------------- | -------- | ------- |
| [RFC-0001](../contributions/pending-RFCs/RFC-0001-mobile-capture-flow.md) | Mobile capture flow (no Google Keep, no Apps Script) | n/a (process) | none     | Drafted |
| [RFC-0002](../contributions/pending-RFCs/RFC-0002-n305-auto-power-on.md)  | N305 auto power-on after AC loss (BIOS)              | High          | None     | Drafted |
| [RFC-0003](../contributions/pending-RFCs/RFC-0003-fanless-ups-nut.md)     | Fanless UPS + NUT graceful shutdown choreography     | High          | UPS      | Drafted |
| [RFC-0004](../contributions/pending-RFCs/RFC-0004-notebooklm-digest.md)   | NotebookLM digest pipeline (CI-flatten the repo)     | Medium        | None     | Drafted |

## 7. CI enforcement (the "always up to date" guarantee)

> **First time here?** Read
> [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) for the noob-view tour
> with three concrete examples (BIOS update, AdGuard LXC,
> notification channel swap).

### 7.1. The three CI invariants

1. **Automation invariant.** The roadmap snapshot, the critique
   importer, the stale sweeper, the weekly digest and the
   issue→draft-PR scaffolder all keep running. A PR that disables
   any of them fails review.
2. **Security invariant.** `zero-trust-guard.yml` fails any PR that
   re-introduces SSH outside the documentation allow-list. Anchored
   in [ADR-0002](../decisions/ADR-0002-no-ssh-ever.md).
3. **Unified invariant.** Every PR must reference an issue and that
   issue must be triaged out of `status:inbox` before merge.
   Override: the `docs-skip` label.

### 7.2. The workflows that enforce them

* **[`roadmap-sync.yml`](../../.github/workflows/roadmap-sync.yml)** —
  on every issue event, on every push to `master`, daily at 06:15
  *and* 18:15 UTC, after every `critique-sync` run, and on manual
  dispatch. Regenerates [`active-roadmap.md`](active-roadmap.md) by
  pulling open and recently-closed issues from the GitHub API and
  grouping them by `status:*`, type, and priority labels. Commits
  the snapshot back to `master` with `[skip ci]`. **This is the
  "always-up-to-date roadmap" guarantee — the snapshot is at most
  one issue-event old.**

* **[`docs-up-to-date.yml`](../../.github/workflows/docs-up-to-date.yml)** \u2014
  on every PR. Fails the check (advisory, non-blocking on docs-only
  PRs) if a PR touches `infra/`, `tools/fortress-agent/`, or
  `.github/workflows/` without also touching `docs/`. Also fails if
  the PR body does not link an issue (`#NN`, `closes #NN`, or
  `refs #NN`).
* **[`notebooklm-digest.yml`](../../.github/workflows/notebooklm-digest.yml)** \u2014
  weekly schedule + manual dispatch. Runs
  [`tools/digest/digest-repo.sh`](../../tools/digest/digest-repo.sh),
  flattens every committed Markdown file plus selected `tools/`
  YAML/JSON, and uploads the resulting `whitelab-digest.txt` as a
  GitHub Actions artifact (90-day retention). Download and drop into
  NotebookLM whenever you want a fresh "backup brain".

### 7.3. PR #20 additions — the holy-grail funnel

* **[`critique-sync.yml`](../../.github/workflows/critique-sync.yml)** —
  parses every top-level finding in
  [`unified-critique.md`](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md)
  and mirrors it to a GitHub issue with a hidden HTML-comment
  anchor (idempotent). Auto-closes findings that a `docs/decisions/`
  ADR lists in its `related-critique:` front-matter block.
* **[`issue-to-pr.yml`](../../.github/workflows/issue-to-pr.yml)** —
  any issue moved to `status:in-progress` gets a draft PR opened
  automatically with a scratch marker file. Nothing rots in a
  forgotten branch.
* **[`stale-sweeper.yml`](../../.github/workflows/stale-sweeper.yml)** —
  daily; nudges issues at 14 days, labels them `stale` at 30 days,
  **never auto-closes**. `pinned`, `security`, `status:next` and
  `critique` issues are exempt.
* **[`weekly-digest-issue.yml`](../../.github/workflows/weekly-digest-issue.yml)** —
  Mondays 06:30 UTC. Maintains a single pinned digest issue with
  open-by-status counts, stale list, open critique findings, and
  recently merged PRs. Edited in place; no spam.
* **[`zero-trust-guard.yml`](../../.github/workflows/zero-trust-guard.yml)** —
  every PR. Runs [`tools/guards/no-ssh.sh`](../../tools/guards/no-ssh.sh)
  against the diff. Fails on any re-introduction of SSH outside the
  allow-list (`docs/decisions/`, `docs/learning/`,
  `docs/contributions/`, the guard itself).

## 8. The "always-up-to-date roadmap" property, formally

The roadmap is current iff each of the following holds:

1. **Capture is current.** Every `Inbox` issue is triaged at the
   start of every working session.
2. **Snapshot is current.** [`active-roadmap.md`](active-roadmap.md)
   is regenerated automatically on every issue event by
   [`roadmap-sync.yml`](../../.github/workflows/roadmap-sync.yml);
   no human is in the loop.
3. **Status is current.** The Project automation transitions the
   linked issue to `Done` when the PR closing it merges.
4. **Docs are current.** The `docs-up-to-date` workflow blocks PRs
   that change behaviour without changing documentation.
5. **NotebookLM is current.** The `notebooklm-digest` workflow
   produces a weekly artifact you re-upload to NotebookLM.

Violating any of (1)–(5) is a process failure, captured by the
unified critique on the next reflection pass and remediated as a
new RFC.

## 9. ADHD-aware practices (the sustainable defaults)

* **One open issue at a time on the board.** WIP=1 is non-negotiable.
* **30-minute slots.** When you sit down, take the top item from
  `Next`, no choosing.
* **No memory.** If you remember it, you write it. Never trust your
  next-week self to remember.
* **Mobile is first-class.** The Issue templates are designed to fit
  on a phone keyboard.
* **Months between sessions are normal.** Re-onboarding lives in
  [`docs/learning/01-zero-trust-explained.md`](../learning/01-zero-trust-explained.md)
  plus the latest NotebookLM digest. Read those two; do not
  re-explore the Proxmox UI.

## 10. Cross-references

* **Live snapshot:** [`active-roadmap.md`](active-roadmap.md) — auto-generated, always current.
* Issue templates: [`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/).
* PR template: [`.github/pull_request_template.md`](../../.github/pull_request_template.md).
* Pending RFCs: [`docs/contributions/pending-RFCs/`](../contributions/pending-RFCs/).
* Unified deep dive: [`docs/contributions/running summary of unified contributions/unified deep dive/unified-deep-dive.md`](../contributions/running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md).
* Unified critique: [`docs/contributions/running summary of unified contributions/unified critique/unified-critique.md`](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md).
* Learning guide: [`docs/learning/01-zero-trust-explained.md`](../learning/01-zero-trust-explained.md).

## 11. Bootstrap (one-time, per repo)

```bash
# Repo labels referenced by the issue templates and the roadmap-sync
# workflow. Idempotent; re-run any time you tweak labels.sh.
GH_TOKEN=$(gh auth token) REPO=ricardo-david-francisco/WhiteLab \
  bash tools/roadmap/sync-labels.sh
```

After labels exist, mobile capture works end-to-end:

1. GitHub Mobile → `+` → `New issue` → **Shower thought** template.
2. The template auto-applies `shower-thought` and `status:inbox`.
3. The `Roadmap Sync` workflow picks up the issue event and
   updates [`active-roadmap.md`](active-roadmap.md) within ~30 s.
4. At your next working session, triage the `Inbox` section,
   relabel as `bug` / `chore` / `rfc` / `infra`, optionally bump
   to `status:next` for the next 1–3 things you intend to do.
