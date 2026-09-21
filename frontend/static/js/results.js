// Dựng nội dung ba tab: Kết quả, Các bước giải, Mã LaTeX.
import { figureSVG } from './figure.js';
import { richText, tex } from './math.js';
import { countUp } from './motion.js';
import { checkAnswer, copyText, downloadBase64, downloadText, h, toast } from './utils.js';

const line = (latex) => h('div', { class: 'math-line' }, tex(latex, false));
const block = (title, ...children) => h('section', { class: 'block' }, h('h3', {}, title), ...children);

export function renderEmpty(panel, message) {
  panel.replaceChildren(h('p', { class: 'empty' }, message));
}

// ------------------------------------------------------------------ TAB 1: KẾT QUẢ
export function renderResult(panel, res, ctx) {
  panel.replaceChildren();
  if (ctx.study && !ctx.revealed) {
    panel.append(coverCard(res, ctx));
    return;
  }
  const root = fullResult(res);
  panel.append(root);
  const num = root.querySelector('.decimal-num');
  if (num) {
    if (ctx.animate) countUp(num, res.area_value, res.area_decimal);
    else num.textContent = res.area_decimal;
  }
}

function coverCard(res, ctx) {
  const msg = h('p', { class: 'check-msg', 'aria-live': 'polite' });
  const input = h('input', { class: 'math-input', type: 'text', placeholder: 'Đáp số, ví dụ 32/3 hoặc 10.67', 'aria-label': 'Đáp số của bạn' });
  const verify = () => {
    const r = checkAnswer(input.value, res.area_value);
    msg.className = 'check-msg';
    if (r === 'invalid') msg.textContent = 'Hãy nhập đáp số dạng phân số (32/3) hoặc số thập phân (10.67).';
    else if (r === 'correct') { msg.textContent = 'Chính xác! Hãy mở lời giải để đối chiếu cách làm.'; msg.classList.add('ok'); }
    else { msg.textContent = 'Chưa đúng. Kiểm tra lại cận, hàm trên/dưới hoặc nguyên hàm rồi thử lại.'; msg.classList.add('no'); }
  };
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); verify(); } });
  return h('div', { class: 'cover' },
    h('h3', {}, 'Chế độ học tập'),
    h('p', {}, 'Đồ thị đã cho thấy miền cần tính. Hãy tự tìm giao điểm, lập tích phân và tính diện tích, rồi nhập đáp số để kiểm tra.'),
    h('div', { class: 'check-row' }, input, h('button', { type: 'button', class: 'btn secondary', onclick: verify }, 'Kiểm tra')),
    msg,
    h('button', { type: 'button', class: 'btn ghost', onclick: () => ctx.reveal() }, 'Hiện đáp án'));
}

function fullResult(res) {
  const root = h('div');
  const grid = h('div', { class: 'result-grid' });

  const inter = block('Giao điểm');
  if (res.intersections.length) {
    inter.append(line(res.intersections.map((p) => `x=${p.x_latex}`).join(',\\qquad ')));
    inter.append(line(res.intersections.map((p) => p.point_latex).join(',\\qquad ')));
    if (res.intersections.some((p) => !p.exact)) inter.append(h('p', { class: 'hint' }, 'Nghiệm gần đúng (không có công thức đóng).'));
  } else {
    inter.append(h('p', { class: 'hint' }, 'Hai đồ thị không cắt nhau trong đoạn đã chọn.'));
  }
  grid.append(inter);

  const bounds = block('Các cận', line(`a=${res.bounds.a.latex},\\qquad b=${res.bounds.b.latex}`));
  if (res.breakpoints.length > 2) {
    bounds.append(h('p', { class: 'hint' }, 'Các mốc chia miền:'));
    bounds.append(line(res.breakpoints.map((b, i) => `x_{${i}}=${b.latex}`).join(',\\quad ')));
  }
  grid.append(bounds);

  const roles = block(res.intervals.length > 1 ? 'Hàm trên / hàm dưới theo từng khoảng' : 'Hàm trên / hàm dưới');
  roles.classList.add('wide');
  res.intervals.forEach((iv) => {
    roles.append(h('div', { class: 'interval' },
      line(`\\text{Trên }\\left[${iv.lo.latex};\\,${iv.hi.latex}\\right]:`),
      h('dl', { class: 'roles' },
        h('dt', {}, 'Hàm trên'), h('dd', {}, line(`${iv.upper}(x)=${iv.upper_latex}`)),
        h('dt', {}, res.is_ox ? 'Hàm dưới (trục Ox)' : 'Hàm dưới'), h('dd', {}, line(`${iv.lower}(x)=${iv.lower_latex}`)))));
  });
  grid.append(roles);

  const formula = block('Công thức diện tích');
  formula.classList.add('wide');
  formula.append(tex(res.integral_latex));
  if (res.intervals.length === 1) {
    formula.append(h('p', { class: 'hint' }, 'Vì một hàm luôn nằm trên hàm còn lại nên bỏ được dấu giá trị tuyệt đối:'));
    formula.append(tex(`S=${res.intervals[0].integral_latex}`));
  } else {
    formula.append(h('p', { class: 'hint' }, 'Tách theo các mốc chia miền:'));
    formula.append(tex(res.pieces_formula_latex));
    res.intervals.forEach((iv) => {
      const rel = iv.exact ? '=' : '\\approx';
      formula.append(tex(`S_{${iv.index}}=${iv.integral_latex}${rel}${iv.area_latex}`));
    });
  }
  grid.append(formula);

  const rel = res.exact ? '=' : '\\approx';
  const final = block('Kết quả');
  final.classList.add('wide', 'final');
  final.append(tex(`\\boxed{S${rel}${res.area_latex}}`));
  final.append(h('p', { class: 'decimal' }, 'S ≈ ', h('span', { class: 'decimal-num' }, res.area_decimal), ' (đơn vị diện tích)'));
  if (!res.exact) final.append(h('span', { class: 'badge' }, 'Giá trị gần đúng'));
  grid.append(final);

  [...grid.children].forEach((b, i) => b.style.setProperty('--i', i));
  root.append(grid);
  if (res.warnings?.length) {
    root.append(h('div', { class: 'warn' }, h('ul', {}, res.warnings.map((w) => h('li', {}, w)))));
  }
  return root;
}

