# 01 — Anonymization Pipeline (sanitization of raw exports)

Status: **Proposed**. Implementation tracked on a follow-up branch.

## Problem

Raw exports from OPNsense (`config.xml`), Proxmox (`/etc/pve/...`), and
Omada (controller backups + logs) contain secrets, real device names, MAC
addresses, public IPs, and DDNS hostnames. None of this can be pushed.

We need a **deterministic, reproducible** transformation:

```text
vault/raw/<device>/<file>     ──▶  infra/<device>/exports/<file>.sanitized.<ext>
```

Properties required:

1. **Deterministic** — the same real value maps to the same placeholde
   every time, so diffs across snapshots remain meaningful.
2. **Reversible only on the workstation** — an encrypted `secrets-map.yaml`
   in `vault/` lets the operator restore real values when applying a change
   back to the device. The map never leaves the workstation.
3. **Fail-closed** — if the tool encounters an unknown sensitive shape, it
   refuses to emit output. It is better to break the pipeline than to leak.
4. **Format-aware** — XML, JSON, YAML, and `key = value` configs are parsed
   structurally; we do not rely on regex over arbitrary text alone.

## Tooling choice

Python 3.11+ in `tools/anonymize/`. Single-purpose CLI:

```text
python tools/anonymize/cli.py \
  --input  vault/raw/opnsense/config-2026-05-04.raw.xml \
  --output infra/opnsense/exports/config-2026-05-04.sanitized.xml \
  --map    vault/secrets-map.yaml \
  --profile opnsense
```

Profiles encode device-specific rules. Initial profiles:

| Profile      | Targets (non-exhaustive)                                                                   |
| ------------ | ------------------------------------------------------------------------------------------ |
| `opnsense`   | `<password>`, `<authorizedkeys>`, `<privatekey>`, `<pre-shared-key>`, `<apikey>`,          |
|              | WAN public IP, DDNS hostnames, WireGuard private/public keys, IPsec PSKs,                  |
|              | RADIUS shared secrets, local user descriptions, certificate private blocks.                |
| `proxmox`    | `/etc/pve/priv/*`, ACME account keys, root password hash, replication tokens,              |
|              | host SSH keys, cluster join secrets, real hostnames, MAC addresses on bridges.             |
| `omada`      | Admin credentials, cloud account email, RADIUS secret, captive portal secrets,             |
|              | real client MACs and hostnames in logs/exports.                                            |
| `wireguard`  | All `[Peer] PublicKey`, `PresharedKey`, real `Endpoint`s, allowed-IPs of personal peers.   |

## Placeholder scheme

Stable, descriptive, sortable placeholders. Examples:

- Passwords / hashes → `__SECRET__<sha1[:8]>__`
- Private keys / certs → entire block replaced with `-----BEGIN REDACTED-----\n<sha1[:8]>\n-----END REDACTED-----`
- WAN public IP → `__WAN_PUBLIC_IP__`
- DDNS hostname → `wg.example.invalid`
- LAN host names → `host-<sha1[:6]>` with mapping in `secrets-map.yaml`
- MAC addresses → `02:00:00:<sha1[:6] formatted>` (locally-administered prefix; preserves OUI shape)

The mapping is computed once from `secrets-map.yaml` (or appended on first
sight), so the placeholder for a given real value is stable across runs.

## Verification (`tools/anonymize/verify.py`)

A second tool used as a pre-commit gate. It runs over **everything currently
staged** and refuses the commit if any of the following match:

- A regex bank for: PEM blocks, JWTs, AWS-style keys, bcrypt/argon2 hashes,
  Cloudflare token shape, common password XML tags with non-empty content.
- An entropy threshold over long base64-looking strings outside known
  placeholder shapes.
- Any path under `vault/` accidentally staged.

`verify.py` will be wired as a `pre-commit` hook (see
`docs/runbooks/02-pre-commit-setup.md`).

## What does **not** belong in the pipeline

- Anything binary that we cannot meaningfully sanitize (Proxmox VM disk
  images, Omada full database backups). These stay in `vault/` permanently.
- Live secrets we want to keep version-controlled. Use a separate, encrypted
  store outside this repo (1Password, Bitwarden, or `age`-encrypted blobs in
  a different private repo). This repo is **review material**, not a vault.

## Encrypted reverse-map (PR #24)

The reverse-map (`{placeholder → real value}`) is now persisted as
`vault/anonmap.age` instead of plaintext JSON. The crypto layer lives
in `tools/anonymizer/secret_map.py` and uses [age](https://age-encryption.org)
because:

- single static binary, no daemon, no key-management service;
- one identity file is enough for our threat model (laptop +
  out-of-band paper backup);
- format is well-documented and reproducible across distros, so a
  fresh Ubuntu LTS VM is sufficient to read the map.

### Key resolution orde

When `load_map` / `save_map` see a path ending in `.age`, they call
`resolve_identity_key()`, which walks three sources in order:

1. an explicit `--key-file` argument, if given;
2. the `WHITELAB_ANONMAP_KEY` environment variable;
3. `vault/anonmap.key` on disk (gitignored).

If none of those are present the tool exits with a clear error rathe
than silently falling back to plaintext. A foreign identity yields a
crypto-level error from `age` itself; round-trip tests in
`tests/anonymizer/test_secret_map.py` exercise both paths.

### Key rotation procedure

1. `age-keygen -o vault/anonmap.key.new` on the operator workstation.
2. Decrypt the existing map with the old key:
   `python -m tools.anonymizer.rehydrate --map-file vault/anonmap.age
   --key-file vault/anonmap.key`.
3. Re-encrypt by setting `WHITELAB_ANONMAP_KEY=$PWD/vault/anonmap.key.new`
   and re-running `python -m tools.anonymizer.anonymize` over `infra/`.
4. `mv vault/anonmap.key.new vault/anonmap.key`, then commit the
   updated `vault/anonmap.age`. The `.key` file is **never** committed.
5. Distribute the new identity to your offline backup (paper / hardware
   key vault / second machine). Do not transmit it over chat.

### Round-trippable secrets (PR #24)

The regex catalog now also redacts plaintext `password`,
`Authorization`/`Bearer`, `api_key`, and generic `*_secret`/`*_token`
assignments, with an `is_real_secret` validator that ignores obvious
non-secrets (`changeme`, `${VAR}`, etc.) and already-redacted
placeholders. This is what makes the snippet → draft-PR funnel safe:
the funnel can refuse a paste containing a real password without
having to re-implement the regex set.
