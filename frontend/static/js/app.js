// Điều phối giao diện: nhập liệu -> gọi API -> hiển thị đồ thị, kết quả, bước giải, mã LaTeX.
import { get, post } from './api.js';
import { initContact } from './contact.js';
import { openGuide } from './guide.js';
import { tex, typeset } from './math.js';
import { initReveal, moveInk } from './motion.js';
import { Plot } from './plot.js';
import { renderEmpty, renderLatex, renderResult, renderSteps } from './results.js';
import { h, sleep } from './utils.js';

const $ = (id) => document.getElementById(id);

const state = {
  mode: 'manual',
  study: false,
  revealed: false,
  result: null,
  payload: null,
  run: 0,
  roots: null,
  previewCache: {},
  examples: null,
  health: null,
};

// Đồ thị lấy mẫu lại theo lần tính gần nhất (không phải nội dung đang gõ dở trong ô nhập)
const plot = new Plot($('plot'), () => state.payload && { f1: state.payload.f1, f2: state.payload.f2 });

const STAGES = ['parse', 'intersections', 'region', 'integral', 'graph', 'latex'];
const NODE_OF = { parse: ['parse'], intersections: ['intersections'], region: ['region'], integral: ['integral', 'area'], graph: ['graph'], latex: ['latex'] };
const DONE_TEXT = {
  parse: 'Đã phân tích hàm số', intersections: 'Đã tìm giao điểm', region: 'Đã xác định miền cần tính',
  integral: 'Đã tính tích phân', graph: 'Đã tạo đồ thị', latex: 'Đã sinh mã LaTeX',
};
const FAIL_TEXT = {
  parse: 'Chưa đọc được hàm số', intersections: 'Chưa xác định được giao điểm', region: 'Chưa xác định được miền cần tính',
  integral: 'Chưa tính được tích phân', graph: 'Chưa tạo được đồ thị', latex: 'Chưa sinh được mã LaTeX',
};

// ------------------------------------------------------------------ chế độ cận
function setMode(mode) {
  state.mode = mode;
  $('mode-manual').setAttribute('aria-checked', String(mode === 'manual'));
  $('mode-auto').setAttribute('aria-checked', String(mode === 'auto'));
  $('bounds-manual').hidden = mode !== 'manual';
  $('bounds-auto').hidden = mode !== 'auto';
}

function payload() {
  return {
    f1: $('f1').value.trim(),
    f2: $('f2').value.trim() || '0',
    a: state.mode === 'manual' ? $('a').value.trim() : '',
    b: state.mode === 'manual' ? $('b').value.trim() : '',
    mode: state.mode,
  };
}

// ------------------------------------------------------------------ xem trước công thức khi đang gõ
function attachLive(input, out, kind, prefix, emptyText) {
  let timer;
  let seq = 0;
  const run = async () => {
    const my = ++seq;
    const text = input.value.trim();
    if (!text) {
      out.className = 'live';
      out.replaceChildren(emptyText ? h('span', { class: 'live-empty' }, emptyText) : '');
      return;
    }
    try {
      const r = await post('/api/parse', { text, kind });
      if (my !== seq) return;
      out.className = 'live ok';
      out.replaceChildren(tex(`${prefix}${r.latex}`, false));
    } catch (e) {
      if (my !== seq) return;
      out.className = 'live bad';
      const msg = e.code === 'parse' || e.code === 'bound'
        ? 'Chưa đọc được biểu thức này. Bấm "Hướng dẫn gõ" để xem cách nhập.'
        : (e.message || '').split('\n')[0];
      out.replaceChildren(h('span', {}, msg));
    }
  };
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(run, 320); });
  run();
}

// ------------------------------------------------------------------ quy trình + trạng thái
const nodeEl = (k) => document.querySelector(`#flow li[data-node="${k}"]`);

function resetFlow() {
  document.querySelectorAll('#flow li').forEach((n) => n.classList.remove('done', 'active', 'error'));
  $('status').replaceChildren();
}

function statusLine(text, cls, mark) {
  const li = h('li', { class: cls }, h('span', { class: 'mark' }, mark), h('span', {}, text));
  $('status').append(li);
  return li;
}

async function animateProgress(doneKeys, failKey, token) {
  resetFlow();
  for (const key of STAGES) {
    if (token !== state.run) return;
    if (doneKeys.includes(key)) {
      NODE_OF[key].forEach((n) => nodeEl(n)?.classList.add('done'));
      statusLine(DONE_TEXT[key], '', '✓');
      await sleep(110);
    } else if (key === failKey) {
      NODE_OF[key].forEach((n) => nodeEl(n)?.classList.add('error'));
      statusLine(FAIL_TEXT[key], 'fail', '✗');
      break;
    }
  }
}

