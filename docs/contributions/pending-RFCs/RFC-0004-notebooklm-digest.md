# RFC-0004 — NotebookLM digest pipeline

* **Status**        : Draft
* **Author**        : @ricardo-david-francisco
* **Created**       : 2026-05-06
* **Last updated**  : 2026-05-06
* **Tracking issue**: TBD
* **Severity**      : Medium (knowledge continuity)
* **Hardware**      : none

## 1. Problem

Months pass between working sessions. Re-onboarding into the lab
through Proxmox UI clicks is a time sink that immediately invites
documentation drift. The operator already uses **NotebookLM** as
an external "backup brain": feeding it the entire repository
produces excellent deep-dives and critiques (see
[`docs/contributions/notebooklm/`](../notebooklm/)).

The current digest tool — `.digest.sh` at the repo root — flattens
files from a **local research vault** outside the repository
(`~/.cache/whitelab-research/Home_Infra/`). That makes it:

* unrunnable in CI (vault is not committed);
* unable to capture *committed* documentation, which is the actual
  source of truth;
* dependent on a single workstation.

We need a CI-driven digest that flattens the **public, committed**
content of this repository on a schedule, and stores the result
where the operator can grab it from any phone.

## 2. Background

NotebookLM accepts plain-text and Markdown uploads up to a
generous size limit. A flat concatenation of `docs/`, the top-level
`README.md`, selected `tools/` configs, and the unified critique +
deep-dive is the right input for it.

GitHub Actions provides:

* `schedule:` triggers (cron);
* `workflow_dispatch:` for manual runs (callable from GitHub Mobile);
* `actions/upload-artifact@v4` with `retention-days` up to 90 on
  free tier — well beyond the operator's typical session gap.

## 3. Proposal

Add two artefacts to the repository:

1. **`tools/digest/digest-repo.sh`** — a self-contained,
   POSIX-shell flattener that:
   * walks every committed `*.md` under the repo root;
   * walks `tools/fortress-agent/**/*.{yml,yaml,json}` (sanitised
     by the existing anonymisation gate);
   * concatenates each file with a header banner (`==== FILE: <path>
     ====`) and a trailing newline;
   * writes to `dist/whitelab-digest.txt`;
   * prints `wc -l` and `wc -c` summaries to stdout.
2. **`.github/workflows/notebooklm-digest.yml`** — a workflow that:
   * runs on `schedule: '0 6 * * 1'` (Monday 06:00 UTC);
   * also runs on `workflow_dispatch:`;
   * checks out the repository;
   * executes the script;
   * uploads `dist/whitelab-digest.txt` as a 90-day artifact named
     `whitelab-digest-${{ github.run_number }}`.

The legacy `.digest.sh` (vault-aware, local-only) stays in place
for the operator's offline workflow but is renamed in a follow-up
PR to `.local/digest-vault.sh` to remove ambiguity. That rename is
not part of this RFC's scope.

## 4. Alternatives considered

* **Generate digest on every commit.** Rejected — inflates Actions
  minutes for low marginal value; weekly is fine for a slow-moving
  knowledge corpus.
* **Commit `dist/whitelab-digest.txt` into the repo.** Rejected —
  binary-ish blob, churn in diffs, anonymisation surface enlargement.
* **Push the digest to S3 / R2.** Rejected — adds a paid service
  and a credential. Free Actions artifacts solve the problem.
* **Use a third-party "RAG-as-a-service".** Rejected — privacy and
  cost.

## 5. Risks

* **Anonymisation regression.** Mitigated — the digest only reads
  files that are already committed and have therefore already
  passed the anonymisation gate (`.github/workflows/anonymization-gate.yml`).
* **Artifact size.** Current corpus ≈ 200 KB after flattening;
  well under the 500 MB free-tier per-artifact ceiling.
* **Cron drift on free tier.** GitHub may delay scheduled runs
  during off-peak. Mitigated by `workflow_dispatch:` — the
  operator can trigger manually from GitHub Mobile.

## 6. Acceptance criteria

1. `tools/digest/digest-repo.sh` runs on a clean clone and
   produces `dist/whitelab-digest.txt`.
2. The flattened output contains a header banner per source file.
3. `.github/workflows/notebooklm-digest.yml` exists and lints
   clean against `yamllint` with the project's `.yamllint`.
4. A manual `workflow_dispatch:` run uploads the artifact and the
   operator can download it from the Actions tab on mobile.
5. `docs/roadmap/README.md` §7 references this workflow.

## 7. Rollout plan

* Land the script + workflow in the same PR as RFC-0001.
* Trigger one manual run; download the artifact; upload it into
  NotebookLM as a baseline.
* Let the weekly schedule take over.

## 8. References

* [`docs/contributions/notebooklm/`](../notebooklm/)
* [`docs/contributions/running summary of unified contributions/unified deep dive/unified-deep-dive.md`](../running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md)
* GitHub Docs — Storing workflow artifacts.
