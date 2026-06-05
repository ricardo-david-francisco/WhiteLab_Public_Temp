# WhiteLab

> **One-line summary.** WhiteLab is the Git-backed, zero-trust control
> plane for a home network: Proxmox (N95 + N305), OPNsense, Omada
> Wi-Fi, LXC containers, Tailscale, reverse proxy. Every change is a
> pull request; every apply is gated by a TOTP and an offline-signed
> audit log; no target ever exposes SSH.

## Welcome — human or AI

If you are an LLM, an automation script, or a human acting like one,
**read [AGENTS.md](AGENTS.md) first**. It is the single canonical
entrypoint for any agent that intends to write code in this repo, and
it lists the hard rules (no SSH, no auto-merge, no plaintext secrets,
always draft PRs, always `git commit -s`) along with the build/test
commands and the agent-writable / agent-forbidden file map.

If you just want to add a snippet without cloning the repo, open a
GitHub issue from the **Proposal** template, paste your snippet, and
label it `proposal:apply`. CI will turn it into a draft PR and a
human will review it. Alternatively, drop the file plus a tiny
manifest into `inbox/<slug>/` and push: see
[inbox/README.md](inbox/README.md).

This repo runs end-to-end on a fresh Ubuntu LTS VM with only `git`,
`python3`, `pyyaml`, `ruff`, `mypy`, `yamllint`, and `age`. There is
no paid subscription anywhere on the critical path; if a workflow
ever starts to depend on one, treat it as a bug.

## Start here

* **New to the project?** Read
  [docs/learning/01-zero-trust-explained.md](docs/learning/01-zero-trust-explained.md).
  Long-form, no DevOps background assumed. Covers the *why*,
  redundancy, and the defenses against IoT pivot, phishing, malicious
  dependencies, GitHub account takeover, GitHub itself being
  compromised, and physical access.
* **Need a five-minute mental model of the daily/weekly loop?** Read
  [docs/roadmap/HOW-IT-WORKS.md](docs/roadmap/HOW-IT-WORKS.md). Three
  concrete examples (BIOS update, AdGuard LXC, notification channel
  swap) show capture → triage → ship → reflect end-to-end.
* **Want the narrative end-to-end?** See
  [docs/contributions/running summary of unified contributions/unified deep dive/unified-deep-dive.md](docs/contributions/running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md)
  for a single-document end-to-end synthesis, and the
  [unified critique](docs/contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md)
  for a consolidated list of findings and remediations.
* **Adding a component (AdGuard, Immich, NAS share, …)?** Follow
  [docs/runbooks/03-add-new-component.md](docs/runbooks/03-add-new-component.md).
* **Reading live state (firewall XML, Wi-Fi events, container log)?**
  See [pull-proxmox](docs/runbooks/pull-proxmox.md),
  [pull-opnsense](docs/runbooks/pull-opnsense.md),
  [pull-omada](docs/runbooks/pull-omada.md).
* **Need the formal contract?**
  [docs/architecture/2.0-fortress-design.md](docs/architecture/2.0-fortress-design.md).

## What this repo holds

* **Source of truth.** Declarative configuration for OPNsense,
  Proxmox hosts, every LXC, the Omada controller, the Caddy reverse
  proxy, and the Tailscale ACL.
* **Anonymized only.** Every committed file is scrubbed of real IPs,
  hostnames, MACs, public keys, and domains. The map back lives in
  `vault/` (gitignored), under `age` encryption, on your workstation.
* **Audit log.** Every applied change produces a signed JSON record
  under `audit/`.

## What this repo does *not* hold

* Raw exports, real secrets, certificates, or private keys.
* Any code that opens an SSH session against a target.
* Any path that lets a merged PR alone modify the network. Apply
  always requires a fresh TOTP confirmation by the maintainer in
  person.

## Architecture in one diagram

```text
laptop ──► GitHub (PR, CI, Snyk, Trivy, OPA, review) ──► maste
                                                           │
                                                    apply:approved
                                                    label + merge
                                                           │
                                                           ▼
                                               signed HMAC webhook
                                                           │
                                                    Tailscale only
                                                           │
                                                           ▼
                                         ┌──────────────────────────┐
                                         │ CT-104  fortress-agent   │
                                         │ - TOTP unlock (you)      │
                                         │ - tmpfs API-token vault  │
                                         │ - drift / OPA / snapshot │
                                         │ - signed audit log       │
                                         └──┬───────────┬───────────┘
                                            │ HTTPS API │ HTTPS API
                                            ▼           ▼
                                       Proxmox      OPNsense / Omada
```

Full picture and per-component details:
[docs/learning/01-zero-trust-explained.md §4](docs/learning/01-zero-trust-explained.md).

## Repository layout

