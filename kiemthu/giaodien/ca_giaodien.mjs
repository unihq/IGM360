// Tệp ca đo giao diện 0.10.1 (M01–M12) – bản chạy trên máy GitHub (QĐ683), cùng nội dung bộ đo tự kiểm trên máy (Cửa 0, QĐ681).
// cách chèn học từ CDO sc_chatdai.mjs / sau.js (mauChat, dongMau). Mã chạy ở trang không dùng dấu gạch ngược.
// Chọn bài: biến BAI = "M01,M02,M03" (mặc định cả 03); KHO = "1920,1440,1280,1024,390".
const BAI = (process.env.BAI || 'M01,M02,M03').split(',');
const KHO_CHON = (process.env.KHO || '1920,1440,1280,1024,390').split(',').map(Number);
const KHO = [[1920, 1080, false], [1440, 900, false], [1366, 768, false], [1280, 800, false], [1024, 768, false], [390, 844, true]]
  .filter(k => KHO_CHON.includes(k[0]));
const CHEDO = process.env.CHEDO || 'sang';
const MAN = (process.env.MAN || '03,04,05,06,07,08,09,10,11,12,13,14,15').split(',');

// Mở màn bằng bấm mục menu như người dùng
const MO = (t, xoa = true) => `(async () => { const ngu = ms => new Promise(r => setTimeout(r, ms));
  if ('${t}' === '08' && ${xoa}) { try { localStorage.removeItem('igm360_tc_cot'); localStorage.removeItem('igm360_tc_thu'); } catch (e) {} }   // khóa nhớ cột có thể còn sót do Edge bị tắt cưỡng bức trước khi ghi xuống đĩa
  const c = [...document.querySelectorAll('[data-trang="${t}"]')].find(e => e.offsetParent !== null) || document.querySelector('[data-trang="${t}"]');
  if (c) { c.click(); await ngu(1500); } })()`;

// Chèn dữ liệu dài: 60 dòng vào thân trang (màn 09 vào khối cuộn trong), 40 đoạn tin vào vùng tin màn 08
const CHEN = t => `(async () => { const ngu = ms => new Promise(r => setTimeout(r, ms));
  const p = document.getElementById('p${t}'); if (!p) return;
  if ('${t}' === '08') { const th = p.querySelector('.tc-than'); const d = document.createElement('div'); d.className = 'gia-dai';
    for (let i = 1; i <= 40; i++) { const e = document.createElement('p'); e.textContent = 'Đoạn thử ' + i + ' – dữ liệu giả chèn trong trình duyệt đo, không phải dữ liệu thật.'; d.appendChild(e); }
    th.appendChild(d); const ds = p.querySelector('#ds-ht'); if (ds) for (let i = 1; i <= 30; i++) { const e = document.createElement('div'); e.className = 'gia-dai'; e.textContent = 'Hội thoại mẫu ' + i; ds.appendChild(e); } }
  else { const dich = (('${t}' === '09') && p.querySelector('.cd-than')) || p; const d = document.createElement('div'); d.className = 'gia-dai';
    for (let i = 1; i <= 60; i++) { const e = document.createElement('p'); e.textContent = 'Dòng mẫu ' + i + ' – dữ liệu giả chèn trong trình duyệt đo.'; d.appendChild(e); }
    dich.appendChild(d); }
  await ngu(300); })()`;

// Công cụ đo dùng chung (đặt vào trang)
const CONG_CU = `const vis = e => { if (!e) return false; const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && (e.offsetParent !== null || s.position === 'fixed'); };
  const R = e => { const b = e.getBoundingClientRect(); return [Math.round(b.left * 2) / 2, Math.round(b['top'] * 2) / 2, Math.round(b.width * 2) / 2, Math.round(b.height * 2) / 2]; };
  const ten = e => (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(' ').slice(0, 2).join('.') : e.tagName.toLowerCase()) + ':' + ((e.innerText || e.getAttribute('aria-label') || '').trim().replace(/ +/g, ' ').slice(0, 24));
  const cuonDuoc = () => [...document.querySelectorAll('*')].filter(e => { const s = getComputedStyle(e); return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 2 && vis(e); });`;

