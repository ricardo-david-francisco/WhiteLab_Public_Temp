# RFC-0001 — Mobile capture flow (no Google Keep, no Apps Script)

* **Status**        : Draft
* **Author**        : @ricardo-david-francisco
* **Created**       : 2026-05-06
* **Last updated**  : 2026-05-06
* **Tracking issue**: TBD
* **Severity**      : n/a (process / tooling)
* **Hardware**      : none

## 1. Problem

The operator has limited time and an ADHD-shaped attention budget.
Ideas, defects, and design notes appear at random moments —
typically away from the lab, often without a laptop. Without an
ultra-low-friction capture surface those thoughts are lost, and the
roadmap stops reflecting reality.

Earlier prototypes considered Google Keep with an Apps Script bridge
into the repository. That approach is rejected because it:

* introduces a non-GitHub system of record;
* requires custom OAuth/Apps-Script plumbing the operator has to
  maintain alongside the lab;
* creates a second place to look for "what did I write down";
* depends on a paid Google Workspace tier for governance features.

## 2. Background

The repository is already the single source of truth for code,
configuration, and documentation. The unified deep-dive identifies
documentation drift as the dominant failure mode (`INC-NADD-DRIFT-01`).
Adding a sidecar tool would re-create the very drift the lab is
designed to eliminate.

GitHub Issues, GitHub Projects v2, and the GitHub Mobile app are
free on private repositories and provide:

* native push notifications, biometrics, and 2FA;
* fully-fledged labels, assignees, and templates;
* automation rules into a Project board;
* identical surface across phone, tablet, and desktop.

## 3. Proposal

Standardise the capture surface as **GitHub Mobile + Issue
templates**:

1. Install GitHub Mobile, sign in with hardware-backed 2FA.
2. Ship three issue forms in `.github/ISSUE_TEMPLATE/`:
   * `shower-thought.yml` — single-textarea form, auto-labels
     `shower-thought`, `triage`.
   * `bug-or-incident.yml` — incident form with severity dropdown.
   * `rfc.yml` — design proposal placeholder.
3. Ship a Project (v2) with the columns described in
   [`docs/roadmap/README.md` §5](../../roadmap/README.md), and an
   automation rule "When an issue is opened, add to project".
4. The triage rule is in [`docs/roadmap/README.md` §4](../../roadmap/README.md):
   every working session begins by emptying the `Inbox` column.

## 4. Alternatives considered

* **Google Keep + Apps Script bridge.** Rejected — second source of
  truth, non-trivial to maintain, requires Workspace governance.
* **Plain text file synced via Tailscale Drive.** Rejected — no
  notifications, no triage primitive, easy to forget.
* **Self-hosted Trilium/Obsidian with mobile sync.** Rejected —
  added moving parts, extra LXC, extra credentials, no integration
  with the PR pipeline.
* **Email-to-issue gateway.** Rejected — adds an SMTP attack
  surface to a Zero Trust lab.

## 5. Risks

* **Phone loss.** Mitigated by 2FA + remote sign-out from
  github.com → Settings → Sessions.
* **GitHub outage.** Mitigated by capturing in the phone's notes
  app as a tactical fallback; the operator transcribes after
  recovery. This happens rarely enough not to justify a permanent
  second tool.
* **Mobile typing fatigue.** Mitigated by the single-textarea
  template — one bullet, ship it; details captured during triage.

## 6. Acceptance criteria

1. The three issue templates exist under `.github/ISSUE_TEMPLATE/`
   and render correctly when opening an issue from GitHub Mobile.
2. `.github/ISSUE_TEMPLATE/config.yml` disables blank issues.
3. A Project (v2) exists, linked to the repository, with the six
   columns from `docs/roadmap/README.md` §5.
4. Project automation moves new issues to `Inbox`.
5. `docs/roadmap/README.md` is the only documentation describing
   the capture flow.

## 7. Rollout plan

* Day 0 — merge the templates and the roadmap doc.
* Day 0 — bootstrap the Project (manual GitHub UI step, ~5 min).
* Day 0 — install GitHub Mobile on the operator's phone, test by
  filing one shower-thought issue.
* Week 1 — backfill the four current shower-thoughts as issues
  linked to RFC-0001..0004.

## 8. References

* [`docs/roadmap/README.md`](../../roadmap/README.md)
* [`.github/ISSUE_TEMPLATE/`](../../../.github/ISSUE_TEMPLATE/)
* GitHub Docs — Issue forms (free for private repos).
