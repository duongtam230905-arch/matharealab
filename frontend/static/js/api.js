// Lớp gọi API. Mọi lỗi được chuẩn hoá thành {code, message, detail, stage}.

function normalizeError(data, status) {
  if (data && typeof data.error === 'string') return { code: 'server', message: data.error, detail: data.log || null };
  if (data && data.error && typeof data.error === 'object') return data.error;
  if (data && Array.isArray(data.detail)) return { code: 'validation', message: 'Dữ liệu nhập chưa hợp lệ.\nVui lòng kiểm tra lại các ô nhập.' };
  return { code: 'unknown', message: `Đã xảy ra lỗi (mã ${status}). Vui lòng thử lại.` };
}

async function request(path, options) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw { code: 'network', message: 'Không kết nối được máy chủ.\nHãy kiểm tra mạng rồi thử lại.' };
  }
  let data = null;
  try { data = await res.json(); } catch { /* xử lý bên dưới */ }
  if (!res.ok || !data || data.ok === false) throw normalizeError(data, res.status);
  return data;
}

export const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export const get = (path) => request(path, { method: 'GET' });
