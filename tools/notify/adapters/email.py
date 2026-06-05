"""SMTP-over-STARTTLS adapter (default channel).

Reads the password from the environment variable ``NOTIFY_SMTP_PASS``.
Never reads credentials from disk; never logs them.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

REQUIRED_KEYS = ("smtp_host", "smtp_port", "from_addr", "to_addrs")


def send(title: str, body: str, severity: str, config: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if not config.get(k)]
    if missing:
        raise RuntimeError(f"email adapter missing config keys: {missing}")

    password = os.environ.get("NOTIFY_SMTP_PASS")
    if not password:
        raise RuntimeError("email adapter requires env var NOTIFY_SMTP_PASS")

    to_addrs = config["to_addrs"]
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]

    subject_prefix = config.get("subject_prefix", "")
    subject = f"{subject_prefix} {title}".strip()
    if severity != "info":
        subject = f"[{severity.upper()}] {subject}"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["from_addr"]
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    host = config["smtp_host"]
    port = int(config["smtp_port"])
    with smtplib.SMTP(host, port, timeout=15) as server:
        server.starttls()
        server.login(config["from_addr"], password)
        server.send_message(msg)
