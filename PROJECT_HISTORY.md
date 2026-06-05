# WhiteLab — Project History

> Append-only diary of every meaningful change merged into `master`.
> One entry per merged branch. Newest entries at the top.

---

## 2026-05-06 — contributions narrative folder

- (docs/unified-contributions) Introduced `docs/contributions/` to host
  agent-assisted narrative material that complements (does not replace)
  the normative specs in `docs/architecture/`, `docs/research/`, and
  `docs/threat-model/`. Layout:
  `docs/contributions/notebooklm/{Deep_Dive,Critique,Debate}/` for raw
  per-session AI transcripts, and
  `docs/contributions/running summary of unified contributions/` for
  the consolidated, human-edited synthesis. Authored the two seed
  documents — `unified deep dive/unified-deep-dive.md` (end-to-end
  walk through the lab, the centralized brain, the eight-gate apply
  path, the threat ladder T1–T6, and the DNS-resilience design) and
  `unified critique/unified-critique.md` (seven prioritized findings
  with severities, mechanisms, fixes, and acceptance criteria, plus a
  consolidated remediation roadmap covering Telegram-mediated TOTP
  approval, uniform SSH masking on N305, the monitoring stack in
  LXC 103, the `emergency-apply`/`sync-drift` break-glass pair, the
  desired-state vs roadmap split with a `pending-RFCs/` folder, the
  AdGuard DMZ subnet collision, the cold-standby fortress on N305,
  and the `--laptop-agent` mode for total cluster loss). Wrote
  READMEs at all three new levels documenting editorial rules —
  single living file per kind, professional voice,
  merge-by-topic-not-by-session, IaC parser is blind to this
  directory by construction. Updated
  `docs/architecture/00-repo-layout.md` with a `docs/` subfolder
  table and the top-level `README.md` to advertise the new entry
  point.

## 2026-05-05 — fortress 2.0 design

- (feature/fortress-2.0-design, pending review) Authored the WhiteLab
  2.0 *fortress* architecture design and laid down the supporting
  repository skeleton. Adds `docs/architecture/2.0-fortress-design.md`
  (~700 lines, 14 sections: goals/non-goals, threat model with
  adversary classes A1-A7 and trust zones 0-5, architecture diagram,
  repository layout, anonymization pipeline with placeholder grammar,
  Fortress Agent on LXC 104 with tmpfs vault, target adapters for
  OPNsense / Proxmox / Omada via REST APIs only — no SSH —, deploy
  flow with TOTP gate, audit pipeline (Snyk Code/IaC/Container, Trivy
  fs/config, Lynis, OPA), branch protection, AdGuard-on-N305 worked
  example, runbook stubs, glossary, 10-PR roadmap). Skeleton:
  `infra/{opnsense,proxmox/{n95,n305},lxc/{images,ct-100..ct-105},omada,caddy,policies}`,
  `tools/{anonymizer,fortress-agent/{adapters,vault,systemd},precommit}`,
  `audit/{snyk,trivy,lynis,pentest,agent-log,keys}`, `.github/workflows`,
  `docs/{runbooks,adr}`. Working anonymizer scaffolding:
  `tools/anonymizer/anonymize.py` (idempotent regex+format dispatch),
  `rehydrate.py`, `rules.yaml` (MAC, public IPv4/IPv6, WG keys, age,
  PEM, JWT, SOPS envelope, Snyk token, Tailnet name; well-known public
  anycast DNS allow-listed), `lexicon.example.yaml`, full pytest suite
  (9 tests, all green). CI workflow stubs:
  `ci.yml`, `snyk.yml`, `trivy.yml`, `anonymization-gate.yml`,
  `apply-trigger.yml`. Fortress Agent skeleton: `agent.py` state
  machine + `adapters/{base,opnsense,proxmox,omada}.py` with the
  `TargetAdapter` Protocol; concrete adapter implementations deferred
  to PR3 / PR4 / PR5. Hardened systemd unit
  `fortress-agent.service` (NoNewPrivileges, ProtectSystem=strict,
  SystemCallFilter, MemoryDenyWriteExecute, no ambient capabilities).
  AdGuard-on-N305 worked-example placeholders under
  `infra/lxc/ct-105-adguard-dmz/` using DMZ subnet `192.168.25.0/24`
  (no collision with VLAN 20 SECURE). OPA stubs: `secrets.rego`,
  `opnsense.rego`, `proxmox.rego`, `lxc.rego`. PR template +
  `CODEOWNERS` + `.gitignore` extensions for fortress helper scripts
  and the local anonymizer map. Verify gate passes
  (`python -m tools.anonymizer.anonymize --verify infra/` →
  `verify OK.`); pytest 9/9 green. No secrets, real MACs, public IPs,
  hostnames or tailnet identifiers committed.

