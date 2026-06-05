---
id: ADR-0002
status: Accepted
date: 2026-05-06
supersedes: []
related-issues: []
related-critique:
  - "#3-hardening-inconsistency-ssh-surface-across-nodes"
tags: [security, zero-trust, ssh]
---

# ADR-0002 — SSH is permanently disabled on every WhiteLab-managed host

## Context

The unified critique §3 records that SSH was masked on the N95 but
left reachable on the N305, and prescribes uniform IaC-driven masking
of `ssh.socket` *and* `ssh.service` on every host. The deeper
question is whether SSH should ever exist at all on this fleet.

The architecture's deep-dive §9 already argues no: SSH is an
always-on attack surface, grants coarse-grained authority (a shell
is "do anything"), and is hard to credential-rotate. Every replacement
exists: the fortress agent uses HTTPS APIs with named/scoped/time-bound
tokens; the physical Proxmox console plus Tailscale-reachable web GUI
covers the break-glass path.

## Decision

**SSH is permanently disabled on every host the fortress agent
manages, and CI mechanically rejects any change that would
re-introduce it.** The decision applies to:

* OPNsense (N305 VM and any successor),
* Proxmox VE (N305 host, N95 host, any future hypervisor),
* every LXC container provisioned through the apply pipeline,
* every Omada-managed device that exposes an SSH service.

The enforcement primitives are:

1. An **idempotent IaC module** (Bash) that on every apply runs
   `systemctl stop|disable|mask` for both `ssh.socket` and
   `ssh.service`. Specified in critique §3.4; the module itself ships
   in a follow-up RFC.
2. A **CI grep guard** (`tools/guards/no-ssh.sh`) that fails any PR
   adding lines containing `Port 22`, `sshd_config`, `ssh-rsa` keys,
   `systemctl enable ssh`, or equivalent strings — outside an
   explicit allow-list (`docs/decisions/`, `docs/learning/`,
   `docs/contributions/`, `tools/guards/no-ssh.sh` itself, the
   architecture deep-dive narrative).
3. An **OPA Rego policy** (`policy/zero_trust.rego`) that fails any
   declarative manifest declaring an inbound listener on port 22 or
   enabling `ssh.service`.

Break-glass does **not** re-enable SSH. The escape paths are the
physical console (HDMI + keyboard), the Proxmox web GUI reachable
over Tailscale, and `ratchet --laptop-agent` mode (critique §9).

## Consequences

* Critique §3 finding is **Adopted (in full)** — the disposition
  goes further than the finding asked for: not "harden uniformly"
  but "remove permanently".
* Any operator instinct to "just SSH in to look around" is blocked
  by CI before it ships. This is intentional. The cost of remembering
  the right web-GUI URL is lower than the cost of debugging an
  unattributed sshd intrusion.
* When a third-party appliance is added that ships SSH-only, this
  ADR forces an explicit ADR superseding it before that appliance
  can be merged. The grep guard cannot be bypassed without an
  ADR-acknowledged exception.
* Critique §5 break-glass workflow remains the documented manual
  recovery path — no SSH involved.

## Alternatives considered

* **Harden but keep SSH available behind WireGuard.** Rejected: a
  reachable sshd is a reachable sshd; "behind a VPN" is necessary
  but not sufficient (defence-in-depth must compose).
* **Allow SSH only on the management VLAN.** Rejected: the VLAN is
  protected by firewall rules that themselves can drift; we do not
  let "VLAN reachability" stand in for authentication anywhere
  else, and we will not start here.

## References

* Unified critique §3:
  [Hardening Inconsistency: SSH Surface Across Nodes](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md#3-hardening-inconsistency-ssh-surface-across-nodes).
* Deep dive §9:
  [Deprecation of SSH](../contributions/running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md#9-deprecation-of-ssh).
* Guard implementation: `tools/guards/no-ssh.sh`.
* OPA policy: `policy/zero_trust.rego`.
