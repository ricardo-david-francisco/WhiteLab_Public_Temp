"""Shared pytest fixtures and path setup for the WhiteLab test suite.

The repository root is added to ``sys.path`` so tests can import
``tools.*`` modules without an editable install.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
