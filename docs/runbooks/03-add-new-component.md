# 03 — Adding a new component (end-to-end)

> Canonical recipe for landing a new component (AdGuard, Immich, Seafile,
> Loki, a NAS share, …) in WhiteLab. Worked example throughout: the
> `ct-105-adguard-dmz` stub already on disk under
> [`infra/lxc/ct-105-adguard-dmz/`](../../infra/lxc/ct-105-adguard-dmz/).
>
> Read this first if you have never landed a component before. Once you
> have, you can follow the section headings as a checklist.

---

## 0. Why no-SSH is non-negotiable

The Proxmox hosts (`n95`, `n305`) **never expose SSH**. The fortress-agent
LXC (CT-104) is the only thing that talks to them, and it talks over the
following channels only:

| Target          | Transport                        | Auth                                       |
| --------------- | -------------------------------- | ------------------------------------------ |
| Proxmox VE API  | HTTPS to `pve.<host>:8006`       | scoped API token (per-node, per-action)    |
| OPNsense API    | HTTPS to `firewall.<dmz>`        | scoped API key/secret (per role)           |
| Omada API       | HTTPS to controller (LXC 101)    | OpenAPI v6 token                           |
| Tailscale ACL   | wireguard inside the tailnet     | machine identity + ACL tags                |

The agent itself is reached **only inbound from GitHub Actions** via a
signed webhook (see [`apply-trigger.yml`](../../.github/workflows/apply-trigger.yml)),
and that endpoint is published only on the agent's tailscale interface
(`tag:fortress-agent`). There is no public ingress, no SSH key in any
authorized_keys file, and no shared root password.

A new component never gets a new transport. It either reuses the
existing per-target adapter (`tools/fortress-agent/adapters/{proxmox,opnsense,omada}.py`)
or it triggers writing a new adapter — which itself is a separate PR
gated by Snyk + OPA + a manual review. **You cannot bypass an adapter
to deploy something faster.** That's the entire point of the design.

---

## 1. The recipe (per component)

Each new component is a **5-PR sequence**, all on feature branches off
`master`, each independently squash-merged. Smaller PRs = green CI =
tighter blast radius if something is wrong.

| #   | Branch                                         | What lands                                                         | Reviewer focus                            |
| --- | ---------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------- |
| PR1 | `design/<comp>-bible`                          | `docs/research/NN-<comp>-bible.md` + threat-model entry            | Is the design correct?                    |
| PR2 | `infra/<comp>-network`                         | OPNsense delta + Proxmox bridge/VLAN delta                         | Network reachability + firewall rules     |
| PR3 | `infra/<comp>-ct`                              | `infra/lxc/ct-NNN-<comp>/` (`ct.yaml`, `compose.yaml`, audit)      | Resource sizing + image lineage           |
| PR4 | `infra/<comp>-reverse-proxy`                   | `infra/caddy/Caddyfile.j2` adds `<comp>.<TAILNET>.ts.net`          | TLS, ACL, Tailscale tag                   |
| PR5 | `chore/<comp>-anonymizer-rules`                | `tools/anonymizer/rules.yaml` entries for the new export formats   | No real secret can leak after this lands  |

Each PR runs the same CI gate: **anonymization-gate → ci → trivy → snyk
→ opa**. All five must be green before the `apply:approved` label can
even be considered.

---

## 2. Worked example — AdGuard Home (CT-105)

What the worked example shows is reusable for *any* container-style
component on Proxmox. Substitute the name/VMID/VLAN as needed.

### 2.1 PR1 — the design bible

Create `docs/research/NN-adguard-bible.md` with these sections:

1. **Purpose** — recursive resolver for SECURE/IOT/GUEST/PERSONAL/WORK
   VLANs; OPNsense unbound stays primary, AdGuard is failover/blocklist.
2. **Topology** — DMZ subnet `192.168.25.0/24` on `vmbr2`,
   reachable only from OPNsense + CT-100 (Caddy).
3. **Failure mode** — if AdGuard down, OPNsense unbound continues; no
   single-point-of-failure for DNS.
4. **Anonymization** — query log filenames + blocklist URLs scrubbed.
5. **Threat model entry** — append to
   [`docs/threat-model/00-initial-sketch.md`](../threat-model/00-initial-sketch.md)
   (DNS-rebind / cache-poisoning / log-disclosure rows).

### 2.2 PR2 — the network delta

Two files:

```text
infra/opnsense/deltas/2026-MM-DD-vmbr2-dmz-interface.xml.j2
infra/proxmox/n305/exports/interfaces.anonymized
```

The OPNsense delta adds the `vlan_dmz` interface (untagged on `vmbr2`),
firewall rules permitting `tcp/udp/53` from VLAN-clients to
`192.168.25.10`, and **denying** all other DMZ-egress except DoT/DoH
upstream. The Proxmox export updates the bridge map.

### 2.3 PR3 — the LXC delta

The directory `infra/lxc/ct-105-adguard-dmz/` already exists in this
repo as a worked example. Inspect:

