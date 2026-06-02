"""Generate explanatory figures referenced from README."""

from __future__ import annotations

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
    eclipse_minimum_temperature_k,
    emissivity_area_sum,
    equilibrium_temperature_k,
    orbital_average_temperature_k,
    run_annual_model,
    sun_flux_w_m2,
)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
M_STARTS = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
BG = "#ffffff"
GRID = "#dddddd"
TXT = "#222222"


def _save(fig: go.Figure, path: Path, width: int = 900, height: int = 500) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TXT, size=12),
        margin=dict(l=60, r=30, t=50, b=60),
    )
    fig.write_image(str(path), width=width, height=height, scale=2)


def fig_energy_balance(config: AppConfig, out: Path) -> None:
    """Bar chart of heat flux components at sunlit equilibrium (example: DOY 3)."""
    th = config.thermal
    area = config.panel.area_m2
    area_total = 2 * area
    doy = 3.0
    s = sun_flux_w_m2(doy, th.solar_constant_w_m2)
    t_k = equilibrium_temperature_k(
        s,
        alpha_s=th.alpha_s,
        epsilon_front=th.epsilon_front,
        epsilon_back=th.epsilon_back,
        eta_eol=th.eta_eol,
        area_front=area,
        area_back=area,
        t_earth=th.earth_ir_temperature_k,
        alpha_albedo=th.earth_albedo,
    )
    q_solar = th.alpha_s * (1 - th.eta_eol) * s * area
    q_ir = th.epsilon_back * STEFAN_BOLTZMANN * th.earth_ir_temperature_k**4 * VIEW_FACTOR_EARTH * area
    q_alb = th.alpha_s * s * th.earth_albedo * VIEW_FACTOR_EARTH * area
    q_rad = STEFAN_BOLTZMANN * emissivity_area_sum(
        th.epsilon_front, th.epsilon_back, area, area
    ) * t_k**4

    labels = ["日射吸収", "地球IR", "アルベド", "放射（出）"]
    values = [q_solar, q_ir, q_alb, -q_rad]
    colors = ["#ff9f43", "#e17055", "#fdcb6e", "#0984e3"]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=[abs(v) for v in values],
            marker_color=colors,
            text=[f"{abs(v):.0f} W" for v in values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"日射平衡時の熱収支（DOY {int(doy)}、T = {t_k - 273.15:.1f} °C）",
        yaxis_title="熱流量 [W]",
    )
    _save(fig, out / "fig01_energy_balance.png", height=450)


def fig_solar_flux(result, config: AppConfig, out: Path) -> None:
    days = result.days
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=days, y=result.solar_flux, line=dict(color="#ffd700", width=2), name="S")
    )
    fig.add_hline(
        y=config.thermal.solar_constant_w_m2,
        line_dash="dot",
        annotation_text=f"S0 = {config.thermal.solar_constant_w_m2} W/m²",
    )
    fig.update_layout(
        title="太陽フラックスの年変動（日心距離）",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis_title="太陽フラックス [W/m²]",
    )
    _save(fig, out / "fig02_solar_flux.png")


def fig_beta_angle(result, out: Path) -> None:
    days = result.days
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.beta_angle_deg,
            name="β角（太陽赤緯）",
            line=dict(color="#2ecc71", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.incidence_angle_deg,
            name="θ_max（日最大入射角）",
            line=dict(color="#a29bfe", width=2, dash="dash"),
        )
    )
    fig.add_hline(y=23.45, line_dash="dot", line_color="#999")
    fig.add_hline(y=-23.45, line_dash="dot", line_color="#999")
    fig.add_hline(y=0, line_color="#ccc")
    fig.update_layout(
        title="β角とパネル面への日最大入射角",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis_title="角度 [°]",
    )
    _save(fig, out / "fig03_beta_angle.png")


def fig_eclipse_duration(result, out: Path) -> None:
    days = result.days
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.eclipse_duration_min,
            fill="tozeroy",
            line=dict(color="#74b9ff", width=2),
            name="日食時間",
        )
    )
    fig.add_hline(y=72, line_dash="dash", line_color="#fd79a8", annotation_text="最大 72 min")
    fig.update_layout(
        title="GEO の日食時間（1日あたり）",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis_title="日食時間 [min]",
    )
    _save(fig, out / "fig04_eclipse_duration.png")


