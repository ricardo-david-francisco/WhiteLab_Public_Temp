"""Tests for the age-encrypted secret map round-trip.

These tests are skipped automatically if the ``age`` binary is not on
``PATH`` (e.g. on a stripped-down CI runner). When ``age`` is present
the suite verifies the full encrypt → decrypt → json-load lifecycle
and the failure modes used by the anonymiser.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tools.anonymizer import secret_map

age_missing = shutil.which("age") is None
pytestmark = pytest.mark.skipif(
    age_missing, reason="age binary not available; secret_map tests skipped."
)


@pytest.fixture()
def keypair(tmp_path: Path) -> Path:
    """Return the path to a freshly generated age identity file."""
    key = tmp_path / "id.age.key"
    proc = subprocess.run(
        ["age-keygen", "-o", str(key)],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return key


def test_round_trip_json(tmp_path: Path, keypair: Path):
    cipher = tmp_path / "anonmap.age"
    payload = {"version": 1, "classes": {"PASSWORD": [
        {"id": "PASSWORD_001", "value": "topsecret", "first_seen": "x"},
    ]}}
    secret_map.save_encrypted_map(cipher, payload, keypair)
    assert cipher.is_file()
    assert cipher.read_bytes().startswith(b"-----BEGIN AGE ENCRYPTED FILE-----")
    out = secret_map.load_encrypted_map(cipher, keypair)
    assert out == payload


def test_load_missing_returns_bootstrap(tmp_path: Path, keypair: Path):
    out = secret_map.load_encrypted_map(tmp_path / "nope.age", keypair)
    assert out == {"version": 1, "classes": {}}


def test_wrong_key_raises(tmp_path: Path, keypair: Path):
    cipher = tmp_path / "anonmap.age"
    secret_map.save_encrypted_map(cipher, {"version": 1, "classes": {}}, keypair)
    other = tmp_path / "other.age.key"
    subprocess.run(["age-keygen", "-o", str(other)], check=True, capture_output=True)
    with pytest.raises(secret_map.SecretMapError):
        secret_map.load_encrypted_map(cipher, other)


def test_missing_age_recipient_raises(tmp_path: Path):
    with pytest.raises(secret_map.SecretMapError):
        secret_map.encrypt_to_file(b"hi", tmp_path / "missing.key", tmp_path / "out.age")


def test_resolve_identity_key_explicit(tmp_path: Path, keypair: Path):
    assert secret_map.resolve_identity_key(keypair) == keypair


def test_resolve_identity_key_explicit_missing(tmp_path: Path):
    assert secret_map.resolve_identity_key(tmp_path / "no.key") is None


def test_resolve_identity_key_via_env(monkeypatch: pytest.MonkeyPatch, keypair: Path):
    monkeypatch.setenv("WHITELAB_ANONMAP_KEY", str(keypair))
    assert secret_map.resolve_identity_key() == keypair


def test_is_encrypted_map_path():
    assert secret_map.is_encrypted_map_path(Path("vault/anonmap.age"))
    assert not secret_map.is_encrypted_map_path(Path(".anonmap.json"))


def test_anonymizer_round_trip_via_encrypted_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, keypair: Path
):
    """End-to-end: anonymise → save encrypted → reload → rehydrate."""
    from tools.anonymizer import anonymize, rehydrate

    monkeypatch.setenv("WHITELAB_ANONMAP_KEY", str(keypair))
    src = 'password = "Sup3rS3cret!"'
    map_path = tmp_path / "anonmap.age"
    rules, _ = anonymize.load_rules(anonymize.DEFAULT_RULES)

    mp = anonymize.load_map(map_path)
    out = anonymize.scrub_text(src, rules, mp)
    anonymize.save_map(map_path, mp)
    assert "Sup3rS3cret!" not in out
    assert "PASSWORD_001" in out

    # Reload from cipher and rehydrate.
    mp2 = anonymize.load_map(map_path)
    lut = rehydrate.build_lookup(mp2)
    restored = rehydrate.rehydrate(out, lut)
    assert restored == src
