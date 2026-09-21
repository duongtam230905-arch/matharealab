// Hộp thoại "Hướng dẫn gõ hàm số". Cột hiển thị do máy chủ tính bằng đúng bộ đọc biểu thức của web.
import { get } from './api.js';
import { tex } from './math.js';
import { h } from './utils.js';

let cache = null;

const TILES = [
  ['*', 'Nhân', '2*x', '2\\cdot x'],
  ['/', 'Chia', 'x/2', '\\dfrac{x}{2}'],
  ['^  hoặc  **', 'Mũ', 'x^2', 'x^{2}'],
  ['( )', 'Ngoặc', '(x+1)/(x-2)', '\\dfrac{x+1}{x-2}'],
  ['sqrt( )', 'Căn bậc hai', 'sqrt(x)', '\\sqrt{x}'],
  ['| |', 'Giá trị tuyệt đối', '|x-1|', '|x-1|'],
];

function tile([key, name, typed, latex]) {
  return h('div', { class: 'tile' },
    h('div', { class: 'tile-key' }, key),
    h('div', { class: 'tile-name' }, name),
    h('code', {}, typed), h('span', { class: 'tile-arrow', 'aria-hidden': 'true' }, '→'), tex(latex, false));
}

function row(r, tryIt) {
  return h('div', { class: 'g-row' },
    h('code', { class: 'g-typed' }, r.typed),
    h('div', { class: 'g-show' }, tex(`y=${r.latex}`, false)),
    h('div', { class: 'g-note' }, r.note),
    h('button', { type: 'button', class: 'btn ghost small', onclick: () => tryIt(r.typed) }, 'Dùng thử'));
}

function render(body, data, tryIt) {
  body.replaceChildren(
    h('p', { class: 'g-intro' }, 'Gõ như trên máy tính: dùng ký hiệu trên bàn phím, không cần gõ công thức LaTeX. Ô nhập bên trái luôn hiện lại công thức bạn vừa gõ để kiểm tra.'),
    h('div', { class: 'tiles' }, TILES.map(tile)),
    ...data.groups.map((g) => h('section', { class: 'g-group' },
      h('h3', {}, g.title),
      h('div', { class: 'g-head' }, h('span', {}, 'Bạn gõ'), h('span', {}, 'Web hiểu là'), h('span', {}, 'Ghi chú'), h('span', {})),
      g.rows.map((r) => row(r, tryIt)))),
    h('section', { class: 'g-group' },
      h('h3', {}, 'Những chỗ dễ nhầm'),
      data.mistakes.map((m) => h('div', { class: 'g-mistake' },
        h('div', {}, h('code', {}, m.typed), h('span', { class: 'tile-arrow' }, '→'), tex(m.latex, false)),
        h('p', {}, m.note),
        h('div', {}, 'Cách gõ đúng: ', h('code', {}, m.fix), h('span', { class: 'tile-arrow' }, '→'), tex(m.fix_latex, false),
          ' ', h('button', { type: 'button', class: 'btn ghost small', onclick: () => tryIt(m.fix) }, 'Dùng thử'))))),
    h('section', { class: 'g-group' }, h('h3', {}, 'Mẹo'), h('ul', { class: 'g-tips' }, data.tips.map((t) => h('li', {}, t)))));
}

export async function openGuide(dialog, body, tryIt) {
  dialog.showModal();
  if (cache) return render(body, cache, tryIt);
  body.replaceChildren(h('p', { class: 'hint' }, 'Đang tải hướng dẫn…'));
  try {
    cache = await get('/api/guide');
  } catch (err) {
    body.replaceChildren(h('p', { class: 'error' }, err.message || 'Không tải được hướng dẫn.'));
    return;
  }
  render(body, cache, tryIt);
}
