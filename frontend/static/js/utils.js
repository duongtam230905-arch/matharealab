// Tiện ích thuần (không phụ thuộc trình duyệt trừ h/download) để dễ kiểm thử.

/** Tạo phần tử DOM: h('div', {class:'x'}, 'text', child). Không bao giờ dùng innerHTML. */
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Đọc đáp số người học nhập: 32/3, 10,67, -2.5. Trả về NaN nếu không hiểu. */
export function parseAnswer(text) {
  if (typeof text !== 'string') return NaN;
  const s = text.trim().replace(/\s+/g, '').replace(/,/g, '.').replace(/[−–]/g, '-');
  if (/^-?\d+(\.\d+)?$/.test(s)) return parseFloat(s);
  const m = s.match(/^(-?\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
  if (m && parseFloat(m[2]) !== 0) return parseFloat(m[1]) / parseFloat(m[2]);
  return NaN;
}

/** So sánh đáp số với giá trị đúng (sai số tương đối 1e-4 hoặc làm tròn đến 2 chữ số thập phân). */
export function checkAnswer(text, truth) {
  const v = parseAnswer(text);
  if (Number.isNaN(v)) return 'invalid';
  const tol = Math.max(1e-4 * Math.max(1, Math.abs(truth)), 0);
  if (Math.abs(v - truth) <= tol) return 'correct';
  if (Math.abs(v - truth) <= 0.005 + 1e-9) return 'correct'; // đã làm tròn 2 chữ số
  return 'wrong';
}

export function downloadText(filename, text, mime = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  clickDownload(filename, url);
}

export function downloadBase64(filename, b64, mime) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  clickDownload(filename, URL.createObjectURL(new Blob([bytes], { type: mime })));
}

function clickDownload(filename, url) {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = h('textarea', { style: 'position:fixed;opacity:0' });
    ta.value = text;
    document.body.append(ta);
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch { /* bỏ qua */ }
    ta.remove();
    return ok;
  }
}

let toastTimer;
export function toast(message) {
  document.querySelector('.toast')?.remove();
  const el = h('div', { class: 'toast', role: 'status' }, message);
  document.body.append(el);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.remove(), 1800);
}
