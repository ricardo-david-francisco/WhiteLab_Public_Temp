# CT-105 — AdGuard Home (DMZ recursive resolver)

> **Status: design placeholder.** This directory holds the worked
> example referenced in
> [`docs/architecture/2.0-fortress-design.md`](../../../docs/architecture/2.0-fortress-design.md) §11.
> The CT is **not** deployed yet. The full apply lands when the
> OPNsense + Proxmox adapters ship (PR3 + PR4).

## What it is

A **resolver-only** AdGuard Home instance running in a Docker container
inside an LXC on N305. It serves DNS for the SECURE / IOT / GUEST /
PERSONAL / WORK VLANs, talking upstream to Quad9 / Cloudflare over DoT.
The OPNsense unbound resolver remains the primary; AdGuard sits on a
*new* DMZ subnet (`192.168.25.0/24`, vmbr2) and is reachable only from
OPNsense and the Caddy LXC, never directly from clients.

| Field           | Value                                                                                              |
| --------------- | -------------------------------------------------------------------------------------------------- |
| Host            | N305 (`HOST_SECONDARY`)                                                                            |
| Lineage         | `IMG-DEB12-DOCKER-v2`                                                                              |
| VMID            | 105                                                                                                |
| Hostname        | `adguard-dmz`                                                                                      |
| Resources       | 1 vCPU, 512 MiB RAM, 6 GiB disk                                                                    |
| Network         | bridge `vmbr2`, VLAN-untagged, address `192.168.25.10/24`, gw `192.168.25.1` (OPNsense `vlan_dmz`) |
| Tailscale tag   | `tag:server`                                                                                       |
| External access | Caddy reverse proxy on LXC 100 (`adguard.<TAILNET>.ts.net`)                                        |

## Files in this directory

| File                  | Purpose                                                                |
| --------------------- | ---------------------------------------------------------------------- |
| `ct.yaml`             | declarative payload for `POST /nodes/n305/lxc`                         |
| `compose.yaml`        | the AdGuard container stack                                            |
| `adguard-config.yaml` | upstream DNS, bind, log, listen                                        |
| `audit_ct105.sh`      | network-identity / security baseline / app-layer / reverse-proxy audit |

## Apply sequence

See [`docs/architecture/2.0-fortress-design.md`](../../../docs/architecture/2.0-fortress-design.md) §11 step-by-step
(10-step plan). The required PRs in order are:

1. **Network delta** (this repo): `infra/opnsense/deltas/2026-05-XX-vmbr2-dmz-interface.xml.j2`,
   `infra/proxmox/n305/exports/interfaces.anonymized` updated.
2. **CT delta**: this directory's `ct.yaml` + `compose.yaml`.
3. **Caddy delta**: `infra/caddy/Caddyfile.j2` adds the `adguard.*` vhost.
4. **DNS failover delta**: `infra/opnsense/deltas/2026-05-XX-vmbr2-dns-failover.xml.j2`.

Each PR lands independently with its own `apply:approved` label and
TOTP unlock.
