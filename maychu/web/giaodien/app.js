// IGM360 giao diện: màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt, 13 Mô hình AI, 08 Trò chuyện AI (bản vẽ đã duyệt
// QĐ88, QĐ94; icon theo từ điển QĐ91; chặn đoán mật khẩu, phiên 30 ngày QĐ90).
// Cách bật tắt khối theo trạng thái (data-s) giữ như bản vẽ; số liệu lấy từ máy chủ.
'use strict';
const S = {g: '01', dn: 'matkhau', k: 'binhthuong', trang: '03', tab: 'thongso', cn: 'moinhat', xem: 'dt', thu: 0, tc: 'rong'};
const $ = (q, r = document) => r.querySelector(q), $$ = (q, r = document) => [...r.querySelectorAll(q)];
const D = {thongso: null, maTam: '', maTamDoiMay: '', xnCb: null, suaK: '', capnhat: null, hetLuc: null, khoaDen: 0,
  md: null, dn: {}, trung: {}, ht: [], htId: null, soLuc: ''};
if (window.innerWidth < 700) { S.xem = 'mb'; document.body.classList.add('dien-thoai'); }

// ---- Định dạng: số 1-9 đứng trước danh từ đếm ghi 02 chữ số; ngày dd/mm/yyyy; nghìn ngăn bằng dấu chấm
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);
const soVN = v => { const n = Number(v); if (!Number.isFinite(n)) return v;
  if (Number.isInteger(n) && n < 10) return hai(n);
  const [a, b] = String(n).split('.'); return a.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (b ? ',' + b : ''); };
const ngay = iso => { if (!iso) return ''; const [y, m, d] = iso.slice(0, 10).split('-'); return d + '/' + m + '/' + y; };
const gio = iso => iso ? iso.slice(11, 16) : '';
const homNay = () => new Date(Date.now() + 7 * 3600e3).toISOString().slice(0, 10);
const luc = iso => !iso ? '' : (iso.slice(0, 10) === homNay() ? gio(iso) + '\u00a0hôm\u00a0nay' : ngay(iso) + ' · ' + gio(iso));
const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
// Không tách cụm từ khi xuống dòng (chữ do máy chủ gửi): nối các cụm thường gặp bằng dấu cách không ngắt
// U4 (S1, S3): cụm "mục + tên màn" dài hơn đặt trước để nối trước khi cụm ngắn hơn được nối.
const CUM = ['Việc nền', 'mục Chờ duyệt', 'mục Két khoá', 'mục Bộ mã chung', 'mục Nguồn dữ liệu', 'mục Mô hình AI', 'giai đoạn', 'giá trị', 'ứng dụng', 'gấp đôi', 'tài khoản', 'mật khẩu', 'phần mềm', 'sao lưu', 'trò chuyện',
  'đăng nhập', 'cập nhật', 'khoá API', 'Google Drive', 'tỷ giá', 'hạn mức', 'nguồn AI', 'việc AI', 'thông số', 'mỗi ngày',
  'bản mới', 'máy chủ', 'Chờ duyệt', 'Két khoá', 'đề xuất', 'chờ anh', 'tự áp dụng', 'thao tác', 'hằng ngày', 'quy đổi',
  'tham khảo', 'ưu tiên', 'gì mới', 'Cài đặt', 'Thông số', 'dự phòng', 'cài máy',
  'Mở trang', 'TikTok Shop', 'mã sàn'];   // N12, T1
// Số luôn đi liền chữ đứng sau (04 dòng, 1.240 dòng); "tài khoản 01", "ưu tiên 2", "bản 0.5.0", "02 lớp" không tách.
const cum = s => { let r = esc(s).replace(/(?<![\p{L}\d])(\d+(?:[.,]\d+)*) (?=\p{L})/gu, '$1&nbsp;');
  CUM.forEach(c => { r = r.split(c).join(c.replace(/ /g, '&nbsp;')); });
  return r.replace(/(khoản|tiên|[Bb]ản|lớp) (\d)/g, '$1&nbsp;$2').replace(/ (›|·) /g, '&nbsp;$1 '); };
const cau = s => /[.!?…]$/.test(String(s).trim()) ? s : s + '.';   // câu báo lỗi luôn có dấu chấm cuối (N12)

