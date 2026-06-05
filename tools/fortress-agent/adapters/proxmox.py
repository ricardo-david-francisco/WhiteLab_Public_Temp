"""Proxmox adapter — talks to the Proxmox VE REST API only.

Two distinct API tokens per host:
    fortress@pve!pull   — Auditor role (read-only)
    fortress@pve!apply  — PVEAdmin role on a constrained path set

Endpoints used::

    GET  /api2/json/cluster/status
    GET  /api2/json/nodes/<node>/status
    GET  /api2/json/cluster/firewall/rules
    PUT  /api2/json/cluster/firewall/rules/<pos>
    GET  /api2/json/nodes/<node>/lxc
    POST /api2/json/nodes/<node>/lxc                (create CT)
    POST /api2/json/nodes/<node>/lxc/<vmid>/status/start
    POST /api2/json/nodes/<node>/lxc/<vmid>/exec    (signed-bundle hash gate)
    GET  /api2/json/nodes/<node>/network
    PUT  /api2/json/nodes/<node>/network/<iface>
    POST /api2/json/nodes/<node>/network            (apply pending)

For the rare feature without an API endpoint we use ``exec`` with a
SHA256-pinned allow-list of bundle hashes (config files materialised
from this repo). PR3 ships that allow-list.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .base import HealthCheck, StagedChange


class ProxmoxAdapter:
    """Single instance handles one host. Construct two: one for n95, one for n305."""

    def __init__(
        self,
        *,
        node: str,
        base_url: str,
        creds: Mapping[str, Any],
    ) -> None:
        self.target_id = f"proxmox-{node}"
        self._node = node
        self._base_url = base_url.rstrip("/")
        self._creds = creds

    def pull_config(self, *, dst: Path) -> Path:
        raise NotImplementedError("ProxmoxAdapter.pull_config — PR4")

    def stage(self, *, anonymized_input: Path, deltas: Path) -> StagedChange:
        raise NotImplementedError("ProxmoxAdapter.stage — PR4")

    def backup(self, *, dst: Path) -> Path:
        raise NotImplementedError("ProxmoxAdapter.backup — PR4")

    def apply(self, *, change: StagedChange) -> None:
        raise NotImplementedError("ProxmoxAdapter.apply — PR4")

    def rollback(self, *, snapshot: Path) -> None:
        raise NotImplementedError("ProxmoxAdapter.rollback — PR4")

    def health(self) -> list[HealthCheck]:
        raise NotImplementedError("ProxmoxAdapter.health — PR4")