// M01: phần tử bấm được + chữ lá đang hiện, từng cặp không lồng nhau giao > 1 px
const DO_M01 = `(() => { ${CONG_CU}
  const bam = [...document.querySelectorAll('button, a, input, select, textarea, [role=button], [data-trang]')].filter(vis)
    .filter(e => !e.closest('.tha:not([hidden]), .lop, [hidden]') && !e.classList.contains('bao'));
  const la = [...document.querySelectorAll('#khung *')].filter(e => vis(e) && e.children.length === 0 && (e.innerText || '').trim() && !bam.some(b => b.contains(e)));
  // chữ lá: hộp của CHÍNH dòng chữ (Range) cắt theo khung phần tử – chữ bị cắt "…" chỉ tính phần hiện (QA giữ; chữ bị cắt do M05 bắt)
  const hop = e => { const k = e.getBoundingClientRect(); if (!la.includes(e)) return k; const g = document.createRange(); g.selectNodeContents(e); const r = g.getBoundingClientRect();
    const s = getComputedStyle(e); if (s.overflowX === 'visible') return r; const L = Math.max(r.left, k.left), T = Math.max(r['top'], k['top']);
    return {left: L, top: T, right: Math.min(r.right, k.right), bottom: Math.min(r.bottom, k.bottom), width: Math.max(0, Math.min(r.right, k.right) - L)}; };
  // thanh cố định / dính (QA SOAT-BODO-P1, P2): (i) cặp cả 02 bên thuộc thanh (kể cả 02 thanh khác nhau) vẫn so;
  // (ii) [thanh] × [nội dung]: chỉ bỏ qua khi vùng cuộn GẦN NHẤT chứa nội dung còn đủ LƯỢNG cuộn để kéo nó ra khỏi thanh:
  //      thanh dưới: scrollHeight − scrollTop − clientHeight ≥ r.bottom − rb['top']; thanh trên: scrollTop ≥ rb.bottom − r['top']
  const noi = e => { for (let x = e; x && x !== document.body; x = x.parentElement) { const ps = getComputedStyle(x).position; if (ps === 'fixed' || ps === 'sticky') return x; } return null; };
  const vungGan = e => { for (let x = e.parentElement; x && x !== document.body && x !== document.documentElement; x = x.parentElement) {
      if (/(auto|scroll)/.test(getComputedStyle(x).overflowY) && x.scrollHeight > x.clientHeight + 2) return x; } return document.scrollingElement; };
  const loDuoc = (e, thanh) => { const v = vungGan(e), r = hop(e), rb = thanh.getBoundingClientRect();
    const ch = v === document.scrollingElement ? innerHeight : v.clientHeight;
    return rb['top'] > innerHeight / 2 ? v.scrollHeight - v.scrollTop - ch >= r.bottom - rb['top'] : v.scrollTop >= rb.bottom - r['top']; };
  const boQua = (a, b) => { const na = noi(a), nb = noi(b); if (!na === !nb) return false; return na ? loDuoc(b, na) : loDuoc(a, nb); };
  const ds = [...bam, ...la].filter(e => { const r = hop(e); return r.width > 0 && r.bottom > 0 && r['top'] < innerHeight && r.right > 0 && r.left < innerWidth; });
  const de = [];
  for (let i = 0; i < ds.length; i++) for (let j = i + 1; j < ds.length; j++) { const a = ds[i], b = ds[j]; if (a.contains(b) || b.contains(a) || boQua(a, b)) continue;
    const x = hop(a), y = hop(b); const w = Math.min(x.right, y.right) - Math.max(x.left, y.left), h = Math.min(x.bottom, y.bottom) - Math.max(x['top'], y['top']);
    if (w > 1 && h > 1) de.push([ten(a), ten(b), Math.round(w) + 'x' + Math.round(h)]); }
  // (iii) elementFromPoint tại tâm mỗi nút trong khung: phần tử trên cùng phải là chính nút (hoặc con của nút)
  const che = bam.filter(e => { const r = e.getBoundingClientRect(); const x = r.left + r.width / 2, y = r['top'] + r.height / 2;
      if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return false; const t = document.elementFromPoint(x, y); if (!t || t === e || e.contains(t)) return false;
      // (iii) cùng điều kiện (ii): nút nội dung bị thanh che chỉ bỏ qua khi còn đủ lượng cuộn để lộ ra
      const tb = noi(t); if (!tb || noi(e)) return true; return !loDuoc(e, tb); })
    .map(e => { const r = e.getBoundingClientRect(); const t = document.elementFromPoint(r.left + r.width / 2, r['top'] + r.height / 2); return [ten(e), ten(t)]; });
  return {so_de: de.length, de: de.slice(0, 10), so_che: che.length, che: che.slice(0, 10), so_phan_tu: ds.length}; })()`;

// M01C: như M01 nhưng đo ở vị trí cuộn cuối (QA SOAT-BODO-P2 – nút cuối trang dưới thanh tab)
const DO_M01C = `(async () => { const ngu = ms => new Promise(r => setTimeout(r, ms));
  document.querySelectorAll('*').forEach(e => { if (e.scrollHeight > e.clientHeight + 2 && /(auto|scroll)/.test(getComputedStyle(e).overflowY)) e.scrollTop = e.scrollHeight; });
  window.scrollTo(0, 99999); await ngu(400); return ${DO_M01}; })()`;