// ------------------------------------------------------------------ TAB 2: CÁC BƯỚC GIẢI
function blocks(list) {
  return list.map((b) => (b.type === 'math' ? tex(b.content) : richText(b.content)));
}

export function renderSteps(panel, res, ctx) {
  panel.replaceChildren();
  panel.append(h('p', { class: 'hint' },
    ctx.study ? 'Chế độ học tập: thử tự làm từng bước, cần thì mở gợi ý rồi lời giải.' : 'Nhấn vào tiêu đề từng bước để thu gọn hoặc mở rộng.'));
  res.steps.forEach((s, i) => {
    const body = h('div', { class: 'step-body' });
    if (!ctx.study) {
      body.append(...blocks(s.blocks));
    } else {
      const hint = h('div', { class: 'hint-box', hidden: true }, richText(s.hint));
      const sol = h('div', { hidden: true }, ...blocks(s.blocks));
      body.append(
        richText(s.prompt),
        h('div', { class: 'step-actions' },
          h('button', { type: 'button', class: 'btn ghost small', onclick: () => { hint.hidden = !hint.hidden; } }, 'Hiển thị gợi ý'),
          h('button', { type: 'button', class: 'btn secondary small', onclick: () => { sol.hidden = !sol.hidden; } }, 'Hiện lời giải')),
        hint, sol);
    }
    const step = h('details', { class: 'step', open: true }, h('summary', {}, s.title), body);
    step.style.setProperty('--i', i);
    panel.append(step);
  });
}

// ------------------------------------------------------------------ TAB 3: MÃ LaTeX
/** Tô màu cú pháp LaTeX (lệnh, ngoặc, chú thích) bằng DOM, không dùng innerHTML. */
export function highlightTeX(text) {
  const frag = document.createDocumentFragment();
  const re = /(%.*$)|(\\[A-Za-z@]+|\\.)|([{}[\]$&])/gm;
  let last = 0;
  let m = re.exec(text);
  while (m) {
    if (m.index > last) frag.append(text.slice(last, m.index));
    frag.append(h('span', { class: m[1] ? 'tk-cm' : m[2] ? 'tk-cmd' : 'tk-br' }, m[0]));
    last = m.index + m[0].length;
    m = re.exec(text);
  }
  frag.append(text.slice(last));
  return frag;
}

/** Mở tài liệu trong Overleaf bằng một cú bấm (Overleaf nhận mã LaTeX qua biểu mẫu POST). */
export function openInOverleaf(docText) {
  const form = h('form', { action: 'https://www.overleaf.com/docs', method: 'post', target: '_blank', style: 'display:none' },
    h('input', { type: 'hidden', name: 'snip', value: docText }),
    h('input', { type: 'hidden', name: 'snip_name', value: 'arealab-hinh.tex' }),
    h('input', { type: 'hidden', name: 'engine', value: 'pdflatex' }));
  document.body.append(form);
  form.submit();
  form.remove();
}

