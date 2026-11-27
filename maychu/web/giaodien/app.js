// IGM360 giao diện: màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt, 13 Mô hình AI, 08 Trò chuyện AI (bản vẽ đã duyệt
// QĐ88, QĐ94; icon theo từ điển QĐ91; chặn đoán mật khẩu, phiên 30 ngày QĐ90).
// Cách bật tắt khối theo trạng thái (data-s) giữ như bản vẽ; số liệu lấy từ máy chủ.
'use strict';
const S = {g: '01', dn: 'matkhau', k: 'binhthuong', trang: '03', tab: 'chung', nhom: 'Tài chính', cdMan: 1, cn: 'moinhat', xem: 'dt', thu: 0, tc: 'rong', lv: null};
const $ = (q, r = document) => r.querySelector(q), $$ = (q, r = document) => [...r.querySelectorAll(q)];
const D = {thongso: null, maTam: '', maTamDoiMay: '', xnCb: null, suaK: '', capnhat: null, hetLuc: null, khoaDen: 0,
  md: null, dn: {}, trung: {}, ht: [], htId: null, soLuc: ''};
if (window.innerWidth < 700) { S.xem = 'mb'; document.body.classList.add('dien-thoai'); }

// ---- Định dạng: số 1-9 đứng trước danh từ đếm ghi 02 chữ số; ngày dd/mm/yyyy; nghìn ngăn bằng dấu chấm
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);
const soVN = v => { const n = Number(v); if (!Number.isFinite(n)) return v;
  if (Number.isInteger(n) && n < 10) return hai(n);
  const [a, b] = String(n).split('.'); return a.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (b ? ',' + b : ''); };