// M02: đầu màn (máy tính) / thanh trên + thanh đáy (điện thoại) đứng yên khi cuộn tới cuối với dữ liệu dài
const DO_M02 = t => `(async () => { ${CONG_CU} const ngu = ms => new Promise(r => setTimeout(r, ms));
  const p = document.getElementById('p${t}'); const dt = document.getElementById('app').classList.contains('mb');
  const moc = dt ? [document.querySelector('.thanh-tren'), document.querySelector('nav.tab-duoi')]
    : [document.querySelector('#dau-man .dau-trang') || (p && p.querySelector('.dau-trang, .tc-dau')), document.querySelector('.vi-tri')];
  const truoc = moc.map(e => vis(e) ? R(e) : null);
  const vung = cuonDuoc().sort((a, b) => b.clientHeight * b.clientWidth - a.clientHeight * a.clientWidth);
  vung.forEach(v => v.scrollTop = v.scrollHeight); window.scrollTo(0, 99999); await ngu(400);
  const sau = moc.map(e => vis(e) ? R(e) : null);
  const lech = truoc.map((a, i) => a && sau[i] ? Math.abs(a[1] - sau[i][1]) : null);
  const cum = document.querySelector('.vi-tri'); const cr = cum && vis(cum) ? cum.getBoundingClientRect() : null;
  return {man: '${t}', vung_cuon: vung.map(v => (v.className || v.tagName).toString().slice(0, 24) + ' ' + v.clientHeight + '/' + v.scrollHeight).slice(0, 3),
    trang_cuon: document.scrollingElement.scrollHeight > innerHeight, truoc, sau, lech, cum_trong_khung: cr ? cr['top'] >= 0 && cr.bottom <= innerHeight : null}; })()`;

// M03: ô nhập + chọn mô hình màn 08 luôn trong khung ở đầu / giữa / cuối vùng tin
const DO_M03 = `(async () => { ${CONG_CU} const ngu = ms => new Promise(r => setTimeout(r, ms));
  const n = document.querySelector('#p08 .tc-nhap'), d = document.querySelector('#p08 .tc-duoi');
  const vung = cuonDuoc().sort((a, b) => b.clientHeight - a.clientHeight); const kq = [];
  for (const vt of [0, 0.5, 1]) { vung.forEach(v => v.scrollTop = (v.scrollHeight - v.clientHeight) * vt); window.scrollTo(0, (document.scrollingElement.scrollHeight - innerHeight) * vt); await ngu(300);
    const a = n.getBoundingClientRect(), b = d.getBoundingClientRect(); const tab = [...document.querySelectorAll('nav.tab-duoi')].find(vis);
    const day = tab ? tab.getBoundingClientRect()['top'] : innerHeight;   // (iv) QA: 390 đáy ô nhập không được thấp hơn mép trên thanh tab
    kq.push({vt, nhap: R(n), duoi: R(d), day_khung: Math.round(day), ngoai_px: Math.round(Math.max(0, -a['top'], a.bottom - day, -b['top'], b.bottom - day))}); }
  return {vung_cuon: vung.map(v => (v.className || v.tagName).toString().slice(0, 24) + ' ' + v.clientHeight + '/' + v.scrollHeight).slice(0, 3), kq}; })()`;

// M06: hộp bao (trái, trên, rộng, cao) + tâm dọc các khối cùng hàng giữa các cột (VE0101_13), mô tả đầu màn 01 dòng
const DO_M06 = `(() => { ${CONG_CU}
  const H = q => { const e = [...document.querySelectorAll(q)].find(vis); if (!e) return null; const r = e.getBoundingClientRect(); return {hop: R(e), tam: Math.round((r['top'] + r.height / 2) * 2) / 2}; };
  const mt = [...document.querySelectorAll('#dau-man .dau-trang .phu')].find(vis);
  return {dau_man: H('#dau-man'), dau_trang: H('#dau-man .dau-trang'), cum: H('.vi-tri'), nut_chinh: H('#dau-man .btn-chinh'),
    logo: H('nav.menu .logo'), muc_tc: H('nav.menu [data-trang="08"]'), tc_hang: H('#p08 .tc-hang'), tc_dau: H('#p08 .tc-dau'), tc_tim: H('#p08 #tc-tim'),
    tc_day: H('#p08 .tc-day'), tc_nhap: H('#p08 .tc-nhap'), chan: H('nav.menu .chan-menu'), he_thong: H('nav.menu [data-nhom-nut="HỆ THỐNG"]'),
    o_go: (() => { const i = document.querySelector('#p08 .tc-nhap input'), k = document.querySelector('#p08 .tc-nhap'); return i && k ? {nen_o_go: getComputedStyle(i).backgroundColor, nen_khoi: getComputedStyle(k).backgroundColor, chu: getComputedStyle(i).color} : null; })(),
    mo_ta: mt ? {mot_dong: mt.getBoundingClientRect().height < 26, cat: mt.scrollWidth > mt.clientWidth, ellipsis: getComputedStyle(mt).textOverflow} : null}; })()`;

