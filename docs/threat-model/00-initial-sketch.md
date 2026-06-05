# 03 — Threat Model (initial sketch)

Status: **Draft**. To be expanded once devices begin contributing exports.

## Assets

1. Network availability of the home (WAN, internal routing, Wi-Fi).
2. Confidentiality of household personal data on `20_SECURE`, `30_SERVERS`,
   `110_SERVICES`.
3. Integrity of management plane: OPNsense, Proxmox, Omada controller.
4. Continuity of `40_ADMIN` "bunker" as the only path to OPNsense GUI.

## Trust zones (recap of the VLAN model)

- **Tier 0 — Bunker**: `40_ADMIN`, `100_PROXMOX`, `140_PROXTER`. No internet;
  only path to hypervisor + firewall GUIs.
- **Tier 1 — Trusted**: `20_SECURE`.
- **Tier 2 — Internal services**: `30_SERVERS`, `110_SERVICES`.
- **Tier 3 — Family / media**: `50_MEDIA`, `130_KIDS`.
- **Tier 4 — Untrusted**: `70_IOT`, `80_CAMERA`, `90_GUEST`, `150_EMPLOYER`,
  `60_QUARANTINE`.
- **Tier X — Dead ends**: `999_BLACKHOLE`, `1` (default unused).

## Adversaries considered

| Adversary                                  | Capability                                                                  | Primary mitigation                                                                       |
| ------------------------------------------ | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Opportunistic internet scanner             | Hits WAN; brute-force, CVE scans.                                           | OPNsense default-deny; no exposed admin services; WireGuard.                             |
| Compromised IoT device                     | LAN-side; scans; tries lateral movement.                                    | VLAN segmentation; egress-only rules; client isolation.                                  |
| Compromised personal laptop on `20_SECURE` | Has user-level network access; can read their own files.                    | Stateful per-VLAN rules; admin GUI unreachable from `20_SECURE`.                         |
| Compromised GitHub account / token         | Reads any repo blob ever pushed; can push.                                  | Sanitized-only repo; branch protection; commit signing (later).                          |
| Lost/stolen workstation                    | Physical access to `vault/` and keys.                                       | Full-disk encryption; `vault/` inside an encrypted container; OS keyring locked at rest. |
| Insider at GitHub / cloud provider         | Reads private blobs.                                                        | Sanitization is the control. Treat repo as semi-public.                                  |
| Family member curiosity                    | Casual access to a shared device.                                           | Workstation lock; separate OS user; `vault/` encrypted at rest.                          |

## Non-goals (explicitly out of scope here)

- Defense against a nation-state with persistence on the workstation.
- Defense against a fully compromised OPNsense (that would require an HSM
  and out-of-band attestation we do not have).
- Recovery from key loss without a documented backup procedure (tracked
  separately).

## Open questions to resolve before first device export lands

1. Where do `age`/GPG private keys live, and how are they backed up?
2. Is `vault/` a plain folder on an encrypted disk, or a per-folder
   encrypted container (e.g., VeraCrypt, `gocryptfs`, `age` per-file)?
3. Do we want commit signing (SSH or GPG) on `master` from day one?
4. Pre-commit hook installation: per-clone manual, or a `make bootstrap`?

These will be answered in the runbook PRs.
