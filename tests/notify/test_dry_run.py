"""Dry-run coverage for the notify dispatcher."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.notify import notify


def _write_config(tmp_path: Path, body: str) -> Path:
    cfg = tmp_path / "channels.yaml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_load_config_missing(tmp_path: Path):
    with pytest.raises(SystemExit):
        notify.load_config(tmp_path / "missing.yaml")


def test_load_config_no_channels_map(tmp_path: Path):
    cfg = _write_config(tmp_path, "channels: 42\n")
    with pytest.raises(SystemExit):
        notify.load_config(cfg)


def test_dispatch_no_channels_enabled(capsys):
    rc = notify.dispatch(
        channels={"ntfy": {"enabled": False}},
        title="t",
        body="b",
        severity="info",
        dry_run=True,
    )
    assert rc == 1


def test_dispatch_dry_run_all_channels(capsys):
    channels = {
        "ntfy":   {"enabled": True, "url": "https://example.invalid/topic"},
        "email":  {"enabled": True, "to": "ops@example.invalid"},
        "github": {"enabled": True, "repo": "owner/repo"},
        "signal": {"enabled": True, "to": "+10000000000"},
    }
    rc = notify.dispatch(
        channels=channels,
        title="hello",
        body="world",
        severity="warning",
        dry_run=True,
    )
    assert rc == 0
    err = capsys.readouterr().err
    for ch in channels:
        assert f"[dry-run] {ch}" in err


def test_main_dry_run(tmp_path: Path):
    cfg = _write_config(
        tmp_path,
        "channels:\n  ntfy:\n    enabled: true\n    url: https://x.invalid\n",
    )
    rc = notify.main([
        "--title", "t", "--body", "b",
        "--config", str(cfg),
        "--dry-run",
    ])
    assert rc == 0


def test_main_rejects_invalid_severity(tmp_path: Path):
    cfg = _write_config(tmp_path, "channels: {}\n")
    with pytest.raises(SystemExit):
        notify.main([
            "--title", "t", "--body", "b",
            "--severity", "DEFCON1",
            "--config", str(cfg),
            "--dry-run",
        ])
