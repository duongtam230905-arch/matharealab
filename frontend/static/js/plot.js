// Đồ thị tương tác bằng Plotly: hai hàm số, miền diện tích, đường cận, giao điểm.
//  - Tự lấy mẫu lại theo khung nhìn (zoom/kéo) nên đường cong không bao giờ bị cụt.
//  - Nhãn giao điểm có nền trắng + đường chỉ, tự chọn hướng để không bị đường cong cắt qua.
//  - Hiệu ứng vào: đường cong vẽ dần, vùng diện tích tô dần, rồi hiện giao điểm.
import { post } from './api.js';
import { reduced } from './motion.js';

export const COLORS = { f: '#1E4FD6', g: '#EB5A2A', ink: '#1C2E58', area: [124, 92, 219], areaAlpha: 0.22, grid: '#E3E8F4' };
const FONT = 'Be Vietnam Pro, system-ui, sans-serif';
const PAD = { l: 44, r: 20, t: 38, b: 38 };
const rgba = (a) => `rgba(${COLORS.area.join(',')},${a})`;

export class Plot {
  /** @param getRequest hàm trả về {f1, f2} của lần tính gần nhất (dùng để lấy mẫu lại) */
  constructor(el, getRequest) {
    this.el = el;
    this.getRequest = getRequest;
    this.view = null;
    this.idx = { f: [], g: [], area: [], points: [], verticals: [] };
    this.points = [];
    this.verticals = [];
    this.opts = { coords: true };
    this.cur = null;     // {x, f, g}: dữ liệu đường cong đang vẽ
    this.cover = null;   // vùng đã lấy mẫu {x0, x1, y0, y1}
    this.bound = false;
    this.timer = null;
    this.seq = 0;
    this.animToken = 0;
    this.animating = false;
  }

  get ready() { return typeof window.Plotly !== 'undefined'; }

  /** Hệ trục trống (trước khi có kết quả). */
  drawEmpty() {
    if (!this.ready) return;
    this.view = { xmin: -5, xmax: 5, ymin: -3.5, ymax: 3.5 };
    this.idx = { f: [], g: [], area: [], points: [], verticals: [] };
    this.points = [];
    this.cur = null;
    window.Plotly.react(this.el, [], this._layout(false, true), this._config());
  }

  draw(graph, opts, animate = false) {
    if (!this.ready) return Promise.resolve();
    const anim = animate && !reduced();
    this.animToken += 1;
    this.animating = false;
    this.view = graph.view;
    this.points = graph.points;
    this.verticals = graph.verticals;
    this.opts = { ...opts };
    this.cur = { x: graph.x, f: graph.f, g: graph.g };
    const w = graph.view.xmax - graph.view.xmin;
    this.cover = { x0: graph.view.xmin - w, x1: graph.view.xmax + w, y0: graph.view.ymin, y1: graph.view.ymax };

    const blank = (arr) => arr.map(() => null);
    const traces = [];
    const idx = { f: [], g: [], area: [], points: [], verticals: [] };

    graph.regions.forEach((r, i) => {
      idx.area.push(traces.length);
      traces.push({
        x: r.x, y: r.y, type: 'scatter', mode: 'lines', fill: 'toself', fillcolor: rgba(anim ? 0 : COLORS.areaAlpha),
        line: { width: 0 }, hoverinfo: 'skip', name: 'Vùng diện tích', legendgroup: 'area', showlegend: i === 0,
      });
    });
    idx.f.push(traces.length);
    traces.push({
      x: graph.x, y: anim ? blank(graph.f) : graph.f, type: 'scatter', mode: 'lines', connectgaps: false,
      line: { color: COLORS.f, width: 3.2 }, name: 'y = f(x)',
      hovertemplate: 'x = %{x:.3f}<br>y = %{y:.3f}<extra>f(x)</extra>',
    });
    idx.g.push(traces.length);
    traces.push({
      x: graph.x, y: anim ? blank(graph.g) : graph.g, type: 'scatter', mode: 'lines', connectgaps: false,
      line: { color: COLORS.g, width: 3.2 }, name: graph.is_ox ? 'y = 0 (trục Ox)' : 'y = g(x)',
      hovertemplate: 'x = %{x:.3f}<br>y = %{y:.3f}<extra>g(x)</extra>',
    });
    graph.verticals.forEach((v) => {
      idx.verticals.push(traces.length);
      traces.push({
        x: [v.x, v.x], y: [v.y0, v.y1], type: 'scatter', mode: 'lines', showlegend: false, opacity: anim ? 0 : 1,
        line: { color: COLORS.ink, width: 1.6, dash: 'dash' }, hoverinfo: 'skip',
      });
    });
    if (graph.points.length) {
      idx.points.push(traces.length);
      traces.push({
        x: graph.points.map((p) => p.x), y: graph.points.map((p) => p.y), type: 'scatter', mode: 'markers', showlegend: false,
        marker: { color: COLORS.ink, size: 10, opacity: anim ? 0 : 1, line: { color: '#fff', width: 2 } },
        hovertext: graph.points.map((p) => p.text), hoverinfo: 'text',
      });
    }
    this.idx = idx;

    return window.Plotly.react(this.el, traces, this._layout(opts.equal, opts.grid), this._config()).then(() => {
      this._bind();
      this.apply(opts);
      if (anim) return this._animateIn();
      this._relabel();
      return undefined;
    });
  }

