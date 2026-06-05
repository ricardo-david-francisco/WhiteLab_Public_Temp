"""ntfy.sh adapter — stub.

Posts to a self-hosted ntfy server. Requires ``base_url`` and
``topic`` in config; reads the bearer token from the env var named
in ``auth_token_env`` (default ``NOTIFY_NTFY_TOKEN``).
"""

from __future__ import annotations

import os
from typing import Any
from urllib import request

SEVERITY_PRIO = {"info": "default", "warning": "high", "critical": "urgent"}


def send(title: str, body: str, severity: str, config: dict[str, Any]) -> None:
    base_url = config.get("base_url")
    topic = config.get("topic")
    if not base_url or not topic:
        raise RuntimeError("ntfy adapter requires base_url and topic in channels.yaml")

    token_env = config.get("auth_token_env", "NOTIFY_NTFY_TOKEN")
    token = os.environ.get(token_env)

    url = f"{base_url.rstrip('/')}/{topic}"
    headers = {
        "Title": title,
        "Priority": SEVERITY_PRIO.get(severity, "default"),
        "Content-Type": "text/plain; charset=utf-8",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    with request.urlopen(req, timeout=15) as resp:  # noqa: S310 - configured URL.
        if resp.status >= 400:
            raise RuntimeError(f"ntfy returned HTTP {resp.status}")