// QĐ636 (D-a): giờ hiện theo múi đã chọn (③). Máy chủ lưu giờ +07:00; chuỗi chỉ có ngày (② ngày số liệu) hiện nguyên.
let MUI = 'Asia/Ho_Chi_Minh', _MUI_F = null;   // múi lấy ở /api/toi
const theoMui = t => { const ms = typeof t === 'number' ? t : Date.parse(t); if (Number.isNaN(ms)) return String(t ?? ''); if (!_MUI_F || _MUI_F.tz !== MUI) _MUI_F = {tz: MUI, f: new Intl.DateTimeFormat('en-CA', {timeZone: MUI, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'})}; const p = Object.fromEntries(_MUI_F.f.formatToParts(ms).map(x => [x.type, x.value])); return p.year + '-' + p.month + '-' + p.day + 'T' + p.hour + ':' + p.minute + ':' + p.second; };
const hien = iso => !iso || !/(Z|[+-]\d\d:\d\d)$/.test(String(iso)) ? String(iso ?? '') : theoMui(iso);   // chuỗi giờ lưu (có độ lệch) → "YYYY-MM-DDTHH:MM:SS" theo múi đã chọn; chuỗi ngày, chuỗi đã đổi: giữ nguyên
const ngay = iso => { if (!iso) return ''; const [y, m, d] = hien(iso).slice(0, 10).split('-'); return d + '/' + m + '/' + y; };
const gio = iso => iso ? hien(iso).slice(11, 16) : '';
const homNay = () => theoMui(Date.now()).slice(0, 10);
const luc = iso => !iso ? '' : (hien(iso).slice(0, 10) === homNay() ? gio(iso) + '\u00a0hôm\u00a0nay' : ngay(iso) + ' · ' + gio(iso));
const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
// Không tách cụm từ khi xuống dòng (chữ do máy chủ gửi): nối các cụm thường gặp bằng dấu cách không ngắt
// U4 (S1, S3): cụm "mục + tên màn" dài hơn đặt trước để nối trước khi cụm ngắn hơn được nối.
const CUM = ['Việc nền', 'mục Chờ duyệt', 'mục Két khóa', 'mục Bộ mã chung', 'mục Nguồn dữ liệu', 'mục Mô hình AI', 'giai đoạn', 'giá trị', 'ứng dụng', 'gấp đôi', 'tài khoản', 'mật khẩu', 'phần mềm', 'sao lưu', 'trò chuyện',
  'đăng nhập', 'cập nhật', 'khóa API', 'Google Drive', 'tỷ giá', 'hạn mức', 'nguồn AI', 'việc AI', 'thông số', 'mỗi ngày',
  'bản mới', 'máy chủ', 'Chờ duyệt', 'Két khóa', 'đề xuất', 'chờ bạn', 'tự áp dụng', 'thao tác', 'hằng ngày', 'quy đổi',
  'tham khảo', 'ưu tiên', 'gì mới', 'Cài đặt', 'Thông số', 'dự phòng', 'cài máy',
  'Mở trang', 'TikTok Shop', 'mã sàn'];   // N12, T1
CUM.push('trả về', 'giữ được', 'an toàn', 'bản sao Drive');   // Y38d N35: câu 25, 30, 40 không ngắt giữa cụm
CUM.push('Khóa API', 'khởi động', 'chưa được', 'Dữ liệu', 'dữ liệu');   // Y38f U14 L1 (A1), L2 (A6, A7)
// Số luôn đi liền chữ đứng sau (04 dòng, 1.240 dòng); "tài khoản 01", "ưu tiên 2", "bản 0.5.0", "02 lớp" không tách.
const cum = s => { let r = esc(s).replace(/(?<![\p{L}\d])(\d+(?:[.,]\d+)*) (?=\p{L})/gu, '$1&nbsp;');
  CUM.forEach(c => { r = r.split(c).join(c.replace(/ /g, '&nbsp;')); });
  return r.replace(/(khoản|tiên|[Bb]ản|lớp) (\d)/g, '$1&nbsp;$2').replace(/ (›|·) /g, '&nbsp;$1 '); };
const cau = s => /[.!?…]$/.test(String(s).trim()) ? s : s + '.';   // câu báo lỗi luôn có dấu chấm cuối (N12)

// ---- Gọi máy chủ
async function api(duong, than) {
  let r;
  if (duong === '/trochuyen' && than) than = {...than, nen: true};   // N0 (QĐ344, QĐ355): gửi tin trò chuyện luôn mở lượt chạy nền
  try {
    r = await fetch('/api' + duong, {method: than === undefined ? 'GET' : 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-IGM360': '1'}, body: than === undefined ? undefined : JSON.stringify(than)});
  } catch (e) { S.k = 'matketnoi'; ve();   // QĐ361: thay chữ "Failed to fetch" của trình duyệt (dải đỏ giữ như cũ)
    const m = new Error('Mất kết nối máy chủ, thao tác này chưa lưu được. Bạn thử lại khi đã nối\u00a0lại'); m.matKetNoi = true; throw m; }   // SUA-NBSP: "nối lại" không tách 02 dòng
  if (S.k === 'matketnoi') { S.k = 'binhthuong'; }
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && S.g !== '01') { S.g = '01'; S.dn = 'hethan'; ve(); }
  if (!r.ok) { const ct = d.detail; const e = new Error(typeof ct === 'string' ? ct : (ct && ct.loi) || 'Có lỗi');
    e.o = ct && ct.o; e.status = r.status; e.ct = ct; e.ma = d.ma; throw e; }   // N0: mã lỗi riêng (cho_capnhat)
  return d;
}

// ---- Vẽ theo trạng thái (như bản vẽ)
function khop(el) { return el.dataset.s.split(';').every(c => { const i = c.indexOf(':');
  return c.slice(i + 1).split(' ').includes(String(S[c.slice(0, i)])); }); }
function ve() {
  const app = $('#app'); app.className = S.xem + (S.thu ? ' thu' : '');
  const mk = $('#mk-gio'); if (mk) mk.textContent = D.soLuc || '';
  $('#s01').hidden = S.g !== '01'; $('#khung').hidden = S.g === '01';
  $('#s01').classList.toggle('sai', S.dn === 'sai');
  $$('[data-s]').forEach(e => e.hidden = !khop(e));
  $$('.bao, .cham').forEach(e => { if (!e.textContent) e.hidden = true; });
  $$('.trang').forEach(e => e.hidden = e.id !== 'p' + S.trang);
  $$('[data-trang]').forEach(e => e.classList.toggle('on', e.dataset.trang === S.trang));
  $$('.tab').forEach(e => e.classList.toggle('on', e.dataset.tab === S.tab));
  danhDauMenuCd(); const p9 = $('#p09'); if (p9) p9.classList.toggle('man2', S.cdMan === 2);   // điện thoại: màn 2 = khối chi tiết
  $('#tieude-tren').innerHTML = (ICO[S.trang] || '') + '<b class="t16 nw">' + (TEN[S.trang] || '') + '</b>';
  const nutDn = $('[data-dangnhap]');   // 0.8.9 (CDA SOAT-KH-088 điểm 3): "Đang xử lý…" theo S.lv riêng; S.dn giữ 07 giá trị
  nutDn.disabled = S.dn === 'khoa' || S.dn === 'khoatk' || S.lv === 'dang';
  if ((S.lv === 'dang') !== nutDn.classList.contains('dang')) {
    if (S.lv === 'dang') { D.nutDn = nutDn.innerHTML; nutDn.innerHTML = icoMau(ICON.loader, 'var(--chu-tren-nut)', 18).replace('<svg', '<svg aria-hidden="true"') + CHU_DN.dang; }
    else nutDn.innerHTML = D.nutDn;
    nutDn.classList.toggle('dang', S.lv === 'dang'); }
  if (S.g === '01') dongTacLv();   // 0.8.9: linh vật màn 01
  doiViTri();   // 0.9.0 (QĐ387): chuông + tài khoản dưới logo ở khổ máy tính
  veNhom();   // Y52: thu gọn nhóm thanh trái
}
// 0.9.0 (QĐ387, khung ii-c2): khổ máy tính bỏ thanh trên, khối chuông + tài khoản (.vi-tri) đặt ngay dưới logo; điện thoại giữ ở thanh trên.
function doiViTri() {
  const vt = $('.vi-tri'), lg = $('nav.menu .logo'), tt = $('.thanh-tren'); if (!vt || !lg || !tt) return;
  const vg = $('#app .vung');   // QĐ548 B: máy tính – góc phải khung nội dung
  if (S.xem !== 'mb' && vg && vt.parentElement !== vg) vg.prepend(vt);
  else if (S.xem === 'mb' && vt.parentElement !== tt) tt.append(vt);
}
// KH-090 2.2 (c), CDO P1: 02 bảng thả xuống mở từ cột menu nổi trên cùng (position: fixed), mép trái 08 px, ngay dưới chuông.
function datTha(e, nut) {   // bảng nổi: canh mép phải nút góc phải khung; menu tài khoản mở sang phải mục "Tài khoản" ở thanh trái
  if (S.xem === 'mb' || e.hidden) { e.style['top'] = e.style['left'] = ''; return; }
  const n = (nut || $('[data-chuong]')).getBoundingClientRect();
  if (nut && nut.closest('nav.menu')) { e.style['left'] = Math.round(n.right + 6) + 'px'; e.style['top'] = Math.round(Math.max(8, Math.min(n['top'] - 60, innerHeight - e.offsetHeight - 8))) + 'px'; }
  else { e.style['left'] = Math.round(Math.max(8, n.right - e.offsetWidth)) + 'px'; e.style['top'] = Math.round(n.bottom + 6) + 'px'; }
}
function dongTha() { $$('.tha').forEach(e => e.hidden = true); }
function dongHop() { $$('.lop').forEach(e => e.hidden = true); }
function mo(id) { dongTha(); $('#' + id).hidden = false; }
// <NHOM> Y52 (QĐ321–QĐ331, QĐ332; bản vẽ Z27 · U40): thu gọn 05 nhóm thanh trái, chỉ khổ máy tính (QĐ329).
// L1 A: 01 nhóm mở 1 lúc, bấm lại thì gập · L2 A: mở trang thì nhóm chứa trang tự mở; anh tự gập thì tiêu đề tô xanh ·
// L3 A: nhóm gập hiện số báo ở tiêu đề, giữ màu, rê chuột "<tên mục>: <số>" · L4 A: thu cả thanh giữ như nay ·
// L5 B: nhóm 01 mục ("Trò chuyện AI") đứng riêng, bỏ tiêu đề · không lưu (QĐ327) · không câu rê chuột ở tiêu đề (QĐ330).
// L6 (cuộn riêng) KHÔNG làm ở bản này: đi cùng QĐ317 B1.
const NHOM = {ds: [], mo: new Set(), trangCu: null};
// Hàm thuần (bài kiểm chạy bằng node): ds = [{ten, so: số mục, bao: [{ten, so, do}]}], mo = tên nhóm đang mở, cur = nhóm
// chứa trang đang mở → [{ten, rieng, mo, coTrang, bao}].
const tinhNhom = (ds, mo, cur) => ds.map(g => { const rieng = g.so === 1, m = rieng || mo.has(g.ten);
  return {ten: g.ten, rieng, mo: m, coTrang: !m && g.ten === cur, bao: m ? [] : g.bao}; });
const nhomCua = tr => NHOM.ds.find(g => g.ds.querySelector('[data-trang="' + tr + '"]'));
function dungNhom() {   // gom mục của mỗi tiêu đề vào 01 khối, tiêu đề thành nút (01 lần)
  const nav = $('nav.menu'); if (!nav || NHOM.ds.length) return;
  [...nav.querySelectorAll(':scope > .nhom')].forEach(h => {
    const ten = h.textContent.trim(), ds = document.createElement('div'); ds.className = 'nhom-ds';
    let n = h.nextElementSibling;
    while (n && n.classList.contains('muc') && !n.classList.contains('thu-gon')) { const x = n.nextElementSibling; ds.appendChild(n); n = x; }
    const b = document.createElement('button'); b.type = 'button'; b.className = 'nhom nhom-nut'; b.dataset.nhomNut = ten;
    b.innerHTML = '<span class="nhom-ten">' + esc(ten) + '</span><span class="nhom-bao"></span><span class="nhom-mt"></span>';
    h.replaceWith(b); b.after(ds); NHOM.ds.push({ten, b, ds});
  });
  const c = nhomCua(S.trang); NHOM.mo = new Set(c ? [c.ten] : []); NHOM.trangCu = S.trang;
}
const muiTen = mo => ICON[mo ? 'chevron-down' : 'chevron-right'].replace(/color:[^;"]*/, 'color:var(--phu)')
  .replace(/width="\d+"/, 'width="14"').replace(/height="\d+"/, 'height="14"');   // QĐ331
function veNhom() {
  if (!NHOM.ds.length) dungNhom();
  if (!NHOM.ds.length) return;
  const cur = nhomCua(S.trang);
  if (S.trang !== NHOM.trangCu) { NHOM.trangCu = S.trang; if (cur) NHOM.mo = new Set([cur.ten]); }   // L2 A
  const kq = tinhNhom(NHOM.ds.map(g => ({ten: g.ten, so: g.ds.querySelectorAll(':scope > .muc').length,
    bao: [...g.ds.querySelectorAll('.bao')].filter(x => !x.hidden && x.textContent.trim())
      .map(x => ({ten: x.closest('.muc').title, so: x.textContent.trim(), do: x.classList.contains('do')}))})),
  NHOM.mo, cur && cur.ten);
  NHOM.ds.forEach((g, i) => { const k = kq[i];
    g.b.hidden = k.rieng; g.ds.classList.toggle('rieng', k.rieng); g.ds.classList.toggle('gap', !k.mo);
    g.b.classList.toggle('co-trang', k.coTrang); g.b.setAttribute('aria-expanded', String(k.mo));
    g.b.querySelector('.nhom-mt').innerHTML = muiTen(k.mo);
    g.b.querySelector('.nhom-bao').innerHTML = k.bao.map(x => '<span class="bao' + (x.do ? ' do' : '') + '" title="'
      + esc(x.ten + ': ' + x.so) + '">' + esc(x.so) + '</span>').join(''); });   // L3 A
}
function batNhom(ten) { if (NHOM.mo.has(ten)) NHOM.mo.delete(ten); else { NHOM.mo.clear(); NHOM.mo.add(ten); } veNhom(); }   // L1 A
// </NHOM>
function bao(t) { const e = $('#tb-msg'); e.textContent = t; e.hidden = false; clearTimeout(bao.h); bao.h = setTimeout(() => e.hidden = true, 3200); }
function xacnhan(tieu, chu, nut, cb, ico) { const dau = $('#h-xacnhan .hop-dau svg');
  if (dau) { if (!xacnhan.goc) xacnhan.goc = dau.outerHTML; dau.outerHTML = ico ? icoMau(ICON[ico], 'var(--xanh-chu)', 20) : xacnhan.goc; }
  $('#h-xacnhan [data-tieu]').textContent = tieu; $('#xn-chu').innerHTML = chu;
  $('#xn-nut').textContent = nut; D.xnCb = cb; mo('h-xacnhan'); }
const ma6 = goc => $$('.o6', goc).map(i => i.value).join('');
const xoa6 = goc => $$('.o6', goc).forEach(i => i.value = '');

// ---- Màn 01
function hienLoiDn(t, con) { $('#dn-loi').textContent = t; $('#dn-con').textContent = con == null ? '' : hai(con);
  $('#dn-con-cau').hidden = con == null; S.dn = 'sai'; ve(); }
const gioPhut = sec => { const d = theoMui(sec * 1000); return d.slice(11, 16) + (d.slice(0, 10) === homNay() ? '' : ' ngày ' + ngay(d)); };
function hienKhoa(k) {
  S.dn = k.loai === 'taikhoan' ? 'khoatk' : 'khoa'; D.khoaDen = k.den;
  $('#k-thoigian').textContent = k.phut < 60 ? hai(k.phut) + ' phút' : hai(k.phut / 60) + ' giờ';
  $$('.k-luc').forEach(e => e.textContent = gioPhut(k.den)); ve();
}
function loiDangNhap(e, oMa) {
  if (e.status === 429) { hienKhoa(e.ct); return; }
  const con = e.ct && e.ct.con_lai;
  if (oMa) { bao(e.message + (con != null ? ' Còn ' + hai(con) + ' lần thử.' : '')); return; }
  hienLoiDn(e.message, con);
}
async function dangNhap() {
  const ten = $('#dn-ten').value.trim(), mk = $('#mk').value;
  if (!ten || !mk) { hienLoiDn('Bạn nhập tên đăng nhập và mật khẩu.', null); return; }
  if (S.lv === 'dang') return;
  S.lv = 'dang'; ve();   // 0.8.9: nút "Đang xử lý…", linh vật đang làm; mọi nhánh (cả mất kết nối) trả lại ở finally
  try {
    const kq = await api('/dangnhap', {ten, matkhau: mk});
    D.maTam = kq.ma_tam; $('#mk').value = '';
    if (kq.buoc === 'vao') { S.lv = 'xong'; ve(); await vaoPhanMem(); return; }   // QĐ390: 02 lớp đang tắt, máy chủ đã đặt cookie
    if (kq.buoc === 'bat2lop') { $('#qr-2lop').innerHTML = kq.qr_svg; S.dn = 'batdau2lop'; } else S.dn = 'ma2lop';
    ve(); const o = $('[data-s="dn:' + S.dn + '"] .o6'); if (o) o.focus();
  } catch (e) { if (e.status) loiDangNhap(e, false); }
  finally { S.lv = null; ve(); }
}
async function xacNhanMa(nut) {
  const goc = nut.closest('[data-s]'), ma = ma6(goc);
  if (ma.length !== 6) { bao('Bạn nhập đủ 06 số.'); return; }
  try {
    await api('/dangnhap/ma2lop', {ma_tam: D.maTam, ma});
    S.lv = 'xong'; ve();   // 0.8.9: linh vật xong việc, không thêm thời gian chờ
    if (nut.dataset.xacnhan === 'bat') bao('Đã bật đăng nhập 02 lớp.');
    xoa6(goc); $('#qr-2lop').innerHTML = ''; await vaoPhanMem();
  } catch (e) { xoa6(goc); if (e.status === 429) { hienKhoa(e.ct); return; }
    if (/hết hạn/.test(e.message)) { S.dn = 'hethan'; ve(); bao(e.message); return; } loiDangNhap(e, true); }
  finally { S.lv = null; ve(); }
}

// <LINHVAT> 0.8.9 (QĐ364, QĐ368, QĐ371): linh vật màn 01 đổi động tác theo S.lv || S.dn; chào mừng 01 lần khi màn 01 hiện.
// Giảm chuyển động hoặc máy yếu (CDA SOAT-KH-088 2a) → lớp .tinh trên #s01, bỏ chào mừng. Lỗi ở đây không chặn ve() (L3 d).
const CHU_DN = {hien: 'Hiện mật khẩu', an: 'Ẩn mật khẩu', dang: 'Đang xử lý…'};   // bảng chữ QĐ369 (6); quy chuẩn 5.1
const LV = {matkhau: 'cho', dang: 'danglam', sai: 'loi', khoa: 'loi', khoatk: 'loi', hethan: 'loi', ma2lop: 'chay', batdau2lop: 'chay', xong: 'xong'};
const lvTinh = () => matchMedia('(prefers-reduced-motion: reduce)').matches || navigator.hardwareConcurrency <= 2
  || (navigator.deviceMemory > 0 && navigator.deviceMemory <= 2);
const LVC = {pha: '', da: false};   // chào mừng: 'vao' (0–1,8 giây) → 'chao' (1,8–3,6 giây) → đứng chờ
function dongTacLv() {
  try {
    const s01 = $('#s01'), tinh = lvTinh(); s01.classList.toggle('tinh', tinh);
    if (!LVC.da) { LVC.da = true;
      if (!tinh) { LVC.pha = 'vao'; setTimeout(() => { LVC.pha = 'chao'; dongTacLv(); }, 1800); setTimeout(() => { LVC.pha = ''; dongTacLv(); }, 3600); } }
    const dt = LVC.pha && !S.lv && S.dn === 'matkhau' ? LVC.pha : (LV[S.lv || S.dn] || 'cho');
    $$('.lv-o', s01).forEach(o => { o.className = 'lv-o lv-xanh dt-' + dt; });
  } catch (e) { /* linh vật lỗi: bỏ qua, ô đăng nhập vẫn dùng được */ }
}
addEventListener('pointermove', e => { const s01 = $('#s01');   // phông nền: lớp xa – gần lệch theo con trỏ (chỉ màn 01, không tĩnh)
  if (S.g !== '01' || !s01 || s01.classList.contains('tinh')) return;
  s01.style.setProperty('--mx', (e.clientX / innerWidth - .5).toFixed(3)); s01.style.setProperty('--my', (e.clientY / innerHeight - .5).toFixed(3)); });
// </LINHVAT>

// ---- Màn 02
const DAU_SAU_CN = '#sau-capnhat';   // dấu trên địa chỉ trang khi tự tải lại sau cập nhật (CDO U21 G1)
async function vaoPhanMem() {
  const toi = await api('/toi');
  const chu = (toi.ten || toi.ten_dangnhap || '').trim();
  $('#tk-chu').textContent = chu.slice(0, 1).toUpperCase(); $('#tk-ten').textContent = chu;
  D.hetLuc = toi.het_luc; S.g = '02'; S.dn = 'matkhau'; if (toi.muigio) MUI = toi.muigio;   // QĐ636
  try { D.anToan = !!(await (await fetch('/suckhoe', {cache: 'no-store'})).json()).an_toan; } catch (e) { D.anToan = false; }
  if (D.anToan) { S.trang = '09'; S.tab = 'capnhat'; ve(); napTab(); return; }   // 0.7.9 lớp 2: chỉ mở Cài đặt › Cập nhật
  if (location.hash === DAU_SAU_CN) {   // CDO U21 G1: vừa tải lại sau cập nhật → mở đúng Cài đặt › Cập nhật để thấy thẻ kết quả
    S.trang = '09'; S.tab = 'capnhat'; history.replaceState(null, '', location.pathname + location.search); }
  ve(); demSo();
  if (S.trang === '09') napTab();
}
// ---- Chuông thông báo bước 1 (QĐ165, bản vẽ Z7b): số = dòng Mới (sau mốc đọc); nhóm Mới rồi Đã xem, còn mở
const MAU_TB = {do: ['do-n', 'var(--canh)'], xem: ['xem-n', 'var(--xem)'], tin: ['tin-n', 'var(--xanh-chu)']};
const lucTb = iso => { if (!iso) return ''; const h = homNay(), q = new Date(Date.parse(h) - 86400e3).toISOString().slice(0, 10), d = hien(iso).slice(0, 10);
  return d === h ? gio(iso) : d === q ? 'Hôm qua ' + gio(iso) : d.slice(8, 10) + '/' + d.slice(5, 7); };
const icoTb = x => (ICON[x.icon] || ICON['circle-alert']).replace(/width="\d+"/, 'width="16"').replace(/height="\d+"/, 'height="16"')
  .replace(/color:[^;"]*/, 'color:' + MAU_TB[x.muc][1]);
const dongTb = x => '<button class="tha-muc tb-dong' + (x.moi ? ' moi' : '') + '" data-di="' + esc(x.di) + '"' + (x.cuon ? ' data-cuon="' + esc(x.cuon) + '"' : '') + '><span class="tl-cham" aria-hidden="true"></span><span class="ico-tron nho '
  + MAU_TB[x.muc][0] + '">' + icoTb(x) + '</span><span class="f1 trai"><span class="b6 t13 khoi">' + cum(x.chu) + '</span>' + (dong2Tb(x) ? '<span class="t13 khoi">' + esc(dong2Tb(x)) + '</span>' : '') + '<span class="t12 phu">'
  + esc(lucTb(x.luc)) + ' · ' + esc(x.noi) + '</span></span></button>';
// QĐ662 dòng 2 tin đổi tên miền / múi giờ: "cũ → mới"; tên múi theo QĐ652 (tên nước tiếng Việt do trình duyệt dịch từ mã nước)
const nuocVi = cc => { try { return cc ? new Intl.DisplayNames(['vi'], {type: 'region'}).of(cc) : ''; } catch (e) { return ''; } };
const tenMuiTb = (tz, qg) => tz === 'Asia/Ho_Chi_Minh' ? CHU_MG.vn : (nuocVi((qg || {})[tz]) ? nuocVi(qg[tz]) + ' – ' : '') + thanhPho(tz) + ' (' + lechMui(tz) + ')';
const dong2Tb = x => x.mg ? tenMuiTb(x.mg[0], x.qg) + ' → ' + tenMuiTb(x.mg[1], x.qg) : x.phu || '';
function veChuong(d) {   // QĐ553 (3): 02 thẻ Thông báo · Cần xử lý, chấm chưa đọc, "Hiện N tin đã đọc", chân bảng số bản + Có gì mới
  D.tbCuoi = d; const ds = d.thongbao || [], tat = !!d.tamtat, so = d.so_moi || 0;
  if (D.tbSoMoi !== undefined && so > D.tbSoMoi && amBat() && (!tat || ds.some(x => x.moi && x.muc === 'do'))) keuChuong();   // QĐ551: tạm tắt vẫn kêu tin nghiêm trọng
  D.tbSoMoi = so; D.tbTamTat = tat; D.tbCoDo = ds.some(x => x.moi && x.muc === 'do'); if (d.ban) D.tbBan = d.ban; veBa();
  const e = $('#tha-chuong'); if (!e) return;
  const the = D.tbThe || 'tb', loc = the === 'cxl' ? ds.filter(x => x.muc === 'do') : ds, moi = loc.filter(x => x.moi), cu = loc.filter(x => !x.moi);
  e.innerHTML = '<div class="tha-dau tl-dau"><b>' + CHU_BA.thongBao + '</b><button class="tl-nutchu" data-tamtat>' + icoMau(ICON[tat ? 'bell' : 'bell-off'], 'currentColor', 16)
      + (tat ? CHU_BA.moLai : CHU_BA.tamTat) + '</button>' + (ds.some(x => x.moi) ? '<button class="tl-nutchu x" id="tb-dochet" data-dochet>' + icoMau(ICON.check, 'currentColor', 16)
      + CHU_BA.docHet + '</button>' : '') + '</div>'
    + (tat ? '<div class="tl-dai" role="status">' + icoMau(ICON['bell-off'], 'var(--xem)', 18) + '<span class="nd3">' + cum(CHU_BA.daiTat) + '</span><button class="tl-nutchu x" data-tamtat>'
      + CHU_BA.moLai + '</button></div>' : '')
    + '<div class="tl-the" role="tablist">' + [['tb', CHU_BA.thongBao, ds.filter(x => x.moi).length], ['cxl', CHU_BA.canXl, ds.filter(x => x.moi && x.muc === 'do').length]]
      .map(([k, t, n]) => '<button role="tab" aria-selected="' + (k === the) + '"' + (k === the ? ' class="on"' : '') + ' data-tbthe="' + k + '">' + t + (n ? ' <i>' + hai(n) + '</i>' : '') + '</button>').join('') + '</div>'
    + '<div class="tb-ds" id="chuong-ds">' + (!loc.length ? '<div class="tb-rong"><span class="ico-tron">' + icoMau(ICON.bell, 'var(--phu)', 20) + '</span><span class="t13 phu">' + CHU_BA.rong + '</span></div>'
      : moi.map(dongTb).join('') + (cu.length ? (D.tbHienDoc ? cu.map(dongTb).join('') : '<button class="tl-hien" data-tbhien>' + CHU_BA.hienDoc(hai(cu.length)) + '</button>') : '')) + '</div>'
    + '<div class="tl-chan">IGM360 ' + esc(D.tbBan || '') + '<button data-di="capnhat">' + CHU_BA.coGiMoi + '</button></div>';
}
// Tự cập nhật số mỗi 60 giây khi phần mềm đang mở (hỏi lại máy chủ, 0 thư viện)
setInterval(() => { if (S.g !== '01' && document.visibilityState === 'visible') lamMoi13(), demSo(); }, 60e3);   // 01 vòng 60 giây
// QĐ192 (0.7.7): màn Mô hình AI tự làm mới số hạn mức mỗi 60 giây; không làm mới khi anh đang đăng nhập dở, đang mở hộp,
// hoặc đang gõ trong màn (để không mất chữ đang gõ)
function lamMoi13() {
  if (S.trang !== '13' || !D.md) return;
  if (Object.values(D.dn || {}).some(x => x && x.url)) return;
  if (Object.values(D.mdh || {}).some(x => x) || D.mdDan) return;   // 0.7.8: đang lấy mã, dán mã dài hạn
  if ($$('.lop').some(e => !e.hidden)) return;
  const a = document.activeElement; if (a && a.closest && a.closest('#p13') && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) return;
  napMoHinh();
}
async function demSo(mo) {
  try {
    const d = await api('/demso' + (mo ? '?mo=1' : ''));   // QĐ174: mở chuông thì dò bản mới nếu kết quả đã cũ
    $$('[data-trang="05"] .bao').forEach(b => { b.textContent = d.cuacho ? soVN(d.cuacho) : ''; b.hidden = !d.cuacho; });
    $$('[data-trang="10"] .bao, [data-them] .bao').forEach(g => { g.textContent = d.ket_ai ? soVN(d.ket_ai) : ''; g.hidden = !d.ket_ai; });
    veNhom();   // Y52 L3: số báo ở tiêu đề nhóm gập theo số mới
    D.soLuc = theoMui(Date.now()).slice(11, 16);
    veChuong(d);
  } catch (e) { /* mất kết nối đã hiện dải báo */ }
}

// ---- Màn 09 ngăn Thông số
// ---- Màn 09 khung Cài đặt B (QĐ573; menu 05 ngăn đã có nội dung – Thông báo, Mức dùng thêm ở bước của chúng; icon QĐ653)
const NGAN_CD = [['chung', 'monitor-cog', 'Chung'], ['thongso', 'sliders-horizontal', 'Thông số'],
  ['taikhoan', 'user-round', 'Tài khoản và 02\u00a0lớp'], ['capnhat', 'cloud-download', 'Cập nhật'], ['ketkhoa', 'vault', 'Két khóa']];
const NHOM_CD = ['Tài chính', 'Máy chủ, sao lưu', 'AI', 'Báo cáo, dữ liệu'];   // QĐ586 (nhóm Bộ não ẩn ở 0.10.0 – L16)
const demChua = n => D.thongso ? D.thongso.thongso.filter(t => t.nhom === n && !giaiDoanSau(t) && !hienGt(t)).length : 0;
function veMenuCd() {
  const m = $('#cd-menu'); if (!m) return;
  m.innerHTML = '<div class="cd-mtc">' + NGAN_CD.map(([k, ic, ten]) => '<button class="cd-mm" data-tab="' + k + '">' + icoMau(ICON[ic], 'var(--phu)', 16)
    + '<span>' + ten + '</span>' + (k === 'capnhat' && D.coBanMoi ? '<span class="cham-xanh"></span>' : '') + '</button>'
    + (k === 'thongso' ? NHOM_CD.map(n => '<button class="cd-mm cd-con" data-tab="thongso" data-nhom="' + n + '"><span>' + n + '</span>'
      + (demChua(n) ? '<span class="cd-sv">' + hai(demChua(n)) + '</span>' : '') + '</button>').join('') : '')).join('') + '</div>';
  danhDauMenuCd();
}
function danhDauMenuCd() {   // ngăn đang mở: nền --xam + chữ, icon --xanh-chu (QĐ575: không vạch trái); trang gom tô "Thông số" (QĐ583)
  $$('#cd-menu [data-tab]').forEach(e => e.classList.toggle('on', e.dataset.tab === S.tab
    && (S.tab !== 'thongso' || (S.nhom === 'gom' ? !e.dataset.nhom : e.dataset.nhom === S.nhom))));
  const loc = $('[data-loc-chua]'); if (loc) loc.classList.toggle('on', S.tab === 'thongso' && S.nhom === 'gom');
  const kd = $('#cd-ten'); if (!kd) return;
  const ngan = NGAN_CD.find(x => x[0] === S.tab) || NGAN_CD[0], ts = S.tab === 'thongso';
  const ten = ts ? (S.nhom === 'gom' ? 'Thông số chưa đặt' : S.nhom) : ngan[2];
  const ic = ts ? (S.nhom === 'gom' ? 'filter' : NHOM_ICO[S.nhom]) : ngan[1];
  $('#cd-ic').innerHTML = ICON[ic] ? icoMau(ICON[ic], 'var(--xanh-chu)', 18) : '';
  const lui = $('[data-cd-lui]'); if (lui && !lui.firstChild) lui.innerHTML = icoMau(ICON['chevron-left'], 'var(--xanh-chu)', 20);
  kd.innerHTML = ten;
  const n = !ts || !D.thongso ? 0 : S.nhom === 'gom' ? NHOM_CD.reduce((a, x) => a + demChua(x), 0)
    : D.thongso.thongso.filter(t => t.nhom === S.nhom && !giaiDoanSau(t)).length;
  $('#cd-dem').textContent = n ? hai(n) + ' thông số' : '';
}
const NHOM_ICO = {'Tài chính': 'nhom0', 'Máy chủ, sao lưu': 'nhom1', 'AI': 'nhom2', 'Báo cáo, dữ liệu': 'nhom3'};
const giaiDoanSau = t => /^Từ GĐ \d/.test(t.khong_sua || '');
const hienGt = t => t.giatri_chu === null || t.giatri_chu === '' ? null
  : ((t.kieu === 'so' ? soVN(t.giatri_chu) : t.giatri_chu) + (t.donvi && t.kieu === 'so' ? ' ' + t.donvi : ''));
function veThongSo() {
  const d = D.thongso, nhom = {};
  d.thongso.forEach(t => (nhom[t.nhom] = nhom[t.nhom] || []).push(t));
  $('#ts-dem').innerHTML = '<b>' + hai(d.da_dat) + '/' + hai(d.tong) + '</b> đã đặt';   // QĐ580 hàng 2
  $('#ts-thanh').style.width = (100 * d.da_dat / (d.tong || 1)).toFixed(1) + '%';
  const chua = d.tong - d.da_dat; $('#ts-chua').textContent = chua ? hai(chua) + ' thông số bạn chưa đặt' : 'Bạn đã đặt đủ thông số';
  const dong = t => { const gt = hienGt(t);
      if (t.cong_tac) return veCongTac(t, d);
      return '<div class="ts' + (gt ? '' : ' chua') + '"><div class="ts-ten">' + esc(t.nhan)
        + (gt || !t.khi_trong ? '' : '<div class="t12 xem-chu">' + cum(t.khi_trong) + '</div>') + '</div><div class="ts-phai"><div class="ts-gt">'
        + (gt ? '<span class="b7 so">' + esc(gt) + '</span><span class="t12 phu">Từ ' + ngay(t.hieuluc_tu) + ' · ' + (t.nguoi_dat === 'hethong' ? 'Mặc định' : 'Chủ') + '</span>'
             : '<span class="ttag xem">' + (t.ten === 'nhip_lay_dulieu' ? 'Chưa đặt loại nào' : 'Chưa đặt') + '</span>' + (t.ten === 'nhip_lay_dulieu' ? '' : '<span class="t12 phu">\u00a0</span>'))
        + '</div>' + (t.ten === 'nhip_lay_dulieu' ? '<button class="btn-chu" data-trang="11">Đặt ở Nguồn dữ liệu' + ICON.sangtrang + '</button>'   // QĐ583, QĐ585: icon sau chữ
          : t.khong_sua ? '<span class="t12 phu nw khoa-ts">' + ICON.khoats + esc(t.khong_sua) + '</span>'
          : '<button class="btn-chu" data-sua="' + t.ten + '">' + ICON.pencil + 'Sửa</button>') + '</div></div>'; };
  const sau = tat => tat.filter(giaiDoanSau).map(t => '<div class="dong t12 phu">' + ICON.khoats + '<span>' + cum(t.khong_sua + ': ' + t.nhan + '. ' + (t.khi_trong || '').replace(/^GĐ 1: /, 'GĐ 1 ')) + '</span></div>').join('');
  if (S.nhom === 'gom') {   // QĐ583: trang gom "Thông số chưa đặt" – đủ mục chưa đặt của mọi nhóm, tên nhóm làm tiêu đề
    const co = NHOM_CD.map(ten => [ten, (nhom[ten] || []).filter(t => !giaiDoanSau(t) && !hienGt(t))]).filter(x => x[1].length);   // thứ tự như menu
    $('#ds-thongso').innerHTML = co.map(([ten, ds]) => '<div class="cd-nhom">' + esc(ten) + '</div>' + ds.map(dong).join('')).join('');
  } else { const tat = nhom[S.nhom] || [];
    $('#ds-thongso').innerHTML = tat.filter(t => !giaiDoanSau(t)).map(dong).join('') + sau(tat); }
  veMenuCd();
}
// QĐ278 (Z21 dòng 1–3): công tắc "Sao lưu Google Drive" gạt ngay (không qua hộp "Sửa"), chữ đúng bảng chữ màn 09.
const CHU_Z21 = {tat: 'Tắt', bat: 'Bật', tu: n => 'Từ ' + n, macDinh: ' · Mặc định', banDoi: ' · Bạn đổi',
  chuaNoi: 'Drive chưa nối: bản sao chỉ nằm trên máy chủ.',
  hopTieu: 'Tắt sao lưu Google Drive?', hopChu: 'Bản sao chỉ nằm trên máy chủ. Máy chủ hỏng thì không lấy lại được.', hopNut: 'Tắt'};
function veCongTac(t, d) {
  const bat = t.giatri === '1';
  return '<div class="ts"><div class="ts-ten">' + esc(t.nhan) + (t.giai_thich ? '<div class="t12 phu">' + cum(t.giai_thich) + '</div>' : '')
    + (bat && !d.drive_noi ? '<div class="t12 xem-chu" style="display:flex;align-items:center;gap:4px;margin-top:2px">'   // Z21_02 (QĐ278)
      + icoMau(ICON['cloud-alert'], 'var(--xem)', 13) + '<span>' + cum(CHU_Z21.chuaNoi) + '</span></div>' : '') + '</div><div class="ts-phai"><div class="ts-gt">'
    + '<span class="b7 so">' + (bat ? CHU_Z21.bat : CHU_Z21.tat) + '</span><span class="t12 phu">'
    + (t.hieuluc_tu ? CHU_Z21.tu(ngay(t.hieuluc_tu)) + (t.nguoi_dat === 'hethong' ? CHU_Z21.macDinh : CHU_Z21.banDoi) : ' ') + '</span></div>'
    + '<button class="gat-o nut-gat" data-gat="' + esc(t.ten) + '" role="switch" aria-checked="' + bat + '" aria-label="' + esc(t.nhan) + '">'
    + '<input type="checkbox" tabindex="-1"' + (bat ? ' checked' : '') + '><span class="gat"></span></button></div></div>';
}
async function gatCongTac(ten) {
  const t = D.thongso.thongso.find(x => x.ten === ten), bat = t.giatri !== '1';
  const lam = async () => { try { await api('/thongso/' + encodeURIComponent(ten) + '/gat', {bat}); } catch (e) { if (e.status) bao(e.message + '.'); } await napThongSo(); };
  if (bat) await lam(); else xacnhan(CHU_Z21.hopTieu, cum(CHU_Z21.hopChu), CHU_Z21.hopNut, lam);   // gạt bật thì không hỏi
}
async function napThongSo() { D.thongso = await api('/thongso'); veThongSo(); }
async function moSua(ten) {
  const t = D.thongso.thongso.find(x => x.ten === ten); D.suaK = ten;
  $('#h-sua [data-tieu]').textContent = 'Sửa · ' + t.nhan;
  $('#sua-cu').textContent = hienGt(t) || 'Chưa đặt';
  const chon = t.luachon.length > 0;
  $('#sua-o').hidden = chon; $('#sua-chon').hidden = !chon;
  if (chon) $('#sua-chon').innerHTML = t.luachon.map(l => '<option value="' + esc(l.giatri) + '"' + (l.giatri === t.giatri ? ' selected' : '') + '>' + esc(l.chu) + '</option>').join('');
  else { $('#sua-gt').value = t.giatri ?? ''; $('#sua-dv').textContent = t.donvi || ''; $('#sua-gt').placeholder = t.ten === 'gio_baocao_sang' ? '07:30' : ''; }
  const mai = theoMui(Date.now() + 864e5).slice(0, 10);   // ② ngày mai theo múi đã chọn
  $('#sua-tu').value = ngay(mai); $('#sua-loi').hidden = true; $('#sua-moc').textContent = ngay(t.hieuluc_tu);
  $('#h-sua input[placeholder^="Vì sao"]').value = '';
  $('#sua-ls').innerHTML = '<span class="phu">Đang tải</span>'; mo('h-sua');
  const ls = await api('/thongso/' + ten + '/lichsu');
  $('#sua-ls').innerHTML = ls.length ? ls.map((x, i) => '<div class="dong"><span class="nhan ' + (i === 0 ? 'n-dat' : 'n-xam') + '"><i></i>'
    + (x.hieuluc_den ? 'Đã thay' : 'Đang dùng') + '</span><span><b>' + esc(hienGt({...t, giatri_chu: (t.luachon.find(l => l.giatri === x.giatri) || {}).chu || x.giatri}) || 'Trống')
    + '</b> · từ ' + ngay(x.hieuluc_tu) + (x.hieuluc_den ? ' đến ' + ngay(x.hieuluc_den) : '') + ' · ' + (x.nguoi_dat === 'hethong' ? 'Mặc định' : 'Chủ') + '</span></div>').join('')
    : '<span class="phu">Chưa đặt lần nào</span>';
}
async function luuSua() {
  const t = D.thongso.thongso.find(x => x.ten === D.suaK);
  const giatri = t.luachon.length ? $('#sua-chon').value : $('#sua-gt').value.trim();
  const m = $('#sua-tu').value.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) { bao('Bạn gõ ngày áp dụng theo dạng ngày/tháng/năm, ví dụ 22/11/2026.'); return; }
  const tu = m[3] + '-' + m[2].padStart(2, '0') + '-' + m[1].padStart(2, '0');
  try {
    await api('/thongso/' + D.suaK, {giatri, hieuluc_tu: tu, ghichu: $('#h-sua input[placeholder^="Vì sao"]').value.trim()});
    dongHop(); bao((t.giatri ? 'Đã lưu. Giá trị mới chạy từ ' : 'Đã đặt. Chạy từ ') + ngay(tu) + (t.giatri ? ', giá trị cũ giữ trong lịch sử.' : '.'));
    await napThongSo();
  } catch (e) { if (e.o === 'tu') { $('#sua-loi span').textContent = e.message + '.'; $('#sua-loi').hidden = false; } else bao(e.message + '.'); }
}

// ---- Màn 09 ngăn Tài khoản và 02 lớp
async function napTaiKhoan() {
  const d = await api('/taikhoan'), chu = (d.ten || d.ten_dangnhap || '').trim();
  $('#tk-ten-lon').textContent = chu; $('#tk-chu-lon').textContent = chu.slice(0, 1).toUpperCase();
  $('#phien-dem').textContent = hai(d.phien.length) + ' phiên · thu hồi là máy đó phải đăng nhập lại';
  $('#mk-luc').textContent = ngay(d.lan_doi_matkhau); $('[data-dxkhac]').hidden = d.phien.length < 2;
  ve2Lop(d);   // 0.9.0 (QĐ390): công tắc 02 lớp
  const cot = 'grid-template-columns:2.2fr 1.4fr 1fr 110px';
  $$('#ds-phien .hang:not(.tieu-de)').forEach(e => e.remove());
  $('#ds-phien').insertAdjacentHTML('beforeend', d.phien.map(p => { const nay = p.id === d.phien_id;
    return '<div class="hang" style="' + cot + '"><div class="rong-mb dong">' + (p.loai === 'ma_truycap' ? ICON['key-round'] : /Điện thoại|Máy tính bảng|iPhone|Android|iPad/.test(p.thietbi || '') ? ICON.smartphone : ICON.laptop)
      + '<div><div class="b6">' + esc(p.thietbi || 'Không rõ thiết bị') + '</div><div class="t12 phu">' + (p.loai === 'ma_truycap' ? 'Mã truy cập' : 'Phiên web') + '</div></div></div>'
      + '<div data-l="Lần dùng cuối" class="so">' + (nay ? 'Đang dùng' : esc(luc(p.lan_dung_cuoi))) + '</div>'
      + '<div data-l="Hết hạn" class="so">' + ngay(p.het_luc) + '</div>'
      + '<div class="rong-mb phai">' + (nay ? '<span class="ttag dat">Phiên này</span>' : '<button class="btn btn-phu nho" data-thuhoi="' + esc(p.id) + '">Thu hồi</button>') + '</div></div>'; }).join(''));
}
async function doiMatKhau() {
  const [cu, moi, lai] = $$('#h-matkhau input').map(i => i.value);
  try { const kq = await api('/matkhau', {cu, moi, nhap_lai: lai}); $$('#h-matkhau input').forEach(i => i.value = ''); dongHop();
    $('#bao-doimk-chu').textContent = 'Đã đổi mật khẩu. Đã đăng xuất ' + hai(kq.thu_hoi) + ' phiên trên các máy khác.';
    $('#bao-doimk').hidden = false; napTaiKhoan(); }
  catch (e) { bao(e.message + '.'); }
}
async function doiMay() {
  const hop = $('#h-2lop'), ma = ma6(hop);
  if (ma.length !== 6) { bao('Bạn nhập đủ 06 số.'); return; }
  try {
    if (!D.maTamDoiMay) {
      const kq = await api('/2lop/doimay/batdau', {ma}); D.maTamDoiMay = kq.ma_tam; xoa6(hop);
      $('.hop-than .t13', hop).innerHTML = '<div class="qr-hang"><div class="qr">' + kq.qr_svg + '</div><div class="t13 phu">Mở ứng dụng xác thực trên máy mới, quét mã này, rồi nhập 06 số máy mới đang hiện.</div></div>';
      $('[data-luu2lop]', hop).textContent = 'Xác nhận máy mới';
    } else {
      await api('/2lop/doimay/xacnhan', {ma_tam: D.maTamDoiMay, ma}); dongHop(); datLaiDoiMay(); bao('Đã đổi máy nhận mã 02 lớp.');
    }
  } catch (e) { xoa6(hop); if (e.status === 429) { loi2Lop(hop, e); return; }   // QĐ393 (4): khóa như đăng nhập
    if (/[.!?]$/.test(e.message)) bao(e.message); else bao(e.message + '.'); }   // QĐ398: câu từ chối có dấu chấm sẵn
}
function datLaiDoiMay() { D.maTamDoiMay = ''; const hop = $('#h-2lop'); xoa6(hop);
  $('.hop-than .t13', hop).textContent = 'Nhập mã 06 số trên máy cũ để xác nhận, rồi quét mã QR mới bằng máy mới.';
  $('[data-luu2lop]', hop).textContent = 'Tiếp tục'; }
// <TAT2LOP> 0.9.0 (QĐ390–QĐ393, QĐ397, QĐ398): công tắc đăng nhập 02 lớp ở ngăn Tài khoản và 02 lớp (bản vẽ BV01–BV08).
// Chữ bản A bảng chữ màn 09 khối "Công tắc đăng nhập 02 lớp" (anh duyệt QĐ397), chép bằng chương trình; số dòng ghi cuối.
const CHU_2LOP = {
  dangBat: "Đang bật",   // dòng 1
  dangTat: "Đang tắt",   // dòng 1
  gat: "Bật đăng nhập 02 lớp",   // dòng 2
  giaiBat: "Đăng nhập trên máy mới cần thêm mã 06 số trên điện thoại.",   // dòng 3
  giaiTat: "Chỉ cần mật khẩu là vào được phần mềm.",   // dòng 4
  baoTat: "Đăng nhập 02 lớp đang tắt: ai có mật khẩu của bạn là vào được phần mềm, gồm cả khóa kết nối và số liệu tài chính.",   // dòng 5
  nutBatLai: "Bật lại",   // dòng 5
  hopTatTieu: "Tắt đăng nhập 02 lớp?",   // dòng 6
  hopTatThan: "Khi tắt, ai có mật khẩu của bạn là vào được phần mềm. Bạn nhập mật khẩu và mã 06 số đang hiện trên điện thoại để xác nhận.",   // dòng 7
  oMk: "Mật khẩu đang dùng",   // dòng 8
  oMa: "Mã 06 số",   // dòng 8
  huy: "Hủy",   // dòng 8
  nutTat: "Tắt 02 lớp",   // dòng 8
  saiTat: "Mật khẩu hoặc mã 06 số chưa đúng.",   // dòng 9
  hopBatTieu: "Bật lại đăng nhập 02 lớp",   // dòng 10
  hopBatThan: "Nhập mã 06 số đang hiện trên ứng dụng xác thực của điện thoại (máy đã cài lần trước, không cần quét lại mã QR).",   // dòng 10
  nutBat: "Bật lại",   // dòng 10
  antoan: "Đang ở chế độ an toàn: chưa tắt được đăng nhập 02 lớp.",   // dòng 11
  daTat: "Đã tắt đăng nhập 02 lớp.",   // dòng 13
  daBat: "Đã bật lại đăng nhập 02 lớp.",   // dòng 13
  hopBatDx: "Bật lại xong, mọi máy khác tự đăng xuất.",   // dòng 15
};
function ve2Lop(d) {
  const C = CHU_2LOP, tat = !d.da_bat_2lop && !!d.co_khoa_2lop, khoa = !!D.anToan && !tat;   // chế độ an toàn: không cho tắt, bật vẫn được
  D.tat2lop = tat;
  $('#vong-2lop').hidden = tat; $('#ico-2lop-tat').hidden = !tat;   // đang tắt: vòng xanh lá đổi thành ô icon cảnh báo (BV03)
  if (tat) $('#ico-2lop-tat').innerHTML = icoMau(ICON['shield-alert'], 'var(--xem)', 26);
  $('#f1-2lop').innerHTML = '<div class="dong" style="gap:8px;align-items:center;justify-content:space-between"><div class="b7 nw">Đăng nhập 02&nbsp;lớp</div>'
    + '<button class="gat-o nut-gat" data-gat2lop role="switch" aria-checked="' + !tat + '" aria-label="' + esc(C.gat) + '"'
    + (khoa ? ' disabled style="margin-left:0;opacity:.4;cursor:not-allowed"' : ' style="margin-left:0"') + '>'
    + '<input type="checkbox" tabindex="-1"' + (tat ? '' : ' checked') + '><span class="gat"></span></button></div>'
    + '<div class="nhan ' + (tat ? 'n-canh' : 'n-dat') + '"><i></i>' + esc(tat ? C.dangTat : C.dangBat) + '</div>'
    + '<div class="phu t13" style="margin-top:2px">' + cum(tat ? C.giaiTat : C.giaiBat) + '</div>'
    + (khoa ? '<div class="dong t13 phu" style="gap:6px;margin-top:6px">' + icoMau(ICON.lock, 'var(--phu)', 14) + '<span>' + cum(C.antoan) + '</span></div>' : '');
  D.nutDoiMay = D.nutDoiMay || $('#the-2lop [data-mo="h-2lop"]');   // giữ tham chiếu: vẽ lại innerHTML không làm mất nút
  $('#f1-2lop').append(D.nutDoiMay); D.nutDoiMay.hidden = tat;   // QĐ398: đang tắt thì ẩn "Đổi máy nhận mã"
  const b = $('#bao-2lop'); b.hidden = !tat;   // dòng cảnh báo đầu ngăn khi tắt (BV03), nút "Bật lại" mở hộp bật lại
  if (tat) b.innerHTML = icoMau(ICON['shield-alert'], 'var(--xem)', 18) + '<span class="f1 xem-chu t13">' + cum(C.baoTat) + '</span>'
    + '<button class="btn btn-chinh" data-bat2lopmo>' + icoMau(ICON['shield-check'], 'var(--chu-tren-nut)', 16) + esc(C.nutBatLai) + '</button>';
}
function hop2Lop(id) {   // hộp tắt, hộp bật lại (bản vẽ BV02, BV05, BV07, BV08); dựng 01 lần
  const C = CHU_2LOP, o6 = '<div class="o6-hang">' + '<input class="o6" maxlength="1" inputmode="numeric">'.repeat(6) + '</div>';
  if (!$('#' + id)) {
    const tat = id === 'h-tat2lop', l = document.createElement('div'); l.className = 'lop'; l.id = id; l.hidden = true;
    l.innerHTML = '<div class="hop" style="width:440px;max-width:100%"><div class="hop-dau">' + icoMau(ICON[tat ? 'shield-alert' : 'shield-check'], 'var(--chu)', 20)
      + '<b class="f1 t16">' + cum(tat ? C.hopTatTieu : C.hopBatTieu) + '</b><button class="nut-ico" data-dong>' + icoMau(ICON.x, 'var(--phu)', 18) + '</button></div>'
      + '<div class="hop-than">' + (tat ? '<div class="t13">' + cum(C.hopTatThan) + '</div><label class="nhan-o">' + esc(C.oMk) + '<div class="o-nhap"><input type="password" autocomplete="current-password"></div></label>'
          + '<div class="nhan-o">' + cum(C.oMa) + o6 + '</div>'
        : '<div class="t13">' + cum(C.hopBatThan) + '</div>' + o6 + '<div class="dong t13 phu" style="gap:6px">' + icoMau(ICON['info'], 'var(--phu)', 16) + '<span>' + cum(C.hopBatDx) + '</span></div>')
      + '<div class="dong t13" data-loi2lop style="gap:6px;color:var(--canh);align-items:flex-start" hidden>' + icoMau(ICON['circle-alert'], 'var(--canh)', 16) + '<span></span></div></div>'
      + '<div class="hop-chan"><button class="btn btn-phu" data-dong>' + esc(C.huy) + '</button><button class="btn btn-chinh" ' + (tat ? 'data-tat2lop>' + cum(C.nutTat) : 'data-bat2lop>' + esc(C.nutBat)) + '</button></div></div>';
    $('#h-2lop').before(l);
  }
  const l = $('#' + id); xoa6(l); $$('input', l).forEach(i => { i.value = ''; i.disabled = false; }); $$('.o6', l).forEach(i => i.style.borderColor = '');
  $$('.o-nhap', l).forEach(e => e.classList.remove('loi')); $('[data-loi2lop]', l).hidden = true;
  mo(id); const o = $(id === 'h-tat2lop' ? 'input[type="password"]' : '.o6', l); if (o) o.focus();
}
function loi2Lop(l, e) {   // bản vẽ BV07: câu báo sai + câu có sẵn số lần thử (đếm chung chặn đăng nhập)
  const con = e.status === 429 ? 0 : e.ct && e.ct.con_lai, b = $('[data-loi2lop]', l);
  const chu = cum(l.id === 'h-tat2lop' ? CHU_2LOP.saiTat : e.status === 429 ? 'Mã 02 lớp chưa đúng.' : cau(e.message))   // 429: chi tiết máy chủ là mã "khoa"
    + (con != null ? ' Còn <b>' + hai(con) + '</b>&nbsp;lần thử: sai <b>05</b>&nbsp;lần trong 15&nbsp;phút sẽ tạm khóa <b>15</b>&nbsp;phút.' : '');   // L4: số đi liền chữ sau
  if (!b) { bao(chu.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, NB)); return; }   // SUA-090-L6: hộp Đổi máy nhận mã không có dòng báo → báo nhanh
  $('span', b).innerHTML = chu;
  b.hidden = false; $$('.o-nhap', l).forEach(x => x.classList.add('loi')); $$('.o6', l).forEach(x => x.style.borderColor = 'var(--canh)');
}
async function gui2Lop(tat) {   // bản vẽ BV08: đang xử lý – nút giữ màu, không mờ (quy chuẩn 5.1)
  const l = $(tat ? '#h-tat2lop' : '#h-bat2lop'), ma = ma6(l), nut = $('.hop-chan .btn-chinh', l), goc = nut.innerHTML;
  if (ma.length !== 6) { bao('Bạn nhập đủ 06 số.'); return; }
  const mk = tat ? $('input[type="password"]', l).value : '';
  $('[data-loi2lop]', l).hidden = true; $$('.o-nhap', l).forEach(x => x.classList.remove('loi')); $$('.o6', l).forEach(x => x.style.borderColor = '');   // L3: bỏ báo sai lần trước
  nut.disabled = true; nut.classList.add('dang'); nut.innerHTML = icoMau(ICON.loader, 'var(--chu-tren-nut)', 16) + CHU_DN.dang;   // L2: .lop .btn.dang không mờ
  $$('input, .btn-phu', l).forEach(e => e.disabled = true);
  try {
    const kq = await api(tat ? '/2lop/tat' : '/2lop/bat', tat ? {matkhau: mk, ma} : {ma});
    dongHop(); bao((tat ? CHU_2LOP.daTat : CHU_2LOP.daBat).replace(/(\d) /g, '$1' + NB)); if (kq.doi !== false) demSo(); napTaiKhoan();
  } catch (e) { if (e.matKetNoi) { bao(cau(e.message)); } else if (e.status === 403) { dongHop(); bao(cau(e.message)); } else { xoa6(l); loi2Lop(l, e); } }
  finally { nut.disabled = false; nut.classList.remove('dang'); nut.innerHTML = goc; $$('input, .btn-phu', l).forEach(e => e.disabled = false); }
}
// </TAT2LOP>

// ---- Màn 09 ngăn Cập nhật
// 0.7.9: chữ 05 lớp an toàn anh đã duyệt nguyên văn (QĐ218, bảng Z16 dòng 24–47), viết ở 01 chỗ này; số dòng ghi cuối câu.
// Chữ máy chủ gửi (ổ trống, chế độ an toàn, quay về) viết ở maychu/hethong/antoan.py CHU.
const CHU_CN = {sao: {chup: 'Bước 1/2 · Đang tạo bản sao Drive (tối đa 10 phút)', day: 'Bước 1/2 · Đang tạo bản sao Drive (tối đa 10 phút)',   // 27
    qua_gio: 'Bước 1/2 · Bản sao Drive quá 10 phút, chờ bạn chọn', gui: 'Bước 2/2 · Đang tải bản ', tai: 'Bước 2/2 · Đang tải bản ',   // 28, 29
    cho_viec: 'Đã hẹn: chờ việc AI đang chạy xong (tối đa 30 phút) rồi tự cập nhật.'},   // Y38c R4: dùng lại câu đã có từ bản 0.6
  khoaRe: 'Chưa đủ ổ trống',                                                                                                         // 26
  hopTieu: 'Cập nhật khi chưa có bản sao Drive?', hopPhu: 'Máy chủ hỏng thì không lấy lại được bản sao này.',                      // 30, 33
  nutKetNoi: 'Kết nối Drive', nutHuy: 'Hủy', nutVan: 'Vẫn cập nhật',                                                                // 34
  theTieu: 'Chế độ an toàn', theDong1: 'Việc nền, AI tạm dừng.', theDong2: 'Chỉ mở Cập nhật và nhật ký; việc ghi khác bị chặn.',    // 36
  chan: 'Chế độ an toàn: chỉ mở được Cập nhật. Việc ghi khác bị chặn.',                                                               // 37
  quayve: 'Quay về bản trước', qvRe: b => 'Chạy lại bản ' + b + ' đi kèm gói cài, không cần mạng', qvTieu: b => 'Quay về bản ' + b + '?',   // 38, 39
  qvChung: 'Phần mềm tạm ngừng rồi tự mở lại. Thao tác ghi vào nhật ký.',   // 43: bỏ "khoảng 30 giây" vì chưa đo được trên máy thử (QĐ218)
  qvBao: 'Đang quay về bản trước. Trang tự tải lại khi xong.', kiem: 'Kiểm sau cập nhật: ',                                          // 44, 45, 46
  // Y38d: CHỮ MỚI CHỜ ANH DUYỆT (CPO trình): N32 thẻ lúc đang quay về; câu quay về hỏng (CDO soạn ở U13b, null = chưa hiện)
  qvDang: 'Đang quay về bản ',
  qvDam: 'việc nhập sau lúc đó không giữ được',   // N36 (f): in đậm trong câu 40
  cho: 'Trang tự tải lại khi xong. Bạn không cần bấm gì thêm.'};
function veAnToan(d) {   // lớp 2 theo bản vẽ Z16: dải trên (35, nút ở dải), thẻ viền đỏ có vòng icon, 02 dòng (36) và nút
  let o = $('#dai-antoan'); const the = $('#cn-the-antoan'), qv = (d.quay_ve || {}).co;
  const nut = c => qv ? '<button class="btn btn-chinh' + c + '" data-quayve>' + ICON['rotate-ccw'] + nbsp(CHU_CN.quayve) + '</button>' : '';
  if (the) { the.hidden = !d.an_toan; if (d.an_toan) the.innerHTML = '<div class="giua" style="width:96px;height:96px">'
    + icoMau(ICON['shield-alert'], 'var(--canh)', 40) + '</div><div class="f1"><div class="t20 b7">' + CHU_CN.theTieu + '</div>'
    + '<ul class="at-ds"><li>' + cum(CHU_CN.theDong1) + '</li><li>' + cum(CHU_CN.theDong2) + '</li></ul></div>' + nut(''); }
  if (!d.an_toan) { if (o) o.hidden = true; return; }
  if (!o) { const m = $('.vach[data-s="k:matketnoi"]');
    if (m) m.insertAdjacentHTML('afterend', '<div class="vach do-v" id="dai-antoan"></div>'); else $('#app').insertAdjacentHTML('afterbegin', '<div class="vach do-v" id="dai-antoan"></div>');
    o = $('#dai-antoan'); }
  o.hidden = false;
  const c = String(d.an_toan), i = c.indexOf(':');   // "Chế độ an toàn:" in đậm như bản vẽ
  o.innerHTML = icoMau(ICON['shield-alert'], 'var(--canh)', 18) + '<span class="f1"><b>' + cum(c.slice(0, i + 1)) + '</b>' + cum(c.slice(i + 1)) + '</span>' + nut(' nho');
}
function veQuayVe(d) {   // lớp 3 theo bản vẽ Z16: nút chữ dưới "Kiểm tra lại", câu 38 ở rê; khóa khi đang cập nhật (N33)
  const q = d.quay_ve || {}, dang = S.cn === 'dangcn' || ['chup', 'day', 'qua_gio', 'cho_viec', 'gui', 'tai'].includes(d.dang_sao);
  $$('[data-qv-nut]').forEach(b => { b.hidden = !q.co || !!d.an_toan; b.title = q.co ? CHU_CN.qvRe(q.ban) : '';
    b.innerHTML = ICON['rotate-ccw'] + nbsp(CHU_CN.quayve); });
  $$('[data-quayve]').forEach(b => { b.disabled = dang || !!q.khoa; });   // QĐ287: khóa thì bấm không được
}
function moQuayVe() {   // 39–44
  const q = (D.capnhat || {}).quay_ve || {}; if (!q.co || q.khoa || S.cn === 'dangcn') return;   // N33; QĐ287: khóa không mở hộp
  const dam = cum(CHU_CN.qvDam), chu = cum(q.chu).replace(dam, '<b>' + dam + '</b>');
  xacnhan(CHU_CN.qvTieu(q.ban), chu + '<div class="t12 phu" style="margin-top:8px">' + cum(CHU_CN.qvChung) + '</div>', CHU_CN.quayve, async () => {
    try { await api('/capnhat/quayve', {dong_y_mat: !!q.mat_tu}); }
    catch (e) { if (e.status) bao(e.message); return; }
    bao(CHU_CN.qvBao); S.cn = 'dangcn'; tieuDangCn(CHU_CN.qvDang + q.ban); ve(); veQuayVe(D.capnhat); const het = Date.now() + 3 * 60e3;   // N32
    let roi = false;   // đã thấy máy chủ dừng
    const cho = async () => { try { const r = await fetch('/suckhoe', {cache: 'no-store'}); if (r.status === 421) { const e = new Error((await r.text()).replace(/<[^>]*>/g, '')); e.s421 = true; throw e; } const k = await r.json();   // QĐ656: 421 = tên không hợp lệ
      if (k.phienban === q.ban) { location.reload(); return; }
      if (roi && k.phienban) { const s = await api('/capnhat').catch(() => ({}));   // Y38d: lên lại bằng bản mới = quay về hỏng
        if (s.quayve_loi) { tieuDangCn(cau(s.quayve_loi.chu_hien)); $('[data-s="cn:dangcn"] .phu').textContent = ''; setTimeout(() => location.reload(), 5000); return; } }
    } catch (e) { if (e.s421) { tieuDangCn(e.message); return; } roi = true; }   // QĐ656: tên không hợp lệ → dừng chờ
      if (Date.now() < het) setTimeout(cho, 3000); };
    setTimeout(cho, 3000); }, 'rotate-ccw');
}
function tieuDangCn(chu) {   // tiêu đề thẻ đang cập nhật: mặc định "Đang cập nhật lên <bản>", lúc quay về "Đang quay về bản …"
  const e = $('[data-s="cn:dangcn"] .t20'); if (!e) return; if (!tieuDangCn.goc) tieuDangCn.goc = e.innerHTML;
  if (chu) e.textContent = chu; else e.innerHTML = tieuDangCn.goc; }
function moHopDrive(loai, cheDo) {   // lớp 5: hộp "Cập nhật khi chưa có bản sao Drive?" (30–34)
  if (!$('#h-cndrive')) $('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-cndrive" hidden><div class="hop"><div class="hop-dau">'
    + ICON['cloud-upload'] + '<b class="f1 t16">' + cum(CHU_CN.hopTieu) + '</b><button class="nut-ico" data-dong>' + icoMau(ICON.x, 'var(--phu)', 20) + '</button></div>'
    + '<div class="hop-than" id="cndrive-than"></div><div class="hop-chan" id="cndrive-chan"></div></div></div>');
  D.cnDrive = {loai, cheDo};
  $('#cndrive-than').innerHTML = '<div class="dong t13 xem-chu">' + ICON['circle-alert'] + '<span>' + cum(loai === 'qua_gio' ? D.capnhat.chu_qua_gio : D.capnhat.chu_drive) + '</span></div>'
    + '<div class="t12 phu">' + cum(CHU_CN.hopPhu) + '</div>';
  $('#cndrive-chan').innerHTML = (loai === 'qua_gio' ? '' : '<button class="btn btn-phu" data-cn-ketnoi>' + nbsp(CHU_CN.nutKetNoi) + '</button>')
    + '<button class="btn btn-phu" data-cn-huy>' + CHU_CN.nutHuy + '</button><button class="btn btn-chinh" data-cn-van>' + nbsp(CHU_CN.nutVan) + '</button>';
  mo('h-cndrive');
}
function veCapNhat(d) {
  D.capnhat = d;
  if (S.cn !== 'hong' && S.cn !== 'dangcn') S.cn = d.an_toan ? 'antoan' : d.co_ban_moi ? 'coban' : 'moinhat';   // N31
  $('#ban-hien').textContent = d.ban_dang; $$('.cn-dang').forEach(e => e.textContent = d.ban_dang);
  $$('.cn-moi').forEach(e => e.textContent = d.ban_moi || '');
  $('#cn-luc').textContent = d.luc_kiem ? luc(d.luc_kiem) : 'chưa kiểm';
  if (d.nhip_phut) $('#cn-nhip').innerHTML = hai(d.nhip_phut) + '&nbsp;phút';   // QĐ174: nhịp lấy từ máy chủ (01 chỗ)
  $('#cn-loi').textContent = d.loi ? ' · ' + d.loi + '.' : '';   // Y17 (d): lỗi kiểm bản mới hiện cố định cạnh giờ kiểm
  const moi = d.thaydoi.find(m => m.ban === d.ban_moi) || d.thaydoi[0] || {dong: []};
  $('#cn-thaydoi').innerHTML = moi.dong.map(x => '<div class="dong t13">' + ICON.check + '<span>' + cum(x) + '</span></div>').join('');   // Y41e (CDO U18b L3): hiện đủ mọi dòng của bản, bỏ trần 05 dòng
  const tomTat = ban => (d.tomtat || {})[ban] || (ban === d.ban_dang ? 'Bản đang dùng' : 'Bản đã dùng');   // dòng "Tóm tắt:" ở THAYDOI.md (N07)
  const cot = 'grid-template-columns:120px 1fr 160px';
  const tdk = d.tien_do, dangKiemDong = tdk && tdk.den === d.ban_dang && !tdk.loi && !tdk.treo && ['nang', 'kiem'].includes(tdk.buoc);
  const kiem = x => !x.kiem ? (dangKiemDong && x.ban === d.ban_dang   // QĐ261 dòng 9: kiểm đang chạy nền
      ? '<span class="ks">' + icoMau(ICON.loader, 'var(--xanh-chu)', 13) + '<span>' + cum(SL.dangKiem(tdk.buoc === 'kiem' ? +(tdk.chi_tiet || {}).da || 0 : 0,
        tdk.buoc === 'kiem' ? (tdk.chi_tiet || {}).tong || 6 : 6)) + '</span></span>' : '')
    : '<span class="ks ' + (x.kiem.dat ? 'dat' : 'canh') + '">' + icoMau(ICON[x.kiem.dat ? 'circle-check' : 'circle-alert'],
    x.kiem.dat ? 'var(--dat)' : 'var(--canh)', 13) + '<span>' + CHU_CN.kiem + cum(x.kiem.chu) + '</span></span>';   // lớp 4, N36 (b)
  $('#ls-capnhat').innerHTML = d.lichsu.map(x => '<div class="hang" style="' + cot + '"><b class="so">' + esc(x.ban)
    + '</b><span data-l="Nội dung">' + cum(tomTat(x.ban)) + kiem(x) + '</span><span data-l="Ngày cài" class="so">' + ngay(x.luc) + '</span></div>').join('');
  veAnToan(d); veQuayVe(d);
  const o = d.o_trong || {du: true}, oc = $('#cn-otrong');
  if (oc) oc.innerHTML = !o.chu ? '' : '<div class="ot-dong ' + (o.du ? 'dat' : 'canh') + '">' + icoMau(ICON[o.du ? 'circle-check' : 'hard-drive'], o.du ? 'var(--dat)' : 'var(--canh)', 14)
    + '<span>' + cum(o.chu) + '</span></div>' + (o.lam ? '<div class="t12 phu" style="margin-top:2px">' + cum(o.lam) + '</div>' : '');   // N36 (b)
  if (oc && d.co_ban_moi && d.drive_bat === false) {   // QĐ278 Z21 dòng 4 (thay 02 dòng nâng dữ liệu), QĐ280, QĐ282 dòng 7
    oc.insertAdjacentHTML('beforeend', '<div class="ot-dong">' + icoMau(ICON['cloud-off'], 'var(--phu)', 14) + '<span class="phu">' + cum(SL.tat) + '</span></div>'
      + (d.nang_dulieu === true ? '<div class="ot-dong xem-chu">' + icoMau(ICON.database, 'var(--xem)', 14) + '<span>' + cum(SL.tatNd) + '</span></div>' : ''));
  } else if (oc && d.co_ban_moi && typeof d.nang_dulieu === 'boolean') {   // QĐ261 dòng 1: thẻ Có bản mới biết trước có nâng dữ liệu không
    const mau = d.nang_dulieu ? 'var(--xem)' : 'var(--phu)';
    oc.insertAdjacentHTML('beforeend', '<div class="ot-dong">' + icoMau(ICON.database, mau, 14) + '<span>' + cum(d.nang_dulieu ? SL.ndCo : SL.ndKhong) + '</span></div>');
  }
  const sl = veSauLen(d);   // QĐ261 dòng 4–8: thẻ bản đang dùng sau khi tải lại
  const kl = $('#cn-kiemloi'), k = d.kiem_hien;   // N36 (e): lỗi kiểm sau cập nhật hiện cả ở thẻ đầu
  if (kl) { kl.hidden = !k || k.dat || sl.co; if (k && !k.dat) kl.innerHTML = icoMau(ICON['circle-alert'], 'var(--canh)', 13) + '<span>' + CHU_CN.kiem + cum(k.chu) + '</span>'; }
  const qk = (d.quay_ve || {}).khoa;   // QĐ287 (Z24): bản sao trước khi nâng đã xóa → nút hiện, khóa; dòng báo dưới dòng bản
  $$('[data-qv-nut]').forEach(b => {   // QĐ261 dòng 7: kiểm chưa đạt thì "Quay về bản trước" thành nút viền (mở hộp quay về Z16)
    b.className = sl.loiKiem ? 'btn btn-phu' : 'btn-chu';
    b.innerHTML = icoMau(ICON['rotate-ccw'], sl.loiKiem ? 'var(--chu)' : 'var(--xanh-chu)', sl.loiKiem ? 16 : 14) + nbsp(CHU_CN.quayve);
    if (qk) { b.className = 'btn-chu qv-khoa'; b.innerHTML = icoMau(ICON.lock, 'var(--phu)', 14) + nbsp(CHU_CN.quayve);   // Z24 dòng 2
      b.disabled = true; b.title = d.quay_ve.chu; } });
  const qkd = $('#cn-qvkhoa');
  if (qkd) { qkd.hidden = !qk; qkd.innerHTML = qk ? icoMau(ICON['archive-x'], 'var(--phu)', 14) + '<span>' + cum(d.quay_ve.chu) + '</span>' : ''; }
  if (d.quayve_loi) $('#ls-capnhat').insertAdjacentHTML('afterbegin', '<div class="hang" style="' + cot + '"><b class="so">' + esc(d.ban_dang)   // Y38d
    + '</b><span data-l="Nội dung"><span class="ks canh">' + icoMau(ICON['rotate-ccw'], 'var(--canh)', 13) + '<span>' + cum(cau(d.quayve_loi.chu_hien))
    + '</span></span></span><span data-l="Ngày cài" class="so">' + ngay(d.quayve_loi.luc) + '</span></div>');
  $$('[data-s="cn:coban"] [data-capnhat]').forEach(b => { b.disabled = !o.du; b.title = o.du ? '' : CHU_CN.khoaRe; });
  if (D.coBanMoi !== !!d.co_ban_moi) { D.coBanMoi = !!d.co_ban_moi; veMenuCd(); }   // chấm xanh "có bản mới" ở menu Cài đặt
  ve();
  const t = d.tien_do;   // QĐ253: mở trang (hoặc vừa tải lại sang bản mới) giữa lúc đang cập nhật thì hiện tiếp tiến độ 08 bước
  const dangLuot = t && !t.loi && !t.treo && t.buoc !== 'xong' && t.tu && t.den;   // QĐ255 điểm 2: cờ treo do máy chủ tính
  if (dangLuot && !daLen(d.ban_dang, t.den) && S.cn !== 'dangcn') choCapNhat(t.tu, t.den, d);   // bản cũ còn chạy: hiện tiếp tiến độ
  else if ((dangLuot && t.den === d.ban_dang) || sl.keoDrive) theoKiem();   // QĐ258, QĐ261: kiểm 06 điểm, Drive đang chạy nền
}
// QĐ261 (bản vẽ Z19, chữ U19 anh duyệt dòng 1–9): chữ thẻ Có bản mới và thẻ bản đang dùng sau khi tải lại, viết ở 01 chỗ này.
const SL = {ndKhong: 'Không nâng dữ liệu: bản sao Drive đẩy sau khi lên bản mới.', ndCo: 'Có nâng dữ liệu: đẩy bản sao Drive xong mới cập nhật.',
  // QĐ278 Z21 dòng 4, 6 (QĐ288 "lưu"), QĐ282 dòng 7: công tắc Sao lưu Google Drive đang tắt
  tat: 'Sao lưu Google Drive đang tắt: bản sao chỉ lưu trên máy chủ.', tatNd: 'Bản này có nâng dữ liệu.', tatSau: 'Bản sao Drive: tắt',
  vuaLen: (b, l, g) => 'Vừa lên bản ' + b + ' lúc ' + l + ' · tổng thời gian ' + g,
  dangKiem: (k, n) => 'Kiểm sau cập nhật: đang kiểm ' + hai(k) + '/' + hai(n),
  vanChay: b => 'Bản ' + b + ' vẫn chạy. Lỗi đã ghi nhật ký và báo chuông.',
  dangDay: (k, n) => 'Bản sao Drive: đang đẩy ' + hai(k) + '/' + hai(n) + ' tệp', daLen: n => 'Bản sao Drive: đã lên ' + hai(n) + '/' + hai(n) + ' tệp',
  // QĐ273 (anh "Chọn A"): giờ hẹn đẩy lại sớm nhất trong hàng chờ, giờ Việt Nam
  chuaLenHet: (k, n, hen) => 'Bản sao Drive: chưa lên hết ' + hai(k) + '/' + hai(n) + ' tệp' + (hen ? ' · tự đẩy lại từ ' + hen : '')};
function veSauLen(d) {   // trả {co, loiKiem, keoDrive}; không có lượt vừa lên bản này thì xóa trống
  const e = $('#cn-saulen'), the = $('[data-s="cn:moinhat"]'), t = d.tien_do, k = d.kiem_hien;
  const co = !!(e && t && t.den === d.ban_dang && !t.loi && !t.treo && ['nang', 'kiem', 'xong'].includes(t.buoc));
  if (the) the.classList.remove('vien-loi');
  if (!co) { if (e) e.innerHTML = ''; return {}; }
  const moc = t.moc || {}, luc = moc.kiem || t.xong || moc.nang || '';
  const dong = (lop, ico, mau, chu) => '<div class="ks ' + lop + '">' + icoMau(ICON[ico], mau, 14) + '<span>' + cum(chu) + '</span></div>';
  let h = dong('dat', 'circle-check', 'var(--dat)', SL.vuaLen(t.den, gio(luc), mmss((Date.parse(luc) - Date.parse(t.bat_dau)) / 1000)));
  const dangKiem = t.buoc !== 'xong', loiKiem = !dangKiem && !!k && !k.dat;
  if (dangKiem) { const c = t.buoc === 'kiem' ? t.chi_tiet || {} : {}; h += dong('', 'loader', 'var(--xanh-chu)', SL.dangKiem(+c.da || 0, c.tong || 6)); }
  else if (k) h += dong(k.dat ? 'dat' : 'canh', k.dat ? 'circle-check' : 'circle-alert', k.dat ? 'var(--dat)' : 'var(--canh)', CHU_CN.kiem + k.chu)
    + (k.dat ? '' : '<div class="t12 phu">' + cum(SL.vanChay(d.ban_dang)) + '</div>');
  const dn = t.drive_nen;
  if (t.drive_tat) h += '<div class="ks phu">' + icoMau(ICON['cloud-off'], 'var(--phu)', 14) + '<span>' + cum(SL.tatSau) + '</span></div>';   // QĐ278 Z21 dòng 6
  if (dn && dn.tong) h += dn.da >= dn.tong ? dong('dat', 'cloud-check', 'var(--dat)', SL.daLen(dn.tong))
    : dn.loi ? dong('xem', 'cloud-alert', 'var(--xem)', SL.chuaLenHet(dn.da, dn.tong, gio(dn.hen || ''))) : dong('', 'cloud-upload', 'var(--xanh-chu)', SL.dangDay(dn.da, dn.tong));
  e.innerHTML = h;
  if (the) the.classList.toggle('vien-loi', loiKiem);
  return {co, loiKiem, keoDrive: !!(dn && dn.tong && dn.da < dn.tong)};   // CDO U21 G2: Drive lỗi vẫn theo dõi (tự đẩy lại)
}
function moCapNhat() {
  const viec = D.capnhat.so_viec_ai, o = D.capnhat.o_trong || {du: true};
  if (!o.du) { bao(o.chu + ' ' + (o.lam || '')); return; }   // lớp 1: nút đã khóa; phòng khi bấm qua phím
  $('#cn-viec').innerHTML = viec ? 'Đang có <b>' + hai(viec) + '</b> việc AI chạy.' : 'Không có việc AI nào đang chạy.';
  mo('h-capnhat');
}
async function capNhat(cheDo, van) {
  dongHop(); const cu = D.capnhat.ban_dang, moi = D.capnhat.ban_moi;
  try { const kq = await api('/capnhat', {che_do: cheDo, van_capnhat: !!van});
    if (kq.can_chon) { moHopDrive(kq.can_chon, cheDo); return; }   // lớp 5: Drive chưa kết nối → anh chọn
    if (kq.cho) { bao('Đã hẹn: chờ việc AI đang chạy xong (tối đa 30 phút) rồi tự cập nhật.'); return; } }
  catch (e) { if (e.status) { S.cn = 'hong'; $('#cn-lydo').textContent = 'Lý do: ' + e.message + '.'; ve(); } return; }
  choCapNhat(cu, moi);
}
// <TD8> 0.8.1 (QĐ249, QĐ251, QĐ253): thẻ "Đang cập nhật" hiện % theo 08 bước, đúng bản vẽ Z18 (CDO U17). Chữ anh duyệt
// nguyên văn ở bảng màn 09 (Bangdulieu_Manhinh_GD1), viết ở 01 chỗ này. Bước có số đo (tệp i/07, điểm k/06, tệp lên Drive)
// tính theo số đo; bước 5–7 ước tính theo thời gian các lần trước (máy chủ tính từ F04, trả ở tien_do.du_kien).
const TD8 = {ma: ['o_trong', 'chup', 'drive', 'gui', 'tai', 'khoidong', 'nang', 'kiem'], uoc: ['tai', 'khoidong', 'nang'],
  ten: ['Kiểm ổ trống', 'Sao lưu dữ liệu', 'Bản sao Drive', 'Gửi lệnh cập nhật', 'Tải gói cài', 'Thay bản chạy', 'Nâng dữ liệu', 'Kiểm sau cập nhật'],
  cot: {o_trong: 'đang kiểm', drive: 'đang đẩy lên', gui: 'đang gửi'}, uocTinh: 'ước tính', xong: 'xong', cham: 'lâu hơn ước tính',
  quaGio: 'quá 10 phút', chuaDuoc: 'chưa được', tep: ' tệp', diem: ' điểm', sauUoc: ' (ước tính)', thuongLe: ' lâu hơn thường lệ',
  chuaNoi: 'chưa nối Drive', chuaLenHet: 'chưa lên hết',   // QĐ255 điểm 3: bước 3 bỏ qua
  tat: 'tắt',   // QĐ278 Z21 dòng 5: công tắc Sao lưu Google Drive tắt
  sauLen: 'sau khi lên bản', sauTaiLai: 'sau khi tải lại',   // QĐ261 dòng 2, 3: Drive đẩy nền, kiểm chạy nền sau khi tải lại
  dang: b => 'Đang cập nhật lên ' + b, daLen: b => 'Đã lên bản ' + b, chuaLen: b => 'Chưa cập nhật được lên ' + b,
  buoc: k => 'Bước ' + k + '/8:', dung: k => 'Dừng ở bước ' + k + '/8:', xongBuoc: 'Xong 08/08 bước', quaChu: 'Bản sao Drive quá 10 phút, chờ bạn chọn',
  daChay: 'Đã chạy ', tong: 'Tổng thời gian ', conKhoang: p => ' · còn khoảng ' + hai(p) + ' phút (ước tính)',
  conDuoi: ' · còn dưới 01 phút (ước tính)', chuaUoc: ' · chưa ước tính được thời gian còn lại',
  phuDang: 'Trang tự tải lại khi xong. Bạn không cần bấm gì thêm.', phuCham: 'Phần mềm vẫn đang chờ. Bạn không cần bấm gì thêm.',
  phuQua: 'Bạn chọn ở hộp đang mở.', phuLoi: b => 'Chưa gửi lệnh cập nhật nên bản ' + b + ' và dữ liệu giữ nguyên. Lỗi ghi vào nhật ký.',
  phuXong: 'Trang tự tải lại sau 03 giây.', thuLai: 'Thử lại',
  NGUONG_CHAM: 2,   // điểm (a): bước ước tính chạy quá 02 lần thời gian dự kiến thì chuyển "lâu hơn ước tính"
  mau: {dang: 'var(--xanh-chu)', cham: 'var(--xem)', loi: 'var(--canh)', xong: 'var(--dat)', cho: 'var(--phu)', chu: 'var(--chu)'}};
ICON.circle = ICON.circle || ICON['circle-check'].replace(/\s*<path[^>]*\/>/, '');   // `circle` xám: bước chưa tới (bỏ dấu tích)
ICON['circle-minus'] = ICON['circle-minus'] || ICON['circle-check'].replace('lucide-circle-check', 'lucide-circle-minus')
  .replace(/<path d="[^"]*"/, '<path d="M8 12h8"');   // QĐ255 điểm 3: bước 3 bỏ qua (Lucide circle-minus)
// QĐ261, QĐ262 (bản vẽ Z19): 02 icon Lucide (giấy phép ISC) lấy đúng nét trong bản vẽ: Drive đã lên đủ, Drive lỗi / chuông.
const svgLucide = (ten, net) => '<svg\n  style="flex:none;vertical-align:middle;color:var(--chu)" class="lucide lucide-' + ten + '"\n  xmlns="http://www.w3.org/2000/svg"\n'
  + '  width="16"\n  height="16"\n  viewBox="0 0 24 24"\n  fill="none"\n  stroke="currentColor"\n  stroke-width="2"\n  stroke-linecap="round"\n'
  + '  stroke-linejoin="round"\n>\n' + net.map(d => d.startsWith('<') ? '  ' + d + '\n' : '  <path d="' + d + '" />\n').join('') + '</svg>';
ICON['cloud-check'] = ICON['cloud-check'] || svgLucide('cloud-check', ['m17 15-5.5 5.5L9 18', 'M5 17.743A7 7 0 1 1 15.71 10h1.79a4.5 4.5 0 0 1 1.5 8.742']);
// QĐ278, QĐ287 (bản vẽ Z21, Z24): Drive tắt, không còn bản sao để quay về, nút khóa
ICON['cloud-off'] = ICON['cloud-off'] || svgLucide('cloud-off', ['m2 2 20 20', 'M5.782 5.782A7 7 0 0 0 9 19h8.5a4.5 4.5 0 0 0 1.307-.193',
  'M21.532 16.5A4.5 4.5 0 0 0 17.5 10h-1.79A7.008 7.008 0 0 0 10 5.07']);
ICON['archive-x'] = ICON['archive-x'] || svgLucide('archive-x', ['<rect width="20" height="5" x="2" y="3" rx="1" />',
  'M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8', 'm9.5 17 5-5', 'm9.5 12 5 5']);
ICON.lock = ICON.lock || svgLucide('lock', ['<rect width="18" height="11" x="3" y="11" rx="2" ry="2" />', 'M7 11V7a5 5 0 0 1 10 0v4']);
ICON['cloud-alert'] = ICON['cloud-alert'] || svgLucide('cloud-alert', ['M12 12v4', 'M12 20h.01', 'M17 18h.5a1 1 0 0 0 0-9h-1.79A7 7 0 1 0 7 17.708']);
// <CA> Y46 (QĐ263, QĐ264, QĐ271, QĐ306, QĐ307; bản vẽ Z20): khối "Công cụ AI" ở màn Cập nhật. Chữ anh duyệt nguyên văn
// ở bảng màn 09 (Bangdulieu_Manhinh_GD1, Z20 dòng 1–13, 15b, 20), viết ở 01 chỗ này. Số bản, giờ lấy từ máy chủ.
const CA = {tieu: 'Công cụ AI', gat: 'Tự nâng mỗi ngày',
  moTa: 'Công cụ chạy gói Claude, gói ChatGPT trên máy chủ. Chỉ nhận bản hãng đã ra từ 24 giờ, kiểm thử đạt mới dùng; chưa đạt thì tự về bản trước.',
  cot: ['Công cụ', 'Bản đang dùng', 'Bản mới của hãng', 'Nâng gần nhất'],
  truoc: b => 'bản trước ' + b, oGoi: b => b + ' · trong gói', moiNhat: 'Đã mới nhất', raLuc: r => 'ra lúc ' + r,
  chuaDat: 'chưa đạt, không dùng', khongLai: 'không tự nâng lại',
  thuong: k => 'Đang dùng bản mới nhất. Lần kiểm tới: ' + k + '.',
  cho: (t, b, ra, sau) => t + ' có bản ' + b + ' (ra lúc ' + ra + '). Tự nâng khi bản ra đủ 24 giờ, sau ' + sau + '.',
  choPhu: 'Muốn có ngay thì bấm Nâng công cụ AI.',
  choDu: (t, b, ra, k) => t + ' có bản ' + b + ' (ra lúc ' + ra + '). Tự nâng lúc ' + k + '.',   // QĐ311 L4: bản đã đủ 24 giờ
  nut: 'Nâng công cụ AI', nutKhoa: 'Đang dùng bản mới nhất', dangNut: 'Đang nâng…',
  hopTieu: (t, b) => 'Nâng ' + t + ' lên ' + b + '?',
  hopChu: (chua24, co, y) => (chua24 ? 'Bản này ra chưa đủ 24 giờ. ' : '') + 'Phần mềm tải khoảng ' + co
    + ', kiểm thử rồi mới dùng; chưa đạt thì tự về bản ' + y + '. AI vẫn chạy trong lúc nâng.',
  dang: (t, b) => 'Đang nâng ' + t + ' lên ' + b + ': tải và kiểm thử.', dangPhu: y => 'Trong lúc nâng, AI vẫn chạy bằng bản ' + y + '.',   // QĐ309 (Z20 dòng 8b, A)
  dat: (t, b, l) => 'Đã nâng ' + t + ' lên ' + b + ' lúc ' + l + ' · kiểm thử đạt.',
  lui: (t, b, y) => t + ' ' + b + ' kiểm thử chưa đạt, đã tự về bản ' + y + '.',
  luiPhu: b => 'AI vẫn chạy bình thường. Bản ' + b + ' không thử lại. Lỗi đã ghi nhật ký và báo chuông.',
  ve: 'Về bản trước', veTieu: (t, y) => 'Về ' + t + ' bản ' + y + '?', veChu: (x, y) => 'Bản ' + x + ' không tự nâng lại. Lượt AI mới dùng bản ' + y + ' ngay.',
  daVe: (t, y, l, x) => 'Đã về ' + t + ' bản ' + y + ' lúc ' + l + '. Bản ' + x + ' không tự nâng lại.',
  tat: 'Tự nâng đang tắt. Hãng có bản mới thì hiện ở đây; bạn bấm Nâng công cụ AI để nâng.',
  tamDung: b => 'Tự nâng tạm dừng: bạn đã quay về bản ' + b + ', công cụ AI dùng bản trong gói của bản này.',
  tamDungPhu: 'Bật lại: gạt công tắc Tự nâng mỗi ngày, hoặc cập nhật lên bản mới.',
  hoan: (t, b, g, y, n) => 'Hoãn nâng ' + t + ' ' + b + ': gói ' + g + ' đang hết hạn mức nên chưa kiểm thử được. Vẫn dùng bản ' + y
    + '; lượt kiểm 03:00 ' + n + ' thử lại.',   // QĐ307 dòng 20 (QĐ306): dòng xám, không chuông; n theo QĐ308 điểm 11
  goiTen: {claude: 'Claude', chatgpt: 'ChatGPT'}, homNay: 'hôm nay', ngayMai: 'ngày mai',
  chuaNang: 'Chưa nâng',   // QĐ308 điểm 4: cột "Nâng gần nhất" khi chưa nâng lần nào
  mau: {dat: 'var(--dat)', xem: 'var(--xem)', xam: 'var(--phu)', xanh: 'var(--xanh-chu)'}};
ICON['monitor-cog'] = svgLucide('monitor-cog', ['M12 17v4', 'm14.305 7.53.923-.382', 'm15.228 4.852-.923-.383', 'm16.852 3.228-.383-.924',
  'm16.852 8.772-.383.923', 'm19.148 3.228.383-.924', 'm19.53 9.696-.382-.924', 'm20.772 4.852.924-.383', 'm20.772 7.148.924.383',
  'M22 13v2a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7', 'M8 21h8', '<circle cx="18" cy="6" r="3" />']);   // QĐ653
ICON.stamp = svgLucide('stamp', ['M14 13V8.5C14 7 15 7 15 5a3 3 0 0 0-6 0c0 2 1 2 1 3.5V13',
  'M20 15.5a2.5 2.5 0 0 0-2.5-2.5h-11A2.5 2.5 0 0 0 4 15.5V17a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1z', 'M5 22h14']);   // QĐ653
ICON.sun = svgLucide('sun', ['<circle cx="12" cy="12" r="4" />', 'M12 2v2', 'M12 20v2', 'm4.93 4.93 1.41 1.41', 'm17.66 17.66 1.41 1.41', 'M2 12h2',
  'M20 12h2', 'm6.34 17.66-1.41 1.41', 'm19.07 4.93-1.41 1.41']);
ICON.moon = svgLucide('moon', ['M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401']);
ICON.monitor = svgLucide('monitor', ['<rect width="20" height="14" x="2" y="3" rx="2" />', '<line x1="8" x2="16" y1="21" y2="21" />',
  '<line x1="12" x2="12" y1="17" y2="21" />']);
ICON['circle-chevron-right'] = svgLucide('circle-chevron-right', ['<circle cx="12" cy="12" r="10" />', 'm10 8 4 4-4 4']);   // QĐ585
ICON['circle-pause'] = ICON['circle-pause'] || svgLucide('circle-pause', ['<circle cx="12" cy="12" r="10" />',
  '<line x1="10" x2="10" y1="15" y2="9" />', '<line x1="14" x2="14" y1="15" y2="9" />']);
ICON['circle-arrow-up'] = ICON['circle-arrow-up'] || svgLucide('circle-arrow-up', ['<circle cx="12" cy="12" r="10" />', 'm16 12-4-4-4 4', 'M12 16V8']);
const caVn = t => theoMui(t);   // QĐ636: giờ theo múi đã chọn (tên cũ giữ, dùng trong khối Công cụ AI)
const caSo = b => String(b || '0.0.0').split('.').map(x => parseInt(x, 10) || 0);
const caCao = (a, b) => { const x = caSo(a), y = caSo(b); for (let i = 0; i < 3; i++) if (x[i] !== y[i]) return x[i] > y[i]; return false; };
// QĐ386 (LOI-CN-089): bản đang chạy ≥ bản yêu cầu là đã lên (watchtower kéo bản mới nhất, có thể mới hơn bản ghi lúc bấm).
// Chỉ dùng để quyết định "bản cũ còn chạy" (gọi choCapNhat); khi nhận lượt, máy chủ ghi den = bản thật (tiendo.vao_ban_moi).
const daLen = (dang, den) => !!den && !caCao(den, dang);
const caBan = (so, goi) => goi ? (so ? so + ' trong gói' : 'trong gói') : so;   // QĐ307 dòng 10, 11, 15b: bản trong gói
function caLuc(t, bay) {   // "10:00 hôm nay" · "10:00 ngày mai" · ngày khác: "10:00 ngày 23/11/2026"
  const v = caVn(t), n = v.slice(0, 10);
  const ngayChu = n === caVn(bay).slice(0, 10) ? CA.homNay : n === caVn(bay + 864e5).slice(0, 10) ? CA.ngayMai
    : 'ngày ' + ngay(v).slice(0, n.slice(0, 4) === caVn(bay).slice(0, 4) ? 5 : 10);   // cùng năm thì bỏ năm
  return (v.slice(11, 16) + ' ' + ngayChu).replace(/ /g, '\u00a0');   // giờ và ngày không tách khi xuống dòng
}
const caCum = s => cum(s).replace(/(ngày|hôm) (mai|nay)|kiểm thử( đạt)?|trong gói/g, x => x.replace(/ /g, '&nbsp;'));   // U36 L1, L3; U37a L5
const caKiemToi = (t, gk) => {   // lượt kiểm 03:00 kế tiếp sau lúc t (ms)
  const v = caVn(t), lech = Date.parse(v + 'Z') - Math.floor(Date.parse(t) / 1000) * 1000, moc = Date.parse(v.slice(0, 10) + 'T' + hai(gk) + ':00:00Z') - lech;   // giờ kiểm theo múi đã chọn
  return Date.parse(t) < moc ? moc : moc + 864e5; };
const caKiemTiep = (c, bay) => hai(c.gio_kiem ?? 3) + ':00 ' + (c.kiem_ngay === caVn(bay).slice(0, 10) ? CA.ngayMai : CA.homNay);   // dòng 5
const caHomNay = (t, bay) => !!t && caVn(t).slice(0, 10) === caVn(bay).slice(0, 10);
function caMoi(x) {   // bản mới của hãng còn nâng được (chưa hỏng, chưa về tay)
  const h = x.hang; return !!(h && h.ban && caCao(h.ban, x.ban) && !(x.hong || []).includes(h.ban)) ? h : null;
}
function caDich(c) {   // gói nút "Nâng công cụ AI" nâng (gói đầu tiên có bản mới nâng được)
  if (c.dang_nang || c.tam_dung || c.chan) return null;
  return c.goi.find(x => { const h = caMoi(x); return h && h.uoc_chu; }) || null;
}
function htmlCongCu(c, bay) {
  const dong = (mau, ico, chu, phu) => '<span class="ks"' + (mau ? ' style="color:' + mau + '"' : '') + '>' + icoMau(ICON[ico], mau || 'var(--chu)', 14)
    + '<span>' + caCum(chu) + '</span></span>' + (phu ? '<div class="t12 phu" style="margin-top:4px">' + caCum(phu) + '</div>' : '');
  const bat = c.bat && !c.tam_dung, dn = c.dang_nang;
  let h = '<div class="dong" style="gap:8px;align-items:center">' + ICON.wrench + '<span class="t16 b7 f1">' + CA.tieu + '</span><span class="t13">'
    + CA.gat + '</span><button class="gat-o nut-gat" data-cagat role="switch" aria-checked="' + bat + '" aria-label="' + CA.gat + '">'
    + '<input type="checkbox" tabindex="-1"' + (bat ? ' checked' : '') + '><span class="gat"></span></button></div>'
    + '<div class="phu t12" style="margin:4px 0 8px">' + cum(CA.moTa) + '</div>'
    + '<div class="cl-hang cl5 tieu-de">' + CA.cot.map(x => '<span>' + x + '</span>').join('') + '<span></span></div>';
  c.goi.forEach(x => {
    const hg = x.hang, gan = [x.nang_luc, (x.su_kien || {}).luc].filter(Boolean).sort().pop();
    let o3 = '';
    if (hg && hg.ban) {
      if (!caCao(hg.ban, x.ban)) o3 = '<span class="so" style="color:' + CA.mau.dat + '">' + CA.moiNhat + '</span>';
      else if ((x.ve_tay || []).includes(hg.ban)) o3 = '<span class="so" style="color:' + CA.mau.xam + '">' + esc(hg.ban) + '</span><div class="t12 phu">' + CA.khongLai + '</div>';
      else if ((x.hong || []).includes(hg.ban)) o3 = '<span class="so" style="color:' + CA.mau.xem + '">' + esc(hg.ban) + '</span><div class="t12" style="color:' + CA.mau.xem + '">' + CA.chuaDat + '</div>';
      else o3 = '<span class="so" style="color:' + CA.mau.xanh + '">' + esc(hg.ban) + '</span>' + (hg.ra_luc && caHomNay(hg.ra_luc, bay) ? '<div class="t12 phu">' + cum(CA.raLuc(caLuc(hg.ra_luc, bay))) + '</div>' : '');
    }
    const coVe = !x.trong_goi && !dn && !c.tam_dung;   // QĐ308 điểm 10: bị chặn thì khóa + câu rê chuột (không ẩn)
    h += '<div class="cl-hang cl5"><b>' + esc(x.ten) + '</b><span data-l="' + CA.cot[1] + '"><span class="so">' + caCum(x.trong_goi ? CA.oGoi(x.ban || '') : x.ban) + '</span>'
      + (x.truoc || x.truoc_goi ? '<div class="t12 phu">' + caCum(CA.truoc(x.truoc || caBan(x.ban_goi, true))) + '</div>' : '')
      + '</span><span data-l="' + CA.cot[2] + '">' + o3 + '</span>'
      + '<span data-l="' + CA.cot[3] + '">' + (gan ? ngay(caVn(gan)) + ' ' + caVn(gan).slice(11, 16) : CA.chuaNang) + '</span><span class="phai">'
      + (!coVe ? '' : c.chan ? '<button class="btn-chu nho qv-khoa" disabled' + (c.chan_chu ? ' title="' + esc(c.chan_chu) + '"' : '') + '>'
        + icoMau(ICON['rotate-ccw'], 'var(--phu)', 14) + CA.ve + '</button>'
        : '<button class="btn-chu nho" data-cave="' + esc(x.goi) + '">' + icoMau(ICON['rotate-ccw'], 'var(--xanh-chu)', 14) + CA.ve + '</button>') + '</span></div>';
  });
  // dòng trạng thái (01 dòng): đang nâng > tạm dừng > việc vừa xảy ra hôm nay > tắt > hãng có bản mới > mới nhất
  let tt;
  const sk = c.goi.map(x => ({x, s: x.su_kien})).filter(o => o.s && bay < caKiemToi(o.s.luc, c.gio_kiem ?? 3))
    .sort((a, b) => a.s.luc < b.s.luc ? 1 : -1)[0];
  const cho = c.goi.map(x => ({x, m: caMoi(x)})).find(o => o.m);
  if (dn) { const x = c.goi.find(g => g.goi === dn.goi) || c.goi[0];
    tt = dong('', 'loader', CA.dang(x.ten, dn.ban || (x.hang || {}).ban), CA.dangPhu(dn.cu ? caBan(dn.cu, dn.cu_goi) : caBan(x.ban, x.trong_goi)))
      + '<div class="td" style="height:8px;margin-top:6px"><div class="tdf chay"></div></div>'; }
  else if (c.tam_dung) tt = dong(CA.mau.xem, 'circle-pause', CA.tamDung(c.tam_dung_ban || ''), CA.tamDungPhu);
  else if (!c.bat) tt = dong('', 'circle-pause', CA.tat);
  else if (sk) { const {x, s} = sk, y = caBan(s.giu, s.giu_goi), l = caVn(s.luc).slice(11, 16);
    tt = s.loai === 'dat' ? dong(CA.mau.dat, 'circle-check', CA.dat(x.ten, s.ban, l))
      : s.loai === 'hong' ? dong(CA.mau.xem, 'circle-alert', CA.lui(x.ten, s.ban, y), CA.luiPhu(s.ban))
      : s.loai === 've' ? dong('', 'rotate-ccw', CA.daVe(x.ten, y, l, s.ban))
      : dong(CA.mau.xam, 'clock', CA.hoan(x.ten, s.ban, CA.goiTen[x.goi] || x.ten, y,
        +caVn(s.luc).slice(11, 13) < (c.gio_kiem ?? 3) ? CA.homNay : CA.ngayMai)); }
  else if (cho) { const r = Date.parse(cho.m.ra_luc), du = r + (c.cho_gio || 24) * 3600e3;
    tt = !Number.isFinite(r) ? '' : du <= bay   // QĐ311 L4: mốc "sau …" đã qua thì ghi lượt kiểm kế tiếp như dòng 5
      ? dong('', 'circle-arrow-up', CA.choDu(cho.x.ten, cho.m.ban, caLuc(r, bay), caKiemTiep(c, bay)), CA.choPhu)
      : dong('', 'circle-arrow-up', CA.cho(cho.x.ten, cho.m.ban, caLuc(r, bay), caLuc(du, bay)), CA.choPhu); }
  else tt = dong(CA.mau.dat, 'circle-check', CA.thuong(caKiemTiep(c, bay)));
  const dich = caDich(c);
  const nut = dn ? '<button class="btn khoa" disabled>' + ICON.loader + CA.dangNut + '</button>'
    : dich ? '<button class="btn btn-chinh" data-canang="' + esc(dich.goi) + '">' + icoMau(ICON['circle-arrow-up'], 'var(--chu-tren-nut)', 16) + CA.nut + '</button>'
    : '<button class="btn khoa" disabled' + (c.chan_chu ? ' title="' + esc(c.chan_chu) + '"' : c.tam_dung || c.chan ? '' : ' title="' + CA.nutKhoa + '"') + '>' + icoMau(ICON['circle-arrow-up'], 'var(--phu)', 16) + CA.nut + '</button>';
  return h + '<div class="cl-chan"><div class="f1">' + tt + '</div>' + nut + '</div>';
}
// </CA>
async function napCongCu() {
  const e = $('#khoi-cl'); if (!e) return;
  try { D.ca = await api('/capnhat/congcu_ai'); } catch (er) { return; }
  D.ca.chan_chu = D.ca.chan === 'che_do_an_toan' ? CHU_CN.chan   // QĐ308 điểm 10: 0 chữ mới
    : D.ca.chan === 'dang_cap_nhat' ? TD8.dang(D.ca.cap_nhat_len || (D.capnhat || {}).ban_moi || '') : '';
  e.innerHTML = htmlCongCu(D.ca, Date.now());
  clearTimeout(napCongCu.h);
  if (D.ca.dang_nang && S.tab === 'capnhat' && S.trang === '09') napCongCu.h = setTimeout(napCongCu, 3000);   // đang nâng: xem tiếp
}
function moNangCongCu(goi) {
  const c = D.ca, x = c && c.goi.find(g => g.goi === goi), h = x && caMoi(x); if (!h) return;
  const chua24 = !(Date.now() - Date.parse(h.ra_luc) >= (c.cho_gio || 24) * 3600e3);
  xacnhan(CA.hopTieu(x.ten, h.ban), cum(CA.hopChu(chua24, h.uoc_chu, caBan(x.ban, x.trong_goi))), CA.nut, async () => {
    try { await api('/capnhat/congcu_ai/nang', {goi}); } catch (er) { /* bị chặn: vẽ lại theo trạng thái máy chủ */ }
    await napCongCu(); if (!D.ca.dang_nang) setTimeout(napCongCu, 1500); }, 'circle-arrow-up');
}
function moVeCongCu(goi) {
  const x = D.ca && D.ca.goi.find(g => g.goi === goi); if (!x || x.trong_goi) return;
  const y = x.truoc || caBan(x.ban_goi, true);
  xacnhan(CA.veTieu(x.ten, y), cum(CA.veChu(x.ban, y)), CA.ve, async () => {
    try { await api('/capnhat/congcu_ai/ve', {goi}); } catch (er) { /* bị chặn: vẽ lại */ }
    await napCongCu(); }, 'rotate-ccw');
}
async function gatCongCu() {
  const c = D.ca; if (!c) return;
  try { await api('/thongso/tunang_congcu_ai/gat', {bat: !(c.bat && !c.tam_dung)}); } catch (er) { if (er.status) bao(er.message + '.'); }
  await napCongCu();
}
const mmss = g => { g = Math.max(0, Math.floor(g || 0)); return hai(Math.floor(g / 60)) + ':' + hai(g % 60); };
function tinhTienDo(td, bay) {   // bay: giờ máy chủ (ms). Cùng cách tính với maychu/hethong/tiendo.hien
  const t = s => s ? Date.parse(s) : NaN, moc = td.moc || {}, ct = td.chi_tiet || {}, xong = td.buoc === 'xong';
  const du = TD8.ma.map(b => Math.max(0, +(td.du_kien || {})[b] || 0)), cong = a => a.reduce((x, y) => x + y, 0), tong = cong(du) || 1;
  const vi = xong ? 8 : Math.max(0, TD8.ma.indexOf(td.buoc)), b = td.buoc;
  const troi = xong ? 0 : Math.max(0, (bay - t(moc[b])) / 1000) || 0;
  const cham = !xong && !td.loi && TD8.uoc.includes(b) && du[vi] > 0 && troi > TD8.NGUONG_CHAM * du[vi];
  const phan = xong ? 0 : ct.tong ? Math.min(1, (+ct.da || 0) / ct.tong) : td.loi ? 0 : du[vi] ? Math.min(0.95, troi / du[vi]) : 0.95;
  const pt = xong ? 100 : Math.max(0, Math.min(99, Math.floor(100 * (cong(du.slice(0, vi)) + phan * (du[vi] || 0)) / tong)));
  const con = xong || cham ? null : (1 - phan) * (du[vi] || 0) + cong(du.slice(vi + 1));
  const cuoi = xong ? t(td.xong) : td.loi_luc ? t(td.loi_luc) : bay, daChay = Math.max(0, (cuoi - t(td.bat_dau || moc.o_trong)) / 1000) || 0;
  const so = (x, n) => hai(+x || 0) + '/' + hai(n);
  const thu = TD8.ma.map((m, i) => {   // từng bước: trạng thái và chữ cột phải
    if (xong || i < vi) { const sau = TD8.ma.slice(i + 1).map(x => moc[x]).find(Boolean) || td.xong, dr = td.drive || {};
      if (m === 'drive' && td.drive_tat) return {tt: 'bo', cot: TD8.tat};   // QĐ278 Z21 dòng 5
      if (m === 'drive' && dr.nen) return {tt: 'nen', cot: TD8.sauLen};   // QĐ258, QĐ261 dòng 2: Drive đẩy nền sau khi bản mới lên
      if (m === 'drive' && !moc.drive) return {tt: 'bo', cot: TD8.chuaNoi};   // QĐ255 điểm 3: Drive chưa nối
      if (m === 'drive' && dr.tong && (+dr.da || 0) < dr.tong) return {tt: 'bo', cot: TD8.chuaLenHet};   // "Vẫn cập nhật" khi quá giờ
      return {tt: 'xong', cot: TD8.uoc.includes(m) ? TD8.xong : moc[m] && sau ? mmss((t(sau) - t(moc[m])) / 1000) : ''}; }
    if (i > vi) return {tt: 'cho', cot: TD8.uoc.includes(m) ? TD8.uocTinh : m === 'kiem' ? TD8.sauTaiLai : ''};   // QĐ261 dòng 3
    if (td.loi) return {tt: 'loi', cot: TD8.chuaDuoc};
    if (cham) return {tt: 'cham', cot: TD8.cham};
    return {tt: 'dang', cot: m === 'chup' && ct.tong ? so(ct.da, ct.tong) + TD8.tep : m === 'kiem' && ct.tong ? so(ct.da, ct.tong)
      : TD8.cot[m] || (TD8.uoc.includes(m) ? TD8.uocTinh : '')};
  });
  return {vi, pt, cham, con, daChay, thu, xong};
}
function htmlTienDo(td, o) {   // o: {bay, cu (bản đang chạy), kiem (kiểm sau cập nhật), quaGio, choViec}
  const r = tinhTienDo(td, o.bay), M = TD8.mau, b = td.buoc, ct = td.chi_tiet || {}, ten = TD8.ten[r.vi] || '';
  const tt = r.xong ? 'xong' : td.loi ? 'loi' : r.cham || o.quaGio ? 'cham' : 'dang', mau = M[tt];
  const so = (x, n) => hai(+x || 0) + '/' + hai(n);
  const kiem = o.kiem && o.kiem.chu ? cum(CHU_CN.kiem + o.kiem.chu) : '';   // QĐ255 điểm 5: kiểm chưa đạt thì phần này đỏ + circle-alert
  const dong = r.xong ? '<b>' + TD8.xongBuoc + '</b>' + (!kiem ? '' : o.kiem.dat === false ? ' · <span style="color:' + M.loi + '">'
      + icoMau(ICON['circle-alert'], M.loi, 14).replace('vertical-align:middle', 'vertical-align:middle;margin-right:4px') + kiem + '</span>' : ' · ' + kiem)   // Y41e: khoảng hở bằng lề icon, không thêm dấu cách
    : td.loi ? '<b>' + TD8.dung(r.vi + 1) + '</b> ' + cum(ten + ' ' + TD8.chuaDuoc + (td.loi_ct ? ' (' + td.loi_ct + ')' : ''))
    : o.quaGio ? '<b>' + TD8.buoc(3) + '</b> ' + cum(TD8.quaChu)
    : '<b>' + TD8.buoc(r.vi + 1) + '</b> ' + cum(ten + (b === 'chup' && ct.tong ? ' · ' + so(ct.da, ct.tong) + TD8.tep : b === 'kiem' && ct.tong
      ? ' · ' + so(ct.da, ct.tong) + TD8.diem : '') + (TD8.uoc.includes(b) ? TD8.sauUoc : '') + (r.cham ? TD8.thuongLe : ''));
  const gio = r.xong ? TD8.tong + mmss(r.daChay) : TD8.daChay + mmss(r.daChay)
    + (td.loi || o.quaGio ? '' : r.cham ? TD8.chuaUoc : r.con < 60 ? TD8.conDuoi : TD8.conKhoang(Math.ceil(r.con / 60)));
  const phu = r.xong ? TD8.phuXong : td.loi ? TD8.phuLoi(o.cu || td.tu) : o.quaGio ? TD8.phuQua : o.choViec || (r.cham ? TD8.phuCham : TD8.phuDang);
  const ico = {xong: ['circle-check', M.xong], dang: ['loader', M.dang], cho: ['circle', M.cho], cham: ['clock', M.cham], loi: ['circle-alert', M.loi],
    bo: ['circle-minus', M.cho], nen: ['cloud-upload', M.cho]};
  const hang = r.thu.map((x, i) => { const y = o.quaGio && i === 2 ? {tt: 'cham', cot: TD8.quaGio} : x;
    return '<div class="td8-dong ' + (y.tt === 'xong' || y.tt === 'cho' ? y.tt : y.tt === 'bo' || y.tt === 'nen' ? 'cho' : 'dang') + '">' + icoMau(ICON[ico[y.tt][0]], ico[y.tt][1], 15)
      + '<span class="f1">' + (i + 1) + '. ' + TD8.ten[i] + '</span><span class="td8-m">' + y.cot + '</span></div>'; }).join('');
  const vong = c => '<circle cx="48.0" cy="48.0" r="42.0" fill="none" style="stroke:' + c + '" stroke-width="10"';
  return '<div class="giua" style="width:96px;height:96px"><svg width="96" height="96" viewBox="0 0 96 96">' + vong('var(--xam)') + '/>' + vong(mau)
    + ' stroke-linecap="round" stroke-dasharray="' + (r.pt / 100 * 263.9).toFixed(1) + ' 263.9" transform="rotate(-90 48.0 48.0)"/></svg>'
    + '<b class="td-so" style="color:' + mau + '">' + r.pt + '%</b></div><div class="f1"><div class="t20 b7">'
    + esc(r.xong ? TD8.daLen(td.den) : td.loi ? TD8.chuaLen(td.den) : TD8.dang(td.den)) + '</div>'
    + '<div class="td-buoc" style="color:' + (tt === 'dang' ? M.chu : mau) + '">' + dong + '</div>'
    + '<div class="td" style="height:10px;margin-top:8px"><div class="tdf" style="width:' + r.pt + '%;background:' + mau + '"></div></div>'
    + '<div class="td-gio phu">' + gio + '</div><div class="phu" style="margin-top:4px">' + cum(phu) + '</div>'
    + (td.loi ? '<div class="dong" style="margin-top:10px"><button class="btn btn-chinh nho" data-cnngay>' + icoMau(ICON['refresh-cw'], 'var(--chu-tren-nut)', 16)
      + TD8.thuLai + '</button></div>' : '') + '<div class="td8">' + hang + '</div></div>';
}
function veTienDo(td, o) {   // td = null: thẻ cũ (quay về bản trước, máy chủ chưa có tiến độ)
  const e = $('[data-s="cn:dangcn"]'); if (!e) return;
  if (veTienDo.goc == null) veTienDo.goc = e.innerHTML;
  if (!td) { if (e.dataset.td) { e.innerHTML = veTienDo.goc; delete e.dataset.td; e.classList.remove('vien-do'); } return; }
  e.innerHTML = htmlTienDo(td, o); e.dataset.td = '1'; e.classList.toggle('vien-do', !!td.loi);
}
// </TD8>
function theoKiem() {   // QĐ258, QĐ261: trang đã chạy bản mới; kiểm 06 điểm, đẩy Drive chạy nền → hỏi lại máy chủ, vẽ lại mỗi lượt
  const NHIP_GIAY = 10, PHUT_THEO = 15;   // tối đa 15 phút cho 01 lần mở trang; Drive lỗi vẫn hỏi theo nhịp này để lần đẩy lại thành công tự hiện (CDO U21 G2)
  if (D.theoKiem || (D.theoKiemTu && Date.now() - D.theoKiemTu > PHUT_THEO * 60e3)) return;
  D.theoKiem = true; D.theoKiemTu = D.theoKiemTu || Date.now();
  const hoi = async () => {
    let tiep = true;
    try { const s = await api('/capnhat'), t = s.tien_do, dn = t && t.drive_nen;
      tiep = !!t && !t.loi && !t.treo && (t.buoc !== 'xong' || !!(dn && dn.tong && dn.da < dn.tong));   // G2: Drive lỗi vẫn hỏi
      veCapNhat(s); }
    catch (e) { /* mạng chập chờn: hỏi lại lượt sau */ }
    if (tiep && Date.now() - D.theoKiemTu < PHUT_THEO * 60e3) setTimeout(hoi, NHIP_GIAY * 1000); else D.theoKiem = false;
  };
  setTimeout(hoi, NHIP_GIAY * 1000);
}
function choCapNhat(cu, moi, s0) {   // s0: kết quả /api/capnhat đã có (mở trang giữa lúc đang cập nhật)
  S.cn = 'dangcn'; tieuDangCn(); ve(); veQuayVe(D.capnhat || {});   // N33: khóa quay về
  const PHUT_CHO = 35;   // QĐ255 điểm 1: watchtower chờ tối đa 30 phút (QĐ252) + dư. 0.8.1 GAP-080: `het` ở dòng riêng
  const DU_PHUT = PHUT_CHO - 30;   // phần dư 05 phút của QĐ255, dùng chung cho giới hạn riêng bước 3, 4
  const GIOI_HAN_PHUT = {day: 10, cho_viec: 30};   // giới hạn chờ của máy chủ: đẩy Drive (CHO_DRIVE_GIAY), chờ việc AI (CHO_TOIDA_GIAY)
  let het = Date.now() + PHUT_CHO * 60e3;   // cách cũ: tính từ lúc bấm, khi máy chủ chưa có tiến độ
  const datHet = (t, dang) => {   // Y41d (CDA N6): mốc hết giờ theo bước, không báo hỏng oan lúc chờ việc AI, chờ Drive
    const moc = t.moc || {}, may = x => Date.parse(x) - ((Date.parse(t.luc) - Date.now()) || 0);   // giờ máy chủ → giờ trang
    const h = moc.tai ? may(moc.tai) + PHUT_CHO * 60e3                                             // bước 5–8: 35 phút từ bước 5
      : dang === 'qua_gio' ? Infinity                                                                // chờ bạn chọn ở hộp Drive
      : GIOI_HAN_PHUT[dang] ? may(moc[dang === 'day' ? 'drive' : 'gui']) + (GIOI_HAN_PHUT[dang] + DU_PHUT) * 60e3
      : moc[t.buoc] ? may(moc[t.buoc]) + PHUT_CHO * 60e3   // bước khác (chụp, gửi lệnh): 35 phút từ đầu bước, như cách cũ
      : NaN;
    if (!Number.isNaN(h)) het = h; };   // không tính được thì giữ mốc đang có
  const hien = (s, them) => { const t = s.tien_do; if (!t) return false;
    D.td = {t, lech: (Date.parse(t.luc) - Date.now()) || 0, o: {cu, kiem: s.kiem_hien, ...them}};
    datHet(t, s.dang_sao); veTienDo(t, {...D.td.o, bay: Date.now() + D.td.lech}); return true; };
  if (s0) hien(s0, {});
  const cho = async () => {
    try { const r = await fetch('/suckhoe', {cache: 'no-store'}); if (r.status === 421) { const e = new Error((await r.text()).replace(/<[^>]*>/g, '')); e.s421 = true; throw e; } const k = await r.json();   // QĐ656: 421 = tên không hợp lệ
      // QĐ258 (đổi QĐ253): bản mới chạy là tải lại ngay; kiểm 06 điểm chạy nền, kết quả hiện sau (theoKiem)
      if (k.phienban && k.phienban !== cu) { location.hash = DAU_SAU_CN; location.reload(); return; } else {   // G1: về Cập nhật
        const s = await api('/capnhat');   // lớp 5: bước bản sao đang chạy; lỗi bản sao thì dừng, không gửi lệnh
        if (s.sao_loi && !s.dang_sao) { if (s.tien_do && s.tien_do.loi) { hien(s, {}); return; }   // QĐ253: lỗi bước 1–4 có nút Thử lại
          S.cn = 'hong'; $('#cn-lydo').textContent = 'Lý do: ' + s.sao_loi + '.'; ve(); return; }
        if (!hien(s, {quaGio: s.dang_sao === 'qua_gio', choViec: s.dang_sao === 'cho_viec' ? CHU_CN.sao.cho_viec : null})) {
          const b = CHU_CN.sao[s.dang_sao];
          $('[data-s="cn:dangcn"] .phu').textContent = b ? b + (s.dang_sao === 'gui' || s.dang_sao === 'tai' ? (s.sao_den || moi) : '') : CHU_CN.cho; }
        if (s.dang_sao === 'qua_gio') { D.capnhat = {...D.capnhat, ...s}; if ($('#h-cndrive') ? $('#h-cndrive').hidden : true) moHopDrive('qua_gio'); }
      }
    } catch (e) { if (e.s421) { S.cn = 'hong'; $('#cn-lydo').textContent = e.message; ve(); return; }   // QĐ656: dừng chờ
      if (D.td) veTienDo(D.td.t, {...D.td.o, bay: Date.now() + D.td.lech}); }   // máy chủ đang thay bản: % đi theo giờ
    if (Date.now() < het) setTimeout(cho, 5000);
    else { S.cn = 'hong'; $('#cn-lydo').textContent = 'Lý do: sau ' + hai(PHUT_CHO) + ' phút máy chủ vẫn chạy bản ' + cu
      + '. Phần mềm vẫn chạy bình thường bằng bản này.'; ve(); }   // QĐ255 điểm 1
  };
  setTimeout(cho, 5000);
}
async function chonDrive(van) {   // nút Hủy, Vẫn cập nhật trong hộp bản sao Drive
  const k = D.cnDrive || {}; dongHop();
  if (k.loai === 'qua_gio') { try { await api('/capnhat/tieptuc', {van}); } catch (e) { if (e.status) bao(e.message); return; }
    if (!van) { S.cn = 'coban'; ve(); } return; }
  if (van) await capNhat(k.cheDo || 'ngay', true);
}

// ---- Màn 13 Mô hình AI: thẻ gói Claude, gói ChatGPT, khóa API; bảng mô hình mặc định
// QĐ172, QĐ176, QĐ177 (Z9, Z9b, Z9c; từ điển dòng 60, 61): tên nguồn đứng riêng "Hãng · Công cụ", viết ở 01 chỗ này.
// Chỉ đổi chữ trên giao diện: tên lưu trong bảng nguồn AI giữ nguyên (F04, câu chuông "Gói Claude …" vẫn dùng tên gói).
const NB = '\u00a0';   // dấu "·" nối không ngắt 02 bên
const TEN_NGUON_GOI = {claude: 'Claude' + NB + '·' + NB + 'Code', chatgpt: 'ChatGPT' + NB + '·' + NB + 'Codex'};
const TEN_NGUON_HANG = {anthropic: 'Claude · API', openai: 'OpenAI · API', google: 'Gemini · API', openrouter: 'OpenRouter · API',
  groq: 'Groq · API', deepseek: 'DeepSeek · API', ollama: 'Ollama · Cloud'};
// Y31c S3 (QĐ186): tài khoản 02 trở đi ghi thêm "· Tài khoản N"; tài khoản 01 giữ "Claude · Code"
const tenNguon = n => !n ? '' : n.goi ? TEN_NGUON_GOI[n.goi] + (n.taikhoan > 1 ? NB + '·' + NB + 'Tài' + NB + 'khoản' + NB + n.taikhoan : '')
  : (n.loai === 'khoa_api' && TEN_NGUON_HANG[n.hang] ? TEN_NGUON_HANG[n.hang].replace(' · ', NB + '·' + NB) : n.ten);
const GOI_TEN = TEN_NGUON_GOI;   // tiêu đề thẻ gói
const GOI_NGAN = {claude: 'Gói Claude', chatgpt: 'Gói ChatGPT'};   // chỉ còn lấy tên hãng ("Thêm tài khoản Claude khác")
// N15: tên mô hình đọc được từ mã mô hình (claude-sonnet-4-6 → Claude Sonnet 4.6); chưa có lần gọi nào ghi mô hình
// thì ghi "mô hình mặc định" (gói chạy mô hình mặc định của gói).
const tenMoHinh = ma => { if (!ma) return 'mô hình mặc định'; const p = String(ma).split(/[-_\s]+/);
  const chu = p.filter(x => !/^\d+(\.\d+)*$/.test(x)).map(x => /^gpt$/i.test(x) ? 'GPT' : x.charAt(0).toUpperCase() + x.slice(1));
  const so = p.filter(x => /^\d+(\.\d+)*$/.test(x) && x.length < 6).join('.');
  return chu.join(' ') + (so ? ' ' + so : ''); };
// QĐ178, QĐ179, QĐ181 (Z10b): tên mô hình ngắn, viết hoa, bỏ tên hãng khi chỗ đó đã ghi nguồn ("Claude · Code · Sonnet");
// số bản chỉ thêm khi 01 nguồn có 02 bản cùng tên ("Opus 4.1", "Opus 4"); tên có "/" (hãng trung gian đặt, ví dụ
// "Claude 3.5 Haiku") giữ nguyên thứ tự. 01 hàm `tenMh` dùng chung mọi chỗ ghi tên mô hình.
const chuHoa = x => /^gpt$/i.test(x) ? 'GPT' : x.charAt(0).toUpperCase() + x.slice(1);
const laSo = x => /^\d+(\.\d+)*$/.test(x);
const phanMh = ma => { const p = String(ma).split(/[-_\s]+/).filter(Boolean);
  return {chu: p.filter(x => !laSo(x)).map(chuHoa), so: p.filter(x => laSo(x) && x.length < 6).join('.')}; };
const hangCua = n => (tenNguon(n) || '').split(NB + '·')[0].split(' · ')[0].trim().toLowerCase();
const gocMh = (ma, hang) => { const {chu} = phanMh(ma); return (chu.length > 1 && hang && chu[0].toLowerCase() === hang ? chu.slice(1) : chu).join(' '); };
// 0.7.6 (QĐ187): nhóm theo loại nguồn; tìm được bằng mã nhóm hoặc mã 01 tài khoản trong nhóm
const nhomMh = id => D.dsmh && id ? D.dsmh.nhom.find(g => g.nhom === id || (g.nguon_ids || []).includes(id)) : null;
// Tên hãng khác Claude: giữ nguyên thứ tự và số ("gpt-5-codex" → "GPT-5 Codex", "gpt-4.1" → "GPT-4.1", "o3" → "o3").
const tenHang = s => { const p = String(s).split(/[-_\s]+/).filter(Boolean), gpt = /^gpt$/i.test(p[0]) && p.length > 1;
  const chu = x => laSo(x) || /^o\d/i.test(x) || /^\d/.test(x) ? x : chuHoa(x);
  return [...(gpt ? ['GPT-' + p[1]] : [chu(p[0])]), ...p.slice(gpt ? 2 : 1).map(chu)].join(' '); };
const tenMh = (ma, nguonId, n, ngan) => { if (!ma) return 'mô hình mặc định';   // ngan: N3, không thêm số bản
  if (String(ma).includes('/')) return String(ma).split('/').pop().split(/[-_\s]+/).filter(Boolean).map(chuHoa).join(' ');
  const g = nhomMh(nguonId), hang = hangCua(n || g || timNguon(nguonId));
  if (hang !== 'claude') return tenHang(ma);   // Y31b S2: quy tắc bỏ hãng, bỏ số chỉ áp cho Claude (QĐ179, QĐ181)
  const goc = gocMh(ma, hang), {so} = phanMh(ma);
  const trung = !ngan && g && g.mohinh.some(m => m.ma !== ma && gocMh(m.ma, hang) === goc);
  return goc + (trung && so ? ' ' + so : ''); };
const moHinhDong = (ma, n) => tenMh(ma, n && (n.id || n.nguon_id), n);
const dongNguon = n => tenNguon(n) + ' · ' + moHinhDong(n.mohinh_gannhat, n);
// Dòng dưới câu trả lời màn 08 (Z10a): "Claude · Code · Sonnet 4.5" theo mã nguồn; không tìm được nguồn thì giữ chữ máy chủ trả
const timNguon = id => id && D.md ? D.md.nguon.find(n => n.id === id) : null;
// Y31c S4 (QĐ186): mô hình công cụ báo về; không có thì mô hình đã gửi; không có nữa thì "Mặc định" (như nút), không lấy mô hình cũ
const mhThucDung = x => x.mohinh_bao || x.mohinh || null;
// QĐ189 (Z11): dòng nguồn ghi "Hãng · Công cụ · Mô hình", không ghi tài khoản; tài khoản thực chạy chỉ hiện khi rê chuột
// Z11b (QĐ189): cảnh báo khi thêm tài khoản thứ 02 cho cùng 01 gói; chữ IGM360 tự viết
const canhTk = ten => '<div class="canh-tk">' + icoMau(ICON['circle-alert'], 'var(--xem)', 14) + '<span>Lưu ý: dùng nhiều tài khoản ' + ten
  + ' trên cùng phần mềm, hãng có thể khóa tài&nbsp;khoản.</span></div>';
const tenLoai = n => n && n.goi ? TEN_NGUON_GOI[n.goi] : tenNguon(n);
const nhanTraLoi = x => { const n = timNguon(x.nguon_id), mh = mhThucDung(x);
  return n ? tenLoai(n) + ' · ' + (mh ? tenMh(mh, n.id, n, true) : 'Mặc định') : (x.nguon || 'Trợ lý AI'); };   // N3: tên ngắn
const tieuTraLoi = x => { const p = [], mh = mhThucDung(x), dp = x.du_phong;
  if (mh) p.push('Bản cụ thể: ' + mh);
  if (x.chay_tk) p.push('chạy bằng tài khoản ' + x.chay_tk + (dp && dp.tk ? ' (dự phòng, ' + (dp.rieng ? chuHetMh(dp, timNguon(x.nguon_id), dp.tk)
    : 'tài khoản ' + dp.tk + ' đang tạm nghỉ' + (dp.den ? ' đến ' + denLuc(dp.den) : '')) + ')' : ''));   // Y36f N8
  return p.join(' · '); };
const logoGoi = g => g === 'claude'
  ? '<span class="logo-o" data-hang="Claude" title="Claude" style="width:40px;height:40px">' + ICON.logo_claude + '</span>'
  : '<span class="logo-o" data-hang="ChatGPT" title="ChatGPT" style="width:40px;height:40px">' + ICON.logo_chatgpt + '</span>';   // QĐ92: logo gốc OpenAI, giữ đen
const usd = v => Number(v || 0).toFixed(2).replace('.', ',') + '&nbsp;USD';
// Tiền đủ 02 cột (QĐ50, QĐ122): USD kèm đồng Việt tham khảo; chưa có tỷ giá (trước ngày 18) thì ghi rõ.
const vnd = (v, tg) => tg ? '≈&nbsp;' + soVN(Math.round(Number(v || 0) * tg / 1000) * 1000) + '&nbsp;đ tham&nbsp;khảo' : 'chưa có tỷ&nbsp;giá';
// N09: dòng dưới "Tài khoản 1": lúc đăng nhập gói (F04); chưa có dòng nào là đăng nhập lúc cài máy.
const dnLuc = x => !x.dangnhap_luc ? 'Đăng nhập lúc cài&nbsp;máy'
  : Date.now() - Date.parse(x.dangnhap_luc) < 10 * 60e3 ? 'Vừa đăng nhập' : 'Đăng nhập lúc&nbsp;' + esc(luc(x.dangnhap_luc));
const pct = v => v == null ? null : Math.max(0, Math.min(100, Number(v)));
// Z12: thanh giữ số cũ khi vẽ lại rồi trượt tới số mới (0,4 giây), không nháy
D.hmCu = {};
function thanhHm(ten, v, k) { const p = pct(v), cu = k && k in D.hmCu ? D.hmCu[k] : (p ?? 0); if (k) D.hmCu[k] = p ?? 0;
  return '<div class="hm"><span class="t12 phu nw">' + ten + '</span><div class="td" style="height:8px"><div class="tdf" data-w="' + (p ?? 0) + '" style="width:'
  + cu + '%;background:' + (p >= 90 ? 'var(--h-canh)' : 'var(--h-chinh)') + '"></div></div><b class="t12 so">' + (p == null ? 'chưa&nbsp;đo' : Math.round(p) + '%') + '</b></div>'; }
// Y36b, Y36c N4: "Opus của tài khoản 1 hết hạn mức đến 20:45" (khác ngày: "đến 20:45 ngày 26/11"); dùng chung màn 13 và khung chat
const denLuc = iso => !iso ? '' : gio(iso) + (hien(iso).slice(0, 10) !== homNay() ? ' ngày ' + hien(iso).slice(8, 10) + '/' + hien(iso).slice(5, 7) : '');
const tenHet = (m, n) => m.ma ? tenMh(m.ma, n && n.id, n, true) : m.ten_khung || (m.bao ? tenMh(m.bao, n && n.id, n, true) : '');
const chuHetMh = (m, n, tk) => chuHoa(tenHet(m, n) || 'mô hình mặc định') + ' của tài khoản ' + tk + ' hết hạn mức' + (m.den ? ' đến ' + denLuc(m.den) : '');
// N5: cả tài khoản đang tạm nghỉ thì ghi lý do tài khoản (như dòng vàng P3b); chỉ 01 mô hình hết riêng thì ghi tên mô hình
const tieuHetMh = (n, tk) => n.tk_nghi_den ? ' title="' + esc('Tài khoản ' + tk + ' đang tạm nghỉ đến ' + denLuc(n.tk_nghi_den)) + '"'
  : !(n.het_mh || []).length ? '' : ' title="' + esc(n.het_mh.map(m => chuHetMh(m, n, tk)).join('; ')) + '"';
// 0.7.8 (QĐ198, QĐ200): mã dài hạn gói Claude. Tên chỉ ở 01 chỗ (CPO trình anh chốt tên); không bao giờ hiện mã,
// chỉ 04 ký tự cuối. Màu Cảnh báo trong 14 ngày cuối do máy chủ tính lúc hỏi (`vang`), không lưu.
const CHU_MDH = 'Mã dài hạn';   // QĐ208: tên đã chốt (từ điển dòng 74)
D.mdh = {};   // {tk: {url, loi, ct}}: hộp "Đang kết nối" đang mở của tài khoản tk (Z13 trạng thái 2)
// Dòng mã trong ô tài khoản (Z13 trạng thái 3, 4, 5): nhãn mã chiếm hết bề ngang, nút xếp hàng riêng (N11);
// 14 ngày cuối màu Cảnh báo (N12, QĐ200); hết hạn: nhãn đỏ, câu "ngừng chạy" (N13)
// QĐ214, QĐ216, QĐ217: 23 câu chữ anh đã duyệt (bảng Z15 dòng 1–15, Z15b dòng 16–23), viết ở 01 chỗ này
const CHU_Z15 = {
  iRe: 'Mã dài hạn là gì?', iTieu: 'Mã dài hạn',                                                                   // 01, 02
  iDong: [['brain-circuit', 'Đăng nhập kiểu cũ có thể hết phiên giữa chừng: bot và việc nền dừng theo. Mã dài hạn giữ kết nối ổn định.'],   // 03
    ['calendar', 'Mỗi mã dùng 365 ngày. Mã mới chỉ cấp khi bạn đăng nhập trang claude.ai.'],                              // 04
    ['bell', 'Trước hạn 07 ngày, chuông nhắc mỗi ngày; bạn bấm "Lấy mã mới" là xong.'],                                   // 05
    ['log-in', 'Cách 1 (nên dùng): bấm "Kết nối Claude", máy chủ tự chạy lệnh; bạn chỉ đăng nhập claude.ai và dán mã xác nhận.'],   // 06
    ['key-round', 'Cách 2: khi máy chủ không tự lấy được, chạy lệnh claude setup-token ở máy khác rồi bấm "Dán mã".'],      // 07
    ['wallet', 'Mã vẫn tính vào gói Claude của bạn: việc chạy nền tính như khi đăng nhập gói.']],                        // 08
  iNhac: 'Mã dài hạn chỉ dán vào ô "Dán mã". Không chụp ảnh, không gửi qua tin nhắn.', iNut: 'Đã hiểu',                 // 09, 10
  danLenh: 'Tạo mã ở máy có Claude Code, chạy lệnh:', lenh: 'claude setup-token', chep: 'Chép', daChep: 'Đã chép.',      // 11
  thuHoi: 'Thu hồi mã cũ ở trang ', thuHoiTrang: 'claude.ai/settings/claude-code',                                      // 12
  b2: 'Trang hiện 01 mã xác nhận. Chép mã đó, dán vào ô dưới.',                                                         // 13
  b2Phu: 'Máy chủ tự đổi thành mã dài hạn, cất ở Két khóa; bạn không cần chép mã dài hạn.', b2O: 'Mã xác nhận',         // 14, 15
  kiemDat: 'Kiểm mã · đạt ', kiemLoi: 'Kiểm mã · chưa được ', kiemLoiRe: 'Claude chưa nhận mã này. Bấm Lấy mã mới hoặc Dán mã lại.',   // 16, 17
  chuaKiem: 'Chưa kiểm được trùng tài khoản',                                                                           // 18
  chuaKiemRe: 'Phần mềm chưa có tên, gói của tài khoản này nên chưa so được với tài khoản khác. Mã vẫn dùng bình thường.',
  hdTieu: 'Làm 01 lần để hiện tên, gói', hdNut: 'Lấy tên, gói',                                                         // 19
  hdChu: 'Bấm "Lấy tên, gói", đăng nhập đúng tài khoản Claude này; phần mềm tự ghi tên, gói và giữ nguyên mã dài hạn.',
  layMoi: 'Lấy mã mới · tài khoản ', dungTk: 'Đăng nhập đúng tài khoản ',                                               // 20, 21
  danTrong: 'Bạn dán mã dài hạn vào ô', chuaTron: n => 'Mã vừa dán có ' + n + ' ký tự, chưa trọn. Chép lại cả mã rồi dán lại.',   // 23 (22 ở máy chủ)
  // Y38c CPO-1: CHỮ MỚI, CHƯA DUYỆT (CPO trình anh) — chuỗi dán vào không có sk-ant-oat01-
  // Y38d: CHỮ MỚI CHỜ ANH DUYỆT (CPO trình): N30 khóa API, sai tiền tố (CDO đề xuất); N34 trình duyệt chặn chép; N37 gọi thử hết hạn mức
  khoaApi: 'Đây là khóa API, không phải mã dài hạn. Khóa API thêm ở thẻ Khóa API.',
  saiTienTo: 'Đây không phải mã dài hạn (mã bắt đầu bằng sk-ant-oat01-).',   // QĐ219 A2
  chepLoi: 'Trình duyệt chặn chép. Bạn bôi đen lệnh rồi chép tay.',   // QĐ219 A14
  kiemHanMucRe: 'Mã đã lưu; lần gọi thử gặp hết hạn mức của gói nên chưa kiểm được mã.'};
// Y38f L3 (Z17): A8 "Lấy tên, gói" đăng nhập nhầm, mã giữ nguyên: ô báo lỗi chữ đỏ + nút làm lại "Lấy tên, gói"
const coBaoLayLai = (g, tk) => !!(D.trung[g] && (D.trungTk || {})[g] === tk && (D.trungChu || {})[g]);   // Y38f L3, Y38h L4
const baoLayLai = (chu, tk) => '<div class="bao-lai t13"><div class="loi-o">' + ICON['circle-alert'] + '<span>'
  + cum(cau(chu)).split(CHU_Z15.hdNut).join('<b>' + nbsp(CHU_Z15.hdNut) + '</b>') + '</span></div>'
  + '<button class="btn btn-phu nho" data-dn-goi="claude" data-dn-tk="' + tk + '">' + icoMau(ICON['log-in'], 'var(--chu)', 16) + nbsp(CHU_Z15.hdNut) + '</button></div>';
const giuTienTo = h => String(h).split('sk-ant-oat01-').join('<span class="nw">sk-ant-oat01-</span>');   // Y38d N42
// N28 (a): làm sạch mã dán vào như máy chủ (bỏ khoảng trắng, xuống dòng, ký tự ẩn; nhận dạng TÊN=mã, dấu nháy)
function lamSachMa(s) { let m = String(s || '').replace(/[\s\u200b\u200c\u200d\u2060\ufeff]+/g, '');
  const i = m.indexOf('sk-ant-oat01-'); if (i > 0) m = m.slice(i);   // Y38c R9: chữ đứng trước mã bỏ đi
  return m.replace(/^['"`]+|['"`]+$/g, ''); }
const nutMdGt = () => '<button class="nut-i" data-md-gt title="' + CHU_Z15.iRe + '">' + icoMau(ICON['info'], 'var(--phu)', 14) + '</button>';   // 01
const gioKiem = iso => hien(iso).slice(0, 10) === homNay() ? gio(iso) : hien(iso).slice(8, 10) + '/' + hien(iso).slice(5, 7) + ' ' + gio(iso);   // hôm khác ghi ngày
function theMd(x, go) {
  const md = x.ma_daihan, tk = x.taikhoan, canh = md && (md.het || md.vang), k = x.kiem_md;
  let h = '';
  if (md) h += '<div class="md-chip' + (canh ? ' canh' : '') + '">' + icoMau(ICON['key-round'], canh ? 'var(--canh)' : 'var(--dat)', 13)
    + (md.het ? CHU_MDH + ' hết hạn ' + esc(ngay(md.han)) : CHU_MDH + ' ••••' + esc(md.kytu_cuoi || '')) + '</div>' + nutMdGt()
    + (md.het ? '<div class="md-han canh">tài khoản ' + tk + ' ngừng&nbsp;chạy</div>'
      : '<div class="md-han' + (canh ? ' canh' : '') + '">hết hạn ' + esc(ngay(md.han)) + '</div><div class="md-han' + (canh ? ' canh' : '') + '">còn ' + hai(md.con_ngay) + '&nbsp;ngày</div>');
  else if (x.da_noi) h += '<div class="md-chip xem">Đăng nhập kiểu&nbsp;cũ</div>' + nutMdGt() + '<div class="md-han xem">có thể hết phiên giữa&nbsp;chừng</div>';
  if (md && k) h += k.dat ? '<div class="md-han dat-chu dong-i">' + icoMau(ICON['circle-check'], 'var(--dat)', 13) + nbsp(CHU_Z15.kiemDat + gioKiem(k.luc)) + '</div>'   // 16
    : '<div class="md-han canh dong-i" title="' + (k.het_hanmuc ? CHU_Z15.kiemHanMucRe : CHU_Z15.kiemLoiRe) + '">' + icoMau(ICON['circle-alert'], 'var(--canh)', 13) + nbsp(CHU_Z15.kiemLoi + gioKiem(k.luc)) + '</div>';   // 17
  const chuaKiem = md && !md.het && x.chua_kiem_trung;   // QĐ216 N6
  if (chuaKiem) h += '<div class="md-han xem" title="' + CHU_Z15.chuaKiemRe + '">' + nbsp(CHU_Z15.chuaKiem) + '</div>';   // 18
  h += '<div class="md-nut">';
  if (md) h += '<button class="btn-chu" data-md-lay="' + tk + '">' + ICON['refresh-cw'] + 'Lấy mã&nbsp;mới</button><button class="btn-chu" data-md-dan="' + tk + '">' + ICON['key-round'] + 'Dán mã</button>';
  else if (x.da_noi) h += '<button class="btn btn-phu nho" data-md-lay="' + tk + '">' + ICON['key-round'] + 'Chuyển sang ' + CHU_MDH.toLowerCase().replace(/ /g, '&nbsp;') + '</button>';
  h += go + '</div>';
  if (chuaKiem && !coBaoLayLai('claude', tk)) h += '<div class="md-hd"><div class="b6 t13">' + CHU_Z15.hdTieu + '</div><div class="t13">' + cum(CHU_Z15.hdChu) + '</div>'   // 19
    + '<button class="btn btn-phu nho" data-dn-goi="claude" data-dn-tk="' + tk + '">' + ICON['user-check'] + nbsp(CHU_Z15.hdNut) + '</button></div>';
  return h;
}
function moMdGt() {   // hộp (i) "Mã dài hạn" (QĐ214, Z15 dòng 02–10)
  if (!$('#h-mdgt')) $('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-mdgt" hidden><div class="hop" style="max-width:500px"><div class="hop-dau">'
    + ICON['key-round'] + '<b class="f1 t16">' + CHU_Z15.iTieu + '</b><button class="nut-ico" data-dong>' + icoMau(ICON.x, 'var(--phu)', 20) + '</button></div><div class="hop-than">'
    + CHU_Z15.iDong.map(([i, c]) => '<div class="dong t13 md-gt">' + icoMau(ICON[i], 'var(--xanh-chu)', 16) + '<span>'
      + cum(c).replace(CHU_Z15.lenh, '<span class="nw">' + CHU_Z15.lenh + '</span>') + '</span></div>').join('')   // lệnh không ngắt dòng
    + '<div class="bao-vang t13">' + ICON['circle-alert'] + '<span>' + cum(CHU_Z15.iNhac) + '</span></div></div>'
    + '<div class="hop-chan"><button class="btn btn-chinh" data-dong>' + CHU_Z15.iNut + '</button></div></div></div>');
  mo('h-mdgt'); }
// Z13 trạng thái 4c: ô báo viền đỏ dưới ô tài khoản có mã hết hạn
const theMdHet = (x, ds) => { const con = (ds || []).find(y => y.taikhoan !== x.taikhoan && y.da_noi && !(y.ma_daihan && y.ma_daihan.het));
  return '<div class="md-het"><div class="dong t13 b6">' + icoMau(ICON['clock'], 'var(--canh)', 16) + '<span>' + CHU_MDH + ' tài khoản ' + x.taikhoan + ' hết hạn '
  + esc(ngay(x.ma_daihan.han)) + '</span></div><div class="t12 phu">' + (con ? 'Tài&nbsp;khoản&nbsp;' + x.taikhoan + ' ngừng chạy; phần mềm dùng tài&nbsp;khoản&nbsp;' + con.taikhoan
    + ' rồi tới nguồn kế&nbsp;tiếp.' : 'Claude ngừng chạy; phần mềm dùng nguồn kế&nbsp;tiếp.') + '</div>'
  + '<button class="btn btn-chinh nho" data-md-lay="' + x.taikhoan + '">' + ICON['refresh-cw'] + 'Lấy mã&nbsp;mới</button></div>'; };
// Z13 trạng thái 2: hộp "Đang kết nối" (N15, N16); câu lỗi chỉ tiếng Việt, câu gốc của Claude ở rê chuột (N17)
const tkClaude = tk => ((D.md && D.md.goi.claude) || []).find(x => x.taikhoan === tk) || {};
const tenTkClaude = tk => tkClaude(tk).ten_hien;
const theMdKetNoi = (tk, k) => '<div class="md-hop"><div class="b6 t13">' + (tkClaude(tk).ma_daihan ? nbsp(CHU_Z15.layMoi + tk)   // 20
  : 'Kết nối tài khoản ' + tk + ' bằng ' + CHU_MDH.toLowerCase()) + '</div>'
  + '<div class="t12 phu">Dùng 365&nbsp;ngày, không tự hết phiên giữa&nbsp;chừng; vẫn tính vào gói Claude của&nbsp;bạn.</div>'
  + (tenTkClaude(tk) ? '<div class="t12 xem-chu">' + CHU_Z15.dungTk + '<b>' + esc(tenTkClaude(tk)) + '</b></div>' : '')   // 21 (QĐ216 N7)
  + '<div class="buoc-dn"><span class="so-b">1</span><span class="f1">Mở trang claude.ai, đăng nhập tài&nbsp;khoản&nbsp;Claude của bạn để tạo ' + CHU_MDH.toLowerCase() + '.</span></div>'
  + '<div class="dong lk"><span class="t12 phu f1 cat">' + esc((k.url || '').replace(/^https?:\/\//, '')) + '</span><a class="btn btn-phu nho" href="' + esc(k.url || '') + '" target="_blank" rel="noopener noreferrer">' + ICON['external-link'] + 'Mở trang</a></div>'
  + '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">' + cum(CHU_Z15.b2) + '<span class="t12 phu khoi">' + cum(CHU_Z15.b2Phu) + '</span></span></div>'   // 13, 14
  + '<div class="dong"><div class="o-nhap f1' + (k.loi ? ' loi' : '') + '">' + ICON.hash + '<input id="md-ma-web" placeholder="' + CHU_Z15.b2O + '" autocomplete="off"></div><button class="btn btn-chinh" data-md-gui="' + tk + '">Xác nhận mã</button></div>'
  + (k.loi ? '<div class="loi-o"' + (k.ct ? ' title="' + esc(k.ct) + '"' : '') + '>' + ICON['circle-alert'] + '<span>' + cum(cau(k.loi)) + '</span></div>' : '')
  + '<div class="dong"><button class="btn-chu" data-md-lay="' + tk + '">' + ICON['refresh-cw'] + 'Lấy link mới</button><button class="btn-chu" data-md-huy="' + tk + '">Hủy</button></div></div>';
// Z13 trạng thái 6: hộp "Dán mã" riêng (N15); máy không lấy mã tự động được thì báo màu Thông tin (N18)
D.mdDan = null;   // {tk, loi, tin}
function moMdDan(tk, tin) {
  if (!$('#h-mdh')) $('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-mdh" hidden><div class="hop"><div class="hop-dau">' + ICON['key-round']
    + '<b class="f1 t16" id="mdh-tieu"></b><button class="nut-ico" data-dong>' + icoMau(ICON.x, 'var(--phu)', 20) + '</button></div><div class="hop-than" id="mdh-than"></div>'
    + '<div class="hop-chan"><button class="btn btn-phu" data-dong>Hủy</button><button class="btn btn-chinh" id="mdh-luu" data-md-luu="1">Lưu mã</button></div></div></div>');
  D.mdDan = {tk, loi: '', tin: tin || ''}; veMdDan(); mo('h-mdh'); const o = $('#md-ma-dan'); if (o) o.focus(); }
function veMdDan() { const k = D.mdDan; if (!k) return;
  $('#mdh-tieu').textContent = nbsp('Dán ' + CHU_MDH.toLowerCase()) + ' · ' + nbsp('Claude tài khoản ' + k.tk);   // N25
  $('#mdh-luu').dataset.mdLuu = k.tk;   // N27: nút Lưu mã mang đúng tài khoản đang dán
  $('#mdh-than').innerHTML = (k.tin ? '<div class="bao-xanh t13">' + ICON['info'] + '<span>' + cum(cau(k.tin)) + '</span></div>' : '')
    + '<div class="t13 phu">Dùng khi bạn đã tạo ' + CHU_MDH.toLowerCase() + ' ở máy khác. Mã bắt đầu bằng <b class="nw">sk-ant-oat01-</b>, dùng 365&nbsp;ngày.</div>'
    + '<div class="b6 t13">' + CHU_MDH + '</div><div class="o-nhap' + (k.loi ? ' loi' : '') + '">' + ICON['key-round'] + '<input id="md-ma-dan" type="password" placeholder="sk-ant-oat01-…" autocomplete="off"></div>'
    + (k.loi ? '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + giuTienTo(cum(cau(k.loi))) + '</span></div>' : '')
    + '<div class="t13">' + CHU_Z15.danLenh + '</div><div class="dong ma-lenh"><code class="f1">' + CHU_Z15.lenh + '</code>'   // 11
    + '<button class="btn btn-phu nho" data-md-chep>' + ICON.copy + CHU_Z15.chep + '</button></div>'
    + '<div class="t12 phu">' + CHU_Z15.thuHoi + '<a class="nw" href="https://' + CHU_Z15.thuHoiTrang + '" target="_blank" rel="noopener noreferrer">' + CHU_Z15.thuHoiTrang + '</a></div>'   // 12
    + '<div class="t12 phu">Phần mềm cất mã đã mã hóa ở Két&nbsp;khóa, trên màn chỉ hiện 04 ký tự&nbsp;cuối.</div>'; }
async function mdLay(tk) {   // 0.7.8: máy chủ chạy lệnh lấy mã của Claude; "Lấy link mới" chạy lại từ đầu
  try { const kq = await api('/mohinh/goi/claude/madaihan/batdau', {taikhoan: tk});
    if (kq.han) { await mdXong(tk, kq); return; }
    if (kq.khong_ho_tro) { D.mdh[tk] = null; veMoHinh(); moMdDan(tk, kq.loi); return; }
    D.mdh[tk] = {url: kq.url, loi: '', ct: ''}; veMoHinh(); const o = $('#md-ma-web'); if (o) o.focus(); }
  catch (e) { if (D.mdh[tk]) { D.mdh[tk] = {...D.mdh[tk], loi: e.message, ct: (e.ct || {}).chi_tiet || ''}; veMoHinh(); } else bao(e.message + '.'); }
}
async function mdXong(tk, kq) { D.mdh[tk] = null;
  if (kq.lay_lai && kq.trung_voi) { D.trung.claude = kq.trung_voi; D.trungTk = {...(D.trungTk || {}), claude: tk};   // QĐ223: ô A8
    D.trungChu = {...(D.trungChu || {}), claude: kq.trung_chu}; }
  if (kq.giu_ma_cu) { bao(CHU_Z15.kiemLoiRe); await napMoHinh(); return; }   // Y38d N29: giữ mã cũ
  bao(kq.goi_thu ? 'Đã lưu ' + CHU_MDH.toLowerCase() + ' cho tài khoản ' + tk + ', hết hạn ' + ngay(kq.han) + '.'
    : kq.het_hanmuc ? CHU_Z15.kiemHanMucRe   // QĐ222 (N43): hết hạn mức → câu A15, không hiện lời gốc của Claude
    : 'Đã lưu ' + CHU_MDH.toLowerCase() + ' nhưng gọi thử chưa được: ' + (kq.loi_goi_thu || 'chưa rõ lý do') + '.');
  await napMoHinh(); }
function theGoi(g, ds, nguon, uu) {
  const dn = D.dn[g] || {}, ten = GOI_NGAN[g].replace('Gói ', '');
  const coTk = ds.some(x => x.da_noi), coDong = x => nguon.some(y => y.ma === x.ma && y.trangthai === 'dung');
  // QĐ164 (Z6-TK): mới cài hoặc đã gỡ hết thì thẻ hiện 01 dòng "Chưa có tài khoản" (N10)
  const rong = !ds.length || (ds.length === 1 && !ds[0].da_noi && !ds[0].khong_ro && !coDong(ds[0]));
  let h = '<div class="the o-goi"><div class="dong">' + logoGoi(g) + '<div class="f1"><div class="t16 b7">' + esc(GOI_TEN[g]) + '</div><div class="t12 phu">Phí cố định tháng'
    + (uu ? ' · <span class="nw">ưu&nbsp;tiên&nbsp;' + uu + '</span>' : '') + '</div></div></div>';
  const mdMo = g === 'claude' ? Object.keys(D.mdh).filter(k => D.mdh[k]).map(Number) : [];   // hộp Đang kết nối đang mở
  if (rong && !dn.url && !mdMo.length) h += '<div class="tk-dong"><span class="anh-dd mini xam">1</span><div class="f1"><b>Chưa có tài&nbsp;khoản</b><div class="t12 phu">'
    + (g === 'claude' ? 'Kết nối bằng ' + CHU_MDH.toLowerCase() + ' 365&nbsp;ngày để dùng làm nguồn ưu&nbsp;tiên&nbsp;' + uu : 'Đăng nhập để dùng làm nguồn dự&nbsp;phòng') + '</div></div>'
    + (g === 'claude' ? '<span class="nhan n-xem"><i></i>Chưa kết nối</span>' : '<span class="nhan n-xem"><i></i>Chưa đăng nhập</span>') + '</div>';   // N21
  else ds.forEach(x => { const n = nguon.find(y => y.ma === x.ma) || {};
    if (g === 'claude' && mdMo.includes(x.taikhoan) && !x.da_noi && !x.ma_daihan) return;   // hộp Đang kết nối thay ô (Z13)
    const go = (x.da_noi || coDong(x) || x.ma_daihan) && !(dn.url && dn.tk === x.taikhoan);
    const nutGo = go ? '<button class="btn-chu go-tk" data-go-goi="' + g + '" data-go-tk="' + x.taikhoan + '">' + ICON['user-minus'] + 'Gỡ tài&nbsp;khoản</button>' : '';
    const mdHet = g === 'claude' && x.ma_daihan && x.ma_daihan.het, cl = g === 'claude';
    h += '<div class="tk-dong"' + tieuHetMh(n, x.taikhoan) + '><span class="anh-dd mini' + (x.da_noi || mdHet ? '' : ' xam') + '">' + x.taikhoan + '</span><div class="f1"><b>' + tenTk(x) + '</b>'
      + (x.da_noi && x.mota_goi ? '<div class="t12 phu">' + esc(x.mota_goi) + '</div>' : '')
      + (cl && x.ma_daihan ? '' : '<div class="t12 phu">' + (x.da_noi ? dnLuc(x) : x.khong_ro ? 'Chưa kiểm được trạng thái' : cl ? 'Chưa kết nối' : 'Chưa đăng nhập') + '</div>')
      + (cl ? '' : nutGo) + '</div>'
      + (mdHet ? '<span class="nhan n-canh"><i></i>Mã hết hạn</span>' : x.da_noi ? '<span class="nhan n-dat"><i></i>Đã kết nối</span>'
        : '<span class="nhan n-xem"><i></i>' + (cl ? 'Chưa kết nối' : 'Chưa đăng nhập') + '</span>') + '</div>'
      + (cl ? '<div class="md-khoi">' + theMd(x, nutGo) + '</div>' : '')   // 0.7.8 (Z13, N11b): hàng riêng rộng hết thẻ; "Gỡ tài khoản" xóa cả mã
      + (cl && coBaoLayLai(g, x.taikhoan) ? baoLayLai(D.trungChu[g], x.taikhoan) : '');   // Y38f L3: A8
    if (x.da_noi) h += '<div class="cot-doc g8">' + thanhHm('Cửa sổ 05 giờ', n.tyle_5gio, n.ma + '|5') + thanhHm('Tuần này', n.tyle_tuan, n.ma + '|t')
      + (n.da_datlai_luc   // Z12 (3): qua giờ đặt lại
        ? '<div class="t12 phu" title="Qua giờ đặt lại: khung 05 giờ mới bắt đầu, số dùng về 0%">Đã đặt lại lúc ' + esc(gio(n.da_datlai_luc)) + '&nbsp;· số mới có sau lượt gọi AI kế&nbsp;tiếp</div>'
        : '<div class="t12 phu" title="Số đo sau mỗi lượt gọi AI; màn này tự làm mới 01 phút/lần">' + (n.do_luc ? 'Đo lúc ' + esc(luc(n.do_luc))
          + (n.datlai_5gio_luc ? '&nbsp;· đặt lại 05&nbsp;giờ lúc ' + esc(gio(n.datlai_5gio_luc)) : '') : 'Chưa đo: số hiện sau lần gọi AI đầu tiên') + '</div>') + '</div>'; });
  if (g === 'claude') { ds.filter(x => x.ma_daihan && x.ma_daihan.het).forEach(x => { h += theMdHet(x, ds); });   // N13, N23
    mdMo.forEach(tk => { h += theMdKetNoi(tk, D.mdh[tk]); }); }
  // QĐ164 ý 1 (Z6-TK): đăng nhập trùng thì không tạo ô, dải xanh dưới ô đang có; số là số của ô đang giữ tài khoản đó
  if (D.trung[g] && !((D.trungTk || {})[g] && ds.some(x => x.taikhoan === D.trungTk[g]))) h += '<div class="bao-xanh t13">' + ICON['user-round'] + '<span>' + ((D.trungChu || {})[g] ? giuTienTo(cum(cau(D.trungChu[g])))   // Y38d N41: câu 22
    : 'Tài khoản ' + ten + ' này đã kết&nbsp;nối ở Tài&nbsp;khoản&nbsp;' + D.trung[g] + '. Phần mềm không tạo ô&nbsp;mới.') + '</span></div>';
  if (dn.url) {
    h += '<div class="dangnhap"><div class="b6 t13">Đăng nhập tài khoản ' + dn.tk + '</div>' + (dn.tk >= 2 ? canhTk(ten) : '')
      + '<div class="buoc-dn"><span class="so-b">1</span><span class="f1">' + (g === 'claude' ? 'Mở trang đăng nhập, đăng nhập bằng tài&nbsp;khoản&nbsp;Claude của bạn.' : 'Mở trang xác nhận, đăng nhập ChatGPT.') + '</span></div>'
      + '<div class="dong lk"><span class="t12 phu f1 cat">' + esc(dn.url.replace(/^https?:\/\//, '')) + '</span><a class="btn btn-phu nho" href="' + esc(dn.url) + '" target="_blank" rel="noopener noreferrer">' + ICON['external-link'] + 'Mở trang</a></div>';
    if (g === 'claude') h += '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">Trang sẽ hiện 01 mã. Chép mã, dán vào ô dưới.</span></div>'
      + '<div class="dong"><div class="o-nhap f1' + (dn.loi ? ' loi' : '') + '">' + ICON.hash + '<input id="ma-claude" placeholder="Dán mã ở đây" autocomplete="off"></div><button class="btn btn-chinh" data-mc-xacnhan>Xác nhận</button></div>'
      + (dn.loi ? '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + cum(cau(dn.loi)) + '</span></div>' : '');
    else h += '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">Gõ mã thiết bị này vào trang:</span></div><div class="ma-tb"><b>' + esc(dn.ma) + '</b><button class="btn-chu" data-chep="' + esc(dn.ma) + '">' + ICON.copy + 'Chép</button></div>'
      + '<div class="dong t13 phu">' + ICON.loader + 'Đang chờ bạn xác nhận trên web. Xong là thẻ tự chuyển, không cần dán mã.</div>' + (dn.loi ? '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + cum(cau(dn.loi)) + '</span></div>' : '');
    h += '<button class="btn-chu" data-dn-huy="' + g + '">Hủy đăng nhập</button></div>';
  }
  const chua = rong ? {taikhoan: ds.length ? ds[0].taikhoan : oTrong(ds)} : ds.find(x => !x.da_noi && !x.ma_daihan);
  const them = !rong && ds.length < 2 && ds.filter(x => x.da_noi).length === 1;   // Z6-TK: có 01 tài khoản thì hiện, đủ 02 thì ẩn
  h += '<div class="dong chan-goi">' + (chua && !dn.url && g === 'claude' && !mdMo.includes(chua.taikhoan)   // N21 (Z13 trạng thái 1)
      ? '<button class="btn btn-chinh" data-md-lay="' + chua.taikhoan + '">' + ICON['log-in'] + 'Kết nối Claude</button><button class="btn btn-phu" data-md-dan="' + chua.taikhoan + '">' + ICON['key-round'] + 'Dán mã</button>'
      : chua && !dn.url && g !== 'claude' ? '<button class="btn btn-chinh" data-dn-goi="' + g + '" data-dn-tk="' + chua.taikhoan + '">' + ICON['log-in'] + 'Đăng nhập</button>' : '')
    + (them && !dn.url ? '<button class="btn btn-phu" data-them-goi="' + g + '">' + ICON['user-plus'] + 'Thêm tài khoản ' + ten + ' khác</button>' : '')
    + (coTk ? ds.filter(x => x.da_noi).map(x => { const n = nguon.find(y => y.ma === x.ma); return n ? '<button class="btn btn-phu" data-goithu="' + esc(n.id) + '">Gọi thử' + (ds.length > 1 ? ' tài khoản ' + x.taikhoan : '') + '</button>' : ''; }).join('') : '')
    + '</div></div>';
  return h;
}
// QĐ169 đợt 1 (Z8): "Tên · gói" đọc sống; thiếu tên thì "Tài khoản N"; thiếu cả 02 thì "Tài khoản N" như cũ
const tenTk = x => { const tk = 'Tài&nbsp;khoản&nbsp;' + x.taikhoan;
  if (!x.da_noi || (!x.ten_hien && !x.goi_ten)) return tk;
  return (x.ten_hien ? esc(x.ten_hien) : tk) + (x.goi_ten ? '&nbsp;·&nbsp;<span class="nw">' + esc(x.goi_ten) + '</span>' : ''); };
// Số ô tài khoản còn trống đầu tiên (giữ số theo tài khoản: gỡ Tài khoản 1 thì Tài khoản 2 giữ tên)
const oTrong = ds => [1, 2].find(n => !ds.some(x => x.taikhoan === n));
// QĐ164 (Z6-TK): thêm tài khoản khác luôn qua 01 hộp hỏi lại; gói chưa có tài khoản thì vào đăng nhập luôn
async function themTk(g) {
  const ds = (D.md && D.md.goi[g]) || [], ten = GOI_NGAN[g].replace('Gói ', ''), so = ds.filter(x => x.da_noi).length;
  const vao = (gg, tk) => gg === 'claude' ? mdLay(tk) : batDauDn(gg, tk);   // 0.7.8: Claude kết nối bằng mã dài hạn (Z13)
  if (!so) { const c = ds.find(x => !x.da_noi); await vao(g, c ? c.taikhoan : oTrong(ds)); return; }
  const o = oTrong(ds);
  if (so >= 2 || !o) { const c = ds.find(x => !x.da_noi); if (c && so < 2) { await vao(g, c.taikhoan); return; }
    bao(tenNguon({goi: g}) + ' đã đủ 02 tài khoản. Gỡ 01 tài khoản rồi mới thêm.'); return; }
  xacnhan('Thêm tài khoản ' + ten + ' khác?', 'Dùng khi bạn có 02 gói riêng, mỗi gói 01 tài khoản ' + ten + ' khác&nbsp;nhau.<br><br>Đăng nhập lại tài khoản đang kết nối thì phần mềm báo trùng, không tạo ô mới.' + canhTk(ten),
    'Tiếp tục', () => vao(g, o));
}
function veMoHinh() {
  const d = D.md; $('#md-songsong').textContent = hai(Number(d.so_viec_ai_songsong || 3));
  const khoa = d.nguon.filter(n => n.loai === 'khoa_api');
  // N10 b, QĐ160: số ưu tiên = thứ tự dùng thật (máy chủ đã xếp gói trước Khóa API). Gói chưa đăng nhập (chưa có dòng
  // G06) hiện số sẽ nhận: ngay sau các gói đã có, vẫn trước mọi Khóa API.
  let k = 0; const uu = {};
  d.nguon.filter(n => n.loai !== 'khoa_api' && n.trangthai === 'dung').forEach(n => { ++k; if (n.goi && !(n.goi in uu)) uu[n.goi] = k; });
  ['claude', 'chatgpt'].forEach(g => { if (!(g in uu)) uu[g] = ++k; });
  $('#ds-nguonai').innerHTML = theGoi('claude', d.goi.claude, d.nguon, uu.claude) + theGoi('chatgpt', d.goi.chatgpt, d.nguon, uu.chatgpt)
    + '<div class="the o-goi"><div class="dong"><div class="ico-tron">' + ICON['key-round'] + '</div><div class="f1"><div class="t16 b7">Khóa API</div><div class="t12 phu">Phí theo lượt</div></div></div>'
    + (khoa.length ? khoa.map((n, i) => '<div class="tk-dong"><span class="anh-dd mini">K</span><div class="f1"><b>' + esc(tenNguon(n)) + '</b><div class="t12 phu">Cất ở mục&nbsp;Két&nbsp;khóa</div><div class="t12 phu">Ưu&nbsp;tiên&nbsp;' + (k + i + 1) + '</div></div>'
        + (n.tran_tien_thang ? '<span class="nhan n-dat"><i></i>Đang dùng</span>' : '<span class="ttag xem">Chưa đặt hạn mức</span>') + '</div>').join('')
      : '<div class="t13 phu">Chưa có khóa API. Chưa có khóa thì phần mềm chỉ dùng gói.</div><div class="t12 xem-chu">Thêm khóa ở mục Két khóa (có ở bản sau).</div>')
    + '<div class="kv"><span>Chi phí AI tháng&nbsp;' + d.thang.thang + '</span><span class="trai-so"><b class="so">' + usd(d.thang.tien_that_usd)
      + '</b><span class="so-tk">' + vnd(d.thang.tien_that_usd, d.ty_gia_usd) + '</span></span></div>'
    + '</div>';
  requestAnimationFrame(() => document.querySelectorAll('#ds-nguonai .tdf[data-w]').forEach(e => { e.style.width = e.dataset.w + '%'; }));   // Z12: trượt tới số mới
  const dau = d.nguon.find(n => n.trangthai === 'dung');
  // QĐ178 (Z10): nút "Đổi" mở hộp chọn dùng chung danh sách với màn 08; mặc định lưu ở G08 theo loại việc
  const LV = (D.dsmh && D.dsmh.loai_viec) || {trochuyen: 'Trò chuyện AI', trichvanban: 'Trích văn bản (đường D)', dexuat: 'Đề xuất ở mục Chờ duyệt', baocaosang: 'Viết báo cáo sáng'};
  const cot = 'grid-template-columns:1.4fr 1fr 1fr 70px';
  if (LV.viecnen_chung) $('#md-ghichu').textContent = 'Trò chuyện AI chưa đặt thì dùng mặc định của nguồn ưu tiên 1; việc nền chưa đặt riêng theo dòng "' + nbsp(LV.viecnen_chung) + '"';
  $('#ds-mohinh').innerHTML = '<div class="hang tieu-de" style="' + cot + '"><span>Loại việc</span><span>Mô hình</span><span>Nguồn</span><span></span></div>'
    + Object.entries(LV).map(([k, v]) => { const x = mdLoai(k);   // Z10c: x.m trống = "Mặc định của nguồn" x.g
      const mat = ((D.dsmh && D.dsmh.macdinh_ct) || {})[k] && D.dsmh.macdinh_ct[k].mat;   // Đ6: nhóm đã đặt không còn tài khoản
      const iVn = k === 'viecnen_chung' ? ' <button class="nut-ico nho" data-ivn title="' + CHU_VN + '">' + icoMau(ICON['info'], 'var(--phu)', 14) + '</button>' : '';
      return '<div class="hang" style="' + cot + '"><b class="rong-mb' + (iVn ? ' ten-i' : '') + '">' + (iVn ? '<span>' + cum(v) + '</span>' : esc(v)) + iVn + '</b><span data-l="Mô hình"' + (x && x.m ? ' title="Bản cụ thể: ' + esc(x.m.ma) + '"'
        : mat ? ' title="Nguồn đã đặt không còn tài khoản nào: dùng nguồn ưu tiên 1"' : '') + '>'
        + (x && x.m ? esc(tenMh(x.m.ma, x.g.nhom, x.g)) : 'Mặc định của nguồn') + '</span><span data-l="Nguồn">'
        + (x ? cum(tenNguon(x.g)) : (dau ? cum(tenNguon(dau)) : 'Chưa có nguồn')) + '</span><button class="btn-chu" data-doimd="' + k + '">' + ICON.pencil + 'Đổi</button></div>'; }).join('');
}
async function napMoHinh() { const o = $('#ds-nguonai');   // N26: máy chủ hỏi CLI từng tài khoản, có thể mất vài giây
  if (!D.md && o && !o.innerHTML.trim()) o.innerHTML = '<div class="the t13 phu dong">' + ICON.loader + 'Đang tải nguồn AI…</div>';
  try { D.md = await api('/mohinh'); await napDsMh(); veMoHinh(); } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); } }
async function batDauDn(g, tk) {
  D.trung[g] = 0;
  try { const kq = await api('/mohinh/goi/' + g + '/batdau', {taikhoan: tk}); D.dn[g] = {tk, url: kq.url, ma: kq.ma_thietbi, loi: ''}; veMoHinh();
    if (g === 'chatgpt') hoiChatGPT(tk); else { const o = $('#ma-claude'); if (o) o.focus(); } }
  catch (e) { bao(e.message + '.'); }
}
async function hoiChatGPT(tk) {
  const dn = D.dn.chatgpt; if (!dn || dn.tk !== tk || !dn.url) return;
  try { const kq = await api('/mohinh/goi/chatgpt/hoi', {taikhoan: tk});
    if (kq.xong) { D.dn.chatgpt = {}; bao('Đã kết nối ' + tenNguon({goi: 'chatgpt'}) + ', tài khoản ' + tk + '.'); await napMoHinh(); return; } }
  catch (e) { if (e.status) { D.dn.chatgpt = {}; if (e.status === 409) D.trung.chatgpt = (e.ct || {}).trung_voi; else bao(e.message + '.'); await napMoHinh(); return; } }
  setTimeout(() => hoiChatGPT(tk), 4000);
}
async function danMaClaude() {
  const dn = D.dn.claude, ma = ($('#ma-claude') || {}).value || '';
  if (!ma.trim()) { bao('Bạn dán mã trang Claude hiện ra.'); return; }
  try { await api('/mohinh/goi/claude/ma', {taikhoan: dn.tk, ma}); D.dn.claude = {}; bao('Đã kết nối ' + tenNguon({goi: 'claude'}) + ', tài khoản ' + dn.tk + '.'); await napMoHinh(); }
  catch (e) { if (e.status === 409) { D.dn.claude = {}; D.trung.claude = (e.ct || {}).trung_voi;
      D.trungChu = {...(D.trungChu || {}), claude: (e.ct || {}).chu_rieng ? (e.ct || {}).loi : ''};
      D.trungTk = {...(D.trungTk || {}), claude: (e.ct || {}).lay_lai ? dn.tk : 0}; await napMoHinh(); return; } dn.loi = e.message; veMoHinh(); }
}

// ---- Ô chọn mô hình màn 08 + hộp "Đổi" màn 13 (QĐ178–QĐ183, PTD-08, bản vẽ Z10, Z10b): 01 danh sách G08 dùng chung
const MH = {noi: null, tim: '', mo: null, dich: null, cu: false};   // cu: dòng "Bản cũ (n)" đang mở (QĐ311 G2)   // noi: 'chat' (bảng xổ màn 08) | 'md' (hộp màn 13); dich: loại việc
D.hong = {};   // {mã cuộc: {het, dung, nguon_id}}: mô hình ghim không dùng được ở lượt gần nhất (nút vàng tới khi dùng lại được)
// Y31b S5; QĐ562: icon vẽ bằng currentColor, màu đặt ở `color` trong style của thẻ svg (biến màu theo vai trò)
const icoMau = (svg, mau, co) => svg.replace(/stroke="[^"]*"/, 'stroke="currentColor"').replace(/(<svg\b[^>]*?style="[^"]*?)color:[^;"]*/, '$1color:' + mau).replace(/width="\d+"/, 'width="' + co + '"').replace(/height="\d+"/, 'height="' + co + '"');
// Y34: chỉ lượt tải mới nhất được ghi (lượt mạng về muộn thì bỏ); trả true khi danh sách đổi. Bảng đang mở chỉ vẽ lại khi
// danh sách đổi thật, để lượt bấm của anh không rơi vào lúc bảng đang được vẽ lại (nguồn học: tailieu/Songuongoc.md).
let luotDs = 0;
async function napDsMh() { const luot = ++luotDs; let moi; try { moi = await api('/mohinh/danhsach'); } catch (e) { return false; }
  if (luot !== luotDs) return false;
  const doi = JSON.stringify(moi) !== JSON.stringify(D.dsmh); D.dsmh = moi;
  if (moi.nhom.some(g => g.dang_tai)) setTimeout(async () => { if (await napDsMh()) veLaiMh(); }, 2500);
  return doi; }
// Ghim tạm ở trình duyệt theo mã cuộc trò chuyện (QĐ180; lược đồ bản 4 chuyển về cột H07 `mohinh_ghim_id`)
const KHO_GHIM = 'igm360.ghim_mohinh';
const docGhim = () => { try { return JSON.parse(localStorage.getItem(KHO_GHIM) || '{}') || {}; } catch (e) { return {}; } };
const luuGhim = (ht, id) => { try { const g = docGhim(); if (id) g[ht] = id; else delete g[ht]; localStorage.setItem(KHO_GHIM, JSON.stringify(g)); }
  catch (e) { /* trình duyệt chặn lưu: ghim chỉ còn tới khi tải lại trang */ } };
const ghimId = () => (D.htId ? docGhim()[D.htId] : D.ghimMoi) || null;
// 0.7.6 (QĐ187, PTD-08): mô hình nhận diện bằng khóa "loại nguồn|mã mô hình" máy chủ cấp (`m.khoa`); giao diện không tự
// ghép. Ghim dạng cũ (id G08 của 0.7.5, nằm trong `m.ids`) tra ra khóa rồi lưu lại.
const timMh = k => { for (const g of (D.dsmh ? D.dsmh.nhom : [])) { const m = g.mohinh.find(x => x.khoa === k || (x.ids || []).includes(k)); if (m) return {g, m}; } return null; };
const datGhim = k => { if (D.htId) luuGhim(D.htId, k); else D.ghimMoi = k; };
const ghimKhoa = () => { const v = ghimId(); if (!v || v.includes('|')) return v; const x = timMh(v); if (x) { datGhim(x.m.khoa); return x.m.khoa; } return v; };
const nhomChinh = () => D.dsmh ? D.dsmh.nhom.find(n => n.chinh) || null : null;
// Mặc định của 01 loại việc (Đ6): {g, m}; m trống = "mặc định của nguồn" g; chưa đặt hoặc cả nhóm đã mất = nguồn chính, m trống
const mdLoai = lv => { const c = D.dsmh && (D.dsmh.macdinh_ct || {})[lv]; if (!c || c.mat) return null;
  return c.ma ? timMh(c.khoa) : (nhomMh(c.nhom) ? {g: nhomMh(c.nhom), m: null} : null); };
const mdChat = () => mdLoai('trochuyen') || {g: nhomChinh(), m: null};
function dangChonChat() { const x = ghimKhoa() && timMh(ghimKhoa());
  return x ? {...x, ghim: true} : {...mdChat(), ghim: false}; }
function ghiHong(tl, gh) { const k = D.htId; if (!tl || !gh) return;
  if (tl.ghim_khoa && tl.ghim_khoa !== gh) luuGhim(k, tl.ghim_khoa);   // máy chủ đổi ghim dạng cũ sang khóa
  if (tl.ghim_hong) D.hong[k] = {het: tl.ghim_hong.het_hanmuc, dung: mhThucDung(tl), nguon_id: tl.nguon_id,
    nghi: tl.ghim_hong.tk_nghi ? {den: tl.ghim_hong.den, nguon_id: tl.ghim_hong.nguon_id} : null};   // Y36d P3b
  else if (tl.ghim_khoa) delete D.hong[k]; }
const nbsp = s => String(s).replace(/ /g, NB);
// Y36d P3b: cả tài khoản đang tạm nghỉ (mô hình được chọn chưa bị từ chối riêng)
const chuNghi = (g, n0) => 'Tài khoản ' + (n0 && n0.goi ? GOI_NGAN[n0.goi].replace('Gói ', '') : n0 ? tenNguon(n0) : '') + ' đang tạm nghỉ' + (g.den ? ' đến ' + denLuc(g.den) : '');
function chuGhimHong(x) { const g = x.ghim_hong || x.md_hong, a = x.ghim_hong && g.khoa && timMh(g.khoa), n = timNguon(x.nguon_id);
  const n0 = (x.md_hong || g.tk_nghi) && timNguon(g.nguon_id);   // Y36c: lượt thường, nguồn đứng trước đang hết hạn mức
  if (g.tk_nghi) return esc(chuNghi(g, n0)) + ', đã dùng ' + esc(nbsp(n ? tenLoai(n).replace(/ /g, ' ') : 'mô hình'));   // Y36d P3b
  if (x.md_hong && !g.het_hanmuc)   // Y36f N6: lượt thường, nguồn đứng trước lỗi (không phải hạn mức) rồi sang hãng khác
    return esc(n0 && n0.goi ? GOI_NGAN[n0.goi].replace('Gói ', '') : n0 ? tenLoai(n0) : 'Nguồn ưu tiên 1') + ' chưa dùng được'
      + (g.loi ? ' (' + esc(nbsp(g.loi)) + ')' : '') + ', đã dùng ' + esc(nbsp(n ? tenLoai(n).replace(/ /g, ' ') : 'mô hình'));
  const ten = x.md_hong ? chuHoa(tenHet(g, n0) || (n0 ? tenLoai(n0).replace(/ /g, ' ') : 'Mô hình mặc định'))
    : a ? tenMh(a.m.ma, a.g.nhom, a.g, true) : g.ma ? tenMh(g.ma, null, null, true) : 'Mô hình đã chọn';   // N3
  const dung = mhThucDung(x) ? tenMh(mhThucDung(x), x.nguon_id, n, true) : (n ? tenLoai(n).replace(/ /g, ' ') : 'mô hình');   // U10b F2
  return esc(ten) + ' ' + (g.het_hanmuc ? nbsp('đang hết hạn mức') : 'chưa dùng được' + (g.loi ? ' (' + esc(nbsp(g.loi)) + ')' : '')) + ', đã dùng ' + esc(nbsp(dung + ' (mặc định)')); }
// QĐ319 (Y46-7): tệp logo ChatGPT (chép nguyên của OpenAI, QĐ169, QĐ170) có hình chỉ chiếm 49,5% khung, ép về 18 px thì
// hình còn ≈ 09 px. Giữ nguyên tệp, chỉ vẽ cỡ 32 px với lề âm 07 px trong ô 18 px: hình ≈ 16 px, cân logo Claude.
const logoNhom = g => { const cl = g.goi === 'claude' || g.hang === 'anthropic', gpt = !cl && (g.goi === 'chatgpt' || g.hang === 'openai');
  const l = cl ? ICON.logo_claude : gpt ? ICON.logo_chatgpt : icoMau(ICON['key-round'], 'var(--phu)', 16), co = gpt ? 32 : 18;   // QĐ319: 32 px
  const s = l.replace(/width="\d+"/, 'width="' + co + '"').replace(/height="\d+"/, 'height="' + co + '"');
  return '<span class="logo-n">' + (gpt ? s.replace('<svg ', '<svg style="flex:none;margin:-7px" ') : s) + '</span>'; };   // lề âm 07 px
function nutMh() { const c = dangChonChat(); if (!c.g) return '<span class="t12 phu">Chưa có nguồn AI đã kết nối</span>';
  const ten = c.m ? tenMh(c.m.ma, c.g.nhom, c.g) : 'Mặc định', hong = c.ghim && D.hong[D.htId];
  const tieu = hong && hong.nghi ? chuNghi(hong.nghi, timNguon(hong.nghi.nguon_id)) + ' · tạm dùng ' + (timNguon(hong.nguon_id) ? tenLoai(timNguon(hong.nguon_id)).replace(/ /g, ' ') : 'mô hình')
    : hong ? ten + (hong.het ? ' đang hết hạn mức' : ' chưa dùng được') + ' · tạm dùng ' + (hong.dung ? tenMh(hong.dung, hong.nguon_id, null, true) : timNguon(hong.nguon_id) ? tenLoai(timNguon(hong.nguon_id)).replace(/ /g, ' ') : 'mô hình') + ' (mặc định)' + (hong.het ? ' cho tới khi đặt lại' : '')
    : tenNguon(c.g).replace(/\u00a0/g, ' ') + ' · ' + ten + (c.m ? ' · Bản cụ thể: ' + c.m.ma : '') + (c.ghim ? ' · đã ghim cho cuộc trò chuyện này' : ' · theo mặc định chung');
  return '<button type="button" class="mh-nut' + (MH.noi === 'chat' ? ' mo' : '') + '" data-mhnut title="' + esc(tieu) + '"><span class="mh-cham"' + (hong ? ' style="background:var(--xem)"' : '') + '></span>' + esc(ten)
    + (c.ghim ? '<span aria-label="' + (hong ? 'ghim chưa dùng được' : 'đã ghim') + '">' + icoMau(ICON.pin, hong ? 'var(--xem)' : 'var(--phu)', 13) + '</span>' : '')
    + icoMau(ICON['chevron-down'], 'var(--phu)', 14) + '</button>'; }
// N1: loại việc chưa đặt thì hộp "Đổi" ✓ ở "Mặc định của nguồn" của nguồn chính
const chonDang = noi => noi === 'chat' ? dangChonChat() : (MH.dich && mdLoai(MH.dich)) || {g: nhomChinh(), m: null};
const CHU_MD = 'Mặc định của nguồn';
const CHU_VN = 'Việc nền chưa đặt riêng và bot nền sau này dùng dòng này. Trò chuyện AI không theo.';   // Z12 nút (i)
// Y46 phần D (QĐ265; bản vẽ Z20 dòng 16, 17, chữ anh duyệt QĐ271): mô hình mới theo tài khoản cần công cụ AI cao hơn
const CHU_D = {can: 'Cần nâng công cụ AI', moi: 'mới', banCu: n => 'Bản cũ (' + hai(n) + ')',   // QĐ311 G2
  re: (can, dang) => 'Mô hình mới theo tài khoản. Cần Claude · Code từ ' + can + ', bản đang dùng ' + dang + '. Tự dùng được khi công cụ AI nâng xong.'};
// <G2> QĐ311 (CDO U37-G2): gói Claude hiện 04 bí danh + bản mới nhất mỗi họ ("claude-<họ>-<số>"); bản cũ gom 01 dòng.
const hoMh = ma => { const p = String(ma).split('-'); return p[0] === 'claude' && p.length > 2 ? p[1] : null; };
const soMh = ma => String(ma).split('-').slice(2).filter(x => /^\d{1,4}$/.test(x)).map(Number);   // bỏ đuôi ngày (20251001)
const soCao = (a, b) => { for (let i = 0; i < Math.max(a.length, b.length); i++) if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0); return false; };
function tachBanCu(ds, khoaDang) {   // {chinh, cu}; mô hình đang chọn (ghim) luôn ở chinh
  const moi = {};
  ds.forEach(m => { const h = hoMh(m.ma); if (h && (!moi[h] || soCao(soMh(m.ma), soMh(moi[h].ma)))) moi[h] = m; });
  const chinh = [], cu = [];
  ds.forEach(m => { const h = hoMh(m.ma); (!h || moi[h] === m || m.khoa === khoaDang ? chinh : cu).push(m); });
  return {chinh, cu};
}
// </G2>
const nhomDangMo = noi => { const c = chonDang(noi); return MH.mo !== null ? MH.mo : c.g ? c.g.nhom : (nhomChinh() || {}).nhom; };
function dsMhHtml(noi) { const q = MH.tim.trim().toLowerCase(), nh = D.dsmh ? D.dsmh.nhom : [], dang = chonDang(noi), moId = nhomDangMo(noi);
  let h = '', co = 0;
  for (const g of nh) { const tg = tenNguon(g), tenKhop = q && tg.toLowerCase().replace(/\u00a0/g, ' ').includes(q), ten = m => tenMh(m.ma, g.nhom, g);
    const hien = q && !tenKhop ? g.mohinh.filter(m => ten(m).toLowerCase().includes(q) || m.ma.toLowerCase().includes(q)) : g.mohinh;
    const coMd = !q || tenKhop || CHU_MD.toLowerCase().includes(q);   // Z10c: tìm "mặc" cũng ra dòng mặc định
    if (q && !tenKhop && !hien.length && !coMd) continue;
    co++; const mo = q ? true : moId === g.nhom;
    h += '<button type="button" class="mh-nhom" data-mhnhom="' + esc(g.nhom) + '">' + logoNhom(g) + '<span>' + esc(tg) + '</span>'
      + (g.chinh ? '<span title="Nguồn chính · ưu tiên 1">' + icoMau(ICON.check, 'var(--dat)', 14) + '</span>' : '') + '<span class="f1"></span>'
      + icoMau(ICON[mo ? 'chevron-down' : 'chevron-right'], 'var(--phu)', 16) + '</button>';
    if (!mo) continue;
    if (coMd) {   // N2: khung chat chưa ghim thì ✓ ở đây (kể cả khi loại việc đặt 01 mô hình); hộp "Đổi": khi đặt về mặc định của nguồn
      const onMd = !dang.m && dang.g && dang.g.nhom === g.nhom;   // U10b F1 (QĐ190)
      h += '<button type="button" class="mh-dong' + (onMd ? ' on' : '') + '" data-mhmd="' + esc(g.nhom) + '"'
        + (noi === 'chat' ? ' title="Bỏ ghim · cuộc này và các cuộc mới dùng mô hình mặc định của nguồn"' : '') + '><span class="f1">' + CHU_MD + '</span>'
        + (onMd ? icoMau(ICON.check, 'var(--xanh-chu)', 16) : '') + '</button>'; }
    if (g.dang_tai) { h += '<div class="mh-tai">' + icoMau(ICON.loader, 'var(--xanh-chu)', 14) + 'Đang tải danh sách mô hình…</div>'; continue; }
    if (!hien.length) { h += '<div class="mh-tai">Chưa có danh sách: dùng mô hình mặc định của nguồn</div>'; continue; }
    const veMh = m => { const on = !!dang.m && dang.m.khoa === m.khoa;   // U10b F1: ✓ đúng mô hình nút đang ghi (cả khi chưa ghim)
      if (m.can_nang) return '<div class="mh-dong mh-xam" title="' + esc(CHU_D.re(m.can_nang, m.ban_dang)) + '"><span class="f1">' + esc(ten(m))   // Z20 dòng 16
        + '<span class="mh-phu">' + CHU_D.can + '</span></span></div>';
      return '<button type="button" class="mh-dong' + (on ? ' on' : '') + '" data-mhchon="' + esc(m.khoa) + '" title="Bản cụ thể: ' + esc(m.ma) + '"><span class="f1">' + esc(ten(m))
        + (m.moi ? ' <span class="mh-moi">' + CHU_D.moi + '</span>' : '') + '</span>'   // Z20 dòng 17
        + (on ? icoMau(ICON.check, 'var(--xanh-chu)', 16) : '') + '</button>'; };
    const {chinh, cu} = !q && g.nhom === 'goi_claude' ? tachBanCu(hien, dang.m && dang.m.khoa) : {chinh: hien, cu: []};   // QĐ311 G2; đang tìm thì hiện hết
    chinh.forEach(m => { h += veMh(m); });
    if (cu.length) { h += '<button type="button" class="mh-dong mh-cu" data-mhcu>' + icoMau(ICON[MH.cu ? 'chevron-down' : 'chevron-right'], 'var(--phu)', 14)
      + '<span class="f1">' + CHU_D.banCu(cu.length) + '</span></button>'; if (MH.cu) cu.forEach(m => { h += veMh(m); }); } }
  if (!co) h += q ? '<div class="mh-rong">Không có nguồn hoặc mô hình khớp "' + esc(MH.tim) + '"</div>' : '<div class="mh-rong">Chưa có nguồn AI nào đã kết nối</div>';
  return h; }
const bangMhHtml = noi => '<div class="mh-bang" data-mhbang="' + noi + '"><label class="mh-tim">' + icoMau(ICON.search, 'var(--phu)', 15)
  + '<input data-mhtim placeholder="Tìm nguồn, mô hình…" value="' + esc(MH.tim) + '"></label><div class="mh-ghi" title="'
  + 'Nhiều tài khoản cùng loại: dùng tài khoản đang chạy, hết hạn mức mới sang tài khoản dự phòng">'
  + (noi === 'chat' ? 'Dùng ngay cho cuộc này và các cuộc mới' : 'Mô hình mặc định cho loại việc này · chỉ hiện nguồn đã kết nối') + '</div>'
  + '<div class="mh-ds">' + dsMhHtml(noi) + '</div><div class="mh-chan"><button type="button" class="mh-nhom" data-trang="13" data-mhdong>'
  + icoMau(ICON.plus, 'var(--xanh-chu)', 16) + '<span style="color:var(--xanh-chu)">Thêm nguồn AI ở mục Mô hình AI</span></button></div></div>';
function veNutMh() { const e = $('#mh-chat'); if (e) e.innerHTML = nutMh() + (MH.noi === 'chat' ? bangMhHtml('chat') : ''); }
function veLaiMh() { const b = MH.noi === 'md' ? $('#h-chonmh .mh-ds') : MH.noi === 'chat' ? $('#mh-chat .mh-ds') : null;
  if (b) b.innerHTML = dsMhHtml(MH.noi); if (MH.noi !== 'md') { const n = $('#mh-chat .mh-nut'); if (n) n.outerHTML = nutMh(); else veNutMh(); } }
function dongMh() { MH.noi = null; MH.tim = ''; MH.mo = null; veNutMh(); }
$('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-chonmh" hidden><div class="hop mh-hop"><div class="hop-dau">' + icoMau(ICON['brain-circuit'], 'var(--xanh-chu)', 20)
  + '<b class="f1 t16" id="mh-tieu">Chọn mô hình</b><button class="nut-ico" data-dong>' + icoMau(ICON.x, 'var(--phu)', 20) + '</button></div><div class="hop-than" id="mh-than13"></div></div></div>');
document.addEventListener('click', async ev => {
  const b = ev.target.closest('[data-mhnut],[data-mhnhom],[data-mhchon],[data-mhmd],[data-doimd],[data-mhdong],[data-ivn],[data-mhcu]');
  if (!b) { if (MH.noi === 'chat' && !ev.target.closest('#mh-chat')) dongMh(); return; }
  const d = b.dataset;
  if ('mhdong' in d) { dongMh(); return; }   // không chặn: nút còn mở mục Mô hình AI
  if ('ivn' in d) { ev.stopImmediatePropagation(); bao(CHU_VN); return; }   // Z12: điện thoại bấm (i) hiện ô báo
  ev.stopImmediatePropagation();
  if ('mhnut' in d) { MH.noi = MH.noi === 'chat' ? null : 'chat'; MH.tim = ''; MH.mo = null; veNutMh(); if (MH.noi && await napDsMh()) veLaiMh(); return; }
  if ('mhcu' in d) { MH.cu = !MH.cu; veLaiMh(); return; }   // QĐ311 G2: mở / gập dòng "Bản cũ (n)"
  if (d.mhnhom) { MH.mo = nhomDangMo(MH.noi) === d.mhnhom ? '' : d.mhnhom; veLaiMh(); return; }
  if (d.mhchon) { const x = timMh(d.mhchon); if (!x) return; const ten = tenMh(x.m.ma, x.g.nhom, x.g), tn = tenNguon(x.g).replace(/\u00a0/g, ' ');
    if (MH.noi === 'md') { const lv = MH.dich;
      try { await api('/mohinh/macdinh', {loai_viec: lv, khoa: x.m.khoa}); } catch (e) { bao(e.message + '.'); return; }
      MH.noi = null; MH.dich = null; MH.tim = ''; MH.mo = null; dongHop(); await napDsMh(); if (D.md) veMoHinh(); veNutMh();
      bao('Đã đổi mô hình cho "' + D.dsmh.loai_viec[lv] + '": ' + ten + ' · ' + tn + '.'); return; }
    // QĐ190: chọn ở khung chat = cuộc đang mở dùng ngay (ghim) + đổi luôn mặc định "Trò chuyện AI"
    datGhim(x.m.khoa); delete D.hong[D.htId]; dongMh();
    try { await api('/mohinh/macdinh', {loai_viec: 'trochuyen', khoa: x.m.khoa}); }
    catch (e) { bao('Đã chọn ' + ten + ' (' + tn + ') cho cuộc trò chuyện này; chưa đổi được mặc định: ' + e.message + '.'); return; }
    await napDsMh(); if (D.md) veMoHinh(); veNutMh();
    bao('Đã chọn ' + ten + ' (' + tn + ') cho cuộc này và các cuộc mới.'); return; }
  if (d.mhmd) { const g = nhomMh(d.mhmd); if (!g) return; const tn = tenNguon(g).replace(/\u00a0/g, ' ');
    if (MH.noi === 'md') { const lv = MH.dich;   // S6: loại việc về "mặc định của nguồn" này
      try { await api('/mohinh/macdinh', {loai_viec: lv, khoa: g.khoa_md}); } catch (e) { bao(e.message + '.'); return; }
      MH.noi = null; MH.dich = null; MH.tim = ''; MH.mo = null; dongHop(); await napDsMh(); if (D.md) veMoHinh(); veNutMh();
      bao('Đã đặt "' + D.dsmh.loai_viec[lv] + '" về mặc định của nguồn ' + tn + '.'); return; }
    // QĐ190: khung chat chọn dòng này = bỏ ghim cuộc này + mặc định "Trò chuyện AI" về mặc định của nguồn đó
    datGhim(null); delete D.hong[D.htId]; dongMh();
    try { await api('/mohinh/macdinh', {loai_viec: 'trochuyen', khoa: g.khoa_md}); }
    catch (e) { bao('Đã bỏ ghim cuộc trò chuyện này; chưa đổi được mặc định: ' + e.message + '.'); return; }
    await napDsMh(); if (D.md) veMoHinh(); veNutMh();
    bao('Đã bỏ ghim: cuộc này và các cuộc mới theo mặc định của nguồn ' + tn + '.'); return; }
  if (d.doimd) { await napDsMh(); if (!D.dsmh) { bao('Chưa tải được danh sách mô hình, bạn thử lại.'); return; }
    MH.dich = d.doimd; MH.noi = 'md'; MH.tim = ''; MH.mo = null;
    $('#mh-tieu').textContent = 'Chọn mô hình · ' + nbsp(D.dsmh.loai_viec[d.doimd]); $('#mh-than13').innerHTML = bangMhHtml('md'); mo('h-chonmh'); }
}, true);
document.addEventListener('input', ev => { if (!ev.target.matches || !ev.target.matches('[data-mhtim]')) return; MH.tim = ev.target.value; veLaiMh(); });

// ---- Màn 08 Trò chuyện AI
function nhomNgay(iso) { const d = hien(iso || '').slice(0, 10), h = homNay(), q = new Date(Date.parse(h) - 86400e3).toISOString().slice(0, 10);
  return d === h ? 'Hôm nay' : d === q ? 'Hôm qua' : 'Trước đó'; }
function veDsHt() {
  const tim = (($('#tc-tim input') || {}).value || '').trim().toLowerCase(); let nhom = '', h = '';
  D.ht.filter(x => !tim || (x.tieude || '').toLowerCase().includes(tim)).forEach(x => { const n = nhomNgay(x.cap_nhat_luc);
    if (n !== nhom) { h += '<div class="nhom-ht">' + n + '</div>'; nhom = n; }
    h += '<button class="ht' + (x.id === D.htId ? ' on' : '') + '" data-ht="' + esc(x.id) + '">' + ICON['message-square'] + '<span>' + esc(x.tieude) + '</span></button>'; });
  $('#ds-ht').innerHTML = h || '<div class="t12 phu">Chưa có cuộc trò chuyện nào.</div>';
}
function tinHtml(x) {
  if (x.vai === 'nguoi') return '<div class="tn toi"><div class="tn-noi">' + esc(x.noidung).replace(/\n/g, '<br>') + '</div></div>';
  if (x.vai === 'hethong') return '<div class="tn-bao do">' + ICON['circle-alert'] + '<span class="f1">' + cum(x.noidung) + '</span>'
    + (x.phu && x.phu.loai === 'luot_cat' ? '' : '<button class="btn btn-phu nho" data-trang="13">Mở Mô hình AI</button>') + '</div>';   // QĐ350
  return '<div class="tn ai"><div class="tn-ico">' + (ICON.tn_ai || ICON.sparkles) + '</div><div class="tn-noi">' + cum(x.noidung).split(/\n{2,}/).map(o => '<p>' + o.replace(/\n/g, '<br>') + '</p>').join('')
    + (x.ghim_hong || x.md_hong ? '<div class="tn-meta mh-vang"' + ((x.ghim_hong || x.md_hong || {}).loi_ct ? ' title="' + esc((x.ghim_hong || x.md_hong).loi_ct) + '"' : '') + '>' + icoMau(ICON['circle-alert'], 'var(--xem)', 13) + '<span>' + chuGhimHong(x) + '</span></div>' : '')
    + '<div class="tn-meta"' + (tieuTraLoi(x) ? ' title="' + esc(tieuTraLoi(x)) + '"' : '') + '>' + cum(nhanTraLoi(x)) + '<button class="nut-ico nho" title="Chép" data-chep-tin="' + esc(x.id) + '">' + ICON.copy + '</button></div></div></div>';
}
function veTin(ds, giu) { D.tin = ds; $('#ds-tin').innerHTML = ds.map(tinHtml).join(''); S.tc = ds.length ? 'co' : 'rong'; ve();
  const c = vungCuon(); if (c && !giu) c.scrollTop = c.scrollHeight; }   // SUA-P3: vùng cuộn thật; `giu` = người đọc đã cuộn lên
async function napTroChuyen() {
  try { D.ht = (await api('/trochuyen')).hoithoai; veDsHt();
    const md = D.md || await api('/mohinh').catch(() => null); if (md) D.md = md;
    await napDsMh(); veNutMh();   // QĐ178 (Z10): bỏ ô chọn nguồn đầu cuộc, nút chọn mô hình dưới khung nhập
  } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); }
}
// <LUOT> N0 (QĐ344, QĐ352, QĐ355; CDO HINH-TC45 H1–H9; CDA T1–T4, M2, N3): lượt trả lời chạy nền + chữ chạy dần.
// Gửi `nen: true` → máy chủ trả ngay mã lượt; trang nghe luồng sự kiện (EventSource, tự nối lại kèm Last-Event-ID).
// Đóng, tải lại trang không dừng lượt; mở lại cuộc còn lượt chạy thì nối lại (`luot_dang`). Không lưu gì ở trình duyệt.
const LUOT = {es: null, id: null, chu: '', hen: 0};
function boLuot() { if (LUOT.es) LUOT.es.close(); if (LUOT.hen) cancelAnimationFrame(LUOT.hen);
  LUOT.es = null; LUOT.id = null; LUOT.chu = ''; LUOT.hen = 0; }
// H1: bong bóng trả lời có sẵn, mở ngay khi gửi; trước chữ đầu tiên chỉ có con trỏ. H7: aria-busy. H9: chưa có dòng dưới.
const htmlChay = () => '<div class="tn ai" id="tn-chay" aria-busy="true"><div class="tn-ico">' + (ICON.tn_ai || ICON.sparkles)
  + '</div><div class="tn-noi"><p><span class="dang-viet"></span></p></div></div>';
// H2–H4, T4: chữ qua cum() (thoát chữ), tách đoạn như tin đã xong; con trỏ .dang-viet::after ở cuối (H3: span rỗng, chữ giữ
// màu chính). H5: chỉ bám đáy khi đang ở đáy (≤ 40 px).
// SUA-H5 (CDO BT-N0 BT04): vùng cuộn thật – .tc-than khi có thanh cuộn riêng (sau QĐ317 B1), chưa có thì cả trang.
const vungCuon = () => { const c = $('.tc-than'); if (c && c.scrollHeight > c.clientHeight) return c;   // KH-090 2.2 (b): khổ máy tính trang cuộn ở .cuon-trong
  const v = S.xem !== 'mb' && $('#app .cuon-trong'); return v && v.scrollHeight > v.clientHeight ? v : (document.scrollingElement || document.documentElement); };
function veChay() { LUOT.hen = 0; const b = $('#tn-chay'), c = vungCuon(); if (!b) return;
  const day = !c || c.scrollHeight - c.scrollTop - c.clientHeight <= 40, doan = cum(LUOT.chu).split(/\n{2,}/);
  b.querySelector('.tn-noi').innerHTML = doan.map((o, i) => '<p>' + o.replace(/\n/g, '<br>')
    + (i === doan.length - 1 ? '<span class="dang-viet"></span>' : '') + '</p>').join('');
  if (c && day) c.scrollTop = c.scrollHeight; }
const henVe = () => { if (!LUOT.hen) LUOT.hen = requestAnimationFrame(veChay); };   // H4: gộp mẩu, vẽ 01 lần mỗi khung hình
async function xongLuot(ds, tl, gh) {   // T1, T2: thay toàn bộ phần đang chạy bằng câu đã lưu (giữ dòng vàng, nhãn như nay)
  const v = vungCuon(), day = !v || v.scrollHeight - v.scrollTop - v.clientHeight <= 40;   // SUA-P3: đo trước khi vẽ lại
  ghiHong(tl, gh); veTin([...ds, tl], !day); veNutMh();
  try { D.ht = (await api('/trochuyen')).hoithoai; veDsHt(); } catch (e) { /* danh sách cuộc cập nhật ở lần sau */ } }
function theoLuot(id, ds, gh) { boLuot(); LUOT.id = id;
  const es = new EventSource('/api/trochuyen/luot/' + encodeURIComponent(id) + '/sukien'); LUOT.es = es;
  es.onmessage = m => { if (LUOT.id !== id) return; let e; try { e = JSON.parse(m.data); } catch (_) { return; }
    if (e.loai === 'chu') { LUOT.chu += e.them || ''; henVe(); }
    else if (e.loai === 'lam_lai') { LUOT.chu = ''; henVe(); }                          // T3, H8: xóa sạch chữ dở
    else if (e.loai === 'xong' || e.loai === 'dung') { boLuot(); xongLuot(ds, e.tra_loi, gh); }
    else if (e.loai === 'loi') { boLuot(); if (D.htId) moHt(D.htId); } };              // N3, M2: tải lại cuộc, không để chữ dở
  // QĐ358 N2 câu 2: luồng đóng → tự tải lại hội thoại; chỉ khi tải lại cũng lỗi mới hỏi lại luồng để lấy câu báo của máy chủ
  es.onerror = () => { if (es.readyState === 2 && LUOT.id === id) { boLuot(); if (D.htId) moHt(D.htId).catch(async () => {
    try { await api('/trochuyen/luot/' + encodeURIComponent(id) + '/sukien'); } catch (e) { bao(e.message + '.'); } }); } }; }
// QĐ347 H1, QĐ352: đang chờ cập nhật – câu báo ngay dưới câu hỏi vừa gửi (khung "Cần xem", không ghi vào hội thoại,
// vẽ lại khung chat thì mất), câu hỏi trở lại ô nhập. Chữ đúng chữ máy chủ trả (đã duyệt), không thêm dấu.
const htmlChoCn = t => '<div class="tn-bao">' + icoMau(ICON['cloud-download'], 'var(--xem)', 16) + '<span class="f1">' + cum(t) + '</span></div>';
// </LUOT>
async function moHt(id) { boLuot(); const d = await api('/trochuyen/' + encodeURIComponent(id)); D.htId = id;
  $('#tc-tieude').textContent = d.tieude; veTin(d.tinnhan); veDsHt(); dongMh();
  if (d.luot_dang) { $('#ds-tin').insertAdjacentHTML('beforeend', htmlChay()); S.tc = 'dang'; ve();   // nối lại lượt đang chạy
    theoLuot(d.luot_dang, d.tinnhan, ghimKhoa()); } }
async function guiTin(chu) {
  const o = $('#tc-o'), nd = (chu ?? o.value).trim(); if (!nd || S.tc === 'dang') return;
  o.value = ''; const cu = D.tin && D.htId ? D.tin : [], toi = tinHtml({vai: 'nguoi', noidung: nd});
  $('#ds-tin').innerHTML = cu.map(tinHtml).join('') + toi + htmlChay(); S.tc = 'dang'; ve();
  const c = vungCuon(); if (c) c.scrollTop = c.scrollHeight;   // vừa gửi: đưa tới đáy
  try { const ht0 = D.htId, gh = ghimKhoa();   // QĐ180: mỗi tin gửi kèm khóa mô hình ghim (trình duyệt nhớ)
    const kq = await api('/trochuyen', {hoithoai_id: D.htId, noidung: nd, mohinh_id: gh});   // api() thêm nen: true
    if (kq.trung) { o.value = nd; await moHt(kq.hoithoai_id); return; }   // N5 (CDA, cách a): cuộc đang có lượt chạy (mở ở 02 nơi) → trả câu hỏi về ô nhập, vẽ cuộc thật, nối vào lượt đang chạy
    if (!D.htId) $('#tc-tieude').textContent = nd.slice(0, 80);
    D.htId = kq.hoithoai_id; if (!ht0 && D.ghimMoi) { luuGhim(D.htId, D.ghimMoi); D.ghimMoi = null; }
    theoLuot(kq.luot_id, [...cu, kq.hoi || {vai: 'nguoi', noidung: nd}], gh); }
  catch (e) {
    if (e.ma === 'cho_capnhat') { $('#ds-tin').innerHTML = cu.map(tinHtml).join('') + toi + htmlChoCn(e.message);
      o.value = nd; S.tc = 'co'; ve(); return; }
    // SUA-BT7 (CDO BT25): mọi lỗi gửi (409, mất kết nối, 500…) – vẽ lại như trước khi gửi (bỏ câu hỏi, bong bóng đang chạy),
    // câu hỏi trở lại ô nhập như H1, N5, QĐ358 N2 câu 1; chữ báo giữ nguyên
    $('#ds-tin').innerHTML = cu.map(tinHtml).join(''); o.value = nd;
    S.tc = cu.length ? 'co' : 'rong'; ve(); bao(e.message + '.'); }
}

async function napTab() {
  try {
    await napThongSo();   // QĐ574, QĐ583: khối tiến độ + nút lọc hiện ở mọi ngăn
    if (S.tab === 'chung') await napChung();
    else if (S.tab === 'ketkhoa') await napKetKhoa();
    else if (S.tab === 'taikhoan') await napTaiKhoan();
    else if (S.tab === 'capnhat') { veCapNhat(await api('/capnhat')); await napCongCu(); }   // Y46: khối Công cụ AI
  } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); }
}

// ---- Màn 09 ngăn Chung (QĐ627; chế độ màu QĐ411, QĐ562; tên miền QĐ634 – chữ QĐ650, QĐ651; múi giờ QĐ636 – chữ QĐ652, Bổ sung
// QĐ652; dấu ảnh AI QĐ647, QĐ649; icon QĐ653). Đổi tên miền, múi giờ: chỉ Chủ, hỏi mật khẩu + mã 02 lớp (máy chủ kiểm lại).
const CHU_CG = {mau: 'Chế độ màu', seg: [['sang', 'sun', 'Sáng'], ['toi', 'moon', 'Tối'], ['hethong', 'monitor', 'Theo hệ thống']],
  c2pa: 'Giữ dấu ảnh AI', c2paGhi: 'Chưa có tác dụng: GĐ 1 chưa tạo ảnh. Dùng khi có module Marketing.', c2paHt: 'Gỡ dấu ảnh AI?',
  c2paHc: 'Dấu cho biết ảnh do AI tạo; Facebook đọc dấu này để gắn nhãn nội dung AI. Chỉ áp dụng cho ảnh tạo từ lúc này, ảnh đã tạo không đổi.',
  c2paHn: 'Gỡ dấu', mk: 'Mật khẩu đang dùng', ma: 'Mã 06 số'};
const CHU_TM = {ten: 'Tên miền', cot: ['Địa chỉ', 'DNS', 'HTTPS'], goc: 'Tên gốc', rieng: 'Tên riêng', dok: 'Đã trỏ đúng', dsai: 'Chưa trỏ về máy chủ',
  hok: 'Đang chạy · đến {n}', hcho: 'Chờ DNS', hchua: 'Chưa đọc được', dkr: 'Chưa kiểm được, bấm Kiểm tra lại', onhan: 'Tên miền riêng', ogy: 'Ví dụ: igm.tencongty.vn',
  luu: 'Lưu và kiểm tra', kt: 'Kiểm tra lại', bo: 'Bỏ tên riêng',
  cdns: 'Tên miền chưa trỏ về máy chủ này: trỏ bản ghi A về cùng địa chỉ với tên gốc, rồi bấm Kiểm tra lại. Trong lúc chờ vẫn vào bằng tên gốc.',
  cbat: 'Chưa bật đổi tên miền: máy chủ cần chạy 01 lệnh nâng cấu hình. Tên gốc vẫn chạy.',
  ghi: 'Đổi tên miền thì đăng nhập lại ở địa chỉ mới. Nối lại Google Drive: thêm địa chỉ mới ở Google Cloud. Tên gốc luôn dùng được.',
  khoa: 'Chỉ tài khoản Chủ đổi tên miền', ht: 'Đổi tên miền?', hn: 'Lưu tên miền',
  hc: 'IGM360 sẽ mở được ở {moi}; tên gốc {goc} vẫn dùng được. Nhập mật khẩu và mã 06 số đang hiện trên điện thoại để xác nhận.',
  // QĐ657 (4), (5) cột B: hộp "Bỏ tên riêng"
  boHt: 'Bỏ tên riêng?', boHn: 'Bỏ tên riêng',
  boHc: 'IGM360 chỉ còn mở ở tên gốc {goc}. Nhập mật khẩu và mã 06 số đang hiện trên điện thoại để xác nhận.'};
const CHU_MG = {ten: 'Múi giờ', vn: 'Việt Nam – Hồ Chí Minh (UTC+7)', tim: 'Tìm thành phố hoặc nước', goiy: 'Gợi ý', tatca: 'Tất cả múi giờ · {n}',
  khop: 'khớp “{q}”', bay: 'Giờ ở đó lúc này: {g}', luu: 'Lưu', ghi: 'Dùng cho giờ hiện, ngày số liệu, kỳ mới, giờ gửi báo cáo và giờ nhắc.',
  khoa: 'Chỉ tài khoản Chủ đổi múi giờ', ht: 'Đổi múi giờ sang {ten}?', hc: 'Từ lúc lưu, giờ hiện, ngày số liệu và kỳ mới tính theo {ten}.',
  ds: ['Kỳ đang mở {ky}: dòng ghi quanh nửa đêm hôm đổi có thể lệch 01 ngày.', 'Số các kỳ đã chốt không đổi.', 'Báo cáo đã gửi không đổi.',
    'Đối soát với sàn vẫn theo giờ của sàn.', 'Giờ gửi báo cáo, giờ nhắc dời theo múi mới.'], hn: 'Đổi múi giờ'};
const DCG = {c2pa: true, tm: null, kiem: null, mg: null, mgChon: null, mgMo: false, mgTim: '', canMa: true, xmLam: null};
const lechMui = tz => { try { const p = new Intl.DateTimeFormat('en-US', {timeZone: tz, timeZoneName: 'shortOffset'}).formatToParts(new Date())
  .find(x => x.type === 'timeZoneName').value.replace('GMT', ''); return 'UTC' + (p ? p.replace('-', '\u2212') : '+0'); } catch (e) { return ''; } };
const thanhPho = tz => tz.split('/').pop().replace(/_/g, ' ');
const tenNuoc = tz => nuocVi(DCG.mg && (DCG.mg.quoc_gia || {})[tz]);
const tenMui = tz => tz === 'Asia/Ho_Chi_Minh' ? CHU_MG.vn : (tenNuoc(tz) ? tenNuoc(tz) + ' – ' : '') + thanhPho(tz) + ' (' + lechMui(tz) + ')';
const tenMuiNgan = tz => tz === 'Asia/Ho_Chi_Minh' ? 'Hồ Chí Minh (UTC+7)' : thanhPho(tz) + ' (' + lechMui(tz) + ')';
const gioO = tz => { try { return new Intl.DateTimeFormat('vi-VN', {timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false}).format(new Date()); } catch (e) { return ''; } };
const icCg = k => '<span class="cg-ic' + (k ? '' : ' trong') + '">' + (k ? icoMau(ICON[k], 'var(--phu)', 16) : '') + '</span>';
const canhCg = t => '<div class="tm-w" role="status">' + icoMau(ICON['circle-alert'], 'var(--xem)', 16) + '<span>' + cum(t) + '</span></div>';
async function napChung() {
  const [c, tm, mg, toi] = await Promise.all([api('/caidat/chung'), api('/tenmien'), api('/muigio'), api('/toi')]);
  DCG.c2pa = c.c2pa; DCG.tm = tm; DCG.mg = mg; DCG.canMa = !!toi.da_bat_2lop; if (!DCG.mgChon) DCG.mgChon = mg.muigio; veChung();
  api('/tenmien/kiem').then(k => { DCG.kiem = k; veChung(); }).catch(() => {});   // dò DNS, đọc chứng chỉ chạy lâu: vẽ trước, điền sau
}
function veChung() {
  const g = $('#ngan-chung'); if (!g) return; const o = $('#tm-o'), giu = o ? o.value : null;
  const che = window.CHEDO ? CHEDO.doc() : 'hethong';
  let h = '<div class="cg-d">' + icCg(che === 'toi' ? 'moon' : 'sun') + '<span class="cg-tt">' + CHU_CG.mau + '</span><span class="cg-seg" role="radiogroup" aria-label="' + CHU_CG.mau + '">'
    + CHU_CG.seg.map(([k, ic, t]) => '<button class="cg-sg' + (k === che ? ' on' : '') + '" role="radio" aria-checked="' + (k === che) + '" data-chedo="' + k + '">'
      + icoMau(ICON[ic], k === che ? 'var(--chu-tren-nut)' : 'var(--phu)', 14) + t + '</button>').join('') + '</span></div>';
  h += veTenMien() + veMuiGio();
  h += '<div class="cg-d">' + icCg('stamp') + '<span class="cg-tt">' + CHU_CG.c2pa + '<span class="cg-pt">' + cum(CHU_CG.c2paGhi) + '</span></span>'
    + '<button class="gat-o nut-gat" data-c2pa role="switch" aria-checked="' + DCG.c2pa + '" aria-label="' + CHU_CG.c2pa + '"><input type="checkbox" tabindex="-1"'
    + (DCG.c2pa ? ' checked' : '') + '><span class="gat"></span></button></div>';
  g.innerHTML = h;
  if (giu !== null && $('#tm-o')) $('#tm-o').value = giu;
}
function veTenMien() {
  const tm = DCG.tm; if (!tm) return ''; const k = DCG.kiem, C = CHU_TM;
  const tt = (ic, cls, t) => '<span class="tm-t ' + cls + '">' + (ic ? icoMau(ICON[ic], cls === 'dat' ? 'var(--dat)' : 'var(--xem)', 16) : '') + '<span>' + t + '</span></span>';
  const https = x => !x ? tt('', 'pt0', '–') : x.https === 'chay' ? tt('circle-check', 'dat', C.hok.replace('{n}', ngay(x.den)))
    : tt('', 'pt0', x.https === 'cho_dns' ? C.hcho : C.hchua);   // QĐ650
  const dns = x => !x ? tt('', 'pt0', '–') : x.dns === 'khong_ro' ? tt('', 'pt0', C.dkr) : x.dns === 'dung' ? tt('circle-check', 'dat', C.dok) : tt('circle-alert', 'xem', C.dsai);
  const dong = (ten, nhan, d, ht) => '<div class="tm-r"><div class="tm-c"><b>' + esc(ten) + '</b><span class="tm-g">' + nhan + '</span></div><div class="tm-c"><span class="tm-nl">'
    + C.cot[1] + '</span>' + d + '</div><div class="tm-c"><span class="tm-nl">' + C.cot[2] + '</span>' + ht + '</div></div>';
  let s = '<div class="cg-d cg-tm">' + icCg('globe') + '<div class="tm-k"><div>' + C.ten + '</div><div class="tm-b" role="table"><div class="tm-r tm-th">'
    + C.cot.map(x => '<div class="tm-c">' + x + '</div>').join('') + '</div>' + dong(tm.goc, C.goc, tt('', 'pt0', '–'), https(k && k.goc));
  if (tm.rieng) s += dong(tm.rieng, C.rieng, dns(k && k.rieng), https(k && k.rieng));
  s += '</div>';
  if (k && k.rieng && k.rieng.dns === 'chua') s += canhCg(C.cdns);
  if (!tm.bat) s += canhCg(C.cbat);
  if (tm.la_chu) {
    s += '<div class="tm-n"><label class="tm-l" for="tm-o">' + C.onhan + '</label><div class="tm-h"><span class="cg-onhap' + (tm.bat ? '' : ' tat') + '"><input id="tm-o"'
      + (tm.bat ? '' : ' disabled') + ' value="' + esc(tm.rieng || '') + '" placeholder="' + C.ogy + '" autocomplete="off" spellcheck="false"></span>'
      + '<button class="btn btn-chinh" data-tm-luu' + (tm.bat ? '' : ' disabled') + '>' + C.luu + '</button></div>';
    if (tm.rieng) s += '<div class="tm-x">' + (k && k.rieng && (k.rieng.dns === 'chua' || k.rieng.dns === 'khong_ro') ? '<button class="btn-chu" data-tm-kiem>' + C.kt + '</button>' : '')
      + '<button class="btn-chu" data-tm-bo>' + C.bo + '</button></div>';
    s += '</div>';
  } else s += '<div class="tm-k2">' + icoMau(ICON.lock, 'var(--phu)', 14) + '<span>' + C.khoa + '</span></div>';
  return s + '<div class="cg-pt">' + cum(C.ghi) + '</div></div></div>';
}
function veMuiGio() {
  const mg = DCG.mg; if (!mg) return ''; const C = CHU_MG, chon = DCG.mgChon || mg.muigio, doi = chon !== mg.muigio;
  let s = '<div class="cg-d cg-mg">' + icCg('') + '<div class="tm-k"><div>' + C.ten + '</div>';
  if (mg.ban) s += canhCg(mg.ban);
  if (mg.la_chu) {
    s += '<div class="tm-h"><button class="mg-o' + (DCG.mgMo ? ' mo' : '') + '" data-mg-mo aria-expanded="' + DCG.mgMo + '"><span class="mg-och">' + esc(tenMui(chon))
      + '</span>' + icoMau(ICON['chevron-down'], 'var(--phu)', 16) + '</button>' + (doi ? '<button class="btn btn-chinh" data-mg-luu>' + C.luu + '</button>' : '') + '</div>';
    if (DCG.mgMo) s += '<div class="mg-p" role="listbox">' + veMgDs() + '</div>';
  } else s += '<div class="tm-h"><span class="mg-o tat"><span class="mg-och">' + esc(tenMui(chon)) + '</span></span></div><div class="tm-k2">'
    + icoMau(ICON.lock, 'var(--phu)', 14) + '<span>' + C.khoa + '</span></div>';
  return s + '<div class="cg-pt">' + C.bay.replace('{g}', gioO(chon)) + ' · ' + cum(C.ghi) + '</div></div></div>';
}
function veMgDs() {
  const mg = DCG.mg, q = DCG.mgTim.trim().toLowerCase();
  const goiy = [...new Set([mg.muigio, 'Asia/Ho_Chi_Minh', 'Asia/Singapore'])].filter(x => mg.danh_sach.includes(x));
  const khop = q ? mg.danh_sach.filter(x => (x + ' ' + tenMui(x)).toLowerCase().includes(q)) : mg.danh_sach;
  const muc = x => '<button class="mg-i' + (x === DCG.mgChon ? ' on' : '') + '" role="option" aria-selected="' + (x === DCG.mgChon) + '" data-mg-chon="' + esc(x) + '">'
    + (x === DCG.mgChon ? icoMau(ICON.check, 'var(--xanh-chu)', 16) : '<i></i>') + esc(tenMui(x)) + '</button>';
  return '<label class="cg-onhap mg-t">' + icoMau(ICON.search, 'var(--phu)', 16) + '<input id="mg-tim" value="' + esc(DCG.mgTim) + '" placeholder="' + CHU_MG.tim
    + '" aria-label="' + CHU_MG.tim + '"></label><div class="mg-ds">' + (q ? '' : '<div class="mg-n">' + CHU_MG.goiy + '</div>' + goiy.map(muc).join(''))
    + '<div class="mg-n">' + CHU_MG.tatca.replace('{n}', hai(mg.danh_sach.length)) + (q ? ' · ' + CHU_MG.khop.replace('{q}', esc(DCG.mgTim.trim())) : '') + '</div>'
    + khop.map(muc).join('') + '</div>';
}
function moXacMinh(ico, tieu, chu, nut, lam) {   // hộp hỏi mật khẩu + mã 02 lớp (QĐ634, QĐ636); lỗi hiện theo cách hộp 02 lớp (loi2Lop)
  let l = $('#h-xacminh');
  if (!l) { l = document.createElement('div'); l.className = 'lop'; l.id = 'h-xacminh'; l.hidden = true;
    l.innerHTML = '<div class="hop" role="dialog" aria-modal="true" aria-labelledby="xm-tieu"><div class="hop-dau"><span id="xm-ico"></span><b class="f1 t16" id="xm-tieu"></b>'
      + '<button class="nut-ico" data-dong aria-label="Đóng">' + icoMau(ICON.x, 'var(--phu)', 18) + '</button></div><div class="hop-than"><div class="t13" id="xm-chu"></div>'
      + '<label class="tm-l xm-l">' + CHU_CG.mk + '<span class="o-nhap cg-onhap"><input type="password" id="xm-mk" autocomplete="current-password"></span></label>'
      + '<div class="xm-l" id="xm-ma"><span class="tm-l">' + CHU_CG.ma + '</span><div class="o6-hang">' + '<input class="o6" maxlength="1" inputmode="numeric">'.repeat(6) + '</div></div>'
      + '<div class="dong t13" data-loi2lop style="gap:6px;color:var(--canh);align-items:flex-start;margin-top:12px" hidden>' + icoMau(ICON['circle-alert'], 'var(--canh)', 16)
      + '<span></span></div></div><div class="hop-chan"><button class="btn btn-phu" data-dong>Hủy</button><button class="btn btn-chinh" id="xm-nut" data-xacminh></button></div></div>';
    $('#khung').appendChild(l); }
  $('#xm-ico').innerHTML = icoMau(ICON[ico], 'var(--xanh-chu)', 20); $('#xm-tieu').textContent = tieu; $('#xm-chu').innerHTML = chu; $('#xm-nut').textContent = nut;
  $('#xm-ma').hidden = !DCG.canMa; DCG.xmLam = lam; xoa6(l); $('#xm-mk').value = ''; $('[data-loi2lop]', l).hidden = true;
  $$('.o6', l).forEach(i => i.style.borderColor = ''); $$('.o-nhap', l).forEach(e => e.classList.remove('loi')); mo('h-xacminh'); $('#xm-mk').focus();
}
async function nutChung(t, d) {   // trả true khi đã xử lý nút của ngăn Chung
  if (d.chedo) { CHEDO.dat(d.chedo); veChung(); return true; }
  if ('c2pa' in d) { const bat = !DCG.c2pa;
    const lam = async () => { try { await api('/thongso/anh_ai_giu_dau_c2pa/gat', {bat}); DCG.c2pa = bat; } catch (e) { if (e.status) bao(e.message + '.'); } veChung(); };
    if (bat) await lam(); else xacnhan(CHU_CG.c2paHt, cum(CHU_CG.c2paHc), CHU_CG.c2paHn, lam, 'circle-alert');   // QĐ647: chỉ hỏi khi gỡ dấu
    return true; }
  if ('tmLuu' in d || 'tmBo' in d) { const bo = 'tmBo' in d, ten = bo ? '' : ($('#tm-o').value || '').trim(), C = CHU_TM;
    moXacMinh(bo ? 'globe' : 'globe', bo ? C.boHt : C.ht, cum((bo ? C.boHc : C.hc).replace('{moi}', esc(ten)).replace('{goc}', esc(DCG.tm.goc))), bo ? C.boHn : C.hn,
      async (mk, ma) => { const kq = await api('/tenmien', {ten, matkhau: mk, ma}); DCG.tm.rieng = kq.ten || null; DCG.kiem = kq.kiem; veChung(); });
    return true; }
  if ('tmKiem' in d) { DCG.kiem = null; veChung(); try { DCG.kiem = await api('/tenmien/kiem'); } catch (e) { if (e.status) bao(e.message + '.'); } veChung(); return true; }
  if ('mgMo' in d) { DCG.mgMo = !DCG.mgMo; DCG.mgTim = ''; veChung(); const i = $('#mg-tim'); if (i) i.focus(); return true; }
  if (d.mgChon) { DCG.mgChon = d.mgChon; DCG.mgMo = false; veChung(); return true; }
  if ('mgLuu' in d) { const tz = DCG.mgChon, ten = tenMuiNgan(tz), C = CHU_MG, [nam, thang] = DCG.mg.hom_nay.split('-'), ky = thang + '/' + nam;   // kỳ đang mở theo ngày số liệu ② (QĐ636)
    moXacMinh('circle-alert', C.ht.replace('{ten}', ten), cum(C.hc.replace('{ten}', ten)) + '<ol class="mg-l">' + C.ds.map(x => '<li>' + cum(x.replace('{ky}', ky)) + '</li>').join('') + '</ol>',
      C.hn, async (mk, ma) => { const kq = await api('/muigio', {ten: 'muigio', giatri: tz, matkhau: mk, ma}); DCG.mg.muigio = tz; DCG.mg.hom_nay = kq.hom_nay; MUI = tz; veChung(); ve(); });
    return true; }
  if ('xacminh' in d) { const l = $('#h-xacminh'), goc = t.textContent; t.classList.add('dang'); t.textContent = CHU_DN.dang;
    try { await DCG.xmLam($('#xm-mk').value, ma6(l)); l.hidden = true; }
    catch (e) { if (e.matKetNoi) bao(e.message + '.'); else loi2Lop(l, e); xoa6(l); }
    finally { t.classList.remove('dang'); t.textContent = goc; }
    return true; }
  return false;
}
document.addEventListener('input', ev => { if (ev.target.id !== 'mg-tim') return; DCG.mgTim = ev.target.value; const ds = $('.mg-ds');
  if (ds) { const tam = document.createElement('div'); tam.innerHTML = veMgDs(); ds.replaceWith($('.mg-ds', tam)); } });

// ---- QĐ548 B, QĐ551, QĐ553, QĐ559, chữ QĐ566: chuông · âm thanh · chế độ màu ở góc phải khung; menu tài khoản; Tạm tắt
// icon Lucide (ISC) mới – QĐ566 (9): bell-off (nét bản DM lc_010.js), volume-x, megaphone (nét bản CDO Toi_Lop.js)
ICON.watch = ICON.watch || svgLucide('watch', ['<circle cx="12" cy="12" r="6" />', '<polyline points="12 10 12 12 13 13" />',
  'm16.13 7.66-.81-4.05a2 2 0 0 0-2-1.61h-2.68a2 2 0 0 0-2 1.61l-.78 4.05', 'm7.88 16.36.8 4a2 2 0 0 0 2 1.61h2.72a2 2 0 0 0 2-1.61l.81-4.05']);   // Lucide (ISC) 0.468.0: tin đổi múi giờ (QĐ663)
ICON['bell-off'] = svgLucide('bell-off', ['M10.268 21a2 2 0 0 0 3.464 0', 'M17 17H4a1 1 0 0 1-.74-1.673C4.59 13.956 6 12.499 6 8a6 6 0 0 1 .258-1.742',
  'm2 2 20 20', 'M8.668 3.01A6 6 0 0 1 18 8c0 2.687.77 4.653 1.707 6.05']);
ICON['volume-x'] = svgLucide('volume-x', ['M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z',
  '<line x1="22" x2="16" y1="9" y2="15" />', '<line x1="16" x2="22" y1="9" y2="15" />']);
ICON.megaphone = svgLucide('megaphone', ['m3 11 18-5v12L3 14v-3z', 'M11.6 16.8a3 3 0 1 1-5.8-1.6']);
const CHU_BA = {amBat: 'Đang bật âm thanh – bấm để tắt', amTat: 'Đang tắt âm thanh – bấm để bật', cheDo: 'Chế độ màu',   // QĐ566 (2), (3)
  tamTat: 'Tạm tắt', moLai: 'Mở lại', canXl: 'Cần xử lý', thongBao: 'Thông báo', hienDoc: n => 'Hiện ' + n + ' tin đã đọc',   // QĐ566 (6)
  daiTat: 'Đang tạm tắt thông báo. Tin nghiêm trọng (sao lưu lỗi, ổ đầy) vẫn báo.', coGiMoi: 'Có gì mới', docHet: 'Đọc hết',   // QĐ566 (7)
  rong: 'Không có thông báo nào còn mở.'};
const KHOA_AM = 'igm360_amthanh';   // QĐ547: âm thanh mặc định bật, nhớ theo từng máy
const amBat = () => { try { return localStorage.getItem(KHOA_AM) !== 'tat'; } catch (e) { return true; } };
function datAm(bat) { try { if (bat) localStorage.removeItem(KHOA_AM); else localStorage.setItem(KHOA_AM, 'tat'); } catch (e) { /* máy chặn lưu */ } veBa(); }
function keuChuong() {   // tiếng báo tin mới: 02 nốt ngắn bằng Web Audio của trình duyệt (0 thư viện, 0 tệp âm thanh)
  try { const C = window.AudioContext || window.webkitAudioContext; if (!C) return; const a = D.amCtx || (D.amCtx = new C());
    [[880, 0], [1175, .12]].forEach(([f, t]) => { const o = a.createOscillator(), g = a.createGain(); o.type = 'sine'; o.frequency.value = f;
      g.gain.setValueAtTime(.0001, a.currentTime + t); g.gain.exponentialRampToValueAtTime(.08, a.currentTime + t + .02);
      g.gain.exponentialRampToValueAtTime(.0001, a.currentTime + t + .25); o.connect(g).connect(a.destination); o.start(a.currentTime + t); o.stop(a.currentTime + t + .3); });
  } catch (e) { /* trình duyệt chặn âm thanh khi chưa bấm gì */ }
}
const icoChedo = () => ({sang: 'sun', toi: 'moon', hethong: 'monitor'})[window.CHEDO ? CHEDO.doc() : 'hethong'];
const TEN_CHEDO = {sang: 'Sáng', toi: 'Tối', hethong: 'Theo hệ thống'};   // QĐ566 (4)
function dienIco(goc) { $$('i[data-ic]', goc).forEach(i => { if (ICON[i.dataset.ic]) i.outerHTML = icoMau(ICON[i.dataset.ic], 'currentColor', +(i.dataset.co || 18)); }); }
function veBa() {
  const so = D.tbSoMoi || 0, tat = !!D.tbTamTat, c = $('[data-chuong]'), am = amBat();
  if (c) { c.classList.toggle('tat', tat);
    c.innerHTML = icoMau(ICON[tat ? 'bell-off' : 'bell'], 'currentColor', 20) + (tat ? CHU_BA.tamTat : '')
      + (so ? '<span class="so' + (D.tbCoDo ? ' do' : '') + '">' + (so > 99 ? '99+' : soVN(so)) + '</span>' : ''); }   // QĐ553 (2): tối đa "99+"
  const a = $('.vi-tri [data-amthanh]'); if (a) { a.innerHTML = icoMau(ICON[am ? 'volume-2' : 'volume-x'], 'currentColor', 20); a.title = am ? CHU_BA.amBat : CHU_BA.amTat; a.setAttribute('aria-label', a.title); }
  const m = $('.vi-tri > [data-chedonut]'); if (m) m.innerHTML = icoMau(ICON[icoChedo()], 'currentColor', 20);
  const t = $('.vi-tri > [data-tk]'); if (t && !t.firstChild) t.innerHTML = icoMau(ICON['user-round'], 'currentColor', 20);
  const ta = $('#tk-am'); if (ta) ta.innerHTML = '<span class="tl-cong' + (am ? ' bat' : '') + '" role="switch" aria-checked="' + am + '"></span>';
  const tc = $('#tk-chedo'); if (tc && window.CHEDO) tc.textContent = TEN_CHEDO[CHEDO.doc()];
  const tb = $('#tk-ban'); if (tb) tb.textContent = D.tbBan || '';
}
function veCheDoTha() {
  const c = window.CHEDO ? CHEDO.doc() : 'hethong';
  $('#tha-chedo').innerHTML = [['sang', 'sun'], ['toi', 'moon'], ['hethong', 'monitor']].map(([k, ic]) => '<button class="tha-muc' + (k === c ? ' on' : '')
    + '" role="menuitemradio" aria-checked="' + (k === c) + '" data-cdmau="' + k + '">' + icoMau(ICON[ic], 'currentColor', 18) + '<span class="f1">' + TEN_CHEDO[k] + '</span>'
    + (k === c ? icoMau(ICON.check, 'var(--xanh-chu)', 16) : '') + '</button>').join('');
}
dienIco(document); veBa();

// ---- Màn 09 ngăn Két khóa (bản DM-03NGAN-0100; QĐ661: 1440 bảng, 1024 và 390 hàng gọn + nút ⋯ mở Đổi / Xóa; chữ bản GĐ 1 màn 09, QĐ297)
ICON.ellipsis = ICON.ellipsis || svgLucide('ellipsis', ['<circle cx="12" cy="12" r="1" />', '<circle cx="19" cy="12" r="1" />', '<circle cx="5" cy="12" r="1" />']);   // Lucide (ISC): nút ⋯
const CHU_KK = {tong: (n, h, s) => hai(n) + ' khóa · ' + hai(h) + ' hết hạn · ' + hai(s) + ' sắp hết hạn',
  ghi: n => 'Khóa được mã hóa, AI không đọc được. Màn này chỉ hiện 04 ký tự cuối. Báo trước <b>' + hai(n) + ' ngày</b> khi khóa sắp hết hạn, đổi số ngày ở ngăn Thông số.',
  cot: ['Dịch vụ · dùng cho', 'Khóa', 'Hạn', 'Dùng lần cuối', 'Trạng thái'], dung: 'Đang dùng', sap: 'Sắp hết hạn', het: 'Hết hạn',
  con: n => 'Còn ' + hai(n) + ' ngày', khongHan: 'Không đặt hạn', doi: 'Đổi', xoa: 'Xóa', them: 'Đổi, Xóa', chung: 'Dùng chung',
  doiT: t => 'Đổi khóa · ' + t, khoa: 'Khóa', han: 'Hạn (nếu có)', luuGhi: 'Lưu xong, khóa được mã hóa và chỉ hiện 04 ký tự cuối.', luu: 'Lưu khóa',
  daLuu: 'Đã lưu khóa. Màn chỉ hiện 04 ký tự cuối.', xoaT: t => 'Xóa khóa ' + t + '?', xoaN: 'Xóa khóa', daXoa: 'Đã xóa khóa.',
  xoaC: 'Nguồn đang dùng khóa này sẽ ngừng lấy số cho tới khi có khóa mới. Xóa rồi không lấy lại được.', rong: 'Chưa có khóa nào trong két.'};   // rong: TẠM
async function napKetKhoa() { D.kk = await api('/kekhoa'); veKetKhoa(); }
function veKetKhoa() {
  const g = $('#ngan-ketkhoa'); if (!g || !D.kk) return; const k = D.kk, C = CHU_KK, dem = k.dem || {};
  const sap = dem.saphet || 0, het = dem.hethan || 0, dung = (dem.dung || 0) + (dem.khong_han || 0);
  const tt = x => x.tinhtrang === 'hethan' ? ['canh', C.het] : x.tinhtrang === 'saphet' ? ['xem', C.con(Math.max(0, x.con_ngay || 0))] : ['dat', C.dung];
  const nhan = x => { const [m, t] = tt(x); return '<span class="kk-tt ' + m + '"><i></i>' + cum(t) + '</span>'; };
  const han = x => x.han ? ngay(x.han) : C.khongHan, dung1 = x => x.lan_dung_cuoi ? luc(x.lan_dung_cuoi) : '–';
  const tac = x => '<button class="btn-chu" data-kkdoi="' + esc(x.id) + '">' + icoMau(ICON.replace || ICON['refresh-cw'], 'var(--xanh-chu)', 15) + C.doi + '</button>'
    + '<button class="btn-chu do" data-kkxoa="' + esc(x.id) + '">' + icoMau(ICON['trash-2'], 'var(--canh)', 15) + C.xoa + '</button>';
  let h = '<div class="the kk-tong"><span class="kk-ic">' + icoMau(ICON.vault, 'var(--xanh-chu)', 22) + '</span><div class="f1"><b class="t16">' + cum(C.tong(k.tong, het, sap)) + '</b>'
    + '<div class="kk-thanh"><i style="flex:' + dung + ';background:var(--h-dat)"></i><i style="flex:' + sap + ';background:var(--h-xem)"></i><i style="flex:' + het + ';background:var(--h-canh)"></i></div>'
    + '<div class="kk-chu"><span><i style="background:var(--h-dat)"></i>' + C.dung + '</span><span><i style="background:var(--h-xem)"></i>' + C.sap + '</span><span><i style="background:var(--h-canh)"></i>' + C.het + '</span></div></div></div>'
    + '<div class="dong t13 kk-ghi">' + icoMau(ICON['lock-keyhole'] || ICON.lock, 'var(--dat)', 15) + '<span>' + C.ghi(k.songay_baotruoc) + '</span></div>';
  if (!k.ds.length) h += '<div class="the cho-dung"><div class="phu">' + C.rong + '</div></div>';
  else h += '<div class="kk-bang"><div class="kk-h kk-dau">' + C.cot.map(x => '<span>' + x + '</span>').join('') + '<span></span></div>'
    + k.ds.map(x => '<div class="kk-h"><span class="kk-ten"><b>' + esc(x.ten) + '</b><span class="t12 phu">' + C.chung + '</span></span><span class="so">•••• ' + esc(x.kytu_cuoi || '') + '</span>'
      + '<span class="nw" data-l="' + C.cot[2] + '">' + esc(han(x)) + '</span><span class="nw" data-l="' + C.cot[3] + '">' + esc(dung1(x)) + '</span><span>' + nhan(x) + '</span>'
      + '<span class="phai kk-tac">' + tac(x) + '</span><button class="nut-ico kk-ba" data-kkba="' + esc(x.id) + '" aria-label="' + C.them + '" title="' + C.them + '">' + icoMau(ICON.ellipsis || ICON['more-horizontal'] || '', 'var(--phu)', 18) + '</button></div>').join('') + '</div>';
  g.innerHTML = h;
}
function moDoiKhoa(id) {
  const x = D.kk.ds.find(k => k.id === id); if (!x) return; const C = CHU_KK;
  if (!$('#h-kkdoi')) $('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-kkdoi" hidden><div class="hop"><div class="hop-dau">' + icoMau(ICON['key-round'], 'var(--xanh-chu)', 20)
    + '<b class="f1 t16" data-tieu></b><button class="nut-ico" data-dong aria-label="Đóng">' + icoMau(ICON.x, 'var(--phu)', 18) + '</button></div><div class="hop-than">'
    + '<label class="tm-l">' + C.khoa + '<span class="o-nhap cg-onhap"><input id="kk-gt" autocomplete="off" spellcheck="false"></span></label>'
    + '<label class="tm-l xm-l">' + C.han + '<span class="o-nhap cg-onhap"><input id="kk-han" type="date"></span></label><div class="t12 phu" style="margin-top:10px">' + C.luuGhi + '</div></div>'
    + '<div class="hop-chan"><button class="btn btn-phu" data-dong>Hủy</button><button class="btn btn-chinh" data-kkluu>' + C.luu + '</button></div></div></div>');
  $('#h-kkdoi [data-tieu]').textContent = C.doiT(x.ten); $('#kk-gt').value = ''; $('#kk-han').value = x.han ? String(x.han).split('T')[0] : ''; D.kkDoi = id; mo('h-kkdoi'); $('#kk-gt').focus();
}
async function nutKetKhoa(t, d) {
  if (d.kkdoi) { dongTha(); moDoiKhoa(d.kkdoi); return true; }
  if (d.kkxoa) { dongTha(); const x = D.kk.ds.find(k => k.id === d.kkxoa); if (!x) return true;
    xacnhan(CHU_KK.xoaT(x.ten), cum(CHU_KK.xoaC), CHU_KK.xoaN, async () => { try { await api('/kekhoa/' + encodeURIComponent(x.id) + '/xoa', {}); bao(CHU_KK.daXoa); }
      catch (e) { if (e.status) bao(e.message + '.'); } await napKetKhoa(); }, 'trash-2'); return true; }
  if ('kkluu' in d) { const gt = $('#kk-gt').value.trim(); if (!gt) { $('#kk-gt').focus(); return true; }
    try { await api('/kekhoa/' + encodeURIComponent(D.kkDoi) + '/doi', {giatri: gt, han: $('#kk-han').value || null}); dongHop(); bao(CHU_KK.daLuu); }
    catch (e) { if (e.status) bao(e.message + '.'); } $('#kk-gt').value = ''; await napKetKhoa(); return true; }
  if (d.kkba) { const e = $('#tha-kk') || (() => { $('#khung').insertAdjacentHTML('beforeend', '<div class="tha tha-kk" id="tha-kk" hidden role="menu"></div>'); return $('#tha-kk'); })();
    const v = e.hidden; dongTha(); e.innerHTML = '<button class="tha-muc" data-kkdoi="' + esc(d.kkba) + '">' + icoMau(ICON.replace || ICON['refresh-cw'], 'currentColor', 16) + CHU_KK.doi + '</button>'
      + '<button class="tha-muc do-chu" data-kkxoa="' + esc(d.kkba) + '">' + icoMau(ICON['trash-2'], 'var(--canh)', 16) + CHU_KK.xoa + '</button>';
    e.hidden = !v; const r = t.getBoundingClientRect(); e.style.position = 'fixed'; e.style['top'] = Math.round(r.bottom + 4) + 'px'; e.style['left'] = Math.round(Math.max(8, r.right - 180)) + 'px'; return true; }
  return false;
}

// ---- Bấm
document.addEventListener('click', async ev => {
  if (ev.target.classList && ev.target.classList.contains('lop')) { dongHop(); return; }
  const t = ev.target.closest('button'); if (!t) { if (!ev.target.closest('.tha')) dongTha(); return; }
  const d = t.dataset;
  if (!('chuong' in d) && !('tk' in d) && !('chedonut' in d) && !t.closest('.tha')) dongTha();
  if (d.set) { const [k, v] = d.set.split(':'); S[k] = v; }
  else if (D.anToan && ((d.trang && d.trang !== '09') || (d.tab && d.tab !== 'capnhat'))) { bao(CHU_CN.chan); return; }   // QĐ218 dòng 37
  else if (d.trang) { if (S.g !== '01') { S.trang = d.trang; dongHop(); $$('#app .cuon, #app .cuon-trong').forEach(c => c.scrollTop = 0); if (d.trang === '09') napTab(); if (d.trang === '13') napMoHinh(); if (d.trang === '08') napTroChuyen(); } }   // KH-090 2.2 (a): khổ máy tính cuộn ở .cuon-trong
  else if ('thu' in d) S.thu = S.thu ? 0 : 1;
  else if (S.trang === '09' && S.tab === 'chung' && await nutChung(t, d)) { /* ngăn Chung */ }
  else if (await nutKetKhoa(t, d)) { /* ngăn Két khóa */ }
  else if (d.tab) { S.tab = d.tab; if (d.tab === 'thongso') S.nhom = d.nhom || NHOM_CD[0]; if (t.closest('#cd-menu')) S.cdMan = 2; napTab(); }
  else if ('cdLui' in d) S.cdMan = 1;   // điện thoại: về danh sách ngăn
  else if ('mat' in d) { const i = $('#mk'), hien = i.type === 'password'; i.type = hien ? 'text' : 'password';   // QĐ369 (6), QĐ404
    t.innerHTML = icoMau(ICON[hien ? 'eye' : 'eye-off'], 'var(--phu)', 18).replace('<svg', '<svg aria-hidden="true"'); t.setAttribute('aria-label', hien ? CHU_DN.an : CHU_DN.hien); }
  else if ('dangnhap' in d) { await dangNhap(); return; }
  else if ('xacnhan' in d) { await xacNhanMa(t); return; }
  else if ('dangxuat' in d) { dongHop(); try { await api('/dangxuat', {}); } catch (e) { /* vẫn ra màn đăng nhập */ }
    S.g = '01'; S.dn = 'matkhau'; bao('Đã đăng xuất. Phiên trên máy này đã được thu hồi.'); }
  else if ('chuong' in d) { const e = $('#tha-chuong'), v = e.hidden; dongTha(); D.tbHienDoc = false; if (D.tbCuoi) veChuong(D.tbCuoi); e.hidden = !v; datTha(e, t); if (v) demSo(true); }
  else if ('tamtat' in d) { try { await api('/thongso/chuong_tamtat/gat', {bat: !D.tbTamTat}); } catch (er) { if (er.status) bao(er.message + '.'); } await demSo(); }   // QĐ551
  else if (d.tbthe) { D.tbThe = d.tbthe; D.tbHienDoc = false; if (D.tbCuoi) veChuong(D.tbCuoi); }
  else if ('tbhien' in d) { D.tbHienDoc = true; if (D.tbCuoi) veChuong(D.tbCuoi); }
  else if ('amthanh' in d) datAm(!amBat());   // QĐ547
  else if ('chedonut' in d) { const e = $('#tha-chedo'), v = e.hidden; dongTha(); veCheDoTha(); e.hidden = !v; datTha(e, $('.vi-tri > [data-chedonut]')); }
  else if (d.cdmau) { CHEDO.dat(d.cdmau); dongTha(); veBa(); if (S.trang === '09' && S.tab === 'chung') veChung(); }   // QĐ411, QĐ566 (3), (4)
  else if ('tk' in d) { const e = $('#tha-tk'), v = e.hidden; dongTha(); veBa(); e.hidden = !v; datTha(e, t); }
  else if ('gat2lop' in d) { if (D.tat2lop) hop2Lop('h-bat2lop'); else if (D.anToan) bao(CHU_2LOP.antoan); else hop2Lop('h-tat2lop'); }   // QĐ390
  else if ('bat2lopmo' in d) hop2Lop('h-bat2lop');   // nút "Bật lại" ở dòng cảnh báo
  else if ('tat2lop' in d) await gui2Lop(true);
  else if ('bat2lop' in d) await gui2Lop(false);
  else if ('dochet' in d) { try { await api('/thongbao/dochet', {}); } catch (e) { bao(e.message + '.'); } await demSo(); return; }
  else if (d.di && D.anToan && d.di !== 'capnhat') { bao(CHU_CN.chan); return; }   // QĐ218 dòng 37
  else if (d.di) { dongTha(); if (d.di === 'taikhoan' || d.di === 'ketkhoa' || d.di === 'capnhat' || d.di === 'chung') { S.trang = '09'; S.tab = d.di; napTab(); } else { S.trang = d.di; if (d.di === '09') napTab(); if (d.di === '13') napMoHinh(); }
    if (d.cuon) setTimeout(() => { const e = document.getElementById(d.cuon); if (e) e.scrollIntoView({block: 'start'}); }, 0); }
  else if ('noilai' in d) { try { await api('/demso'); S.k = 'binhthuong'; bao('Đã nối lại máy chủ.'); } catch (e) { /* vẫn mất */ } }
  else if (d.mo) { if (d.mo === 'h-2lop') datLaiDoiMay(); mo(d.mo); }
  else if ('dong' in d) dongHop();
  else if (d.sua) { await moSua(d.sua); }
  else if (d.gat) { await gatCongTac(d.gat); }   // QĐ278: công tắc Thông số
  else if (d.nhomNut !== undefined) { batNhom(d.nhomNut); return; }   // Y52 L1: bấm tiêu đề nhóm
  else if ('cagat' in d) { await gatCongCu(); }   // Y46 (Z20 dòng 1, 12, 13): công tắc Tự nâng mỗi ngày
  else if (d.canang) moNangCongCu(d.canang);   // Z20 dòng 7
  else if (d.cave) moVeCongCu(d.cave);   // Z20 dòng 11
  else if ('luusua' in d) { await luuSua(); }
  else if ('locChua' in d) { S.tab = 'thongso'; S.nhom = 'gom'; S.cdMan = 2; napTab(); }   // QĐ583: 01 bấm sang trang gom
  else if (d.thuhoi) xacnhan('Thu hồi phiên này?', 'Máy đó phải đăng nhập lại mới dùng tiếp được.', 'Thu hồi', async () => {
    try { await api('/phien/' + encodeURIComponent(d.thuhoi) + '/thuhoi', {}); bao('Đã thu hồi phiên.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
  else if ('kiemtra' in d) { try { const k = await api('/capnhat/kiemtra', {}); veCapNhat(k); if (!k.loi) bao(k.co_ban_moi ? 'Có bản mới ' + k.ban_moi + '.' : 'Đã kiểm tra: chưa có bản mới.'); }
    catch (e) { bao('Kiểm tra lại chưa được: ' + (e.status ? e.message : 'mất kết nối máy chủ') + '.'); } }   // Y17 (c)
  else if ('capnhat' in d) moCapNhat();
  else if ('cnngay' in d) { await capNhat('ngay'); }
  else if ('quayve' in d) { moQuayVe(); }
  else if ('cnVan' in d) { await chonDrive(true); return; }
  else if ('cnHuy' in d) { await chonDrive(false); return; }
  else if ('cnKetnoi' in d) { dongHop(); S.trang = '11'; ve(); return; }
  else if ('mdGt' in d) { moMdGt(); return; }
  else if ('mdChep' in d) { try { await navigator.clipboard.writeText(CHU_Z15.lenh); bao(CHU_Z15.daChep); } catch (e) { bao(CHU_Z15.chepLoi); } return; }   // N34
  else if ('cncho' in d) { await capNhat('cho'); }
  else if ('gd' in d) { const g = t.nextElementSibling; g.hidden = !g.hidden; }
  else if ('giu' in d) { try { const k = await api('/phien/giahan', {}); D.hetLuc = k.het_luc; S.k = 'binhthuong';
      bao(Date.parse(k.het_luc) - Date.now() > 5 * 60e3 ? 'Đã gia hạn phiên đăng nhập.' : 'Đã đủ 30 ngày từ lần đăng nhập, bạn đăng nhập lại để dùng tiếp.'); } catch (e) { /* */ } }
  else if ('dxkhac' in d) xacnhan('Đăng xuất mọi máy khác?', 'Các máy khác phải đăng nhập lại. Máy này vẫn giữ đăng nhập.', 'Đăng xuất', async () => {
    try { const k = await api('/phien/thuhoi_khac', {}); bao('Đã đăng xuất ' + hai(k.so) + ' phiên trên các máy khác.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
  else if ('them' in d) mo('h-them');
  else if (d.dnGoi) { dongHop(); if (S.trang !== '13' || !D.md) { S.trang = '13'; ve(); await napMoHinh(); }
    const tk = Number(d.dnTk); if (tk) await batDauDn(d.dnGoi, tk); else await themTk(d.dnGoi); return; }
  else if (d.themGoi) { await themTk(d.themGoi); return; }
  else if ('mcXacnhan' in d) { await danMaClaude(); return; }
  else if (d.mdLay) { t.disabled = true; await mdLay(Number(d.mdLay)); t.disabled = false; return; }
  else if (d.mdDan) { moMdDan(Number(d.mdDan)); return; }
  else if (d.mdGui) { const tk = Number(d.mdGui), o = $('#md-ma-web'), ma = (o || {}).value || '';
    if (!ma.trim()) { bao('Bạn dán mã trang Claude hiện ra.'); return; }
    t.disabled = true; if (o) o.value = '';
    const dai = lamSachMa(ma).startsWith('sk-ant-oat01-');   // N28 (b): mã dài hạn dán nhầm ô bước 2 → lưu như Dán mã
    try { await mdXong(tk, await api(dai ? '/mohinh/goi/claude/madaihan/dan' : '/mohinh/goi/claude/madaihan/ma', {taikhoan: tk, ma: dai ? lamSachMa(ma) : ma})); }
    catch (e) { D.mdh[tk] = {...(D.mdh[tk] || {}), loi: e.message, ct: (e.ct || {}).chi_tiet || ''}; veMoHinh(); } t.disabled = false; return; }
  else if (d.mdLuu) { const tk = Number(d.mdLuu), o = $('#md-ma-dan'), ma = lamSachMa((o || {}).value);   // N28 (a)
    if (!ma) { D.mdDan = {...D.mdDan, loi: CHU_Z15.danTrong}; veMdDan(); return; }
    if (!/^sk-ant-oat01-[A-Za-z0-9_-]{20,}$/.test(ma)) { if (o) o.value = '';
      D.mdDan = {...D.mdDan, loi: ma.startsWith('sk-ant-oat01-') ? CHU_Z15.chuaTron(ma.length) : ma.startsWith('sk-ant-api') ? CHU_Z15.khoaApi
        : CHU_Z15.saiTienTo}; veMdDan(); return; }   // 23, N30
    t.disabled = true; if (o) o.value = '';   // không giữ mã trên màn
    try { const kq = await api('/mohinh/goi/claude/madaihan/dan', {taikhoan: tk, ma}); dongHop(); D.mdDan = null; await mdXong(tk, kq); }
    catch (e) { D.mdDan = {...D.mdDan, loi: e.message}; veMdDan(); } t.disabled = false; return; }
  else if (d.mdHuy) { const tk = Number(d.mdHuy); try { await api('/mohinh/goi/claude/madaihan/huy', {taikhoan: tk}); } catch (e) { /* */ }
    D.mdh[tk] = null; veMoHinh(); return; }
  else if (d.goGoi) { const g = d.goGoi, tk = Number(d.goTk), ten = 'tài khoản ' + tk + ' của ' + tenNguon({goi: g});
    const coMd = g === 'claude' && ((D.md && D.md.goi.claude) || []).some(x => x.taikhoan === tk && x.ma_daihan);
    xacnhan('Gỡ ' + ten + '?', 'Phần mềm ngừng dùng tài khoản này, ô ẩn khỏi màn. Số đã dùng và chi phí cũ giữ nguyên; thao tác ghi vào nhật ký.'
      + (coMd ? '<br><br>' + CHU_MDH + ' của tài khoản này bị xóa khỏi Két&nbsp;khóa; mã vẫn còn hiệu lực ở Claude tới khi bạn thu hồi trên trang của&nbsp;Claude.' : '')
      + '<br><br>Dùng lại thì kết nối lại.', 'Gỡ tài khoản', async () => {
      D.trung[g] = 0;
      try { await api('/mohinh/goi/' + g + '/go', {taikhoan: tk}); bao('Đã gỡ ' + ten + '. Nhật ký đã ghi.'); } catch (e) { bao(e.message + '.'); }
      await napMoHinh(); }); }
  else if (d.dnHuy) { try { await api('/mohinh/goi/' + d.dnHuy + '/huy', {taikhoan: (D.dn[d.dnHuy] || {}).tk || 1}); } catch (e) { /* */ } D.dn[d.dnHuy] = {}; veMoHinh(); }
  else if (d.goithu) { t.disabled = true; const t0 = Date.now();
    try { const k = await api('/mohinh/' + encodeURIComponent(d.goithu) + '/goithu', {}); bao('Gọi thử đạt: ' + (tenNguon(timNguon(d.goithu)) || k.nguon) + ' trả lời sau ' + soVN(Math.round((Date.now() - t0) / 100) / 10) + ' giây.'); }
    catch (e) { bao('Gọi thử chưa đạt: ' + e.message + '.'); } t.disabled = false; await napMoHinh(); return; }
  else if (d.chep) { try { await navigator.clipboard.writeText(d.chep); bao('Đã chép mã thiết bị.'); } catch (e) { bao('Bạn chép tay mã ' + d.chep + '.'); } }
  else if (d.chepTin) { const x = (D.tin || []).find(y => y.id === d.chepTin); if (x) { try { await navigator.clipboard.writeText(x.noidung); bao('Đã chép câu trả lời.'); } catch (e) { /* */ } } }
  else if ('tcMoi' in d) { boLuot(); D.htId = null; D.ghimMoi = null; dongMh(); D.tin = []; $('#ds-tin').innerHTML = ''; $('#tc-tieude').textContent = 'Trò chuyện mới'; S.tc = 'rong'; veDsHt(); $('#tc-o').focus(); }
  else if (d.ht) { await moHt(d.ht); return; }
  else if ('tcMau' in d) { await guiTin(t.textContent); return; }
  else if ('tcGui' in d) { await guiTin(); return; }
  else if ('luumk' in d) { await doiMatKhau(); return; }
  else if ('luu2lop' in d) { await doiMay(); return; }
  if (t.id === 'xn-nut') { $('#h-xacnhan').hidden = true; const cb = D.xnCb; D.xnCb = null; if (cb) await cb(); }
  ve();
});
document.addEventListener('input', ev => { const e = ev.target; if (e.classList.contains('o6')) { e.value = e.value.replace(/\D/g, '').slice(0, 1);
  if (e.value && e.nextElementSibling) e.nextElementSibling.focus(); } });
document.addEventListener('paste', ev => { const e = ev.target; if (!e.classList || !e.classList.contains('o6')) return;
  const so = (ev.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6); if (!so) return; ev.preventDefault();
  $$('.o6', e.parentElement).forEach((o, i) => o.value = so[i] || ''); });
document.addEventListener('keydown', ev => { const e = ev.target;
  if (e.classList && e.classList.contains('o6') && ev.key === 'Backspace' && !e.value && e.previousElementSibling) e.previousElementSibling.focus();
  if (ev.key === 'Enter' && S.g === '01') { if (S.dn === 'matkhau' || S.dn === 'sai' || S.dn === 'hethan') dangNhap();
    else { const n = $('[data-s="dn:' + S.dn + '"] [data-xacnhan]'); if (n) xacNhanMa(n); } }
  if (ev.key === 'Enter' && e.id === 'tc-o') guiTin();
  if (ev.key === 'Enter' && e.id === 'ma-claude') danMaClaude();
  if (ev.key === 'Escape') { dongHop(); dongTha(); ve(); } });
document.addEventListener('input', ev => { if (ev.target.closest && ev.target.closest('#tc-tim')) veDsHt(); });
setInterval(() => {   // phiên 30 ngày (QĐ90): báo trước 05 phút; khóa đăng nhập hết thì bật lại nút
  if (S.g !== '01' && D.hetLuc) { const con = Date.parse(D.hetLuc) - Date.now();
    if (con <= 0) { S.g = '01'; S.dn = 'hethan'; S.k = 'binhthuong'; ve(); } else if (con <= 5 * 60e3 && S.k === 'binhthuong') { S.k = 'saphethan'; ve(); } }
  if ((S.dn === 'khoa' || S.dn === 'khoatk') && D.khoaDen && Date.now() / 1000 >= D.khoaDen) { S.dn = 'matkhau'; D.khoaDen = 0; ve(); }
}, 20000);

ve();
api('/toi').then(vaoPhanMem).catch(() => { S.g = '01'; ve(); });