  _axisAnnotations() {
    const v = this.view;
    return [
      { x: v.xmax, y: 0, xref: 'x', yref: 'y', text: '<i>x</i>', showarrow: false, xanchor: 'right', yanchor: 'bottom', font: { size: 15 } },
      { x: 0, y: v.ymax, xref: 'x', yref: 'y', text: '<i>y</i>', showarrow: false, xanchor: 'left', yanchor: 'top', font: { size: 15 } },
    ];
  }

  _layout(equal, grid = true) {
    const v = this.view;
    const axis = (range) => ({
      range, zeroline: true, zerolinecolor: COLORS.ink, zerolinewidth: 2, showgrid: grid, gridcolor: COLORS.grid,
      showline: false, ticks: 'outside', tickcolor: '#9aa8c7', ticklen: 4, automargin: true,
    });
    return {
      margin: PAD, paper_bgcolor: '#fff', plot_bgcolor: '#fff',
      font: { family: FONT, color: COLORS.ink, size: 13 },
      xaxis: axis([v.xmin, v.xmax]),
      yaxis: { ...axis([v.ymin, v.ymax]), ...(equal ? { scaleanchor: 'x', scaleratio: 1 } : {}) },
      showlegend: true, legend: { orientation: 'h', x: 0, y: 1.02, yanchor: 'bottom' },
      hovermode: 'closest', dragmode: 'pan',
      annotations: this._axisAnnotations(),
    };
  }

  _config() {
    return {
      responsive: true, displaylogo: false, scrollZoom: true, displayModeBar: 'hover',
      modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d', 'toImage'],
    };
  }

  _bind() {
    if (this.bound || typeof this.el.on !== 'function') return;
    this.bound = true;
    this.el.on('plotly_relayout', (e) => this._onRelayout(e));
  }