// M05 (G04, QA R01, S03; CPO P2-COT): phần tử con vượt mép thẻ chứa (không có lớp cắt ở giữa) · chữ bị cắt KHÔNG có "…" ·
// trang cuộn ngang · vạch màu sát mép trái (QĐ575, công thức QA ca_do02) · tên nhóm thanh trái 13 px (QĐ556), icon nhóm 16 × 16 cùng màu chữ (QĐ674)
const DO_M05 = `(() => { ${CONG_CU}
  const KHOI_CHINH = ['nav.menu', '#dau-man', '.thanh-tren', 'nav.tab-duoi', '.tc-trai', '.tc-giua'];
  const laKhoi = x => { const s = getComputedStyle(x); return (parseFloat(s.borderTopWidth) > 0 && parseFloat(s.borderTopLeftRadius) > 0)
      || s.overflowX !== 'visible' || s.overflowY !== 'visible' || KHOI_CHINH.some(q => x.matches(q)); };
  const khoi = e => { for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) if (laKhoi(x)) return x; return null; };
  const cuonDoc = x => /(auto|scroll)/.test(getComputedStyle(x).overflowY);   // khối cuộn dọc: nội dung dài hơn khối theo chiều dọc là bình thường
  const chu = e => { const g = document.createRange(); g.selectNodeContents(e); return g.getBoundingClientRect(); };
  const hien = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && e.getClientRects().length > 0 && !e.closest('[hidden]'); };
  // phần tử xét: bấm được, ô nhập, thẻ, nút, mọi khối có lớp cắt (khối bọc tự tràn), chữ lá (gồm thẻ dòng) – không lọc "đang thấy"
  const cac = [...document.querySelectorAll('#khung *')].filter(hien).filter(e => e.matches('button, input, select, textarea, a, .o-nhap, .the, .btn')
      || getComputedStyle(e).overflowX !== 'visible' || (e.children.length === 0 && (e.textContent || '').trim()));
  const vuot = [];
  const chuCat = e => { const r = chu(e), k = e.getBoundingClientRect(), st = getComputedStyle(e); if (st.overflowX === 'visible' || k.width === 0) return r;
    const L = Math.max(r.left, k.left), T = Math.max(r['top'], k['top']), Rr = Math.min(r.right, k.right), B = Math.min(r.bottom, k.bottom); return {left: L, top: T, right: Rr, bottom: B, width: Math.max(0, Rr - L), height: Math.max(0, B - T)}; };   // QA M05b: chữ tự cắt "…"
  for (const e of cac) { const laChu = e.children.length === 0 && !e.matches('button, input, select, textarea, a'); const a = laChu ? chuCat(e) : e.getBoundingClientRect();
    if (a.width === 0 && a.height === 0) continue;
    const c = khoi(e); if (c) { const b = c.getBoundingClientRect(); const ngang = Math.max(b.left - a.left, a.right - b.right);
      const doc = cuonDoc(c) ? 0 : Math.max(b['top'] - a['top'], a.bottom - b.bottom); const d = Math.max(ngang, doc);
      if (d > 0.5) vuot.push([ten(e), ten(c), Math.round(d * 2) / 2, ngang >= doc ? 'ngang' : 'doc']); }
    const w = Math.max(-a.left, a.right - innerWidth); if (w > 0.5) vuot.push([ten(e), 'mép cửa sổ', Math.round(w * 2) / 2, 'ngang']); }
  const la = [...document.querySelectorAll('#khung *')].filter(e => hien(e) && e.children.length === 0 && (e.textContent || '').trim());
  // chữ bị cắt không "…": ngang (khối có lớp cắt, không ellipsis) hoặc dọc (khối cao cố định có lớp cắt); thẻ dòng đo bằng Range so khối gần nhất
  const catKhong = la.filter(e => { const s = getComputedStyle(e); const ngang = e.clientWidth > 0 ? e.scrollWidth > e.clientWidth + 1 && s.overflowX !== 'visible' && !/(auto|scroll)/.test(s.overflowX) && s.textOverflow !== 'ellipsis' : false;
      const doc = e.clientHeight > 0 && e.scrollHeight > e.clientHeight + 1 && s.overflowY === 'hidden';
      let dong = false; if (e.clientWidth === 0) { const c = khoi(e); if (c && getComputedStyle(c).overflowX === 'hidden' && getComputedStyle(c).textOverflow !== 'ellipsis') { const r = chu(e), b = c.getBoundingClientRect(); dong = r.right > b.right + 1 || r.left < b.left - 1; } }
      return ngang || doc || dong; }).map(ten);
  const catCo = la.filter(e => { const s = getComputedStyle(e); return e.scrollWidth > e.clientWidth + 1 && s.textOverflow === 'ellipsis'; }).map(ten);
  const vach = [...document.querySelectorAll('#khung *')].filter(vis).filter(e => { const s = getComputedStyle(e); const bl = parseFloat(s.borderLeftWidth), br = parseFloat(s.borderRightWidth), bt = parseFloat(s.borderTopWidth);
      const sh = s.boxShadow || ''; const q = sh.indexOf('inset') >= 0 ? sh.split('inset')[1].trim().split(' ') : null; const inset = q && parseFloat(q[0]) > 0 && parseFloat(q[1]) === 0;
      return (bl >= 2 && bl > br && bl > bt && s.borderLeftColor !== 'rgba(0, 0, 0, 0)') || inset; }).map(ten);
  const nhom = [...document.querySelectorAll('nav.menu .nhom-nut')].filter(vis).map(b => { const t = b.querySelector('.nhom-ten'), i = b.querySelector('svg');
    const ri = i ? i.getBoundingClientRect() : null; const pa = i ? i.querySelector('path, rect, circle, line') : null;
    return {ten: (t ? t.innerText : b.innerText).trim(), co: getComputedStyle(t || b).fontSize, icon: ri ? [Math.round(ri.width), Math.round(ri.height)] : null,
      mau_chu: getComputedStyle(t || b).color, stroke_icon: pa ? getComputedStyle(pa).stroke : null}; });
  return {so_vuot: vuot.length, vuot: vuot.slice(0, 12), so_cat_khong_cham: catKhong.length, cat_khong_cham: catKhong.slice(0, 8), cat_co_cham: catCo.slice(0, 6),
    cuon_ngang: document.scrollingElement.scrollWidth > innerWidth + 1, so_vach_trai: vach.length, vach: vach.slice(0, 5), nhom}; })()`;
