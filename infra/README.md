# `infra/` — declarative infrastructure (anonymized)

This tree holds the **desired state** of every target managed by
WhiteLab. Every file here is either:

1. An **anonymized export** (`*/exports/`) — the result of a `pull`
   operation by the Fortress Agent, with all secrets replaced by
   placeholders from `tools/anonymizer/rules.yaml`.
2. A **delta** (`*/deltas/`) — a Jinja fragment authored by a human (or
   Copilot) that, when applied to the export, produces the *next*
   desired state.
3. A **policy** (`policies/`) — Open Policy Agent (OPA) rules that
   forbid undesirable shapes (plaintext secrets, missing 2FA, world-open
   firewall rules, etc.).

> **Hard rule.** No file under `infra/` may contain a real secret, real
> MAC, real public IP, real internal hostname or real tailnet name. The
> pre-commit hook and the `anonymization-gate` CI job enforce this.

## Subtrees

* [`opnsense/`](opnsense/) — OPNsense `config.xml`, deltas, schemas.
* [`proxmox/n95/`](proxmox/n95/) and [`proxmox/n305/`](proxmox/n305/) —
  per-host configuration and Ansible roles.
* [`lxc/`](lxc/) — golden image recipes and per-CT declarative specs.
* [`omada/`](omada/) — Omada controller exports + deltas.
* [`caddy/`](caddy/) — reverse-proxy configuration.
* [`policies/`](policies/) — OPA `.rego` policy bundles.

See [`docs/architecture/2.0-fortress-design.md`](../docs/architecture/2.0-fortress-design.md)
for the full contract.