function showError(err) {
  const box = $('error');
  box.replaceChildren(document.createTextNode(err.message || 'Đã xảy ra lỗi.'));
  if (err.detail) box.append(h('div', { style: 'margin-top:.35rem;font-size:.85rem;opacity:.85' }, `Chi tiết: ${err.detail}`));
  box.hidden = false;
}

// ------------------------------------------------------------------ tính toán
async function calculate() {
  const token = ++state.run;
  const btn = $('btn-calc');
  $('error').hidden = true;
  btn.disabled = true;
  btn.textContent = 'Đang tính…';
  resetFlow();
  nodeEl('parse')?.classList.add('active');
  statusLine('Đang xử lý…', 'busy', '…');

  const body = payload();
  try {
    const res = await post('/api/calculate', body);
    if (token !== state.run) return;
    state.result = res;
    state.payload = body;
    state.revealed = false;
    state.previewCache = {};
    renderAll();
    await animateProgress(res.pipeline.map((p) => p.key), null, token);
  } catch (err) {
    if (token !== state.run) return;
    showError(err);
    const failKey = STAGES.includes(err.stage) ? err.stage : null;
    await animateProgress(failKey ? STAGES.slice(0, STAGES.indexOf(failKey)) : [], failKey, token);
  } finally {
    if (token === state.run) {
      btn.disabled = false;
      btn.textContent = 'Tính diện tích';
    }
  }
}

function toggles() {
  return {
    f: $('t-f').checked, g: $('t-g').checked, area: $('t-area').checked,
    grid: $('t-grid').checked, coords: $('t-coords').checked, equal: $('t-equal').checked,
  };
}

function ctx(animate = false) {
  return {
    study: state.study,
    revealed: state.revealed,
    animate,
    health: state.health,
    reveal: () => { state.revealed = true; renderTabs(false); },
    previewCache: state.previewCache,
    fetchPreview: (variant) => post('/api/latex/preview', { ...state.payload, variant }),
  };
}

function renderTabs(animate) {
  if (!state.result) return;
  const c = ctx(animate);
  renderResult($('panel-result'), state.result, c);
  renderSteps($('panel-steps'), state.result, c);
  renderLatex($('panel-latex'), state.result, c);
}

function renderAll() {
  $('plot-empty').classList.add('hide');
  plot.draw(state.result.graph_data, toggles(), true);
  renderTabs(true);
}

// ------------------------------------------------------------------ tab
function selectTab(id) {
  document.querySelectorAll('[role="tab"]').forEach((t) => {
    const on = t.id === id;
    t.setAttribute('aria-selected', String(on));
    t.tabIndex = on ? 0 : -1;
    $(t.getAttribute('aria-controls')).hidden = !on;
  });
  moveInk(document.querySelector('.tabs'));
}

document.querySelectorAll('[role="tab"]').forEach((t, i, all) => {
  t.addEventListener('click', () => selectTab(t.id));
  t.addEventListener('keydown', (e) => {
    const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!dir) return;
    const next = all[(i + dir + all.length) % all.length];
    next.focus();
    selectTab(next.id);
  });
});
window.addEventListener('resize', () => moveInk(document.querySelector('.tabs')));

// ------------------------------------------------------------------ sự kiện
$('calc-form').addEventListener('submit', (e) => { e.preventDefault(); calculate(); });
$('mode-manual').addEventListener('click', () => setMode('manual'));
$('mode-auto').addEventListener('click', () => setMode('auto'));

$('btn-find').addEventListener('click', async () => {
  const box = $('roots');
  box.replaceChildren(h('span', { class: 'hint' }, 'Đang tìm giao điểm…'));
  $('btn-use-roots').hidden = true;
  $('error').hidden = true;
  try {
    const res = await post('/api/intersections', { f1: $('f1').value.trim(), f2: $('f2').value.trim() || '0' });
    state.roots = res;
    box.replaceChildren(...res.intersections.map((p) => h('span', { class: 'root-chip' }, tex(p.point_latex, false))));
    $('btn-use-roots').hidden = !res.suggested;
  } catch (err) {
    box.replaceChildren();
    showError(err);
  }
});

$('btn-use-roots').addEventListener('click', () => {
  if (!state.roots?.suggested) return;
  $('a').value = state.roots.suggested.a;
  $('b').value = state.roots.suggested.b;
  $('a').dispatchEvent(new Event('input'));
  $('b').dispatchEvent(new Event('input'));
  setMode('manual');
});

