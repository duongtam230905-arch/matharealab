// Hiệu ứng chuyển động tinh tế. Tất cả tự tắt khi hệ điều hành bật "giảm chuyển động".

export const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/** Các phần tử có class .reveal hiện dần (trượt nhẹ lên) khi cuộn tới. */
export function initReveal(root = document) {
  const els = [...root.querySelectorAll('.reveal:not(.in)')];
  if (reduced() || !('IntersectionObserver' in window)) {
    els.forEach((e) => e.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        en.target.classList.add('in');
        io.unobserve(en.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });
  els.forEach((e, i) => {
    e.style.setProperty('--d', `${Math.min(i, 6) * 70}ms`);
    io.observe(e);
  });
}

/** Số chạy từ 0 đến giá trị cuối; chữ cuối cùng luôn là finalText (đúng từng chữ số). */
export function countUp(el, to, finalText, ms = 950) {
  cancelAnimationFrame(el._raf);
  const decimals = (finalText.split('.')[1] || '').length;
  if (reduced() || !Number.isFinite(to)) { el.textContent = finalText; return; }
  const t0 = performance.now();
  const frame = (now) => {
    const t = Math.min(1, (now - t0) / ms);
    const e = 1 - Math.pow(1 - t, 3);
    el.textContent = t < 1 ? (to * e).toFixed(decimals) : finalText;
    if (t < 1) el._raf = requestAnimationFrame(frame);
  };
  el._raf = requestAnimationFrame(frame);
}

/** Thanh gạch chân trượt mượt dưới tab đang chọn. */
export function moveInk(tabs) {
  const ink = tabs.querySelector('.tab-ink');
  const sel = tabs.querySelector('[aria-selected="true"]');
  if (!ink || !sel) return;
  ink.style.width = `${sel.offsetWidth}px`;
  ink.style.transform = `translateX(${sel.offsetLeft}px)`;
}
