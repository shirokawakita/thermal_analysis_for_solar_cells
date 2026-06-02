/** Supplemental animations for docs/README.html (season, tilt, orbit η). */

const ORBIT_S = 86164;
const SIGMA = 5.670374419e-8;

function sunFlux(doy, s0 = 1361) {
  const dist = 1 - 0.01671 * Math.cos((2 * Math.PI * (doy - 3)) / 365.25);
  return s0 / dist ** 2;
}

function equilibriumTempC(s, eta, alphaS = 0.9, epsF = 0.85, epsB = 0.82, tEarth = 255) {
  const area = 1;
  const epsA = epsF * area + epsB * area;
  const qSolar = alphaS * (1 - eta) * s * area;
  const qIr = epsB * SIGMA * tEarth ** 4 * 0.198 * area;
  const qAlb = alphaS * s * 0.3 * 0.198 * area;
  const tK = ((qSolar + qIr + qAlb) / (SIGMA * epsA)) ** 0.25;
  return tK - 273.15;
}

function initSeasonAnim() {
  const svg = document.getElementById("anim-season");
  if (!svg) return;
  const seasons = [
    { id: "spring", label: "春分 β=0°", beta: 0, eclipse: true, sun: [1, 0] },
    { id: "summer", label: "夏至 β=+23.45°", beta: 23.45, eclipse: false, sun: [0, 1] },
    { id: "autumn", label: "秋分 β=0°", beta: 0, eclipse: true, sun: [-1, 0] },
    { id: "winter", label: "冬至 β=−23.45°", beta: -23.45, eclipse: false, sun: [0, -1] },
  ];
  let current = seasons[0];
  const cx = 300;
  const cy = 220;
  const scale = 90;

  function draw() {
    const tilt = (23.45 * Math.PI) / 180;
    const [sx, sy] = current.sun;
    const betaRad = (current.beta * Math.PI) / 180;
    let html = `
      <circle cx="${cx}" cy="${cy}" r="${scale * 0.22}" fill="#0984e3"/>
      <ellipse cx="${cx}" cy="${cy}" rx="${scale * 1.1}" ry="${scale * 1.1}" fill="none" stroke="#f39c12" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.7"/>
    `;
    const eqPts = [];
    for (let a = 0; a <= 360; a += 8) {
      const rad = (a * Math.PI) / 180;
      eqPts.push(`${cx + scale * 0.55 * Math.cos(rad)},${cy + scale * 0.55 * Math.sin(rad) * Math.cos(tilt)}`);
    }
    html += `<polyline points="${eqPts.join(" ")}" fill="none" stroke="#1abc9c" stroke-width="2"/>`;
    const sunX = cx + sx * scale * 1.35;
    const sunY = cy - sy * scale * 1.35;
    html += `<circle cx="${sunX}" cy="${sunY}" r="18" fill="#f39c12"/>`;
    html += `<text x="20" y="28" fill="#fff" font-size="13">${current.label}</text>`;
    html += `<text x="20" y="48" fill="${current.eclipse ? "#e74c3c" : "#2ecc71"}" font-size="12">日食: ${current.eclipse ? "あり" : "なし"}</text>`;
    svg.innerHTML = html;
  }

  document.querySelectorAll("[data-season]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-season]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      current = seasons.find((s) => s.id === btn.dataset.season);
      draw();
    });
  });
  draw();
}

