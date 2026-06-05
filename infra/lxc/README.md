# LXC — golden images and per-CT specs

## `images/`

Packer-style recipes for the two image lineages defined in the bible:

* `deb12-hardened-v1/` — the base hardened Debian 12 image
  (`IMG-DEB12-HARDENED-v1`). UFW deny-by-default, Fail2Ban on systemd
  backend, unattended-upgrades, SSH masked, `sysadmin` user with
  key-only auth.
* `deb12-docker-v2/` — extends `hardened-v1` with Docker CE + Compose
  and the Docker apt origin in `Allowed-Origins`. **The only image
  allowed for containers that run Docker.**

Promotion gate: Snyk + Trivy + Lynis + OPA `lxc.rego` must be green
before an image is tagged "golden".

## `ct-NNN-*/`

One directory per LXC. Required files:

* `README.md` — what the CT does, why it exists, why this host.
* `ct.yaml` — declarative payload that the Proxmox adapter feeds to
  `POST /nodes/{node}/lxc`. Includes resources, network, features,
  unprivileged flag, mount entries, startup ordering.
* `compose.yaml` (if applicable) — Docker Compose stack.
* `audit_*.sh` — audit script (network identity, security baseline,
  application layer, reverse-proxy, VPN where applicable).
* `verify_security.sh` (gold-image candidates) — Live Fire
  verification.

See [`docs/architecture/2.0-fortress-design.md`](../../docs/architecture/2.0-fortress-design.md) §7.2 and §11
for the worked AdGuard example.
