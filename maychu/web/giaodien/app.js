// IGM360 giao diện ngày 04: màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt (bản vẽ đợt 1 đã duyệt, QĐ88;
// cập nhật theo QĐ89, QĐ90: chặn đoán mật khẩu, phiên 30 ngày, đăng xuất mọi máy khác).
// Cách bật tắt khối theo trạng thái (data-s) giữ như bản vẽ; số liệu lấy từ máy chủ.
'use strict';
const S = {g: '01', dn: 'matkhau', k: 'binhthuong', trang: '03', tab: 'thongso', cn: 'moinhat', xem: 'dt', thu: 0};
const $ = (q, r = document) => r.querySelector(q), $$ = (q, r = document) => [...r.querySelectorAll(q)];
const D = {thongso: null, maTam: '', maTamDoiMay: '', xnCb: null, suaK: '', capnhat: null, hetLuc: null, khoaDen: 0};
if (window.innerWidth < 700) { S.xem = 'mb'; document.body.classList.add('dien-thoai'); }

// ---- Định dạng: số 1-9 đứng trước danh từ đếm ghi 02 chữ số; ngày dd/mm/yyyy; nghìn ngăn bằng dấu chấm
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);
const soVN = v => { const n = Number(v); if (!Number.isFinite(n)) return v;
  if (Number.isInteger(n) && n < 10) return hai(n);
  const [a, b] = String(n).split('.'); return a.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (b ? ',' + b : ''); };
