"""Fortress agent — main loop.

Lives on LXC 104 (N95). systemd service in
``tools/fortress-agent/systemd/fortress-agent.service``.

This file is the orchestration spine. Adapter implementations land in
PR3-PR5; this module is the contract they plug into.

State machine and dataflow are described in
``tools/fortress-agent/README.md``.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

from .adapters.base import (
    AdapterError,
    FatalAdapterError,
    TargetAdapter,
)

LOG = logging.getLogger("fortress")


class State(Enum):
    IDLE = auto()
    DRIFT_CHECK = auto()
    AWAIT_TOTP = auto()
    STAGE = auto()
    BACKUP = auto()
    APPLY = auto()
    ROLLBACK = auto()
    SIGN_AUDIT = auto()


@dataclass
class AgentConfig:
    repo_path: Path
    vault_path: Path
    poll_interval_seconds: int = 60
    totp_window_seconds: int = 600
    dry_run: bool = True


class FortressAgent:
    def __init__(self, cfg: AgentConfig, adapters: List[TargetAdapter]) -> None:
        self._cfg = cfg
        self._adapters = {a.target_id: a for a in adapters}
        self._state = State.IDLE

    # -- main loop ----------------------------------------------------------

    def run(self) -> int:
        LOG.info("fortress agent starting (dry_run=%s)", self._cfg.dry_run)
        while True:
            try:
                self._tick()
            except FatalAdapterError as exc:
                LOG.critical("fatal adapter error: %s", exc)
                return 2
            except Exception:  # noqa: BLE001
                LOG.exception("unhandled exception in tick; staying IDLE")
                self._state = State.IDLE
            time.sleep(self._cfg.poll_interval_seconds)

    def _tick(self) -> None:
        # PR3+ wires: GitHub poll -> drift PR -> apply pipeline.
        # For now, prove the loop runs.
        LOG.debug("tick: state=%s", self._state.name)
        if self._state == State.IDLE:
            return

    # -- apply pipeline -----------------------------------------------------

    def apply_change(
        self,
        *,
        adapter: TargetAdapter,
        anonymized_input: Path,
        deltas: Path,
    ) -> None:
        """End-to-end apply for one adapter. Raises on rollback failure."""
        snapshot: Optional[Path] = None
        try:
            self._state = State.STAGE
            change = adapter.stage(anonymized_input=anonymized_input, deltas=deltas)
            LOG.info("staged %s sha256=%s", change.target_id, change.sha256)

            self._state = State.BACKUP
            snapshot = adapter.backup(dst=self._cfg.vault_path / "backup" / change.target_id)
            LOG.info("backup written to %s", snapshot)

            self._state = State.APPLY
            if self._cfg.dry_run:
                LOG.info("dry_run: skipping apply for %s", change.target_id)
            else:
                adapter.apply(change=change)

            checks = adapter.health()
            if any(not c.ok for c in checks):
                LOG.warning("post-apply health checks failed: %s", checks)
                raise AdapterError("post-apply health failed")

            self._state = State.SIGN_AUDIT
            # PR3+: minisign the audit log and push to audit/agent-log/.
        except AdapterError as exc:
            LOG.error("apply failed: %s; rolling back", exc)
            self._state = State.ROLLBACK
            if snapshot is not None and not self._cfg.dry_run:
                adapter.rollback(snapshot=snapshot)
        finally:
            self._state = State.IDLE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fortress-agent")
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--vault", type=Path, default=Path("/run/fortress"))
    p.add_argument("--poll", type=int, default=60)
    p.add_argument("--apply", action="store_true", help="disable dry_run (DANGEROUS)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cfg = AgentConfig(
        repo_path=args.repo,
        vault_path=args.vault,
        poll_interval_seconds=args.poll,
        dry_run=not args.apply,
    )
    # PR3+: instantiate adapters from /run/fortress/api-tokens/.
    agent = FortressAgent(cfg, adapters=[])
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
