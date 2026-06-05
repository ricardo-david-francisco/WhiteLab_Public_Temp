"""Tests for the PR #24 secret-class anonymisation rules."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.anonymizer import anonymize, rehydrate


@pytest.fixture()
def map_path(tmp_path: Path) -> Path:
    return tmp_path / "anonmap.json"


@pytest.fixture()
def rules():
    rules, _ = anonymize.load_rules(anonymize.DEFAULT_RULES)
    return rules


def _scrub(text: str, map_path: Path, rules) -> str:
    mp = anonymize.load_map(map_path)
    out = anonymize.scrub_text(text, rules, mp)
    anonymize.save_map(map_path, mp)
    return out


def test_password_assignment_is_anonymized(map_path, rules):
    src = 'password = "Sup3rS3cretValue!"'
    out = _scrub(src, map_path, rules)
    assert "Sup3rS3cretValue!" not in out
    assert "PASSWORD_001" in out


def test_password_round_trip(map_path, rules):
    src = 'password: "Sup3rS3cretValue!"'
    scrubbed = _scrub(src, map_path, rules)
    mp = json.loads(map_path.read_text())
    lut = rehydrate.build_lookup(mp)
    restored = rehydrate.rehydrate(scrubbed, lut)
    assert restored == src


def test_bearer_token_is_anonymized(map_path, rules):
    src = "Authorization: Bearer ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
    out = _scrub(src, map_path, rules)
    assert "ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789" not in out
    assert "BEARER_TOKEN_001" in out


def test_api_key_assignment(map_path, rules):
    src = 'api_key = "sk-prod-abcdefgh12345678ZZZ"'
    out = _scrub(src, map_path, rules)
    assert "sk-prod-abcdefgh12345678ZZZ" not in out
    assert "API_KEY_001" in out


def test_generic_secret_token(map_path, rules):
    src = 'gitlab_token: "glpat-XYZ12345abcdefghIJKL"'
    out = _scrub(src, map_path, rules)
    assert "glpat-XYZ12345abcdefghIJKL" not in out
    assert "GENERIC_SECRET_001" in out


def test_obvious_non_secret_is_left_alone(map_path, rules):
    src = 'password = "changeme"'
    out = _scrub(src, map_path, rules)
    # `changeme` is on the well-known non-secret allow-list.
    assert out == src


def test_envvar_reference_is_left_alone(map_path, rules):
    src = "password = ${SMTP_PASS}"
    out = _scrub(src, map_path, rules)
    assert "${SMTP_PASS}" in out


def test_secret_idempotency(map_path, rules):
    src = 'password = "Sup3rS3cretValue!"'
    once = _scrub(src, map_path, rules)
    twice = _scrub(once, map_path, rules)
    assert once == twice
    mp = json.loads(map_path.read_text())
    assert len(mp["classes"].get("PASSWORD", [])) == 1