def fig_eclipse_cooling_transient(config: AppConfig, out: Path) -> None:
    """Temperature drop during a representative eclipse (DOY 80)."""
    th = config.thermal
    area = config.panel.area_m2
    area_total = 2 * area
    doy = 80.0
    s = sun_flux_w_m2(doy, th.solar_constant_w_m2)
    em = eclipse_duration_min(doy)
    t0 = equilibrium_temperature_k(
        s,
        alpha_s=th.alpha_s,
        epsilon_front=th.epsilon_front,
        epsilon_back=th.epsilon_back,
        eta_eol=th.eta_eol,
        area_front=area,
        area_back=area,
        t_earth=th.earth_ir_temperature_k,
        alpha_albedo=th.earth_albedo,
    )

    dt = config.simulation.dt_eclipse_seconds
    n = int(em * 60 / dt) + 1
    times_min = np.linspace(0, em, n)
    temps_c = []
    t = t0
    for _ in times_min:
        temps_c.append(t - 273.15)
        q_rad = STEFAN_BOLTZMANN * emissivity_area_sum(
            th.epsilon_front, th.epsilon_back, area, area
        ) * t**4
        t = max(t - q_rad / th.m_cp_j_k * dt, 0.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times_min,
            y=temps_c,
            line=dict(color="#48dbfb", width=2),
            name="パネル温度",
        )
    )
    fig.add_hline(
        y=t0 - 273.15,
        line_dash="dot",
        line_color="#ff9f43",
        annotation_text=f"日食前平衡 {t0 - 273.15:.1f} °C",
    )
    fig.update_layout(
        title=f"日食中の温度低下（DOY {int(doy)}、日食 {em:.0f} min）",
        xaxis_title="日食経過時間 [min]",
        yaxis_title="温度 [°C]",
    )
    _save(fig, out / "fig05_eclipse_cooling.png")


def fig_orbital_average_concept(config: AppConfig, out: Path) -> None:
    """Compare Ts, Te, Tavg for one eclipse-season day."""
    th = config.thermal
    area = config.panel.area_m2
    area_total = 2 * area
    doy = 80.0
    s = sun_flux_w_m2(doy, th.solar_constant_w_m2)
    em = eclipse_duration_min(doy)
    ef = em / (24.0 * 60.0)
    ts = equilibrium_temperature_k(
        s,
        alpha_s=th.alpha_s,
        epsilon_front=th.epsilon_front,
        epsilon_back=th.epsilon_back,
        eta_eol=th.eta_eol,
        area_front=area,
        area_back=area,
        t_earth=th.earth_ir_temperature_k,
        alpha_albedo=th.earth_albedo,
    )
    te = eclipse_minimum_temperature_k(
        ts,
        em,
        epsilon_front=th.epsilon_front,
        epsilon_back=th.epsilon_back,
        area_front=area,
        area_back=area,
        m_cp=th.m_cp_j_k,
        dt_s=config.simulation.dt_eclipse_seconds,
    )
    ta = orbital_average_temperature_k(ts, te, ef)

    labels = ["日射平衡 T_sl", "日食最低 T_ecl", "軌道平均 T_avg"]
    vals = [ts - 273.15, te - 273.15, ta - 273.15]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=vals,
            marker_color=["#ff9f43", "#48dbfb", "#ff6b9d"],
            text=[f"{v:.1f} °C" for v in vals],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=f"1日の代表温度（DOY {int(doy)}、日食率 {ef * 100:.1f}%）",
        yaxis_title="温度 [°C]",
    )
    _save(fig, out / "fig06_orbital_average.png", height=450)


