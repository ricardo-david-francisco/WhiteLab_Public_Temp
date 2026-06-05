# WhiteLab Dev Sandbox

This folder is **infrastructure-as-code for the development environment
itself**. It builds a self-contained, portable toolchain at `../.sandbox/`
(gitignored) so the same workflow runs on:

- Windows + WSL2 Ubuntu (the primary case)
- Any Linux x86_64 host (a Linux VM you copy this folder to)
- Inside a Debian container (no host installs required)

Tools provided: `gh`, `age`, `age-keygen`, `sops`, plus a Python venv with
the deps listed in `requirements.txt`. `terraform` is expected on the host
(already present on Ubuntu).

## Why two variants?

| Variant           | Files                                         | Use when                                           |
| ----------------- | --------------------------------------------- | -------------------------------------------------- |
| **Bare-metal**    | `bootstrap.sh`, `activate.sh`, `versions.env` | Daily local work. Browser-based `gh auth` is easy. |
| **Containerized** | `Dockerfile`, `docker-compose.yml`            | Hosts without WSL; future CI; maximum isolation.   |

Both pin the same versions and SHA256 hashes (`versions.env` /
`Dockerfile` ARGs).

## Bare-metal quickstart (WSL or Linux)

```bash
# From the repo root:
bash sandbox/bootstrap.sh
source sandbox/activate.sh

gh --version
age --version
sops --version --disable-version-check
```

Re-running `bootstrap.sh` is safe and idempotent. `--clean` wipes
`.sandbox/` and starts over.

## Containerized quickstart

```bash
docker compose -f sandbox/docker-compose.yml build
docker compose -f sandbox/docker-compose.yml run --rm sandbox
# Inside the container, /workspace is the repo. gh state persists in
# ../.sandbox/state/gh on the host.
```

## What is generated under `.sandbox/`

```text
.sandbox/
├── bin/             # gh, age, age-keygen, sops      (executable)
├── downloads/       # cached release tarballs        (cache, safe to delete)
├── venv/            # Python virtualenv              (regeneratable)
├── state/
│   ├── gh/          # GitHub CLI auth token + hosts  (SECRET — never commit)
│   └── age/         # age private keys (if you put them here, not recommended)
└── .stamp           # last successful bootstrap manifest
```

`.sandbox/` is in `.gitignore`. **Do not** force-add it.

## Portability

Because `/mnt/c` in WSL2 supports the executable bit and the binaries are
Linux x86_64 statically-linked, you can:

1. Bootstrap on the Windows + WSL workstation.
2. Copy the entire `15_WhiteLab/` folder (including `.sandbox/`) onto a
   Linux x86_64 VM.
3. `source sandbox/activate.sh` and continue working — including reusing
   the same `gh` auth token. Treat that as if you were carrying a
   credential, because you are.

Alternative for distributed teams: do **not** copy `.sandbox/state/gh`;
re-run `gh auth login` on each host.

## Threat model considerations

- The pinned SHA256 in `versions.env` is the single point of trust for tool
  binaries. Update only via PR; the PR diff makes hash changes auditable.
- `bootstrap.sh` fails closed on any mismatch; do not "fix" failures by
  bumping a hash without verifying upstream provenance.
- `gh` auth tokens live under `.sandbox/state/gh/`. Never push that path.
- The container variant drops all Linux capabilities and runs as UID 1000.
