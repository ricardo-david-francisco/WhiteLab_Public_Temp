"""GitHub-mobile-only adapter — no-op.

Use when the operator wants to rely solely on GitHub mobile
notifications (free, already configured) and does not want to add a
secondary channel. Records the event to stderr so the operator can
audit fan-out behaviour but does not send anywhere.
"""

from __future__ import annotations

import sys
from typing import Any


def send(title: str, body: str, severity: str, config: dict[str, Any]) -> None:
    print(
        f"github-noop: severity={severity} title={title!r}",
        file=sys.stderr,
    )