const DO_M05C = `(async () => { const ngu = ms => new Promise(r => setTimeout(r, ms));
  document.querySelectorAll('*').forEach(e => { if (e.scrollHeight > e.clientHeight + 2 && /(auto|scroll)/.test(getComputedStyle(e).overflowY)) e.scrollTop = e.scrollHeight; });
  window.scrollTo(0, 99999); await ngu(400); return ${DO_M05}; })()`;

// M10 (CPO P2-COT): cột danh sách với 100 cuộc giả – đáy cột = đáy khung chat, cuộn riêng, thanh cuộn kiểu C (12 px), cuộn danh sách không làm trôi trang
const CHEN_100 = `(async () => { const ds = document.querySelector('#ds-ht'); let h = '';
  for (let i = 1; i <= 100; i++) h += '<button class="ht gia-dai"><span>Hội thoại mẫu ' + i + ' – dữ liệu giả</span></button>';
  ds.insertAdjacentHTML('beforeend', h); await new Promise(r => setTimeout(r, 300)); })()`;
const DO_M10 = `(async () => { ${CONG_CU} const ngu = ms => new Promise(r => setTimeout(r, ms));
  const p = document.getElementById('p08'), tr = p.querySelector('.tc-trai'), g = p.querySelector('.tc-giua'), ds = p.querySelector('#ds-ht'), hang = p.querySelector('.tc-hang'), ct = document.querySelector('.cuon-trong');
  const truoc = {hang: R(hang), ct: ct.scrollTop, trang: document.scrollingElement.scrollTop};
  ds.scrollTop = ds.scrollHeight; await ngu(300);
  const a = tr.getBoundingClientRect(), b = g.getBoundingClientRect();
  const cs = getComputedStyle(ds), thanh = ds.offsetWidth - ds.clientWidth - parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth);
  const muc = [...ds.children].filter(x => x.getClientRects().length).pop(); const rm = muc.getBoundingClientRect(), rd = ds.getBoundingClientRect();
  const tam = document.elementFromPoint(rm.left + rm.width / 2, rm['top'] + rm.height / 2);
  const luat = []; for (const ss of document.styleSheets) { let r = []; try { r = [...ss.cssRules]; } catch (e) {} for (const x of r) if (x.selectorText && /::-webkit-scrollbar-thumb(?!:)/.test(x.selectorText)) luat.push(x.cssText.slice(0, 220)); }
  return {muc_cuoi_tron: rm.bottom <= rd.bottom + 0.5 && rd.bottom <= a.bottom + 0.5 && !!tam && (tam === muc || muc.contains(tam)), muc_cuoi: [Math.round(rm['top']), Math.round(rm.bottom)], day_ds: Math.round(rd.bottom),
    thanh_cuon_tru_vien: thanh, luat_thanh_cuon: luat,
    day_cot: Math.round(a.bottom), day_khung: Math.round(b.bottom), lech_day: Math.round(Math.abs(a.bottom - b.bottom) * 2) / 2,
    ds_cuon: [ds.clientHeight, ds.scrollHeight, ds.scrollTop], thanh_cuon_px: ds.offsetWidth - ds.clientWidth, hang_truoc: truoc.hang, hang_sau: R(hang),
    trang_troi: ct.scrollTop !== truoc.ct || document.scrollingElement.scrollTop !== truoc.trang}; })()`;