// ---- Gọi máy chủ
async function api(duong, than) {
  let r;
  try {
    r = await fetch('/api' + duong, {method: than === undefined ? 'GET' : 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-IGM360': '1'}, body: than === undefined ? undefined : JSON.stringify(than)});
  } catch (e) { S.k = 'matketnoi'; ve(); throw e; }
  if (S.k === 'matketnoi') { S.k = 'binhthuong'; }
  const d = await r.json().catch(() => ({}));
  if (r.status === 401 && S.g !== '01') { S.g = '01'; S.dn = 'hethan'; ve(); }
  if (!r.ok) { const ct = d.detail; const e = new Error(typeof ct === 'string' ? ct : (ct && ct.loi) || 'Có lỗi');
    e.o = ct && ct.o; e.status = r.status; e.ct = ct; throw e; }
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
  $('#tieude-tren').innerHTML = (ICO[S.trang] || '') + '<b class="t16 nw">' + (TEN[S.trang] || '') + '</b>';
  $('[data-dangnhap]').disabled = S.dn === 'khoa' || S.dn === 'khoatk';
}
function dongTha() { $$('.tha').forEach(e => e.hidden = true); }
function dongHop() { $$('.lop').forEach(e => e.hidden = true); }
function mo(id) { dongTha(); $('#' + id).hidden = false; }
function bao(t) { const e = $('#tb-msg'); e.textContent = t; e.hidden = false; clearTimeout(bao.h); bao.h = setTimeout(() => e.hidden = true, 3200); }
function xacnhan(tieu, chu, nut, cb) { $('#h-xacnhan [data-tieu]').textContent = tieu; $('#xn-chu').innerHTML = chu;
  $('#xn-nut').textContent = nut; D.xnCb = cb; mo('h-xacnhan'); }
const ma6 = goc => $$('.o6', goc).map(i => i.value).join('');
const xoa6 = goc => $$('.o6', goc).forEach(i => i.value = '');

// ---- Màn 01
function hienLoiDn(t, con) { $('#dn-loi').textContent = t; $('#dn-con').textContent = con == null ? '' : hai(con);
  $('#dn-con-cau').hidden = con == null; S.dn = 'sai'; ve(); }
const gioPhut = sec => { const d = new Date(sec * 1000 + 7 * 3600e3).toISOString(); return d.slice(11, 16) + (d.slice(0, 10) === homNay() ? '' : ' ngày ' + ngay(d)); };
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
  if (!ten || !mk) { hienLoiDn('Anh nhập tên đăng nhập và mật khẩu.', null); return; }
  try {
    const kq = await api('/dangnhap', {ten, matkhau: mk});
    D.maTam = kq.ma_tam; $('#mk').value = '';
    if (kq.buoc === 'bat2lop') { $('#qr-2lop').innerHTML = kq.qr_svg; S.dn = 'batdau2lop'; } else S.dn = 'ma2lop';
    ve(); const o = $('[data-s="dn:' + S.dn + '"] .o6'); if (o) o.focus();
  } catch (e) { if (e.status) loiDangNhap(e, false); }
}
async function xacNhanMa(nut) {
  const goc = nut.closest('[data-s]'), ma = ma6(goc);
  if (ma.length !== 6) { bao('Anh nhập đủ 06 số.'); return; }
  try {
    await api('/dangnhap/ma2lop', {ma_tam: D.maTam, ma});
    if (nut.dataset.xacnhan === 'bat') bao('Đã bật đăng nhập 02 lớp.');
    xoa6(goc); $('#qr-2lop').innerHTML = ''; await vaoPhanMem();
  } catch (e) { xoa6(goc); if (e.status === 429) { hienKhoa(e.ct); return; }
    if (/hết hạn/.test(e.message)) { S.dn = 'hethan'; ve(); bao(e.message); return; } loiDangNhap(e, true); }
}

// ---- Màn 02
async function vaoPhanMem() {
  const toi = await api('/toi');
  const chu = (toi.ten || toi.ten_dangnhap || '').trim();
  $('#tk-chu').textContent = chu.slice(0, 1).toUpperCase(); $('#tk-ten').textContent = chu;
  D.hetLuc = toi.het_luc; S.g = '02'; S.dn = 'matkhau'; ve(); demSo();
  if (S.trang === '09') napTab();
}
// ---- Chuông thông báo bước 1 (QĐ165, bản vẽ Z7b): số = dòng Mới (sau mốc đọc); nhóm Mới rồi Đã xem, còn mở
const MAU_TB = {do: ['do-n', '#E22E28'], xem: ['xem-n', '#C97A00'], tin: ['tin-n', '#1456F0']};
const lucTb = iso => { if (!iso) return ''; const h = homNay(), q = new Date(Date.parse(h) - 86400e3).toISOString().slice(0, 10), d = iso.slice(0, 10);
  return d === h ? gio(iso) : d === q ? 'Hôm qua ' + gio(iso) : d.slice(8, 10) + '/' + d.slice(5, 7); };
const icoTb = x => (ICON[x.icon] || ICON['circle-alert']).replace(/width="\d+"/, 'width="16"').replace(/height="\d+"/, 'height="16"')
  .replace(/stroke="#[0-9A-Fa-f]{6}"/, 'stroke="' + MAU_TB[x.muc][1] + '"');
const dongTb = x => '<button class="tha-muc tb-dong" data-di="' + esc(x.di) + '"' + (x.cuon ? ' data-cuon="' + esc(x.cuon) + '"' : '') + '><span class="ico-tron nho '
  + MAU_TB[x.muc][0] + '">' + icoTb(x) + '</span><span class="f1 trai"><span class="b6 t13 khoi">' + esc(x.chu) + '</span><span class="t12 phu">'
  + esc(lucTb(x.luc)) + ' · ' + esc(x.noi) + '</span></span></button>';
function veChuong(d) {
  const ds = d.thongbao || [], moi = ds.filter(x => x.moi), cu = ds.filter(x => !x.moi);
  const c = $('[data-chuong] .cham'); c.textContent = d.so_moi ? soVN(d.so_moi) : ''; c.hidden = !d.so_moi;
  $('#tb-dochet').hidden = !moi.length; $('#tb-dadoc').hidden = !!moi.length || !ds.length;
  $('#chuong-ds').innerHTML = !ds.length ? '<div class="tb-rong"><span class="ico-tron">' + ICON.bell.replace(/width="\d+"/, 'width="20"').replace(/height="\d+"/, 'height="20"')
      + '</span><span class="t13 phu">Không có thông báo nào còn mở.</span></div>'
    : (moi.length ? '<div class="tb-nhom2">Mới · ' + soVN(moi.length) + '</div>' + moi.map(dongTb).join('') : '')
      + (cu.length ? '<div class="tb-nhom2">Đã xem, còn mở · ' + soVN(cu.length) + '</div>' + cu.map(dongTb).join('') : '');
}
// Tự cập nhật số mỗi 60 giây khi phần mềm đang mở (hỏi lại máy chủ, 0 thư viện)
setInterval(() => { if (S.g !== '01' && document.visibilityState === 'visible') lamMoi13(), demSo(); }, 60e3);   // 01 vòng 60 giây
// QĐ192 (0.7.7): màn Mô hình AI tự làm mới số hạn mức mỗi 60 giây; không làm mới khi anh đang đăng nhập dở, đang mở hộp,
// hoặc đang gõ trong màn (để không mất chữ đang gõ)
function lamMoi13() {
  if (S.trang !== '13' || !D.md) return;
  if (Object.values(D.dn || {}).some(x => x && x.url)) return;
  if (Object.values(D.mdh || {}).some(x => x)) return;   // 0.7.8: đang lấy mã, dán mã dài hạn
  if ($$('.lop').some(e => !e.hidden)) return;
  const a = document.activeElement; if (a && a.closest && a.closest('#p13') && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) return;
  napMoHinh();
}
async function demSo(mo) {
  try {
    const d = await api('/demso' + (mo ? '?mo=1' : ''));   // QĐ174: mở chuông thì dò bản mới nếu kết quả đã cũ
    $$('[data-trang="05"] .bao').forEach(b => { b.textContent = d.cuacho ? soVN(d.cuacho) : ''; b.hidden = !d.cuacho; });
    $$('[data-trang="10"] .bao, [data-them] .bao').forEach(g => { g.textContent = d.ket_ai ? soVN(d.ket_ai) : ''; g.hidden = !d.ket_ai; });
    D.soLuc = new Date(Date.now() + 7 * 3600e3).toISOString().slice(11, 16);
    veChuong(d);
  } catch (e) { /* mất kết nối đã hiện dải báo */ }
}

// ---- Màn 09 ngăn Thông số
const NHOM_ICO = {'Tài chính': 'nhom0', 'Máy chủ và bảo mật': 'nhom1', 'AI': 'nhom2', 'Báo cáo, dữ liệu': 'nhom3'};
const giaiDoanSau = t => /^Từ GĐ \d/.test(t.khong_sua || '');
const hienGt = t => t.giatri_chu === null || t.giatri_chu === '' ? null
  : ((t.kieu === 'so' ? soVN(t.giatri_chu) : t.giatri_chu) + (t.donvi && t.kieu === 'so' ? ' ' + t.donvi : ''));
function veThongSo() {
  const d = D.thongso, nhom = {};
  d.thongso.forEach(t => (nhom[t.nhom] = nhom[t.nhom] || []).push(t));
  $('#ts-dem').innerHTML = hai(d.da_dat) + '/' + hai(d.tong) + '<small>đã đặt</small>';
  const vong = $('#ts-vong circle:last-child'); if (vong) vong.setAttribute('stroke-dasharray', (241.9 * d.da_dat / d.tong).toFixed(1) + ' 241.9');
  const chua = d.tong - d.da_dat; $('#ts-chua').textContent = chua ? hai(chua) + ' thông số anh chưa đặt' : 'Anh đã đặt đủ thông số';
  $('#ds-thongso').innerHTML = Object.entries(nhom).map(([ten, tat]) => { const ds = tat.filter(t => !giaiDoanSau(t)), sau = tat.filter(giaiDoanSau);
    return '<div class="the nhom-ts"><div class="tieu">'
    + (ICON[NHOM_ICO[ten]] || '') + '<span class="b7">' + esc(ten) + '</span><span class="phu t12 ml">' + hai(ds.length) + ' thông số</span></div>'
    + ds.map(t => { const gt = hienGt(t);
      return '<div class="ts' + (gt ? '' : ' chua') + '"><div class="ts-ten">' + esc(t.nhan)
        + (gt || !t.khi_trong ? '' : '<div class="t12 xem-chu">' + cum(t.khi_trong) + '</div>') + '</div><div class="ts-gt">'
        + (gt ? '<span class="b7 so">' + esc(gt) + '</span><span class="t12 phu">Từ ' + ngay(t.hieuluc_tu) + ' · ' + (t.nguoi_dat === 'hethong' ? 'Mặc định' : 'Chủ') + '</span>'
             : '<span class="ttag xem">' + (t.ten === 'nhip_lay_dulieu' ? 'Chưa đặt loại nào' : 'Chưa đặt') + '</span>' + (t.ten === 'nhip_lay_dulieu' ? '' : '<span class="t12 phu">\u00a0</span>'))
        + '</div>' + (t.ten === 'nhip_lay_dulieu' ? '<button class="btn-chu" data-trang="11">' + ICON.sangtrang + 'Đặt ở Nguồn dữ liệu</button>'
          : t.khong_sua ? '<span class="t12 phu nw khoa-ts">' + ICON.khoats + esc(t.khong_sua) + '</span>'
          : '<button class="btn-chu" data-sua="' + t.ten + '">' + ICON.pencil + 'Sửa</button>') + '</div>'; }).join('')
    + sau.map(t => '<div class="dong t12 phu">' + ICON.khoats + '<span>' + cum(t.khong_sua + ': ' + t.nhan + '. ' + (t.khi_trong || '').replace(/^GĐ 1: /, 'GĐ 1 ')) + '</span></div>').join('')
    + '</div>'; }).join('');
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
  const mai = new Date(Date.now() + 31 * 3600e3).toISOString().slice(0, 10);
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
  if (!m) { bao('Anh gõ ngày áp dụng theo dạng ngày/tháng/năm, ví dụ 22/11/2026.'); return; }
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
  if (ma.length !== 6) { bao('Anh nhập đủ 06 số.'); return; }
  try {
    if (!D.maTamDoiMay) {
      const kq = await api('/2lop/doimay/batdau', {ma}); D.maTamDoiMay = kq.ma_tam; xoa6(hop);
      $('.hop-than .t13', hop).innerHTML = '<div class="qr-hang"><div class="qr">' + kq.qr_svg + '</div><div class="t13 phu">Mở ứng dụng xác thực trên máy mới, quét mã này, rồi nhập 06 số máy mới đang hiện.</div></div>';
      $('[data-luu2lop]', hop).textContent = 'Xác nhận máy mới';
    } else {
      await api('/2lop/doimay/xacnhan', {ma_tam: D.maTamDoiMay, ma}); dongHop(); datLaiDoiMay(); bao('Đã đổi máy nhận mã 02 lớp.');
    }
  } catch (e) { xoa6(hop); bao(e.message + '.'); }
}
function datLaiDoiMay() { D.maTamDoiMay = ''; const hop = $('#h-2lop'); xoa6(hop);
  $('.hop-than .t13', hop).textContent = 'Nhập mã 06 số trên máy cũ để xác nhận, rồi quét mã QR mới bằng máy mới.';
  $('[data-luu2lop]', hop).textContent = 'Tiếp tục'; }

// ---- Màn 09 ngăn Cập nhật
function veCapNhat(d) {
  D.capnhat = d;
  if (S.cn !== 'hong') S.cn = d.co_ban_moi ? 'coban' : 'moinhat';
  $('#ban-hien').textContent = d.ban_dang; $$('.cn-dang').forEach(e => e.textContent = d.ban_dang);
  $$('.cn-moi').forEach(e => e.textContent = d.ban_moi || '');
  $('#cn-luc').textContent = d.luc_kiem ? luc(d.luc_kiem) : 'chưa kiểm';
  if (d.nhip_phut) $('#cn-nhip').innerHTML = hai(d.nhip_phut) + '&nbsp;phút';   // QĐ174: nhịp lấy từ máy chủ (01 chỗ)
  $('#cn-loi').textContent = d.loi ? ' · ' + d.loi + '.' : '';   // Y17 (d): lỗi kiểm bản mới hiện cố định cạnh giờ kiểm
  const moi = d.thaydoi.find(m => m.ban === d.ban_moi) || d.thaydoi[0] || {dong: []};
  $('#cn-thaydoi').innerHTML = moi.dong.slice(0, 5).map(x => '<div class="dong t13">' + ICON.check + '<span>' + cum(x) + '</span></div>').join('');
  const tomTat = ban => (d.tomtat || {})[ban] || (ban === d.ban_dang ? 'Bản đang dùng' : 'Bản đã dùng');   // dòng "Tóm tắt:" ở THAYDOI.md (N07)
  const cot = 'grid-template-columns:120px 1fr 160px';
  $('#ls-capnhat').innerHTML = d.lichsu.map(x => '<div class="hang" style="' + cot + '"><b class="so">' + esc(x.ban)
    + '</b><span data-l="Nội dung">' + cum(tomTat(x.ban)) + '</span><span data-l="Ngày cài" class="so">' + ngay(x.luc) + '</span></div>').join('');
  $('.tab[data-tab="capnhat"] .cham-xanh').hidden = !d.co_ban_moi;
  ve();
}
function moCapNhat() {
  const viec = D.capnhat.so_viec_ai;
  $('#cn-viec').innerHTML = viec ? 'Đang có <b>' + hai(viec) + '</b> việc AI chạy.' : 'Không có việc AI nào đang chạy.';
  mo('h-capnhat');
}
async function capNhat(cheDo) {
  dongHop(); const cu = D.capnhat.ban_dang;
  try { const kq = await api('/capnhat', {che_do: cheDo});
    if (kq.cho) { bao('Đã hẹn: chờ việc AI đang chạy xong (tối đa 30 phút) rồi tự cập nhật.'); return; } }
  catch (e) { if (e.status) { S.cn = 'hong'; $('#cn-lydo').textContent = 'Lý do: ' + e.message + '.'; ve(); } return; }
  S.cn = 'dangcn'; ve(); const het = Date.now() + 5 * 60e3;
  const cho = async () => {
    try { const r = await fetch('/suckhoe', {cache: 'no-store'}); const k = await r.json();
      if (k.phienban && k.phienban !== cu) { location.reload(); return; } } catch (e) { /* đang khởi động lại */ }
    if (Date.now() < het) setTimeout(cho, 5000);
    else { S.cn = 'hong'; $('#cn-lydo').textContent = 'Lý do: sau 05 phút máy chủ vẫn chạy bản cũ. Phần mềm vẫn chạy bình thường bằng bản cũ.'; ve(); }
  };
  setTimeout(cho, 5000);
}

// ---- Màn 13 Mô hình AI: thẻ gói Claude, gói ChatGPT, khoá API; bảng mô hình mặc định
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
const canhTk = ten => '<div class="canh-tk">' + icoMau(ICON['circle-alert'], '#8F5F00', 14) + '<span>Lưu ý: dùng nhiều tài khoản ' + ten
  + ' trên cùng phần mềm, hãng có thể khoá tài&nbsp;khoản.</span></div>';
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
  + cu + '%;background:' + (p >= 90 ? '#E22E28' : '#1456F0') + '"></div></div><b class="t12 so">' + (p == null ? 'chưa&nbsp;đo' : Math.round(p) + '%') + '</b></div>'; }
