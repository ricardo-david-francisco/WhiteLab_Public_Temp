# RFC-0003 — Fanless UPS + NUT graceful shutdown choreography

* **Status**        : Draft
* **Author**        : @ricardo-david-francisco
* **Created**       : 2026-05-06
* **Last updated**  : 2026-05-06
* **Tracking issue**: TBD
* **Severity**      : High (availability + data integrity)
* **Hardware**      : Fanless / silent UPS (purchase pending)

## 1. Problem

Power outages currently cause hard power loss across the rack. The
visible symptoms are:

* **Data risk** — MongoDB, Loki, and Prometheus volumes on the
  TerraMaster NAS lose pending writes (`INC-MONGO-SHUTDOWN-01`).
* **VM corruption risk** — the OPNsense VM and the LXCs on N305
  drop without flushing.
* **Recovery delay** — even with RFC-0002 in place the boot order
  is not deterministic, so the OPNsense VM may come up before
  TerraMaster NFS is mountable, leaving LXCs in a half-attached
  state.

There is no UPS today, and the operator wants a **fanless** unit
to keep the lab silent. The challenge is choreographing a clean
multi-host shutdown when the UPS reports `LOW_BATTERY`.

## 2. Background

* The lab has four populated power consumers:
  1. **N95 host** — runs Proxmox + Caddy + Tailscale subnet router.
     Lowest draw, designated UPS controller.
  2. **N305 host** — runs Proxmox + OPNsense VM + Fortress agent +
     monitoring LXCs.
  3. **TerraMaster NAS** — bulk storage, NFS, MongoDB volumes.
  4. **OPNsense VM** (logical) — already inside N305 but needs a
     dedicated NUT *slave* config so it shuts itself down before
     N305 starts halting LXCs.
* Network/peripherals (Omada switches, G.hn adapters, ISP modem)
  are out of scope for graceful shutdown — they survive abrupt loss.