// M07 (PD10, PD11): cột hội thoại – tọa độ tính theo bố cục chốt: thẻ cột trái mép trái 248, vạch kéo ở [248 + cột, +8], tâm +4;
// nút thu (cuối hàng đầu cột) tâm x = 248 + 260 − 1 − 10 − 18 = 479, y = 37; nút "Hiện lịch sử" ở dải tâm x = 248 + 28 = 276, y = 37
const DAT_LAI = `(async () => { try { localStorage.removeItem('igm360_tc_cot'); localStorage.removeItem('igm360_tc_thu'); } catch (e) {}
  window.dispatchEvent(new Event('resize')); await new Promise(r => setTimeout(r, 300)); })()`;
const DO_M07 = `(() => { const p = document.getElementById('p08'), tr = p.querySelector('.tc-trai'), g = p.querySelector('.tc-giua'), v = p.querySelector('.tc-vach');
  const hien = e => e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden';
  const dau = p.querySelector('.tc-dai-dau'); const rd = dau && hien(dau) ? dau.getBoundingClientRect() : null;
  let k = {}; try { k = {cot: localStorage.getItem('igm360_tc_cot'), thu: localStorage.getItem('igm360_tc_thu')}; } catch (e) {}
  return {cot: Math.round(tr.getBoundingClientRect().width), khung: Math.round(g.getBoundingClientRect().width), tc: Math.round(p.querySelector('.tc').clientWidth),
    khoa: k, thu: p.classList.contains('thu-cot'), vach: hien(v) ? [Math.round(v.getBoundingClientRect().left), Math.round(v.getBoundingClientRect().width)] : null,
    dai_nut: [...p.querySelectorAll('.tc-dai button')].filter(hien).map(b => b.getAttribute('aria-label')),
    dai_dau: rd ? [Math.round(rd['top']), Math.round(rd.height), Math.round((rd['top'] + rd.height / 2) * 2) / 2] : null,
    nhan: [...p.querySelectorAll('[data-tc-thu], .tc-vach')].map(e => e.getAttribute('aria-label'))}; })()`;
const keo = (tu, toi) => [['mouseMoved', tu, 400], ['mousePressed', tu, 400], ['mouseMoved', (tu + toi) / 2, 400], ['mouseMoved', toi, 400], ['mouseReleased', toi, 400]];
const bam = (x, y) => [['mouseMoved', x, y], ['mousePressed', x, y], ['mouseReleased', x, y]];
const CA_M07 = (kho, NOI) => { const c = (ten, them) => ({ten: 'M07_' + ten, kho, chedo: CHEDO, cho: 2200, cho_sau: 400, do: DO_M07, anh: kho[0] === 1440, ...them});
  const mo = NOI(MO('08'), DAT_LAI);
  return [
    c('0_macdinh', {truoc: mo}),
    c('1_keo_nho', {truoc: mo, chuot: keo(512, 300)}),
    c('2_keo_lon', {truoc: mo, chuot: keo(512, 1200)}),
    c('3_phim', {truoc: NOI(mo, `(async () => { document.querySelector('#p08 .tc-vach').focus(); })()`), phim: ['ArrowRight', 'ArrowRight']}),
    c('4_bam_dup', {truoc: NOI(mo, `(async () => { localStorage.setItem('igm360_tc_cot', '270'); window.dispatchEvent(new Event('resize')); await new Promise(r => setTimeout(r, 300)); })()`),
      chuot: [['mouseMoved', 522, 400], ['mousePressed', 522, 400, 1], ['mouseReleased', 522, 400, 1], ['mousePressed', 522, 400, 2], ['mouseReleased', 522, 400, 2]]}),
    c('5_nho_tai_lai', {truoc: mo, chuot: keo(512, 552), tai_lai: true, truoc_sau_tai: MO('08', false)}),   // không xóa khóa: đo đúng phần nhớ
    c('6_thu', {truoc: mo, chuot: bam(479, 37)}),
    c('7_thu_tai_lai', {truoc: MO('08', false), tai_lai: true, truoc_sau_tai: MO('08', false)}),
    c('8_mo_lai', {truoc: MO('08', false), chuot: bam(276, 37)}),
    c('9_don', {truoc: mo}),
  ]; };