- [`ct.yaml`](../../infra/lxc/ct-105-adguard-dmz/ct.yaml) — declarative payload
  the Proxmox adapter `POST`s to `/api2/json/nodes/<node>/lxc`.
- [`compose.yaml`](../../infra/lxc/ct-105-adguard-dmz/compose.yaml) — Docker
  stack rendered onto rootfs once the CT is up.
- [`adguard-config.yaml`](../../infra/lxc/ct-105-adguard-dmz/adguard-config.yaml)
  — application config with `${...}` placeholders for anonmap rehydration.
- [`audit_ct105.sh`](../../infra/lxc/ct-105-adguard-dmz/audit_ct105.sh) — post-apply
  health/audit script the agent runs to populate the signed audit log.

The Proxmox adapter's job is to take `ct.yaml` and:

1. POST `/api2/json/nodes/n305/lxc` to create the CT.
2. POST `/api2/json/nodes/n305/lxc/105/firewall/options` for per-CT firewall.
3. POST `/api2/json/nodes/n305/lxc/105/status/start`.
4. Render `compose.yaml` via `pct exec` (this is HTTPS API too —
   Proxmox VE exposes `pct exec` over the API).
5. Run `audit_ct105.sh` and capture stdout/stderr into the audit log.

No SSH at any point.

### 2.4 PR4 — reverse proxy

Add a vhost block to [`infra/caddy/Caddyfile.j2`](../../infra/caddy/Caddyfile.j2):

```caddyfile
adguard.{$TAILNET}.ts.net {
    @authorized remote_ip 100.64.0.0/10
    handle @authorized {
        reverse_proxy 192.168.25.10:80
    }
    respond 403
}
```

The `remote_ip` ACL pins access to the Tailscale CGNAT range, so even
if the LAN ever reaches Caddy directly the request is rejected.

### 2.5 PR5 — anonymizer rules

Add entries in [`tools/anonymizer/rules.yaml`](../../tools/anonymizer/rules.yaml)
matching the formats AdGuard exports (query log JSON, blocklist URL
list). Add a `format_hooks` entry only if the format isn't covered by
the generic regex pass — and remember the **closed dispatch table** in
[`tools/anonymizer/anonymize.py`](../../tools/anonymizer/anonymize.py)
(`_load_static_hooks`) requires a source-code edit too.

---

## 3. The apply path — what happens after merge

```text
GitHub master                                       fortress-agent (CT-104)
     │                                                       │
     │  PR3 merged with `apply:approved` label               │
     │  apply-trigger.yml emits signed webhook               │
     │ ────────────────────────────────────────────────────▶ │
     │                                                       │ AWAIT_TOTP
     │                                                       │ (10-min window)
     │  user POSTs TOTP via ratchet CLI                      │
     │ ────────────────────────────────────────────────────▶ │
     │                                                       │ STAGE
     │                                                       │   ↓
     │                                                       │ rehydrate
     │                                                       │ (anonmap.json)
     │                                                       │   ↓
     │                                                       │ adapter.stage()
     │                                                       │   • schema check
     │                                                       │   • opa eval
     │                                                       │   ↓
     │                                                       │ adapter.backup()
     │                                                       │   ↓
     │                                                       │ adapter.apply()
     │                                                       │   • Proxmox API calls
     │                                                       │   ↓
     │                                                       │ audit_ct105.sh
     │                                                       │   ↓
     │  signed audit log pushed to audit/agent-log/          │
     │ ◀──────────────────────────────────────────────────── │ IDLE
```

If `audit_ct105.sh` exits non-zero or any step fails, the agent
auto-rollbacks via `adapter.rollback()` (snapshot restore for Proxmox,
config restore for OPNsense, transaction-rollback for Omada) and the
component never reaches `IDLE`.

---

## 4. Token / secret management

Per-target tokens live in `/run/fortress/api-tokens/` on **tmpfs**
inside CT-104. They are never written to disk in cleartext. The
encrypted bundle (`anonmap.age` + tokens) is loaded at boot only after
TOTP unlock.

| Token                    | Scope                                          | Rotation                          |
| ------------------------ | ---------------------------------------------- | --------------------------------- |
| `pve-n95-pull`           | `PVEAuditor` on `/nodes/n95`                   | 90 d via `rotate-secrets.md`      |
| `pve-n95-apply`          | `PVEVMAdmin` + `PVESDNAdmin` on `/nodes/n95`   | 30 d                              |
| `pve-n305-pull`          | `PVEAuditor` on `/nodes/n305`                  | 90 d                              |
| `pve-n305-apply`         | `PVEVMAdmin` + `PVESDNAdmin` on `/nodes/n305`  | 30 d                              |
| `opnsense-pull`          | `Diagnostics` API role                         | 90 d                              |
| `opnsense-apply`         | `Firewall + Interfaces + DHCP + Unbound` role  | 30 d                              |
| `omada-pull`             | `Viewer` OpenAPI role                          | 90 d                              |
| `omada-apply`            | `Site Admin` OpenAPI role                      | 30 d                              |
| `FORTRESS_WEBHOOK_TOKEN` | HMAC key for the apply-trigger webhook         | 30 d (GitHub repo secret)         |