export function renderLatex(panel, res, ctx) {
  panel.replaceChildren();
  if (!res.pgfplots_code) {
    panel.append(h('p', { class: 'empty' }, res.latex_note || 'Chưa có mã LaTeX cho bài toán này.'));
    return;
  }
  const variants = {
    pgfplots: { label: 'PGFPlots (khuyên dùng)', code: res.pgfplots_code, doc: res.tex_document, preview: 'pgfplots' },
    tikz: { label: 'TikZ thuần', code: res.tikz_code, doc: res.tex_document_tikz, preview: 'tikz' },
    doc: { label: 'Tài liệu đầy đủ (.tex)', code: res.tex_document, doc: res.tex_document, preview: 'pgfplots' },
  };
  let current = 'pgfplots';

  const code = h('code', {});
  code.append(highlightTeX(variants[current].code));
  const pre = h('pre', { class: 'code', tabindex: '0', 'aria-label': 'Mã LaTeX' }, code);

  const select = h('select', { 'aria-label': 'Loại mã LaTeX' },
    Object.entries(variants).map(([k, v]) => h('option', { value: k }, v.label)));
  select.addEventListener('change', () => {
    current = select.value;
    code.replaceChildren(highlightTeX(variants[current].code));
  });

  // ---- khung xem trước: mặc định dựng nhanh bằng SVG (không cần TeX)
  const previewBox = h('div', { class: 'preview' }, figureSVG(res.graph_data, res));
  const note = h('p', { class: 'preview-note' }, 'Xem trước nhanh: dựng ngay trong trình duyệt, gần giống bản biên dịch bằng pdfLaTeX.');
  const compileNote = h('div', { class: 'preview-actions' });

  async function compileReal() {
    const kind = variants[current].preview;
    previewBox.replaceChildren(h('span', {}, 'Đang biên dịch bằng pdflatex…'));
    try {
      const out = ctx.previewCache[kind] || (ctx.previewCache[kind] = await ctx.fetchPreview(kind));
      if (out.png_base64) {
        previewBox.replaceChildren(h('img', { src: `data:image/png;base64,${out.png_base64}`, alt: 'Hình LaTeX đã biên dịch' }));
      } else {
        const bin = Uint8Array.from(atob(out.pdf_base64), (c) => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bin], { type: 'application/pdf' }));
        previewBox.replaceChildren(h('embed', { src: url, type: 'application/pdf', class: 'pdf-embed' }));
      }
      note.textContent = out.note || 'Bản biên dịch thật bằng pdfLaTeX.';
      if (out.pdf_base64) {
        compileNote.append(h('button', { type: 'button', class: 'btn ghost small', onclick: () => downloadBase64('arealab-hinh.pdf', out.pdf_base64, 'application/pdf') }, 'Tải PDF vector'));
      }
    } catch (e) {
      previewBox.replaceChildren(figureSVG(res.graph_data, res));
      note.textContent = `Không biên dịch được bằng pdflatex: ${(e.message || '').split('\n')[0]} Đang hiển thị bản xem trước nhanh.`;
    }
  }

  const copyBtn = h('button', { type: 'button', class: 'btn primary', onclick: async () => {
    toast((await copyText(variants[current].code)) ? 'Đã sao chép mã LaTeX' : 'Không sao chép được, hãy chọn và copy thủ công');
  } }, 'Sao chép mã LaTeX');
  const dlBtn = h('button', { type: 'button', class: 'btn ghost', onclick: () => downloadText('arealab-hinh.tex', variants[current].doc) }, 'Tải file .tex');
  const olBtn = h('button', { type: 'button', class: 'btn overleaf', onclick: () => openInOverleaf(variants[current].doc) }, 'Mở trong Overleaf');
  if (ctx.health?.pdflatex) {
    compileNote.append(h('button', { type: 'button', class: 'btn ghost small', onclick: compileReal }, 'Biên dịch thật bằng pdflatex'));
  }

  panel.append(h('div', { class: 'latex-layout' },
    h('div', {},
      h('div', { class: 'latex-tools' }, select, copyBtn, dlBtn),
      pre,
      h('p', { class: 'hint' }, 'Hai loại đầu là hình để dán vào tài liệu (cần gói tikz, pgfplots); loại thứ ba là tệp độc lập biên dịch bằng pdfLaTeX.')),
    h('div', {},
      h('div', { class: 'preview-head' }, h('h3', {}, 'Xem trước hình'), olBtn),
      previewBox, note, compileNote)));
}
