"""WhiteLab notify entry point.

Loads ``tools/notify/channels.yaml``, fans out to each enabled
adapter, and reports per-adapter success/failure to stderr without
aborting the whole fan-out.

Adapter contract::

    def send(title: str, body: str, severity: str, config: dict) -> None: ...

See ``tools/notify/README.md`` and
``docs/decisions/ADR-0001-approval-channel.md``.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

import yaml

VALID_SEVERITIES = ("info", "warning", "critical")
DEFAULT_CONFIG_PATH = Path(__file__).parent / "channels.yaml"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"notify: config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    channels = data.get("channels")
    if not isinstance(channels, dict):
        raise SystemExit("notify: channels.yaml must define a 'channels' map.")
    return channels


def dispatch(
    channels: dict[str, dict[str, Any]],
    title: str,
    body: str,
    severity: str,
    dry_run: bool,
) -> int:
    """Return 0 if at least one channel delivered, 1 otherwise.

    A configured-but-disabled channel is a no-op. An enabled channel
    that fails records the error and continues with the next channel.
    """
    delivered = 0
    failed = 0
    enabled = [(name, cfg) for name, cfg in channels.items() if cfg.get("enabled")]
    if not enabled:
        print("notify: no channels enabled; nothing to do.", file=sys.stderr)
        return 1

    for name, cfg in enabled:
        if dry_run:
            print(
                f"notify: [dry-run] {name} <- "
                f"severity={severity} title={title!r}",
                file=sys.stderr,
            )
            delivered += 1
            continue
        try:
            module = importlib.import_module(f"adapters.{name}", package=__package__)
        except ImportError as exc:
            print(f"notify: adapter '{name}' not importable: {exc}", file=sys.stderr)
            failed += 1
            continue
        send = getattr(module, "send", None)
        if not callable(send):
            print(
                f"notify: adapter '{name}' missing send(); skipped.",
                file=sys.stderr,
            )
            failed += 1
            continue
        try:
            send(title=title, body=body, severity=severity, config=cfg)
            delivered += 1
        except Exception as exc:  # noqa: BLE001 - per-adapter best-effort.
            print(f"notify: adapter '{name}' failed: {exc}", file=sys.stderr)
            failed += 1

    return 0 if delivered > 0 else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WhiteLab notify dispatcher.")
    p.add_argument("--title", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--severity", choices=VALID_SEVERITIES, default="info")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent; do not call adapters.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    # Make sure the package-relative adapter import works whether the
    # script is run as ``python -m tools.notify.notify`` or as a path.
    sys.path.insert(0, str(Path(__file__).parent))
    channels = load_config(args.config)
    return dispatch(
        channels=channels,
        title=args.title,
        body=args.body,
        severity=args.severity,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
