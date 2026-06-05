# `audit/` — third-party audit artifacts

| Subtree      | Tool                                                                | Cadence             |
| ------------ | ------------------------------------------------------------------- | ------------------- |
| `snyk/`      | Snyk Code + Snyk IaC + Snyk Container                               | every PR + nightly  |
| `trivy/`     | Trivy fs + config + image                                           | every PR            |
| `lynis/`     | Lynis on each LXC golden image                                      | weekly              |
| `pentest/`   | Manual pen-test reports + offensive runs                            | release / on demand |
| `agent-log/` | Signed audit log emitted by the Fortress Agent                      | every apply         |
| `keys/`      | Public verification keys (age, minisign). **Public material only.** | as keys rotate      |

Severity gates:

* **Snyk**: any new High or Critical → CI fails. Existing High/Critical
  must have a tracked exception (`audit/snyk/exceptions.yaml`) with an
  owner and an expiry.
* **Trivy**: HIGH/CRITICAL → CI fails (`exit-code: 1`).
* **Lynis**: hardening score must stay ≥ 80 on every golden image.
