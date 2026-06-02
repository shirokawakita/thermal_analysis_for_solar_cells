"""Yearly thermal simulation driver and post-processing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config_loader import AppConfig
from .geo_panel_model import (
    AnnualThermalResult,
    beta_angle_deg,
    panel_incidence_angle_deg,
    run_annual_model,
)
from .plotting import plot_annual_results


def run_simulation(config: AppConfig) -> AnnualThermalResult:
    return run_annual_model(config)


def load_result_from_csv(csv_path: Path, config: AppConfig) -> AnnualThermalResult:
    """Rebuild result from daily_temperature_trend.csv for replotting."""
    df = pd.read_csv(csv_path)
    days = df["day_of_year"].values
    if "beta_angle_deg" in df.columns:
        beta = df["beta_angle_deg"].values
        incidence = df["incidence_angle_deg"].values
    else:
        paddle = config.panel.paddle_tracks_declination
        beta = np.array([beta_angle_deg(float(d)) for d in days])
        incidence = np.array(
            [
                panel_incidence_angle_deg(float(d), paddle_tracks_declination=paddle)
                for d in days
            ]
        )
    return AnnualThermalResult(
        days=days,
        solar_flux=df["solar_flux_w_m2"].values,
        eclipse_duration_min=df["eclipse_duration_min"].values,
        eclipse_fraction=df["eclipse_fraction"].values,
        beta_angle_deg=beta,
        incidence_angle_deg=incidence,
        t_sunlit_c=df["t_sunlit_c"].values,
        t_eclipse_min_c=df["t_eclipse_min_c"].values,
        t_orbital_avg_c=df["t_orbital_avg_c"].values,
    )


def _month_day_mask(days: np.ndarray, month: int) -> np.ndarray:
    lo = (month - 1) * 30 + 1
    hi = month * 30
    return (days >= lo) & (days <= hi)


def save_results(result: AnnualThermalResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "day_of_year": result.days,
            "solar_flux_w_m2": result.solar_flux,
            "eclipse_duration_min": result.eclipse_duration_min,
            "eclipse_fraction": result.eclipse_fraction,
            "beta_angle_deg": result.beta_angle_deg,
            "incidence_angle_deg": result.incidence_angle_deg,
            "t_sunlit_c": result.t_sunlit_c,
            "t_eclipse_min_c": result.t_eclipse_min_c,
            "t_orbital_avg_c": result.t_orbital_avg_c,
        }
    ).to_csv(output_dir / "daily_temperature_trend.csv", index=False)

    ecl_mask = result.eclipse_fraction > 0
    if len(result.days) >= 300:
        monthly = pd.DataFrame(
            {
                "month": np.arange(1, 13),
                "t_sunlit_mean_c": [
                    float(result.t_sunlit_c[_month_day_mask(result.days, m)].mean())
                    if np.any(_month_day_mask(result.days, m))
                    else float("nan")
                    for m in range(1, 13)
                ],
                "t_eclipse_min_c": [
                    float(
                        result.t_eclipse_min_c[
                            ecl_mask & _month_day_mask(result.days, m)
                        ].min()
                    )
                    if np.any(ecl_mask & _month_day_mask(result.days, m))
                    else float("nan")
                    for m in range(1, 13)
                ],
                "t_orbital_avg_mean_c": [
                    float(result.t_orbital_avg_c[_month_day_mask(result.days, m)].mean())
                    if np.any(_month_day_mask(result.days, m))
                    else float("nan")
                    for m in range(1, 13)
                ],
            }
        )
        monthly.to_csv(output_dir / "monthly_trend.csv", index=False)


def plot_results(result: AnnualThermalResult, config: AppConfig, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_annual_results(result, config, output_dir)
