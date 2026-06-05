# pull-opnsense — read OPNsense state without SSH

> Concrete steps for reading OPNsense state (config XML, firewall logs,
> live diagnostics) through the fortress-agent's read-only adapter.
> Companion to [`apply-opnsense.md`](apply-opnsense.md). See also the
> learning guide
> [`docs/learning/01-zero-trust-explained.md`](../learning/01-zero-trust-explained.md)
> §7 (the observe path).

## Purpose

You need to inspect the **live** OPNsense configuration or logs:

* Audit firewall rules vs. the version committed to this repo.
* Debug a connectivity issue (which rule actually matched?).
* Pull the latest `config.xml` to start a new change branch.

Reads use a dedicated read-only API key. They never touch SSH.

## Pre-conditions

* You are on the tailnet (`tailscale status` shows `tag:operator`).
* The fortress-agent (CT-104) is running.
* `ratchet` CLI is installed on your laptop
  (`tools/fortress-agent/cli/ratchet`).
* The OPNsense read-only API key is provisioned in the agent's tmpfs
  vault under `/run/fortress/api-tokens/opnsense-readonly`. If not,
  see [`rotate-secrets.md`](rotate-secrets.md).

## Steps

### A. Pull the full config XML (anonymized)

```text
ratchet pull opnsense config --review \
  --out vault/opnsense/$(date +%F)/config.anon.xml
```

Under the hood the agent calls `GET /api/core/backup/download/this`,
streams the raw XML to a tmpfs buffer, runs
`tools/anonymizer/anonymize.py` over it, and forwards the scrubbed
copy to your laptop. The raw XML never lands on disk on the agent.

### B. Pull the raw config XML (vault-only)

For a backup snapshot you sometimes want the *unredacted* XML stored
locally. Add `--raw`:

```text
ratchet pull opnsense config --raw \
  --out vault/opnsense/$(date +%F)/config.raw.xml
```

The file lands in your `vault/` directory (gitignored). It must never
be committed; the anonymization-gate workflow will reject it on PR if
you do.

### C. Tail the firewall log

```text
ratchet pull opnsense log firewall --since 1h
ratchet pull opnsense log firewall --filter "src=192.168.40.0/24" --since 30m
```

Calls `GET /api/diagnostics/log/firewall` with a since-cursor. Output
is plain text, one event per line. Severity / interface / source /
destination columns are preserved.

### D. Diff live vs. repo

```text
diff <(ratchet pull opnsense config --review --stdout) \
     infra/opnsense/config.anon.xml
```

A non-empty diff means **drift**. Either:

* Update the repo (open a PR with the new XML, document why).
* Or revert the live change (open a PR that re-applies the repo
  version, label `apply:approved`, TOTP).

## Verification

* The pull command exits 0.
* The output file is non-empty and starts with `<?xml` (config) or
  contains timestamped lines (logs).
* The agent records the read in `audit/reads/<timestamp>-<who>.json`
  (signed). Inspect with `ratchet audit list --kind pull`.

## Rollback

Reads are non-mutating. There is nothing to roll back.

If the read **failed** because the read token is expired, run
[`rotate-secrets.md`](rotate-secrets.md) to regenerate the OPNsense
read-only key.

## Audit trail

Every pull is logged on the agent. The log entry includes:

* Timestamp.
* Caller tailnet identity (`tag:operator` + node name).
* Endpoint called (`/api/core/backup/download/this`).
* Anonymization mode (`--raw` or `--review`).
* Output bytes.
* `age` signature.

To read your own pull history:

```text
ratchet audit list --kind pull --target opnsense --last 30d
```
