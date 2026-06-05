"""Omada controller adapter — Omada OpenAPI v6.

Two API tokens (granted via the controller's Hotspot/OpenAPI page):
    fortress-pull   — read scope only
    fortress-apply  — read/write scope on the controller-bound site

Endpoints used::

    POST /openapi/authorize/login                  (client-credentials)
    GET  /openapi/v1/{omadacId}/sites              (resolve site id)
    GET  /openapi/v1/{omadacId}/sites/{sid}/setting/wired-networks
    PUT  /openapi/v1/{omadacId}/sites/{sid}/setting/wired-networks
    GET  /openapi/v1/{omadacId}/sites/{sid}/setting/wireless-networks
    PUT  /openapi/v1/{omadacId}/sites/{sid}/setting/wireless-networks
    GET  /openapi/v1/{omadacId}/sites/{sid}/setting/port-profile
    PUT  /openapi/v1/{omadacId}/sites/{sid}/setting/port-profile
    POST /openapi/v1/{omadacId}/sites/{sid}/setting/backup
    POST /openapi/v1/{omadacId}/sites/{sid}/setting/restore
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import HealthCheck, StagedChange


class OmadaAdapter:
    target_id = "omada"

    def __init__(self, *, base_url: str, creds: Mapping[str, Any]) -> None:
        self._base_url = base_url.rstrip("/")
        self._creds = creds

    def pull_config(self, *, dst: Path) -> Path:
        raise NotImplementedError("OmadaAdapter.pull_config — PR5")

    def stage(self, *, anonymized_input: Path, deltas: Path) -> StagedChange:
        raise NotImplementedError("OmadaAdapter.stage — PR5")

    def backup(self, *, dst: Path) -> Path:
        raise NotImplementedError("OmadaAdapter.backup — PR5")

    def apply(self, *, change: StagedChange) -> None:
        raise NotImplementedError("OmadaAdapter.apply — PR5")

    def rollback(self, *, snapshot: Path) -> None:
        raise NotImplementedError("OmadaAdapter.rollback — PR5")

    def health(self) -> list[HealthCheck]:
        raise NotImplementedError("OmadaAdapter.health — PR5")
