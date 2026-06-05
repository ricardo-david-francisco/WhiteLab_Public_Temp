"""Tests for the WhiteLab anonymizer.

Run::

    pytest tools/anonymizer/tests
"""
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


def test_mac_is_anonymized(map_path, rules):
    src = "static lease 3c:7c:3f:11:22:33 -> 192.168.20.10"
    out = _scrub(src, map_path, rules)
    assert "3c:7c:3f:11:22:33" not in out
    assert "MAC_001" in out


def test_rfc1918_is_preserved(map_path, rules):
    src = "interface 192.168.20.10 / 10.0.0.5 / 172.16.4.2"
    out = _scrub(src, map_path, rules)
    assert "192.168.20.10" in out
    assert "10.0.0.5" in out
    assert "172.16.4.2" in out


def test_public_ipv4_is_anonymized(map_path, rules):
    src = "upstream 23.45.67.89 / 198.51.100.5 (placeholder)"
    out = _scrub(src, map_path, rules)
    # 23.45.67.89 is global and not on the well-known DNS allow-list.
    assert "23.45.67.89" not in out
    assert "PUBLIC_IPV4_" in out
    # 198.51.100.0/24 is RFC5737 documentation - not is_global.
    assert "198.51.100.5" in out


def test_idempotent(map_path, rules):
    src = "lease 3c:7c:3f:11:22:33 from 23.45.67.89"
    once = _scrub(src, map_path, rules)
    twice = _scrub(once, map_path, rules)
    assert once == twice
    mp = json.loads(map_path.read_text())
    # Exactly one MAC and one PUBLIC_IPV4 should be in the map.
    assert len(mp["classes"].get("MAC", [])) == 1
    assert len(mp["classes"].get("PUBLIC_IPV4", [])) == 1


def test_deterministic_ordering(tmp_path: Path, rules):
    map_a = tmp_path / "a.json"
    map_b = tmp_path / "b.json"
    src = "lease 3c:7c:3f:11:22:33 ... lease 3c:7c:3f:11:22:44"
    out_a = _scrub(src, map_a, rules)
    out_b = _scrub(src, map_b, rules)
    assert out_a == out_b
    assert "MAC_001" in out_a
    assert "MAC_002" in out_a


def test_rehydrate_round_trip(map_path, rules):
    src = "host with mac 3c:7c:3f:11:22:33 reaching 23.45.67.89"
    scrubbed = _scrub(src, map_path, rules)
    mp = json.loads(map_path.read_text())
    lut = rehydrate.build_lookup(mp)
    restored = rehydrate.rehydrate(scrubbed, lut)
    assert restored == src


def test_placeholder_is_not_re_anonymized(map_path, rules):
    src = "lease MAC_001 reaches PUBLIC_IPV4_001"
    out = _scrub(src, map_path, rules)
    assert out == src
    mp = json.loads(map_path.read_text())
    assert mp.get("classes", {}) == {}


def test_age_secret_key_is_anonymized(map_path, rules):
    fake = "AGE-SECRET-KEY-1" + ("A" * 58)
    src = f"export VAULT_KEY={fake}"
    out = _scrub(src, map_path, rules)
    assert fake not in out
    assert "AGE_PRIV_001" in out


def test_jwt_is_anonymized(map_path, rules):
    fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    src = f"Authorization: Bearer {fake_jwt}"
    out = _scrub(src, map_path, rules)
    assert fake_jwt not in out
    assert "JWT_001" in out