// Y36b, Y36c N4: "Opus của tài khoản 1 hết hạn mức đến 20:45" (khác ngày: "đến 20:45 ngày 26/11"); dùng chung màn 13 và khung chat
const denLuc = iso => !iso ? '' : gio(iso) + (String(iso).slice(0, 10) !== homNay() ? ' ngày ' + iso.slice(8, 10) + '/' + iso.slice(5, 7) : '');
const tenHet = (m, n) => m.ma ? tenMh(m.ma, n && n.id, n, true) : m.ten_khung || (m.bao ? tenMh(m.bao, n && n.id, n, true) : '');
const chuHetMh = (m, n, tk) => chuHoa(tenHet(m, n) || 'mô hình mặc định') + ' của tài khoản ' + tk + ' hết hạn mức' + (m.den ? ' đến ' + denLuc(m.den) : '');
// N5: cả tài khoản đang tạm nghỉ thì ghi lý do tài khoản (như dòng vàng P3b); chỉ 01 mô hình hết riêng thì ghi tên mô hình
const tieuHetMh = (n, tk) => n.tk_nghi_den ? ' title="' + esc('Tài khoản ' + tk + ' đang tạm nghỉ đến ' + denLuc(n.tk_nghi_den)) + '"'
  : !(n.het_mh || []).length ? '' : ' title="' + esc(n.het_mh.map(m => chuHetMh(m, n, tk)).join('; ')) + '"';
