# `tools/` — anonymizer, fortress agent, pre-commit hooks

| Subtree              | What it is                                                |
| -------------------- | --------------------------------------------------------- |
| `anonymizer/`        | The two-way scrub-and-rehydrate pipeline (Zone 1 + 3).    |
| `fortress-agent/`    | The home-side daemon that pulls / applies / signs.        |
| `precommit/`         | Hooks invoked by `pre-commit` on the dev laptop.          |
| `audit-bootstrap.sh` | Portable installer for trivy + snyk + pytest.             |

All Python. Targeted at Python 3.11 (matches the bible's Debian 12
toolchain). Type-checked with `mypy --strict`. Linted with `ruff`.

Each subtree has its own README with the exact command surface.

## Running the full audit suite locally on a fresh machine

The CI gates (anonymization, trivy, snyk, pytest) are reproducible
end-to-end on any clean Linux box without root. Everything lands under
`./.sandbox/` (gitignored), so the host stays clean:

```bash
git clone https://github.com/ricardo-david-francisco/WhiteLab.git
cd WhiteLab
./tools/audit-bootstrap.sh install   # downloads trivy + snyk + venv
export SNYK_TOKEN=...                 # optional, enables snyk-* gates
./tools/audit-bootstrap.sh audit      # runs every gate
```

This is the recommended path when migrating the working tree from one
laptop to another (e.g. company laptop → personal VMware guest): copy
the folder, then run `./tools/audit-bootstrap.sh` and you have the
identical audit posture as CI.
