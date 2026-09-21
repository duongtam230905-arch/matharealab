// Nút nổi liên hệ (góc dưới phải) và chân trang đầy đủ. Dữ liệu lấy từ site-config.js.
import { SITE } from './site-config.js';
import { copyText, h, toast } from './utils.js';

function link(cls, href, label, sub) {
  return h('a', { class: `contact-link ${cls}`, href, target: '_blank', rel: 'noopener noreferrer' },
    h('span', { class: 'contact-badge', 'aria-hidden': 'true' }, cls === 'zalo' ? 'Zalo' : 'f'),
    h('span', {}, h('strong', {}, label), h('small', {}, sub)));
}

export function initContact() {
  const pop = h('div', { id: 'contact-pop', class: 'contact-pop', role: 'dialog', 'aria-label': `Liên hệ ${SITE.teacher}`, hidden: true },
    h('div', { class: 'contact-head' },
      h('span', { class: 'contact-avatar', 'aria-hidden': 'true' }, 'T'),
      h('div', {}, h('strong', {}, SITE.teacher), h('small', {}, SITE.title))),
    h('p', {}, SITE.blurb),
    link('zalo', SITE.zaloUrl, 'Nhắn Zalo', SITE.phoneDisplay),
    link('fb', SITE.facebookUrl, 'Facebook', SITE.facebookName),
    h('div', { class: 'contact-row' },
      h('a', { class: 'btn ghost small', href: `tel:${SITE.phone}` }, 'Gọi điện'),
      h('button', { type: 'button', class: 'btn ghost small', onclick: async () => {
        toast((await copyText(SITE.phone)) ? 'Đã sao chép số điện thoại' : 'Không sao chép được');
      } }, 'Sao chép SĐT')));

  const fab = h('button', { type: 'button', class: 'fab', 'aria-expanded': 'false', 'aria-controls': 'contact-pop' },
    h('span', { class: 'fab-avatar', 'aria-hidden': 'true' }, 'T'),
    h('span', { class: 'fab-text' }, `Liên hệ ${SITE.teacher}`));

  const setOpen = (open) => {
    pop.hidden = !open;
    fab.setAttribute('aria-expanded', String(open));
  };
  fab.addEventListener('click', (e) => { e.stopPropagation(); setOpen(pop.hidden); });
  document.addEventListener('click', (e) => { if (!pop.hidden && !pop.contains(e.target)) setOpen(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') setOpen(false); });

  document.body.append(h('div', { class: 'fab-wrap' }, pop, fab));

  const footer = document.getElementById('site-footer');
  if (footer) {
    footer.replaceChildren(
      h('div', { class: 'foot-grid' },
        h('div', {},
          h('strong', { class: 'foot-brand' }, 'AreaLab'),
          h('p', {}, 'Công cụ trực quan hóa và tính diện tích hình phẳng bằng tích phân.'),
          h('p', { class: 'foot-small' }, 'Tính toán bằng SymPy · đồ thị Plotly · công thức KaTeX. Hàm lượng giác dùng đơn vị radian.')),
        h('div', {},
          h('strong', {}, `${SITE.teacher} – ${SITE.title}`),
          h('ul', { class: 'foot-contact' },
            h('li', {}, 'Facebook: ', h('a', { href: SITE.facebookUrl, target: '_blank', rel: 'noopener noreferrer' }, SITE.facebookName)),
            h('li', {}, 'Zalo: ', h('a', { href: SITE.zaloUrl, target: '_blank', rel: 'noopener noreferrer' }, SITE.phoneDisplay)),
            h('li', {}, 'Điện thoại: ', h('a', { href: `tel:${SITE.phone}` }, SITE.phoneDisplay))))),
      h('p', { class: 'foot-copy' }, `© ${new Date().getFullYear()} AreaLab · ${SITE.teacher}`));
  }
}
