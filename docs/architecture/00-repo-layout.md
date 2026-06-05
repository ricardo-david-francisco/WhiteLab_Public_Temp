# 00 — Repository Layout

Status: **Proposed**. Discussed on branch `feature/architecture-plan`.

## Goals

1. Make the repo safe to host on GitHub even under partial compromise.
2. Separate **raw** (sensitive, local-only) from **sanitized** (committed) so
   accidents are mechanically impossible, not just procedurally discouraged.
3. One canonical place per device: easy to diff over time.
4. Encourage small, reviewable PRs whose only "merge artifact" on `master`
   is an entry in `PROJECT_HISTORY.md`.

## Top-level directories

| Path                  | Purpose                                                                 | Committed? |
| --------------------- | ----------------------------------------------------------------------- | ---------- |
| `PROJECT_HISTORY.md`  | Append-only diary; one entry per merge.                                 | Yes        |
| `README.md`           | Orientation.                                                            | Yes        |
| `SECURITY.md`         | Normative handling rules. Read-before-commit.                           | Yes        |
| `.gitignore`          | Hard barrier against committing raw material.                           | Yes        |
| `.gitattributes`      | Deterministic line endings, binary attrs.                               | Yes        |
| `docs/`               | Architecture, runbooks, threat model, contributions (narrative).        | Yes        |
| `infra/<device>/`     | Sanitized exports + per-device notes.                                   | Yes        |
| `tools/anonymize/`    | Deterministic sanitization pipeline (Python).                           | Yes        |
| `tools/sync/`         | Helpers for the SSH-less pull/push flow.                                | Yes        |
| `vault/`              | **Local-only** raw exports, key material, secrets maps.                 | **No**     |

## Per-device folder convention

For every managed device, e.g. `infra/opnsense/`:

```text
infra/opnsense/
├── README.md                 # What lives here, how to refresh, last-pulled date
├── exports/
│   ├── config-2026-05-04.sanitized.xml
│   └── ...                   # Append-only timeline of sanitized snapshots
├── policy/
│   ├── vlan-matrix.md        # Source-of-truth VLAN policy summary
│   └── firewall-rules.md     # Reviewed rule changes (human-readable)
└── changes/
    └── 2026-05-04-<topic>.md # Proposed change + rollback plan
```

Rationale:

- **`exports/`** holds machine-generated snapshots. Diffs across snapshots
  are the audit trail.
- **`policy/`** holds human intent. When intent and exports diverge, the
  reviewer notices in PR.
- **`changes/`** is where proposals are written before they are applied to
  the device, including rollback steps.

## `docs/` subfolders

| Path                  | Purpose                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `docs/adr/`           | Architecture Decision Records — one short, immutable note per choice.                                                 |
| `docs/architecture/`  | Normative design notes (this folder).                                                                                 |
| `docs/learning/`      | Long-form educational guides (no DevOps background assumed).                                                          |
| `docs/research/`      | Reference / inference material; the Infrastructure Bible lives here.                                                  |
| `docs/runbooks/`      | Step-by-step operational procedures.                                                                                  |
| `docs/threat-model/`  | Risk register, trust zones, T1–T6 levels.                                                                             |
| `docs/contributions/` | Agent-assisted narrative summaries and critiques. Explanatory, not normative. The IaC parser does not read from here. |

## What the `vault/` looks like (local-only, never pushed)

```text
vault/
├── raw/
│   ├── opnsense/config-2026-05-04.raw.xml
│   ├── proxmox-n305/...
│   ├── proxmox-n95/...
│   └── omada/...
├── secrets-map.yaml          # name -> placeholder mapping for the anonymizer
└── keys/                     # GPG/age keys used to encrypt the vault at rest
```

`secrets-map.yaml` is the deterministic input to the anonymizer so the same
real value always becomes the same placeholder across snapshots — that keeps
diffs meaningful.

## Branching and merge protocol

- `master`: protected, append-only.
- Work happens on `feature/<topic>` branches.
- A PR merges only after:
  1. `git diff` reviewed for any sensitive leak.
  2. `tools/anonymize/verify.py` passes (to be implemented).
  3. The branch updates `PROJECT_HISTORY.md` with an entry summarizing the change.
- Squash-merge or fast-forward; no merge commits with secret-bearing parents.