  // ------------------------------------------------------------------ lấy mẫu lại khi zoom/kéo
  _onRelayout(e) {
    const keys = Object.keys(e || {});
    if (!keys.some((k) => k.startsWith('xaxis.range') || k.startsWith('yaxis.range') || k.endsWith('autorange'))) return;
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this._resample(), 160);
  }

  _ranges() {
    const fl = this.el._fullLayout;
    return fl ? { xr: fl.xaxis.range, yr: fl.yaxis.range } : null;
  }

  async _resample() {
    if (this.animating || !this.cur) return;
    const r = this._ranges();
    const req = this.getRequest?.();
    if (!r || !req) return;
    const { xr, yr } = r;
    const w = xr[1] - xr[0];
    const c = this.cover;
    const covW = c.x1 - c.x0;
    const need = xr[0] < c.x0 + 0.25 * w || xr[1] > c.x1 - 0.25 * w || covW / w > 6 || covW / w < 2
      || Math.abs((yr[1] - yr[0]) - (c.y1 - c.y0)) > 0.3 * (c.y1 - c.y0);
    if (!need) { this._relabel(); return; }

    const my = ++this.seq;
    const body = { f1: req.f1, f2: req.f2, x0: xr[0] - w, x1: xr[1] + w, y0: yr[0], y1: yr[1], n: 1600 };
    try {
      const out = await post('/api/sample', body);
      if (my !== this.seq || this.animating) return;
      this.cur = { x: out.x, f: out.f, g: out.g };
      this.cover = { x0: body.x0, x1: body.x1, y0: body.y0, y1: body.y1 };
      window.Plotly.restyle(this.el, { x: [out.x, out.x], y: [out.f, out.g] }, [this.idx.f[0], this.idx.g[0]]);
      this._relabel();
    } catch { /* mất mạng: giữ dữ liệu cũ */ }
  }

  // ------------------------------------------------------------------ nhãn giao điểm không bị đường cắt qua
  _pointAnnotations() {
    const fl = this.el._fullLayout;
    if (!fl || !this.points.length || !this.cur) return [];
    const { xr, yr } = this._ranges();
    const { w, h } = fl._size;
    const px = (x) => ((x - xr[0]) / (xr[1] - xr[0])) * w;
    const py = (y) => ((yr[1] - y) / (yr[1] - yr[0])) * h;

    // Vật cản: các điểm mẫu của hai đường cong, hai trục và các đường x = a, x = b (theo pixel)
    const obst = [];
    const { x, f, g } = this.cur;
    for (let i = 0; i < x.length; i += 1) {
      const X = px(x[i]);
      if (X < -60 || X > w + 60) continue;
      if (f[i] != null) obst.push([X, py(f[i])]);
      if (g[i] != null) obst.push([X, py(g[i])]);
    }
    const line = (x0, y0, x1, y1) => {
      const n = Math.max(2, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 6));
      for (let i = 0; i <= n; i += 1) obst.push([x0 + ((x1 - x0) * i) / n, y0 + ((y1 - y0) * i) / n]);
    };
    line(px(0), 0, px(0), h);
    line(0, py(0), w, py(0));
    this.verticals.forEach((v) => line(px(v.x), py(v.y0), px(v.x), py(v.y1)));

    const placed = [];
    const out = [];
    this.points.forEach((p) => {
      if (p.x < xr[0] || p.x > xr[1] || p.y < yr[0] || p.y > yr[1]) return;
      const text = this.opts.coords ? p.text : p.label;
      const bw = this.opts.coords ? text.length * 7.2 + 14 : text.length * 9 + 12;
      const bh = 24;
      const P = [px(p.x), py(p.y)];
      let best = null;
      for (const r of [40, 62, 88]) {
        for (let k = 0; k < 12; k += 1) {
          const ang = (k * Math.PI) / 6 + Math.PI / 12;
          const C = [P[0] + r * Math.cos(ang), P[1] - r * Math.sin(ang)];
          const rect = [C[0] - bw / 2, C[1] - bh / 2, C[0] + bw / 2, C[1] + bh / 2];
          if (rect[0] < 2 || rect[1] < 2 || rect[2] > w - 2 || rect[3] > h - 2) continue;
          let clear = 999;
          for (const [ox, oy] of obst) {
            const dx = Math.max(rect[0] - ox, 0, ox - rect[2]);
            const dy = Math.max(rect[1] - oy, 0, oy - rect[3]);
            const d = Math.hypot(dx, dy);
            if (d < clear) clear = d;
            if (clear < 1) break;
          }
          for (const q of placed) {
            if (rect[0] < q[2] + 4 && rect[2] > q[0] - 4 && rect[1] < q[3] + 4 && rect[3] > q[1] - 4) clear = -1;
          }
          const score = clear - 0.12 * r;
          if (!best || score > best.score) best = { score, C, rect };
        }
      }
      if (!best) best = { C: [P[0] + 46, P[1] - 40], rect: [P[0] + 46 - bw / 2, P[1] - 52, P[0] + 46 + bw / 2, P[1] - 28] };
      placed.push(best.rect);
      out.push({
        x: p.x, y: p.y, xref: 'x', yref: 'y', ax: best.C[0] - P[0], ay: best.C[1] - P[1], axref: 'pixel', ayref: 'pixel',
        text, showarrow: true, arrowhead: 0, arrowwidth: 1.2, arrowcolor: COLORS.ink, standoff: 5,
        xanchor: 'center', yanchor: 'middle', bgcolor: 'rgba(255,255,255,0.96)', bordercolor: '#B9C6E4', borderwidth: 1, borderpad: 3,
        font: { size: 13, color: COLORS.ink },
      });
    });
    return out;
  }

  _relabel() {
    if (!this.ready || !this.view) return;
    window.Plotly.relayout(this.el, { annotations: [...this._axisAnnotations(), ...this._pointAnnotations()] });
  }

  // ------------------------------------------------------------------ hiệu ứng vào
  async _animateIn() {
    const my = this.animToken;
    this.animating = true;
    const alive = () => my === this.animToken;
    const frame = () => new Promise((r) => requestAnimationFrame(r));
    const { x, f, g } = this.cur;
    const [iF] = this.idx.f;
    const [iG] = this.idx.g;
    const vx0 = this.view.xmin;
    const vx1 = this.view.xmax;
    const kStart = Math.max(0, x.findIndex((v) => v >= vx0));
    let kEnd = x.findIndex((v) => v >= vx1);
    if (kEnd < 0) kEnd = x.length - 1;

    // 1) đường cong vẽ dần từ trái sang phải
    const t0 = performance.now();
    while (alive()) {
      const t = Math.min(1, (performance.now() - t0) / 760);
      const k = Math.round(kStart + (1 - (1 - t) ** 3) * (kEnd - kStart));
      window.Plotly.restyle(this.el, { y: [f.map((v, i) => (i <= k ? v : null)), g.map((v, i) => (i <= k ? v : null))] }, [iF, iG]);
      if (t >= 1) break;
      await frame();
    }
    if (!alive()) return;
    window.Plotly.restyle(this.el, { y: [f, g] }, [iF, iG]);

    // 2) vùng diện tích tô dần + đường cận hiện ra
    const t1 = performance.now();
    while (alive()) {
      const t = Math.min(1, (performance.now() - t1) / 520);
      if (this.idx.area.length) window.Plotly.restyle(this.el, { fillcolor: rgba(COLORS.areaAlpha * t) }, this.idx.area);
      if (this.idx.verticals.length) window.Plotly.restyle(this.el, { opacity: t }, this.idx.verticals);
      if (t >= 1) break;
      await frame();
    }
    if (!alive()) return;

    // 3) giao điểm và nhãn
    if (this.idx.points.length) window.Plotly.restyle(this.el, { 'marker.opacity': 1 }, this.idx.points);
    this.animating = false;
    this._relabel();
  }

  // ------------------------------------------------------------------ bật/tắt thành phần
  apply(o) {
    this.opts = { ...this.opts, ...o };
    this.setVisible('f', o.f);
    this.setVisible('g', o.g);
    this.setVisible('area', o.area);
    this.setGrid(o.grid);
    this.setEqual(o.equal);
  }

  setVisible(kind, on) {
    const ids = this.idx?.[kind];
    if (!this.ready || !ids?.length) return;
    window.Plotly.restyle(this.el, { visible: !!on }, ids);
    if (kind === 'area') this.idx.verticals.length && window.Plotly.restyle(this.el, { visible: true }, this.idx.verticals);
  }

  setGrid(on) {
    if (this.ready) window.Plotly.relayout(this.el, { 'xaxis.showgrid': !!on, 'yaxis.showgrid': !!on });
  }

  setCoords(on) {
    this.opts.coords = !!on;
    if (!this.animating) this._relabel();
  }

  setEqual(on) {
    if (!this.ready) return;
    window.Plotly.relayout(this.el, on
      ? { 'yaxis.scaleanchor': 'x', 'yaxis.scaleratio': 1 }
      : { 'yaxis.scaleanchor': false });
  }

  reset() {
    if (!this.ready || !this.view) return;
    const v = this.view;
    window.Plotly.relayout(this.el, { 'xaxis.range': [v.xmin, v.xmax], 'yaxis.range': [v.ymin, v.ymax] });
  }

  download(format) {
    if (!this.ready) return Promise.resolve();
    return window.Plotly.downloadImage(this.el, {
      format, filename: 'arealab-do-thi', width: 1400, height: 900, scale: format === 'png' ? 2 : 1,
    });
  }
}