Pull-tokens are read-only; apply-tokens are only readable by the agent
after TOTP unlock. **No human ever copies an apply-token.** Rotation is
automated by the runbook [`rotate-secrets.md`](rotate-secrets.md).

---

## 5. Why not Terraform / OpenTofu?

You will see Terraform-shaped solutions for Proxmox (the
`bpg/proxmox` provider, formerly Telmate). Reasonable question.

We did **not** adopt Terraform here, for these reasons:

1. **No SSH path**. Most TF Proxmox modules require SSH for `qm` /
   `pct` operations. The remaining API-only path duplicates what
   `adapters/proxmox.py` already does in 200 lines of typed Python.
2. **Audit boundary**. Every apply must produce a signed audit
   artifact. That's a first-class concern in `adapters/base.py`. With
   Terraform we'd need to wrap `terraform apply` in the same audit
   harness — net zero saving.
3. **Anonymization round-trip**. `ct.yaml` uses `${PLACEHOLDER}` tokens
   that the agent rehydrates from `anonmap.json` at apply time. TF's
   variable model assumes secrets stay in `terraform.tfvars`, which
   would re-introduce the very problem the anonymizer exists to
   prevent.
4. **OPA before apply**. Each adapter's `stage()` calls into the OPA
   policy bundle in [`infra/policies/`](../../infra/policies/) before
   any state change. Wrapping TF in OPA is doable but adds a layer.
5. **Rollback semantics**. TF's "destroy" is not what we want when an
   apply fails — we want a snapshot restore. Custom adapter wins.

**`compose.yaml` *is* the IaC for the application layer.** The CT itself
is described by `ct.yaml`. Both are declarative, both are linted, both
are diff-able in PR review. We just don't pay for HCL on top.

If a future component genuinely needs TF (e.g., a cloud target outside
the homelab), it lands as a *new adapter* (`adapters/aws.py`) and
follows the same `stage / backup / apply / rollback / audit` shape.

---

## 6. Pre-flight checklist for the maintainer

Before opening PR3 (the LXC delta, the one that actually creates a
container):

- [ ] PR1 (design bible) merged. Threat-model row added.
- [ ] PR2 (network) merged and applied; `vmbr2`/`vlan_dmz` exists on N305 and OPNsense.
- [ ] `ct.yaml` lints (`yamllint -c .yamllint`).
- [ ] `compose.yaml` lints (`docker compose -f compose.yaml config -q`, run in sandbox).
- [ ] `audit_ct<NNN>.sh` runs cleanly against a throwaway CT in the sandbox (does not depend on prod state).
- [ ] OPA bundle in `infra/policies/` updated to allow VMID NNN on the chosen node.
- [ ] Snyk + Trivy CI green.
- [ ] `apply:approved` label applied **only after** all the above.

---

## 7. Where to put each kind of file

| File kind                  | Path                                                                                                            |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Architecture / threat-mdl  | `docs/architecture/`, `docs/threat-model/`                                                                      |
| Component bible            | `docs/research/NN-<comp>-bible.md`                                                                              |
| OPNsense delta             | `infra/opnsense/deltas/YYYY-MM-DD-<scope>.xml.j2`                                                               |
| Proxmox export (anon'd)    | `infra/proxmox/<host>/exports/`                                                                                 |
| LXC component              | `infra/lxc/ct-NNN-<comp>/{ct.yaml,compose.yaml,audit_*.sh}`                                                     |
| Caddy vhost                | edit `infra/caddy/Caddyfile.j2`                                                                                 |
| Omada delta                | `infra/omada/deltas/YYYY-MM-DD-<scope>.json`                                                                    |
| Anonymizer rule            | edit `tools/anonymizer/rules.yaml`                                                                              |
| Format hook (rare)         | `tools/anonymizer/format_hooks/<name>.py` + register in `_load_static_hooks` in `tools/anonymizer/anonymize.py` |
| Apply runbook entry        | `docs/runbooks/apply-<target>.md` (link the new component)                                                      |

---

## 8. References

- [`docs/architecture/2.0-fortress-design.md`](../architecture/2.0-fortress-design.md) — system-level design + the 14-section roadmap this runbook implements.
- [`docs/architecture/01-anonymization-pipeline.md`](../architecture/01-anonymization-pipeline.md) — how anonymization + rehydration interact at apply time.
- [`docs/architecture/02-sync-workflow.md`](../architecture/02-sync-workflow.md) — pull/apply transports T1–T5.
- [`docs/runbooks/01-branch-and-diary.md`](01-branch-and-diary.md) — branching/diary discipline.
- [`docs/runbooks/02-sandbox-bootstrap.md`](02-sandbox-bootstrap.md) — local sandbox so you never test against prod.
- [`docs/runbooks/apply-proxmox.md`](apply-proxmox.md), [`apply-opnsense.md`](apply-opnsense.md), [`apply-omada.md`](apply-omada.md) — per-target apply runbooks.
- [`docs/runbooks/rotate-secrets.md`](rotate-secrets.md), [`break-glass.md`](break-glass.md), [`recover-fortress-agent.md`](recover-fortress-agent.md) — operational backstops.
