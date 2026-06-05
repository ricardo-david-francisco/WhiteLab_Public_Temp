# `inbox/` — the offline drop folder

The second channel of the proposal funnel. Use this when:

* you do not want to (or cannot) open a GitHub Issue;
* you need to deliver multiple files in one shot;
* you want the snippet review to happen out-of-band (mobile, plane,
  laptop in the kitchen) and only the *push* to be online.

## How to use

1. Pick a short kebab-case slug, for example `add-immich-runbook`.
2. Create `inbox/<slug>/` and drop both:
   - the proposed file(s) you want landed in the repo, *under whatever
     filename you like inside that folder*;
   - a `manifest.yml` that maps each filename to its desired target
     path inside the repo.
3. Commit and push to `master` (or to a personal branch and merge in).
   The `proposal-apply` workflow will:
   - parse the manifest;
   - validate every target path against the allow-list;
   - run the anonymiser refuse-on-secret check;
   - copy the files into place;
   - delete the `inbox/<slug>/` folder;
   - open a **draft** PR titled `WIP[proposal]: inbox/<slug>`.

The PR is **always draft**. Auto-merge is structurally impossible —
the workflow contains zero `gh pr merge` calls.

## Manifest format

Single file:

```yaml
target: docs/runbooks/immich.md
source: immich.md     # relative to inbox/<slug>/
```

Multiple files:

```yaml
files:
  - target: docs/runbooks/immich.md
    source: immich.md
  - target: infra/lxc/ct-110-immich-trust/compose.yaml
    source: compose.yaml
```

## Hard limits

The funnel refuses any proposal whose target:

- escapes the repo via `..`;
- starts at `/`;
- falls outside `docs/`, `infra/`, `tools/`, `tests/`, `inbox/`, or
  the three root files (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`);
- lives inside `tools/guards/`, `tools/proposals/`, `tools/anonymizer/`,
  `policy/`, `vault/`, `audit/`, `.github/workflows/`, or
  `.github/CODEOWNERS`.

The funnel also refuses any snippet whose body contains a plaintext
secret (password, bearer token, API key, MAC address, public IP,
private TLS/WireGuard/SSH key, JWT). Anonymise first, then propose.
