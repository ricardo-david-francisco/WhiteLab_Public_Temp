"""Encrypted-at-rest persistence for the WhiteLab anonymisation map.

The vanilla anonymiser stores the placeholder ↔ original-value table in
a plain JSON file (``.anonmap.json``). That file is gitignored, but it
is still plaintext on disk. For password / token classes the user
explicitly asked to keep the round-trip data encrypted, with a key
that lives only on the operator's laptop.

This module is a thin wrapper around the ``age`` binary
(`<https://age-encryption.org>`_) so the dependency surface stays at:

* the Go ``age`` binary (already vendored in ``sandbox/Dockerfile``);
* one private key file at ``vault/anonmap.key`` (gitignored);
* one ciphertext map at ``vault/anonmap.age`` (gitignored).

CI runs without the key file and never decrypts. ``--verify`` mode is
read-only and does not touch the encrypted map at all, so CI stays
fully offline-safe.

Design choices
==============

* No persistent decrypted file ever lands on disk: everything goes
  through ``stdin`` / ``stdout`` of the ``age`` subprocess.
* Failure modes are loud: missing key, wrong key, malformed ciphertext
  all raise ``SecretMapError`` rather than silently degrading.
* The on-disk format is exactly the JSON the rest of the anonymiser
  already understands, so this module can be removed or replaced
  without rewriting the call sites.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class SecretMapError(RuntimeError):
    """Raised on any age / IO failure of the encrypted secret map."""


def _age_binary() -> str:
    path = shutil.which("age")
    if path is None:
        raise SecretMapError(
            "the 'age' binary is not on PATH. Install it from "
            "https://age-encryption.org or use the WhiteLab sandbox "
            "image which vendors a pinned build."
        )
    return path


def _age_keygen_binary() -> str:
    path = shutil.which("age-keygen")
    if path is None:
        raise SecretMapError(
            "the 'age-keygen' binary is not on PATH (it ships with age)."
        )
    return path


def _derive_recipient(identity_key: Path) -> str:
    """Return the ``age1...`` public recipient string for an identity file."""
    proc = subprocess.run(  # noqa: S603 - args validated, shell=False.
        [_age_keygen_binary(), "-y", str(identity_key)],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SecretMapError(f"age-keygen -y failed: {stderr or '<no stderr>'}")
    recipient = proc.stdout.decode("utf-8").strip()
    if not recipient.startswith("age1"):
        raise SecretMapError(
            f"identity at {identity_key}: derived recipient is not age1..."
        )
    return recipient


def _run(cmd: list[str], stdin_bytes: bytes) -> bytes:
    # No shell=True; arguments are a fixed list. Path inputs are
    # validated by the caller before reaching this function.
    proc = subprocess.run(  # noqa: S603 - args validated, shell=False.
        cmd,
        input=stdin_bytes,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SecretMapError(
            f"age failed (exit {proc.returncode}): {stderr or '<no stderr>'}"
        )
    return proc.stdout


def encrypt_to_file(plaintext: bytes, recipient_key: Path, dst: Path) -> None:
    """Encrypt ``plaintext`` to ``dst`` for the given age identity file.

    ``recipient_key`` is the **identity** file (``AGE-SECRET-KEY-...``);
    the public-recipient half is derived on the fly via
    ``age-keygen -y`` so the caller never has to maintain a parallel
    public-key file.
    """
    if not recipient_key.is_file():
        raise SecretMapError(f"recipient key not found: {recipient_key}")
    recipient = _derive_recipient(recipient_key)
    out = _run(
        [
            _age_binary(),
            "--encrypt",
            "--armor",
            "--recipient",
            recipient,
            "-o",
            "-",
        ],
        stdin_bytes=plaintext,
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_bytes(out)
    os.replace(tmp, dst)


def decrypt_from_file(src: Path, identity_key: Path) -> bytes:
    """Return the plaintext bytes of ``src`` decrypted with ``identity_key``."""
    if not src.is_file():
        raise SecretMapError(f"ciphertext not found: {src}")
    if not identity_key.is_file():
        raise SecretMapError(f"identity key not found: {identity_key}")
    return _run(
        [
            _age_binary(),
            "--decrypt",
            "--identity",
            str(identity_key),
            str(src),
        ],
        stdin_bytes=b"",
    )


def load_encrypted_map(path: Path, identity_key: Path) -> Dict[str, Any]:
    """Decrypt and parse a JSON map. Returns an empty bootstrap on miss."""
    if not path.is_file():
        return {"version": 1, "classes": {}}
    raw = decrypt_from_file(path, identity_key)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecretMapError(f"map at {path}: malformed JSON ({exc})") from exc
    if not isinstance(data, dict) or "classes" not in data:
        raise SecretMapError(f"map at {path}: missing 'classes' key")
    return data


def save_encrypted_map(
    path: Path, data: Dict[str, Any], recipient_key: Path
) -> None:
    """Serialise ``data`` to JSON and encrypt it to ``path``."""
    payload = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
    encrypt_to_file(payload, recipient_key, path)


def is_encrypted_map_path(path: Path) -> bool:
    """True if ``path`` should round-trip via age (suffix ``.age``)."""
    return path.suffix == ".age"


def resolve_identity_key(
    explicit: Optional[Path] = None,
) -> Optional[Path]:
    """Locate the operator's age identity key.

    Resolution order:

    1. ``explicit`` argument (CLI override).
    2. ``$WHITELAB_ANONMAP_KEY`` environment variable.
    3. ``vault/anonmap.key`` under the repo root, if it exists.

    Returns ``None`` if none of the above resolve. Callers in CI can
    interpret ``None`` as "no key on this runner; do not attempt to
    decrypt".
    """
    if explicit is not None:
        return explicit if explicit.is_file() else None
    env = os.environ.get("WHITELAB_ANONMAP_KEY")
    if env:
        cand = Path(env)
        return cand if cand.is_file() else None
    # Walk up from this file to find the repo root marker.
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / "Makefile").exists():
            cand = parent / "vault" / "anonmap.key"
            return cand if cand.is_file() else None
    return None
