# 02 — Dev Sandbox Bootstrap

How to build, use, refresh, and recover the local dev sandbox under
`.sandbox/`. The sandbox is the **only** sanctioned place where tools like
`gh`, `age`, `sops`, and the project's Python venv live. Nothing in the
sandbox is committed; everything is reproducible from `sandbox/`.

## TL;DR

```bash
# WSL or Linux x86_64:
bash sandbox/bootstrap.sh
source sandbox/activate.sh

make gh-auth      # opens GitHub device flow in your browser
make repo-create  # creates the private repo and pushes master
```

## Prerequisites on the host

- Linux x86_64 (WSL2 Ubuntu 22.04+ is the supported workstation case).
- `bash`, `curl`, `tar`, `sha256sum`, `python3` (>= 3.10).
- `terraform` (>= 1.6) on PATH for IaC targets. On WSL Ubuntu it's already
  available via the system package.
- Docker is **optional** — only needed for the containerized variant
  (`sandbox/docker-compose.yml`).

## Build (idempotent)

```bash
bash sandbox/bootstrap.sh
```

This downloads `gh`, `age`, and `sops` into `.sandbox/bin/` and verifies
each against the SHA256 pinned in `sandbox/versions.env`. A Python venv is
created at `.sandbox/venv/` with the deps from `sandbox/requirements.txt`.

If a hash mismatch occurs, the script aborts and **does not install**. Do
not "fix" this by editing the hash without verifying the upstream release.

## Activate

```bash
source sandbox/activate.sh
```

Effects:

- Prepends `.sandbox/bin` to `PATH`.
- Activates `.sandbox/venv`.
- Pins `GH_CONFIG_DIR=.sandbox/state/gh` so `gh` auth state lives inside
  the sandbox folder (and not in `$HOME/.config/gh`).
- Sets a `(whitelab)` prompt prefix.
- Defines `whitelab_deactivate` to cleanly restore the prior environment.

## Authenticate `gh`

```bash
make gh-auth
```

This runs `gh auth login --hostname github.com --git-protocol https --web`.
It will:

1. Print a one-time code (e.g. `XXXX-XXXX`).
2. Open / point you at <https://github.com/login/device>.
3. Enter the code, authorize the **GitHub CLI** OAuth app for your
   personal account `ricardo-david-francisco`.
4. `gh` polls and stores the token under `.sandbox/state/gh/`.

Verify:

```bash
make gh-status
gh api user --jq .login    # should print: ricardo-david-francisco
```

## Create the private repo and push

```bash
make repo-create
```

This is equivalent to:

```bash
git checkout master
gh repo create WhiteLab --private --source=. --remote=origin --push \
  --description "WhiteLab — private home infrastructure repo (sanitized only)"
```

Push other branches normally (`git push -u origin feature/<name>`).

## Refresh / upgrade

To bump a tool version: edit `sandbox/versions.env` (and the matching
`Dockerfile` ARG), update the SHA256, open a PR. The diff is small and
auditable. Then on each developer machine:

```bash
make sandbox        # idempotent; only re-installs what changed
```

To force a full reinstall:

```bash
make sandbox-clean
make sandbox
```

## Portability — copying to another machine

The sandbox runs from binaries on the Windows-mounted folder under WSL,
which already supports the executable bit. To migrate to a Linux VM:

1. Stop using the workstation copy.
2. Copy the **entire** `15_WhiteLab/` folder (including `.sandbox/`) to the
   Linux x86_64 target.
3. On the target: `source sandbox/activate.sh`. Tools work as-is. The `gh`
   token in `.sandbox/state/gh/` is reusable.

Treat that copy operation as carrying a credential — because you are. If
the target host is not equally trusted, **do not** copy `.sandbox/state/`;
re-bootstrap and re-authenticate on the target.

## Containerized variant

For hosts without WSL or for CI:

```bash
docker compose -f sandbox/docker-compose.yml build
docker compose -f sandbox/docker-compose.yml run --rm sandbox
```

The container drops all Linux capabilities, runs as UID 1000, mounts the
repo at `/workspace`, and persists `gh`/`age` state under
`.sandbox/state/` on the host (same location as the bare-metal flow).

## Recovery

| Symptom                                   | Fix                                                                            |
| ----------------------------------------- | ------------------------------------------------------------------------------ |
| `command not found: gh`                   | You forgot `source sandbox/activate.sh`.                                       |
| Bootstrap fails with `SHA256 mismatch`    | Investigate. Do NOT bump the hash without verification.                        |
| `gh` says "not logged in" after a copy    | `make gh-auth` again. The previous token may have been intentionally excluded. |
| `pip install` fails behind a proxy        | Set `HTTPS_PROXY` and re-run `make sandbox`.                                   |
| Want to throw everything away             | `make sandbox-clean && make sandbox`.                                          |

## What lives outside the sandbox (must)

- This repo's tracked files. The sandbox is purely tooling.
- The `vault/` folder for raw, sensitive material. **Never** put raw
  exports under `.sandbox/`.
- OS-level credentials (Windows Credential Manager, etc.).

## What lives inside the sandbox (must)

- `gh` auth token (under `.sandbox/state/gh/`).
- Pinned binaries (under `.sandbox/bin/`).
- Python venv (under `.sandbox/venv/`).

Nothing in `.sandbox/` is committed. The `.gitignore` enforces this; do
not override with `git add -f`.
