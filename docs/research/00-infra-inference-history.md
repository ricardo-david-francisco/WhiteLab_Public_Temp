# Infrastructure Inference History

> **Superseded by [`01-infrastructure-bible.md`](01-infrastructure-bible.md).**
> The bible is the canonical, comprehensive synthesis (hardware, VLANs,
> switch ports, full OPNsense bible, Proxmox N95+N305 hardening, LXC
> bible incl. AdGuard DMZ jail, Caddy, Omada, printer, DNS, NAS,
> monitoring, incident register, master roadmap river-flow). This
> document is preserved as the initial, shorter inference snapshot.
>
> **Purpose.** Synthesized snapshot of everything that has been learned about
> the existing Home_Infra deployment from the previous private repo
> (`ricardo-david-francisco/Home_Infra`) and the long-form Gemini research
> chats kept under `.Gemini_Chats_Home_Infra/` (gitignored). This document
> is the *previous-project diary* that informs every IaC decision made in
> WhiteLab going forward.
>
> **Status.** Inferred from documentation and audit reports — not from a
> fresh live audit. Where the source documentation explicitly contradicts
> itself, both states are recorded and the *current* state is flagged.
>
> **Scope.** No secrets, MAC addresses, public IPs, Tailscale node IDs, or
> account names are reproduced here. Only architectural facts and design
> rationale.

---

## 1. Sources

| Source                                                               | Location                                                          | Role                                                                    |
| -------------------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `ricardo-david-francisco/Home_Infra` (private)                       | cloned out-of-tree to `$HOME/.cache/whitelab-research/Home_Infra` | NADD v1.6 master blueprint, As-Built configs, audit scripts and reports |
| `01_Gemini_Chats/` (24 markdown files, ~97k lines)                   | inside the cloned repo                                            | Chronological design discussions, decision rationale                    |
| `.Gemini_Chats_Home_Infra/` (8 .txt exports)                         | workspace root, gitignored                                        | User-supplied chat exports (overlap with `01_Gemini_Chats/`)            |
| `audit_n95_magnum.sh` / `audit_lxc100_magnum.sh` / `audit_secure.sh` | Home_Infra repo                                                   | Forensic audit scripts that produced the DNA reports referenced below   |

The cloned repo and the `.Gemini_Chats_Home_Infra/` folder are intentionally
**not** committed to WhiteLab — only this synthesized document is.

---

## 2. Design Philosophy (carried forward into WhiteLab)

- **Physical isolation + Zero Trust.** Default-deny everywhere. No VLAN
  trusts another VLAN. All inter-VLAN traffic is firewalled.
- **Management plane is a bunker.** OPNsense GUI is reachable only from
  the ADMIN VLAN; ADMIN itself has *no internet access*.
- **East-west blocked by default** via an RFC1918 alias on every internal
  interface (block private→private, then explicit allow).
- **SSH disabled** on every hardened node. Recovery is via the Proxmox
  host console (or the physical console) only.
- **Image baselines, not snowflakes.** Two reference templates:
  `IMG-DEB12-HARDENED-v1` (base) and `IMG-DEB12-DOCKER-v2` (production).
- **Defense-in-depth per node.** UFW (default deny) + Fail2Ban
  (systemd backend) + unattended-upgrades (auto-reboot 03:00–03:30) +
  kernel hardening (`dmesg_restrict=1`, `accept_redirects=0`,
  `kptr_restrict=2`, `unprivileged_bpf_disabled=1`).

---

## 3. Topology (current, as inferred)

> **Documentation drift caveat.** NADD v1.6 still describes OPNsense as
> running **bare-metal on the Topton N305**. Both the README's own ALERT
> banner and the `PARAMOUNT_-_Lobotomy` migration plan confirm the *current*
> state: **OPNsense is virtualized inside Proxmox VE on the N305** (VLAN
> 140 “PROXTER” for admin reach to the N305 Proxmox GUI). The bare-metal
> description is legacy.

### 3.1 Hardware

| Role                  | Device                                                             | Notes                           |
| --------------------- | ------------------------------------------------------------------ | ------------------------------- |
| Router host           | Topton N305 mini-PC (i3-N305, 16 GB DDR5, 2× Intel i226-V 2.5 GbE) | Proxmox host; OPNsense as VM    |
| App / controller host | N95 mini-PC (`pve-n95`)                                            | Proxmox host; LXC 100, LXC 101  |
| Core switch           | TP-Link Omada SG2008 (8× 1 GbE, managed)                           | Aggregation, VLAN enforcement   |
| Distribution switch   | TP-Link TL-SG108E (smart)                                          | Hallway; trunked from core      |
| Office edge           | Unmanaged PoE switch                                               | Hybrid port from hallway        |
| Wireless              | Omada EAP683 UR (living), EAP653 UR (garage, G.hn powerline)       | Wi-Fi 6                         |
| Future upgrade        | 2× Omada SG2210XMP-M2                                              | Planned 2.5 G full-PoE backbone |

