# WhiteLab — Unified Critique

**Version:** 1.0
**Date:** 2026-05-06
**Scope:** Operational, observability, recovery, and documentation-hygiene
findings against the WhiteLab architecture as it stands today, with concrete
remediations for each.
**Sources:** Architecture Bible, NADD, fortress-agent specification, the
unified deep dive ([../unified deep dive/unified-deep-dive.md](../unified%20deep%20dive/unified-deep-dive.md)),
and the NotebookLM critique transcripts in [../../notebooklm/Critique/](../../notebooklm/Critique/).
**Audience:** The repository owner planning the next iteration of the lab,
plus anyone preparing or reviewing the corresponding RFC PRs.

---

## Quick read — jump to the finding you need

If you are not going to read the whole document, read these bullets. Each
links to the section that discusses that finding in depth and proposes a
fix.

* [TOTP-gate friction — the operator will bypass an unergonomic gate](#2-operational-friction-at-the-totp-gate). Remediation: Telegram-mediated approval (RFC pending).
* [SSH still reachable on N305 — worst hardening gap in the architecture](#3-hardening-inconsistency-ssh-surface-across-nodes). Remediation: idempotent IaC mask of `ssh.socket` *and* `ssh.service`. Tracked as [RFC follow-up to RFC-0002](../../pending-RFCs/).
* [Observability gap — no metrics or logs stack today](#4-observability-gap). Remediation: Prometheus + Grafana + Loki + Promtail in `LXC 103`, declared as code.
* [No codified break-glass for emergency hotfixes](#5-disaster-recovery-no-codified-break-glass). Remediation: `ratchet emergency-apply` + `ratchet sync-drift` (RFC pending).
* [Desired state and roadmap mixed in the same docs](#6-documentation-hygiene-desired-state-vs-roadmap). Remediation already shipped: `docs/contributions/pending-RFCs/` is the parser-invisible roadmap zone (see `docs/roadmap/README.md`).
* [AdGuard DMZ subnet collision with `20 SECURE`](#7-ip-plan-adguard-dmz-subnet-collision). Remediation: move DMZ to `192.168.25.0/24`.
* [Single-instance fortress agent — no recovery on disk corruption](#8-resilience-single-instance-fortress-agent). Remediation: cold-standby fortress LXC on N305.
* [Total cluster loss — N95 and N305 simultaneously dead](#9-total-cluster-loss-laptop-as-agent-mode). Remediation: `ratchet --laptop-agent` jump-start mode.
* [Prioritised remediation roadmap (the table you actually want)](#10-prioritized-remediation-roadmap).

> **The centralised capture / roadmap / CI system is already live on
> `master`.** Every finding above is tracked as a GitHub Issue (mobile
> capture via the `Shower thought` issue form) and on the GitHub Project
> board described in [`docs/roadmap/README.md`](../../../roadmap/README.md).
> Pending design proposals are in
> [`docs/contributions/pending-RFCs/`](../../pending-RFCs/) and the
> `docs-up-to-date` workflow blocks PRs that change behaviour without
> updating documentation.

## Table of contents

1. [Executive Summary](#1-executive-summary)
2. [Operational Friction at the TOTP Gate](#2-operational-friction-at-the-totp-gate)
    1. [Finding](#21-finding)
    2. [Severity](#22-severity)
    3. [Remediation — Telegram-mediated approval](#23-remediation--telegram-mediated-approval)
    4. [What does and does not change](#24-what-does-and-does-not-change)
    5. [Why this is not an air-gap violation](#25-why-this-is-not-an-air-gap-violation)
    6. [Acceptance criteria](#26-acceptance-criteria)
3. [Hardening Inconsistency: SSH Surface Across Nodes](#3-hardening-inconsistency-ssh-surface-across-nodes)
    1. [Finding](#31-finding)
    2. [Severity](#32-severity)
    3. [The systemd subtlety](#33-the-systemd-subtlety)
    4. [Remediation — IaC enforcement, not memory](#34-remediation--iac-enforcement-not-memory)
    5. [Concern: am I removing my last fallback?](#35-concern-am-i-removing-my-last-fallback)
    6. [Acceptance criteria](#36-acceptance-criteria)
4. [Observability Gap](#4-observability-gap)
    1. [Finding](#41-finding)
    2. [Severity](#42-severity)
    3. [Remediation — Prometheus + Grafana + Loki, declared not built](#43-remediation--prometheus--grafana--loki-declared-not-built)
    4. [Required firewall rules](#44-required-firewall-rules)
    5. [Validation against AI-emitted XML](#45-validation-against-ai-emitted-xml)
    6. [Acceptance criteria](#46-acceptance-criteria)
5. [Disaster Recovery: No Codified Break-Glass](#5-disaster-recovery-no-codified-break-glass)
    1. [Finding](#51-finding)
    2. [Severity](#52-severity)
    3. [Remediation — two-part break-glass](#53-remediation--two-part-break-glass)
    4. [Acceptance criteria](#54-acceptance-criteria)
6. [Documentation Hygiene: Desired State vs Roadmap](#6-documentation-hygiene-desired-state-vs-roadmap)
    1. [Finding](#61-finding)
    2. [Severity](#62-severity)
    3. [Remediation — split-brain documentation](#63-remediation--split-brain-documentation)
    4. [Acceptance criteria](#64-acceptance-criteria)
7. [IP Plan: AdGuard DMZ Subnet Collision](#7-ip-plan-adguard-dmz-subnet-collision)
    1. [Finding](#71-finding)
    2. [Severity](#72-severity)
    3. [Remediation — declare and apply](#73-remediation--declare-and-apply)
    4. [Acceptance criteria](#74-acceptance-criteria)
8. [Resilience: Single-Instance Fortress Agent](#8-resilience-single-instance-fortress-agent)
    1. [Finding](#81-finding)
    2. [Severity](#82-severity)
    3. [Remediation — cold standby on N305](#83-remediation--cold-standby-on-n305)
    4. [Acceptance criteria](#84-acceptance-criteria)
9. [Total Cluster Loss: Laptop-as-Agent Mode](#9-total-cluster-loss-laptop-as-agent-mode)
    1. [Finding](#91-finding)
    2. [Severity](#92-severity)
    3. [Remediation — `ratchet --laptop-agent`](#93-remediation--ratchet---laptop-agent)
    4. [Acceptance criteria](#94-acceptance-criteria)
10. [Prioritized Remediation Roadmap](#10-prioritized-remediation-roadmap)
11. [Cross-references](#11-cross-references)

---

## 1. Executive Summary

The WhiteLab security model is rigorous and the cryptography is sound. The
findings below are not failures of the model; they are gaps between *the
model as designed* and *the model as a single overworked human can sustain
on a Tuesday morning*. They cluster into seven themes:

1. **Approval friction.** The TOTP gate is correct in principle and
   ergonomically punishing in practice — likely to be circumvented under
   load.
2. **Hardening inconsistency.** SSH is masked on the N95 management node
   but still reachable on the N305 firewall host. The strictest node in
   the architecture is currently the weakest in practice.
3. **Observability gap.** Diagnosing network problems requires
   command-line spelunking that the operator will not remember at 03:00.
4. **No emergency hot-fix protocol.** The current pipeline assumes the
   internet, GitHub, and the fortress agent are all alive. When any one
   of them isn't, the operator is forced into undocumented manual
   changes — exactly the failure mode WhiteLab was built to prevent.
5. **Mixed desired-state and roadmap.** The architecture document
   intermingles "what the network is" with "what the network should
   become". A declarative parser cannot distinguish the two; it will
   try to apply the future.
6. **Active subnet collision.** The AdGuard DMZ is documented as
   `192.168.20.0/24`, which is already the secure VLAN. East-west
   isolation cannot be enforced over an overlap.
7. **Single-instance fortress agent.** Correct from a cryptographic
   standpoint; catastrophic if its host disk corrupts during a power
   event.

Each finding is detailed below with severity, mechanism, fix, and
acceptance criteria. A consolidated remediation roadmap is in §10.

---

## 2. Operational Friction at the TOTP Gate

### 2.1 Finding

The Gate-6 TOTP requirement (see deep dive §10) is enforced through a
local CLI tool (`ratchet apply --pr <n> --totp <code>`) that the
operator must run while the rotating six-digit code is still valid.
This combines:

* recall of the exact CLI syntax months after last use,
* lookup of the correct PR number,
* a 30-second window before the code rotates,
* a terminal session in the right working directory with the right
  identity loaded.

The empirical consequence — observable in the operator's own notes — is
that small, time-sensitive changes get postponed until they are no
longer small.

### 2.2 Severity

**Medium.** Pipelines that are unpleasant to use are the pipelines
that get bypassed. A bypass means a manual change, which means drift,
which is precisely the failure mode the architecture exists to
prevent.

### 2.3 Remediation — Telegram-mediated approval

Replace the CLI prompt with a chat round-trip. Concretely:

1. The fortress agent runs a small Python service that subscribes to
   the GitHub webhook (existing) and additionally to a private
   Telegram bot.
2. When a labelled merge arrives, the service posts a structured
   message to the operator's chat: PR title, author, diff summary,
   target host, expected blast radius.
3. The operator opens their existing authenticator app, types the
   six digits into the Telegram thread.
4. The service hands those digits to the *unchanged* local
   verification routine that consumes the TOTP today.

### 2.4 What does and does not change

* **Unchanged:** the TOTP seed, the local verification logic, the
  signed audit receipt, the rollback path, the Git source-of-truth
  commit. The PR remains the cryptographic record of intent.
* **Changed:** the *interface* by which the operator delivers the
  six digits. The Telegram bot is purely a transport — it generates
  no token and grants no authority.

### 2.5 Why this is not an air-gap violation

The TOTP seed never traverses Telegram. The Telegram channel carries
only (a) a notification *out* of the agent and (b) an opaque six-digit
string *in*. The string is meaningless without the seed; the seed
remains local. The bot is the building's intercom, not the bouncer.

### 2.6 Acceptance criteria

* The agent rejects approvals delivered through any channel other
  than the configured chat ID.
* HMAC verification of the GitHub webhook (`X-Hub-Signature-256`)
  is enforced before any Telegram notification fires.
* A Telegram outage is *fail-closed*: the operator can still fall
  back to the original CLI flow.
* The audit receipt records `approved_via: telegram` so the channel
  is recoverable from the log.

---

## 3. Hardening Inconsistency: SSH Surface Across Nodes

### 3.1 Finding

The SSH hardening procedure was applied successfully to the N95
management node — both `ssh.service` *and* `ssh.socket` were stopped,
disabled, and **masked**. On the N305 firewall host, the equivalent
work was not completed: the daemon is reachable.

This is the worst possible distribution of the gap. The N305 is the
node that holds the WAN; it is the highest-value compromise in the
architecture.

### 3.2 Severity

**High.** It directly contradicts the zero-trust model documented in
the deep dive (§9) and is the kind of inconsistency that a reviewer
would flag immediately. It exists only because a manual procedure
was run on one box and forgotten on the other.

### 3.3 The systemd subtlety

This finding is also recorded as `INC-01` in the incident register.
The first attempt on the N95 stopped and disabled `ssh.service` but
left `ssh.socket` active. systemd socket-activation will then *wake
the service back up* on the next inbound connection. Masking both
units is the only way to render SSH inert.

The same trap applies to N305 the moment someone runs only half the
procedure.

### 3.4 Remediation — IaC enforcement, not memory

Move SSH masking out of human procedure and into the apply pipeline.
The artefact is an idempotent script (Bash is acceptable here; it
avoids the Ansible/Python prerequisite chain on the targets):

```bash
# Stop and mask both units; run repeatedly without error.
for unit in ssh.socket ssh.service; do
  systemctl is-active --quiet "$unit"  && systemctl stop    "$unit"
  systemctl is-enabled --quiet "$unit" && systemctl disable "$unit"
  systemctl is-masked  --quiet "$unit" || systemctl mask    "$unit"
done
```

The script is committed to the repository, executed by the fortress
agent over the Proxmox `pct exec` API, and applied uniformly to
every host of class `proxmox-host`. Idempotency is non-negotiable —
non-zero exit codes on a no-op would surface as false-positive
pipeline failures and erode operator trust.

### 3.5 Concern: am I removing my last fallback?

No. The fallback when the agent and the chat bot are both
unavailable is the **physical Proxmox console** (HDMI + keyboard
plugged into the node) and the **Proxmox web GUI reached over
Tailscale** — neither requires SSH. The break-glass workflow in §5
formalises this.

### 3.6 Acceptance criteria

* OPA policy in CI rejects any PR that re-introduces an SSH listener
  on a class-`proxmox-host` node.
* `systemctl is-masked ssh.socket ssh.service` is part of the
  agent's post-apply self-check; a non-masked result fails the run
  and triggers rollback.
* The same script targets the N305 explicitly; the prior asymmetry
  is removed.

---

## 4. Observability Gap

### 4.1 Finding

Diagnosing a flaky access point or a dropped firewall packet today
requires logging into the management plane and running CLI tools
(`ratchet poll omada`, OPNsense `pflog`, journal greps). This
assumes the operator remembers tool names, file paths, and event
flags after months of inactivity. Empirically, they do not.

The architecture acknowledges the gap by reserving `LXC 103` for a
monitoring stack. The container is provisioned but the stack is not.

### 4.2 Severity

**Medium.** The system runs without it. But every undiagnosed
incident becomes either a manual override (drift) or a deferred
problem.

### 4.3 Remediation — Prometheus + Grafana + Loki, declared not built

Generate the entire stack as code, including the dashboards, so
there is no "click in the GUI to make a panel" step that gets lost
on the next rebuild.

Components, all in `LXC 103` on `110 SERVICES`:

* **Prometheus** — metric scrape and storage.
* **Loki** — log indexing on labels only (low-RAM, suitable for the
  N95).
* **Promtail** — log shipper deployed to every host that emits
  syslog.
* **Grafana** — pre-loaded dashboards as JSON committed to the repo.

### 4.4 Required firewall rules

`LXC 103` lives on `110 SERVICES`; the targets it must scrape live
on `100 PROXMOX` and the Omada controller on `100 MGMT`. The
default-deny posture means the stack is non-functional until OPNsense
is told otherwise. The agent must therefore ship, along with the
container manifest, an OPNsense XML alias-and-rule fragment that:

* Allows `110 SERVICES` → `100 PROXMOX` on the metrics port
  (`9100/tcp`).
* Allows the Omada controller on `100 MGMT` to ship syslog to `LXC
  103` on `514/udp`.
* Permits *nothing else* across these boundaries.

### 4.5 Validation against AI-emitted XML

OPNsense XML is fragile — a missing closing tag fails the entire
import. The mitigation is structural: the apply path's Gate 7
snapshot covers the firewall configuration. If the import fails, the
agent's OPNsense API call returns an error and the staged change is
rolled back from the snapshot before traffic is affected.

### 4.6 Acceptance criteria

* `docker-compose.yaml` for the stack and `dashboards/*.json` are
  both committed; rebuilding the host from scratch requires zero
  GUI steps.
* A failing apply of either the manifests or the firewall fragment
  rolls back cleanly; no half-imported rules survive.
* The default Grafana dashboard renders Omada Wi-Fi drop events and
  OPNsense block events on a single screen, queryable by VLAN.

---

## 5. Disaster Recovery: No Codified Break-Glass

### 5.1 Finding

The current apply path is correct under the assumption that the
internet, GitHub, the CI runners, and the fortress agent are all
reachable. When they are not — primary DNS is down, the WAN is out,
the fortress host is rebooting — the operator has no documented way
to make a network change.

In practice, the operator will improvise: physical console into
OPNsense, edit a rule, restore service, walk away. That edit is
**undocumented drift**. The next routine reconciliation by the
fortress agent will either (a) revert the emergency fix, resurrecting
the outage, or (b) detect drift and refuse to run, leaving the
operator manually maintaining a parallel state forever.

### 5.2 Severity

**High.** This is the failure mode WhiteLab was built to eliminate;
the architecture currently re-introduces it under stress.

### 5.3 Remediation — two-part break-glass

A break-glass procedure must (a) let the operator save the network
*now* and (b) heal the source of truth *afterwards*.

#### 5.3.1 `ratchet emergency-apply` — local-CLI direct path

A new CLI subcommand on the operator's laptop. It:

1. Skips GitHub entirely. The diff is signed locally with the
   operator's offline key.
2. Pushes the signed payload directly to the fortress agent over
   Tailscale, **using the agent's hard-coded Tailscale IP** rather
   than its hostname (because if DNS is down, name resolution is
   exactly what is failing).
3. Triggers the same Gate-6 TOTP and Gate-7 snapshot as the normal
   path. The cryptographic boundary is unchanged.
4. Writes the signed receipt to local storage; the receipt is
   uploaded to the audit log automatically when the WAN returns.

This handles the case where the cloud is gone but the lab is alive.

#### 5.3.2 `ratchet sync-drift` — retroactive reconciliation

For the harder case (fortress host itself unreachable, or the
operator was forced to use the physical console), a second
subcommand. After the crisis it:

1. Pulls the *running* configuration from OPNsense, Proxmox, and
   Omada via their APIs.
2. Diffs the running state against the last-committed declarative
   state in Git.
3. Generates a single retroactive commit on a `recovery/<date>`
   branch that brings Git back into agreement with reality.
4. The operator opens this as a normal PR, reviews what they did at
   03:00, and merges.

The state file is healed; the manual change is captured as code; the
agent's next reconciliation pass finds nothing to do.

### 5.4 Acceptance criteria

* `emergency-apply` works against a laptop on `120 ESCAPE` with no
  resolver, no GitHub reachability, and the agent reachable only by
  IP.
* `sync-drift` produces a clean diff that round-trips — re-running
  it against an already-synced state yields zero changes.
* Both subcommands write the same audit receipt format as the
  normal apply path; downstream tooling does not need a special
  case.
* A runbook entry under [`docs/runbooks/break-glass.md`](../../../runbooks/break-glass.md)
  documents both flows and is rehearsed at least once before
  Q4 2026.

---

## 6. Documentation Hygiene: Desired State vs Roadmap

### 6.1 Finding

The Architecture Bible currently intermingles three categories of
content:

1. **Desired state** — what the system *is* and must remain.
2. **Roadmap items** — hardware not yet in service (e.g. the
   forthcoming TP-Link SG2210XMP-M2 switches), planned UPS rollout,
   power-on policies pending hardware purchase.
3. **Shower thoughts** — short bullet lists copied from the
   operator's Google Keep that are sometimes ideas, sometimes
   unresolved questions.

Mixing categories is acceptable in a human-only document. It is
**not** acceptable once the file is the canonical input to a
declarative parser. A parser cannot distinguish "this 10 GbE port
plan describes a switch that does not yet exist" from "this is the
configuration to push tonight". It will push.

### 6.2 Severity

**Medium**, rising to **High** the moment the IaC parser starts
ingesting the Bible verbatim.

### 6.3 Remediation — split-brain documentation

* Strip every roadmap and shower-thought item out of the
  desired-state files in `docs/architecture/` and `docs/research/`.
* Move them into a new `docs/contributions/pending-RFCs/` folder, one
  file per topic (e.g. `RFC-0001-fanless-ups.md`,
  `RFC-0002-power-on-states-n305.md`,
  `RFC-0003-uplink-switch-upgrade.md`).
* Configure the IaC parser to read **only** from
  `infra/` and `docs/architecture/`. The pending-RFCs directory is
  invisible to the parser by construction.
* Configure NotebookLM (and Copilot) to read **everything**, so the
  human and AI views remain holistic. The split applies to
  automation, not to humans.

This is the four-issue puzzle from the operator's notes: it
preserves the holistic view (humans and NotebookLM see all of it),
prevents accidental provisioning of imaginary hardware (the parser
sees only the desired state), and gives planning items a structured
home (RFCs are versionable, reviewable, and dateable).

### 6.4 Acceptance criteria

* `infra/` and `docs/architecture/` contain *only* statements that
  describe the running network. Linting fails on `TODO`, `FUTURE`,
  `WHEN WE GET`, `UPGRADE TO`.
* Every item moved into `pending-RFCs/` has an ID, an owner, an open
  question, and a target review date.
* The parser's input set is documented and tested — adding a file
  outside the allowed list does not silently change behaviour.

---

## 7. IP Plan: AdGuard DMZ Subnet Collision

### 7.1 Finding

The interface-assignment table flags an open issue: the AdGuard DMZ
is provisionally mapped to `192.168.20.0/24`, which is the same
subnet currently in use by `20 SECURE`. The note has remained "to be
resolved" for some time.

### 7.2 Severity

**High.** OPNsense uses subnet definitions to compute its routing
and isolation rules. Two zones sharing an address space cannot be
isolated east-to-west — the firewall has no way to tell whether a
packet to `192.168.20.50` belongs to a trusted laptop or a
DMZ-resident DNS server. The zero-trust model is mathematically
unenforceable on overlapping space.

### 7.3 Remediation — declare and apply

Move the DMZ to `192.168.25.0/24` (the next free /24 in the plan)
and commit the change as part of the next apply. Concretely:

* Update `docs/architecture/00-repo-layout.md` and the VLAN matrix to
  declare `192.168.25.0/24` as the AdGuard DMZ.
* Update the OPNsense interface manifest accordingly.
* Update DHCP scopes, firewall aliases, and the Promtail target list
  in the same PR — these are the cross-references that fail
  silently if missed.
* Stage and apply through the eight-gate path; Gate 7's snapshot
  covers the rollback if a static client breaks.

### 7.4 Acceptance criteria

* Zero references to `192.168.20.0/24` outside the `20 SECURE`
  VLAN definition. CI grep enforces this.
* Drift check on next apply reports zero divergence.
* East-west test from `20 SECURE` to `LXC 105` is *blocked*; from
  the DMZ inward to `100 PROXMOX` is *blocked*; outbound DNS to
  Cloudflare is *allowed*.

---

## 8. Resilience: Single-Instance Fortress Agent

### 8.1 Finding

The fortress agent is intentionally singleton. Two fortress agents
would race for the apply lock, contend for the TOTP seed, and could
diverge on encrypted state. Singleton is the right call for the
*active* instance.

The risk is that the singleton's host (the N95) is also a single
piece of fanless silicon with no UPS yet on the roadmap. A power
event during write-out can corrupt the agent's filesystem. With the
agent gone, the operator owns the keys but has no executor — the
metaphorical equivalent of locking the keys inside the tow truck
that was supposed to recover the broken car.

A manual rebuild from the encrypted vault is hours of work in a
known-difficult sequence: install Proxmox, build a base LXC,
reconfigure Tailscale identity, decrypt API tokens with the offline
master key, sequence the start-up dependencies. None of this is
something the operator should be doing for the first time at 02:00.

### 8.2 Severity

**Medium**, rising to **High** until the UPS lands.

### 8.3 Remediation — cold standby on N305

Stand up a *cold* (powered-off) clone of the fortress LXC on the
N305 host. Properties:

* Stored as a Proxmox template, not a running container. It
  consumes disk only.
* No Tailscale identity, no API tokens loaded into memory; it
  cannot accept work in this state.
* Activation is a single documented Proxmox CLI command on the N305
  console — clone the template, attach the operator-supplied
  decryption material, start the container. Existing TOTP and audit
  flows resume.
* Since the standby is *off*, it neither contends for the apply
  lock nor competes for a Tailscale identity. There is no race.

This converts a multi-hour rebuild into a five-minute recovery and
re-uses hardware already in the rack.

### 8.4 Acceptance criteria

* The cold standby is rebuilt from scratch *as part of the apply
  pipeline* on every fortress release; it cannot rot.
* A documented drill — power off N95, activate standby, run a
  no-op apply, verify the audit receipt — is rehearsed at least
  once per quarter.
* The standby's disk image is encrypted at rest; activation
  requires the offline master key.

---

## 9. Total Cluster Loss: Laptop-as-Agent Mode

### 9.1 Finding

If a power surge removes both the N95 and the N305 motherboards
simultaneously — the worst case the no-UPS roadmap explicitly
admits — the cold standby in §8 is unreachable. The operator has the
encrypted vault, the offline keys, and Git history on the laptop;
they have *no execution surface* on which to run the agent.

### 9.2 Severity

**Low (probability) × High (impact)**. Treated as a tail-risk that
must be testable, not as a daily concern.

### 9.3 Remediation — `ratchet --laptop-agent`

Add an explicit, audit-flagged mode to the local CLI in which the
laptop temporarily assumes the fortress identity for the purpose of
bootstrapping replacement hardware:

* The CLI loads the agent's identity from the offline vault using
  the operator's master key.
* It runs the same state machine the LXC normally runs, but in the
  laptop's process space.
* The first thing it does on a freshly imaged Proxmox host is push
  the fortress LXC manifest itself, then transfer the active
  identity to the new container, then revoke the laptop's
  temporary role.
* Every step still demands TOTP, signs receipts, and writes audit
  entries; the cryptographic contract is unchanged.

This is the architectural equivalent of jump-starting a car: the
external power source is permitted to participate just long enough
to get the car running, then disengages.

### 9.4 Acceptance criteria

* The mode self-revokes the laptop identity once the new fortress
  is healthy. There is no path that leaves the laptop with
  permanent agent powers.
* A "rebuild from a single laptop and a USB key" drill is documented
  in the runbooks and rehearsed at least annually.
* The drill produces a complete audit chain — receipts from the
  laptop-agent phase are indistinguishable in format from receipts
  produced by the LXC.

---

## 10. Prioritized Remediation Roadmap

The findings interact. The order below reflects (a) how much each
remediation reduces *operational* risk and (b) which other fixes
become safer once the prerequisite is in place.

| # | Remediation | Severity | Prerequisite | Target |
| - | ----------- | -------- | ------------ | ------ |
| 1 | Resolve AdGuard DMZ subnet collision (§7) | High | None | Immediate — single-PR fix |
| 2 | Apply uniform SSH masking via IaC to N305 (§3) | High | None | Within next apply cycle |
| 3 | Split desired state from roadmap into `pending-RFCs/` (§6) | Medium → High | None | Next docs sprint |
| 4 | Document and ship `emergency-apply` + `sync-drift` (§5) | High | Decision on local-signing key UX | Before Q3 2026 |
| 5 | Telegram-mediated TOTP approval (§2) | Medium | HMAC-256 webhook validation in agent | Q3 2026 |
| 6 | Stand up monitoring stack in `LXC 103` (§4) | Medium | Item 1 (so DMZ rules are stable) | Q3 2026 |
| 7 | Cold-standby fortress on N305 (§8) | Medium → High | Item 2 (so N305 is hardened) | Q3 2026 |
| 8 | `--laptop-agent` mode + annual drill (§9) | Tail-risk | Items 4 and 7 | Q4 2026 |

A single sentence captures the spirit of every recommendation
above: **the cryptography is sound; the gaps are in what the
operator has to remember on a Tuesday morning, and every gap should
be closed by code rather than by training the operator harder.**

---

## 11. Cross-references

* [Unified deep dive](../unified%20deep%20dive/unified-deep-dive.md) — companion document.
* [`docs/architecture/02-sync-workflow.md`](../../../architecture/02-sync-workflow.md) — the eight-gate path that the break-glass and Telegram changes extend.
* [`docs/architecture/2.0-fortress-design.md`](../../../architecture/2.0-fortress-design.md) — fortress agent specification; the cold-standby and laptop-agent modes belong here.
* [`docs/runbooks/break-glass.md`](../../../runbooks/break-glass.md) — currently a stub; the home for the §5 procedure.
* [`docs/runbooks/recover-fortress-agent.md`](../../../runbooks/recover-fortress-agent.md) — currently a stub; the home for the §8 and §9 drills.
* [`docs/threat-model/00-initial-sketch.md`](../../../threat-model/00-initial-sketch.md) — the T1–T6 levels referenced throughout.