def fig_annual_temperature(result, out: Path) -> None:
    days = result.days
    ecl = result.eclipse_fraction > 0
    fig = make_subplots(rows=1, cols=1)
    for i in range(len(days) - 1):
        if ecl[i] or ecl[i + 1]:
            fig.add_vrect(
                x0=float(days[i]),
                x1=float(days[i + 1]),
                fillcolor="rgba(26,39,68,0.15)",
                line_width=0,
            )
    fig.add_trace(
        go.Scatter(x=days, y=result.t_sunlit_c, name="日射平衡", line=dict(color="#ff9f43", width=2))
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.t_eclipse_min_c,
            name="日食最低",
            line=dict(color="#48dbfb", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=days,
            y=result.t_orbital_avg_c,
            name="軌道平均",
            line=dict(color="#ff6b9d", width=2, dash="dot"),
        )
    )
    fig.update_layout(
        title="年間温度トレンド（GEO太陽電池パネル）",
        xaxis=dict(tickvals=M_STARTS, ticktext=MONTHS, title="月"),
        yaxis=dict(title="温度 [°C]", range=[-200, 50]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    _save(fig, out / "fig07_annual_temperature.png", width=1000, height=520)


def fig_calculation_flowchart(out: Path) -> None:
    """Simple flow diagram as annotated scatter (text boxes via annotations)."""
    fig = go.Figure()
    steps = [
        (0, 2, "① 環境\nS, β, 日食時間"),
        (1, 2, "② 日射平衡\nT_sl"),
        (2, 2, "③ 日食冷却\nT_ecl"),
        (3, 2, "④ 軌道平均\nT_avg"),
        (4, 2, "⑤ 年間CSV・図"),
    ]
    xs = [s[0] for s in steps]
    ys = [s[1] for s in steps]
    texts = [s[2] for s in steps]
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            marker=dict(size=40, color="#dfe6e9"),
            text=texts,
            textposition="middle center",
            textfont=dict(size=11),
            hoverinfo="skip",
        )
    )
    for i in range(len(xs) - 1):
        fig.add_annotation(
            x=(xs[i] + xs[i + 1]) / 2,
            y=ys[i],
            text="→",
            showarrow=False,
            font=dict(size=20),
        )
    fig.update_xaxes(visible=False, range=[-0.5, 4.5])
    fig.update_yaxes(visible=False, range=[1, 3])
    fig.update_layout(title="温度計算の流れ（1ノードモデル）", height=280)
    _save(fig, out / "fig00_calculation_flow.png", width=1000, height=280)


def fig_seasonal_environment(config: AppConfig, out: Path) -> None:
    """Sun flux and beta vs day — seasonal drivers of temperature."""
    days = np.arange(1, 366)
    s0 = config.thermal.solar_constant_w_m2
    s = np.array([sun_flux_w_m2(float(d), s0) for d in days])
    beta = np.array([beta_angle_deg(float(d)) for d in days])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=days, y=s, name="太陽フラックス S", line=dict(color="#ffd700", width=2)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=days, y=beta, name="β角（太陽赤緯）", line=dict(color="#2ecc71", width=2)),
        secondary_y=True,
    )
    fig.update_xaxes(tickvals=M_STARTS, ticktext=MONTHS, title="月")
    fig.update_yaxes(title_text="太陽フラックス [W/m²]", secondary_y=False)
    fig.update_yaxes(title_text="β角 [°]", secondary_y=True)
    fig.update_layout(
        title="季節変化：日心距離による S と、公転傾斜きによる β角",
        legend=dict(orientation="h", y=1.12),
    )
    _save(fig, out / "fig08_seasonal_environment.png", width=1000, height=520)


