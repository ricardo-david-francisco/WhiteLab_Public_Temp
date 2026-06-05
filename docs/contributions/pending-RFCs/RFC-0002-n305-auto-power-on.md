# RFC-0002 — N305 auto power-on after AC loss

* **Status**        : Draft
* **Author**        : @ricardo-david-francisco
* **Created**       : 2026-05-06
* **Last updated**  : 2026-05-06
* **Tracking issue**: TBD
* **Severity**      : High (availability)
* **Hardware**      : Topton N305 mini-PC (BIOS only, no purchase)

## 1. Problem

When the household loses power and recovers, the **Topton N305**
host (Proxmox; runs the OPNsense VM and several core LXCs) does not
boot automatically. Until the operator presses the physical power
button:

* OPNsense is offline → no routing, no DHCP, no internal DNS;
* the Fortress agent (LXC 104) is unreachable → no GitOps apply;
* the Tailscale subnet router VM is offline → remote recovery is
  blocked;
* TerraMaster NAS shares fail → MongoDB / Loki / Prometheus
  volumes hang (see `INC-MONGO-SHUTDOWN-01` referenced in the
  unified critique).

This contradicts a core property in [`docs/learning/01-zero-trust-explained.md`](../../learning/01-zero-trust-explained.md):
the lab must self-recover from a power blip without operator
intervention.

## 2. Background

The N95 host already has the BIOS option set correctly. The N305
was provisioned earlier and the option was missed. Both boards
expose the same setting under different menu names:

* AMI BIOS — `Advanced` → `Power Management` → `Restore AC Power
  Loss` (values: `Power Off`, `Last State`, `Power On`).
* Some Topton SKUs label it `State after G3` or `AC Power Recovery`.

The desired value is **Power On** (not `Last State`) so the host
boots even if it was intentionally shut down before the outage.
This eliminates ambiguity during recovery drills.

## 3. Proposal

1. Schedule a maintenance window (~10 min) when the lab can be
   gracefully shut down.
2. Power the N305 down cleanly via `pvesh` from the Fortress agent.
3. Pull power, attach keyboard + monitor.
4. Enter BIOS (`Del` at POST), navigate to the power-management
   menu, set **Restore AC Power Loss = Power On**.
5. Save and exit.
6. Verify: pull power, restore power, observe POST → boot without
   button press.
7. Repeat the verification a second time after a 30-second idle to
   exclude transient state.
8. Record the BIOS revision and the exact menu path in
   [`docs/architecture/4.0-hardware-inventory.md`](../../architecture/4.0-hardware-inventory.md)
   (or create that doc if absent) so future BIOS upgrades preserve
   the setting.

## 4. Alternatives considered

* **Wake-on-LAN.** Rejected — requires a healthy network during the
  outage, which is exactly what we cannot assume.
* **Smart plug with auto-on profile.** Rejected — adds a
  third-party cloud dependency on the critical path; the BIOS
  setting is free and offline.
* **`Last State`.** Rejected — ambiguous after intentional
  shutdowns; `Power On` is unconditional and matches the home-lab
  reality.

## 5. Risks

* **BIOS reset on CMOS-battery failure.** Mitigated by the
  inventory doc + a periodic verification step in the quarterly
  maintenance runbook.
* **Forgotten power-on after maintenance.** Mitigated — `Power On`
  is the desired post-maintenance state anyway.

## 6. Acceptance criteria

1. Two consecutive power-cycle tests confirm the N305 boots
   automatically.
2. The BIOS revision and exact menu path are documented under
   `docs/architecture/4.0-hardware-inventory.md` (or equivalent).
3. The N95's existing setting is recorded in the same document for
   parity.
4. A check-list line "verify Restore-AC-Power-Loss = Power On"
   exists in the quarterly maintenance runbook.

## 7. Rollout plan

* Maintenance window: weekend evening, ~30 min total.
* Pre-window: announce in the Operator Telegram channel (audit
  trail).
* Post-window: open the documentation PR and link this RFC.

## 8. References

* [`docs/learning/01-zero-trust-explained.md`](../../learning/01-zero-trust-explained.md)
* RFC-0003 (UPS + NUT) — together they form the full power-event
  story.
