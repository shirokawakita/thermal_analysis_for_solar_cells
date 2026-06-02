"""Load YAML configuration into typed dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SimulationConfig:
    year: int
    duration_days: float
    dt_eclipse_seconds: float
    output_dir: str


@dataclass
class PanelConfig:
    area_m2: float
    paddle_tracks_declination: bool


@dataclass
class ThermalConfig:
    alpha_s: float
    epsilon_front: float  # cover glass (sun-facing)
    epsilon_back: float  # CFRP substrate (space-facing)
    eta_eol: float
    m_cp_j_k: float
    solar_constant_w_m2: float
    earth_ir_temperature_k: float
    earth_albedo: float


@dataclass
class AppConfig:
    simulation: SimulationConfig
    panel: PanelConfig
    thermal: ThermalConfig


def load_config(path: str | Path) -> AppConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    sim = raw["simulation"]
    th = raw["thermal"]
    return AppConfig(
        simulation=SimulationConfig(
            year=int(sim["year"]),
            duration_days=float(sim["duration_days"]),
            dt_eclipse_seconds=float(sim["dt_eclipse_seconds"]),
            output_dir=str(sim["output_dir"]),
        ),
        panel=PanelConfig(
            area_m2=float(raw["panel"]["area_m2"]),
            paddle_tracks_declination=bool(
                raw["panel"].get("paddle_tracks_declination", True)
            ),
        ),
        thermal=ThermalConfig(
            alpha_s=float(th["alpha_s"]),
            epsilon_front=float(th.get("epsilon_front", th.get("epsilon_ir", 0.85))),
            epsilon_back=float(th.get("epsilon_back", th.get("epsilon_ir", 0.82))),
            eta_eol=float(th["eta_eol"]),
            m_cp_j_k=float(th["m_cp_j_k"]),
            solar_constant_w_m2=float(th["solar_constant_w_m2"]),
            earth_ir_temperature_k=float(th["earth_ir_temperature_k"]),
            earth_albedo=float(th["earth_albedo"]),
        ),
    )
