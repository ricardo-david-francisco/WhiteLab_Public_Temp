# Infrastructure Bible — Home_Infra → WhiteLab

> **Purpose.** Single, comprehensive, river-flow knowledge base of the
> existing home infrastructure: hardware, VLANs, switch ports, OPNsense
> install + every firewall artefact, WireGuard plan, Proxmox host
> hardening (N95 + N305), LXC containers (100 gateway, 101 Omada, 102
> planned, AdGuard DMZ), Caddy reverse proxy, Omada controller, printer
> placement, DNS/AdGuard strategy, NAS plan, monitoring, incidents and
> the chronological roadmap. This document supersedes
> `00-infra-inference-history.md` as the canonical synthesis and is the
> design rationale for every IaC change made in WhiteLab going forward.
>
> **Status.** Synthesized from the cloned `Home_Infra` repo (24 Gemini
> chat exports under `01_Gemini_Chats/`, ~97k lines) and the seven
> long-form chat exports under `.Gemini_Chats_Home_Infra/` in this
> workspace (~28k lines). Both sources are gitignored; only this
> sanitized synthesis is committed. Numeric values, ports, VLAN IDs,
> file paths and configuration keys are preserved. MAC addresses,
> personal account names, public IPs, Tailscale node IDs and passwords
> are replaced with placeholders.
>
> **How to read this document.** §1 is the executive summary. §2–§4 are
> the physical/L2 facts (hardware, VLANs, switch ports). §5 is the
> OPNsense bible (install procedure, interfaces, aliases, every firewall
> rule, DHCP, DNS, services, VPN, hardening, backup). §6 is the Proxmox
> bible (N95 source-of-truth + N305 hardening parity). §7 is the LXC
> bible (golden images, LXC 100/101/102, AdGuard DMZ). §8 is the
> reverse-proxy / remote-access bible. §9 is the Omada controller
> bible. §10–§13 are the smaller component bibles (printer, DNS,
> NAS, monitoring). §14 is the incident register. §15 is the master
> roadmap river-flow (chronological narrative). §16 is the WhiteLab
> IaC implication list. §17 is the anonymizer scrub list.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Hardware & physical topology](#2-hardware--physical-topology)
3. [VLAN bible](#3-vlan-bible)
4. [Switch port matrix](#4-switch-port-matrix)
5. [OPNsense bible](#5-opnsense-bible)
6. [Proxmox host bible (N95 + N305)](#6-proxmox-host-bible-n95--n305)
7. [LXC bible](#7-lxc-bible)
8. [Reverse proxy & remote-access bible](#8-reverse-proxy--remote-access-bible)
9. [Omada controller bible](#9-omada-controller-bible)
10. [Printer bible (Brother MFC-J5320DW)](#10-printer-bible-brother-mfc-j5320dw)
11. [DNS / AdGuard bible](#11-dns--adguard-bible)
12. [NAS bible (TerraMaster + unRAID)](#12-nas-bible-terramaster--unraid)
13. [Monitoring stack](#13-monitoring-stack)
14. [Incident register](#14-incident-register)
15. [Master roadmap river-flow](#15-master-roadmap-river-flow)
16. [WhiteLab IaC implications](#16-whitelab-iac-implications)
17. [Anonymizer scrub list](#17-anonymizer-scrub-list)
18. [Provenance](#18-provenance)

---

## 1. Executive summary

The deployment is a Zero-Trust home network anchored on a virtualized
OPNsense firewall running inside Proxmox VE on a fanless Topton N305
appliance. A second Proxmox node (N95) acts as the source-of-truth for
host hardening recipes and runs the management LXCs (Tailscale + Caddy
gateway, Omada controller). Everything is segmented across 15 VLANs
terminated as virtual interfaces on OPNsense (`opt1`–`opt15`), with
inter-VLAN traffic default-denied and egress allowed selectively. Layer
2 is provided by an Omada SG2008 + TL-SG108E pair (planned upgrade to
two SG2210XMP-M2) controlled by a self-hosted Omada Controller v6 in
LXC 101. Remote access is exclusively via Tailscale terminating in an
unprivileged LXC 100 that fronts Proxmox/Omada/Portainer through Caddy.
DNS is being moved out of OPNsense Unbound into a dedicated AdGuard
Home jail on `vmbr2` (no physical port) with Cloudflare 1.1.1.2
(malware-blocking) upstream, with Unbound retained as failover.

The unifying design principle, repeated across every chat export, is
**"the firewall is the only authority"**: no DHCP on the switches, no
inter-VLAN routing on the L2 fabric, no shared L3 anywhere except the
OPNsense interfaces themselves. Every other component is a guest of
that authority.

---

## 2. Hardware & physical topology

### 2.1 Hosts

| Role                  | Box                              | CPU           | NICs                          | Notes                                                                                                                                        |
| --------------------- | -------------------------------- | ------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary firewall      | Topton fanless N305              | Intel N305    | 4× Intel i226-V 2.5GbE        | Runs Proxmox + OPNsense VM 100 + AdGuard DMZ jail. Mandatory CPU type `host` for VirtIO/AES-NI.                                              |
| Mgmt + LXC node       | Topton/equivalent N95            | Intel N95     | (per box)                     | Runs Proxmox `pve-n95` (PVE 9.1.4 / kernel 6.17.4-2-pve), 7.5 GiB RAM, hosts LXC 100 + LXC 101 today. Source-of-truth for hardening recipes. |
| L2 core               | Omada SG2008 (8-port)            | —             | 8× 1GbE                       | Trunk + access, web-managed via Omada Controller.                                                                                            |
| L2 access             | TP-Link TL-SG108E (8-port)       | —             | 8× 1GbE                       | EasySmart sibling, also adopted into Omada.                                                                                                  |
| Wi-Fi                 | TP-Link Omada EAP683 LR + EAP653 | —             | Wi-Fi 6                       | SSID-to-VLAN mapping defined in §9.4.                                                                                                        |
| Powerline backhaul    | TP-Link G.hn pair                | —             | 1GbE (~1Gbit headline)        | Carries tagged VLAN traffic transparently between rooms.                                                                                     |
| NAS (planned)         | TerraMaster 4-bay                | —             | 1GbE                          | unRAID OS, RAM-cached HDDs, see §12.                                                                                                         |
| Printer               | Brother MFC-J5320DW              | —             | 1GbE                          | VLAN 50 MEDIA, see §10.                                                                                                                      |

### 2.2 Planned / future hardware

* **2× TP-Link Omada SG2210XMP-M2** — replaces SG2008 + TL-SG108E. 2.5 GbE access + 10 GbE uplinks; lifts the gigabit ceiling that currently caps the NAS plan.
* **More RAM for the NAS** — required before any meaningful RAM-cache speedup of the old Western Digital HDDs.

### 2.3 Cabling logic

* Modem → N305 WAN port (`enp3s0` / passed through to OPNsense `vtnet0` via `vmbr1`).
* N305 LAN port (`enp2s0`) → SG2008 trunk port (PVID 100, tagged 10/20/30/40/90/etc.).
* SG2008 → TL-SG108E (uplink trunk).
* SG2008 → G.hn powerline pair → far-room SG108E or AP.
* APs (EAP683/EAP653) connect to access ports configured for the management VLAN with SSIDs broadcasting tagged VLANs.

---

## 3. VLAN bible

### 3.1 Master schema

| ID    | Name           | Subnet             | Gateway            | DHCP range                            | DNS                 | OPNsense iface   | Omada wired-network purpose                                                               |
| ----- | -------------- | ------------------ | ------------------ | ------------------------------------- | ------------------- | ---------------- | ----------------------------------------------------------------------------------------- |
| 1     | DEFAULT/LAN    | 192.168.1.0/24     | 192.168.1.1        | 192.168.1.100–199                     | OPNsense Unbound    | `lan` (vtnet1)   | Unused for clients; reserve.                                                              |
| 10    | MGMT           | 192.168.10.0/24    | 192.168.10.1       | 192.168.10.100–200                    | OPNsense Unbound    | `opt1` vlan01    | Network infrastructure (switches, APs, Omada Controller LXC, MGMT-tagged NIC of LXC 100). |
| 20    | SECURE         | 192.168.20.0/24    | 192.168.20.1       | 192.168.20.100–200                    | OPNsense Unbound    | `opt2` vlan02    | Trusted laptops, PCs, sysadmin phone.                                                     |
| 30    | SERVERS        | 192.168.30.0/24    | 192.168.30.1       | 192.168.30.100–200                    | OPNsense Unbound    | `opt3` vlan03    | Internal services, NAS, homelab compute.                                                  |
| 40    | ADMIN          | 192.168.40.0/24    | 192.168.40.1       | 192.168.40.100–200                    | OPNsense Unbound    | `opt8` vlan08    | Air-gapped admin VLAN — only VLAN with OPNsense GUI access. No internet.                  |
| 50    | MEDIA          | 192.168.50.0/24    | 192.168.50.1       | 192.168.50.100–200                    | OPNsense Unbound    | `opt9` vlan09    | TVs, Xbox, speakers, Brother MFC-J5320DW printer.                                         |
| 60    | QUARANTINE     | 192.168.60.0/24    | 192.168.60.1       | 192.168.60.100–200                    | **Forced 1.1.1.2**  | `opt6` vlan06    | Untrusted/infected/unknown devices, force-DNS to Cloudflare malware-blocking.             |
| 70    | IOT            | 192.168.70.0/24    | 192.168.70.1       | 192.168.70.100–200                    | OPNsense Unbound    | `opt4` vlan04    | Smart home — internet only, LAN blocked.                                                  |
| 80    | CAMERA         | 192.168.80.0/24    | 192.168.80.1       | 192.168.80.100–200                    | OPNsense Unbound    | `opt5` vlan05    | Cloud cameras — cloud-only egress, no LAN.                                                |
| 90    | GUEST          | 192.168.90.0/24    | 192.168.90.1       | 192.168.90.100–200                    | OPNsense Unbound    | `opt7` vlan07    | Visitor Wi-Fi — internet only, total isolation.                                           |
| 100   | PROXMOX        | 192.168.100.0/24   | 192.168.100.1      | 192.168.100.100–200                   | OPNsense Unbound    | `opt10` vlan010  | Hypervisor management LAN (Proxmox GUI/SSH on N305 .2 and N95 .10).                       |
| 110   | SERVICES       | 192.168.110.0/24   | 192.168.110.1      | 192.168.110.100–200                   | OPNsense Unbound    | `opt11` vlan011  | Docker workloads (Immich, Seafile, future apps).                                          |
| 120   | ESCAPE         | 192.168.120.0/24   | 192.168.120.1      | 192.168.120.100–200                   | OPNsense Unbound    | `opt12` vlan012  | **Break-glass.** Captive portal, single concurrent login, sysadmin SSH source net.        |
| 130   | KIDS           | 192.168.1.130/24   | 192.168.1.130      | (none)                                | OPNsense Unbound    | `opt13` vlan015  | Reserved for parental-controlled devices (currently unconfigured DHCP).                   |
| 140   | PROXTER        | 192.168.140.0/24   | 192.168.140.1      | 192.168.140.100–200                   | OPNsense Unbound    | `opt14` vlan013  | Proxmox-host-side test/staging interface.                                                 |
| 150   | EMPLOYER       | 192.168.150.0/24   | 192.168.150.1      | 192.168.150.100–200                   | OPNsense Unbound    | `opt15` vlan014  | Employer-managed laptop. Print-only access to MEDIA printer; otherwise isolated.          |
| 999   | BLACKHOLE      | (none)             | (none)             | (none)                                | (none)              | n/a              | PVID for unused/disabled access ports. No L3 anywhere.                                    |

### 3.2 Inter-VLAN policy summary

* Default deny between any two non-adjacent VLANs.
* `40_ADMIN` is the only VLAN allowed to reach the OPNsense WebGUI (port 443). It is denied internet egress.
* `60_QUARANTINE` is denied reaching the firewall login page and the entire RFC1918 space; egress is allowed only to the internet, with DNS forced to 1.1.1.2 / 1.0.0.2 (Cloudflare malware-blocking) at the firewall layer.
* `70_IOT`, `80_CAMERA`, `90_GUEST` are denied RFC1918 and allowed `!RFC1918_PRIVATE` (internet only).
* `100_PROXMOX` and `10_MGMT` are mutually isolated except for Tailscale node `192.168.10.5` → `opt10` on `Proxmox_Mgmt_Ports` (SSH 22, GUI 8006).
* `120_ESCAPE` has explicit allow-list to Omada Controller (`192.168.10.13`) on 8043, 8088, 9000, 22 — and nothing else.
* `150_EMPLOYER` is isolated from all internal VLANs except a planned print-only allow rule to `MEDIA_PRINTER_IP` on TCP 631 (IPP).

---

## 4. Switch port matrix

The matrix below is the *current* (legacy SG2008 + TL-SG108E) layout
recovered from the Lobotomy and Migration chats. Every port has a
PVID (untagged VLAN) and an explicit tagged-VLAN list. Powerline G.hn
adapters are transparent and pass tagged frames unchanged.

### 4.1 Omada SG2008 (core)

| Port   | Role                         | PVID   | Tagged VLANs                                           | Connected device                                                          |
| ------ | ---------------------------- | ------ | ------------------------------------------------------ | ------------------------------------------------------------------------- |
| 1      | Uplink to N305 (LAN port)    | 100    | 10, 20, 30, 40, 50, 60, 70, 80, 90, 110, 120, 140, 150 | Proxmox `vmbr0` (VLAN-aware), trunks all VLANs into the OPNsense LAN NIC. |
| 2      | Uplink to TL-SG108E          | 100    | 10, 20, 30, 50, 70, 80, 90, 120                        | Inter-switch trunk.                                                       |
| 3      | AP EAP683 LR                 | 10     | 20, 50, 70, 80, 90, 130                                | Tagged SSIDs map to client VLANs; AP itself sits on MGMT 10.              |
| 4      | AP EAP653                    | 10     | 20, 50, 70, 80, 90                                     | Secondary AP.                                                             |
| 5      | N95 mgmt port                | 100    | 10, 20, 30, 40, 50, 90, 110                            | `vmbr0` of `pve-n95` (also VLAN-aware).                                   |
| 6      | Wired desktop (SECURE)       | 20     | (none)                                                 | Access port.                                                              |
| 7      | G.hn powerline → far room    | 1      | 10, 20, 50, 70                                         | Trunk; far-end TL-SG108E or in-room AP.                                   |
| 8      | **Lifeboat**                 | 1      | All VLANs                                              | Profile "All" — emergency console-laptop port. Used for break-glass.      |

### 4.2 TP-Link TL-SG108E (access)

| Port   | Role                         | PVID           | Tagged VLANs                       | Notes                                                              |
| ------ | ---------------------------- | -------------- | ---------------------------------- | ------------------------------------------------------------------ |
| 1      | Uplink from SG2008           | 100            | 10, 20, 30, 50, 70, 80, 90, 120    |                                                                    |
| 2–6    | Access ports                 | 20 (default)   | (none)                             | Assignable per device.                                             |
| 7      | Hybrid office port           | 20             | 30, 50                             | Workstation needs SECURE access + occasional SERVERS / MEDIA.      |
| 8      | Reserved (BLACKHOLE)         | 999            | (none)                             | Disabled/unused.                                                   |

### 4.3 Future: 2× SG2210XMP-M2

* Same logical layout, but uplinks promote to 10 GbE and access ports promote to 2.5 GbE.
* Adoption sequence per Omada Controller: factory reset → power on first switch → adopt → push port profile → power on second switch → adopt → push port profile → label and rack.
* Migration from existing fabric is documented in §15 (river-flow).

---

## 5. OPNsense bible

This is the single largest section of the document because OPNsense is
the only authority enforcing the Zero-Trust model.

### 5.1 Installation on Proxmox N305 (the "Lobotomy" procedure)

**Why the name.** The procedure migrates an existing **bare-metal**
OPNsense install on the N305 into a virtualized OPNsense VM running on
Proxmox on the **same** hardware. The bare-metal install is wiped
("lobotomy") and the saved `config.xml` is restored into the VM. Done
without secondary hardware, it must succeed on the first boot or the
LAN goes dark.

**Pre-flight (Phase 0 — Lifeboat USB).**

* Two USB sticks: (a) Proxmox VE 8.x installer, (b) "Nuclear" OPNsense bare-metal ISO for 15-minute rollback.
* `config.xml` exported from running OPNsense (System → Configuration → Backups → Download).
* Screenshots of all current DHCP leases (so static-MAC → IP mappings can be re-verified).
* Laptop pre-configured with static IP recovery profile: `192.168.100.99/24`, gateway `192.168.100.1` (post-migration target) or `192.168.1.1` (current).
* Modem and switches scheduled for a window where 5–10 minutes of downtime is acceptable.

**BIOS / boot.**

* F7 or Del at POST → boot menu.
* Disable Secure Boot for the duration of the install (re-enable after).
* CPU virtualization (VT-x, VT-d) enabled.
* USB selected with UEFI flag.

**Phase 1 — install Proxmox.**

* Target disk: NVMe (`/dev/nvme0n1`). ext4 acceptable for single-disk; ZFS RAID0 acceptable. Wipes the old OPNsense bare-metal install.
* Hostname: `pve-n305.lan`.
* Management IP: `192.168.100.2/24`.
* Gateway: `192.168.100.1` (the *future* OPNsense VM IP).
* DNS: `1.1.1.1` for install only; replaced later.
* Root password: strong, stored in vault.
* Email: required by installer; use sysadmin alias.

**Phase 2 — host hardening.** See §6.

**Phase 3 — network surgery (`/etc/network/interfaces`).**

```bash
auto lo
iface lo inet loopback

# Physical ports (manual / no IP).
iface enp3s0 inet manual            # WAN — passed through to OPNsense via vmbr1
iface enp2s0 inet manual            # LAN — VLAN trunk to switch via vmbr0

# LAN bridge — VLAN-aware so OPNsense and any LXC can pick up tagged VLANs.
auto vmbr0
iface vmbr0 inet static
    address 192.168.100.2/24
    gateway 192.168.100.1
    bridge-ports enp2s0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094              # CRITICAL — without this, tagged frames are dropped.

# WAN bridge — bridge-only, no IP, OPNsense owns it.
auto vmbr1
iface vmbr1 inet manual
    bridge-ports enp3s0
    bridge-stp off
    bridge-fd 0

# DMZ bridge — no physical port; isolated network for AdGuard jail.
auto vmbr2
iface vmbr2 inet manual
    bridge-ports none
    bridge-stp off
    bridge-fd 0
    # comment "Digital Jail"
```

Apply with `ifreload -a`. Brief LAN drop expected.

**Phase 4 — create OPNsense VM (VMID 100).**

* Name: `OPNsense`.
* CPU type: `host` (mandatory — `kvm64` produces hangs on N305).
* vCPU: 4. RAM: 8192 MiB, ballooning unchecked.
* Disk: VirtIO Block, 32 GiB minimum, on `local-lvm`.
* BIOS: SeaBIOS or UEFI (default acceptable). Machine type: `q35`.
* QEMU Guest Agent: enabled.
* Start at boot: enabled.
* Network 0 (WAN): `vmbr1`, VirtIO, **firewall flag off** at the Proxmox layer.
* Network 1 (LAN): `vmbr0`, VirtIO, firewall flag off.
* Network 2 (DMZ): `vmbr2`, VirtIO, firewall flag off (optional, used by AdGuard jail).
* ISO upload via Proxmox GUI; install OPNsense to virtual disk (UFS or ZFS both acceptable). Default credentials: `installer` / `opnsense`.

**Phase 5 — interface assignment.**

* On first boot the OPNsense console reports an "Interface Mismatch" because the saved `config.xml` references the bare-metal NIC names `igc0` / `igc1`.
* Console option `1) Assign Interfaces` → VLANs? `n` → WAN: `vtnet0` → LAN: `vtnet1` → optional `vtnet2` for DMZ → confirm `y`.

**Phase 6 — restore `config.xml`.**

* Browse to `https://192.168.100.1` from a laptop on `192.168.100.99/24`.
* Login `root` / `opnsense` (default).
* System → Configuration → Backups → Restore → upload `config.xml`, area `All`, click `Restore Configuration`. VM reboots.
* Re-run interface assignment (the mismatch repeats once after restore — accept the new vtnet mapping).
* Open `config.xml` in a text editor on the laptop and grep for `<staticmap>`; verify every critical device (Omada Controller, AP, NAS, sysadmin laptop, printer) has its `<mac>` and `<ipaddr>` present. If a dynamic lease was never converted to static, do it before powering up the switch.

**Phase 7 — ARP shock & MAC clone fallback.**

* Symptom: WAN shows `0.0.0.0` or `Pending` — the ISP modem has cached the previous (bare-metal NIC) MAC against the DHCP lease.
* Recovery: power off modem 60 s, switch 10 s, AP soft-reboot. Wait 5–10 minutes for ARP cache expiration on every device.
* If still pending: System → Interfaces → WAN → MAC Address → paste the *old* physical MAC, save, apply, reconnect modem.

**Phase 8 — lockdown.**

* Re-enable SSH killswitch on the Proxmox host (see §6).
* Confirm 2FA on the OPNsense root account (recommended) and the Proxmox `sysadmin` account.
* Take a fresh backup through the GUI.
* Delete the laptop's static-IP recovery profile.

### 5.2 Interfaces (assignments)

| Iface    | Parent    | Tag   | IPv4                                               | IPv6                           | Description                          |
| -------- | --------- | ----- | -------------------------------------------------- | ------------------------------ | ------------------------------------ |
| WAN      | vtnet0    | —     | DHCP                                               | DHCPv6                         | WAN, block private + bogons enabled. |
| LAN      | vtnet1    | —     | 192.168.1.1/24                                     | track6 from WAN, prefix-id 0   | Default LAN; reserved.               |
| opt1     | vtnet1    | 10    | 192.168.10.1/24                                    | (track from WAN if needed)     | 10_MGMT                              |
| opt2     | vtnet1    | 20    | 192.168.20.1/24                                    | —                              | 20_SECURE                            |
| opt3     | vtnet1    | 30    | 192.168.30.1/24                                    | —                              | 30_SERVERS                           |
| opt4     | vtnet1    | 70    | 192.168.70.1/24                                    | —                              | 70_IOT                               |
| opt5     | vtnet1    | 80    | 192.168.80.1/24                                    | —                              | 80_CAMERA                            |
| opt6     | vtnet1    | 60    | 192.168.60.1/24                                    | —                              | 60_QUARANTINE                        |
| opt7     | vtnet1    | 90    | 192.168.90.1/24                                    | —                              | 90_GUEST                             |
| opt8     | vtnet1    | 40    | 192.168.40.1/24                                    | —                              | 40_ADMIN                             |
| opt9     | vtnet1    | 50    | 192.168.50.1/24                                    | —                              | 50_MEDIA                             |
| opt10    | vtnet1    | 100   | 192.168.100.1/24                                   | —                              | 100_PROXMOX                          |
| opt11    | vtnet1    | 110   | 192.168.110.1/24                                   | —                              | 110_SERVICES                         |
| opt12    | vtnet1    | 120   | 192.168.120.1/24                                   | —                              | 120_ESCAPE                           |
| opt13    | vtnet1    | 130   | 192.168.1.130/24                                   | —                              | 130_KIDS (planned)                   |
| opt14    | vtnet1    | 140   | 192.168.140.1/24                                   | —                              | 140_PROXTER                          |
| opt15    | vtnet1    | 150   | 192.168.150.1/24                                   | —                              | 150_EMPLOYER                         |
| opt2-DMZ | vtnet2    | —     | 192.168.20.1/24 (planned, see §11.2 conflict note) | —                              | AdGuard jail (vmbr2).                |

Note: VLAN `20_SECURE` and the planned AdGuard DMZ subnet currently
collide on `192.168.20.0/24` in the source chats. Action item recorded
in §16: choose a non-conflicting subnet for the DMZ (e.g.
`192.168.25.0/24`) before deployment.

### 5.3 Aliases

**Network aliases.**

| Name                | Type      | Contents                                                           | Purpose                                                       |
| ------------------- | --------- | ------------------------------------------------------------------ | ------------------------------------------------------------- |
| `RFC1918_PRIVATE`   | network   | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`                    | Master block list for "no internal-to-internal traffic".      |
| `MGMT_NETS`         | network   | `192.168.10.0/24`, `192.168.40.0/24`, `192.168.120.0/24`           | Allow-source for OPNsense GUI access (planned).               |
| `OMADA_CONTROLLER`  | host      | `192.168.10.13`                                                    | Omada controller LXC IP.                                      |
| `MEDIA_PRINTER`     | host      | (Brother MFC-J5320DW static-DHCP IP, planned in §10)               | Print-only allow target from VLAN 20 / 50 / 150.              |
| `TAILSCALE_GW`      | host      | `192.168.10.5`                                                     | LXC 100 — only host allowed to reach Proxmox mgmt cross-VLAN. |

**Port aliases.**

| Name                     | Ports                         | Purpose                                                                   |
| ------------------------ | ----------------------------- | ------------------------------------------------------------------------- |
| `DNS_NTP_PORTS`          | 53, 123                       | DNS + NTP allow groups for trusted VLANs.                                 |
| `ADMIN_PORTS`            | 80, 443, 22                   | OPNsense WebGUI + admin SSH.                                              |
| `OMADA_CONTROL_PORTS`    | 8043, 29810:29814             | Omada controller management + adoption channel.                           |
| `OMADA_FULL_PORTS`       | 8088, 8043, 8843, 29810:29817 | Full Omada port range.                                                    |
| `PROXMOX_MGMT_PORTS`     | 22, 8006                      | Proxmox SSH + GUI.                                                        |
| `PRINT_IPP`              | 631                           | IPP-over-TCP for Brother printer (only port enabled after PCAP analysis). |
| `PRINT_LEGACY`           | 9100, 515                     | Raw + LPD; **planned to drop** if PCAP shows IPP-only.                    |

**URL-table aliases.** Reserved slot for a future GeoIP block list
sourced from MaxMind GeoLite2 (license key required, weekly refresh).

### 5.4 Firewall rules — every interface

Conventions: `pass`/`block` is the action; `quick` means stop on match
(OPNsense default for user rules); rules within an interface are listed
top-to-bottom. "Temp Migration Access" rules are explicitly marked
because they exist only during the migration window and must be deleted
in Phase 8.

#### 5.4.1 LAN (default LAN, reserved)

| #   | Action   | Proto   | Source         | Destination   | Port   | Description         |
| --- | -------- | ------- | -------------- | ------------- | ------ | ------------------- |
| 1   | pass     | any     | lan net        | any           | —      | Default allow IPv4. |
| 2   | pass     | IPv6    | lan net        | any           | —      | Default allow IPv6. |

#### 5.4.2 opt1 — 10_MGMT

| #   | Action   | Proto   | Source               | Destination   | Port                 | Description                                            |
| --- | -------- | ------- | -------------------- | ------------- | -------------------- | ------------------------------------------------------ |
| 1   | pass     | any     | `192.168.10.6`       | any           | —                    | Force-allow Omada AP discovery during boot (priority). |
| 2   | pass     | any     | opt1 net             | any           | —                    | **Temp** migration.                                    |
| 3   | pass     | TCP     | `TAILSCALE_GW`       | opt10 net     | `PROXMOX_MGMT_PORTS` | Tailscale gateway → Proxmox.                           |
| 4   | block    | any     | opt1 net             | opt10 net     | —                    | Isolate MGMT from PROXMOX (after migration).           |

#### 5.4.3 opt2 — 20_SECURE

| #   | Action   | Proto      | Source     | Destination         | Port              | Description           |
| --- | -------- | ---------- | ---------- | ------------------- | ----------------- | --------------------- |
| 1   | pass     | any        | opt2 net   | any                 | —                 | **Temp** migration.   |
| 2   | pass     | TCP/UDP    | opt2 net   | (this firewall)     | `DNS_NTP_PORTS`   | DNS + NTP to gateway. |
| 3   | block    | any        | opt2 net   | `RFC1918_PRIVATE`   | —                 | No private→private.   |
| 4   | pass     | any        | opt2 net   | `!RFC1918_PRIVATE`  | —                 | Internet only.        |

#### 5.4.4 opt3 — 30_SERVERS

| #   | Action   | Proto   | Source   | Destination   | Port   | Description                                                                             |
| --- | -------- | ------- | -------- | ------------- | ------ | --------------------------------------------------------------------------------------- |
| 1   | pass     | any     | opt3 net | any           | —      | **Temp** migration. (Permanent rules to be authored when service inventory stabilizes.) |

#### 5.4.5 opt4 — 70_IOT

| #   | Action   | Proto   | Source   | Destination        | Port            | Description         |
| --- | -------- | ------- | -------- | ------------------ | --------------- | ------------------- |
| 1   | pass     | any     | opt4 net | any                | —               | **Temp** migration. |
| 2   | pass     | TCP/UDP | opt4 net | (this firewall)    | `DNS_NTP_PORTS` | DNS + NTP.          |
| 3   | block    | any     | opt4 net | `RFC1918_PRIVATE`  | —               | No private.         |
| 4   | pass     | any     | opt4 net | `!RFC1918_PRIVATE` | —               | Internet only.      |

#### 5.4.6 opt5 — 80_CAMERA

| #   | Action   | Proto   | Source   | Destination        | Port            | Description                                                          |
| --- | -------- | ------- | -------- | ------------------ | --------------- | -------------------------------------------------------------------- |
| 1   | pass     | any     | opt5 net | any                | —               | **Temp** migration.                                                  |
| 2   | pass     | TCP/UDP | opt5 net | (this firewall)    | `DNS_NTP_PORTS` | DNS + NTP.                                                           |
| 3   | block    | any     | opt5 net | `RFC1918_PRIVATE`  | —               | No private.                                                          |
| 4   | pass     | any     | opt5 net | `!RFC1918_PRIVATE` | —               | Internet (cloud-only egress). Tag category: "Allow Internet Access". |

#### 5.4.7 opt6 — 60_QUARANTINE

| #   | Action   | Proto   | Source   | Destination        | Port   | Description                     |
| --- | -------- | ------- | -------- | ------------------ | ------ | ------------------------------- |
| 1   | pass     | any     | opt6 net | any                | —      | **Temp** migration.             |
| 2   | pass     | TCP/UDP | opt6 net | `1.1.1.2`          | 53     | Force DNS Cloudflare primary.   |
| 3   | pass     | TCP/UDP | opt6 net | `1.0.0.2`          | 53     | Force DNS Cloudflare secondary. |
| 4   | block    | any     | opt6 net | (this firewall)    | —      | Block router login.             |
| 5   | block    | any     | opt6 net | `RFC1918_PRIVATE`  | —      | Block home network.             |
| 6   | pass     | any     | opt6 net | `!RFC1918_PRIVATE` | —      | Internet only.                  |

#### 5.4.8 opt7 — 90_GUEST

| #   | Action   | Proto   | Source   | Destination        | Port            | Description         |
| --- | -------- | ------- | -------- | ------------------ | --------------- | ------------------- |
| 1   | pass     | any     | opt7 net | any                | —               | **Temp** migration. |
| 2   | pass     | TCP/UDP | opt7 net | (this firewall)    | `DNS_NTP_PORTS` | DNS + NTP.          |
| 3   | block    | any     | opt7 net | `RFC1918_PRIVATE`  | —               | No private.         |
| 4   | pass     | any     | opt7 net | `!RFC1918_PRIVATE` | —               | Internet only.      |

#### 5.4.9 opt8 — 40_ADMIN

| #   | Action             | Proto   | Source   | Destination       | Port            | Description                                                 |
| --- | ------------------ | ------- | -------- | ----------------- | --------------- | ----------------------------------------------------------- |
| 1   | pass               | any     | any      | any               | —               | **Temp** migration.                                         |
| 2   | pass               | TCP/UDP | opt8 net | (this firewall)   | `DNS_NTP_PORTS` | DNS + NTP.                                                  |
| 3   | pass               | TCP/UDP | opt8 net | (this firewall)   | `ADMIN_PORTS`   | OPNsense GUI + admin SSH (the only VLAN allowed to log in). |
| 4   | block              | any     | opt8 net | `RFC1918_PRIVATE` | —               | No private.                                                 |
| 5   | (no internet rule) |         |          |                   |                 | ADMIN VLAN is intentionally air-gapped from the internet.   |

#### 5.4.10 opt9 — 50_MEDIA

| #   | Action   | Proto   | Source   | Destination   | Port   | Description         |
| --- | -------- | ------- | -------- | ------------- | ------ | ------------------- |
| 1   | pass     | any     | opt9 net | any           | —      | **Temp** migration. |

Permanent rules planned (recorded in §16): allow IPP (`PRINT_IPP`)
inbound from `opt2`/`opt9`/`opt15` to `MEDIA_PRINTER`; deny printer →
any except DNS for firmware updates (decision: keep firmware updates
allowed because the original Brother firmware unlocks third-party
cartridges and rolling back is undesirable).

#### 5.4.11 opt10 — 100_PROXMOX

| #   | Action   | Proto   | Source    | Destination   | Port   | Description         |
| --- | -------- | ------- | --------- | ------------- | ------ | ------------------- |
| 1   | pass     | any     | opt10 net | any           | —      | **Temp** migration. |

Permanent rules planned: deny opt10 → all RFC1918 except `MGMT_NETS`
(i.e. mgmt and admin can reach Proxmox, nothing else can); allow opt10
egress 53/123/80/443 only.

#### 5.4.12 opt11 — 110_SERVICES

| #   | Action   | Proto   | Source    | Destination   | Port   | Description         |
| --- | -------- | ------- | --------- | ------------- | ------ | ------------------- |
| 1   | pass     | any     | opt11 net | any           | —      | **Temp** migration. |

#### 5.4.13 opt12 — 120_ESCAPE (break-glass)

| #   | Action   | Proto   | Source      | Destination                    | Port   | Description                                                         |
| --- | -------- | ------- | ----------- | ------------------------------ | ------ | ------------------------------------------------------------------- |
| 1   | pass     | TCP     | opt12 net   | `192.168.10.13/32`             | 8043   | Omada HTTPS.                                                        |
| 2   | pass     | TCP     | opt12 net   | `192.168.10.13`                | 8088   | Omada adopt/old port.                                               |
| 3   | pass     | TCP     | opt12 net   | `192.168.10.13`                | 9000   | Portainer emergency UI (reserved).                                  |
| 4   | pass     | TCP     | opt12 net   | `192.168.10.13`                | 22     | SSH vault (host SSH normally masked; only enabled during incident). |

The captive portal (§5.6) restricts who can claim a `120_ESCAPE` lease.

#### 5.4.14 opt14 — 140_PROXTER, opt15 — 150_EMPLOYER

* `opt14`: pass any → any during migration only; permanent profile = `30_SERVERS` clone.
* `opt15`: pass TCP from opt15 net to `MEDIA_PRINTER:631` (planned); deny opt15 → `RFC1918_PRIVATE`; pass opt15 → `!RFC1918_PRIVATE`.

### 5.5 NAT

* **Outbound NAT.** Mode = Automatic (default), with one custom rule mapping `opt7` (GUEST) → `opt10` (PROXMOX) — left over from a debugging session. Action item: review and most likely remove.
* **Port forwards.** None. All inbound is brokered through Tailscale; no public-internet listener exists.
* **NAT reflection.** Disabled.

### 5.6 DHCP

Per-VLAN ranges already given in §3.1. Additional global facts:

* DDNS algorithm: `hmac-md5`.
* Static mappings are exhaustive; conversion of dynamic leases to static is mandatory before any cable migration (so the new VM can reproduce the lease table without surprises).
* DHCP DNS overrides: only `60_QUARANTINE` overrides DNS to Cloudflare `1.1.1.2` / `1.0.0.2`; all other VLANs serve OPNsense Unbound (which itself forwards to AdGuard once §11 is implemented).

### 5.7 DNS — Unbound

| Setting                                  | Value                                | Rationale                                                                                                |
| ---------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| Enable Unbound                           | yes                                  | Local recursive resolver, reachable on all interfaces.                                                   |
| Listen port                              | 53                                   | Standard.                                                                                                |
| DNSSEC                                   | disabled                             | Will be re-enabled once AdGuard upstream is stable (§11).                                                |
| Register DHCP leases / static mappings   | disabled                             | Hostnames are managed centrally; avoid leaking dynamic leases into DNS.                                  |
| Aggressive NSEC                          | enabled                              | Reduces upstream chatter.                                                                                |
| Prefetch / Prefetch Key                  | disabled (today) → **enable in §11** | Pre-warms cache for top domains; required for AdGuard failover masking.                                  |
| Serve Expired Responses                  | disabled (today) → **enable in §11** | Lets Unbound answer with stale records while it asynchronously verifies upstream during AdGuard outages. |
| Local Zone Type                          | transparent                          | Forward unknown queries upstream.                                                                        |
| Query Name Minimization Strict           | disabled                             | Some upstreams misbehave with strict QNM; revisit.                                                       |
| Logging                                  | off (verb 1)                         | Reduces SSD wear; pivot to Loki when monitoring stack lands.                                             |

Private-address rebinding protection list (the Unbound built-in
"private-address" set): `127.0.0.0/8`, `10.0.0.0/8`, `100.64.0.0/10`,
`169.254.0.0/16`, `172.16.0.0/12`, `192.0.0.0/24`, `192.168.0.0/16`,
`192.0.2.0/24`, `198.18.0.0/15`, `198.51.100.0/24`, `203.0.113.0/24`,
`::1/128`, `2001:db8::/32`, `fc00::/8`, `fd00::/8`, `fe80::/10`.

Forwarding mode: currently **off** (recursive). After §11 lands,
forward to AdGuard jail; AdGuard upstreams to Cloudflare DoT
`1.1.1.2@853#cloudflare-dns.com`.

DNSMasq is present in `config.xml` but disabled (port 0).

### 5.8 Services

* **Captive Portal — zone `EmergencyAccess`** (UUID
  `89a8ae8c-ede3-4f12-a0b4-94dbdd1bde33`, zone ID 0). Bound to `opt12`
  (`120_ESCAPE`). Auth: local DB. Idle timeout 10 min. Hard timeout
  unlimited. Concurrent logins 1. Authenticated user `breakglass`
  (UID 2000, scope user, no admin privileges).
* **Zenarmor / Sensei (planned).** Pre-install checklist:
  * Disable all hardware offloading (`Disable Checksum`, `Segmentation`, `Large Receive`, `VLAN Hardware Filter`).
  * Verify with `ifconfig -m vtnet0` — no `RXCSUM/TXCSUM/TSO/LRO` flags.
  * Set RSS: `net.inet.rss.bits=2` (4 buckets to match the i226-V's 4 hardware queues).
  * Allocate 8 GiB+ RAM for the local Elasticsearch (or use a remote DB).
  * Choose Native Netmap if the NIC is PCI-passthroughed; Emulated Netmap if VirtIO.
  * Throughput baseline: `iperf3 -P 4` ≥ 2.5 Gb/s before installing Zenarmor.
* **Avahi mDNS reflector (planned, see §10).** To allow VLAN 50 printer discovery from VLAN 20 / 150 without bridging.
* **NTP.** Pool: `0.opnsense.pool.ntp.org` … `3.opnsense.pool.ntp.org`.
* **Suricata.** Disabled. Will pivot to Zenarmor.
* **Monit.** Configured but disabled. Watches `$HOST` (memory, CPU, load), root FS usage, CARP/gateway alert custom scripts. Mail relay `127.0.0.1:25` (placeholder). HTTPD UI on port 2812 disabled.
* **QEMU Guest Agent.** Enabled.
* **Syslog.** Local logging on, max preserve 31. Remote syslog → Loki/Grafana planned.

### 5.9 VPN

#### 5.9.1 WireGuard — current state

The OPNsense WireGuard subsystem is **enabled but unused** in the
current `config.xml`: zero servers, zero peers. The end-to-end remote
access path today is **Tailscale (in LXC 100)**, not WireGuard on the
firewall. WireGuard remains in the plan as the **second** remote-access
channel, intentionally architected to survive a Tailscale control-plane
outage.

Planned WireGuard server profile (recorded in §16 as an action item):

```text
[Interface]
ListenPort   = 51820
PrivateKey   = <generated; stored in OPNsense secret store>
Address      = 10.99.0.1/24
DNS          = 192.168.10.1
MTU          = 1420

# Per-peer template (one peer per trusted device)
[Peer]
# Friendly name: <device>
PublicKey    = <peer pubkey>
PresharedKey = <peer psk>          # mandatory for quantum-resistant tunnel
AllowedIPs   = 10.99.0.X/32        # /32 per peer, no LAN routes by default
PersistentKeepalive = 25
```

Routing intent: peers reach internal VLANs only via explicit firewall
rules on the WireGuard interface (`wg0`), mirroring the Tailscale ACL
philosophy (allow → MGMT or PROXMOX, deny everything else).

#### 5.9.2 IPsec, OpenVPN

Both subsystems are present in `config.xml` but disabled. IPsec
defaults: 16 threads, IKE SA table 32 / 4 segments, init-limit
half-open 1000, install-routes off, Cisco Unity off. No OpenVPN
instance configured.

### 5.10 Users / authentication / 2FA

* `root` (UID 0, group `admins`, page-all privilege). Password and SSH
  authorized keys stored in vault. TOTP seed currently empty —
  **recommendation**: enable TOTP for WebGUI + SSH.
* `breakglass` (UID 2000, scope user, no admin privilege). Used by
  the captive portal in §5.8.
* Group `admins` (GID 1999) with `page-all`.
* SSH service: enabled for `admins`, auto-start = no (started manually
  during incidents). Listen interfaces should be restricted to `opt8`
  (`40_ADMIN`) and `opt12` (`120_ESCAPE`). Action item: confirm.

### 5.11 Hardening / tunables

System tunables that are baked into `config.xml` (with the rationale
already given in §5.8 for Zenarmor):

| Tunable                                  | Value       | Purpose                             |
| ---------------------------------------- | ----------- | ----------------------------------- |
| `net.inet.rss.enabled`                   | 1           | Multi-core packet distribution.     |
| `net.inet.rss.bits`                      | 2           | 4 buckets matching i226-V queues.   |
| `net.isr.bindthreads`                    | 1           | Pin interrupt threads.              |
| `net.isr.maxthreads`                     | -1          | Use all cores.                      |
| `net.isr.dispatch`                       | deferred    | Avoid interrupt storms.             |
| `hw.vtnet.csum_disable`                  | 0           | Enable cap; UI-side disables.       |
| `hw.igc.rx_process_limit`                | 100         | Batch RX for the igc driver.        |
| `vm.pmap.pti`                            | 1           | Meltdown mitigation.                |
| `hw.ibrs_disable`                        | 0           | Spectre IBRS for Intel.             |
| `net.inet.ip.random_id`                  | 1           | Randomise IPv4 IDs.                 |
| `security.bsd.hardlink_check_gid`        | 1           | Prevent cross-group hardlink abuse. |
| `security.bsd.hardlink_check_uid`        | 1           | Cross-user hardlink hardening.      |
| `security.bsd.unprivileged_proc_debug`   | 0           | No `ptrace` for unprivileged users. |
| `security.bsd.see_other_gids`            | 0           | Hide other groups' processes.       |
| `security.bsd.see_other_uids`            | 0           | Hide other users' processes.        |
| `security.bsd.unprivileged_read_msgbuf`  | 0           | Hide kernel msgbuf.                 |

Console: `Disable Console Menu = yes`, primary console `video`,
secondary `serial @115200`. Power management `hadp` (high adaptive)
across AC/battery/normal. Memory FS for `/var` and `/tmp` capped at
8 MiB each. SSL cert ref `6921e88ce5e8e` (replace with a Let's-Encrypt
chain via the os-acme-client plugin once §11 lands).

### 5.12 Backup / HA

* **HA / CARP.** Not configured. Not on the roadmap (single-node home setup).
* **Configuration backup.** Daily via cron, using the `os-api-backup` plugin and a dedicated `backup` user/group with the `Backup API` privilege only. The backup user's API key/secret is generated through the GUI and stored encrypted in the vault. Backups land on a remote Linux/BSD host via `curl`, are encrypted with a password, and are rotated with a 30-day retention policy.
* **Backup format.** XML files named `opnsense-config-YYYYMMDD.xml`.
* **Manual fallback.** System → Configuration → Backups → Download.
* **RRD / NetFlow backup.** Disabled (`-1`).

---

## 6. Proxmox host bible (N95 + N305)

### 6.1 Repositories

```bash
# Disable enterprise.
sed -i "s/^deb/#deb/g" /etc/apt/sources.list.d/pve-enterprise.list
# Add no-subscription.
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  >> /etc/apt/sources.list
# Fix Ceph (if present).
sed -i "s/^deb/#deb/g" /etc/apt/sources.list.d/ceph.list
echo "deb http://download.proxmox.com/debian/ceph-quincy bookworm no-subscription" \
  >> /etc/apt/sources.list.d/ceph.list
```

### 6.2 Kernel hardening — `/etc/sysctl.d/99-security.conf`

```text
# 1. Restrict kernel logs.
kernel.dmesg_restrict          = 1
# 2. Restrict kernel pointers in /proc.
kernel.kptr_restrict           = 2
# 3. Disable unprivileged BPF.
kernel.unprivileged_bpf_disabled = 1
# 4. Prevent ICMP redirect attacks.
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects   = 0
```

Additional tunables for the **gateway role** (LXC 100): set
`net.ipv4.ip_forward = 1` only inside that container, never on the
Proxmox host itself.

### 6.3 Cluster firewall — `/etc/pve/firewall/cluster.fw`

```ini
[OPTIONS]
enable: 1

[ALIASES]
management_ips 192.168.100.0/24

[RULES]
IN SSH(ACCEPT)  -source dc/management_ips                       -log nolog
IN ACCEPT       -source dc/management_ips -p tcp -dport 8006    -log nolog
IN ACCEPT       -source 192.168.90.0/24   -p udp -dport 29810   -log nolog   # Omada device discovery (during migration window only)
IN ACCEPT       -source 192.168.90.0/24   -p tcp -dport 29811:29814 -log nolog
IN ACCEPT       -source 192.168.90.0/24   -p tcp -dport 29817   -log nolog
```

(After migration, the Omada source-net narrows from `192.168.90.0/24`
to `192.168.10.0/24` once the controller is permanently in MGMT.)

### 6.4 Fail2Ban

* `/etc/fail2ban/jail.d/proxmox.conf`:

  ```ini
  [proxmox]
  enabled  = true
  port     = https,http,8006
  filter   = proxmox
  logpath  = /var/log/daemon.log
  maxretry = 3
  findtime = 600
  bantime  = 3600
  backend  = systemd
  ```

* `/etc/fail2ban/filter.d/proxmox.conf`:

  ```ini
  [Definition]
  failregex = pvedaemon\[.*authentication failure; rhost=<HOST> user=.* msg=.*
  ignoreregex =
  ```

* `sshd` jail kept enabled (default), `backend = systemd` so it works
  on Debian 12's systemd-journald.

### 6.5 2FA / MFA

* TOTP for the `sysadmin` Proxmox user via Datacenter → Permissions →
  Two Factor → TOTP.
* `/etc/pve/priv/tfa.cfg` must exist and be non-empty after enrolment.
* Recovery codes downloaded once and stored in the offline vault.

### 6.6 SSH killswitch

```bash
# Mask the socket (else systemd would re-create the unit on demand)
systemctl stop ssh.socket
systemctl disable ssh.socket
systemctl mask ssh.socket

# Mask the service
systemctl stop ssh.service
systemctl disable ssh.service
systemctl mask ssh.service
```

Re-enable only from physical console:

```bash
systemctl unmask ssh.socket ssh.service
systemctl start  ssh.service
```

**Parity gap to close.** N95 currently has `ssh.service` active (with
the socket inactive). N305 must close the parity by masking both
units. This is recorded in §16 as a hardening item.

### 6.7 Network bridges

Already given in §5.1 (Phase 3). N95's `/etc/network/interfaces` is
identical except the management IP is `192.168.100.10/24` and the WAN
bridge is absent (N95 doesn't host OPNsense).

### 6.8 Storage

* Local filesystem: ext4 on a single NVMe.
* Local-LVM thin pool: `/dev/pve/data` mounted as `local-lvm`. All VM
  / CT root disks live here.
* `local` directory storage for ISOs, backups, templates.

### 6.9 Unattended-upgrades

* `/etc/apt/apt.conf.d/50unattended-upgrades` — Allowed-Origins:

  ```text
  "Debian:bookworm-security";
  "Debian:bookworm-updates";
  ```

* Auto-reboot at 03:30 (on the host, randomised). No Docker repo on
  the Proxmox hosts themselves (the Docker origin lives only inside
  LXC 101 and any future Docker LXC — see §7).

### 6.10 Software inventory

Installed: `micro`, `nmap`, `fail2ban`, `curl`, `wget`. Not installed
on purpose: `git`, `vim`, `htop` (kept off the firewall blast radius;
operations happen from the gateway LXC instead).

### 6.11 Differences N95 vs N305

| Item                          | N95                                   | N305                                    |
| ----------------------------- | ------------------------------------- | --------------------------------------- |
| Hostname                      | `pve-n95`                             | `pve-n305.lan`                          |
| Mgmt IP                       | `192.168.100.10/24`                   | `192.168.100.2/24`                      |
| PVE version                   | `9.1.4 / 5ac30304265fbd8e`            | (target 8.x baseline; upgrade later)    |
| Kernel                        | `6.17.4-2-pve`                        | (target equal or newer)                 |
| WAN bridge `vmbr1`            | not present                           | required (OPNsense WAN passthrough)     |
| DMZ bridge `vmbr2`            | optional (no AdGuard locally)         | required for AdGuard jail               |
| SSH state                     | `ssh.service` active                  | both units must be masked               |
| 2FA                           | enabled                               | mandatory before lockdown               |
| Cluster firewall              | enabled, same alias / rules           | same                                    |

---

## 7. LXC bible

### 7.1 Golden image baselines

#### 7.1.1 `IMG-DEB12-HARDENED-v1` — base

* Debian 12 (Bookworm) unprivileged template.
* Packages: `ufw`, `fail2ban`, `unattended-upgrades`, `curl`, `wget`, `micro`, `debian-keyring`, `debsums`, `apt-transport-https`, `gnupg`.
* sysctl: `net.ipv4.ip_forward=0` (gateways override), `net.ipv4.conf.all.rp_filter=1`, `kernel.dmesg_restrict=1`, `kernel.kptr_restrict=2`, `kernel.unprivileged_bpf_disabled=1`.
* UFW: default `deny incoming`, `allow outgoing`, plus per-service explicit rules.
* Fail2Ban: `backend=systemd`, jails `sshd` (aggressive), action `iptables-multiport`.
* Unattended-upgrades: Debian security + updates only on the base; Docker origin added by the v2 image.
* SSH: present but masked by default; only the runbook re-enables it briefly.
* User `sysadmin` with sudo, key-only auth, restricted to `192.168.120.*` (`AllowUsers sysadmin@192.168.120.*`).
* `chattr +i /etc/resolv.conf` after writing `nameserver 192.168.10.1` (DNS sovereignty — see §14 incident).

#### 7.1.2 `IMG-DEB12-DOCKER-v2` — production extension

* Extends `HARDENED-v1`.
* Adds Docker CE (from the official `docker.io` repository with the modern keyring layout) and the Compose plugin.
* `net.ipv4.ip_forward=1` (Docker bridge requirement).
* Adds `Docker:${distro_codename}` to unattended-upgrades Allowed-Origins.
* `sysadmin` is added to the `docker` group.
* Audit hooks (`audit_secure.sh`, `verify_security.sh`) shipped under `/usr/local/sbin/`.

### 7.2 LXC 100 — Tailscale gateway + Caddy reverse proxy

* CTID `100`, hostname `tailscale-lxc`, image `IMG-DEB12-HARDENED-v1`.
* **Unprivileged**, ID-mapping `root:0:1` → host `100000`. `features: nesting=1`. TUN passthrough:

  ```text
  lxc.cgroup2.devices.allow: c 10:200 rwm
  lxc.mount.entry: /dev/net dev/net none bind,create=dir
  ```

* Resources: 1 vCPU, 512 MiB RAM, 4 GiB disk on `local-lvm`.
* Network: bridge `vmbr0`, VLAN tag `10`, IP `192.168.10.5/24`, GW `192.168.10.1`.
* Tailscale: userspace networking mode (because TUN is mapped via passthrough rather than full kernel ownership), `--advertise-tags=tag:server`, advertises subnets `192.168.100.0/24` and `192.168.10.0/24`. State at `/var/lib/tailscale/tailscaled.state`. Identity hostname `tailscale-lxc-n95-proxmox-host` (one per Proxmox node).
* MagicDNS certificate: `whale-mulley.ts.net.crt` / `.key`, generated via `tailscale cert` and dropped into `/etc/caddy/`.
* Caddy: `setcap 'cap_net_bind_service=+ep' /usr/bin/caddy` so the unprivileged container can bind 80/443. Caddyfile reproduced in §8.
* UFW allow list: `22` (sysadmin only), `80`, `443`, `41641/udp` (Tailscale direct), `9001` (Portainer Agent — used by future LXC 102 server).
* Unattended-upgrades — Tailscale "Site-Match" pattern:

  ```text
  Unattended-Upgrade::Allowed-Origins {
      "Debian:bookworm-security";
      "Debian:bookworm-updates";
      "site=pkgs.tailscale.com";
      "site=dl.cloudsmith.io";       # Caddy
  };
  ```

* Audit script: `audit_lxc100_magnum.sh` (alias "Mad Hacker Omega"), phases:
  1. Network identity (IP, route, ARP, resolver).
  2. Security baseline (UFW status & rules, SSH **purged**, Fail2Ban).
  3. Reverse-proxy config (Caddyfile syntax, upstream IPs `192.168.100.10` / `192.168.10.13`, TLS cert paths).
  4. VPN (Tailscale status + peer list, `tailscale netcheck`, advertised routes).
  5. Application layer (Docker `ps` if relevant, Portainer Agent on `:9001`).
  Plus stand-alone tests: port-4444 egress test, IPv6 leak test, ASLR check, Docker-socket exposure hunt.

### 7.3 LXC 101 — Omada controller (Silver image)

* CTID `101`, hostname `Omada-Controller`, OS Debian 12.
* Resources: 2 vCPU (host CPU type, AVX2), 3 GiB RAM, 2 GiB swap, 16 GiB disk.
* Network: bridge `vmbr0`, VLAN tag `10`, IP `192.168.10.13/24`, GW `192.168.10.1`, MAC `BC:24:11:XX:XX:XX` (sanitized).
* `pct set 101 --startup order=2,up=10,down=120` — the **120-second shutdown grace** is what prevents MongoDB corruption under Proxmox restart.
* `/opt/stacks/container/compose.yaml` (verbatim minus secrets):

  ```yaml
  services:
    omada-controller:
      image: mbentley/omada-controller:6.0
      container_name: omada-controller
      restart: unless-stopped
      network_mode: host                  # L2 broadcast required for AP/switch discovery
      stop_grace_period: 60s              # MongoDB graceful shutdown
      environment:
        - MANAGE_HTTP_PORT=8088
        - MANAGE_HTTPS_PORT=8043
        - PORTAL_HTTP_PORT=8088
        - PORTAL_HTTPS_PORT=8843
        - SHOW_SERVER_LOGS=true
        - SHOW_MONGODB_LOGS=false
        - TZ=Europe/Lisbon
      volumes:
        - ./data:/opt/tplink/EAPController/data
        - ./logs:/opt/tplink/EAPController/logs

    portainer_agent:
      image: portainer/agent:2.21.5
      container_name: portainer_agent
      restart: always
      ports:
        - "9001:9001"
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock
        - /var/lib/docker/volumes:/var/lib/docker/volumes
  ```

* Portainer **Agent** (not Server) — the agent has no credentials and only accepts encrypted instructions from the future LXC 102 server, scoped via the Tailscale tag.
* DNS sovereignty fix: `echo "nameserver 192.168.10.1" > /etc/resolv.conf && chattr +i /etc/resolv.conf` to prevent inheritance of the Proxmox host's legacy `192.168.90.1`.
* UFW allow list: `22` (from `192.168.10.5` / `192.168.120.0/24`), `8088`, `8043`, `8843`, `29810:29814`, `9001` (from `192.168.10.5` only).
* Audit script `audit_secure.sh` checks: identity, security posture, auto-update, application layer (Docker / Portainer Agent), filesystem.
* `verify_security.sh` ("Live Fire"):
  1. UFW integrity (active, default deny).
  2. Fail2Ban "dummy ban" of `192.0.2.1` — verifies the kernel-level packet-filter insertion path.
  3. Unattended-upgrades dry-run confirms sources.
  4. Portainer Agent listening on `:9001`.
* Auto-backup: Omada exports `.cfg` + `.zip` daily into the bind-mounted `data/autobackup`; off-host copy via the cluster backup job.

### 7.4 LXC 102 — Management hub (planned)

* Purpose: Portainer **Server** (split from LXC 100, which is overloaded) + Homepage dashboard.
* Image: `IMG-DEB12-DOCKER-v2`.
* Network: VLAN 10 / `192.168.10.x`. Tailscale member with `tag:server`.
* Tailscale ACLs (golden):
  * `tag:user` (admin laptops/phone) → `tag:server` on TCP 22, 80, 443, 9000, 9443.
  * `tag:server` ↔ `tag:server` on TCP 9001 (Agent), 9100 (Node Exporter), 8080 (cAdvisor).
  * Default deny.

### 7.5 AdGuard Home — DMZ jail (planned)

* CTID `105` (proposed). Image `IMG-DEB12-DOCKER-v2`.
* **Network: `vmbr2` only** — no physical port; `bridge-ports none`. Traffic to / from this LXC must transit OPNsense.
* Subnet: `192.168.25.0/24` is recommended over the original `192.168.20.0/24` plan (collides with VLAN `20_SECURE`). IP `192.168.25.5/24`, GW `192.168.25.1` (a new OPNsense interface on `vtnet2`).
* OPNsense rules on the new DMZ interface:
  * **pass** TCP/UDP from DMZ → `any` port 53, 853 (allow upstream DoT to Cloudflare).
  * **pass** TCP from DMZ → `any` port 80, 443 (so AdGuard can fetch filter list updates).
  * **block** from DMZ → `RFC1918_PRIVATE`.
  * **block** from DMZ → `(this firewall)`.
  * **pass** from `LAN/opt*` → `192.168.25.5` port 53, 853 (DNS query from LAN-side VLANs).
* AdGuard upstream chain: Cloudflare DoT primary `1.1.1.2@853#cloudflare-dns.com`; secondary `1.0.0.2@853#cloudflare-dns.com`; with `1.1.1.3` reserved for the future kids profile.
* Failover: OPNsense Unbound is configured (§5.7) to forward to AdGuard with `serve-expired = yes` and `prefetch = yes`, so a dead AdGuard masks the latency until Unbound takes over directly to Cloudflare.
* Cache: configure AdGuard's runtime cache in `tmpfs` (mount `/opt/adguardhome/work/data/querylog` and `/cache` as tmpfs) to avoid SSD wear, with a daily `cron` snapshot to disk for warm restart.

---

## 8. Reverse proxy & remote-access bible

### 8.1 Caddyfile (LXC 100)

```caddy
# Proxmox GUI — root MagicDNS hostname.
tailscale-lxc-n95-proxmox-host.whale-mulley.ts.net {
    tls /etc/caddy/tailscale.crt /etc/caddy/tailscale.key
    reverse_proxy https://192.168.100.10:8006 {
        transport http {
            tls_insecure_skip_verify
        }
    }
}

# Omada Controller — port 8443 on the same hostname.
tailscale-lxc-n95-proxmox-host.whale-mulley.ts.net:8443 {
    tls /etc/caddy/tailscale.crt /etc/caddy/tailscale.key
    reverse_proxy https://192.168.10.13:8043 {
        header_up Host {upstream_hostport}            # Omada is picky about Host header
        transport http {
            tls_insecure_skip_verify
        }
    }
}

# Portainer (Agent UI / future Server) — port 9443.
tailscale-lxc-n95-proxmox-host.whale-mulley.ts.net:9443 {
    tls /etc/caddy/tailscale.crt /etc/caddy/tailscale.key
    reverse_proxy http://192.168.10.13:9000
}
```

`tls_insecure_skip_verify` is acceptable here because the upstream
already has its own (untrusted) self-signed certificate, the path is
inside the LAN, and the encrypted leg the user actually traverses is
the Tailscale WireGuard tunnel ending at the Caddy listener.

### 8.2 Tailscale topology

* **Single tailnet** (`whale-mulley.ts.net`).
* Tags: `tag:user` for human devices; `tag:server` for LXCs and any future server. ACLs in §7.4.
* Subnet routing: LXC 100 advertises `192.168.10.0/24` and `192.168.100.0/24` so that admin laptops can reach Proxmox even when Caddy is unavailable (emergency path).
* MagicDNS: enabled. Each LXC has a stable name `whale-mulley.ts.net` suffix.

### 8.3 Future: WireGuard as the "second key"

Once §5.9.1 lands, the WireGuard server runs on OPNsense itself,
listening on `WAN:51820` (port allow rule on WAN). Peers are:

* Sysadmin laptop (`AllowedIPs = 10.99.0.2/32`).
* Sysadmin phone (`AllowedIPs = 10.99.0.3/32`).

Routing intent stays Tailscale-equivalent (allow-list to MGMT and
PROXMOX, deny everything else). Used only when Tailscale is down.

---

## 9. Omada controller bible

### 9.1 Adoption flow

1. Power on switch / AP. By default it broadcasts on the management VLAN.
2. From the Omada Controller (LXC 101 — `https://192.168.10.13:8043`),
   `Devices → +` → discovery shows the new device.
3. Adopt with the controller's preset credentials.
4. Push the appropriate port profile (§9.2) and wireless network (§9.4).

### 9.2 Port profiles

* **`Proxmox_Trunk`.** PVID `100`. Tagged: `10, 20, 30, 40, 50, 60, 70, 80, 90, 110, 120, 140, 150` (all except `999`). Applied to switch ports facing N305 and N95.
* **`AP_Trunk`.** PVID `10`. Tagged: every VLAN whose SSID is broadcast from APs (10, 20, 50, 70, 80, 90, 130). Applied to AP-facing ports.
* **`Access_<VLAN>`.** PVID `<VLAN>`. No tagged VLANs. One profile per access VLAN.
* **`Office_Hybrid`.** PVID `20`. Tagged: `30, 50`. For the workstation that needs occasional SERVERS / MEDIA access.
* **`All_Lifeboat`.** PVID `1`. Tagged: every VLAN. SG2008 P8 only.
* **`Blackhole`.** PVID `999`. No tagged VLANs. For unused ports.

### 9.3 Wired networks

One Omada "Wired Network" entry per VLAN. Each has:

* Purpose: `VLAN`.
* VLAN ID: as in §3.1.
* DHCP: **disabled** (OPNsense is the only DHCP authority).
* IGMP / DHCP guarding: enabled where supported.

### 9.4 SSID-to-VLAN mapping

| SSID                   | VLAN   | Security                      | Notes                                                            |
| ---------------------- | ------ | ----------------------------- | ---------------------------------------------------------------- |
| `Whale_SECURE`         | 20     | WPA3-Personal + WPA2 fallback | Family laptops/phones.                                           |
| `Whale_MEDIA`          | 50     | WPA3-Personal                 | TVs, speakers, Brother printer (Wi-Fi unused; printer is wired). |
| `Whale_IoT`            | 70     | WPA2-Personal                 | Some IoT can't do WPA3. Client-isolation enabled.                |
| `Whale_GUEST`          | 90     | Open + portal                 | Guest portal with bandwidth cap.                                 |
| `Whale_KIDS`           | 130    | WPA2-Personal                 | Reserved; activated when 130 DHCP is configured.                 |
| `Whale_HIDDEN_MGMT`    | 10     | WPA3-Personal, hidden         | Management Wi-Fi for admin laptop break-glass.                   |

### 9.5 Omada → OPNsense interaction

* No DHCP on Omada. No Layer-3 anywhere on the switches.
* `Omada Discovery` uses UDP `29810` and `29812`; only the `90_GUEST`
  source-net is allowed inbound during the migration window (so the
  initial controller-on-Guest-VLAN bootstrap works); the rule is
  rewritten to source `192.168.10.0/24` once the controller is
  migrated to MGMT permanently.

### 9.6 Backup automation

* Omada autobackup runs nightly into `./data/autobackup` (bind-mounted into the LXC).
* The Proxmox cluster backup job copies the LXC volume off-host weekly.
* The autobackup directory is also tarballed and uploaded to the off-site cold-storage by the same `os-api-backup` cron that handles OPNsense (planned).

### 9.7 Migration to 2× SG2210XMP-M2

Sequence (zero-lockout):

1. Build the new switches' configuration in the controller as **inactive** (push later).
2. Pre-stage power and uplink cables in the rack.
3. During a maintenance window: unplug SG2008's uplink, plug it into SG2210#1's same port profile. Wait 10 s, reconnect.
4. Adopt SG2210#1 from the controller, push the Proxmox_Trunk profile, verify Proxmox is reachable.
5. Repeat with TL-SG108E → SG2210#2.
6. Move the AP cables from the old switches to the new ones.
7. Power down old switches; keep them as cold-spare for 30 days.
8. Push 2.5 GbE / 10 GbE port profiles where the cabling supports it (NAS, between-switch uplink).

---

## 10. Printer bible (Brother MFC-J5320DW)

* **Placement.** VLAN `50_MEDIA`, static-DHCP IP (`MEDIA_PRINTER`).
* **Why MEDIA.** Printer is a household device; placing it in `30_SERVERS` would force every casual print job to cross a VLAN boundary unnecessarily.
* **Firmware policy.** Keep the *current* firmware. The user has selected this firmware specifically because it permits second-hand cartridges; an upgrade is suspected to lock that. **Do not** auto-update via OPNsense egress rules; deny printer → `*:80/443` except whitelisted update servers.
* **Discovery.** Two acceptable strategies, picked per client:
  1. **Static-IP TCP/IP port** install on each client laptop (preferred for VLAN 20 / 150 — bypasses mDNS entirely). Cleanest from a firewall perspective.
  2. **Avahi mDNS reflector** on OPNsense, reflecting between `opt2 / opt9 / opt15`. Slightly more permissive but easier for new family laptops.
* **Allowed protocols.**
  * IPP over TCP `631` — keep.
  * Raw `9100` and LPD `515` — **drop after PCAP analysis** confirms the family of devices (Windows, macOS, Linux laptops + the company-managed laptop) only use IPP.
  * SNMP `161` — keep only if the controller actively monitors the printer; otherwise drop.
  * Scanner-to-PC — **disabled.** Pull scanning happens via the printer's web UI (HTTPS) reachable only from VLAN 20 admin laptop.
* **PCAP procedure.** During the migration window, mirror the printer's switch port to a sysadmin laptop, run a single test print from each client, capture with Wireshark, and confirm the only L4 flow is `client:* → printer:631`. The result of that PCAP becomes the canonical port allow-list.
* **Employer-laptop access.** From `150_EMPLOYER`, allow only IPP to the printer; deny everything else internal.

---

## 11. DNS / AdGuard bible

### 11.1 Upstream resolver matrix

| Resolver                    | IPv4                   | IPv6                             | Use here?                  | Notes                                                                                          |
| --------------------------- | ---------------------- | -------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------- |
| Cloudflare standard         | `1.1.1.1` / `1.0.0.1`  | `2606:4700:4700::1111` / `…1001` | optional fallback          | No filtering.                                                                                  |
| Cloudflare Malware-block    | `1.1.1.2` / `1.0.0.2`  | `2606:4700:4700::1112` / `…1002` | **primary**                | Blocks malware / phishing / C&C. False-positive rate low. Bad domains redirected to `0.0.0.0`. |
| Cloudflare Family           | `1.1.1.3`              | (similar)                        | reserved for VLAN 130_KIDS | Adds adult-content blocking.                                                                   |
| Quad9                       | `9.9.9.9` / `9.9.9.11` | (similar)                        | secondary considered       | `9.9.9.11` is the EDNS-Client-Subnet variant the user prefers.                                 |
| NextDNS                     | per-account            | per-account                      | not chosen                 | Free tier limits and per-host ID complicate VLAN-level filtering.                              |
| Pi-hole                     | (self-host)            | —                                | rejected (see 11.4)        | Less polished UI for parental controls.                                                        |

### 11.2 OPNsense Unbound cache settings (final)

* `Enable Unbound`: yes.
* `Forwarding mode`: yes (forward to AdGuard at `192.168.25.5:53` once §11.5 lands).
* `Prefetch`: **yes**.
* `Prefetch Key`: yes.
* `Serve Expired Responses`: **yes** with `serve-expired-ttl = 3600` so stale records can be answered for up to 1 h while AdGuard is unhealthy.
* `Aggressive NSEC`: yes.
* DNSSEC: yes (after AdGuard is stable).
* `qname-minimisation`: yes (non-strict).

### 11.3 Per-VLAN DNS overrides

* `60_QUARANTINE` → `1.1.1.2` / `1.0.0.2` (Cloudflare malware-block direct, bypassing AdGuard) so that even an AdGuard outage cannot let a quarantined device resolve attacker domains.
* `130_KIDS` (planned) → `1.1.1.3` (Cloudflare Family) directly; AdGuard parental profile still applied for fine-grained per-app blocking.
* All other VLANs → OPNsense Unbound (which forwards to AdGuard).

### 11.4 AdGuard vs Pi-hole — final verdict

**AdGuard Home** chosen over Pi-hole on these criteria:

| Criterion                                                           | AdGuard Home                              | Pi-hole                     | Winner                     |
| ------------------------------------------------------------------- | ----------------------------------------- | --------------------------- | -------------------------- |
| Parental controls (one-click services: YouTube, TikTok, SafeSearch) | native                                    | manual blocklists           | AdGuard                    |
| Native DoH / DoT / DoQ                                              | yes                                       | needs Unbound / Cloudflared | AdGuard                    |
| OPNsense plugin                                                     | available                                 | needs separate VM/Docker    | AdGuard                    |
| Modern UI / mobile companion                                        | yes (PWA + 3rd-party AdGuard Home Remote) | functional but dated        | AdGuard                    |
| Block-list granularity                                              | very good                                 | excellent (per-group)       | tie                        |
| Memory/CPU footprint                                                | small                                     | very small                  | tie (both fine on the LXC) |

The tie-breaker was the parental-controls UX: matching the "Omada-like
controller experience" the user wants for the rest of the lab.

### 11.5 Deployment architecture (single source of failure mitigated)

```text
Client → OPNsense Unbound (cache, prefetch, serve-expired)
              │
              ▼
         AdGuard LXC :53 (vmbr2 jail) ────┐
              │ (Cloudflare DoT 1.1.1.2)  │
              ▼                            │ (failover when AdGuard dead)
         Cloudflare resolvers ◄────────────┘ (Unbound direct)
```

* Primary path: client → Unbound → AdGuard → Cloudflare DoT.
* Failover: if AdGuard is unreachable for `infra-cache-min-rtt`, Unbound's `serve-expired` answers from cache while it asynchronously refetches from Cloudflare directly.
* Recovery: when AdGuard returns, Unbound's normal forward path resumes. No restart required.
* SSD-wear mitigation: AdGuard's hot caches live on `tmpfs`; the persistent config and stats ride a daily snapshot.

### 11.6 Subnet conflict note

The chats discuss the AdGuard jail on `192.168.20.0/24`, which collides
with the existing `20_SECURE` VLAN. The committed plan in §7.5 uses
`192.168.25.0/24`. Action item recorded in §16.

---

## 12. NAS bible (TerraMaster + unRAID)

* **Hardware.** TerraMaster 4-bay enclosure. Drives: existing Western
  Digital NAS HDDs (ageing, gigabit-bound today). RAM: undersized;
  upgrade scheduled before any RAM-cache scheme is enabled.
* **OS choice.** unRAID. Reasoning: array flexibility (can mix drive
  sizes, single-parity), strong RAM-cache and Docker support, simpler
  GUI than TrueNAS for a household.
* **Network.** Wired into the future SG2210XMP-M2 fabric on a 2.5 GbE
  port — the gigabit ceiling of the legacy SG2008 / TL-SG108E is the
  reason RAM-caching of the old WD HDDs feels useless until the switch
  upgrade.
* **RAM-cache strategy.** Half of installed RAM is `tmpfs` at `/dev/shm`
  by default. Suitable use cases:
  * Plex transcode folder (Plex on Docker → `/dev/shm`).
  * Game / CAD scratch space (AutoCAD, Revit, occasional gaming) for
    "sysadmin workstation" pulls.
* **Read-ahead tuning.** For the spinning-rust array:

  ```bash
  for drive in /dev/sd[a-d]; do
    blockdev --setra 4096 "$drive"        # 2 MiB read-ahead per drive
  done
  ```

  Persisted via `/boot/config/go` or the User Scripts plugin (run on
  array start). Higher values (`8192`/`16384`) are tested with
  `hdparm -tT` before adoption.
* **Samba read-ahead.** `/etc/samba/smb-shares.conf` includes per-share:

  ```text
  [video]
  path = /mnt/user/video
  vfs objects = catia fruit streams_xattr read_ahead
  read_ahead:readahead = 65536
  follow symlinks = yes
  wide links      = yes
  unix extensions = no
  ```

  (Configured via Settings → Samba Extra in the unRAID Web UI; pasted
  in full because the field is replace-not-append.)
* **VLAN.** `30_SERVERS` (NAS UI) + a separate `110_SERVICES` interface
  for Docker workloads if running Docker on the NAS.

---

## 13. Monitoring stack

* **Where it lives.** A dedicated LXC on `pve-n95` (CTID `103`,
  reserved). Image `IMG-DEB12-DOCKER-v2`. VLAN `110_SERVICES`.
* **Compose stack** (planned):
  * `prom/prometheus` — pull-based scraping; persistent volume for the
    TSDB; 30-day retention.
  * `grafana/grafana` — dashboards; Tailscale-fronted via Caddy.
  * `prom/node-exporter` — runs on every Proxmox host on `:9100`,
    scraped by Prometheus.
  * `gcr.io/cadvisor/cadvisor` — container metrics; `:8080`.
  * `grafana/loki` + `grafana/promtail` — log aggregation. Promtail on
    each node ships syslog / docker logs.
  * `prom/alertmanager` — alerting rules: disk > 80 %, CPU > 90 % for
    5 min, container restart loop, Fail2Ban ban event, MongoDB
    shutdown not graceful, OPNsense backup failure, AdGuard
    unreachable for > 5 min.
* **Access.** Only via Tailscale + Caddy (`grafana.whale-mulley.ts.net`).

---

## 14. Incident register

| Code                         | Date       | Title                                              | Root cause                                                                       | Fix                                                                                                                  | Lesson                                                                              |
| ---------------------------- | ---------- | -------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `INC-LXC101-NET-01`          | 2025-12    | Omada LXC isolated on VLAN 10                      | `vmbr0` not VLAN-aware; tagged frames dropped at the Linux bridge.               | Added `bridge-vlan-aware yes` and `bridge-vids 2-4094` to `/etc/network/interfaces`; `ifreload -a`.                  | VLAN-aware bridges require explicit `bridge-vids`.                                  |
| `INC-MONGO-SHUTDOWN-01`      | 2025-12    | Omada controller corrupted after host reboot       | MongoDB SIGKILL after Proxmox's default 60 s shutdown grace.                     | `pct set 101 --startup down=120` + Compose `stop_grace_period: 60s`.                                                 | Heavy DBs need long shutdown grace at *both* the orchestrator and container layers. |
| `INC-DNS-POISON-01`          | 2026-01    | LXC 101 resolved internal names via untrusted VLAN | LXC inherited Proxmox host's `resolv.conf` pointing at `192.168.90.1` (Guest).   | Hardcoded `nameserver 192.168.10.1` and `chattr +i /etc/resolv.conf`.                                                | Infrastructure containers need DNS sovereignty.                                     |
| `INC-ARP-SHOCK-01`           | 2026-02    | Modem failed to renew DHCP after Lobotomy          | ISP modem's MAC cache pinned old physical NIC MAC; new VirtIO MAC rejected.      | 60 s modem power-cycle + 10 s switch power-cycle + 5–10 min wait; if persistent, MAC clone fallback in OPNsense.     | ARP/DHCP caches in the ISP edge are real and slow.                                  |
| `INC-SSH-KILLSWITCH-01`      | 2026-02    | SSH kept restarting after `systemctl disable`      | Only `ssh.service` was masked; `ssh.socket` re-spawned the daemon on demand.     | Mask both `ssh.socket` and `ssh.service`; document the unmask procedure.                                             | systemd socket activation is the trap.                                              |
| `INC-NADD-DRIFT-01`          | 2026-02    | Documentation diverged from reality                | NADD blueprint updated, but `EVOLUTION` and `MIGRATION` chats forked separately. | Single canonical doc (this one) + diary in `PROJECT_HISTORY.md`.                                                     | One source of truth, append-only diary.                                             |
| `INC-TAILSCALE-KEY-01`       | 2026-03    | Tailscale repo key expired; updates failed         | Cloudsmith repository key rotation.                                              | Manual key import + Site-Match unattended-upgrades pattern.                                                          | Third-party origins need explicit allow-list.                                       |
| `INC-CADDY-CERT-01`          | 2026-03    | Caddy fail to load TLS                             | TLS path mismatch after `tailscale cert` regeneration.                           | Hardcode `tailscale.crt` / `tailscale.key` paths under `/etc/caddy/` + symlink update on rotation.                   | Certificate paths are part of the runtime contract.                                 |

---

## 15. Master roadmap river-flow

A single chronological narrative of what has been built, what is in
flight, and what is next. This is the user-facing answer to *"how did
we get here and where are we going?"*.

**2025-Q4 (`INITIAL-LEGACY`).** OPNsense bare-metal on the N305 with
flat LAN + Suricata. False-positive avalanche from Suricata; first
incidence of the "documentation drift" problem. Decision to move to
Zenarmor in the future and to virtualize the firewall.

**2025-12 (`PROXMOX_Omada_Setup`, `Proxmox_OPNsense_Install`).** Procured
N95 as the management node. Installed Proxmox VE on N95. Designed the
VLAN schema (10/20/30/40/50/60/70/80/90 + 100/110/120/140/150/999).
Decided the firewall would be the only DHCP/DNS authority. Designed
the cluster firewall + Fail2Ban + sysctl baseline.

**2025-12 (`switch_setup_OPNsense_DHCP_Interface_Configuration`,
`UPDATED-MIGRATION`).** Wired the SG2008 + TL-SG108E as a tagged
fabric. Created Omada port profiles (`Proxmox_Trunk`, `AP_Trunk`,
`Office_Hybrid`, `All_Lifeboat`, `Blackhole`). Adopted EAP683 + EAP653
APs and mapped SSIDs to VLANs.

**2025-12 (`NADD_Master_Blueprint`).** Wrote the Network Architecture
Design Document v1.6 — first formal description of the Zero-Trust
architecture. The blueprint defined the LXC roles before any container
was built.

**2025-12 → 2026-01 (`Zero_Trust_Home_Lab__LXC_101`).** Built LXC 101
on `pve-n95` to run Omada Controller v6 (with Portainer Agent).
Encountered `INC-LXC101-NET-01` (bridge-vids), `INC-MONGO-SHUTDOWN-01`
(120 s startup down), `INC-DNS-POISON-01` (resolv.conf sovereignty).
Established the "Silver" hardened image baseline (`audit_secure.sh`,
`verify_security.sh`, UFW default-deny, Fail2Ban with systemd backend,
unattended-upgrades with Docker:codename origin, SSH off-by-default).

**2026-01 → 2026-02 (`MASTER_GUIDE - replicate proxmox caddy
tailscale`, `Lobotomy_-_N305_Proxmox_OPNsense_Transition`).** Built
LXC 100 — unprivileged Tailscale gateway with Caddy. Devised the
"Lobotomy" procedure (this document §5.1) to migrate OPNsense from
N305 bare-metal into a virtualized VM **without** secondary hardware.
Hit `INC-ARP-SHOCK-01`, `INC-SSH-KILLSWITCH-01`, `INC-CADDY-CERT-01`.
First end-to-end remote access via `whale-mulley.ts.net`.

**2026-02 (`MIGRATION_-_Network_Migration_Execution_Checklist`).**
Codified the migration as Phases 0–8 (Lifeboat → Lockdown). Defined
break-glass via VLAN `120_ESCAPE` + captive portal + lifeboat switch
port.

**2026-04 → 2026-05 (`AdGuard_Home_vs_Pi-hole_Comparison`,
`PROXMOX___Omada_Setup` v2, `Homelab_Monitoring_Solutions`).** Decided
DNS architecture: AdGuard Home in a `vmbr2` DMZ jail outside the
OPNsense VM, Cloudflare `1.1.1.2` upstream over DoT, Unbound retained
as failover with `serve-expired` + `prefetch`. Comparison to Pi-hole
(table in §11.4) chose AdGuard for parental-control UX. Sketched the
monitoring stack (Prometheus / Grafana / Loki / Alertmanager) as
LXC 103 on N95.

**2026-05 (`TOP_VPN…Secure_VPN_Domain_and_DNS_Setu`,
`OPNSENS_Deep_Research`).** Most recent state captured in this bible:

* Confirmed the Brother MFC-J5320DW placement in VLAN 50 + the IPP-only
  policy + scanner-disable + PCAP-driven port narrowing.
* Confirmed AdGuard outside OPNsense VM + `serve-expired` failover
  pattern.
* Confirmed unRAID NAS plan + RAM-cache + read-ahead tuning, and that
  the TRUE bottleneck is the gigabit fabric — hence the 2× SG2210XMP-M2
  upgrade landing **before** the NAS goes hot.
* Designed the future WireGuard server on OPNsense as a "second-key"
  remote-access path.

**Now (2026-05-05).** WhiteLab repository established (PRs #1–#3
merged). This bible is the synthesis. Next up:

1. (`whitelab/feature/iac-bootstrap`) Author the Terraform / Ansible
   skeleton that this document directly translates into.
2. Decide the AdGuard DMZ subnet (move off `192.168.20.0/24`, e.g.
   `192.168.25.0/24`) and create the `vmbr2 / opt2-DMZ` interface in
   OPNsense.
3. Replace temp migration "pass any → any" rules with the permanent
   per-VLAN profiles in §5.4.
4. Stand up LXC 102 (Portainer Server) and split the responsibilities
   currently hosted in LXC 100.
5. Stand up the AdGuard jail and flip Unbound into forward-mode with
   `serve-expired = yes` + `prefetch = yes`.
6. Deploy the WireGuard server profile in §5.9.1.
7. Schedule the 2× SG2210XMP-M2 swap window and hot-cut per §9.7.
8. Bring up the unRAID NAS and the monitoring LXC 103.
9. Install Zenarmor with the offload-disabled, RSS-tuned baseline.

---

## 16. WhiteLab IaC implications

This bible is the *spec* the WhiteLab IaC must reproduce idempotently.
Concrete demands on the IaC layer:

1. **One canonical anonymizer scrub-list** (next section), enforced by a
   pre-commit hook before any artefact under `infra/exports/` can be
   committed.
2. **Two base LXC images** as Packer / `pct` recipes:
   * `IMG-DEB12-HARDENED-v1`.
   * `IMG-DEB12-DOCKER-v2`.
3. **Declarative LXC objects** for `100`, `101`, `102` (planned),
   `103` (monitoring, planned), `105` (AdGuard, planned), each with
   their network, resources, features, mounts, startup ordering and
   audit-script expectations.
4. **Declarative OPNsense `config.xml`** broken into per-domain SOPS-
   encrypted slices (interfaces, aliases, rules, DHCP, DNS, services,
   users, system tunables, certs). Reassembled by a generator that
   emits the same `config.xml` schema OPNsense expects, then deployed
   with the `os-api-backup` plugin's restore endpoint.
5. **Declarative Omada port profiles + wired networks** via the Omada
   API (the controller exposes a v5 API we can drive from a
   small Python module).
6. **Ansible playbooks** for the Proxmox host hardening (§6) — one
   role per concern (repos, sysctl, Fail2Ban, cluster firewall, SSH
   killswitch, 2FA enrolment, network bridges, unattended-upgrades).
7. **Pre-commit gate** (`pre-commit` framework + `ggshield`/`gitleaks`
   * the local anonymizer) blocking any commit that contains a real
   MAC / Tailscale node ID / public IP / internal hostname / ULA
   /tailnet name.
8. **Action-item tracker**:
   * Choose AdGuard DMZ subnet ≠ `192.168.20.0/24`.
   * Drop the `opt7 → opt10` outbound NAT rule once verified safe.
   * Restrict OPNsense SSH listen interfaces to `opt8` and `opt12` only.
   * Mask both `ssh.socket` and `ssh.service` on N95 (parity with N305).
   * Enable TOTP on OPNsense root.
   * Convert all dynamic DHCP leases to static before any cable cut.
   * PCAP the printer and remove `9100`/`515` if unused.
   * Replace temp "pass any → any" migration rules with the permanent
     per-VLAN profiles in §5.4.
   * Move Unbound to forward-mode + enable `prefetch` + `serve-expired`.
   * Upgrade the N305 Proxmox to match N95's PVE 9.1.4 / kernel
     6.17.4-2-pve.

---

## 17. Anonymizer scrub list

The pre-commit anonymizer must match and replace **at least** the
following before any artefact lands in this repo:

* MAC addresses: `[0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5}` → `XX:XX:XX:XX:XX:XX`.
* Tailscale tailnet name: `whale-mulley` → `<tailnet>`.
* Tailscale FQDN suffix: `.whale-mulley.ts.net` → `.<tailnet>.ts.net`.
* Tailscale node identifiers (any `-n95-`/`-n305-` host token tied to a
  user-chosen prefix).
* Tailscale 100.64.0.0/10 ULA range and `fd7a:115c:a1e0::/48` IPv6 ULA.
* Public WAN IPv4 addresses (anything matching the user's known ISP
  range).
* Personal account names: real first/last name fragments, GitHub login
  `ricardo-david-francisco`, email addresses.
* Internal hostnames distinct from the canonical role names used in
  this document (`pve-n95`, `pve-n305`, `Omada-Controller`,
  `tailscale-lxc`).
* All RFC1918 subnets specific to this deployment (`192.168.10.0/24`
  through `192.168.150.0/24`, plus `192.168.100.0/24`,
  `192.168.110.0/24`, `192.168.120.0/24`).
* OUI fragments leaking vendor identity in real exports
  (`BC:24:11:` for Proxmox VirtIO, plus the EAP/SG2008 OUIs).
* Passwords / TOTP seeds / API keys / WireGuard keys / age keys.
* OPNsense API key/secret pairs.
* Cloudflare account tokens.

The anonymizer tags every replacement with a deterministic placeholder
so cross-document references survive.

---

## 18. Provenance

This document is a synthesis of, and supersedes:

* `docs/research/00-infra-inference-history.md` (initial, thinner
  version merged in PR #3).
* The full `01_Gemini_Chats/` tree of `ricardo-david-francisco/Home_Infra`
  (24 markdown files, ~97 415 lines) — cloned out-of-tree to
  `~/.cache/whitelab-research/Home_Infra` and never committed.
* The seven long-form chat exports under `.Gemini_Chats_Home_Infra/`
  in this workspace (~28 398 lines), prioritized in this order per
  user instruction:
  1. `TOP_VPN_FUNDAMENTAL_Secure_VPN_Domain_and_DNS_Setu_2026-05-05.txt`
     (most recent — latest state of the deployment).
  2. `OPNSENS_Deep_Research_Agent_Ready_For_Test_2026-05-05.txt`.
  3. `PARAMOUNT___Lobotomy___N305_Proxmox_OPNsense_Trans_2026-05-05.txt`.
  4. `FUNDAMENTAL___PROXMOX___Omada_Setup_2026-05-05.txt`.
  5. `FUNDAMENTAL___UTILIZADO___SEGUIR_ESTE___Zero_Trust_2026-05-05.txt`.
  6. `FUNDAMENTAL___AdGuard_Home_vs__Pi_hole_Comparison_2026-05-05.txt`.
  7. `Homelab_Monitoring_Solutions_2026-05-05.txt`.

No raw chat content is reproduced verbatim. No secrets (passwords,
keys, tokens, MACs, public IPs, tailnet IDs, account names) are
committed. Numeric tunables, port numbers, VLAN IDs, file paths and
configuration keys are preserved exactly because they are the design
contract this bible enforces.
