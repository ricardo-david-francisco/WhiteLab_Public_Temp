# Omada controller — exports + deltas

* `exports/` — anonymized snapshots of:
  * `controller.cfg.anonymized` — the controller backup (with device
    MACs, AP serials and any RADIUS PSK redacted).
  * `port-profiles.anonymized.yaml` — the port profile catalog
    (`Proxmox_Trunk`, `AP_Trunk`, `Office_Hybrid`, `All_Lifeboat`,
    `Blackhole`, per-VLAN access).
  * `wireless-networks.anonymized.yaml` — SSID-to-VLAN mapping.
  * `wired-networks.anonymized.yaml` — per-VLAN settings.
* `deltas/` — Jinja fragments to mutate the above.

The agent's adapter calls Omada's REST v6 API at
`https://omada.<TAILNET>.ts.net:8043/api/v6/...`, never SSH.

See [`docs/architecture/2.0-fortress-design.md`](../../docs/architecture/2.0-fortress-design.md) §7.3.