// 0.7.8 (QĐ198, QĐ200): mã dài hạn gói Claude. Tên chỉ ở 01 chỗ (CPO trình anh chốt tên); không bao giờ hiện mã,
// chỉ 04 ký tự cuối. Màu Cảnh báo trong 14 ngày cuối do máy chủ tính lúc hỏi (`vang`), không lưu.
const CHU_MDH = 'Mã dài hạn';
D.mdh = {};   // {tk: {kieu: 'lay' | 'dan', url, loi}}: khung lấy mã, dán mã đang mở
function theMd(x) {
  const md = x.ma_daihan, k = D.mdh[x.taikhoan], tk = x.taikhoan;
  if (!md && !x.da_noi && !k) return '';
  let h = '<div class="md-dong' + (md && (md.het || md.vang) ? ' md-vang' : '') + '">' + icoMau(ICON['key-round'], md && (md.het || md.vang) ? '#8F5F00' : '#646A73', 14);
  if (md) h += '<span class="f1 t12">' + CHU_MDH + ' ••••' + esc(md.kytu_cuoi || '') + (md.het ? ' · đã hết&nbsp;hạn, lấy mã&nbsp;mới'
    : ' · hết hạn ' + esc(ngay(md.han)) + ' · còn ' + hai(md.con_ngay) + '&nbsp;ngày') + '</span>'
    + '<button class="btn-chu" data-md-lay="' + tk + '">Lấy mã&nbsp;mới</button><button class="btn-chu" data-md-dan="' + tk + '">Dán mã</button>'
    + '<button class="btn-chu" data-md-ngat="' + tk + '">Ngắt</button>';
  else h += '<span class="f1 t12 phu">Đăng nhập kiểu cũ, có thể hết hạn giữa chừng</span><button class="btn-chu" data-md-lay="' + tk + '">Chuyển sang '
    + CHU_MDH.toLowerCase().replace(/ /g, '&nbsp;') + '</button><button class="btn-chu" data-md-dan="' + tk + '">Dán mã</button>';
  h += '</div>';
  if (k) {
    h += '<div class="dangnhap"><div class="b6 t13">' + (k.kieu === 'lay' ? 'Lấy ' : 'Dán ') + CHU_MDH.toLowerCase() + ' · tài khoản ' + tk + '</div>';
    if (k.kieu === 'lay') h += '<div class="buoc-dn"><span class="so-b">1</span><span class="f1">Mở trang, đăng nhập bằng tài&nbsp;khoản&nbsp;Claude của anh.</span></div>'
      + '<div class="dong lk"><span class="t12 phu f1 cat">' + esc((k.url || '').replace(/^https?:\/\//, '')) + '</span><a class="btn btn-phu nho" href="' + esc(k.url || '') + '" target="_blank" rel="noopener noreferrer">' + ICON['external-link'] + 'Mở trang</a></div>'
      + '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">Trang sẽ hiện 01 mã. Chép mã, dán vào ô dưới.</span></div>'
      + '<div class="dong"><div class="o-nhap f1' + (k.loi ? ' loi' : '') + '">' + ICON.hash + '<input id="md-ma-web" placeholder="Dán mã ở đây" autocomplete="off"></div><button class="btn btn-chinh" data-md-gui="' + tk + '">Xác nhận</button></div>';
    else h += '<div class="t12 phu">Mã làm ở nơi khác bằng lệnh claude setup-token. Phần mềm cất mã đã mã hoá ở Két&nbsp;khoá, không hiện lại.</div>'
      + '<div class="dong"><div class="o-nhap f1' + (k.loi ? ' loi' : '') + '">' + ICON['key-round'] + '<input id="md-ma-dan" type="password" placeholder="sk-ant-oat01-…" autocomplete="off"></div><button class="btn btn-chinh" data-md-luu="' + tk + '">Lưu</button></div>';
    if (k.loi) h += '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + cum(cau(k.loi)) + '</span></div>';
    h += '<button class="btn-chu" data-md-huy="' + tk + '">Huỷ</button></div>';
  }
  return h;
}
async function mdXong(tk, kq) { D.mdh[tk] = null;
  bao(kq.goi_thu ? 'Đã lưu ' + CHU_MDH.toLowerCase() + ' cho tài khoản ' + tk + ', hết hạn ' + ngay(kq.han) + '.'
    : 'Đã lưu ' + CHU_MDH.toLowerCase() + ' nhưng gọi thử chưa được: ' + (kq.loi_goi_thu || 'chưa rõ lý do') + '.');
  await napMoHinh(); }
function theGoi(g, ds, nguon, uu) {
  const dn = D.dn[g] || {}, ten = GOI_NGAN[g].replace('Gói ', '');
  const coTk = ds.some(x => x.da_noi), coDong = x => nguon.some(y => y.ma === x.ma && y.trangthai === 'dung');
  // QĐ164 (Z6-TK): mới cài hoặc đã gỡ hết thì thẻ hiện 01 dòng "Chưa có tài khoản" (N10)
  const rong = !ds.length || (ds.length === 1 && !ds[0].da_noi && !ds[0].khong_ro && !coDong(ds[0]));
  let h = '<div class="the o-goi"><div class="dong">' + logoGoi(g) + '<div class="f1"><div class="t16 b7">' + esc(GOI_TEN[g]) + '</div><div class="t12 phu">Phí cố định tháng'
    + (uu ? ' · <span class="nw">ưu&nbsp;tiên&nbsp;' + uu + '</span>' : '') + '</div></div></div>';
  if (rong && !dn.url) h += '<div class="tk-dong"><span class="anh-dd mini xam">1</span><div class="f1"><b>Chưa có tài&nbsp;khoản</b><div class="t12 phu">'
    + (g === 'claude' ? 'Đăng nhập để dùng làm nguồn ưu&nbsp;tiên&nbsp;' + uu : 'Đăng nhập để dùng làm nguồn dự&nbsp;phòng') + '</div></div><span class="nhan n-xem"><i></i>Chưa đăng nhập</span></div>';
  else ds.forEach(x => { const n = nguon.find(y => y.ma === x.ma) || {};
    const go = (x.da_noi || coDong(x)) && !(dn.url && dn.tk === x.taikhoan);
    h += '<div class="tk-dong"' + tieuHetMh(n, x.taikhoan) + '><span class="anh-dd mini' + (x.da_noi ? '' : ' xam') + '">' + x.taikhoan + '</span><div class="f1"><b>' + tenTk(x) + '</b>'
      + (x.da_noi && x.mota_goi ? '<div class="t12 phu">' + esc(x.mota_goi) + '</div>' : '') + '<div class="t12 phu">'
      + (x.da_noi ? dnLuc(x) : x.khong_ro ? 'Chưa kiểm được trạng thái' : 'Chưa đăng nhập') + '</div>'
      + (go ? '<button class="btn-chu go-tk" data-go-goi="' + g + '" data-go-tk="' + x.taikhoan + '">' + ICON['user-minus'] + 'Gỡ tài&nbsp;khoản</button>' : '') + '</div>'
      + (x.da_noi ? '<span class="nhan n-dat"><i></i>Đã kết nối</span>' : '<span class="nhan n-xem"><i></i>Chưa đăng nhập</span>') + '</div>';
    if (g === 'claude') h += theMd(x);   // 0.7.8
    if (x.da_noi) h += '<div class="cot-doc g8">' + thanhHm('Cửa sổ 05 giờ', n.tyle_5gio, n.ma + '|5') + thanhHm('Tuần này', n.tyle_tuan, n.ma + '|t')
      + (n.da_datlai_luc   // Z12 (3): qua giờ đặt lại
        ? '<div class="t12 phu" title="Qua giờ đặt lại: khung 05 giờ mới bắt đầu, số dùng về 0%">Đã đặt lại lúc ' + esc(gio(n.da_datlai_luc)) + '&nbsp;· số mới có sau lượt gọi AI kế&nbsp;tiếp</div>'
        : '<div class="t12 phu" title="Số đo sau mỗi lượt gọi AI; màn này tự làm mới 01 phút/lần">' + (n.do_luc ? 'Đo lúc ' + esc(luc(n.do_luc))
          + (n.datlai_5gio_luc ? '&nbsp;· đặt lại 05&nbsp;giờ lúc ' + esc(gio(n.datlai_5gio_luc)) : '') : 'Chưa đo: số hiện sau lần gọi AI đầu tiên') + '</div>') + '</div>'; });
  // QĐ164 ý 1 (Z6-TK): đăng nhập trùng thì không tạo ô, dải xanh dưới ô đang có; số là số của ô đang giữ tài khoản đó
  if (D.trung[g]) h += '<div class="bao-xanh t13">' + ICON['user-round'] + '<span>Tài khoản ' + ten + ' này đã kết&nbsp;nối ở Tài&nbsp;khoản&nbsp;' + D.trung[g] + '. Phần mềm không tạo ô&nbsp;mới.</span></div>';
  if (dn.url) {
    h += '<div class="dangnhap"><div class="b6 t13">Đăng nhập tài khoản ' + dn.tk + '</div>' + (dn.tk >= 2 ? canhTk(ten) : '')
      + '<div class="buoc-dn"><span class="so-b">1</span><span class="f1">' + (g === 'claude' ? 'Mở trang đăng nhập, đăng nhập bằng tài&nbsp;khoản&nbsp;Claude của anh.' : 'Mở trang xác nhận, đăng nhập ChatGPT.') + '</span></div>'
      + '<div class="dong lk"><span class="t12 phu f1 cat">' + esc(dn.url.replace(/^https?:\/\//, '')) + '</span><a class="btn btn-phu nho" href="' + esc(dn.url) + '" target="_blank" rel="noopener noreferrer">' + ICON['external-link'] + 'Mở trang</a></div>';
    if (g === 'claude') h += '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">Trang sẽ hiện 01 mã. Chép mã, dán vào ô dưới.</span></div>'
      + '<div class="dong"><div class="o-nhap f1' + (dn.loi ? ' loi' : '') + '">' + ICON.hash + '<input id="ma-claude" placeholder="Dán mã ở đây" autocomplete="off"></div><button class="btn btn-chinh" data-mc-xacnhan>Xác nhận</button></div>'
      + (dn.loi ? '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + cum(cau(dn.loi)) + '</span></div>' : '');
    else h += '<div class="buoc-dn"><span class="so-b">2</span><span class="f1">Gõ mã thiết bị này vào trang:</span></div><div class="ma-tb"><b>' + esc(dn.ma) + '</b><button class="btn-chu" data-chep="' + esc(dn.ma) + '">' + ICON.copy + 'Chép</button></div>'
      + '<div class="dong t13 phu">' + ICON.loader + 'Đang chờ anh xác nhận trên web. Xong là thẻ tự chuyển, không cần dán mã.</div>' + (dn.loi ? '<div class="loi-o">' + ICON['circle-alert'] + '<span>' + cum(cau(dn.loi)) + '</span></div>' : '');
    h += '<button class="btn-chu" data-dn-huy="' + g + '">Huỷ đăng nhập</button></div>';
  }
  const chua = rong ? {taikhoan: ds.length ? ds[0].taikhoan : oTrong(ds)} : ds.find(x => !x.da_noi);
  const them = !rong && ds.length < 2 && ds.filter(x => x.da_noi).length === 1;   // Z6-TK: có 01 tài khoản thì hiện, đủ 02 thì ẩn
  h += '<div class="dong chan-goi">' + (chua && !dn.url ? '<button class="btn btn-chinh" data-dn-goi="' + g + '" data-dn-tk="' + chua.taikhoan + '">' + ICON['log-in'] + 'Đăng nhập</button>' : '')
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
  if (!so) { const c = ds.find(x => !x.da_noi); await batDauDn(g, c ? c.taikhoan : oTrong(ds)); return; }
  const o = oTrong(ds);
  if (so >= 2 || !o) { const c = ds.find(x => !x.da_noi); if (c && so < 2) { await batDauDn(g, c.taikhoan); return; }
    bao(tenNguon({goi: g}) + ' đã đủ 02 tài khoản. Gỡ 01 tài khoản rồi mới thêm.'); return; }
  xacnhan('Thêm tài khoản ' + ten + ' khác?', 'Dùng khi anh có 02 gói riêng, mỗi gói 01 tài khoản ' + ten + ' khác&nbsp;nhau.<br><br>Đăng nhập lại tài khoản đang kết nối thì phần mềm báo trùng, không tạo ô mới.' + canhTk(ten),
    'Tiếp tục', () => batDauDn(g, o));
}
function veMoHinh() {
  const d = D.md; $('#md-songsong').textContent = hai(Number(d.so_viec_ai_songsong || 3));
  const khoa = d.nguon.filter(n => n.loai === 'khoa_api');
  // N10 b, QĐ160: số ưu tiên = thứ tự dùng thật (máy chủ đã xếp gói trước Khoá API). Gói chưa đăng nhập (chưa có dòng
  // G06) hiện số sẽ nhận: ngay sau các gói đã có, vẫn trước mọi Khoá API.
  let k = 0; const uu = {};
  d.nguon.filter(n => n.loai !== 'khoa_api' && n.trangthai === 'dung').forEach(n => { ++k; if (n.goi && !(n.goi in uu)) uu[n.goi] = k; });
  ['claude', 'chatgpt'].forEach(g => { if (!(g in uu)) uu[g] = ++k; });
  $('#ds-nguonai').innerHTML = theGoi('claude', d.goi.claude, d.nguon, uu.claude) + theGoi('chatgpt', d.goi.chatgpt, d.nguon, uu.chatgpt)
    + '<div class="the o-goi"><div class="dong"><div class="ico-tron">' + ICON['key-round'] + '</div><div class="f1"><div class="t16 b7">Khoá API</div><div class="t12 phu">Phí theo lượt</div></div></div>'
    + (khoa.length ? khoa.map((n, i) => '<div class="tk-dong"><span class="anh-dd mini">K</span><div class="f1"><b>' + esc(tenNguon(n)) + '</b><div class="t12 phu">Cất ở mục&nbsp;Két&nbsp;khoá</div><div class="t12 phu">Ưu&nbsp;tiên&nbsp;' + (k + i + 1) + '</div></div>'
        + (n.tran_tien_thang ? '<span class="nhan n-dat"><i></i>Đang dùng</span>' : '<span class="ttag xem">Chưa đặt hạn mức</span>') + '</div>').join('')
      : '<div class="t13 phu">Chưa có khoá API. Chưa có khoá thì phần mềm chỉ dùng gói.</div><div class="t12 xem-chu">Thêm khoá ở mục Két khoá (có ở bản sau).</div>')
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
      const iVn = k === 'viecnen_chung' ? ' <button class="nut-ico nho" data-ivn title="' + CHU_VN + '">' + icoMau(ICON['info'], '#646A73', 14) + '</button>' : '';
      return '<div class="hang" style="' + cot + '"><b class="rong-mb' + (iVn ? ' ten-i' : '') + '">' + (iVn ? '<span>' + cum(v) + '</span>' : esc(v)) + iVn + '</b><span data-l="Mô hình"' + (x && x.m ? ' title="Bản cụ thể: ' + esc(x.m.ma) + '"'
        : mat ? ' title="Nguồn đã đặt không còn tài khoản nào: dùng nguồn ưu tiên 1"' : '') + '>'
        + (x && x.m ? esc(tenMh(x.m.ma, x.g.nhom, x.g)) : 'Mặc định của nguồn') + '</span><span data-l="Nguồn">'
        + (x ? cum(tenNguon(x.g)) : (dau ? cum(tenNguon(dau)) : 'Chưa có nguồn')) + '</span><button class="btn-chu" data-doimd="' + k + '">' + ICON.pencil + 'Đổi</button></div>'; }).join('');
}
async function napMoHinh() { try { D.md = await api('/mohinh'); await napDsMh(); veMoHinh(); } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); } }
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
  if (!ma.trim()) { bao('Anh dán mã trang Claude hiện ra.'); return; }
  try { await api('/mohinh/goi/claude/ma', {taikhoan: dn.tk, ma}); D.dn.claude = {}; bao('Đã kết nối ' + tenNguon({goi: 'claude'}) + ', tài khoản ' + dn.tk + '.'); await napMoHinh(); }
  catch (e) { if (e.status === 409) { D.dn.claude = {}; D.trung.claude = (e.ct || {}).trung_voi; await napMoHinh(); return; } dn.loi = e.message; veMoHinh(); }
}