def fig_beta_geometry_schematic(out: Path) -> None:
    """Schematic: Sun direction vs equatorial plane for GEO (beta angles)."""
    fig = go.Figure()
    # Equatorial plane (horizontal)
    fig.add_shape(
        type="line", x0=-1.2, x1=1.2, y0=0, y1=0, line=dict(color="#636e72", width=2)
    )
    fig.add_annotation(x=1.25, y=0, text="赤道面（GEO軌道面）", showarrow=False, xanchor="left")

    # Earth disk (schematic)
    theta = np.linspace(0, 2 * np.pi, 80)
    fig.add_trace(
        go.Scatter(
            x=0.15 * np.cos(theta),
            y=0.15 * np.sin(theta),
            fill="toself",
            fillcolor="rgba(9,132,227,0.3)",
            line=dict(color="#0984e3"),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_annotation(x=0, y=-0.28, text="地球", showarrow=False)

    # GEO spacecraft on orbit
    fig.add_trace(
        go.Scatter(
            x=[1.0],
            y=[0],
            mode="markers+text",
            marker=dict(size=14, color="#e17055", symbol="square"),
            text=["GEO衛星"],
            textposition="top center",
            showlegend=False,
        )
    )

    def _sun_ray(beta_deg: float, color: str, label: str) -> None:
        b = np.radians(beta_deg)
        dx, dy = 0.85 * np.cos(b), 0.85 * np.sin(b)
        fig.add_trace(
            go.Scatter(
                x=[1.0, 1.0 + dx],
                y=[0, dy],
                mode="lines",
                line=dict(color=color, width=2),
                name=label,
            )
        )

    _sun_ray(0, "#f39c12", "β = 0°（春分・秋分）")
    _sun_ray(23.45, "#e74c3c", "β = +23.45°（夏至）")
    _sun_ray(-23.45, "#3498db", "β = −23.45°（冬至）")

    fig.update_xaxes(visible=False, range=[-0.3, 2.0])
    fig.update_yaxes(visible=False, range=[-0.5, 0.9], scaleanchor="x", scaleratio=1)
    fig.update_layout(
        title="GEO における β角：太陽方向と赤道面のなす角",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        height=480,
    )
    _save(fig, out / "fig09_beta_geometry.png", width=900, height=480)


def fig_eclipse_and_beta(result, out: Path) -> None:
    """Eclipse duration vs beta — shows eclipses near equinox (|beta| small)."""
    days = result.days
    beta = result.beta_angle_deg
    ecl = result.eclipse_duration_min

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("β角の年変化", "日食時間（β ≈ 0° 付近の春・秋シーズンに発生）"),
        vertical_spacing=0.12,
    )
    fig.add_trace(
        go.Scatter(x=days, y=beta, line=dict(color="#2ecc71", width=2), name="β角"),
        row=1,
        col=1,
    )
    fig.add_hline(y=0, line_color="#aaa", row=1, col=1)
    fig.add_hline(y=23.45, line_dash="dot", line_color="#ddd", row=1, col=1)
    fig.add_hline(y=-23.45, line_dash="dot", line_color="#ddd", row=1, col=1)

    fig.add_trace(
        go.Scatter(
            x=days,
            y=ecl,
            fill="tozeroy",
            line=dict(color="#74b9ff", width=2),
            name="日食時間",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=72, line_dash="dash", line_color="#fd79a8", row=2, col=1)

    for i in range(len(days) - 1):
        if ecl[i] > 0 or ecl[i + 1] > 0:
            fig.add_vrect(
                x0=float(days[i]),
                x1=float(days[i + 1]),
                fillcolor="rgba(253,121,168,0.1)",
                line_width=0,
                row=1,
                col=1,
            )

    fig.update_xaxes(tickvals=M_STARTS, ticktext=MONTHS, title="月", row=2, col=1)
    fig.update_yaxes(title_text="β [°]", row=1, col=1)
    fig.update_yaxes(title_text="日食時間 [min]", row=2, col=1)
    fig.update_layout(title="β角と日食シーズンの対応（GEO）", height=620)
    _save(fig, out / "fig10_eclipse_and_beta.png", width=1000, height=620)


def fig_eclipse_vs_abs_beta(result, out: Path) -> None:
    """Scatter: eclipse duration vs |beta|."""
    days = result.days
    abs_beta = np.abs(result.beta_angle_deg)
    ecl = result.eclipse_duration_min
    mask = ecl > 0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=abs_beta[~mask],
            y=ecl[~mask],
            mode="markers",
            marker=dict(size=4, color="#ccc"),
            name="日食なし",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=abs_beta[mask],
            y=ecl[mask],
            mode="markers",
            marker=dict(size=8, color="#74b9ff"),
            name="日食あり",
        )
    )
    fig.add_hline(y=72, line_dash="dash", line_color="#fd79a8", annotation_text="最大 72 min")
    fig.update_layout(
        title="日食時間と |β| の関係（|β| が小さいほど日食シーズン）",
        xaxis_title="|β| [°]",
        yaxis_title="日食時間 [min]",
    )
    _save(fig, out / "fig11_eclipse_vs_abs_beta.png")


