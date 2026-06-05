# OPA / Conftest policies

Open Policy Agent rules that gate every PR. CI fails (and the agent
refuses to apply) if any policy returns a violation.

* `secrets.rego` — forbid plaintext patterns. Any token that *looks*
  like a real secret (private-key headers, JWT shape, MAC address,
  public IPv4 in a non-allowed block, `.ts.net` FQDNs not equal to
  `<TAILNET>`, etc.) is a hard fail. Mirrors the bible's anonymizer
  scrub list.
* `opnsense.rego` — invariants on OPNsense `config.xml`:
  * No `pass any → any` rule outside the temp-migration window.
  * `60_QUARANTINE` keeps its forced-DNS rules.
  * `40_ADMIN` has no internet-egress rule.
  * Captive portal `EmergencyAccess` exists with `concurrentlogins: 1`.
  * SSH service has a non-wildcard listen-iface list.
* `proxmox.rego` — invariants on Proxmox config:
  * Cluster firewall enabled.
  * `ssh.socket` *and* `ssh.service` masked on every node.
  * 2FA enrolled for the admin user.
  * No LXC `unprivileged: 0` outside the explicit allow-list.
* `lxc.rego` — invariants on LXC specs:
  * Lineage check (HARDENED-v1 or DOCKER-v2 only).
  * `audit_*.sh` and (where required) `verify_security.sh` exist.
  * `bridge-vlan-aware` set when any VLAN tag > 1 is referenced.

Run locally:

```text
opa eval -d infra/policies/ -i <input.json> "data.whitelab.deny"
```

CI uses [`conftest`](https://www.conftest.dev/).
