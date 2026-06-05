# AGENTS.md — read this first

You are reading this because you are about to write or change code in
the WhiteLab repository. You may be a human, an LLM, an automation
script, or some combination of the three. The rules below apply to
all of you equally.

This file is the **single canonical entrypoint** for any agent (or
human acting like one). Everything else — `README.md`,
`docs/architecture/`, `docs/roadmap/HOW-IT-WORKS.md` — is allowed to
disagree with itself. AGENTS.md is the tiebreaker.

## Hard rules (non-negotiable)

1. **Never SSH into a host.** Not as a user, not as a script, not as
   a "just this once". If a workflow or local helper looks like it is
   about to open an SSH session, refuse the change. The repo enforces
   this with `tools/guards/no-ssh.sh` and the `ci-no-ssh` make target.
2. **Never auto-merge.** All proposed changes land as **draft** PRs.
   The repo contains zero `gh pr merge --auto` calls. Do not add one.
3. **Never commit a plaintext secret.** Run the anonymiser before
   every commit. The pre-commit hook and `verify-anonymization.py`
   enforce this; if either fails, fix the snippet rather than
   bypassing the gate.
4. **Always sign your commits with DCO.** `git commit -s`. Workflows
   that author commits already do this.
5. **Always run `make ci` locally before opening a PR.** It mirrors
   the GitHub Actions checks bit-for-bit (lint → types → tests →
   anon-verify → no-ssh-guard).

## Build / test commands

```bash
# One-shot, mirrors CI exactly:
make ci

# Sub-targets (run individually while iterating):
make ci-lint        # ruff
make ci-types       # mypy on tools/anonymizer (tools/notify, tools/proposals best-effort)
make ci-tests       # pytest tests/ tools/anonymizer/tests/
make ci-yaml        # yamllint
make ci-anon-verify # python -m tools.anonymizer.anonymize --verify infra/
make ci-no-ssh      # tools/guards/no-ssh.sh

# Build the NotebookLM single-paste bundle:
make bundle  # → dist/whitelab-bundle.md
```

The repo has no paid-subscription dependencies. Everything above runs
on a fresh Ubuntu LTS VM with `git`, `python3`, `pyyaml`, `ruff`,
`mypy`, `yamllint`, and (for the encrypted anonymiser map) `age` /
`age-keygen`. There is no Copilot dependency, no Claude dependency,
and no GitHub-hosted dependency beyond the public APIs that
`gh` already uses.

## File map

The proposal funnel and the pre-commit hooks both share the same
allow-list / deny-list. Any agent that respects this list will never
trip a guard.

### Agent-writable

- `docs/`
- `infra/`
- `tools/` *except* the forbidden subtrees below
- `tests/`
- `inbox/`
- `README.md`, `AGENTS.md`, `CONTRIBUTING.md`

### Agent-forbidden (security envelope)

- `.github/workflows/` — CI must not be able to rewrite itself
- `.github/CODEOWNERS`
- `tools/guards/` — zero-trust guards (no-SSH, etc.)
- `tools/proposals/` — the proposal engine itself
- `tools/anonymizer/` — the anonymiser
- `policy/` — OPA / admission policies
- `vault/` — encrypted secrets (incl. `vault/anonmap.age`)
- `audit/` — signed audit log
- `.pre-commit-config.yaml`

If you need to change anything in those paths, open a regular PR by
hand. The funnel will not do it for you, by design.

## The canonical funnel

There are **exactly two** automated ways for a snippet to become a
draft PR:

1. **Issue body.** Open an issue from the *Proposal* template, paste
   `target: <path>` lines followed by fenced code blocks, and label
   it `proposal:apply`. The `proposal-apply.yml` workflow will open a
   draft PR linked to the issue.
2. **Inbox folder.** Push an `inbox/<slug>/manifest.yml` (plus the
   files it points at) to `master`. The same workflow turns the slug
   into a draft PR and removes the inbox folder.

Both channels share `tools/proposals/apply.py` and therefore share
the same allow-list and the same anonymiser refusal check. Both
channels always produce a **draft** PR.

## Anonymiser quick reference

- Local lookup: `python -m tools.anonymizer.anonymize --verify infra/`
- Round-trip: `python -m tools.anonymizer.anonymize <files...>` to
  redact, `python -m tools.anonymizer.rehydrate <files...> --map-file
  vault/anonmap.age` to restore.
- Key resolution order for the encrypted map:
  1. `--key-file` argument
  2. `$WHITELAB_ANONMAP_KEY`
  3. `vault/anonmap.key` (gitignored)
- Generate a fresh key: `age-keygen -o vault/anonmap.key`. Keep the
  key out of git; only the encrypted `vault/anonmap.age` is
  committed.

## Pointer files (deferred)

We deliberately do **not** ship `.cursorrules`, `.claude/rules.md`,
`.gemini/instructions.md`, etc. AGENTS.md is the single source of
truth. If you are running an agent framework that needs a
framework-specific entrypoint, point it at this file.

## When in doubt

Open an issue with the `proposal:apply` label, paste the snippet, let
the funnel produce a draft PR, and let a human merge it. That is the
worst-case path; everything else is an optimisation on top.