// ---- Ô chọn mô hình màn 08 + hộp "Đổi" màn 13 (QĐ178–QĐ183, PTD-08, bản vẽ Z10, Z10b): 01 danh sách G08 dùng chung
const MH = {noi: null, tim: '', mo: null, dich: null};   // noi: 'chat' (bảng xổ màn 08) | 'md' (hộp màn 13); dich: loại việc
D.hong = {};   // {mã cuộc: {het, dung, nguon_id}}: mô hình ghim không dùng được ở lượt gần nhất (nút vàng tới khi dùng lại được)
// Y31b S5: đổi màu nét mọi dạng mã màu, kể cả "#fff" của icon dấu cộng
const icoMau = (svg, mau, co) => svg.replace(/stroke="[^"]*"/, 'stroke="' + mau + '"').replace(/width="\d+"/, 'width="' + co + '"').replace(/height="\d+"/, 'height="' + co + '"');
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
// 0.7.6 (QĐ187, PTD-08): mô hình nhận diện bằng khoá "loại nguồn|mã mô hình" máy chủ cấp (`m.khoa`); giao diện không tự
// ghép. Ghim dạng cũ (id G08 của 0.7.5, nằm trong `m.ids`) tra ra khoá rồi lưu lại.
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
  if (tl.ghim_khoa && tl.ghim_khoa !== gh) luuGhim(k, tl.ghim_khoa);   // máy chủ đổi ghim dạng cũ sang khoá
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
const logoNhom = g => { const l = g.goi === 'claude' || g.hang === 'anthropic' ? ICON.logo_claude : g.goi === 'chatgpt' || g.hang === 'openai' ? ICON.logo_chatgpt : icoMau(ICON['key-round'], '#646A73', 16);
  return '<span class="logo-n">' + l.replace(/width="\d+"/, 'width="18"').replace(/height="\d+"/, 'height="18"') + '</span>'; };