```text
.
├── PROJECT_HISTORY.md           # Append-only diary
├── audit/                       # Signed apply + read receipts
├── docs/
│   ├── adr/                     # Architecture decision records
│   ├── architecture/            # Formal contract (design, anonymizer, sync)
│   ├── contributions/           # Agent-assisted narrative summaries + critiques
│   ├── learning/                # Long-form educational guides ← start here
│   ├── research/                # Per-component "bibles" (designs)
│   ├── runbooks/                # apply-*, pull-*, recover, rotate, break-glass
│   └── threat-model/            # Risk register, trust zones, assumptions
├── infra/
│   ├── caddy/                   # Reverse-proxy config (Caddyfile.j2)
│   ├── lxc/                     # Per-container declarative spec
│   │   └── ct-NNN-<name>-<zone>/
│   │       ├── ct.yaml          # Proxmox-side spec (vmid, node, mounts, …)
│   │       ├── compose.yaml     # docker-compose for the workload
│   │       └── audit_NNN.sh     # health-check used by the apply path
│   ├── omada/                   # Controller settings, port profiles
│   ├── opnsense/                # Anonymized config-*.xml + diffs
│   ├── proxmox-n95/             # Host config, datacenter.cfg, fw rules
│   └── proxmox-n305/            # Host config, datacenter.cfg, fw rules
├── policies/                    # OPA bundle (no-shell, no-egress, …)
├── tools/
│   ├── anonymizer/              # Raw → review-safe sanitize
│   └── fortress-agent/          # Agent + adapters + ratchet CLI
└── vault/                       # LOCAL-ONLY raw exports. .gitignore'd. Never pushed.
```

`docs/contributions/` is **non-normative** — the IaC parser does not
read from it. It exists so that a returning maintainer (or a new
reviewer) can absorb the system in narrative form before reaching
for the formal contract.

## Branching and review

* `master` — protected. Required: signed commits, green CI (lint,
  Snyk, Trivy, OPA, anonymization-gate), one review, fast-forward
  only.
* `feature/*`, `infra/*`, `docs/*` — one topic per branch.
* Every merge updates `PROJECT_HISTORY.md`.

## Apply workflow (TL;DR)

```text
git checkout -b infra/<thing>
$EDITOR <file>
git commit -s -m "infra(<scope>): ..."
gh pr create --base maste
# review, CI green, merge, label apply:approved
ratchet apply --pr <N> --totp <code>
```

Full walkthrough:
[docs/learning/01-zero-trust-explained.md §6](docs/learning/01-zero-trust-explained.md).

## Read workflow (TL;DR)

```text
ratchet pull opnsense config --review            # firewall XML, anonymized
ratchet pull omada events --since 24h            # Wi-Fi event log
ratchet pull omada clients --rssi-below -75      # find weak signals
ratchet pull proxmox cts --node n305             # CT inventory
ratchet pull proxmox ct 105 --log --tail 200     # container log
```

Each command has its own runbook:
[pull-opnsense](docs/runbooks/pull-opnsense.md),
[pull-omada](docs/runbooks/pull-omada.md),
[pull-proxmox](docs/runbooks/pull-proxmox.md).

## Capture, roadmap, and contributions

The roadmap is GitHub Issues + GitHub Projects. There is no second
system of record.

* Capture an idea on the phone in two taps via the **Showe
  thought** issue template
  ([`.github/ISSUE_TEMPLATE/shower-thought.yml`](.github/ISSUE_TEMPLATE/shower-thought.yml)).
* The full capture / triage / RFC / done lifecycle:
  [docs/roadmap/README.md](docs/roadmap/README.md).
* Pending design proposals (waiting to be promoted into the formal
  architecture docs):
  [docs/contributions/pending-RFCs/](docs/contributions/pending-RFCs/).
* NotebookLM source transcripts and unified prose summaries:
  [docs/contributions/notebooklm/](docs/contributions/notebooklm/) and
  [docs/contributions/running summary of unified contributions/](docs/contributions/running%20summary%20of%20unified%20contributions/).
* Two CI workflows enforce freshness:
  [`docs-up-to-date`](.github/workflows/docs-up-to-date.yml) blocks
  PRs that change behaviour without updating docs;
  [`notebooklm-digest`](.github/workflows/notebooklm-digest.yml)
  publishes a weekly flat-text artifact for upload into NotebookLM.

## Security posture

Threat model and per-attacker controls:
[docs/threat-model/](docs/threat-model/) (formal) and
[docs/learning/01-zero-trust-explained.md §§3, 10–12](docs/learning/01-zero-trust-explained.md)
(narrative).

Short version:

* GitHub is treated as **hostile-curious**. Compromise of the GitHub
  side cannot ship a change to the network — TOTP is required at the
  agent and lives only on a separate device.
* The home LAN is treated as **partially hostile**. IoT cannot reach
  LAN; LAN cannot reach the agent; only the tailnet operator tag can.
* No SSH on any target, ever. Every action goes through a per-target
  HTTPS adapter with a scoped, named, time-limited token.

## Status

Bootstrapping. The agent and adapters are scaffolded; per-target
runbooks (`apply-*`, `pull-*`) are landing one PR at a time. Track
the roadmap in
[docs/architecture/2.0-fortress-design.md §14](docs/architecture/2.0-fortress-design.md).