### 3.2 VLAN map

| VLAN | Name       | Subnet                        | Purpose                               |
| ---- | ---------- | ----------------------------- | ------------------------------------- |
| 1    | Default    | —                             | Unused (safety)                       |
| 10   | MGMT       | 192.168.10.0/24               | Switches, APs, Omada controller       |
| 20   | SECURE     | 192.168.20.0/24               | Trusted clients                       |
| 30   | SERVERS    | 192.168.30.0/24               | NAS, homelab, Proxmox guest workloads |
| 40   | ADMIN      | 192.168.40.0/24               | OPNsense GUI bunker — *no internet*   |
| 50   | MEDIA      | 192.168.50.0/24               | TV, console, Cast/AirPlay             |
| 60   | QUARANTINE | 192.168.60.0/24               | Untrusted; DNS forced to 1.1.1.2      |
| 70   | IOT        | 192.168.70.0/24               | Smart-home; internet only, no LAN     |
| 80   | CAMERA     | 192.168.80.0/24               | Cloud cams; cloud-only egress         |
| 90   | GUEST      | 192.168.90.0/24               | Visitors; internet-only               |
| 120  | ESCAPE     | (escape hatch)                | Captive-portal-gated break-glass path |
| 140  | PROXTER    | (admin reach to N305 PVE GUI) | Admin → N305 Proxmox web UI           |
| 999  | BLACKHOLE  | —                             | PVID for unused/break-glass ports     |

### 3.3 Switch port logic (highlights)

- **SG2008 P1** — PVID 40 (ADMIN). Physical key to the OPNsense GUI.
- **SG2008 P2** — Trunk to OPNsense (all VLANs).
- **SG2008 P5** — Trunk to TL-SG108E (excludes VLAN 40 by design).
- **SG2008 P8** — Lifeboat profile “All” (untagged native), retained as a
  failsafe.
- **TL-SG108E P2** — Hybrid: PVID 20 untagged (office PC) + tagged 10/50/60/70/90
  for the office AP (single cable, two roles).
- **Break-glass path** — set port PVID to 999, manually NIC-tag VLAN 120,
  authenticate against the OPNsense captive portal as `breakglass`, then
  pinholes only allow reaching the Omada controller's specific ports.

### 3.4 Host & guest IP map (current target)

| Node                        | IP                                                      | Notes                                                |
| --------------------------- | ------------------------------------------------------- | ---------------------------------------------------- |
| OPNsense (admin GUI)        | 192.168.40.1                                            | only reachable from VLAN 40                          |
| Proxmox host (N95)          | 192.168.100.10                                          | `pve-n95` — `vmbr0` VLAN-aware, trunk                |
| Proxmox host (N305)         | 192.168.100.2 (post-migration) / VLAN 140 reach         | `pve-n305`, hosts OPNsense VM                        |
| LXC 100 — Tailscale + Caddy | 192.168.100.5 (current) → 192.168.10.5 (target on MGMT) | unprivileged, TUN passthrough                        |
| LXC 101 — Omada controller  | 192.168.10.13 (VLAN 10)                                 | Docker, Portainer **Agent**                          |
| LXC 102 — Management Hub    | (planned) 192.168.10.x                                  | Phase 1.4: split Portainer **Server** out of LXC 100 |
| Omada SG2008 (mgmt)         | 192.168.10.113                                          |                                                      |

---

## 4. Critical guest profiles (As-Built)

### 4.1 LXC 100 — Tailscale gateway + Caddy reverse proxy (Golden image)

- Debian 12, **unprivileged** (UID 0 inside → UID 100000 on host),
  `features: nesting=1`, 1 core / 512 MB / 4 GB rootfs, `onboot=1`.
- TUN passthrough required:

  ```ini
  lxc.cgroup2.devices.allow: c 10:200 rwm
  lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
  ```

- **Tailscale** in userspace networking; identity persisted in
  `/var/lib/tailscale/tailscaled.state`; unattended-upgrades extended via
  Site-Match origins (`pkgs.tailscale.com`, `dl.cloudsmith.io`) so
  Tailscale and Caddy patch automatically.
