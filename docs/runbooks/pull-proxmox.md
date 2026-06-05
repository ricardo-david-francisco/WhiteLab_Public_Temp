# pull-proxmox — read Proxmox state without SSH

> Concrete steps for reading Proxmox host and LXC state (CT inventory,
> resource usage, container console log, host config) through the
> fortress-agent's read-only adapter. Companion to
> [`apply-proxmox.md`](apply-proxmox.md). See also
> [`docs/learning/01-zero-trust-explained.md`](../learning/01-zero-trust-explained.md)
> §7.

## Purpose

You need to inspect the **live** Proxmox state:

* See which CTs are running on which node, and at what resource use.
* Read the console log of a flaky container without `pct console`.
* Pull the host network / firewall config to diff against the repo.

Reads use a `PVEAuditor`-scoped API token. No SSH, no `root@pam`
password.

## Pre-conditions

* You are on the tailnet.
* The fortress-agent (CT-104) is running.
* `ratchet` is installed on your laptop.
* Per-node read-only API tokens are provisioned in the agent's
  tmpfs vault under `/run/fortress/api-tokens/pve-{n95,n305}-audit`.

## Steps

### A. List containers on a node

```text
ratchet pull proxmox cts --node n305
ratchet pull proxmox cts --node n95
```

Calls `GET /api2/json/nodes/<node>/lxc`. Renders vmid, name, status,
uptime, cpu %, memory used / configured, swap, network in/out, disk.

### B. Read a container's console log

```text
ratchet pull proxmox ct 105 --log --tail 200
```

Calls `GET /api2/json/nodes/<node>/lxc/105/log` (last N lines, plus
recent journal entries). Useful when a container won't start cleanly.

### C. Read a container's effective config

```text
ratchet pull proxmox ct 105 --config
```

Returns the live `pct config 105` output (JSON). Diff against
`infra/lxc/ct-105-adguard-dmz/ct.yaml` to detect drift.

### D. Read host-level config

```text
ratchet pull proxmox host --node n305 --section network
ratchet pull proxmox host --node n305 --section firewall
ratchet pull proxmox host --node n305 --section storage
```

Maps to the corresponding `/api2/json/nodes/<node>/{network,firewall,storage}`
endpoints. Output is JSON; pipe through `jq` for readability.

### E. Snapshot inventory

```text
ratchet pull proxmox snapshots --node n305 --vmid 105
```

Lists the snapshots created by previous applies (each apply takes
one — see learning guide §6.10).

## Verification

* The pull commands exit 0 and print non-empty rows.
* `ratchet audit list --kind pull --target proxmox --last 1d` shows
  the calls.

## Rollback

Reads are non-mutating. Nothing to roll back.

If the read fails with `401`, the audit token expired; rotate via
[`rotate-secrets.md`](rotate-secrets.md). If the read fails with
`403`, the token is missing the required role on the resource — open
an adapter PR to widen the scope, then rotate.

## Audit trail

Same format as `pull-opnsense.md` and `pull-omada.md`: tailnet
identity, endpoint, response size, `age` signature, written under
`audit/reads/`.
