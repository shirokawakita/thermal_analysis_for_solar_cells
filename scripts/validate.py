#!/usr/bin/env python
"""Validation checks against reference geo_panel_thermal.py results."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config
from src.geo_panel_model import run_annual_model


def main() -> int:
    config = load_config(ROOT / "config" / "default_panel.yaml")
    result = run_annual_model(config)
    ecl_mask = result.eclipse_fraction > 0

    print("=== GEO Panel Thermal Model Validation (1-node reference) ===\n")
    ok = True

    t_sl_max = float(result.t_sunlit_c.max())
    t_sl_min = float(result.t_sunlit_c.min())
    t_ecl_min = float(result.t_eclipse_min_c[ecl_mask].min())
    t_avg_mean = float(result.t_orbital_avg_c.mean())
    s_min, s_max = float(result.solar_flux.min()), float(result.solar_flux.max())
    ecl_max = float(result.eclipse_duration_min.max())

    check1 = 30 <= t_sl_max <= 45 and 30 <= t_sl_min <= 45
    print(f"1. Sunlit equilibrium: {t_sl_min:.1f} ~ {t_sl_max:.1f} degC")
    print(f"   PASS: {check1} (reference ~35-40 degC)")
    ok = ok and check1

    check2 = t_ecl_min < -100
    print(f"\n2. Eclipse minimum: {t_ecl_min:.1f} degC")
    print(f"   PASS: {check2} (reference ~-180 degC order)")
    ok = ok and check2

    check3 = 28 <= t_avg_mean <= 38
    print(f"\n3. Orbital annual average: {t_avg_mean:.1f} degC")
    print(f"   PASS: {check3} (reference ~30-35 degC)")
    ok = ok and check3

    check4 = 65 <= ecl_max <= 75
    print(f"\n4. Max eclipse duration: {ecl_max:.1f} min")
    print(f"   PASS: {check4} (reference 72 min)")
    ok = ok and check4

    check5 = 1310 <= s_min <= 1330 and 1400 <= s_max <= 1420
    print(f"\n5. Solar flux range: {s_min:.1f} ~ {s_max:.1f} W/m2")
    print(f"   PASS: {check5} (reference 1320-1410 W/m2)")
    ok = ok and check5

    check6 = t_ecl_min < t_sl_min - 50
    print(f"\n6. Eclipse colder than sunlit: delta = {t_sl_min - t_ecl_min:.1f} degC")
    print(f"   PASS: {check6}")
    ok = ok and check6

    print(f"\n=== Overall: {'PASS' if ok else 'FAIL'} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