- **Caddy** binds 80/443 via `cap_net_bind_service` (no root).
- **Reverse-proxy upstreams (sanitized):**
  - `<gateway>.ts.net` (443) → `https://<pve-n95>:8006` (Proxmox GUI), TLS skip-verify.
  - `<gateway>.ts.net:8443` → `https://<omada>:8043` with `header_up Host {upstream_hostport}`.
  - `<gateway>.ts.net:9443` → `http://<portainer>:9000` (planned: move to LXC 102).
- **UFW:** default deny in / allow out; only 80/tcp, 443/tcp, 41641/udp, 22/tcp open (22 is a vestigial rule — SSH is masked).
- **SSH:** stopped, disabled and masked (both `ssh.socket` and `ssh.service`).

### 4.2 LXC 101 — Omada controller (Silver image, hardened)

- Debian 12, 2 cores / 3 GB / 16 GB, VLAN tag 10, bridge `vmbr0`.
- **Docker stack** (`/opt/stacks/container/compose.yaml`):
  - `mbentley/omada-controller:6.0`, `network_mode: host`,
    `stop_grace_period: 60s`, ports 8088/8043/8843/29810–29817,
    persistent volumes `./data` and `./logs`.
  - `portainer/agent:2.21.5` on 9001 (Agent only — no DB on this node).
- **Resilience fix:** `pct set 101 --startup order=2,up=10,down=120` —
  gives MongoDB 120 s on shutdown instead of Proxmox's default 60, which
  was corrupting the DB on host reboot.
- **DNS sovereignty fix:** `/etc/resolv.conf` hardcoded to MGMT gateway
  (`192.168.10.1`) to stop inheriting the Proxmox host's legacy DNS.
- Same UFW + Fail2Ban-systemd + unattended-upgrades baseline.

### 4.3 Proxmox host baseline (`pve-n95`, replicated for `pve-n305`)

- Free repo only (`pve-no-subscription`), enterprise repo disabled.
- `vmbr0` is **VLAN-aware** with `bridge-vids 2-4094` *and*
  `bridge-vlan-aware yes`. Both lines are mandatory — see §6.
- Cluster firewall enabled; alias `management_ips = 192.168.100.0/24`;
  Omada discovery/management ports 29810/29811–29814/29817 explicitly
  allowed from the controller's source subnet.
- 2FA (`/etc/pve/priv/tfa.cfg`) enforced for the GUI.
- Fail2Ban with the `proxmox` jail (filter: `pvedaemon` auth failures,
  systemd backend, 3 retries / 1 h ban).
- **Open issue (recorded):** SSH on the N95 host is currently
  *running* despite `PermitRootLogin yes` in config — the killswitch was
  never executed on the host. WhiteLab's IaC reorg must enforce it
  declaratively.

---

## 5. Reverse-proxy & remote-access topology

```text
Internet
   │
   └─ ISP modem ── WAN ── OPNsense (VM, on N305 Proxmox)
                                 │
                                 ├─ VLAN 10 MGMT  ─── Omada SG2008 ─── …
                                 ├─ VLAN 30 SERVERS
                                 ├─ VLAN 40 ADMIN  ──→ OPNsense GUI
                                 └─ …

Tailscale tailnet (whale-mulley.*)
   │
   └─ LXC 100 (subnet router + Caddy)
         │
         ├─→ Proxmox PVE GUI (N95 / N305)
         ├─→ Omada controller (LXC 101)
         └─→ Portainer (LXC 101 today; LXC 102 planned)
```

ACL principle (Phase 1.4 “golden ACLs”): the tailnet sees the gateway
node only; lateral movement to LXC 101 / future LXC 102 is permitted only
via Caddy's specific upstream pinholes, not raw L3.

---

## 6. Lessons learned (incidents & gotchas)

