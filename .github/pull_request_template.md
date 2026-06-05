# Pull request

## Target & blast radius

- [ ] OPNsense (firewall / NAT / VPN)
- [ ] Proxmox N95
- [ ] Proxmox N305
- [ ] Omada controlle
- [ ] LXC golden image
- [ ] LXC per-CT spec
- [ ] Caddy
- [ ] Tooling / CI / docs only

**Hosts impacted:** _e.g. `n305`, LXC `105`_
**VLANs impacted:** _e.g. `40_ADMIN`, `61_TRUST_DMZ`_
**Estimated downtime:** _none / sub-second / N seconds / N minutes_

## Anonymization

- [ ] All committed configs ran through `tools/anonymizer/anonymize.py`.
- [ ] No real MAC, public IP, hostname, tailnet name or credential
      appears in the diff.
- [ ] `make verify` (or `python -m tools.anonymizer.anonymize --verify infra/`)
      passes locally.

## Audit gates

- [ ] Snyk Code/IaC: no new High/Critical.
- [ ] Trivy fs+config: no new High/Critical.
- [ ] OPA `conftest`: green.
- [ ] (LXC images) Lynis score ≥ 80.

## Sovereignty checklist (PR #24 onwards)

- [ ] `make ci` passes locally; mirrors GitHub Actions bit-for-bit.
- [ ] No new GitHub-only or paid-subscription dependency was added.
- [ ] No SSH session is opened by any new code path
      (`make ci-no-ssh` is green).
- [ ] No `gh pr merge --auto` call was added; this PR will be
      merged manually after review.
- [ ] If this PR touches the proposal funnel, anonymiser, o
      guards, [AGENTS.md](../AGENTS.md) is still accurate.

## Apply plan (if applicable)

1. Pre-flight: agent re-pulls current config and verifies no drift since
   last `pull` PR.
2. Snapshot/backup recorded in `audit/snyk/snapshots/<date>.txt`.
3. TOTP unlock window: `<HH:MM-HH:MM Europe/Lisbon>`.
4. Apply call: _list of API endpoints / Ansible plays_.
5. Post-apply checks: _what HTTP/curl/dig/etc. tests confirm health_.

## Rollback

How exactly do we revert? List the commit / API call / Ansible play
that returns the system to its prior state.

## Linked tickets

<!-- One of: Fixes / Closes / Refs #N. The `docs-up-to-date`
workflow verifies that this section is non-empty. -->

`#`

## Documentation contract

The `docs-up-to-date` workflow enforces these on every PR:

- [ ] An issue is linked above.
- [ ] If `infra/**`, `tools/fortress-agent/**` o
      `.github/workflows/**` changed, a matching `docs/**` change
      is in this PR, **or** the PR carries the `docs-skip` label
      with a justification.
- [ ] If this PR implements an RFC unde
      `docs/contributions/pending-RFCs/`, the RFC stub has been
      moved into the relevant architecture/runbook document.
- [ ] The unified critique reflects any newly-discovered finding.

See [`docs/roadmap/README.md`](../docs/roadmap/README.md) for the
full workflow.
