#!/usr/bin/env python3
"""Pre-commit hook: run anonymizer in --verify mode on infra/."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.anonymizer.anonymize import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["--verify", str(ROOT / "infra")]))
