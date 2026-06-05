# tools/notify — pluggable notification channels

> Pluggable adapter pattern. The fortress agent and the GitHub
> Actions workflows call a single entry point — `notify.py` — and
> never need to know which channel is active. Switching from email
> to ntfy/Signal/etc. is a YAML edit, not a code change.
>
> See [`docs/decisions/ADR-0001-approval-channel.md`](../../docs/decisions/ADR-0001-approval-channel.md)
> for the architectural decision behind this folder.

## Files

| File | Role |
| ---- | ---- |
| `notify.py` | Entry point. Loads `channels.yaml`, fans out to enabled adapters. |
| `channels.yaml` | The only knob. Lists adapters and their per-adapter settings. |
| `adapters/email.py` | SMTP over STARTTLS. Default channel. |
| `adapters/ntfy.py` | Stub — talks to a self-hosted ntfy server (free). Off by default. |
| `adapters/signal.py` | Stub — wraps `signal-cli`. Off by default. |
| `adapters/github.py` | No-op stub: assumes GitHub mobile notifications. Off by default. |

## Usage

```bash
# Send a test notification via every enabled channel.
NOTIFY_SMTP_PASS='app-password' python3 tools/notify/notify.py \
  --title "WhiteLab self-test" \
  --severity info \
  --body "Adapter smoke test from $(hostname)."

# Dry-run (prints the payload, sends nothing).
python3 tools/notify/notify.py --dry-run \
  --title 'WhiteLab self-test' --severity info --body 'demo'
```

## Contract

Every adapter implements:

```python
def send(title: str, body: str, severity: str, config: dict) -> None: ...
```

* `severity` is one of `info`, `warning`, `critical`.
* Adapter raises on failure; `notify.py` catches per-adapter and
  records the error to stderr but never aborts the whole fan-out.
* No adapter mutates global state.
* No adapter is imported at top level — `notify.py` lazy-imports the
  module only if the channel is enabled in `channels.yaml`. This
  keeps the dependency footprint minimal in environments that only
  use one adapter.

## Adding a new channel

1. Drop `adapters/<name>.py` implementing the `send` contract.
2. Add the channel block to `channels.yaml` with `enabled: false`.
3. Document the required env vars / secrets in the file's docstring.
4. Open a PR. The CI guard verifies the new adapter follows the
   contract via `python -m py_compile` and a smoke test in
   `--dry-run` mode.
