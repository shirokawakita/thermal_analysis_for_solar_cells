"""Educational figures aligned with Claude share guide (beta, eclipse, efficiency)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config_loader import AppConfig, load_config
from .constants import STEFAN_BOLTZMANN
from .geo_panel_model import (
    VIEW_FACTOR_EARTH,
    beta_angle_deg,
    eclipse_duration_min,
    emissivity_area_sum,
    equilibrium_temperature_k,
    run_annual_model,
    sun_flux_w_m2,
)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
M_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
BETA_ECLIPSE_DEG = 8.7  # |beta| below this: GEO can enter Earth umbra


def _save(fig: go.Figure, path: Path, w: int = 1000, h: int = 560) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.update_layout(paper_bgcolor="#fff", plot_bgcolor="#fff", font=dict(size=12))
    fig.write_image(str(path), width=w, height=h, scale=2)


def fig_guide_ecliptic_equator(out: Path) -> None:
    """Top view: ecliptic orbit + tilted equatorial plane (4 seasons)."""
    fig = go.Figure()
    t = np.linspace(0, 2 * np.pi, 200)
    r_ecl = 1.0
    fig.add_trace(
        go.Scatter(
            x=r_ecl * np.cos(t),
            y=r_ecl * np.sin(t),
            mode="lines",
            line=dict(color="#f39c12", width=2, dash="dash"),
            name="黄道面（地球公転）",
        )
    )
    seasons = [
        (0, 1.0, 0, "春分 β=0° 食あり", "#e74c3c"),
        (np.pi / 2, 0, 1.0, "夏至 β=+23.45°", "#3498db"),
        (np.pi, -1.0, 0, "秋分 β=0° 食あり", "#e74c3c"),
        (3 * np.pi / 2, 0, -1.0, "冬至 β=−23.45°", "#3498db"),
    ]
    tilt = math.radians(23.45)
    for angle, ex, ey, label, col in seasons:
        # Equatorial plane as ellipse in ecliptic view (tilted ring)
        eq_t = np.linspace(0, 2 * np.pi, 100)
        x_eq = 0.35 * np.cos(eq_t)
        y_eq = 0.35 * np.sin(eq_t) * np.cos(tilt) + 0.35 * np.sin(eq_t) * np.sin(tilt) * 0.3
        z_proj_y = 0.35 * np.sin(eq_t) * np.sin(tilt)
        fig.add_trace(
            go.Scatter(
                x=ex + x_eq,
                y=ey + z_proj_y,
                mode="lines",
                line=dict(color="#1abc9c", width=1.5),
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[ex],
                y=[ey],
                mode="markers+text",
                marker=dict(size=14, color=col),
                text=[label],
                textposition="top center",
                showlegend=False,
            )
        )
        # Satellite on equatorial ring
        fig.add_trace(
            go.Scatter(
                x=[ex + 0.35],
                y=[ey],
                mode="markers",
                marker=dict(size=10, color="#2c3e50", symbol="square"),
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=20, color="#0984e3"), text=["太陽"], textposition="middle center", showlegend=False)
    )
    fig.update_layout(
        title="黄道面と赤道面（GEO軌道面）— 季節ごとに β角と食の有無が変わる",
        xaxis=dict(scaleanchor="y", title="黄道面 X"),
        yaxis=dict(title="黄道面 Y"),
        showlegend=True,
    )
    _save(fig, out / "guide01_ecliptic_equator.png", h=600)


def fig_guide_beta_definition(out: Path) -> None:
    """Beta = angle between Sun vector and orbital plane."""
    fig = go.Figure()
    # Orbital plane (horizontal line)
    fig.add_trace(go.Scatter(x=[-1, 1], y=[0, 0], mode="lines", line=dict(color="#636e72", width=3), name="軌道面（赤道面）"))
    # Sun vector at beta = 20 deg
    beta = 20.0
    b = math.radians(beta)
    fig.add_trace(
        go.Scatter(x=[0, 0.9 * math.cos(b)], y=[0, 0.9 * math.sin(b)], mode="lines+markers", line=dict(color="#f39c12", width=3), marker=dict(size=8), name="太陽方向")
    )
    # Arc for beta
    arc_t = np.linspace(0, b, 30)
    fig.add_trace(
        go.Scatter(x=0.35 * np.cos(arc_t), y=0.35 * np.sin(arc_t), mode="lines", line=dict(color="#e74c3c", width=2), name="β角")
    )
    fig.add_annotation(x=0.45, y=0.12, text="β", showarrow=False, font=dict(size=16, color="#e74c3c"))
    fig.add_annotation(x=0.5, y=-0.15, text="β = 太陽ベクトルと軌道面のなす角<br>GEOでは β ≈ 太陽赤緯 δ", showarrow=False)
    fig.update_layout(title="β角の定義", xaxis=dict(visible=False, range=[-1.1, 1.1]), yaxis=dict(visible=False, range=[-0.3, 1.0], scaleanchor="x"))
    _save(fig, out / "guide02_beta_definition.png", w=700, h=450)


def fig_guide_eclipse_geometry(out: Path) -> None:
    """Side view: Earth shadow vs beta."""
    fig = go.Figure()
    # Earth
    theta = np.linspace(0, 2 * np.pi, 80)
    fig.add_trace(
        go.Scatter(x=0.2 * np.cos(theta), y=0.2 * np.sin(theta), fill="toself", fillcolor="rgba(9,132,227,0.4)", line=dict(color="#0984e3"), showlegend=False)
    )
    # Shadow cone (simplified triangle)
    fig.add_trace(go.Scatter(x=[-0.2, -2.5, -2.5, -0.2], y=[0.2, 0.5, -0.5, -0.2], fill="toself", fillcolor="rgba(50,50,50,0.25)", line=dict(width=0), name="地球本影"))
    # Sun rays
    for y0 in [-0.3, 0, 0.3]:
        fig.add_trace(go.Scatter(x=[-3, 0.5], y=[y0, y0], mode="lines", line=dict(color="#f1c40f", width=1), showlegend=False))
    # beta=0 path through shadow
    fig.add_trace(go.Scatter(x=[-1.5, -1.5], y=[-0.4, 0.4], mode="lines", line=dict(color="#e74c3c", width=3), name="β≈0°: 影を貫通 → 最大72min"))
    # beta large path above shadow
    fig.add_trace(go.Scatter(x=[-1.2, -0.5], y=[0.8, 0.8], mode="lines", line=dict(color="#2ecc71", width=3, dash="dash"), name="|β|>β_crit: 全日照"))
    fig.add_annotation(x=-1.5, y=0.5, text="食", showarrow=False)
    fig.add_annotation(x=-2.2, y=0, text="太陽", showarrow=False)
    fig.update_layout(title="日食と β角 — β≈0° で影に入り最大約72分/日", xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"))
    _save(fig, out / "guide03_eclipse_geometry.png", w=900, h=450)


def fig_guide_beta_eclipse_zone(out: Path) -> None:
    """Yearly beta with eclipse zone |beta| < 8.7 deg."""
    days = np.arange(1, 366)
    beta = np.array([beta_angle_deg(float(d)) for d in days])
    ecl = np.array([eclipse_duration_min(float(d)) for d in days])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("β角の年変化", "日食時間"), vertical_spacing=0.12)
    fig.add_hrect(y0=-BETA_ECLIPSE_DEG, y1=BETA_ECLIPSE_DEG, fillcolor="rgba(231,76,60,0.15)", line_width=0, row=1, col=1)
    fig.add_trace(go.Scatter(x=days, y=beta, line=dict(color="#2ecc71", width=2), name="β"), row=1, col=1)
    fig.add_trace(go.Scatter(x=days, y=ecl, fill="tozeroy", line=dict(color="#74b9ff", width=2), name="日食"), row=2, col=1)
    fig.add_hline(y=72, line_dash="dash", line_color="#fd79a8", row=2, col=1)
    fig.update_xaxes(tickvals=M_STARTS, ticktext=MONTHS, row=2, col=1)
    fig.update_yaxes(title_text="β [°]", row=1, col=1)
    fig.update_yaxes(title_text="日食 [min]", row=2, col=1)
    fig.add_annotation(text=f"食可能域 |β| < {BETA_ECLIPSE_DEG}°", xref="paper", yref="paper", x=0.02, y=0.95, showarrow=False, font=dict(size=10, color="#e74c3c"))
    fig.update_layout(title="β角と日食シーズン（春分・秋分付近で |β|→0）", height=650)
    _save(fig, out / "guide04_beta_eclipse_zone.png", h=650)


def fig_guide_tilt_comparison(out: Path) -> None:
    """Beta profile: obliquity 23.45° vs 0°."""
    days = np.arange(1, 366)
    beta_real = np.array([beta_angle_deg(float(d)) for d in days])
    beta_zero = np.zeros_like(beta_real)

    fig = go.Figure()
    fig.add_hrect(y0=-BETA_ECLIPSE_DEG, y1=BETA_ECLIPSE_DEG, fillcolor="rgba(231,76,60,0.1)", line_width=0)
    fig.add_trace(go.Scatter(x=days, y=beta_real, name="地軸傾き 23.45°（実際）", line=dict(color="#e74c3c", width=2)))
    fig.add_trace(go.Scatter(x=days, y=beta_zero, name="地軸傾き 0°（仮想）", line=dict(color="#3498db", width=2, dash="dash")))
    fig.update_layout(
        title="地軸の傾きと β角 — 傾き0°なら β=0° が通年で毎日食",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis=dict(title="β [°]", range=[-30, 30]),
    )
    _save(fig, out / "guide05_tilt_comparison.png")


def fig_guide_orbit_temperature_efficiency(config: AppConfig, out: Path) -> None:
    """Single-orbit temperature for eta = 10%, 20%, 28%."""
    th = config.thermal
    area = config.panel.area_m2
    area_total = 2 * area
    orbit_s = 86164.0  # sidereal day [s]
    ecl_frac = 72.0 / (24.0 * 60.0)  # representative eclipse season day
    ecl_start = 0.45 * orbit_s
    ecl_end = ecl_start + 72.0 * 60.0
    dt = 30.0
    times = np.arange(0, orbit_s, dt)

    fig = go.Figure()
    colors = {0.10: "#3498db", 0.20: "#9b59b6", 0.28: "#e67e22"}
    for eta in [0.10, 0.20, 0.28]:
        s = sun_flux_w_m2(80.0, th.solar_constant_w_m2)
        t_eq = equilibrium_temperature_k(
            s, alpha_s=th.alpha_s, epsilon_front=th.epsilon_front,
            epsilon_back=th.epsilon_back, eta_eol=eta,
            area_front=area, area_back=area, t_earth=th.earth_ir_temperature_k,
            alpha_albedo=th.earth_albedo,
        )
        temps = []
        t = t_eq
        for tsec in times:
            in_ecl = ecl_start <= tsec <= ecl_end
            if not in_ecl:
                t = t_eq
            else:
                q = STEFAN_BOLTZMANN * emissivity_area_sum(
                    th.epsilon_front, th.epsilon_back, area, area
                ) * t**4
                t = max(t - q / th.m_cp_j_k * dt, 50.0)
            temps.append(t - 273.15)
        fig.add_trace(
            go.Scatter(
                x=times / 60.0,
                y=temps,
                name=f"η={int(eta*100)}%",
                line=dict(color=colors[eta], width=2),
            )
        )
    fig.add_vrect(x0=ecl_start / 60, x1=ecl_end / 60, fillcolor="rgba(50,50,50,0.1)", line_width=0)
    fig.update_layout(
        title="1軌道（約24h）の温度 — 発電効率が低いほど高温（食前平衡）",
        xaxis_title="時間 [min]",
        yaxis_title="温度 [°C]",
    )
    _save(fig, out / "guide06_orbit_efficiency.png")


def fig_guide_efficiency_annual(config: AppConfig, out: Path) -> None:
    """Annual T_sl for eta 10/20/28%."""
    fig = go.Figure()
    for eta, col in [(0.10, "#3498db"), (0.20, "#9b59b6"), (0.28, "#e67e22")]:
        res = run_annual_model(config, eta_eol=eta)
        fig.add_trace(
            go.Scatter(x=res.days, y=res.t_sunlit_c, name=f"η={int(eta*100)}%", line=dict(color=col, width=2))
        )
    fig.update_layout(
        title="年間日射平衡温度 — η_EOL が高いほど廃熱が減り低温",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis_title="T_sl [°C]",
    )
    _save(fig, out / "guide07_efficiency_annual.png")


def fig_guide_ns_panel_beta(out: Path) -> None:
    """N/S panels and incidence angle vs beta."""
    beta_vals = np.linspace(-25, 25, 50)
    cos_beta = np.cos(np.radians(beta_vals))
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=beta_vals, y=cos_beta, name="cos(β)", line=dict(color="#e67e22", width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=beta_vals, y=beta_vals, name="入射角 θ≈|β|（パドル未補償分）", line=dict(color="#1abc9c", width=2, dash="dash")), secondary_y=True)
    fig.update_xaxes(title_text="β [°]")
    fig.update_yaxes(title_text="cos(β) — 有効日射", secondary_y=False)
    fig.update_yaxes(title_text="θ [°]", secondary_y=True)
    fig.update_layout(title="南北面パネルと β角 — 出力・入射は cos(β) で低下")
    _save(fig, out / "guide08_ns_panel_cos_beta.png")


def generate_guide_figures(config_path: Path, out_dir: Path) -> None:
    config = load_config(config_path)
    fig_guide_ecliptic_equator(out_dir)
    fig_guide_beta_definition(out_dir)
    fig_guide_eclipse_geometry(out_dir)
    fig_guide_beta_eclipse_zone(out_dir)
    fig_guide_tilt_comparison(out_dir)
    fig_guide_orbit_temperature_efficiency(config, out_dir)
    fig_guide_efficiency_annual(config, out_dir)
    fig_guide_ns_panel_beta(out_dir)
