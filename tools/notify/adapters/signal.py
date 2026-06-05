"""signal-cli adapter — stub.

Wraps the ``signal-cli`` binary. Implementations should not block
the main fan-out for more than a few seconds; the binary call is
expected to be near-instant on a warm JVM.
"""

from __future__ import annotations

import shlex
import subprocess
from typing import Any


def send(title: str, body: str, severity: str, config: dict[str, Any]) -> None:
    cli_path = config.get("cli_path", "signal-cli")
    account = config.get("account")
    recipient = config.get("recipient")
    if not account or not recipient:
        raise RuntimeError("signal adapter requires 'account' and 'recipient'")

    message = f"[{severity.upper()}] {title}\n\n{body}"
    cmd = [cli_path, "-a", str(account), "send", "-m", message, str(recipient)]
    proc = subprocess.run(  # noqa: S603 - args are list, no shell.
        cmd,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"signal-cli failed (rc={proc.returncode}): "
            f"{shlex.join(cmd)}\n{proc.stderr.strip()}"
        )