const ngay = iso => { if (!iso) return ''; const [y, m, d] = iso.slice(0, 10).split('-'); return d + '/' + m + '/' + y; };
const gio = iso => iso ? iso.slice(11, 16) : '';
const homNay = () => new Date(Date.now() + 7 * 3600e3).toISOString().slice(0, 10);
const luc = iso => !iso ? '' : (iso.slice(0, 10) === homNay() ? gio(iso) + ' hôm nay' : ngay(iso) + ' · ' + gio(iso));
const esc = t => String(t ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

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
async function demSo() {
  try {
    const d = await api('/demso');
    const b = $('[data-trang="05"] .bao'); b.textContent = d.cuacho ? soVN(d.cuacho) : ''; b.hidden = !d.cuacho;
    const g = $('[data-trang="10"] .bao'); g.textContent = d.ket_ai ? soVN(d.ket_ai) : ''; g.hidden = !d.ket_ai;
    const c = $('[data-chuong] .cham'); c.textContent = d.canhbao.length ? soVN(d.canhbao.length) : ''; c.hidden = !d.canhbao.length;
    $('#chuong-dem').textContent = d.canhbao.length ? soVN(d.canhbao.length) + ' mục' : 'Không có cảnh báo mới';
    $('#chuong-ds').innerHTML = d.canhbao.map(x => '<button class="tha-muc" data-di="' + esc(x.di) + '"><span class="ico-tron nho do-n">'
      + ICON['circle-alert'] + '</span><span class="f1 trai"><span class="b6 t13 khoi">' + esc(x.chu)
      + '</span><span class="t12 phu">' + esc(luc(x.luc)) + '</span></span></button>').join('');
  } catch (e) { /* mất kết nối đã hiện dải báo */ }
}

// ---- Màn 09 ngăn Thông số
const NHOM_ICO = {'Tiền và giá': 'wallet', 'Máy chủ và bảo mật': 'server', 'AI': 'bot', 'Báo cáo và lấy dữ liệu': 'clock'};
const hienGt = t => t.giatri_chu === null || t.giatri_chu === '' ? null
  : ((t.kieu === 'so' ? soVN(t.giatri_chu) : t.giatri_chu) + (t.donvi && t.kieu === 'so' ? ' ' + t.donvi : ''));
function veThongSo() {
  const d = D.thongso, nhom = {};
  d.thongso.forEach(t => (nhom[t.nhom] = nhom[t.nhom] || []).push(t));
  $('#ts-dem').innerHTML = hai(d.da_dat) + '/' + hai(d.tong) + '<small>đã đặt</small>';
  const vong = $('#ts-vong circle:last-child'); if (vong) vong.setAttribute('stroke-dasharray', (241.9 * d.da_dat / d.tong).toFixed(1) + ' 241.9');
  const chua = d.tong - d.da_dat; $('#ts-chua').textContent = chua ? hai(chua) + ' thông số anh chưa đặt' : 'Anh đã đặt đủ thông số';
  $('#ds-thongso').innerHTML = Object.entries(nhom).map(([ten, ds]) => '<div class="the nhom-ts"><div class="tieu">'
    + (ICON[NHOM_ICO[ten]] || '') + '<span class="b7">' + esc(ten) + '</span><span class="phu t12 ml">' + hai(ds.length) + ' thông số</span></div>'
    + ds.map(t => { const gt = hienGt(t);
      return '<div class="ts' + (gt ? '' : ' chua') + '"><div class="ts-ten">' + esc(t.nhan)
        + (gt || !t.khi_trong ? '' : '<div class="t12 xem-chu">' + esc(t.khi_trong) + '</div>') + '</div><div class="ts-gt">'
        + (gt ? '<span class="b7 so">' + esc(gt) + '</span><span class="t12 phu">Từ ' + ngay(t.hieuluc_tu) + ' · ' + (t.nguoi_dat === 'hethong' ? 'Mặc định' : 'Chủ') + '</span>'
             : '<span class="ttag xem">' + (t.ten === 'nhip_lay_dulieu' ? 'Chưa đặt loại nào' : 'Chưa đặt') + '</span>' + (t.ten === 'nhip_lay_dulieu' ? '' : '<span class="t12 phu">\u00a0</span>'))
        + '</div>' + (t.ten === 'nhip_lay_dulieu' ? '<button class="btn-chu" data-trang="11">' + ICON.sangtrang + 'Đặt ở Nguồn dữ liệu</button>'
          : t.khong_sua ? '<span class="t12 phu nw khoa-ts">' + ICON.khoats + esc(t.khong_sua) + '</span>'
          : '<button class="btn-chu" data-sua="' + t.ten + '">' + ICON.pencil + 'Sửa</button>') + '</div>'; }).join('') + '</div>').join('');
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
  $('#sua-tu').value = mai; $('#sua-loi').hidden = true; $('#sua-moc').textContent = ngay(t.hieuluc_tu);
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
  const tu = $('#sua-tu').value; if (!tu) { bao('Anh chọn ngày áp dụng.'); return; }
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
    return '<div class="hang" style="' + cot + '"><div class="rong-mb dong">' + (/iPhone|Android|iPad/.test(p.thietbi || '') ? ICON.smartphone : ICON.laptop)
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
  $('#cn-thaydoi').innerHTML = d.thaydoi.flatMap(m => m.dong).slice(0, 5).map(x => '<div class="dong t13">' + ICON.dongmoi + '<span>' + esc(x) + '</span></div>').join('');
  const cot = 'grid-template-columns:120px 1fr 160px';
  $('#ls-capnhat').innerHTML = d.lichsu.map(x => '<div class="hang" style="' + cot + '"><b class="so">' + esc(x.ban)
    + '</b><span data-l="Nội dung">' + (x.ban === d.ban_dang ? 'Bản đang dùng' : 'Bản đã dùng') + '</span><span data-l="Ngày cài" class="so">' + ngay(x.luc) + '</span></div>').join('');
  $('.tab[data-tab="capnhat"] .cham-xanh').hidden = !d.co_ban_moi;
  if (d.loi) bao(d.loi + '.'); ve();
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
  else if (d.trang) { if (S.g !== '01') { S.trang = d.trang; dongHop(); const c = $('#app .cuon'); if (c) c.scrollTop = 0; if (d.trang === '09') napTab(); } }
  else if ('thu' in d) S.thu = S.thu ? 0 : 1;
  else if (d.tab) { S.tab = d.tab; napTab(); }
  else if ('mat' in d) { const i = $('#mk'); i.type = i.type === 'password' ? 'text' : 'password'; }
  else if ('dangnhap' in d) { await dangNhap(); return; }
  else if ('xacnhan' in d) { await xacNhanMa(t); return; }
  else if ('dangxuat' in d) { dongHop(); try { await api('/dangxuat', {}); } catch (e) { /* vẫn ra màn đăng nhập */ }
    S.g = '01'; S.dn = 'matkhau'; bao('Đã đăng xuất. Phiên trên máy này đã được thu hồi.'); }
  else if ('chuong' in d) { const e = $('#tha-chuong'), v = e.hidden; dongTha(); e.hidden = !v; if (v) demSo(); }
  else if ('tk' in d) { const e = $('#tha-tk'), v = e.hidden; dongTha(); e.hidden = !v; }
  else if (d.di) { dongTha(); if (d.di === 'taikhoan' || d.di === 'ketkhoa') { S.trang = '09'; S.tab = d.di; napTab(); } else { S.trang = d.di; if (d.di === '09') napTab(); } }
  else if ('noilai' in d) { try { await api('/demso'); S.k = 'binhthuong'; bao('Đã nối lại máy chủ.'); } catch (e) { /* vẫn mất */ } }
  else if (d.mo) { if (d.mo === 'h-2lop') datLaiDoiMay(); mo(d.mo); }
  else if ('dong' in d) dongHop();
  else if (d.sua) { await moSua(d.sua); }
  else if ('luusua' in d) { await luuSua(); }
  else if ('locChua' in d) { $('#ds-thongso').classList.toggle('chi-chua'); t.classList.toggle('on'); }
  else if (d.thuhoi) xacnhan('Thu hồi phiên này?', 'Máy đó phải đăng nhập lại mới dùng tiếp được.', 'Thu hồi', async () => {
    try { await api('/phien/' + encodeURIComponent(d.thuhoi) + '/thuhoi', {}); bao('Đã thu hồi phiên.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
  else if ('kiemtra' in d) { try { const k = await api('/capnhat/kiemtra', {}); veCapNhat(k); if (!k.loi) bao(k.co_ban_moi ? 'Có bản mới ' + k.ban_moi + '.' : 'Đã kiểm tra: chưa có bản mới.'); } catch (e) { /* */ } }
  else if ('capnhat' in d) moCapNhat();
  else if ('cnngay' in d) { await capNhat('ngay'); }
  else if ('cncho' in d) { await capNhat('cho'); }
  else if ('gd' in d) { const g = t.nextElementSibling; g.hidden = !g.hidden; }
  else if ('giu' in d) { try { const k = await api('/phien/giahan', {}); D.hetLuc = k.het_luc; S.k = 'binhthuong';
      bao(Date.parse(k.het_luc) - Date.now() > 5 * 60e3 ? 'Đã gia hạn phiên đăng nhập.' : 'Đã đủ 30 ngày từ lần đăng nhập, anh đăng nhập lại để dùng tiếp.'); } catch (e) { /* */ } }
  else if ('dxkhac' in d) xacnhan('Đăng xuất mọi máy khác?', 'Các máy khác phải đăng nhập lại. Máy này vẫn giữ đăng nhập.', 'Đăng xuất', async () => {
    try { const k = await api('/phien/thuhoi_khac', {}); bao('Đã đăng xuất ' + hai(k.so) + ' phiên trên các máy khác.'); napTaiKhoan(); } catch (e) { bao(e.message + '.'); } });
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
  if (ev.key === 'Escape') { dongHop(); dongTha(); ve(); } });
setInterval(() => { if (S.g !== '01') demSo(); }, 60000);
setInterval(() => {   // phiên 30 ngày (QĐ90): báo trước 05 phút; khoá đăng nhập hết thì bật lại nút
  if (S.g !== '01' && D.hetLuc) { const con = Date.parse(D.hetLuc) - Date.now();
    if (con <= 0) { S.g = '01'; S.dn = 'hethan'; S.k = 'binhthuong'; ve(); } else if (con <= 5 * 60e3 && S.k === 'binhthuong') { S.k = 'saphethan'; ve(); } }
  if ((S.dn === 'khoa' || S.dn === 'khoatk') && D.khoaDen && Date.now() / 1000 >= D.khoaDen) { S.dn = 'matkhau'; D.khoaDen = 0; ve(); }
}, 20000);

ve();
api('/toi').then(vaoPhanMem).catch(() => { S.g = '01'; ve(); });
