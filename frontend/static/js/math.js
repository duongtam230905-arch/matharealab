// Hiển thị công thức bằng KaTeX; nếu KaTeX chưa tải thì hiện mã LaTeX thô.

export function tex(latex, display = true) {
  const el = document.createElement(display ? 'div' : 'span');
  el.className = display ? 'math' : 'math-inline';
  if (window.katex) {
    try {
      window.katex.render(latex, el, { displayMode: display, throwOnError: false, strict: 'ignore' });
      return el;
    } catch { /* rơi xuống hiển thị thô */ }
  }
  el.textContent = latex;
  return el;
}

/** Dựng chuỗi văn bản có chứa $...$ thành một phần tử <p>. */
export function richText(text, tag = 'p') {
  const el = document.createElement(tag);
  el.textContent = text;
  typeset(el);
  return el;
}

export function typeset(root) {
  if (!window.renderMathInElement) return;
  try {
    window.renderMathInElement(root, {
      delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }],
      throwOnError: false,
      strict: 'ignore',
    });
  } catch { /* bỏ qua */ }
}