function nutMh() { const c = dangChonChat(); if (!c.g) return '<span class="t12 phu">Chưa có nguồn AI đã kết nối</span>';
  const ten = c.m ? tenMh(c.m.ma, c.g.nhom, c.g) : 'Mặc định', hong = c.ghim && D.hong[D.htId];
  const tieu = hong && hong.nghi ? chuNghi(hong.nghi, timNguon(hong.nghi.nguon_id)) + ' · tạm dùng ' + (timNguon(hong.nguon_id) ? tenLoai(timNguon(hong.nguon_id)).replace(/ /g, ' ') : 'mô hình')
    : hong ? ten + (hong.het ? ' đang hết hạn mức' : ' chưa dùng được') + ' · tạm dùng ' + (hong.dung ? tenMh(hong.dung, hong.nguon_id, null, true) : timNguon(hong.nguon_id) ? tenLoai(timNguon(hong.nguon_id)).replace(/ /g, ' ') : 'mô hình') + ' (mặc định)' + (hong.het ? ' cho tới khi đặt lại' : '')
    : tenNguon(c.g).replace(/\u00a0/g, ' ') + ' · ' + ten + (c.m ? ' · Bản cụ thể: ' + c.m.ma : '') + (c.ghim ? ' · đã ghim cho cuộc trò chuyện này' : ' · theo mặc định chung');
  return '<button type="button" class="mh-nut' + (MH.noi === 'chat' ? ' mo' : '') + '" data-mhnut title="' + esc(tieu) + '"><span class="mh-cham"' + (hong ? ' style="background:#8F5F00"' : '') + '></span>' + esc(ten)
    + (c.ghim ? '<span aria-label="' + (hong ? 'ghim chưa dùng được' : 'đã ghim') + '">' + icoMau(ICON.pin, hong ? '#8F5F00' : '#646A73', 13) + '</span>' : '')
    + icoMau(ICON['chevron-down'], '#646A73', 14) + '</button>'; }
// N1: loại việc chưa đặt thì hộp "Đổi" ✓ ở "Mặc định của nguồn" của nguồn chính
const chonDang = noi => noi === 'chat' ? dangChonChat() : (MH.dich && mdLoai(MH.dich)) || {g: nhomChinh(), m: null};
const CHU_MD = 'Mặc định của nguồn';
const CHU_VN = 'Việc nền chưa đặt riêng và bot nền sau này dùng dòng này. Trò chuyện AI không theo.';   // Z12 nút (i)
const nhomDangMo = noi => { const c = chonDang(noi); return MH.mo !== null ? MH.mo : c.g ? c.g.nhom : (nhomChinh() || {}).nhom; };
function dsMhHtml(noi) { const q = MH.tim.trim().toLowerCase(), nh = D.dsmh ? D.dsmh.nhom : [], dang = chonDang(noi), moId = nhomDangMo(noi);
  let h = '', co = 0;
  for (const g of nh) { const tg = tenNguon(g), tenKhop = q && tg.toLowerCase().replace(/\u00a0/g, ' ').includes(q), ten = m => tenMh(m.ma, g.nhom, g);
    const hien = q && !tenKhop ? g.mohinh.filter(m => ten(m).toLowerCase().includes(q) || m.ma.toLowerCase().includes(q)) : g.mohinh;
    const coMd = !q || tenKhop || CHU_MD.toLowerCase().includes(q);   // Z10c: tìm "mặc" cũng ra dòng mặc định
    if (q && !tenKhop && !hien.length && !coMd) continue;
    co++; const mo = q ? true : moId === g.nhom;
    h += '<button type="button" class="mh-nhom" data-mhnhom="' + esc(g.nhom) + '">' + logoNhom(g) + '<span>' + esc(tg) + '</span>'
      + (g.chinh ? '<span title="Nguồn chính · ưu tiên 1">' + icoMau(ICON.check, '#258832', 14) + '</span>' : '') + '<span class="f1"></span>'
      + icoMau(ICON[mo ? 'chevron-down' : 'chevron-right'], '#646A73', 16) + '</button>';
    if (!mo) continue;
    if (coMd) {   // N2: khung chat chưa ghim thì ✓ ở đây (kể cả khi loại việc đặt 01 mô hình); hộp "Đổi": khi đặt về mặc định của nguồn
      const onMd = !dang.m && dang.g && dang.g.nhom === g.nhom;   // U10b F1 (QĐ190)
      h += '<button type="button" class="mh-dong' + (onMd ? ' on' : '') + '" data-mhmd="' + esc(g.nhom) + '"'
        + (noi === 'chat' ? ' title="Bỏ ghim · cuộc này và các cuộc mới dùng mô hình mặc định của nguồn"' : '') + '><span class="f1">' + CHU_MD + '</span>'
        + (onMd ? icoMau(ICON.check, '#1456F0', 16) : '') + '</button>'; }
    if (g.dang_tai) { h += '<div class="mh-tai">' + icoMau(ICON.loader, '#1456F0', 14) + 'Đang tải danh sách mô hình…</div>'; continue; }
    if (!hien.length) { h += '<div class="mh-tai">Chưa có danh sách: dùng mô hình mặc định của nguồn</div>'; continue; }
    for (const m of hien) { const on = !!dang.m && dang.m.khoa === m.khoa;   // U10b F1: ✓ đúng mô hình nút đang ghi (cả khi chưa ghim)
      h += '<button type="button" class="mh-dong' + (on ? ' on' : '') + '" data-mhchon="' + esc(m.khoa) + '" title="Bản cụ thể: ' + esc(m.ma) + '"><span class="f1">' + esc(ten(m)) + '</span>'
        + (on ? icoMau(ICON.check, '#1456F0', 16) : '') + '</button>'; } }
  if (!co) h += q ? '<div class="mh-rong">Không có nguồn hoặc mô hình khớp "' + esc(MH.tim) + '"</div>' : '<div class="mh-rong">Chưa có nguồn AI nào đã kết nối</div>';
  return h; }
const bangMhHtml = noi => '<div class="mh-bang" data-mhbang="' + noi + '"><label class="mh-tim">' + icoMau(ICON.search, '#646A73', 15)
  + '<input data-mhtim placeholder="Tìm nguồn, mô hình…" value="' + esc(MH.tim) + '"></label><div class="mh-ghi" title="'
  + 'Nhiều tài khoản cùng loại: dùng tài khoản đang chạy, hết hạn mức mới sang tài khoản dự phòng">'
  + (noi === 'chat' ? 'Dùng ngay cho cuộc này và các cuộc mới' : 'Mô hình mặc định cho loại việc này · chỉ hiện nguồn đã kết nối') + '</div>'
  + '<div class="mh-ds">' + dsMhHtml(noi) + '</div><div class="mh-chan"><button type="button" class="mh-nhom" data-trang="13" data-mhdong>'
  + icoMau(ICON.plus, '#1456F0', 16) + '<span style="color:#1456F0">Thêm nguồn AI ở mục Mô hình AI</span></button></div></div>';
function veNutMh() { const e = $('#mh-chat'); if (e) e.innerHTML = nutMh() + (MH.noi === 'chat' ? bangMhHtml('chat') : ''); }
function veLaiMh() { const b = MH.noi === 'md' ? $('#h-chonmh .mh-ds') : MH.noi === 'chat' ? $('#mh-chat .mh-ds') : null;
  if (b) b.innerHTML = dsMhHtml(MH.noi); if (MH.noi !== 'md') { const n = $('#mh-chat .mh-nut'); if (n) n.outerHTML = nutMh(); else veNutMh(); } }
function dongMh() { MH.noi = null; MH.tim = ''; MH.mo = null; veNutMh(); }
$('#h-them').insertAdjacentHTML('afterend', '<div class="lop" id="h-chonmh" hidden><div class="hop mh-hop"><div class="hop-dau">' + icoMau(ICON['brain-circuit'], '#1456F0', 20)
  + '<b class="f1 t16" id="mh-tieu">Chọn mô hình</b><button class="nut-ico" data-dong>' + icoMau(ICON.x, '#646A73', 20) + '</button></div><div class="hop-than" id="mh-than13"></div></div></div>');
