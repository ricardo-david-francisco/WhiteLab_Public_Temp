# 02 — SSH-less Sync Workflow

Status: **Proposed**. Pick one transport per device on the implementation branch.

## Constraint

No device exposes SSH. We still need to:

- **Pull** raw configs and logs to the workstation for review.
- **Push** reviewed changes back to the device.

We must do this without weakening the security posture (no opening 22/tcp
"just for the audit").

## Transports considered

| #  | Transport                                            | Pull | Push | Trust assumption                                            | Verdict                       |
| -- | ---------------------------------------------------- | ---- | ---- | ----------------------------------------------------------- | ----------------------------- |
| T1 | OPNsense Web GUI export + manual download via HTTPS  | ✅   | ⚠️   | Browser session on `40_ADMIN` only.                         | Baseline. Always available.   |
| T2 | OPNsense REST API (`/api/...`) over HTTPS, API key   | ✅   | ✅   | API key scoped read-only or read-write per workflow.        | Strong primary for OPNsense.  |
| T3 | Proxmox API (`/api2/json`) with API token            | ✅   | ✅   | Token with the minimum role (`PVEAuditor` for read).        | Strong primary for Proxmox.   |
| T4 | Omada Controller Open API                            | ✅   | ⚠️   | Token + site scope; some operations still GUI-only.         | Use where supported.          |
| T5 | Tailscale tailnet from workstation to LXCs           | ✅   | ✅   | Already deployed; ACL-restricted to admin device + LXC tag. | Excellent for the LXCs.       |
| T6 | WireGuard road-warrior tunnel (already configured)   | ✅   | ✅   | Tunnel terminates on OPNsense; reachable subnets via FW.    | Use when off-LAN.             |
| T7 | USB sneakernet (encrypted volume)                    | ✅   | ✅   | Physical access only.                                       | Break-glass / first export.   |
| T8 | Google Cloud Storage object as drop box              | ✅   | ✅   | Per-object IAM; client-side `age` encryption mandatory.     | Optional async channel.       |

## Recommended per-device defaults

- **OPNsense (N305 host VM)**:
  - Primary: **T2** (REST API over HTTPS, API key on `40_ADMIN` only).
  - Fallback: **T1** for full XML config download.
  - First-time: **T7** (USB) if the API is not yet enabled.

- **Proxmox N305 (host)**:
  - Primary: **T3** with a dedicated API token (`audit@pam!whitelab-ro`),
    read-only role for pulls; a separate token for pushes only when applying
    a reviewed change.
  - Fallback: GUI download of `/etc/pve/...` archives.

- **Proxmox N95 (host)** — same as N305.

- **LXCs (Tailscale reverse proxy, Omada controller, etc.)**:
  - Primary: **T5** Tailscale, with ACLs restricting the workstation tag
    (`tag:admin-ws`) to only those LXC tags it needs. Use HTTPS to the
    container's local API where one exists; otherwise file copy via a
    purpose-built minimal endpoint (HTTPS + mTLS), **not** SSH.

- **Omada Controller (LXC)**:
  - Primary: **T4** Open API for what it supports (sites, devices, clients).
  - Plus: scheduled **controller backup** to a path that the LXC exposes via
    Tailscale-only HTTPS; workstation pulls the encrypted backup.

- **Off-LAN access**: **T6** (your existing WireGuard) into `40_ADMIN`,
  then any of T2/T3/T4/T5 over the tunnel.

## Authentication hardening

- **No passwords in scripts.** Tokens/API keys live in OS keyring (Windows
  Credential Manager via `keyring` Python lib) referenced by name only.
- **Per-purpose tokens**: separate read-only "audit" token and a short-lived
  "apply" token. The apply token is created at change time and revoked
  immediately after.
- **Scope minimization**: every token is bound to the minimum role and,
  where supported, source-IP-restricted to the workstation's static lease
  on `40_ADMIN`.
- **mTLS** on any custom endpoint we expose on LXCs. Client cert lives in
  the workstation keyring; CA is the OPNsense or a dedicated `step-ca`.

## The Google Cloud option (T8)

Only as an **asynchronous, encrypted drop box** — never as a primary control
plane. Pattern:

1. Device-side cron exports → `age -r <pubkey>` encrypts → uploads to a
   GCS bucket with a 7-day object lifecycle and uniform bucket-level access.
2. Workstation pulls the encrypted blob, decrypts locally, runs the
   anonymizer, then commits the sanitized result.

This is useful when the device cannot initiate a Tailscale/WireGuard
session but can reach the internet outbound (e.g., a future appliance).

## What we deliberately do not do

- No SSH re-enablement "just for this".
- No device-initiated `git push` to GitHub. Devices never see this repo.
- No long-lived credentials checked into anything, anywhere.
