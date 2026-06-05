# Security Policy & Handling Rules

This document is **normative**. Every commit on every branch must comply.

## 1. Threat model assumed by this repo

Treat the GitHub remote as **hostile-curious**:

- Assume any blob pushed to `origin` is *eventually readable* by an adversary
  (insider at provider, compromised PAT, accidental visibility flip,
  forensic disk recovery on a developer laptop, etc.).
- Therefore: **the repo is for sanitized, review-grade material only.** Raw
  exports stay on the workstation, in `vault/`, which is `.gitignore`d.

## 2. Hard rules (no exceptions)

1. **Never** `git add` anything from `vault/`, `**/raw/`, `**/secrets/`, or any
   file with a `.raw.*` extension. The `.gitignore` enforces this; do not
   override with `git add -f`.
2. **Never** commit:
   - Plaintext passwords, password hashes, PSKs, PSK hints.
   - Private keys, certificates with private material, `*.kdbx`, `*.gpg` private bundles.
   - WireGuard private keys, IPsec PSKs, RADIUS shared secrets.
   - Real public IPs of WAN endpoints (use `WAN_PUBLIC_IP_PLACEHOLDER`).
   - Real DDNS hostnames (use `wg.example.invalid`).
   - Cloudflare API tokens, dynamic DNS credentials.
   - MAC addresses of personal devices (use OUI-only or stable pseudonyms).
   - Email addresses, phone numbers, real names of household members.
3. **Always** run sanitized exports through `tools/anonymize/` before staging.
4. **Always** review `git diff --cached` before every commit on infra files.
5. **Master is append-only history.** No force-push, no rewrites.

## 3. Workflow boundary

```text
┌─────────────────────────────┐         ┌──────────────────────────┐
│ Device (OPNsense, Proxmox,  │         │  Workstation             │
│ Omada, LXCs)                │  pull   │  c:/...//15_WhiteLab/    │
│                             │ ──────▶ │   vault/raw/   (LOCAL)   │
│  Raw exports: config.xml,   │         │      │                   │
│  pveproxy.pem, etc.         │         │      ▼                   │
└─────────────────────────────┘         │   tools/anonymize/       │
                                        │      │                   │
                                        │      ▼                   │
                                        │   infra/.../sanitized    │
                                        │      │  git add/commit   │
                                        │      ▼                   │
                                        │   origin (GitHub)        │
                                        └──────────────────────────┘
```

## 4. If a secret is committed by accident

1. **Treat the secret as compromised.** Rotate immediately on the device.
2. Do **not** rely on `git rm` + new commit — the blob remains in history.
3. Use `git filter-repo` to purge, then `git push --force-with-lease` after
   approval. Document in `PROJECT_HISTORY.md` under an `INCIDENT` heading.
4. Force-push requires explicit owner approval and is the only legitimate
   exception to rule 2.5.

## 5. Identity

Commits use a per-repo local git identity tied to a GitHub `noreply` email.
No work email is used in this repo. See `git config --local --list`.

## 6. Reporting

Any deviation discovered during review must be logged in `PROJECT_HISTORY.md`
with the date, the affected paths, and the remediation action.