document.addEventListener('click', async ev => {
  const b = ev.target.closest('[data-mhnut],[data-mhnhom],[data-mhchon],[data-mhmd],[data-doimd],[data-mhdong],[data-ivn]');
  if (!b) { if (MH.noi === 'chat' && !ev.target.closest('#mh-chat')) dongMh(); return; }
  const d = b.dataset;
  if ('mhdong' in d) { dongMh(); return; }   // không chặn: nút còn mở mục Mô hình AI
  if ('ivn' in d) { ev.stopImmediatePropagation(); bao(CHU_VN); return; }   // Z12: điện thoại bấm (i) hiện ô báo
  ev.stopImmediatePropagation();
  if ('mhnut' in d) { MH.noi = MH.noi === 'chat' ? null : 'chat'; MH.tim = ''; MH.mo = null; veNutMh(); if (MH.noi && await napDsMh()) veLaiMh(); return; }
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
  if (d.doimd) { await napDsMh(); if (!D.dsmh) { bao('Chưa tải được danh sách mô hình, anh thử lại.'); return; }
    MH.dich = d.doimd; MH.noi = 'md'; MH.tim = ''; MH.mo = null;
    $('#mh-tieu').textContent = 'Chọn mô hình · ' + nbsp(D.dsmh.loai_viec[d.doimd]); $('#mh-than13').innerHTML = bangMhHtml('md'); mo('h-chonmh'); }
}, true);
document.addEventListener('input', ev => { if (!ev.target.matches || !ev.target.matches('[data-mhtim]')) return; MH.tim = ev.target.value; veLaiMh(); });

// ---- Màn 08 Trò chuyện AI
function nhomNgay(iso) { const d = (iso || '').slice(0, 10), h = homNay(), q = new Date(Date.parse(h) - 86400e3).toISOString().slice(0, 10);
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
  if (x.vai === 'hethong') return '<div class="tn-bao do">' + ICON['circle-alert'] + '<span class="f1">' + cum(x.noidung) + '</span><button class="btn btn-phu nho" data-trang="13">Mở Mô hình AI</button></div>';
  return '<div class="tn ai"><div class="tn-ico">' + (ICON.tn_ai || ICON.sparkles) + '</div><div class="tn-noi">' + cum(x.noidung).split(/\n{2,}/).map(o => '<p>' + o.replace(/\n/g, '<br>') + '</p>').join('')
    + (x.ghim_hong || x.md_hong ? '<div class="tn-meta mh-vang"' + ((x.ghim_hong || x.md_hong || {}).loi_ct ? ' title="' + esc((x.ghim_hong || x.md_hong).loi_ct) + '"' : '') + '>' + icoMau(ICON['circle-alert'], '#8F5F00', 13) + '<span>' + chuGhimHong(x) + '</span></div>' : '')
    + '<div class="tn-meta"' + (tieuTraLoi(x) ? ' title="' + esc(tieuTraLoi(x)) + '"' : '') + '>' + cum(nhanTraLoi(x)) + '<button class="nut-ico nho" title="Chép" data-chep-tin="' + esc(x.id) + '">' + ICON.copy + '</button></div></div></div>';
}
function veTin(ds) { D.tin = ds; $('#ds-tin').innerHTML = ds.map(tinHtml).join(''); S.tc = ds.length ? 'co' : 'rong'; ve();
  const c = $('.tc-than'); if (c) c.scrollTop = c.scrollHeight; }
async function napTroChuyen() {
  try { D.ht = (await api('/trochuyen')).hoithoai; veDsHt();
    const md = D.md || await api('/mohinh').catch(() => null); if (md) D.md = md;
    await napDsMh(); veNutMh();   // QĐ178 (Z10): bỏ ô chọn nguồn đầu cuộc, nút chọn mô hình dưới khung nhập
  } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); }
}
async function moHt(id) { const d = await api('/trochuyen/' + encodeURIComponent(id)); D.htId = id; $('#tc-tieude').textContent = d.tieude; veTin(d.tinnhan); veDsHt(); dongMh(); }
async function guiTin(chu) {
  const o = $('#tc-o'), nd = (chu ?? o.value).trim(); if (!nd || S.tc === 'dang') return;
  o.value = ''; const cu = D.tin && D.htId ? D.tin : [];
  $('#ds-tin').innerHTML = cu.map(tinHtml).join('') + tinHtml({vai: 'nguoi', noidung: nd}); S.tc = 'dang'; ve();
  try { const ht0 = D.htId, gh = ghimKhoa();   // QĐ180: mỗi tin gửi kèm khoá mô hình ghim (trình duyệt nhớ)
    const kq = await api('/trochuyen', {hoithoai_id: D.htId, noidung: nd, mohinh_id: gh});
    if (!D.htId) $('#tc-tieude').textContent = nd.slice(0, 80);
    D.htId = kq.hoithoai_id; if (!ht0 && D.ghimMoi) { luuGhim(D.htId, D.ghimMoi); D.ghimMoi = null; }
    ghiHong(kq.tra_loi, gh); veTin([...cu, kq.hoi, kq.tra_loi]); veNutMh(); D.ht = (await api('/trochuyen')).hoithoai; veDsHt(); }
  catch (e) { S.tc = cu.length ? 'co' : 'rong'; ve(); bao(e.message + '.'); }
}

async function napTab() {
  try {
    if (S.tab === 'thongso') await napThongSo();
    else if (S.tab === 'taikhoan') await napTaiKhoan();
    else if (S.tab === 'capnhat') veCapNhat(await api('/capnhat'));
  } catch (e) { if (e.status && e.status !== 401) bao(e.message + '.'); }
}