def fig_efficiency_sensitivity(config: AppConfig, out: Path) -> None:
    """Annual temperature profiles for eta_EOL = 10%, 20%, 28%."""
    etas = [0.10, 0.20, 0.28]
    labels = ["η=10%", "η=20%", "η=28%（デフォルト）"]
    colors = ["#3498db", "#9b59b6", "#e67e22"]

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(
            "日射平衡温度 T_sl（発電効率が高いほど吸収熱が減り低温）",
            "日食最低温度 T_ecl",
        ),
        vertical_spacing=0.1,
    )

    for eta, label, color in zip(etas, labels, colors):
        res = run_annual_model(config, eta_eol=eta)
        fig.add_trace(
            go.Scatter(
                x=res.days,
                y=res.t_sunlit_c,
                name=label,
                line=dict(color=color, width=2),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=res.days,
                y=res.t_eclipse_min_c,
                name=label,
                line=dict(color=color, width=1.8, dash="dash"),
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    fig.update_xaxes(tickvals=M_STARTS, ticktext=MONTHS, title="月", row=2, col=1)
    fig.update_yaxes(title_text="T_sl [°C]", row=1, col=1)
    fig.update_yaxes(title_text="T_ecl [°C]", range=[-200, 50], row=2, col=1)
    fig.update_layout(
        title="発電効率 η_EOL による温度プロファイルの違い",
        legend=dict(orientation="h", y=1.08),
        height=700,
    )
    _save(fig, out / "fig12_efficiency_sensitivity.png", width=1000, height=700)


def fig_efficiency_sunlit_bar(config: AppConfig, out: Path) -> None:
    """Bar chart: T_sl at summer/winter/equinox for different eta."""
    th = config.thermal
    area = config.panel.area_m2
    doys = {"夏至 (DOY 172)": 172, "春分 (DOY 81)": 81, "冬至 (DOY 355)": 355}
    etas = [0.10, 0.20, 0.28]

    fig = go.Figure()
    for eta in etas:
        vals = []
        names = []
        for name, doy in doys.items():
            s = sun_flux_w_m2(float(doy), th.solar_constant_w_m2)
            t = equilibrium_temperature_k(
                s,
                alpha_s=th.alpha_s,
                epsilon_front=th.epsilon_front,
                epsilon_back=th.epsilon_back,
                eta_eol=eta,
                area_front=area,
                area_back=area,
                t_earth=th.earth_ir_temperature_k,
                alpha_albedo=th.earth_albedo,
            )
            vals.append(t - 273.15)
            names.append(name)
        fig.add_trace(
            go.Bar(
                x=names,
                y=vals,
                name=f"η={int(eta * 100)}%",
            )
        )
    fig.update_layout(
        title="代表日の日射平衡温度と発電効率",
        yaxis_title="T_sl [°C]",
        barmode="group",
    )
    _save(fig, out / "fig13_efficiency_bar.png", height=450)


def fig_temperature_profile_derivation(out: Path) -> None:
    """Block diagram: from environment to annual profile."""
    fig = go.Figure()
    blocks = [
        (0, 3, "地球公転\n→ S(d)"),
        (1, 3, "軌道傾斜\n→ β(d)"),
        (2, 3, "春分・秋分\n→ 日食 t_ecl"),
        (0.5, 2, "Q_in(S,β,η)"),
        (1.5, 2, "T_sl 平衡"),
        (1, 1, "日食冷却\n→ T_ecl"),
        (1, 0, "T_avg\n年間プロファイル"),
    ]
    for x, y, text in blocks:
        fig.add_shape(
            type="rect",
            x0=x - 0.35,
            y0=y - 0.25,
            x1=x + 0.35,
            y1=y + 0.25,
            line=dict(color="#636e72"),
            fillcolor="#ecf0f1",
        )
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, font=dict(size=10))
    arrows = [
        (0, 2.75, 0.5, 2.35),
        (1, 2.75, 1.5, 2.35),
        (2, 2.75, 1.5, 2.35),
        (0.5, 1.75, 1.5, 2.25),
        (1.5, 1.75, 1, 1.25),
        (1, 0.25, 1, 0.75),
    ]
    for x0, y0, x1, y1 in arrows:
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", arrowhead=2
        )
    fig.update_xaxes(visible=False, range=[-0.5, 2.5])
    fig.update_yaxes(visible=False, range=[-0.5, 3.5])
    fig.update_layout(title="温度プロファイル導出の概念図", height=500)
    _save(fig, out / "fig14_profile_derivation.png", width=900, height=500)


def generate_all(config_path: Path, out_dir: Path) -> None:
    config = load_config(config_path)
    result = run_annual_model(config)
    fig_calculation_flowchart(out_dir)
    fig_temperature_profile_derivation(out_dir)
    fig_energy_balance(config, out_dir)
    fig_solar_flux(result, config, out_dir)
    fig_beta_angle(result, out_dir)
    fig_eclipse_duration(result, out_dir)
    fig_eclipse_cooling_transient(config, out_dir)
    fig_orbital_average_concept(config, out_dir)
    fig_annual_temperature(result, out_dir)
    fig_seasonal_environment(config, out_dir)
    fig_beta_geometry_schematic(out_dir)
    fig_eclipse_and_beta(result, out_dir)
    fig_eclipse_vs_abs_beta(result, out_dir)
    fig_efficiency_sensitivity(config, out_dir)
    fig_efficiency_sunlit_bar(config, out_dir)