| Code                                        | Title                                                          | Lesson                                                                                                                                     |
| ------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **INC-LXC101-NET-01**                       | Omada controller could not see APs/switches                    | `vmbr0` needs **both** `bridge-vlan-aware yes` *and* `bridge-vids 2-4094`. Either alone is silently insufficient.                          |
| **MongoDB shutdown corruption**             | Random Omada DB damage on host reboot                          | Default Proxmox shutdown grace (60 s) < MongoDB commit time. Fix: `pct set ... --startup ... down=120`.                                    |
| **DNS poisoning of LXC 101**                | Container resolved via Proxmox host's legacy DNS               | Hardcode `/etc/resolv.conf` to MGMT gateway; do not rely on inherited DNS.                                                                 |
| **ARP shock after OPNsense virtualization** | Devices unreachable for ~10 min after the bare-metal→VM switch | Power-cycle the modem (60 s) **and** the core switch (10 s) immediately after cutover; consider MAC-cloning the old WAN MAC onto `vtnet0`. |
| **Static-mapping continuity**               | Switches/APs grabbing random IPs after restore                 | Audit `<staticmap>` entries in `config.xml` *before* migrating; screenshot lease tables as a fallback.                                     |
| **N305 CPU type**                           | OPNsense VM unstable / slow                                    | CPU type **must** be `host` (not `kvm64`) on N305.                                                                                         |
| **SSH “killswitch” not idempotent**         | Service revived after reboot                                   | Need to mask both `ssh.service` *and* `ssh.socket`; current N95 host shows the revival.                                                    |
| **Documentation drift**                     | NADD says “bare-metal OPNsense”                                | Truth is virtualized on N305 Proxmox since the “Lobotomy” migration. Treat NADD §2 as legacy.                                              |

---

## 7. Roadmap inherited from Home_Infra

1. **Phase 1.4 — Mesh split.** Move Portainer Server out of LXC 100 into a
   new LXC 102 “Management Hub”; mesh LXC 100/101/102 over Tailscale with
   per-node ACLs (no flat trust).
2. **AdGuard DMZ jail.** New `vmbr2` (no physical port) on the N305;
   AdGuard LXC pinned to a 192.168.20.0/24 DMZ; OPNsense `OPT1` is the
   only path in/out, with rules: allow DNS to anywhere, deny everything
   to LAN/firewall.
3. **N305 host hardening parity.** Reapply the N95 hardening recipe to the
   N305 host (kernel sysctls, Fail2Ban `proxmox` jail, cluster firewall
   aliases, 2FA). N305 is currently *less* hardened than N95.
4. **Switch refresh.** Replace SG2008 + TL-SG108E with 2× Omada
   SG2210XMP-M2 for full 2.5 G PoE backbone and single-pane Omada
   management (the TL-SG108E cannot be adopted today).
5. **Backup automation.** Scheduled, off-host backups of the Omada
   `data/` volume (currently only one-shot autobackup zips inside the
   container).
6. **Zenarmor / mDNS.** Activate Zenarmor on OPNsense; configure Avahi as
   an mDNS reflector between SECURE (20) and MEDIA (50).

---

## 8. How this informs WhiteLab IaC

- **Repo layout target:** one folder per device class —
  `infra/opnsense/`, `infra/proxmox-n305/`, `infra/proxmox-n95/`,
  `infra/omada/`, `infra/lxc/{100-gateway,101-omada,102-mgmt}/`.
- **Anonymizer must scrub:** IPv4, IPv6 (incl. Tailscale 100.64.0.0/10
  and `fd7a:115c:a1e0::/48`), MAC addresses, Tailscale node names,
  the `<gateway>.<tailnet>.ts.net` magic-DNS hostname, OPNsense
  `<staticmap>` entries (MAC + hostname pairs), passwords/keys/secrets,
  email addresses, and account names.
- **Two reference base images** to be modeled as Packer or
  cloud-init templates: `IMG-DEB12-HARDENED-v1` and `IMG-DEB12-DOCKER-v2`.
- **Per-LXC declarative spec** (Terraform `bpg/proxmox` provider) must
  emit the `lxc.cgroup2.devices.allow` / `lxc.mount.entry` lines for
  TUN passthrough and the `--startup order=...,down=120` flag for any
  container running a stateful DB.
- **Pre-commit gate** must reject any file containing the literal
  Tailscale tailnet name, any MAC, or any 100.64.0.0/10 / 192.168.x.y
  address that is not on the explicit allowlist.

---

## 9. Provenance

- Cloned: `gh repo clone ricardo-david-francisco/Home_Infra` →
  `$HOME/.cache/whitelab-research/Home_Infra` (out-of-tree, never
  committed).
- Digest assembled by `.digest.sh` (gitignored) from the README plus
  seven key chats (Lobotomy, Zero Trust LXC 101, Omada/Proxmox setup,
  OPNsense deep research, Network Architecture Design Document, AdGuard
  vs Pi-hole, Network Migration Execution Checklist).
- Synthesis written for this branch: `feature/infra-research-import`.
- No file from `.Gemini_Chats_Home_Infra/` or the cloned repo is
  reproduced verbatim here; only architectural facts and decisions.
