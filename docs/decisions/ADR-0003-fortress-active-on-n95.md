---
id: ADR-0003
status: Accepted
date: 2026-05-06
supersedes: []
related-issues: []
related-critique:
  - "#8-resilience-single-instance-fortress-agent"
tags: [resilience, fortress, n95, n305]
---

# ADR-0003 — Fortress agent stays on the N95; cold standby on the N305

## Context

The unified critique §8 flags the fortress agent (LXC 104 on the N95)
as a single point of failure. The recommended remediation is a *cold*
(powered-off) standby clone of the fortress LXC, kept on the N305 host
as a Proxmox template, activatable in five minutes through a documented
console procedure.

A reasonable counter-proposal is to move the *active* fortress to the
N305 instead — putting the keys closer to the firewall and on the
beefier silicon. This ADR records why we do not.

## Decision

The active fortress agent **remains on the N95**. The N305 hosts the
**cold standby** template. Concretely:

* The active LXC 104 keeps its current home on the N95.
* A new resource — `LXC 104-standby`, a Proxmox template — lives on
  the N305. It is created by the apply pipeline on every fortress
  release, so it cannot rot.
* Activation is a documented one-line `pct clone … && pct start …`
  on the N305 console plus the operator-supplied decryption material.

The split mirrors the **steering wheel / muscle** asymmetry in the
deep dive §6: the N305 is a network-perimeter device whose only job
is firewall and routing. Co-locating the fortress on the N305 would
multiply that node's blast radius — a single hardware fault would
take down the firewall *and* the executor of changes that could
recover from it. Keeping them on separate hosts is the same logic
that puts your spare house key with a neighbour, not on the front
porch.

## Consequences

* Critique §8 finding is **Adopted (in full)**: cold standby on
  N305 lands as proposed.
* The active fortress workload pattern (one LXC, no replicas) is
  preserved; we explicitly accept the singleton property because
  two simultaneous active agents would race on the apply lock and
  the TOTP seed.
* The N305's role remains "firewall host plus standby template
  host" — no active workloads beyond the OPNsense VM and the
  rebuild target.
* Critique §9 (`--laptop-agent` mode) covers the further tail-risk
  where N95 *and* N305 are simultaneously dead; that mode is
  unaffected by this ADR and remains the deeper recovery layer.

## Alternatives considered

* **Move active fortress to N305.** Rejected: concentrates
  blast radius on the WAN-facing node; tightens hardware coupling.
* **Active/active fortress on both hosts.** Rejected: race on the
  apply lock and TOTP seed; the singleton property of the agent is
  load-bearing for the audit chain.
* **Skip the cold standby entirely; rely on rebuild from vault.**
  Rejected: rebuild is hours of work in a known-difficult sequence,
  and the recovery drill is least pleasant exactly when it is most
  needed.

## References

* Unified critique §8:
  [Resilience: Single-Instance Fortress Agent](../contributions/running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md#8-resilience-single-instance-fortress-agent).
* Deep dive §6:
  [Architectural Pattern: Steering Wheel and Muscle](../contributions/running%20summary%20of%20unified%20contributions/unified%20deep%20dive/unified-deep-dive.md#6-architectural-pattern-steering-wheel-and-muscle).
