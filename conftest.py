"""Ensure the repo root is on sys.path so `src.csnote.*` imports work in tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
