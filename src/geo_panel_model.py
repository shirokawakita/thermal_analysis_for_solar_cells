"""
GEO solar panel annual thermal model (1-node, dual-face radiation).

Based on equilibrium heat balance + eclipse transient cooling, aligned with
standard GEO array thermal screening (ECSS / NASA SP-8105 style lumped model).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config_loader import AppConfig
from .constants import STEFAN_BOLTZMANN

# GEO geometry (m)
R_GEO_M = 42164.0e3
R_EARTH_M = 6371.0e3
OMEGA_EARTH = math.pi * (R_EARTH_M / R_GEO_M) ** 2
VIEW_FACTOR_EARTH = OMEGA_EARTH / (2.0 * math.pi)
OBLIQUITY_DEG = 23.45


@dataclass
class AnnualThermalResult:
    days: np.ndarray
    solar_flux: np.ndarray
    eclipse_duration_min: np.ndarray
    eclipse_fraction: np.ndarray
    beta_angle_deg: np.ndarray
    incidence_angle_deg: np.ndarray
    t_sunlit_c: np.ndarray
    t_eclipse_min_c: np.ndarray
    t_orbital_avg_c: np.ndarray


def sun_declination_deg(doy: float) -> float:
    """Solar declination [deg] (sinusoidal approximation)."""
    return OBLIQUITY_DEG * math.sin(math.radians(360.0 * (doy - 81.0) / 365.25))


def beta_angle_deg(doy: float) -> float:
    """
    GEO beta angle: angle between the Sun vector and the equatorial orbital plane [deg].

    For equatorial GEO, beta equals the solar declination (signed).
    """
    return sun_declination_deg(doy)


def panel_incidence_angle_deg(
    doy: float,
    *,
    paddle_tracks_declination: bool = True,
) -> float:
    """
    Daily maximum solar incidence on the cell surface [deg] (Sun vs. panel normal).

    Without paddle: incidence equals |beta| (panel normal in equatorial plane).
    With east-west single-axis paddle on N/S panel: declination is tracked; the
    untracked Sun motion over 24 h gives theta_max = arcsin(|cos(delta)|).
    """
    dec_rad = math.radians(sun_declination_deg(doy))
    if not paddle_tracks_declination:
        return abs(math.degrees(dec_rad))
    return math.degrees(math.asin(min(1.0, abs(math.cos(dec_rad)))))


def eclipse_duration_min(doy: float, t_max: float = 72.0, half_width: float = 22.0) -> float:
    """Daily GEO eclipse duration [min] (spring/autumn seasons around equinoxes)."""

    def _season(d: float, d0: float) -> float:
        dt = d - d0
        if abs(dt) > half_width:
            return 0.0
        return t_max * math.sqrt(max(0.0, 1.0 - (dt / half_width) ** 2))

    return max(_season(doy, 81.0), _season(doy, 267.0))


def sun_flux_w_m2(doy: float, s0: float) -> float:
    """Solar flux at 1 AU distance variation [W/m^2]."""
    dist_au = 1.0 - 0.01671 * math.cos(2.0 * math.pi * (doy - 3.0) / 365.25)
    return s0 / dist_au**2


def emissivity_area_sum(
    epsilon_front: float,
    epsilon_back: float,
    area_front: float,
    area_back: float,
) -> float:
    """Effective emissivity-weighted radiating area: ε_front·A_front + ε_back·A_back."""
    return epsilon_front * area_front + epsilon_back * area_back


def equilibrium_temperature_k(
    solar_flux: float,
    *,
    alpha_s: float,
    epsilon_front: float,
    epsilon_back: float,
    eta_eol: float,
    area_front: float,
    area_back: float,
    t_earth: float,
    alpha_albedo: float,
    eclipse_fraction: float = 0.0,
) -> float:
    """
    Steady 1-node temperature with dual-face radiation to space.

    Energy in: absorbed solar (after electrical conversion) + Earth IR + albedo.
    Energy out: σ · (ε_front·A_front + ε_back·A_back) · T⁴

    When A_front = A_back, solar-only balance: Q_solar·(1−η) = (ε_front + ε_back)·σ·T⁴.
    """
    ecl_f = eclipse_fraction
    eps_a = emissivity_area_sum(epsilon_front, epsilon_back, area_front, area_back)

    q_solar = (1.0 - ecl_f) * alpha_s * (1.0 - eta_eol) * solar_flux * area_front
    q_ir = (
        epsilon_back
        * STEFAN_BOLTZMANN
        * t_earth**4
        * VIEW_FACTOR_EARTH
        * area_back
        * (1.0 - ecl_f)
    )
    q_alb = (
        (1.0 - ecl_f)
        * alpha_s
        * solar_flux
        * alpha_albedo
        * VIEW_FACTOR_EARTH
        * area_front
    )
    q_in = q_solar + q_ir + q_alb
    if q_in <= 0.0 or eps_a <= 0.0:
        return 0.0
    return (q_in / (STEFAN_BOLTZMANN * eps_a)) ** 0.25


def eclipse_minimum_temperature_k(
    t_start_k: float,
    eclipse_duration_min: float,
    *,
    epsilon_front: float,
    epsilon_back: float,
    area_front: float,
    area_back: float,
    m_cp: float,
    dt_s: float = 10.0,
) -> float:
    """Integrate radiative cooling during eclipse [K] (both faces radiate)."""
    if eclipse_duration_min <= 0.0:
        return t_start_k
    eps_a = emissivity_area_sum(epsilon_front, epsilon_back, area_front, area_back)
    t = t_start_k
    for _ in np.arange(0.0, eclipse_duration_min * 60.0, dt_s):
        q_rad = STEFAN_BOLTZMANN * eps_a * t**4
        t = max(t - q_rad / m_cp * dt_s, 0.0)
    return t


def orbital_average_temperature_k(t_sunlit_k: float, t_eclipse_k: float, ecl_frac: float) -> float:
    """Radiative average over one orbit: T = ((1-f)Ts^4 + f Te^4)^0.25."""
    return ((1.0 - ecl_frac) * t_sunlit_k**4 + ecl_frac * t_eclipse_k**4) ** 0.25


def run_annual_model(
    config: AppConfig,
    *,
    eta_eol: float | None = None,
) -> AnnualThermalResult:
    """Compute daily sunlit, eclipse minimum, and orbital-average temperatures."""
    th = config.thermal
    panel = config.panel

    alpha_s = th.alpha_s
    eps_f = th.epsilon_front
    eps_b = th.epsilon_back
    eta_eol = th.eta_eol if eta_eol is None else eta_eol
    m_cp = th.m_cp_j_k
    s0 = th.solar_constant_w_m2
    t_earth = th.earth_ir_temperature_k
    alpha_alb = th.earth_albedo

    area_front = panel.area_m2
    area_back = panel.area_m2

    n_days = int(config.simulation.duration_days)
    days = np.arange(1, n_days + 1)

    solar_flux = np.zeros(n_days)
    ecl_min = np.zeros(n_days)
    ecl_frac = np.zeros(n_days)
    t_sl = np.zeros(n_days)
    t_ecl = np.zeros(n_days)
    t_avg = np.zeros(n_days)
    beta = np.zeros(n_days)
    incidence = np.zeros(n_days)

    paddle = config.panel.paddle_tracks_declination

    for i, d in enumerate(days):
        d = float(d)
        s = sun_flux_w_m2(d, s0)
        beta[i] = beta_angle_deg(d)
        incidence[i] = panel_incidence_angle_deg(d, paddle_tracks_declination=paddle)
        em = eclipse_duration_min(float(d))
        ef = em / (24.0 * 60.0)

        ts = equilibrium_temperature_k(
            s,
            alpha_s=alpha_s,
            epsilon_front=eps_f,
            epsilon_back=eps_b,
            eta_eol=eta_eol,
            area_front=area_front,
            area_back=area_back,
            t_earth=t_earth,
            alpha_albedo=alpha_alb,
            eclipse_fraction=0.0,
        )
        te = eclipse_minimum_temperature_k(
            ts,
            em,
            epsilon_front=eps_f,
            epsilon_back=eps_b,
            area_front=area_front,
            area_back=area_back,
            m_cp=m_cp,
            dt_s=config.simulation.dt_eclipse_seconds,
        )
        ta = orbital_average_temperature_k(ts, te, ef)

        solar_flux[i] = s
        ecl_min[i] = em
        ecl_frac[i] = ef
        t_sl[i] = ts
        t_ecl[i] = te
        t_avg[i] = ta

    return AnnualThermalResult(
        days=days,
        solar_flux=solar_flux,
        eclipse_duration_min=ecl_min,
        eclipse_fraction=ecl_frac,
        beta_angle_deg=beta,
        incidence_angle_deg=incidence,
        t_sunlit_c=t_sl - 273.15,
        t_eclipse_min_c=t_ecl - 273.15,
        t_orbital_avg_c=t_avg - 273.15,
    )
