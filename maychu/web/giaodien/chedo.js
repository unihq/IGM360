// QĐ562, QĐ411 (0.10.0): chế độ màu Sáng · Tối · Theo hệ thống. Lựa chọn lưu theo máy (CDA 16o mục 3 A): chưa chọn
// = Theo hệ thống (theo cài đặt sáng / tối của máy, đổi theo khi máy đổi). Tệp nạp trong <head> trước khi vẽ để không
// nháy nền sáng. Bản Tối: lớp `toi` trên thẻ <html> (biến màu ở index.html), logo nền tối (QĐ588).
(function () {
  var KHOA = 'igm360_chedo';
  var may = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function doc() {
    try { var x = localStorage.getItem(KHOA); return x === 'sang' || x === 'toi' ? x : 'hethong'; } catch (e) { return 'hethong'; }
  }
  function laToi(c) { return c === 'toi' || (c === 'hethong' && !!(may && may.matches)); }
  function logo(toi) {
    var ds = document.querySelectorAll('img.logo-ngang, img.logo-giua');
    for (var i = 0; i < ds.length; i++) ds[i].src = '/tainguyen/logo/' + (toi ? 'igm360_ngang_toi.svg' : 'igm360_ngang.svg');
  }
  function ap() { var toi = laToi(doc()); document.documentElement.classList.toggle('toi', toi); logo(toi); }
  window.CHEDO = {
    doc: doc,
    dat: function (c) {
      try { if (c === 'sang' || c === 'toi') localStorage.setItem(KHOA, c); else localStorage.removeItem(KHOA); } catch (e) { /* máy chặn lưu: chỉ áp lần này */ }
      ap();
    }
  };
  ap();
  if (may) { if (may.addEventListener) may.addEventListener('change', ap); else if (may.addListener) may.addListener(ap); }
  document.addEventListener('DOMContentLoaded', ap);
})();
