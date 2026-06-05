"""Re-hydrate an anonymized file using a JSON map.

Agent-only. Never run on the public-facing dev box. The map file is
expected to live under /run/fortress/ on the LXC 104 vault, mounted
tmpfs, decrypted from the age-encrypted on-disk copy.

Usage::

    python -m tools.anonymizer.rehydrate \\
        --in infra/opnsense/exports/config.anonymized.xml \\
        --out /run/fortress/staging/config.xml \\
        --map-file /run/fortress/anonmap.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

from tools.anonymizer.secret_map import (
    is_encrypted_map_path,
    load_encrypted_map,
    resolve_identity_key,
)

PLACEHOLDER_RE = re.compile(r"\b([A-Z][A-Z0-9_]+_[0-9]{3,})\b")


def build_lookup(mp: Dict) -> Dict[str, str]:
    """Flatten the map: placeholder id -> original value."""
    lut: Dict[str, str] = {}
    for entries in mp.get("classes", {}).values():
        for entry in entries:
            lut[entry["id"]] = entry["value"]
    return lut


def rehydrate(text: str, lut: Dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: lut.get(m.group(1), m.group(1)), text)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="rehydrate", description=__doc__)
    p.add_argument("--in", dest="src", type=Path, required=True)
    p.add_argument("--out", dest="dst", type=Path, required=True)
    p.add_argument("--map-file", dest="map_file", type=Path, required=True)
    args = p.parse_args(argv)

    if is_encrypted_map_path(args.map_file):
        identity = resolve_identity_key()
        if identity is None:
            print(
                f"rehydrate FAILED: encrypted map {args.map_file} requires "
                "an age identity (set $WHITELAB_ANONMAP_KEY or place "
                "vault/anonmap.key).",
                file=sys.stderr,
            )
            return 2
        mp = load_encrypted_map(args.map_file, identity)
    else:
        mp = json.loads(args.map_file.read_text(encoding="utf-8"))
    lut = build_lookup(mp)
    raw = args.src.read_text(encoding="utf-8")
    out = rehydrate(raw, lut)

    unresolved = [
        m.group(1)
        for m in PLACEHOLDER_RE.finditer(out)
        if m.group(1) not in lut
    ]
    if unresolved:
        print(
            f"rehydrate FAILED: {len(unresolved)} unresolved placeholder(s): "
            f"{sorted(set(unresolved))[:5]}...",
            file=sys.stderr,
        )
        return 1

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_text(out, encoding="utf-8")
    print(f"rehydrated {args.src} -> {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