// M11 (P4: PD12–PD17, PD26): thanh trái – hộp bao + tâm các khối, chân, nút thu; Hiện thêm; thu gọn; cuộn khối giữa
const DO_M11 = `(async () => { ${CONG_CU} const ngu = ms => new Promise(r => setTimeout(r, ms));
  const H = q => { const e = [...document.querySelectorAll(q)].find(vis); if (!e) return null; const r = e.getBoundingClientRect(); return {hop: R(e), tam: Math.round((r['top'] + r.height / 2) * 2) / 2, tamx: Math.round((r.left + r.width / 2) * 2) / 2}; };
  const nav = document.querySelector('nav.menu'), mg = nav.querySelector('.menu-giua'), nt = nav.querySelector('.chan-menu [data-thu]');
  const tt = () => ({nav_rong: Math.round(nav.getBoundingClientRect().width), logo: H('nav.menu .logo'), logo_bt: H('nav.menu .logo-bt'), ghim: H('nav.menu [data-trang="08"]'),
    he_thong: H('nav.menu [data-nhom-nut="HỆ THỐNG"]') || H('nav.menu .nhom-ds[data-nhom="HỆ THỐNG"]'), gd: H('nav.menu .gd-sau'), chan: H('nav.menu .chan-menu'),
    ban_so: (nav.querySelector('#nav-ban-so') || {}).textContent, ban_thu_hien: vis(nav.querySelector('#nav-ban-thu')) ? nav.querySelector('#nav-ban-thu').textContent : null,
    ban_tg_hien: vis(nav.querySelector('.ban-tg')), nut: H('nav.menu .chan-menu [data-thu]'), nut_nhan: nt ? nt.getAttribute('aria-label') : null,
    giua: mg ? [mg.clientHeight, mg.scrollHeight, getComputedStyle(mg).overflowY] : null, chu_thu_gon_hien: /Thu gọn menu/.test(nav.querySelector('.chan-menu').innerText)});
  const kq = {mo: tt()};
  const gdn = nav.querySelector('[data-gd]'); if (gdn) { gdn.click(); await ngu(300); kq.hien_them = tt(); gdn.click(); await ngu(300); }
  if (mg && innerHeight <= 768) { nav.querySelectorAll('.nhom-nut').forEach(b => { if (b.getAttribute('aria-expanded') === 'false' && b.dataset.nhomNut !== 'HỆ THỐNG') b.click(); });
    if (gdn) gdn.click(); await ngu(300); const t0 = tt(); mg.scrollTop = mg.scrollHeight; await ngu(300); kq.cuon_giua = {truoc: t0, sau: tt()}; if (gdn) gdn.click(); await ngu(200); }
  nt.click(); await ngu(500); kq.thu = tt(); nt.click(); await ngu(400);
  return kq; })()`;
// M12 (P4: PD27, QĐ684): màn Cài đặt – ngăn có dòng ghi chú (Thông báo) có dải 52, ngăn Chung không dải; đáy khối = đáy chân thanh trái
const DO_M12 = n => `(async () => { ${CONG_CU} const ngu = ms => new Promise(r => setTimeout(r, ms));
  const b = document.querySelector('#cd-menu [data-tab="${n}"]:not([data-nhom])'); if (b) { b.click(); await ngu(1500); }
  const H = q => { const e = [...document.querySelectorAll(q)].find(vis); return e ? R(e) : null; };
  const mn = document.querySelector('#p09 .cd-menu'), sau = mn ? getComputedStyle(mn, '::after') : null;
  return {ngan: '${n}', co_chan: document.getElementById('p09').classList.contains('co-chan'), cd_chan: H('#cd-chan'), chu_chan: (document.getElementById('cd-chan') || {}).textContent,
    menu_sau: sau ? {cao: sau.height, ke: sau.borderTopWidth, noi_dung: sau.content} : null, khoi_menu: H('#p09 .cd-menu'), khoi_ct: H('#p09 .cd-ct'),
    chan_trai: H('nav.menu .chan-menu'), gd_dong_trong_than_hien: [...document.querySelectorAll('#p09 .cd-than .gd-dong')].filter(vis).length,
    p09_dem: getComputedStyle(document.getElementById('p09')).paddingBottom + ' / ' + getComputedStyle(document.getElementById('p09')).paddingLeft}; })()`;