// ---- Bấm
document.addEventListener('click', async ev => {
  if (ev.target.classList && ev.target.classList.contains('lop')) { dongHop(); return; }
  const t = ev.target.closest('button'); if (!t) { if (!ev.target.closest('.tha')) dongTha(); return; }
  const d = t.dataset;
  if (!('chuong' in d) && !('tk' in d) && !t.closest('.tha')) dongTha();
  if (d.set) { const [k, v] = d.set.split(':'); S[k] = v; }
  else if (d.trang) { if (S.g !== '01') { S.trang = d.trang; dongHop(); const c = $('#app .cuon'); if (c) c.scrollTop = 0; if (d.trang === '09') napTab(); if (d.trang === '13') napMoHinh(); if (d.trang === '08') napTroChuyen(); } }
  else if ('thu' in d) S.thu = S.thu ? 0 : 1;
  else if (d.tab) { S.tab = d.tab; napTab(); }
  else if ('mat' in d) { const i = $('#mk'); i.type = i.type === 'password' ? 'text' : 'password'; }
  else if ('dangnhap' in d) { await dangNhap(); return; }
  else if ('xacnhan' in d) { await xacNhanMa(t); return; }
  else if ('dangxuat' in d) { dongHop(); try { await api('/dangxuat', {}); } catch (e) { /* vẫn ra màn đăng nhập */ }
    S.g = '01'; S.dn = 'matkhau'; bao('Đã đăng xuất. Phiên trên máy này đã được thu hồi.'); }
  else if ('chuong' in d) { const e = $('#tha-chuong'), v = e.hidden; dongTha(); e.hidden = !v; if (v) demSo(true); }
  else if ('tk' in d) { const e = $('#tha-tk'), v = e.hidden; dongTha(); e.hidden = !v; }
  else if ('dochet' in d) { try { await api('/thongbao/dochet', {}); } catch (e) { bao(e.message + '.'); } await demSo(); return; }
  else if (d.di) { dongTha(); if (d.di === 'taikhoan' || d.di === 'ketkhoa' || d.di === 'capnhat') { S.trang = '09'; S.tab = d.di; napTab(); } else { S.trang = d.di; if (d.di === '09') napTab(); if (d.di === '13') napMoHinh(); }
    if (d.cuon) setTimeout(() => { const e = document.getElementById(d.cuon); if (e) e.scrollIntoView({block: 'start'}); }, 0); }
  else if ('noilai' in d) { try { await api('/demso'); S.k = 'binhthuong'; bao('Đã nối lại máy chủ.'); } catch (e) { /* vẫn mất */ } }
  else if (d.mo) { if (d.mo === 'h-2lop') datLaiDoiMay(); mo(d.mo); }
  else if ('dong' in d) dongHop();
  else if (d.sua) { await moSua(d.sua); }
  else if ('luusua' in d) { await luuSua(); }
  else if ('locChua' in d) { $('#ds-thongso').classList.toggle('chi-chua'); t.classList.toggle('on'); }
  else if (d.thuhoi) xacnhan('Thu hồi phiên này?', 'Máy đó phải đăng nhập lại mới dùng tiếp được.', 'Thu hồi', async () => {
    try { await api('/phien/' + encodeURIComponent(d.thuhoi) + '/thuhoi', {}); bao('Đã thu hồi phiên.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
  else if ('kiemtra' in d) { try { const k = await api('/capnhat/kiemtra', {}); veCapNhat(k); if (!k.loi) bao(k.co_ban_moi ? 'Có bản mới ' + k.ban_moi + '.' : 'Đã kiểm tra: chưa có bản mới.'); }
    catch (e) { bao('Kiểm tra lại chưa được: ' + (e.status ? e.message : 'mất kết nối máy chủ') + '.'); } }   // Y17 (c)
  else if ('capnhat' in d) moCapNhat();
  else if ('cnngay' in d) { await capNhat('ngay'); }
  else if ('cncho' in d) { await capNhat('cho'); }
  else if ('gd' in d) { const g = t.nextElementSibling; g.hidden = !g.hidden; }
  else if ('giu' in d) { try { const k = await api('/phien/giahan', {}); D.hetLuc = k.het_luc; S.k = 'binhthuong';
      bao(Date.parse(k.het_luc) - Date.now() > 5 * 60e3 ? 'Đã gia hạn phiên đăng nhập.' : 'Đã đủ 30 ngày từ lần đăng nhập, anh đăng nhập lại để dùng tiếp.'); } catch (e) { /* */ } }
  else if ('dxkhac' in d) xacnhan('Đăng xuất mọi máy khác?', 'Các máy khác phải đăng nhập lại. Máy này vẫn giữ đăng nhập.', 'Đăng xuất', async () => {
    try { const k = await api('/phien/thuhoi_khac', {}); bao('Đã đăng xuất ' + hai(k.so) + ' phiên trên các máy khác.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
  else if ('them' in d) mo('h-them');
  else if (d.dnGoi) { dongHop(); if (S.trang !== '13' || !D.md) { S.trang = '13'; ve(); await napMoHinh(); }
    const tk = Number(d.dnTk); if (tk) await batDauDn(d.dnGoi, tk); else await themTk(d.dnGoi); return; }
  else if (d.themGoi) { await themTk(d.themGoi); return; }
  else if ('mcXacnhan' in d) { await danMaClaude(); return; }
  else if (d.mdLay) { const tk = Number(d.mdLay); t.disabled = true;   // 0.7.8: chạy `claude setup-token` trên máy chủ
    try { const kq = await api('/mohinh/goi/claude/madaihan/batdau', {taikhoan: tk});
      if (kq.han) { await mdXong(tk, kq); return; }
      D.mdh[tk] = kq.khong_ho_tro ? {kieu: 'dan', loi: kq.loi} : {kieu: 'lay', url: kq.url, loi: ''}; veMoHinh();
      const o = $(kq.khong_ho_tro ? '#md-ma-dan' : '#md-ma-web'); if (o) o.focus(); }
    catch (e) { bao(e.message + '.'); } t.disabled = false; return; }
  else if (d.mdDan) { D.mdh[Number(d.mdDan)] = {kieu: 'dan', loi: ''}; veMoHinh(); const o = $('#md-ma-dan'); if (o) o.focus(); return; }
  else if (d.mdGui || d.mdLuu) { const tk = Number(d.mdGui || d.mdLuu), o = $(d.mdGui ? '#md-ma-web' : '#md-ma-dan'), ma = (o || {}).value || '';
    if (!ma.trim()) { bao(d.mdGui ? 'Anh dán mã trang Claude hiện ra.' : 'Anh dán ' + CHU_MDH.toLowerCase() + '.'); return; }
    t.disabled = true; if (o) o.value = '';   // không giữ mã trên màn
    try { await mdXong(tk, await api('/mohinh/goi/claude/madaihan/' + (d.mdGui ? 'ma' : 'dan'), {taikhoan: tk, ma})); }
    catch (e) { D.mdh[tk] = {...(D.mdh[tk] || {}), loi: e.message}; veMoHinh(); } t.disabled = false; return; }
  else if (d.mdHuy) { const tk = Number(d.mdHuy); try { await api('/mohinh/goi/claude/madaihan/huy', {taikhoan: tk}); } catch (e) { /* */ }
    D.mdh[tk] = null; veMoHinh(); return; }
  else if (d.mdNgat) { const tk = Number(d.mdNgat);
    xacnhan('Ngắt ' + CHU_MDH.toLowerCase() + ' của tài khoản ' + tk + '?', 'Phần mềm xoá mã khỏi Két khoá và thôi dùng mã này. Mã vẫn còn hiệu lực ở Claude tới khi anh thu hồi trên trang của Claude.<br><br>Thao tác ghi vào nhật ký.', 'Ngắt', async () => {
      try { await api('/mohinh/goi/claude/madaihan/ngat', {taikhoan: tk}); bao('Đã ngắt ' + CHU_MDH.toLowerCase() + ' của tài khoản ' + tk + '.'); } catch (e) { bao(e.message + '.'); }
      await napMoHinh(); }); return; }
  else if (d.goGoi) { const g = d.goGoi, tk = Number(d.goTk), ten = 'tài khoản ' + tk + ' của ' + tenNguon({goi: g});
    xacnhan('Gỡ ' + ten + '?', 'Phần mềm ngừng dùng tài khoản này, ô ẩn khỏi màn. Số đã dùng và chi phí cũ giữ nguyên; thao tác ghi vào nhật ký.<br><br>Dùng lại thì đăng nhập lại.', 'Gỡ tài khoản', async () => {
      D.trung[g] = 0;
      try { await api('/mohinh/goi/' + g + '/go', {taikhoan: tk}); bao('Đã gỡ ' + ten + '. Nhật ký đã ghi.'); } catch (e) { bao(e.message + '.'); }
      await napMoHinh(); }); }
  else if (d.dnHuy) { try { await api('/mohinh/goi/' + d.dnHuy + '/huy', {taikhoan: (D.dn[d.dnHuy] || {}).tk || 1}); } catch (e) { /* */ } D.dn[d.dnHuy] = {}; veMoHinh(); }
  else if (d.goithu) { t.disabled = true; const t0 = Date.now();
    try { const k = await api('/mohinh/' + encodeURIComponent(d.goithu) + '/goithu', {}); bao('Gọi thử đạt: ' + (tenNguon(timNguon(d.goithu)) || k.nguon) + ' trả lời sau ' + soVN(Math.round((Date.now() - t0) / 100) / 10) + ' giây.'); }
    catch (e) { bao('Gọi thử chưa đạt: ' + e.message + '.'); } t.disabled = false; await napMoHinh(); return; }
  else if (d.chep) { try { await navigator.clipboard.writeText(d.chep); bao('Đã chép mã thiết bị.'); } catch (e) { bao('Anh chép tay mã ' + d.chep + '.'); } }
  else if (d.chepTin) { const x = (D.tin || []).find(y => y.id === d.chepTin); if (x) { try { await navigator.clipboard.writeText(x.noidung); bao('Đã chép câu trả lời.'); } catch (e) { /* */ } } }
  else if ('tcMoi' in d) { D.htId = null; D.ghimMoi = null; dongMh(); D.tin = []; $('#ds-tin').innerHTML = ''; $('#tc-tieude').textContent = 'Trò chuyện mới'; S.tc = 'rong'; veDsHt(); $('#tc-o').focus(); }
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
setInterval(() => {   // phiên 30 ngày (QĐ90): báo trước 05 phút; khoá đăng nhập hết thì bật lại nút
  if (S.g !== '01' && D.hetLuc) { const con = Date.parse(D.hetLuc) - Date.now();
    if (con <= 0) { S.g = '01'; S.dn = 'hethan'; S.k = 'binhthuong'; ve(); } else if (con <= 5 * 60e3 && S.k === 'binhthuong') { S.k = 'saphethan'; ve(); } }
  if ((S.dn === 'khoa' || S.dn === 'khoatk') && D.khoaDen && Date.now() / 1000 >= D.khoaDen) { S.dn = 'matkhau'; D.khoaDen = 0; ve(); }
}, 20000);

ve();
api('/toi').then(vaoPhanMem).catch(() => { S.g = '01'; ve(); });
