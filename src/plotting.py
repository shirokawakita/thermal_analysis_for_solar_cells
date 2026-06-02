"""Plotly-based yearly trend figures (reference style)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config_loader import AppConfig
from .geo_panel_model import AnnualThermalResult

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
M_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
BG = "#0d1117"
GRID = "#30363d"
TXT = "#e6edf3"


def plot_annual_results(
    result: AnnualThermalResult, config: AppConfig, output_dir: Path
) -> None:
    th = config.thermal
    days = result.days
    ecl_mask = result.eclipse_fraction > 0

    fig = make_subplots(
        rows=4,
        cols=1,
        subplot_titles=(
            "GEO Solar Array Panel - Annual Temperature Trend",
            "Daily Eclipse Duration (GEO, 24h orbit)",
            "Solar Beta Angle and Panel Incidence (GEO)",
            "Solar Flux Variation (Earth-Sun Distance)",
        ),
        vertical_spacing=0.06,
        row_heights=[0.38, 0.2, 0.2, 0.22],
    )

    for i in range(len(days) - 1):
        if ecl_mask[i] or ecl_mask[i + 1]:
            fig.add_vrect(
                x0=float(days[i]),
                x1=float(days[i + 1]),
                fillcolor="#1a2744",
                opacity=0.5,
                line_width=0,
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.t_sunlit_c,
            name="Sunlit (equilibrium)",
            line=dict(color="#ff9f43", width=2),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.t_eclipse_min_c,
            name="Eclipse (minimum)",
            line=dict(color="#48dbfb", width=1.8, dash="dash"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.t_orbital_avg_c,
            name="Orbital average",
            line=dict(color="#ff6b9d", width=1.5, dash="dot"),
        ),
        row=1,
        col=1,
    )

    im = int(np.argmax(result.t_sunlit_c))
    ecl_days = days[ecl_mask]
    ecl_vals = result.t_eclipse_min_c[ecl_mask]
    if len(ecl_days) > 0:
        ix = int(np.argmin(ecl_vals))
        fig.add_annotation(
            x=float(days[im]),
            y=float(result.t_sunlit_c[im]),
            text=f"Max: {result.t_sunlit_c[im]:.1f} degC<br>(DOY {days[im]})",
            showarrow=True,
            arrowhead=2,
            ax=40,
            ay=-30,
            font=dict(color="#ff9f43", size=10),
            row=1,
            col=1,
        )
        fig.add_annotation(
            x=float(ecl_days[ix]),
            y=float(ecl_vals[ix]),
            text=f"Min: {ecl_vals[ix]:.1f} degC<br>(DOY {ecl_days[ix]})",
            showarrow=True,
            arrowhead=2,
            ax=40,
            ay=40,
            font=dict(color="#48dbfb", size=10),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.eclipse_duration_min,
            name="Eclipse duration",
            fill="tozeroy",
            line=dict(color="#74b9ff", width=1.5),
            fillcolor="rgba(74,144,217,0.7)",
            showlegend=True,
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=72, line_dash="dash", line_color="#fd79a8", row=2, col=1)

    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.beta_angle_deg,
            name="Beta angle beta (Sun vs. equatorial plane)",
            line=dict(color="#2ecc71", width=2),
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.incidence_angle_deg,
            name="Panel incidence theta_max (daily)",
            line=dict(color="#a29bfe", width=1.8, dash="dash"),
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=23.45, line_dash="dot", line_color="#95a5a6", opacity=0.6, row=3, col=1)
    fig.add_hline(y=-23.45, line_dash="dot", line_color="#95a5a6", opacity=0.6, row=3, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="#95a5a6", opacity=0.4, row=3, col=1)

    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.solar_flux,
            name="Solar flux",
            line=dict(color="#ffd700", width=2),
            fill="tozeroy",
            fillcolor="rgba(255,215,0,0.15)",
        ),
        row=4,
        col=1,
    )
    fig.add_hline(
        y=th.solar_constant_w_m2,
        line_dash="dot",
        line_color="white",
        opacity=0.5,
        row=4,
        col=1,
    )

    for row in (1, 2, 3, 4):
        fig.update_xaxes(
            tickvals=M_STARTS,
            ticktext=MONTHS,
            range=[1, 365],
            gridcolor=GRID,
            row=row,
            col=1,
        )

    fig.update_yaxes(title_text="Temperature [degC]", range=[-200, 50], gridcolor=GRID, row=1, col=1)
    fig.update_yaxes(title_text="Eclipse Duration [min]", gridcolor=GRID, row=2, col=1)
    fig.update_yaxes(
        title_text="Angle [deg]",
        range=[-30, 90],
        gridcolor=GRID,
        row=3,
        col=1,
    )
    fig.update_yaxes(
        title_text="Solar Flux [W/m2]",
        range=[result.solar_flux.min() - 5, result.solar_flux.max() + 5],
        gridcolor=GRID,
        row=4,
        col=1,
    )

    fig.update_layout(
        height=1150,
        width=1200,
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TXT),
        legend=dict(bgcolor="#161b22", font=dict(color=TXT)),
        margin=dict(b=60),
    )
    fig.update_annotations(font_color=TXT)

    fig.add_annotation(
        text=(
            f"Params: alpha_s={th.alpha_s}, eps_f={th.epsilon_front}, "
            f"eps_b={th.epsilon_back}, eta_EOL={th.eta_eol}, "
            f"mCp={th.m_cp_j_k} J/K, dual-face radiation, 1-node model"
        ),
        xref="paper",
        yref="paper",
        x=0.5,
        y=-0.02,
        showarrow=False,
        font=dict(size=10, color="#8b949e"),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "yearly_temperature_timeseries.png"
    fig.write_image(str(out), width=1200, height=1150, scale=2)
