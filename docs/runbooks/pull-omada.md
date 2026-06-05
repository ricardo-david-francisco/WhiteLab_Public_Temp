# pull-omada — read Omada / Wi-Fi state without SSH

> Concrete steps for reading the Omada controller state (AP status,
> client list, event log) through the fortress-agent's read-only
> adapter. Companion to [`apply-omada.md`](apply-omada.md). See also
> the learning guide
> [`docs/learning/01-zero-trust-explained.md`](../learning/01-zero-trust-explained.md)
> §7.3 (worked example: debugging Wi-Fi).

## Purpose

You need to inspect the **live** Wi-Fi fabric:

* Find why a client keeps disconnecting (roaming? RSSI? deauth?).
* Audit which APs are online and which firmware they run.
* Export the controller backup to keep a vault snapshot.

Reads use a dedicated OpenAPI v6 token with read scopes only. They
never touch SSH or the controller's web session cookie.

## Pre-conditions

* You are on the tailnet.
* The fortress-agent (CT-104) is running.
* `ratchet` is installed on your laptop.
* The Omada read-only OpenAPI v6 token is provisioned in the agent's
  tmpfs vault under `/run/fortress/api-tokens/omada-readonly`. If
  not, see [`rotate-secrets.md`](rotate-secrets.md).

## Steps

### A. List APs and their status

```text
ratchet pull omada aps
```

Calls
`GET /openapi/v1/{omadacId}/sites/{siteId}/aps` and renders a table:
name, model, IP, firmware, uptime, client count, mesh role.

### B. List active clients

```text
ratchet pull omada clients --vlan IOT
ratchet pull omada clients --ssid WhiteLab-Personal --rssi-below -75
```

Useful filters: `--vlan`, `--ssid`, `--ap`, `--rssi-below`,
`--idle-above 1h`.

### C. Read events / controller log

```text
ratchet pull omada events --since 24h
ratchet pull omada events --client iot-lr3-thermostat --since 6h
ratchet pull omada events --ap AP-LR3-NorthWall --severity warn --since 12h
```

Returns the controller's event timeline (associations, deauths,
roaming, firmware events, controller-side errors).

### D. Export the controller config (vault snapshot)

```text
ratchet pull omada backup --out vault/omada/$(date +%F)/controller.bak
```

The file is the controller's native backup format. Restore is via
`apply-omada.md`. The export lands in `vault/` only — it must never
be committed.

## Verification

* `ratchet pull omada aps` returns non-empty rows.
* `ratchet audit list --kind pull --target omada --last 1d` shows the
  read.

## Rollback

Reads are non-mutating. Nothing to roll back.

If the read fails with `401`, the OpenAPI v6 token has expired or was
rotated; see [`rotate-secrets.md`](rotate-secrets.md).

## Audit trail

Entries include the OpenAPI endpoint, query string, response size,
and `age` signature, exactly as for the OPNsense pulls.
