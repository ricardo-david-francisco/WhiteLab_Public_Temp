# Fortress Agent (LXC 104 on N95)

The home-side daemon. Pulls anonymized configs into PRs, applies merged
PRs after a TOTP unlock, signs every audit artifact.

| File                             | Purpose                                                                             |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| `agent.py`                       | Main loop / state machine (idle → poll → apply).                                    |
| `adapters/base.py`               | `TargetAdapter` protocol that every target implements.                              |
| `adapters/opnsense.py`           | OPNsense REST adapter (no SSH).                                                     |
| `adapters/proxmox.py`            | Proxmox API adapter (no SSH).                                                       |
| `adapters/omada.py`              | Omada controller v6 OpenAPI adapter.                                                |
| `vault/`                         | tmpfs-mounted secrets directory layout (docs only — secrets are *never* committed). |
| `systemd/fortress-agent.service` | systemd unit definition.                                                            |

## Dataflow

```text
   GitHub master                                  TOTP webhook
        │                                              │
        ▼                                              ▼
   ┌────────────────────────────────────────────────────┐
   │   agent.py main loop on LXC 104                    │
   │     1. poll for PRs labeled `apply:approved`       │
   │     2. fetch merged commit, verify signature       │
   │     3. wait for TOTP unlock (10-min window)        │
   │     4. select adapter by changed paths             │
   │     5. rehydrate via tools/anonymizer/rehydrate    │
   │     6. adapter.stage()  → schema/lint              │
   │     7. adapter.backup() → /run/fortress/backup/    │
   │     8. adapter.apply()                             │
   │     9. health check; on fail → adapter.rollback()  │
   │    10. sign + push audit log to audit/agent-log    │
   └────────────────────────────────────────────────────┘
```

## Vault layout (`/run/fortress/`, tmpfs)

```text
/run/fortress/
├── api-tokens/
│   ├── opnsense-pull
│   ├── opnsense-apply
│   ├── pve-n95-pull
│   ├── pve-n95-apply
│   ├── pve-n305-pull
│   ├── pve-n305-apply
│   ├── omada-pull
│   └── omada-apply
├── anonmap.json          ← decrypted from anonmap.age at boot via TOTP
├── signing-key.age       ← never on disk in cleartext
├── backup/<timestamp>/
└── staging/<sha>/
```

## State machine

```text
IDLE ──poll PR feed──▶ DRIFT_CHECK ──drift?──▶ open chore PR ──▶ IDLE
  │                          └─no drift──▶ IDLE
  │
  └─apply:approved label──▶ AWAIT_TOTP ──ok──▶ STAGE ──▶ BACKUP ──▶ APPLY
                                                                       │
                                              ROLLBACK ◀─unhealthy─────┘
                                                       │
                                              SIGN_AUDIT ◀─healthy────▶ IDLE
```
