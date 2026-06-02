/** β角・南北面パネル・日食 — side view + annual chart (beta_angle_solar_panels.html) */

const TILT_BETA = 23.45;
const DEG_BETA = Math.PI / 180;
const ECX_BETA = 180;
const CY_BETA = 210;
const OR_BETA = 130;
const BETA_ECLIPSE_THRESH = 8.7;

const MONTHS_BETA = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_STARTS_BETA = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

function doyToMonthLabel(d) {
  for (let i = MONTH_STARTS_BETA.length - 1; i >= 0; i--) {
    if (d > MONTH_STARTS_BETA[i]) return `${MONTHS_BETA[i]} ${d - MONTH_STARTS_BETA[i]}`;
  }
  return `Jan ${d}`;
}

function betaFromDoy(doy) {
  return TILT_BETA * Math.sin((2 * Math.PI * (doy - 80)) / 365.25);
}

function initBetaAngleSolarPanels() {
  const root = document.getElementById("beta-angle-viz");
  if (!root) return;

  const slider = document.getElementById("beta-doy-slider");
  const readout = document.getElementById("beta-doy-readout");
  const playBtn = document.getElementById("beta-doy-play");
  if (!slider) return;

  // Pre-draw annual curves
  (function drawCurves() {
    let db = "";
    let dc = "";
    for (let i = 1; i <= 365; i++) {
      const x = 70 + ((i - 1) / 364) * 570;
      const b = betaFromDoy(i);
      const cb = Math.cos(b * DEG_BETA);
      const yb = 491 - (b / TILT_BETA) * 59;
      const ycFixed = 491 - ((cb - 1) / (Math.cos(TILT_BETA * DEG_BETA) - 1)) * 59;
      db += `${i === 1 ? "M" : "L"}${x.toFixed(1)} ${yb.toFixed(1)}`;
      dc += `${i === 1 ? "M" : "L"}${x.toFixed(1)} ${ycFixed.toFixed(1)}`;
    }
    document.getElementById("curveBeta")?.setAttribute("d", db);
    document.getElementById("curveCos")?.setAttribute("d", dc);
  })();

  function update(doy) {
    const b = betaFromDoy(doy);
    const bR = b * DEG_BETA;
    const absB = Math.abs(b);
    const cosB = Math.cos(bR);

    // Equatorial plane
    document.getElementById("eqPlane")?.setAttribute("transform", `translate(${ECX_BETA},${CY_BETA}) rotate(${-b})`);

    const el = document.getElementById("eqLabel");
    if (el) {
      const elDist = 170;
      const elAng = -bR;
      el.setAttribute("x", String(Math.min(ECX_BETA + elDist * Math.cos(elAng), 410)));
      el.setAttribute("y", String(CY_BETA + elDist * Math.sin(elAng) + (b >= 0 ? -6 : 14)));
      el.textContent = "赤道面（GEO軌道面）";
    }

    // Earth axis
    const axL = 32;
    const axAng = (-90 - b) * DEG_BETA;
    const ax = document.getElementById("axisLine");
    if (ax) {
      ax.setAttribute("x1", String(ECX_BETA + axL * Math.cos(axAng)));
      ax.setAttribute("y1", String(CY_BETA + axL * Math.sin(axAng)));
      ax.setAttribute("x2", String(ECX_BETA - axL * Math.cos(axAng)));
      ax.setAttribute("y2", String(CY_BETA - axL * Math.sin(axAng)));
    }

    document.getElementById("orbitE")?.setAttribute("transform", `rotate(${-b},${ECX_BETA},${CY_BETA})`);

    const satX = ECX_BETA + OR_BETA * Math.cos(bR);
    const satY = CY_BETA - OR_BETA * Math.sin(bR);

    document.getElementById("satGroup")?.setAttribute("transform", `translate(${satX},${satY}) rotate(${-b})`);

    const sl = document.getElementById("satLbl");
    if (sl) {
      sl.setAttribute("x", String(satX + 14));
      sl.setAttribute("y", String(satY - 52));
      sl.textContent = "GEO衛星";
    }

    const panelLen = 48;
    const nAng = (-90 - b) * DEG_BETA;
    const nX = satX + panelLen * Math.cos(nAng);
    const nY = satY + panelLen * Math.sin(nAng);
    const sX = satX - panelLen * Math.cos(nAng);
    const sY = satY - panelLen * Math.sin(nAng);

    const nl = document.getElementById("northLbl");
    if (nl) {
      nl.setAttribute("x", String(nX + (b >= 0 ? -12 : 12)));
      nl.setAttribute("y", String(nY + (b >= 0 ? -2 : 4)));
      nl.textContent = "N";
    }
    const sll = document.getElementById("southLbl");
    if (sll) {
      sll.setAttribute("x", String(sX + (b >= 0 ? 12 : -12)));
      sll.setAttribute("y", String(sY + (b >= 0 ? 6 : -2)));
      sll.textContent = "S";
    }

    const normLen = 55;
    const normDx = -Math.cos(bR) * normLen;
    const normDy = Math.sin(bR) * normLen;
    const pn = document.getElementById("panelNormal");
    if (pn) {
      pn.setAttribute("x1", String(satX));
      pn.setAttribute("y1", String(satY));
      pn.setAttribute("x2", String(satX + normDx));
      pn.setAttribute("y2", String(satY + normDy));
    }
    const nll = document.getElementById("normalLbl");
    if (nll) {
      nll.setAttribute("x", String(satX + normDx * 0.5));
      nll.setAttribute("y", String(satY + normDy * 0.5 + (b >= 0 ? 14 : -8)));
      nll.textContent = "パネル法線";
    }

    const rayStartX = satX - 90;
    const rayOffsets = [-20, -7, 7, 20];
    ["ray1", "ray2", "ray3", "ray4"].forEach((id, i) => {
      const ryy = CY_BETA + rayOffsets[i];
      const r = document.getElementById(id);
      if (r) {
        r.setAttribute("x1", String(rayStartX));
        r.setAttribute("y1", String(ryy));
        r.setAttribute("x2", String(satX - 10));
        r.setAttribute("y2", String(ryy));
      }
    });

    const arcR = 30;
    const incArc = document.getElementById("incArc");
    const incLbl = document.getElementById("incLbl");
    if (absB > 1 && incArc && incLbl) {
      const sw = b >= 0 ? 1 : 0;
      incArc.setAttribute(
        "d",
        `M${satX - arcR} ${CY_BETA} A${arcR} ${arcR} 0 0 ${sw} ${satX + (normDx / normLen) * arcR} ${satY + (normDy / normLen) * arcR}`
      );
      incLbl.setAttribute("x", String(satX - arcR - 16));
      incLbl.setAttribute("y", String((CY_BETA + satY) / 2 + 4));
      incLbl.textContent = `θ=${absB.toFixed(1)}°`;
    } else {
      incArc?.setAttribute("d", "");
      if (incLbl) incLbl.textContent = "";
    }

    const bArcR = 48;
    const betaArc = document.getElementById("betaArc");
    const betaLbl = document.getElementById("betaLbl");
    if (absB > 0.5 && betaArc && betaLbl) {
      const baeX = ECX_BETA + bArcR * Math.cos(-bR);
      const baeY = CY_BETA + bArcR * Math.sin(-bR);
      const sw2 = b >= 0 ? 0 : 1;
      betaArc.setAttribute("d", `M${ECX_BETA + bArcR} ${CY_BETA} A${bArcR} ${bArcR} 0 0 ${sw2} ${baeX} ${baeY}`);
      const mA = -bR / 2;
      betaLbl.setAttribute("x", String(ECX_BETA + (bArcR + 16) * Math.cos(mA)));
      betaLbl.setAttribute("y", String(CY_BETA + (bArcR + 16) * Math.sin(mA) + 4));
      betaLbl.textContent = `β=${b.toFixed(1)}°`;
    } else if (betaArc && betaLbl) {
      betaArc.setAttribute("d", "");
      betaLbl.setAttribute("x", String(ECX_BETA + 55));
      betaLbl.setAttribute("y", String(CY_BETA - 6));
      betaLbl.textContent = "β≈0°";
    }

    const dl = document.getElementById("dimL");
    const dt = document.getElementById("dimT");
    if (absB > 3 && dl && dt) {
      dl.setAttribute("x1", String(satX + 12));
      dl.setAttribute("y1", String(CY_BETA));
      dl.setAttribute("x2", String(satX + 12));
      dl.setAttribute("y2", String(satY));
      dl.setAttribute("opacity", "0.5");
      dt.setAttribute("x", String(satX + 18));
      dt.setAttribute("y", String((CY_BETA + satY) / 2 + 4));
      dt.setAttribute("opacity", "0.6");
      dt.textContent = `${Math.round(42164 * Math.sin(Math.abs(bR))).toLocaleString()} km`;
    } else {
      dl?.setAttribute("opacity", "0");
      dt?.setAttribute("opacity", "0");
    }

    const inEcl = absB < BETA_ECLIPSE_THRESH;
    const pwrTitle = document.getElementById("pwrTitle");
    const pwrDetail = document.getElementById("pwrDetail");
    if (pwrTitle) {
      pwrTitle.textContent = `cos(β) = ${cosB.toFixed(4)}  →  出力係数 ${(cosB * 100).toFixed(1)}%`;
    }
    if (pwrDetail) {
      pwrDetail.textContent = inEcl
        ? `入射角 ${absB.toFixed(1)}°（日食シーズン — パネルは冷却も発生）`
        : `入射角 ${absB.toFixed(1)}° — 垂直入射比 ${((1 - cosB) * 100).toFixed(1)}% 損失`;
    }

    const eb = document.getElementById("eclBox");
    const es = document.getElementById("eclStatus");
    if (eb && es) {
      if (inEcl) {
        eb.setAttribute("fill", "var(--color-background-danger)");
        eb.setAttribute("stroke", "var(--color-border-danger)");
        es.setAttribute("fill", "var(--color-text-danger)");
        es.textContent = `|β|=${absB.toFixed(1)}° < ${BETA_ECLIPSE_THRESH}° → 日食あり（最大約72分/日）`;
      } else {
        eb.setAttribute("fill", "var(--color-background-success)");
        eb.setAttribute("stroke", "var(--color-border-success)");
        es.setAttribute("fill", "var(--color-text-success)");
        es.textContent = `|β|=${absB.toFixed(1)}° > ${BETA_ECLIPSE_THRESH}° → 日食なし（全日照）`;
      }
    }

    const cx = 70 + ((doy - 1) / 364) * 570;
    const cyB = 491 - (b / TILT_BETA) * 59;
    const cyC = 491 - ((cosB - 1) / (Math.cos(TILT_BETA * DEG_BETA) - 1)) * 59;
    document.getElementById("doyLine")?.setAttribute("x1", String(cx));
    document.getElementById("doyLine")?.setAttribute("x2", String(cx));
    document.getElementById("doyDotB")?.setAttribute("cx", String(cx));
    document.getElementById("doyDotB")?.setAttribute("cy", String(cyB));
    document.getElementById("doyDotC")?.setAttribute("cx", String(cx));
    document.getElementById("doyDotC")?.setAttribute("cy", String(cyC));

    const slbl = document.getElementById("seasonLbl");
    if (slbl) {
      slbl.setAttribute("x", String(cx));
      slbl.setAttribute("y", "428");
      if (absB < 2) slbl.textContent = "二分（Equinox）";
      else if (absB > 22) slbl.textContent = "至点（Solstice）";
      else slbl.textContent = "";
    }

    if (readout) {
      readout.textContent = `DOY ${doy} (${doyToMonthLabel(doy)})  β=${b.toFixed(1)}°  cos(β)=${cosB.toFixed(3)}`;
    }
  }

  let playing = false;
  let animId = null;

  function togglePlay() {
    playing = !playing;
    if (playBtn) playBtn.textContent = playing ? "⏸ 停止" : "▶ 1年再生";
    if (playing) animate();
    else cancelAnimationFrame(animId);
  }

  function animate() {
    if (!playing) return;
    let v = Number(slider.value) + 1;
    if (v > 365) v = 1;
    slider.value = String(v);
    update(v);
    animId = requestAnimationFrame(animate);
  }

  slider.addEventListener("input", () => update(Number(slider.value)));
  playBtn?.addEventListener("click", togglePlay);

  update(Number(slider.value));
}

document.addEventListener("DOMContentLoaded", initBetaAngleSolarPanels);
