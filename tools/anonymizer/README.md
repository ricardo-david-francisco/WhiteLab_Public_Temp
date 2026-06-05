# Anonymizer

Deterministic, reversible-only-by-the-agent scrub of secrets and
identifying values from configuration files. The repo holds the public
side; the home-side Fortress Agent holds the encrypted map and the
re-hydrator.

## Files

* `anonymize.py` — CLI. Reads a file, scrubs it, appends new mappings
  to the local map (default `./.anonmap.json`, gitignored), writes the
  anonymized file. Idempotent: running on an already-anonymized file is
  a no-op.
* `rehydrate.py` — CLI. Agent-only. Reads a map and an anonymized file,
  emits the plaintext.
* `rules.yaml` — declarative regex set + per-format hooks.
* `lexicon.example.yaml` — the placeholder catalog (no real values),
  committed for humans to read.
* `tests/test_anonymize.py` — round-trip tests.

## Command surface

```bash
# Anonymize an OPNsense config (XML schema-aware).
python -m tools.anonymizer.anonymize \
    --in /tmp/config.xml \
    --out infra/opnsense/exports/config.anonymized.xml \
    --format opnsense_xml \
    --map-file ./.anonmap.json

# Generic text mode (regex rules only).
python -m tools.anonymizer.anonymize \
    --in /tmp/cluster.fw \
    --out infra/proxmox/n95/exports/cluster.fw.anonymized \
    --format text \
    --map-file ./.anonmap.json

# Verify mode (CI gate). Exits non-zero on any cleartext-secret hit.
python -m tools.anonymizer.anonymize --verify infra/

# Re-hydrate (agent-only).
python -m tools.anonymizer.rehydrate \
    --in infra/opnsense/exports/config.anonymized.xml \
    --out /run/fortress/staging/config.xml \
    --map-file /run/fortress/anonmap.json
```

## Map format

JSON. Append-only. Per-class numeric counter:

```json
{
  "version": 1,
  "classes": {
    "MAC": [
      {"id": "MAC_001", "value": "AA:BB:CC:DD:EE:01", "first_seen": "2026-05-05T10:00:00Z"},
      {"id": "MAC_002", "value": "AA:BB:CC:DD:EE:02", "first_seen": "2026-05-05T10:00:01Z"}
    ],
    "PUBLIC_IPV4": [
      {"id": "PUBLIC_IPV4_001", "value": "203.0.113.42", "first_seen": "2026-05-05T10:00:00Z"}
    ]
  }
}
```

The map (`.anonmap.json`) is **never committed**. It is encrypted to
`anonmap.age` for transport between the agent and the offline vault.

## Rules

Two layers in `rules.yaml`:

1. **Regex rules** — generic patterns matched on any `--format text`
   input. Each rule has a `class`, a `pattern`, and an optional
   `validator` (Python callable that confirms the match before
   replacement, e.g. an IPv4 in RFC1918 should *not* match the
   `PUBLIC_IPV4` rule).
2. **Format hooks** — schema-aware Python callables that walk a parsed
   structure (XML, JSON, YAML, INI) and replace specific paths:
   * `opnsense_xml` — the heaviest hook; covers every secret-bearing
     XPath in `config.xml`.
   * `proxmox_tfacfg` — TOTP secrets, WebAuthn descriptors.
   * `proxmox_clusterfw` — comments-embedded hostnames.
   * `omada_db` — MongoDB export internals.
   * `caddy` — log-resolved IPs.

See [`docs/architecture/2.0-fortress-design.md`](../../docs/architecture/2.0-fortress-design.md) §5 for
the full design.