// M08 (P5: PD19–PD21, QĐ680, QĐ682; CDO CUOI-b, VE0101_12): 03 thẻ nguồn AI
const DO_M08 = `(() => { ${CONG_CU}
  const the = [...document.querySelectorAll('#ds-nguonai > .the')].filter(vis);
  const so = r => [Math.round(r['top'] * 2) / 2, Math.round(r.bottom * 2) / 2];
  const dong = e => { if (!e) return null; const r = e.getBoundingClientRect(), lh = parseFloat(getComputedStyle(e).lineHeight) || parseFloat(getComputedStyle(e).fontSize) * 1.4;
    const tu = (e.innerText || '').trim().split(/\s+/).length; const sd = Math.round(r.height / lh); return {rong: Math.round(r.width), dong: sd, tu, vo_tung_tu: tu > 1 && sd >= tu}; };
  return {so_the: the.length, top: the.map(e => Math.round(e.getBoundingClientRect()['top'])), rong: the.map(e => Math.round(e.getBoundingClientRect().width)),
    cao: the.map(e => Math.round(e.getBoundingClientRect().height)),
    nut_chinh: the.map(e => { const b = e.querySelector('.chan-goi .btn-chinh'); return b && vis(b) ? so(b.getBoundingClientRect()) : null; }),
    hang_nut: the.map(e => { const b = e.querySelector(':scope > .chan-goi'); return b ? so(b.getBoundingClientRect()) : null; }),
    chi_phi: the.map(e => { const b = e.querySelector(':scope > .kv'); return b ? so(b.getBoundingClientRect()) : null; }),
    ten: the.map(e => dong(e.querySelector('.tk-dong b'))), mo_ta: the.map(e => dong(e.querySelector('.tk-dong .f1 > .t12.phu'))),
    nhan: the.map(e => { const n = e.querySelector('.tk-dong > .nhan, .tk-dong > .ttag'); return n ? so(n.getBoundingClientRect()) : null; })}; })()`;

const NOI = (...ds) => '(async () => { ' + ds.map(x => 'await ' + x + ';').join(' ') + ' })()';   // chạy lần lượt, chờ xong từng bước
export const CA = [];
for (const kho of KHO) {
  const nho = kho[0] === 1440 || kho[0] === 390;
  for (const t of MAN) {
    if (BAI.includes('M01')) CA.push({ten: 'M01_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: MO(t), cho_sau: 500, do: DO_M01, anh: false});
    if (BAI.includes('M01C')) CA.push({ten: 'M01C_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: MO(t), cho_sau: 500, do: DO_M01C, anh: false});
    if (BAI.includes('M05')) CA.push({ten: 'M05_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: MO(t), cho_sau: 500, do: DO_M05, anh: false});
    if (BAI.includes('M05D')) CA.push({ten: 'M05D_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: NOI(MO(t), CHEN(t)), cho_sau: 500, do: DO_M05, anh: false});
    if (BAI.includes('M05C')) CA.push({ten: 'M05C_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: NOI(MO(t), CHEN(t)), cho_sau: 500, do: DO_M05C, anh: false});
    if (BAI.includes('M06')) CA.push({ten: 'M06_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: MO(t), cho_sau: 500, do: DO_M06, anh: false});
    if (BAI.includes('M02')) CA.push({ten: 'M02_p' + t, kho, chedo: CHEDO, cho: 2200, truoc: NOI(MO(t), CHEN(t)), cho_sau: 500, do: DO_M02(t), anh: nho});
  }
  if (BAI.includes('M07') && !kho[2]) CA.push(...CA_M07(kho, NOI));
  if (BAI.includes('M07') && kho[2]) CA.push({ten: 'M07_390', kho, chedo: CHEDO, cho: 2200, truoc: MO('08'), cho_sau: 400, do: `(() => { const v = document.querySelector('#p08 .tc-vach'); return {vach_hien: !!v && v.getClientRects().length > 0, dai_hien: [...document.querySelectorAll('#p08 .tc-dai, [data-tc-thu]')].some(e => e.getClientRects().length > 0)}; })()`});
  if (BAI.includes('M10') && !kho[2]) CA.push({ten: 'M10_p08', kho, chedo: CHEDO, cho: 2200, truoc: NOI(MO('08'), CHEN_100), cho_sau: 400, do: DO_M10, anh: true});
  if (BAI.includes('M11') && !kho[2]) CA.push({ten: 'M11_thanh', kho, chedo: CHEDO, cho: 2200, truoc: MO('03'), cho_sau: 400, do: DO_M11, anh: kho[0] === 1440});
  if (BAI.includes('M12') && !kho[2]) for (const n of ['thongbao', 'chung']) CA.push({ten: 'M12_' + n, kho, chedo: CHEDO, cho: 2200, truoc: MO('09'), cho_sau: 600, do: DO_M12(n), anh: kho[0] === 1440});
  if (BAI.includes('M08')) CA.push({ten: 'M08_p13', kho, chedo: CHEDO, cho: 2200, truoc: MO('13'), cho_sau: 800, do: DO_M08, anh: true});
  if (BAI.includes('M03')) CA.push({ten: 'M03_p08', kho, chedo: CHEDO, cho: 2200, truoc: NOI(MO('08'), CHEN('08')), cho_sau: 500, do: DO_M03, anh: false});
}
