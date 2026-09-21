// Xem trước nhanh hình LaTeX: dựng SVG ngay trong trình duyệt (không cần TeX), mô phỏng bố cục PGFPlots
// gồm lưới, trục, miền tô, hai đồ thị, đường cận, giao điểm và chú giải. Cùng bảng màu với mã LaTeX.
const NS = 'http://www.w3.org/2000/svg';
const C = { navy: '#1C2E58', fill: '#A9B8CE', gray: '#D7D7D7', f: '#1E4FD6', g: '#EB5A2A' };
const SERIF = '"Source Serif 4", "Times New Roman", Times, serif';

const el = (tag, attrs = {}, text) => {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  if (text != null) e.textContent = text;
  return e;
};

function niceStep(span, target = 8) {
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  for (const m of [1, 2, 2.5, 5, 10]) if (raw <= m * mag + 1e-12) return m * mag;
  return 10 * mag;
}

const fmt = (v, d = 3) => {
  const s = (Math.abs(v) < 10 ** -d ? 0 : v).toFixed(d).replace(/\.?0+$/, '');
  return (s === '-0' || s === '' ? '0' : s).replace('-', '\u2212');
};

export function figureSVG(graph, res) {
  const W = 640, H = 470, L = 52, R = 22, T = 24, B = 42;
  const pw = W - L - R, ph = H - T - B;
  const sx = niceStep(graph.view.xmax - graph.view.xmin);
  const sy = niceStep(graph.view.ymax - graph.view.ymin);
  const x0 = Math.floor(graph.view.xmin / sx + 1e-9) * sx, x1 = Math.ceil(graph.view.xmax / sx - 1e-9) * sx;
  const y0 = Math.floor(graph.view.ymin / sy + 1e-9) * sy, y1 = Math.ceil(graph.view.ymax / sy - 1e-9) * sy;
  const X = (v) => L + ((v - x0) / (x1 - x0)) * pw;
  const Y = (v) => T + ((y1 - v) / (y1 - y0)) * ph;
  const yr = y1 - y0;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Xem trước hình LaTeX', class: 'figure-svg' });
  svg.append(el('rect', { width: W, height: H, fill: '#fff' }));
  const clipId = `clip-${Math.random().toString(36).slice(2, 8)}`;
  const defs = el('defs');
  defs.append(el('clipPath', { id: clipId }, undefined));
  defs.firstChild.append(el('rect', { x: L, y: T, width: pw, height: ph }));
  svg.append(defs);

  // lưới
  const grid = el('g', { stroke: C.gray, 'stroke-width': 0.7 });
  for (let v = Math.ceil(x0 / sx) * sx; v <= x1 + 1e-9; v += sx) grid.append(el('line', { x1: X(v), x2: X(v), y1: T, y2: T + ph }));
  for (let v = Math.ceil(y0 / sy) * sy; v <= y1 + 1e-9; v += sy) grid.append(el('line', { x1: L, x2: L + pw, y1: Y(v), y2: Y(v) }));
  svg.append(grid, el('rect', { x: L, y: T, width: pw, height: ph, fill: 'none', stroke: C.gray, 'stroke-width': 0.7 }));

  // vùng tô, đồ thị, đường cận (cắt theo khung)
  const clipped = el('g', { 'clip-path': `url(#${clipId})` });
  graph.regions.forEach((r) => {
    clipped.append(el('path', { d: `${r.x.map((v, i) => `${i ? 'L' : 'M'}${X(v).toFixed(1)} ${Y(r.y[i]).toFixed(1)}`).join('')}Z`, fill: C.fill, 'fill-opacity': 0.6 }));
  });
  const curve = (ys, color) => {
    let d = '';
    let pen = false;
    graph.x.forEach((v, i) => {
      const y = ys[i];
      if (y == null || v < x0 - sx || v > x1 + sx || y < y0 - yr || y > y1 + yr) { pen = false; return; }
      d += `${pen ? 'L' : 'M'}${X(v).toFixed(1)} ${Y(y).toFixed(1)}`;
      pen = true;
    });
    clipped.append(el('path', { d, fill: 'none', stroke: color, 'stroke-width': 2.4, 'stroke-linejoin': 'round' }));
  };
  curve(graph.f, C.f);
  curve(graph.g, C.g);
  svg.append(clipped);

  // trục (giao tại 0, hoặc sát mép nếu 0 nằm ngoài khung)
  const ax = Math.min(Math.max(0, x0), x1), ay = Math.min(Math.max(0, y0), y1);
  svg.append(el('line', { x1: L, x2: L + pw, y1: Y(ay), y2: Y(ay), stroke: C.navy, 'stroke-width': 1.6 }));
  svg.append(el('line', { x1: X(ax), x2: X(ax), y1: T + ph, y2: T, stroke: C.navy, 'stroke-width': 1.6 }));
  svg.append(el('path', { d: `M${L + pw} ${Y(ay)} l-8 -3.5 v7 z`, fill: C.navy }));
  svg.append(el('path', { d: `M${X(ax)} ${T} l-3.5 8 h7 z`, fill: C.navy }));
  svg.append(el('text', { x: L + pw + 4, y: Y(ay) + 5, 'font-family': SERIF, 'font-style': 'italic', 'font-size': 17, fill: C.navy }, 'x'));
  svg.append(el('text', { x: X(ax) + 8, y: T - 6, 'font-family': SERIF, 'font-style': 'italic', 'font-size': 17, fill: C.navy }, 'y'));

  // nhãn số trên trục
  const tick = { 'font-family': SERIF, 'font-size': 13, fill: C.navy };
  for (let v = Math.ceil(x0 / sx) * sx; v <= x1 + 1e-9; v += sx) {
    if (Math.abs(v) < 1e-9) continue;
    svg.append(el('text', { ...tick, x: X(v), y: Y(ay) + 17, 'text-anchor': 'middle' }, fmt(v)));
  }
  for (let v = Math.ceil(y0 / sy) * sy; v <= y1 + 1e-9; v += sy) {
    if (Math.abs(v) < 1e-9) continue;
    svg.append(el('text', { ...tick, x: X(ax) - 7, y: Y(v) + 4.5, 'text-anchor': 'end' }, fmt(v)));
  }

  // đường x = a, x = b
  graph.verticals.forEach((v) => {
    svg.append(el('line', { x1: X(v.x), x2: X(v.x), y1: Y(v.y0), y2: Y(v.y1), stroke: C.navy, 'stroke-width': 1.5, 'stroke-dasharray': '5 4' }));
    if (res.mode === 'manual') {
      svg.append(el('text', { x: X(v.x) + (v.label === 'a' ? -5 : 5), y: Y(0) - 6, 'text-anchor': v.label === 'a' ? 'end' : 'start', 'font-family': SERIF, 'font-style': 'italic', 'font-size': 14, fill: C.navy }, v.label));
    }
  });

  // giao điểm: chọn vị trí nhãn xa đường cong/trục nhất
  const obst = [];
  [graph.f, graph.g].forEach((ys) => graph.x.forEach((v, i) => {
    if (ys[i] != null && v >= x0 && v <= x1 && ys[i] >= y0 && ys[i] <= y1) obst.push([X(v), Y(ys[i])]);
  }));
  for (let t = L; t <= L + pw; t += 4) obst.push([t, Y(ay)]);
  for (let t = T; t <= T + ph; t += 4) obst.push([X(ax), t]);
  const placed = [];
  graph.points.forEach((p) => {
    const label = `${p.label}(${fmt(p.x)}, ${fmt(p.y)})`;
    const bw = label.length * 6.6 + 8, bh = 18;
    const cx = X(p.x), cy = Y(p.y);
    let best = null;
    for (const r of [14, 30, 48]) {
      for (let k = 0; k < 12; k += 1) {
        const a = (k * Math.PI) / 6 + Math.PI / 12;
        const rx = cx + r * Math.cos(a), ry = cy - r * Math.sin(a);
        const rect = [rx - bw / 2, ry - bh / 2, rx + bw / 2, ry + bh / 2];
        if (rect[0] < L + 2 || rect[2] > L + pw - 2 || rect[1] < T + 2 || rect[3] > T + ph - 2) continue;
        let clear = 999;
        for (const [ox, oy] of obst) {
          const d = Math.hypot(Math.max(rect[0] - ox, 0, ox - rect[2]), Math.max(rect[1] - oy, 0, oy - rect[3]));
          if (d < clear) clear = d;
          if (clear < 1) break;
        }
        if (placed.some((q) => rect[0] < q[2] + 3 && rect[2] > q[0] - 3 && rect[1] < q[3] + 3 && rect[3] > q[1] - 3)) clear = -1;
        const score = clear - 0.1 * r;
        if (!best || score > best.score) best = { score, rect, rx, ry };
      }
    }
    if (!best) best = { rect: [cx + 8, cy - 26, cx + 8 + bw, cy - 8], rx: cx + 8 + bw / 2, ry: cy - 17 };
    placed.push(best.rect);
    svg.append(el('line', { x1: cx, y1: cy, x2: best.rx, y2: best.ry, stroke: C.navy, 'stroke-width': 0.8 }));
    svg.append(el('rect', { x: best.rect[0], y: best.rect[1], width: bw, height: bh, rx: 3, fill: '#fff', 'fill-opacity': 0.95, stroke: '#B9C6E4', 'stroke-width': 0.6 }));
    svg.append(el('text', { x: best.rect[0] + 4, y: best.rect[1] + 13, 'font-family': SERIF, 'font-size': 13, fill: C.navy }, label));
    svg.append(el('circle', { cx, cy, r: 3.6, fill: C.navy }));
  });

  // chú giải
  const gx = L + pw - 118, gy = T + 10;
  svg.append(el('rect', { x: gx, y: gy, width: 108, height: 44, rx: 4, fill: '#fff', 'fill-opacity': 0.9 }));
  [['y = f(x)', C.f], [res.is_ox ? 'y = 0' : 'y = g(x)', C.g]].forEach(([t, col], i) => {
    svg.append(el('line', { x1: gx + 8, x2: gx + 32, y1: gy + 13 + i * 19, y2: gy + 13 + i * 19, stroke: col, 'stroke-width': 3 }));
    svg.append(el('text', { x: gx + 40, y: gy + 18 + i * 19, 'font-family': SERIF, 'font-size': 14, fill: C.navy }, t));
  });
  return svg;
}
