# Caddy reverse proxy (LXC 100 on N95)

A single Jinja-rendered `Caddyfile` is the source of truth. Per-vhost
fragments are composed in by the agent at apply time.

The Caddy admin API is used for **hot reload** at apply time (no
service restart, no dropped connections):

```text
PUT http://127.0.0.1:2019/load   (body = rendered Caddyfile, JSON-encoded)
```

The admin endpoint is bound to `127.0.0.1` only and is reachable from
the agent via the Proxmox `exec` API on LXC 100 with a signed bundle
hash (see fortress design §7.2).

See [`docs/architecture/2.0-fortress-design.md`](../../docs/architecture/2.0-fortress-design.md) §11 for the
AdGuard reverse-proxy delta example.