function initTiltToggle() {
  const canvas = document.getElementById("anim-tilt");
  const btnReal = document.getElementById("tilt-real");
  const btnZero = document.getElementById("tilt-zero");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  let showZero = false;

  function draw() {
    ctx.fillStyle = "#0b1020";
    ctx.fillRect(0, 0, W, H);
    const pad = { l: 44, r: 12, t: 28, b: 32 };
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;
    const days = Array.from({ length: 365 }, (_, i) => i + 1);
    ctx.fillStyle = "rgba(231,76,60,0.1)";
    const y0 = pad.t + ph * (1 - (-8.7 + 30) / 60);
    const y1 = pad.t + ph * (1 - (8.7 + 30) / 60);
    ctx.fillRect(pad.l, y1, pw, y0 - y1);
    ctx.strokeStyle = "#e74c3c";
    ctx.lineWidth = 2;
    ctx.beginPath();
    days.forEach((d, i) => {
      const b = 23.45 * Math.sin((2 * Math.PI * (d - 80)) / 365.25);
      const x = pad.l + (i / 364) * pw;
      const y = pad.t + ph * (1 - (b + 30) / 60);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    if (showZero) {
      ctx.strokeStyle = "#3498db";
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(pad.l, pad.t + ph * (1 - 30 / 60));
      ctx.lineTo(pad.l + pw, pad.t + ph * (1 - 30 / 60));
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.fillStyle = "#fff";
    ctx.font = "12px sans-serif";
    ctx.fillText(showZero ? "地軸傾き 0°: β=0° 通年" : "地軸傾き 23.45°（実際）", pad.l, 18);
  }

  btnReal?.addEventListener("click", () => {
    showZero = false;
    btnReal.classList.add("active");
    btnZero?.classList.remove("active");
    draw();
  });
  btnZero?.addEventListener("click", () => {
    showZero = true;
    btnZero.classList.add("active");
    btnReal?.classList.remove("active");
    draw();
  });
  draw();
}

function initOrbitTemp() {
  const canvas = document.getElementById("anim-orbit-temp");
  const playBtn = document.getElementById("orbit-play");
  const readout = document.getElementById("orbit-readout");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  let eta = 0.28;
  let animId = null;

  function simulate() {
    const s = sunFlux(80);
    const tEq = equilibriumTempC(s, eta) + 273.15;
    const mCp = 800;
    const epsA = 0.85 + 0.82;
    const eclStart = 0.45 * ORBIT_S;
    const eclEnd = eclStart + 72 * 60;
    const dt = 30;
    const pts = [];
    let t = tEq;
    for (let sec = 0; sec < ORBIT_S; sec += dt) {
      if (sec < eclStart || sec > eclEnd) {
        t = tEq;
      } else {
        t = Math.max(t - (SIGMA * epsA * t ** 4 / mCp) * dt, 50);
      }
      pts.push({ min: sec / 60, temp: t - 273.15 });
    }
    return { pts, eclStart: eclStart / 60, eclEnd: eclEnd / 60 };
  }

  function draw(upTo = 1) {
    const { pts, eclStart, eclEnd } = simulate();
    ctx.fillStyle = "#0b1020";
    ctx.fillRect(0, 0, W, H);
    const pad = { l: 48, r: 16, t: 28, b: 36 };
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;
    const tMin = Math.min(...pts.map((p) => p.temp));
    const tMax = Math.max(...pts.map((p) => p.temp));
    const n = Math.floor(pts.length * upTo);
    const colors = { 0.1: "#3498db", 0.2: "#9b59b6", 0.28: "#e67e22" };
    ctx.fillStyle = "rgba(50,50,50,0.2)";
    ctx.fillRect(pad.l + (eclStart / 1440) * pw, pad.t, ((eclEnd - eclStart) / 1440) * pw, ph);
    ctx.strokeStyle = colors[eta] || "#e67e22";
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = pad.l + (pts[i].min / 1440) * pw;
      const y = pad.t + ph * (1 - (pts[i].temp - tMin) / (tMax - tMin + 1));
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = "12px sans-serif";
    ctx.fillText(`η = ${(eta * 100).toFixed(0)}%`, pad.l, 18);
    if (n > 0) readout.textContent = `T = ${pts[n - 1].temp.toFixed(1)} °C`;
  }

  document.querySelectorAll("[data-eta]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-eta]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      eta = Number(btn.dataset.eta);
      cancelAnimationFrame(animId);
      draw(1);
    });
  });

  playBtn?.addEventListener("click", () => {
    cancelAnimationFrame(animId);
    const start = performance.now();
    function loop(now) {
      const p = Math.min(1, (now - start) / 6000);
      draw(p);
      if (p < 1) animId = requestAnimationFrame(loop);
    }
    animId = requestAnimationFrame(loop);
  });

  draw(1);
}

document.addEventListener("DOMContentLoaded", () => {
  initSeasonAnim();
  initTiltToggle();
  initOrbitTemp();
});
