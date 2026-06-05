# Proxmox — N95 + N305

Two host trees, each with:

* `exports/` — anonymized snapshots of host-side files we manage:
  * `cluster.fw.anonymized` (firewall),
  * `99-security.conf.anonymized` (sysctl),
  * `interfaces.anonymized` (bridges, with placeholders for MACs and management IPs),
  * `tfa.cfg.audit.json` (a redacted audit-only view; the file itself is never exported).
* `ansible/roles/` — Ansible roles for each concern: repos, sysctl,
  Fail2Ban, cluster firewall, SSH killswitch, 2FA enrolment, network
  bridges, unattended-upgrades.
* `ansible/playbooks/` — composed plays.

> **Apply path.** Ansible runs **from the Fortress Agent** against the
> Proxmox hosts using the **Proxmox API connector** (no SSH). Playbooks
> assume the inventory variable `ansible_connection=community.general.proxmox_api`
> and use API tokens from `/run/fortress/api-tokens/`.

See [`docs/architecture/2.0-fortress-design.md`](../../docs/architecture/2.0-fortress-design.md) §7.2.
