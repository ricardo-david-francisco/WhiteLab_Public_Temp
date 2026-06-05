"""TargetAdapter protocol and supporting types.

Every adapter (OPNsense, Proxmox-N95, Proxmox-N305, Omada, Caddy)
implements this surface. The agent main loop talks to adapters only;
adapters talk to remote APIs only — never SSH.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StagedChange:
    """A rendered change ready to be applied."""

    target_id: str
    rendered_path: Path
    sha256: str
    summary: str


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str = ""


@runtime_checkable
class TargetAdapter(Protocol):
    """Contract for every target adapter.

    Adapters are constructed with a credentials mapping that names the
    pull-vs-apply token to use. The agent provides the matching token
    from /run/fortress/api-tokens/ when invoking each method.
    """

    target_id: str  # e.g. "opnsense", "proxmox-n95", "omada"

    def pull_config(self, *, dst: Path) -> Path:
        """Fetch the live config and write an anonymized copy to ``dst``.

        Returns the path written. The returned file MUST be safe to
        commit to git (no real secrets, MACs, public IPs, hostnames).
        """
        ...

    def stage(self, *, anonymized_input: Path, deltas: Path) -> StagedChange:
        """Render the next desired state from anonymized base + deltas.

        Performs schema validation only. Does not touch the live target.
        """
        ...

    def backup(self, *, dst: Path) -> Path:
        """Take a snapshot of the live target. Returns the snapshot path."""
        ...

    def apply(self, *, change: StagedChange) -> None:
        """Apply ``change`` to the live target. Raises on failure."""
        ...

    def rollback(self, *, snapshot: Path) -> None:
        """Restore from a backup taken by :meth:`backup`."""
        ...

    def health(self) -> list[HealthCheck]:
        """Run lightweight liveness/readiness probes against the target."""
        ...


class AdapterError(RuntimeError):
    """Raised by any adapter on a recoverable failure (rollback path)."""


class FatalAdapterError(RuntimeError):
    """Raised by any adapter on a non-recoverable failure (page operator)."""
