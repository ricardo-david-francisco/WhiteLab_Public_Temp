# WhiteLab — Unified Deep Dive

**Version:** 1.0
**Date:** 2026-05-06
**Scope:** End-to-end synthesis of the WhiteLab home-lab infrastructure, the
GitOps "centralized brain" that drives it, and the security model that binds
the two together.
**Sources:** Architecture Bible, NADD (Network Architecture Design
Document), incident register, fortress-agent specification, and the
NotebookLM deep-dive transcripts in [../../notebooklm/Deep_Dive/](../../notebooklm/Deep_Dive/).
**Audience:** The repository owner returning to the project after time
away, plus any reviewer or future collaborator who needs the full picture
in one document.

---

## Quick read — jump to the topic you need

If you are not going to read the whole document, read these bullets. Each
links to the section that discusses that topic in depth.

* [DevOps amnesia and documentation drift](#2-background-and-motivation) — why the lab is built around code-as-memory; the canonical drift incident `INC-NADD-DRIFT-01`.
* [Physical topology and VLAN inventory](#3-physical-topology) — N305 / N95 / Omada / G.hn power-line / Caddy / Tailscale; the 15 VLAN segments.
* [Reverse proxy vs. port-forwarding](#32-reverse-proxy-why-not-just-port-forward) — SNI-based routing as the only public surface.
* [The lobotomy and the ARP-shock incident](#4-case-study-the-lobotomy-and-the-arp-shock) — OPNsense bare-metal → Proxmox VM with PCI passthrough; ISP MAC binding; recovery procedure.
* [The five jobs of the centralized brain](#5-the-five-jobs-of-whitelab-centralized-brain) — single source of truth, PR-only changes, internal apply, signed audit, anonymisation.
* [Steering wheel vs. muscle pattern](#6-architectural-pattern-steering-wheel-and-muscle) — powerless laptop / privileged fortress agent; how the split defeats T5 and T6.
* [The anonymisation gate](#7-the-anonymisation-gate) — deterministic placeholders; reverse-mapping inside the perimeter.
* [Zero-trust as four operational rules](#8-zero-trust-model) — default-deny, named-and-scoped tokens, position is not authentication, two factors for every state change.
* [Why SSH is removed everywhere](#9-deprecation-of-ssh) — attack-surface argument; HTTPS API tokens replace shells.
* [The eight-gate apply path](#10-the-eight-gate-apply-path) — worked example: bumping `CT-105` memory from 1 GiB to 2 GiB, gate by gate.
* [Threat model T1–T6 and mitigations](#11-threat-model-and-mitigations) — the table of attacker capabilities and the WhiteLab guarantee against each.
* [DNS resilience and the AdGuard DMZ](#12-dns-resilience) — why DNS moved out of OPNsense; planned redundancy.
* [Glossary of every acronym used](#13-glossary).
* [Cross-references to the formal docs](#14-cross-references).

> **Centralised roadmap and capture system** are live on `master` (see
> [`docs/roadmap/README.md`](../../../roadmap/README.md) and
> [`docs/contributions/pending-RFCs/`](../../pending-RFCs/)). Every
> finding from the [unified critique](../unified%20critique/unified-critique.md)
> is tracked there.

## Table of contents

1. [Executive Summary](#1-executive-summary)
2. [Background and Motivation](#2-background-and-motivation)
    1. [DevOps amnesia](#21-devops-amnesia)
    2. [Documentation drift (`INC-NADD-DRIFT-01`)](#22-documentation-drift-inc-nadd-drift-01)
    3. [Goal: documentation *is* the network](#23-goal-documentation-is-the-network)
3. [Physical Topology](#3-physical-topology)
    1. [VLAN inventory (15 segments)](#31-vlan-inventory-15-segments)
    2. [Reverse proxy: why not just port-forward?](#32-reverse-proxy-why-not-just-port-forward)
4. [Case Study: The Lobotomy and the ARP Shock](#4-case-study-the-lobotomy-and-the-arp-shock)
    1. [The change](#41-the-change)
    2. [The incident — `INC-ARP-SHK-01`](#42-the-incident--inc-arp-shk-01)
    3. [Recovery and lesson](#43-recovery-and-lesson)
5. [The Five Jobs of WhiteLab (Centralized Brain)](#5-the-five-jobs-of-whitelab-centralized-brain)
6. [Architectural Pattern: Steering Wheel and Muscle](#6-architectural-pattern-steering-wheel-and-muscle)
    1. [The steering wheel](#61-the-steering-wheel)
    2. [The muscle — the fortress agent](#62-the-muscle--the-fortress-agent)
    3. [Why split](#63-why-split)
7. [The Anonymisation Gate](#7-the-anonymisation-gate)
    1. [Mechanism](#71-mechanism)
    2. [Why this is enough for Copilot](#72-why-this-is-enough-for-copilot)
    3. [Reverse mapping inside the perimeter](#73-reverse-mapping-inside-the-perimeter)
8. [Zero-Trust Model](#8-zero-trust-model)
    1. [What changed compared to the old castle-and-moat model](#81-what-changed-compared-to-the-old-castle-and-moat-model)
9. [Deprecation of SSH](#9-deprecation-of-ssh)
    1. [Why SSH is incompatible with the model](#91-why-ssh-is-incompatible-with-the-model)
    2. [What replaces it](#92-what-replaces-it)
    3. [Operational consequence](#93-operational-consequence)
10. [The Eight-Gate Apply Path](#10-the-eight-gate-apply-path)
11. [Threat Model and Mitigations](#11-threat-model-and-mitigations)
12. [DNS Resilience](#12-dns-resilience)
    1. [Why DNS is decoupled from the firewall](#121-why-dns-is-decoupled-from-the-firewall)
    2. [Upstream](#122-upstream)
    3. [Failure modes and the planned redundancy](#123-failure-modes-and-the-planned-redundancy)
13. [Glossary](#13-glossary)
14. [Cross-references](#14-cross-references)

---

## 1. Executive Summary

WhiteLab is a single-operator home-lab whose physical layer (one firewall
host, one management host, layer-2 switching, Wi-Fi 6, power-line
backhaul) is segmented into 15 VLANs and operated as **infrastructure as
code from day one**.

The defining problem is not capacity, performance, or cost — it is
**memory**. The lab was co-built with an AI pair-programmer that emitted
correct configuration faster than the operator could internalise it.
Three months of inactivity is enough for the operator to forget which
wires are physical, which are virtual, which firewall rule guards which
zone, and why a given decision was made. The industry term is *DevOps
amnesia*; the local symptom is *documentation drift*
(`INC-NADD-DRIFT-01` in the incident register).

WhiteLab's response is a small system — internally referred to as the
"centralized brain" — that replaces fragile human memory with strictly
enforced code. It has five responsibilities:

1. Be the **single source of truth** (declarative config in Git).
2. **Control all changes via pull requests** with mandatory review.
3. **Apply changes safely** through an internal agent, never from the cloud.
4. **Audit everything** with cryptographically signed receipts.
5. **Anonymise sensitive data** before any byte leaves the workstation.

The architecture separates a powerless **steering wheel** (laptop, Git,
Copilot) from a privileged **muscle** (the fortress agent, an LXC
container deep inside the network) and gates every state change with
zero-trust checks, two independent factors, an automated drift check,
and an automatic snapshot/rollback.

The remainder of this document maps each of those pieces, the incidents
that motivated them, and the mechanics that make them work.

---

## 2. Background and Motivation

### 2.1 DevOps amnesia

A complex, highly customised system loses its operator the moment they
step away from it. The longer the gap, the higher the cost of the
re-entry — every change becomes a guessing game against a decaying
mental model. WhiteLab's posture is that human memory does not scale; it
must be replaced by machine-checked code.

### 2.2 Documentation drift (`INC-NADD-DRIFT-01`)

Drift is the silent failure mode of any text-only documentation. The
canonical example in this repository:

* The original NADD declared the OPNsense firewall as **bare-metal** on
  the N305 host.
* The "lobotomy" (Section 4) virtualised it; the silicon's role
  changed.
* The Word document did not.

From that moment forward, every plan based on the document was planning
against a system that no longer existed. Drift is fatal in declarative
infrastructure because the parser executes the documented intent against
the live system — if the two disagree, the parser either reverts the
fix or refuses to run.

### 2.3 Goal: documentation *is* the network

The cure is structural. The configuration is no longer a description;
it is the executable definition of the system. There is exactly one
source of truth, it lives in Git, and the running infrastructure is
continuously reconciled against it.

---

## 3. Physical Topology

| Role               | Hardware                                       | Notes |
| ------------------ | ---------------------------------------------- | ----- |
| Firewall host      | Topton fanless mini-PC, Intel **N305**, 4 × 2.5 GbE | Hosts virtualised OPNsense (see §4) |
| Management node    | Mini-PC, Intel **N95**                          | Hosts the fortress agent (LXC 104) and DNS container (LXC 105) |
| Core switch        | Omada 8-port                                   | Trunks all VLANs |
| Distribution switch| Omada 8-port                                   | Edge ports |
| Wireless           | Wi-Fi 6 access points (Omada)                  | Multi-SSID, VLAN-tagged |
| Backhaul           | G.hn power-line adapters                        | Carries tagged traffic over mains wiring |
| Reverse proxy      | Caddy in an LXC                                 | TLS termination, SNI-based routing |
| Remote access      | Tailscale (WireGuard mesh)                      | Outbound-only; no inbound ports |

### 3.1 VLAN inventory (15 segments)

Notable segments:

* `10 MGMT` — switches and access points only.
* `20 SECURE` — trusted laptops.
* `40 ADMIN` — air-gapped; **only** network permitted to reach the
  firewall login page.
* `70 IOT` — smart-home devices; default-deny outbound to LAN.
* `80 CAMERA` — cloud cameras.
* `100 PROXMOX` — hypervisor management.
* `110 SERVICES` — application containers (monitoring stack lives here).
* `120 ESCAPE` — break-glass network.

The full table is maintained in
[../../../architecture/00-repo-layout.md](../../../architecture/00-repo-layout.md)
and the Infrastructure Bible (`docs/research/01-infrastructure-bible.md`).

### 3.2 Reverse proxy: why not just port-forward?

Direct port-forwarding exposes the application server to the open
internet — anyone who finds the port can attack the binary directly.
Caddy as a reverse proxy terminates the connection at the perimeter,
inspects the **SNI** (Server Name Indication) field of the TLS
handshake, and proxies to the correct internal service. The internal
topology is invisible from outside; the public surface is one
hostname, one process, one binary kept patched.

---

## 4. Case Study: The Lobotomy and the ARP Shock

The lobotomy is a useful reference because it is the canonical example
of a "successful" change that nonetheless caused an outage and seeded
two years of drift.

### 4.1 The change

* **Before:** OPNsense installed bare-metal on the N305.
* **After:** Proxmox installed bare-metal on the N305; OPNsense restored
  into a VM on top of Proxmox; the four physical 2.5 GbE NICs handed to
  the OPNsense VM via PCI(e) **passthrough**.

PCI passthrough is required because a VM does not natively own physical
NICs — the hypervisor must explicitly relinquish them.

### 4.2 The incident — `INC-ARP-SHK-01`

Immediately after the cut-over the ISP modem refused to issue a public
IP. Cause:

1. ISP modems commonly bind the issued public IP to the **MAC address**
   they first negotiate with (an anti-IP-theft measure).
2. PCI passthrough preserved the *port*, but the OPNsense VM presented a
   fresh, virtual MAC on the WAN interface.
3. From the modem's perspective, a stranger appeared on the wire — it
   dropped the lease.

### 4.3 Recovery and lesson

Recovery required power-cycling the modem long enough for its ARP
table to age out, then power-cycling the upstream switches in a
specific order to force a clean handshake. The architectural takeaway
is that **physical truth and documented truth must converge
automatically**; relying on the operator to remember "we virtualised
this two years ago, watch the WAN MAC" is the failure mode WhiteLab
exists to eliminate.

---

## 5. The Five Jobs of WhiteLab (Centralized Brain)

| # | Job                                                | Implementation |
| - | -------------------------------------------------- | -------------- |
| 1 | Be the single source of truth                     | Declarative YAML/XML in Git |
| 2 | Control all changes via pull requests             | Branch-protected `master`; PR-only merges |
| 3 | Apply changes safely                               | Fortress agent (LXC 104) — never the laptop or GitHub |
| 4 | Audit everything (tamper-proof)                    | Signed JSON receipt per apply, committed back to repo |
| 5 | Anonymise data before it hits the cloud            | Deterministic pre-commit scrubber (see §7) |

These five obligations bound every other design decision in the
repository.

---

## 6. Architectural Pattern: Steering Wheel and Muscle

WhiteLab partitions the change-control system into two halves with
*deliberately asymmetric* power.

### 6.1 The steering wheel

* **What:** the operator's laptop, the GitHub repository, the Copilot
  pair-programmer.
* **Capability:** plan routes, write code, propose changes, review
  diffs, merge PRs.
* **Capability it does not have:** any credential to any device on the
  home network. No Proxmox API token, no OPNsense root password, no
  switch admin password, no ability to open or close a single firewall
  port.

The steering wheel can produce *intent*. It cannot produce a state
change.

### 6.2 The muscle — the fortress agent

* **What:** an LXC container designated `LXC 104`, running on the N95
  management node.
* **Capability:** holds Proxmox API tokens, OPNsense API tokens, and
  Omada controller credentials. It is the only entity in the system
  permitted to mutate live infrastructure.
* **Network position:** inside the home perimeter; reachable from the
  outside world only via the outbound Tailscale tunnel it itself
  initiates.

### 6.3 Why split

Threat-model framing (see also §11):

* **T5 — GitHub credentials compromised.** An attacker who phishes the
  GitHub account or bypasses 2FA gets *the steering wheel*. They can
  merge any change they like. Without the muscle's keys, none of those
  merges turn into network changes.
* **T6 — GitHub itself compromised.** Even an attacker who can forge
  CI checks and the apply-approved label cannot proceed past Gate 6
  (TOTP) because the secret seed lives only on the operator's hardware
  token.

The split is what gives WhiteLab the property that *no purely cloud-side
compromise* can change the network.

---

## 7. The Anonymisation Gate

The anonymiser is the mechanism that allows Copilot and a public Git
remote to participate in the workflow without learning the network's
real identifiers.

### 7.1 Mechanism

A pre-commit hook on the laptop intercepts every diff before Git
commits it. The script is *deterministic*: a given input always
produces the same output, so the same real value always maps to the
same placeholder.

| Real value                          | Replaced with |
| ----------------------------------- | ------------- |
| Firewall LAN IP `192.168.1.1`       | `ROUTER_VAR`  |
| Tailnet name `whalemully`           | `TSNET_VAR`   |
| Per-host MAC addresses              | `MAC_VAR_<n>` |
| Public IP                           | `WAN_VAR`     |
| Tailscale node names                | `TSNODE_VAR_<n>` |

### 7.2 Why this is enough for Copilot

Copilot (and any reviewer) needs the *logical* shape of the
configuration: "router routes to switch", "container A reaches port
9100 on container B". It does not need the absolute values. A rule
that says "block traffic from `IOT_VAR` to `ROUTER_VAR`" carries the
full security semantics with none of the doxxing.

### 7.3 Reverse mapping inside the perimeter

When the fortress agent pulls the sanitised commit, it expands the
placeholders using a **local, encrypted dictionary** stored only on
the agent's filesystem. The dictionary is regenerated from the
operator's offline vault and never crosses the perimeter. The
anonymisation is therefore lossless to the operator and total to
everyone else.

---

## 8. Zero-Trust Model

WhiteLab applies zero-trust as four operational rules, not as a vendor
checkbox.

| # | Rule | Mechanism |
| - | ---- | --------- |
| 1 | No device trusts another device just because they share a network | OPNsense default-deny between VLANs; explicit east-west allow rules only |
| 2 | Every action is named, scoped, and time-bound                     | API tokens (not user logins) with explicit verb scope and expiry |
| 3 | Network position is never authentication                          | Reaching a service over Tailscale is necessary but not sufficient — credentials are still required |
| 4 | Two independent factors are required for any state change         | Merged PR (factor 1) **plus** local TOTP at the fortress agent (factor 2) |

### 8.1 What changed compared to the old castle-and-moat model

In the legacy model, "inside the firewall" implied "trusted". A
laptop on Wi-Fi could ping the printer, scan the NAS, and reach the
firewall login page directly. In WhiteLab none of those edges exist
implicitly — each is an explicit, codified east-west rule, and the
firewall login page is reachable only from the air-gapped `40 ADMIN`
VLAN.

---

## 9. Deprecation of SSH

WhiteLab eliminates SSH from every host it controls, including the
hypervisors. This is a deliberate, controversial decision; the
reasoning matters.

### 9.1 Why SSH is incompatible with the model

* **Always-on attack surface.** `sshd` listens on port 22 (or wherever
  it is moved) 24×7, accepting and parsing untrusted bytes. Any
  remotely exploitable bug in the daemon is an instant root path.
* **Coarse-grained authority.** A successful SSH login produces a
  shell. A shell is "do anything". There is no equivalent of
  "restart this one container, only, for the next 60 minutes".
* **Credential hygiene is hard.** Long-lived keys stored on operator
  laptops are a perennial leak source; rotation is manual and rarely
  done.

### 9.2 What replaces it

The fortress agent talks to Proxmox and OPNsense over their **HTTPS
APIs** using **named, scoped, time-bound tokens**. Each token answers
exactly one question — "may I restart container 105?" — for a
limited window, and every call is logged on both sides.

By analogy: SSH is a master key for the whole house. The HTTPS API is
a key-card that opens one door, only during a stated hour, and writes
an entry in the log every time it is used.

### 9.3 Operational consequence

The IoT-compromise scenario (`T2`) becomes a non-event. A hostile
firmware update inside the `70 IOT` VLAN scans for open ports; finds
none on the management plane; cannot route to it anyway because of
firewall rules; cannot brute-force passwords because no password
endpoint exists. The attack surface from inside the perimeter is a
flat wall.

---

## 10. The Eight-Gate Apply Path

Every change to the running infrastructure traverses eight gates in
order. The example below tracks a single trivial edit — bumping the
RAM allocation of the AdGuard DNS container (`CT-105`) from 1 GiB to
2 GiB.

### Gate 1 — Author intent

The operator opens the relevant YAML file on the laptop, changes
`memory: 1024` to `memory: 2048`, commits the diff, and pushes a
pull request. No production system has been contacted.

### Gate 2 — Automated CI

GitHub Actions runs three checks against the proposed diff:

1. **Lint.** YAML/structural validity. Catches typos that would crash
   the parser.
2. **CVE scan (Snyk / Trivy).** Cross-references requested software
   versions against the public CVE feeds. Stops a PR that would pin a
   known-vulnerable image.
3. **Open Policy Agent (OPA / Rego).** Evaluates the diff against the
   master security policies — for example, *no manifest may declare a
   listener on port 22*. Rule violations block the PR mechanically;
   the human cannot override OPA from the steering wheel.

### Gate 3 — Human review and explicit intent

The CI status passes. A reviewer (in single-operator mode, the author
acting as their own reviewer the next morning) approves and merges.
The merge alone is **not** a deploy authorisation; the PR must also
carry the `apply.approved` label. This separates "the code is good"
from "deploy it now".

### Gate 4 — Webhook delivery without an inbound port

GitHub fires a webhook when the labelled merge lands. The home
network has *no inbound ports* open; the webhook nonetheless reaches
the fortress agent through Tailscale:

* The fortress agent runs a Tailscale client that initiates an
  outbound WireGuard tunnel to the Tailscale coordination plane on
  boot.
* OPNsense permits the outbound flow; UDP hole-punching keeps it
  alive.
* GitHub's webhook is delivered to a Tailscale **funnel** endpoint in
  the cloud, which forwards it down the existing tunnel.

The agent receives the webhook with no firewall change and no public
listener.

### Gate 5 — Drift check

Before doing anything else, the agent queries the live Proxmox and
OPNsense APIs and compares the *current* configuration against the
*last-applied* state recorded in Git. If they disagree (i.e. someone
made a manual change at 03:00 last Tuesday), the agent **halts**.
This is the pre-flight checklist analogue: instruments and physical
control surfaces must agree before take-off.

The break-glass / drift-sync workflow that handles legitimate manual
overrides is covered in the unified critique
([../unified critique/unified-critique.md](../unified%20critique/unified-critique.md))
under §5.

### Gate 6 — TOTP (the ultimate lock)

The agent pauses and waits for an interactive 6-digit
**time-based one-time password**. The seed for that TOTP exists in
exactly two places: the agent's local secret store and the operator's
physical authenticator (phone or YubiKey). The seed has *never*
crossed the perimeter and has *no* representation in GitHub, Copilot,
or the cloud.

This is the gate that defeats `T6` — a fully compromised GitHub. An
attacker can forge merges, labels, CI status, and webhooks; they
cannot generate a valid TOTP because they do not possess the seed.
The deployment fails closed.

### Gate 7 — Pre-change snapshot

Before mutating anything the agent calls Proxmox to take a
**block-level snapshot** of the affected resource. This is the
free, automatic safety net for the next gate.

### Gate 8 — Execute, observe, audit

The agent applies the new configuration (in the example, a 2 GiB
memory allocation), restarts the container, and watches its boot. On
success it generates a signed JSON receipt — PR number, commit hash,
applied diff, timestamp, signature — and commits it back to the audit
log directory of the repository. On failure (kernel panic, health
check timeout, port unreachable) it commands Proxmox to roll back to
the Gate-7 snapshot, records the failure, and notifies the operator.
The system heals itself without human intervention.

---

## 11. Threat Model and Mitigations

The repository's threat-model document
([../../../threat-model/00-initial-sketch.md](../../../threat-model/00-initial-sketch.md))
is the canonical reference. The deep-dive synthesis is below.

| Level | Scenario | What the attacker gains | What WhiteLab guarantees |
| ----- | -------- | ----------------------- | ------------------------ |
| T1 | Hostile public internet | Public IP, ports | Reverse proxy at perimeter; no admin surface exposed |
| T2 | Compromised IoT firmware (cheap smart bulb on `70 IOT`) | Lateral scanning from inside the perimeter | No SSH targets; default-deny east-west; bulb sees only other bulbs |
| T3 | Compromised laptop (steering wheel) | Read access to the sanitised repo, ability to push commits | Cannot reach the network; muscle has separate keys; commits still require CI + label + TOTP |
| T4 | Lost / stolen authenticator | Possession of one factor | Still requires merged-and-labelled PR; revocation rotates the seed |
| T5 | GitHub account stolen (password + 2FA bypass) | Full control of the steering wheel | Cannot generate a TOTP; muscle refuses |
| T6 | GitHub itself compromised (nation-state) | Ability to forge CI, labels, webhooks | TOTP seed is local-only; agent fails closed; pipeline times out |

The recurring property: **no compromise of any cloud-side component
can change the running network without the local TOTP seed**. Local
compromise (physical access to the operator's hardware) is treated as
out of scope for the cryptographic layer and handled with disk
encryption, full-system backups, and the recovery procedures in
[../../../runbooks/](../../../runbooks/).

---

## 12. DNS Resilience

The deep-dive transcripts terminate mid-discussion of DNS; this
section captures the design as committed to the architecture
documents.

### 12.1 Why DNS is decoupled from the firewall

In the original layout DNS resolution lived inside OPNsense. Two
problems:

1. Every firewall reboot was a DNS outage — including reboots
   triggered by routine config reloads.
2. Any DNS-layer customisation (filtering, alternative upstreams) was
   coupled to the firewall release cycle.

DNS is therefore moved out of OPNsense into a dedicated AdGuard Home
container — `LXC 105` — living in a small, isolated DMZ.

### 12.2 Upstream

AdGuard forwards to Cloudflare's malware-blocking resolvers
(`1.1.1.2` / `1.0.0.2`) over DoT/DoH. Internal queries do not
traverse the public DNS hierarchy in plaintext.

### 12.3 Failure modes and the planned redundancy

A single DNS container is itself a single point of failure. The
roadmap (see the unified critique §6) tracks:

* A secondary DNS container or a Pi-hole on the management node, so
  that maintenance on `LXC 105` does not blank the network.
* Client-side DNS configuration distributed by DHCP with both
  resolvers, so a client failure is transparent.
* Documenting the manual fallback (`1.1.1.1` direct) for the
  break-glass network `120 ESCAPE`.

This work is tracked as a pending RFC and is out of scope for the
declarative state until it lands.

---

## 13. Glossary

| Term | Meaning |
| ---- | ------- |
| ADR | Architecture Decision Record. One short, dated, immutable note per structural choice. |
| ARP | Address Resolution Protocol — maps IP to MAC on a local segment. |
| Bare-metal | OS installed directly on hardware, with no hypervisor layer. |
| Caddy | The reverse proxy used at the perimeter. |
| CT / LXC | Linux Container running under Proxmox. |
| Drift | Divergence between the documented intent and the running state. |
| Fortress agent | The privileged LXC (`104`) that holds API tokens and executes changes. |
| GitOps | Workflow in which Git is the single source of truth and an in-cluster agent reconciles reality to it. |
| Hypervisor | Operating system whose only job is to host VMs. Proxmox in our case. |
| IaC | Infrastructure as Code. |
| Idempotent | An operation that produces the same end state whether run once or many times. |
| Lobotomy | The migration of OPNsense from bare-metal to a Proxmox VM on the N305. |
| MAC address | Hardware-level identifier on the network chip; the unit ARP and the ISP modem care about. |
| Muscle | The half of the system with the credentials — the fortress agent. |
| NADD | Network Architecture Design Document. |
| OPA / Rego | Open Policy Agent and its policy language; enforces security policy in CI. |
| PCI passthrough | Handing a physical PCI device directly to a VM; the hypervisor releases ownership. |
| Reverse proxy | A perimeter process that terminates inbound connections and routes them by SNI/host. |
| SNI | Server Name Indication — the hostname the client asks for in the TLS handshake. |
| Steering wheel | The half of the system that plans without privilege — laptop, repo, Copilot. |
| Tailscale | Mesh VPN built on WireGuard; outbound tunnels and identity-based ACLs. |
| TOTP | Time-based One-Time Password — the local 6-digit factor. |
| VLAN | 802.1Q virtual LAN; logical segmentation of a single physical L2. |
| YAML | Human-readable serialisation format used for the declarative state. |

---

## 14. Cross-references

* [`docs/architecture/00-repo-layout.md`](../../../architecture/00-repo-layout.md) — repository layout.
* [`docs/architecture/01-anonymization-pipeline.md`](../../../architecture/01-anonymization-pipeline.md) — the deterministic scrubber.
* [`docs/architecture/02-sync-workflow.md`](../../../architecture/02-sync-workflow.md) — the eight-gate apply path.
* [`docs/architecture/2.0-fortress-design.md`](../../../architecture/2.0-fortress-design.md) — fortress agent specification.
* [`docs/research/01-infrastructure-bible.md`](../../../research/01-infrastructure-bible.md) — physical inventory, VLAN matrix, port assignments.
* [`docs/threat-model/00-initial-sketch.md`](../../../threat-model/00-initial-sketch.md) — threat-model levels T1–T6.
* [`docs/runbooks/`](../../../runbooks/) — operational procedures (apply, pull, recover, break-glass).
* [Unified critique](../unified%20critique/unified-critique.md) — the companion document.