$('study-toggle').addEventListener('click', () => {
  state.study = !state.study;
  $('study-toggle').setAttribute('aria-checked', String(state.study));
  state.revealed = false;
  $('t-coords').checked = !state.study;
  plot.setCoords($('t-coords').checked);
  renderTabs(false);
});

$('t-f').addEventListener('change', (e) => plot.setVisible('f', e.target.checked));
$('t-g').addEventListener('change', (e) => plot.setVisible('g', e.target.checked));
$('t-area').addEventListener('change', (e) => plot.setVisible('area', e.target.checked));
$('t-grid').addEventListener('change', (e) => plot.setGrid(e.target.checked));
$('t-coords').addEventListener('change', (e) => plot.setCoords(e.target.checked));
$('t-equal').addEventListener('change', (e) => plot.setEqual(e.target.checked));
$('btn-reset').addEventListener('click', () => plot.reset());
$('btn-png').addEventListener('click', () => plot.download('png'));
$('btn-svg').addEventListener('click', () => plot.download('svg'));

// ------------------------------------------------------------------ hướng dẫn gõ
function useTyped(typed) {
  $('f1').value = typed;
  $('f1').dispatchEvent(new Event('input'));
  $('guide-dialog').close();
  $('f1').focus();
}
const showGuide = () => openGuide($('guide-dialog'), $('guide-body'), useTyped);
$('open-guide').addEventListener('click', showGuide);
$('open-guide-inline').addEventListener('click', showGuide);
$('close-guide').addEventListener('click', () => $('guide-dialog').close());
$('guide-dialog').addEventListener('click', (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

// ------------------------------------------------------------------ ví dụ mẫu
async function openExamples() {
  const dlg = $('examples-dialog');
  dlg.showModal();
  if (state.examples) return;
  const body = $('examples-body');
  body.replaceChildren(h('p', { class: 'hint' }, 'Đang tải…'));
  try {
    state.examples = (await get('/api/examples')).examples;
  } catch (err) {
    body.replaceChildren(h('p', { class: 'error' }, err.message));
    return;
  }
  const byCat = new Map();
  state.examples.forEach((ex) => byCat.set(ex.category, [...(byCat.get(ex.category) || []), ex]));
  body.replaceChildren();
  for (const [cat, items] of byCat) {
    body.append(h('h3', { class: 'ex-cat' }, cat));
    items.forEach((ex) => body.append(h('div', { class: 'ex' },
      h('div', {},
        h('p', { class: 'ex-title' }, ex.title),
        h('p', { class: 'ex-desc' }, ex.description),
        h('p', { class: 'ex-fn' }, `f(x) = ${ex.f1};  g(x) = ${ex.f2}${ex.mode === 'manual' ? `;  a = ${ex.a}, b = ${ex.b}` : ''}`)),
      h('button', { type: 'button', class: 'btn secondary', onclick: () => useExample(ex) }, 'Dùng ví dụ này'))));
  }
}

function useExample(ex) {
  $('f1').value = ex.f1;
  $('f2').value = ex.f2;
  $('a').value = ex.a || '';
  $('b').value = ex.b || '';
  ['f1', 'f2', 'a', 'b'].forEach((id) => $(id).dispatchEvent(new Event('input')));
  setMode(ex.mode === 'auto' ? 'auto' : 'manual');
  $('examples-dialog').close();
  calculate();
}

$('open-examples').addEventListener('click', openExamples);
$('close-examples').addEventListener('click', () => $('examples-dialog').close());
$('examples-dialog').addEventListener('click', (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

// ------------------------------------------------------------------ khởi động
initContact();
initReveal();
plot.drawEmpty();
renderEmpty($('panel-steps'), 'Các bước giải sẽ hiện sau khi bạn nhấn Tính diện tích.');
renderEmpty($('panel-latex'), 'Mã LaTeX (TikZ/PGFPlots) sẽ hiện sau khi bạn nhấn Tính diện tích.');
typeset(document.body);
attachLive($('f1'), $('f1-live'), 'fn', 'f(x)=', '');
attachLive($('f2'), $('f2-live'), 'fn', 'g(x)=', 'g(x) = 0 (trục Ox)');
attachLive($('a'), $('a-live'), 'bound', 'a=', '');
attachLive($('b'), $('b-live'), 'bound', 'b=', '');
requestAnimationFrame(() => moveInk(document.querySelector('.tabs')));
get('/api/health').then((hs) => { state.health = hs; }).catch(() => {});
calculate(); // chạy sẵn ví dụ mặc định để trang không trống
