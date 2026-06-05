"""OPNsense adapter — talks to the OPNsense REST API only.

Two distinct API users / tokens:
    fortress-pull   — read-only privileges (GET only)
    fortress-apply  — write privileges (POST upload + apply)

Endpoints used::

    GET  /api/core/backup/download/this           (pull current config.xml)
    POST /api/core/backup/upload                  (apply new config.xml)
    POST /api/firewall/filter/apply               (commit filter changes)
    POST /api/firewall/filter/savepoint           (rollback marker)
    POST /api/firewall/filter/cancelRollback      (commit savepoint)
    POST /api/firewall/filter/revert/<savepoint>  (rollback within window)
    GET  /api/diagnostics/interface/getInterfaceStatus
    GET  /api/captiveportal/access/status         (EmergencyAccess health)

This file is intentionally a stub: the apply path requires a live
TOTP-unlocked vault + signed bundle. Implementation lands in PR3.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import (
    HealthCheck,
    StagedChange,
    TargetAdapter,
)


class OpnsenseAdapter:
    target_id = "opnsense"

    def __init__(self, *, base_url: str, creds: Mapping[str, Any]) -> None:
        self._base_url = base_url.rstrip("/")
        self._creds = creds  # contains {"pull": "<token>", "apply": "<token>"}

    # -- protocol surface ---------------------------------------------------

    def pull_config(self, *, dst: Path) -> Path:
        raise NotImplementedError("OpnsenseAdapter.pull_config — PR3")

    def stage(self, *, anonymized_input: Path, deltas: Path) -> StagedChange:
        raise NotImplementedError("OpnsenseAdapter.stage — PR3")

    def backup(self, *, dst: Path) -> Path:
        raise NotImplementedError("OpnsenseAdapter.backup — PR3")

    def apply(self, *, change: StagedChange) -> None:
        raise NotImplementedError("OpnsenseAdapter.apply — PR3")

    def rollback(self, *, snapshot: Path) -> None:
        raise NotImplementedError("OpnsenseAdapter.rollback — PR3")

    def health(self) -> list[HealthCheck]:
        raise NotImplementedError("OpnsenseAdapter.health — PR3")


_ADAPTER: TargetAdapter = OpnsenseAdapter.__new__(OpnsenseAdapter)  # noqa: F841 (type-check only)