* Fanless UPS candidates (e.g. APC SMT/SMC line-interactive +
  no-fan models, or pure-sinewave home models) all expose
  USB/serial; **NUT** ([Network UPS Tools](https://networkupstools.org/))
  is the canonical free, OSS UPS daemon and supports a master/slave
  topology over TCP/3493.

## 3. Proposal

Adopt a NUT master/slave topology with three slaves:

```text
                     ┌─────────────────────────┐
                     │  Fanless UPS (USB)      │
                     └────────────┬────────────┘
                                  │ USB
                ┌─────────────────▼─────────────────┐
                │  N95  (NUT MASTER, upsd)          │
                │  - reads battery + status         │
                │  - exports nut TCP 3493           │
                └─┬───────────────┬─────────────────┘
                  │               │
       NFS off    │               │  TCP 3493
                  ▼               ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  TerraMaster NAS │  │  N305 (slave)    │
        │  (slave, upsmon) │  │  - shuts OPNsense│
        │                  │  │    VM first      │
        │                  │  │  - then LXCs     │
        │                  │  │  - then host     │
        └──────────────────┘  └─────┬────────────┘
                                    │ vmbus
                                    ▼
                          ┌──────────────────┐
                          │  OPNsense VM     │
                          │  (slave, upsmon) │
                          └──────────────────┘
```

Behaviour table:

| Event                    | UPS state       | Action sequence                                                                                   |
| ------------------------ | --------------- | ------------------------------------------------------------------------------------------------- |
| Power loss               | `OB DISCHRG`    | Notification only. Operator alert via Telegram (Fortress agent webhook).                          |
| Discharge ≥ 60 s         | `OB DISCHRG`    | Master raises `early-shutdown` event. Non-essential LXCs stop (Loki/Prometheus retention paused). |
| Battery `LB`             | `OB DISCHRG LB` | OPNsense VM shuts down → N305 LXCs stop → N305 issues `pveshutdown`.                              |
| Battery `LB+10s`         | `OB DISCHRG LB` | TerraMaster `poweroff -h`. NFS gracefully drains.                                                 |
| Battery `LB+20s`         | `OB DISCHRG LB` | N95 `shutdown -h now`. UPS holds residual ~30 s for the master itself.                            |
| AC restored mid-shutdown | `OL`            | Abort if no host has reached `final` state; otherwise stay shut and rely on RFC-0002 power-on.    |

Configuration deliverables (all under `infra/`):

* `infra/nut/master/ups.conf` + `upsd.users` + `upsmon.conf` — N95.
* `infra/nut/slaves/n305-upsmon.conf` + custom `NOTIFYCMD` script
  that orders OPNsense → LXC → host.
* `infra/nut/slaves/terramaster-upsmon.conf` (or vendor-native UPS
  client if NUT slave install is impractical on TOS).
* `infra/nut/slaves/opnsense-upsmon.conf` (FreeBSD package).
* `tools/fortress-agent/` adapter to apply NUT configs on each host
  through the existing 8-gate path (no SSH).

## 4. Alternatives considered

* **No UPS, accept data loss.** Rejected — `INC-MONGO-SHUTDOWN-01`
  already fired once.
* **Per-host independent UPS clients (no NUT master).** Rejected —
  no coordinated ordering; OPNsense might still be live when
  N305 halts, which kills the network mid-shutdown for the NAS.
* **Commercial UPS-management cloud.** Rejected — adds outbound
  cloud egress and a vendor account for a critical-path system.
* **APC PowerChute Network Shutdown.** Rejected — proprietary,
  weaker Linux/FreeBSD support, requires PowerChute server.
* **systemd `inhibit` with manual triggers.** Rejected — no
  battery awareness.

## 5. Risks

* **Master = N95 single point of failure.** If N95 dies, slaves
  lose UPS visibility. Mitigated by `MINSUPPLIES 0` fallback +
  per-slave timeout that triggers a safe shutdown if `upsd`
  becomes unreachable for >60 s.
* **TerraMaster NUT slave support.** Some TOS versions ship NUT
  client; otherwise a CronJob polling the master's HTTP status
  endpoint is the fallback.
* **OPNsense VM order.** Must shut down *before* N305 begins
  halting LXC services that the firewall depends on (e.g.
  AdGuard CT-105). Encoded as an explicit `NOTIFYCMD` ordered
  script.
* **Fanless UPS runtime.** Typical fanless models offer 5–10 min
  on full lab load. The choreography above completes in ~60 s,
  comfortably within budget.

## 6. Acceptance criteria

1. NUT master is healthy on N95: `upsc <ups> ups.status` returns
   `OL` on AC and `OB DISCHRG` on simulated loss.
2. Three slaves report `MASTER` in `upsmon -c status`.
3. A live drill (operator unplugs UPS) results in:
   * Telegram alert within 5 s;
   * OPNsense VM `Stopped` before any N305 LXC begins shutdown;
   * TerraMaster reaches `poweroff` before N95;
   * No unclean MongoDB shutdown in the post-drill log review.
4. All NUT configs live in `infra/nut/` and are applied by the
   Fortress agent through the 8-gate path.
5. The runbook
   [`docs/runbooks/power-event.md`](../../runbooks/power-event.md)
   is filled in with the choreography and the drill procedure.

## 7. Rollout plan

* Phase A (purchase + drafting) — operator selects fanless UPS;
  RFC promoted to `Accepted`; Issue moved to `Next`.
* Phase B (master only) — install NUT on N95, validate `upsc`.
* Phase C (one slave) — bring up N305 slave, verify ordering.
* Phase D (NAS + OPNsense slaves) — close the loop.
* Phase E (drill) — schedule a deliberate cold-blackout test on a
  non-critical evening.

## 8. References

* RFC-0002 — auto power-on after AC loss; together they bracket
  the power-event lifecycle.
* `INC-MONGO-SHUTDOWN-01` — referenced in the unified critique.
* [`docs/contributions/running summary of unified contributions/unified critique/unified-critique.md`](../running%20summary%20of%20unified%20contributions/unified%20critique/unified-critique.md).
* Network UPS Tools — <https://networkupstools.org/>.
