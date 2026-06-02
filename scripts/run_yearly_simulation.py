#!/usr/bin/env python
"""Run GEO solar panel yearly thermal simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config
from src.simulation import (
    load_result_from_csv,
    plot_results,
    run_simulation,
    save_results,
)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GEO panel yearly thermal simulation")
    parser.add_argument(
        "--config",
        default=str(ROOT / "config" / "default_panel.yaml"),
        help="Path to YAML config",
    )
    parser.add_argument("--days", type=int, default=None, help="Override duration [days]")
    parser.add_argument("--output-dir", default=None, help="Override output directory")
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Replot from existing output/daily_temperature_trend.csv (no re-simulation)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.days is not None:
        config.simulation.duration_days = float(args.days)
    if args.output_dir is not None:
        config.simulation.output_dir = args.output_dir

    output_dir = ROOT / config.simulation.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "daily_temperature_trend.csv"
    if args.plot_only:
        if not csv_path.exists():
            print(f"Error: {csv_path} not found. Run simulation first.")
            sys.exit(1)
        print(f"Plot-only mode: {csv_path}")
        result = load_result_from_csv(csv_path, config)
    else:
        print(f"Running 1-node annual model: {config.simulation.duration_days:.0f} days")
        print(f"Output: {output_dir}")
        result = run_simulation(config)
        save_results(result, output_dir)

    plot_results(result, config, output_dir)

    ecl_mask = result.eclipse_fraction > 0
    print("Done.")
    print(f"  Sunlit  MAX: {result.t_sunlit_c.max():.1f} degC  (DOY {result.days[result.t_sunlit_c.argmax()]})")
    if np.any(ecl_mask):
        print(f"  Eclipse MIN: {result.t_eclipse_min_c[ecl_mask].min():.1f} degC")
    else:
        print("  Eclipse MIN: n/a (no eclipse days in this period)")
    print(f"  Plot: {output_dir / 'yearly_temperature_timeseries.png'}")


if __name__ == "__main__":
    main()