---

## 2026-05-05 — infrastructure bible

- (feature/infra-bible, pending review) Expanded the research synthesis
  into a comprehensive infrastructure bible at
  `docs/research/01-infrastructure-bible.md`, drawing from the full
  `Home_Infra` repo (24 chat exports, ~97k lines) and all seven
  long-form chat exports under `.Gemini_Chats_Home_Infra/` (~28k
  lines, with `TOP_VPN_FUNDAMENTAL_…` prioritized as the most recent
  state). Sections cover: hardware & physical topology, VLAN bible
  (15 VLANs incl. 120 ESCAPE / 140 PROXTER / 999 BLACKHOLE), switch
  port matrix, full OPNsense bible (Lobotomy install procedure,
  every interface / alias / firewall rule per VLAN, NAT, DHCP,
  Unbound, captive portal, Zenarmor pre-install, WireGuard plan,
  hardening tunables, backup), Proxmox N95+N305 bible (sysctl,
  cluster firewall, Fail2Ban, 2FA, SSH killswitch, bridges, parity
  gap), LXC bible (golden images HARDENED-v1 / DOCKER-v2; LXC 100
  Tailscale + Caddy unprivileged; LXC 101 Omada compose with 120s
  shutdown grace + DNS sovereignty; LXC 102 mgmt hub planned;
  AdGuard DMZ jail planned on vmbr2 with subnet conflict resolved),
  Caddyfile, Tailscale ACL design, Omada controller bible (port
  profiles, SSID-to-VLAN mapping, SG2210XMP-M2 migration), Brother
  MFC-J5320DW printer policy (IPP-only, scanner disabled, PCAP
  workflow), DNS / AdGuard bible (Cloudflare 1.1.1.2 primary,
  Unbound serve-expired + prefetch, AdGuard vs Pi-hole rationale,
  SSD-wear mitigation), TerraMaster + unRAID NAS plan, monitoring
  stack (Prometheus / Grafana / Loki / Alertmanager), 8-incident
  register, single-river-flow master roadmap (2025-Q4 → next steps),
  WhiteLab IaC implications (action-item tracker), and an extended
  anonymizer scrub list. The previous `00-infra-inference-history.md`
  is preserved with a banner pointing to the bible. Extended
  `.gitignore` for `.sync-and-branch.sh`. No raw chat content
  reproduced verbatim; no secrets, MACs, public IPs, tailnet IDs or
  account names committed.

---

## 2026-05-05 (earlier)

- (feature/infra-research-import, merged via PR #3) Imported the
  initial synthesized inference history of the existing Home_Infra
  deployment from the old private repo `ricardo-david-francisco/Home_Infra`
  and the long-form Gemini research chats. Added
  `docs/research/00-infra-inference-history.md` capturing hardware
  inventory, VLAN/IP map, LXC profiles (100 gateway, 101 Omada, 102
  planned), Caddy upstreams, hardening baseline, known incidents
  (`INC-LXC101-NET-01`, MongoDB shutdown corruption, DNS poisoning,
  ARP shock), Phase 1.4 mesh roadmap, and the implications for
  WhiteLab's IaC reorganization. Extended `.gitignore` to keep raw
  research material (`.Gemini_Chats_Home_Infra/`, helper scripts,
  digest) out of the repo. No device exports or secrets committed.

## 2026-05-04

- Repository created (private).
- Initialized `master` with this file as the sole tracked artifact.
- (feature/architecture-plan, merged via PR #1) Proposed initial repo layout,
  branch/diary workflow, anonymization pipeline, SSH-less sync workflow,
  and threat-model sketch. Added `README.md`, `SECURITY.md`, `.gitignore`,
  `.gitattributes`, and `docs/{architecture,runbooks,threat-model}/`. No
  device exports introduced.
- (feature/sandbox-environment, merged via PR #2) Added portable IaC dev
  sandbox under `sandbox/` plus `Makefile` entrypoint; resolved
  `.gitignore`/`.gitattributes` conflicts by union-merging Terraform,
  Docker, SOPS and age patterns ahead of the upcoming IaC branch.
