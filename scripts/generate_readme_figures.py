#!/usr/bin/env python
"""Generate figures for README documentation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.readme_figures import generate_all
from src.guide_figures import generate_guide_figures

if __name__ == "__main__":
    out = ROOT / "docs" / "images"
    cfg = ROOT / "config" / "default_panel.yaml"
    print(f"Generating README figures -> {out}")
    generate_all(cfg, out)
    print("Generating guide figures...")
    generate_guide_figures(cfg, out)
    print("Done.")
