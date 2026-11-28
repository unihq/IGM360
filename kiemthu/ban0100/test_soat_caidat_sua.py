"""Bài kiểm 0.10.0 – bản sửa lỗi trong phạm vi: CDO SOAT-CAIDAT (5.361) P1-1, P1-2, P2, P3-1..3; QA lượt 04 (c) tạm tắt chỉ
kêu tin đỏ mới xuất hiện (CDA phiếu 06 mục 14.1), (d) chặn "Thêm khóa" ở máy chủ tới 0.12.0 (QĐ287, QĐ608, mục 14.2)."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"


def _dong(js: str, dau: str) -> str:
    i = js.index(dau)
    return js[i:js.index("\n", i)]


class KiemGiaoDien(unittest.TestCase):
    def setUp(self):
        self.h = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        self.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_p1_1_cum_cuoi_thanh_trai_dinh_day(self):
        self.assertIn("#app:not(.mb) nav.menu .gd-sau{margin-top:auto}", self.h)
        self.assertIn('#app.thu:not(.mb) nav.menu .nhom-ds[data-nhom="HỆ THỐNG"]{margin-top:auto', self.h)   # thu gọn: .gd-sau ẩn – QĐ671 (1)(2) (0.10.1): bỏ nút "Thu gọn menu", HỆ THỐNG ghim đáy
        # quy tắc đè (0.9.0) đứng trước quy tắc sửa – cùng độ ưu tiên thì quy tắc sau thắng
        self.assertLess(self.h.index("#app:not(.mb) nav.menu .muc{margin:0 8px;"), self.h.index("#app:not(.mb) nav.menu .gd-sau{margin-top:auto}"))

    def test_qd556_co_chu_thanh_trai(self):   # QA B06, CDO 5.373: Quychuan dòng 117
        self.assertIn(".nhom,#app:not(.mb) .nhom-nut{font-size:13px}", self.h)
        self.assertIn("#app:not(.mb) nav.menu .gd-sau{margin-left:12px;margin-right:12px}#app:not(.mb) nav.menu .gd-nut{font-size:13px;font-weight:600}", self.h)
        self.assertLess(self.h.index("#app:not(.mb) .nhom-nut{display:flex"), self.h.index(".nhom,#app:not(.mb) .nhom-nut{font-size:13px}"))   # đứng sau luật cũ 11 px

    def test_qa_b11_chan_thanh_trai(self):   # QĐ566 (1), QĐ408: "IGM360 {bản} · by UNI TECH", mở trang công nghệ ở thẻ mới
        trang = "https://" + "tech." + "unihq" + ".vn/igm360"   # ghép lúc chạy: chuỗi trang công khai chỉ có ngoại lệ máy quét ở index.html
        self.assertIn('<a class="nav-ban" id="nav-ban" href="' + trang + '" target="_blank" rel="noopener noreferrer"><span class="ban-so" id="nav-ban-so"></span><span class="ban-tg">by UNI TECH</span></a>', self.h)   # QĐ671 (1) (0.10.1): 02 dòng
        self.assertIn("$('#nav-ban-so').textContent = 'IGM360 ' + D.tbBan;", self.js)   # số bản từ /api/demso (VERSION); QĐ671 (1): dòng 2 "by UNI TECH"
        self.assertIn(".thu .nav-ban,.mb .nav-ban{display:none}", self.h)

    def test_qa_c08_o_ngay_khong_tran(self):
        self.assertIn(".kk-h{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,.9fr) 88px 112px 118px 132px;", self.h)
        self.assertIn("@media (max-width:1279px){\n .kk-h{grid-template-columns:minmax(0,1fr) auto auto;", self.h)
        self.assertIn("#app:not(.mb) #ds-phien .hang{grid-template-columns:1fr 1fr!important;", self.h)

    def test_qa_b08_mot_dau_cham(self):
        from maychu.hethong.caidat import thongso
        self.assertFalse(thongso.CHU_TRAN_SAI.endswith("."))   # giao diện tự thêm "." (bao(e.message + '.'))
        self.assertFalse(thongso.CHU_LUON_BAO.endswith("."))

    def test_lop_moi_khong_trung_lop_cu(self):   # bài học .tb-dong (CDO 5.372): lớp ngăn Mức dùng không dùng lại .md-chip của màn 13
        i = self.h.index("/* Ngăn Mức dùng (DM-CAIDAT-010)")
        self.assertNotIn(".md-chip{", self.h[i:self.h.index(".mb .md-onhap", i)])
        self.assertIn(".md-nhan{", self.h)

    def test_p1_2_p2_p3_1(self):
        self.assertIn("#p09 .the.cn{display:grid;grid-template-columns:72px minmax(0,1fr);", self.h)    # cột vòng cố định, không nở
        self.assertIn(".mb #p09 .the.cn{padding:16px;gap:12px 16px;grid-template-columns:56px minmax(0,1fr)}", self.h)
        self.assertIn("#p09 .cd-td>.phu{margin:0}", self.h)                                             # khối tiến độ 142 (QĐ574)
        self.assertIn(".mb #p09 :is(.btn,.btn-chu,.cg-onhap,.o-nhap,.mg-o){min-height:44px}", self.h)

    def test_p1_3_nut_con_truc_tiep_cua_the_va_ket_khoa_44(self):   # CDO 5.364
        self.assertIn(" #p09 .the.cn>.btn{grid-column:2;justify-self:start}", self.h)              # "Cập nhật ngay", "Thử cập nhật lại"
        self.assertIn(".mb #p09 .the.cn>.cn-nut,.mb #p09 .the.cn>.btn{grid-column:1/-1}", self.h)  # 390: không bị ép vào cột vòng 56
        self.assertIn(".mb #p09 .kk-ba{width:44px;height:44px}.mb #tha-kk .tha-muc{min-height:44px}", self.h)

    def test_p3_2_khong_trong_goi_lo_lung(self):
        self.assertIn("caCum(x.trong_goi ? (x.ban ? CA.oGoi(x.ban) : '–') : x.ban)", self.js)


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemChayJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    def chay(self, ma: str):
        ra = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(ra.returncode, 0, ra.stderr)
        return json.loads(ra.stdout)

    def test_c_tam_tat_chi_keu_tin_do_moi_xuat_hien(self):
        ma = _dong(self.js, "const canKeu = ") + """
const S = (...m) => new Set(m);
console.log(JSON.stringify([
  canKeu(S('d1'), [{id: 'd1', moi: true, muc: 'do'}, {id: 'v1', moi: true, muc: 'xem'}], true),   // đỏ cũ + vàng mới, tạm tắt
  canKeu(S('v0'), [{id: 'v0', moi: true, muc: 'xem'}, {id: 'd2', moi: true, muc: 'do'}], true),   // đỏ mới, tạm tắt
  canKeu(S('a'), [{id: 'b', moi: true, muc: 'tin'}], false),                                         // 01 tin đóng + 01 tin mở: số giữ nguyên
  canKeu(undefined, [{id: 'b', moi: true, muc: 'do'}], false),                                       // lần tải đầu
  canKeu(S(), [{id: 'b', moi: false, muc: 'do'}], false)                                             // đã đọc
]));"""
        self.assertEqual(self.chay(ma), [False, True, True, False, False])

    def test_p3_3_lan_kiem_toi_qua_gio_kiem(self):
        ma = ("const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);\n"
              "const CA = {homNay: 'hôm nay', ngayMai: 'ngày mai'};\n"
              "const caVn = t => new Date(t + 7 * 3600 * 1000).toISOString().slice(0, 19);\n"   # giả múi +7 cho bài kiểm
              + _dong(self.js, "const caKiemTiep = ") + """
const b = s => Date.parse(s);
console.log(JSON.stringify([
  caKiemTiep({kiem_ngay: '2026-11-26', gio_kiem: 3}, b('2026-11-27T02:30:00+07:00')),   // chưa tới 03:00, chưa kiểm hôm nay
  caKiemTiep({kiem_ngay: '2026-11-26', gio_kiem: 3}, b('2026-11-27T22:30:00+07:00')),   // đã qua 03:00 (máy tắt / lịch chưa chạy)
  caKiemTiep({kiem_ngay: '2026-11-27', gio_kiem: 3}, b('2026-11-27T22:30:00+07:00'))    // đã kiểm hôm nay
]));""")
        self.assertEqual(self.chay(ma), ["03:00 hôm nay", "03:00 ngày mai", "03:00 ngày mai"])


class KiemThemKhoaChan(unittest.TestCase):
    def test_d_chan_o_may_chu(self):
        src = (GOC / "maychu/web/api.py").read_text(encoding="utf-8")
        self.assertIn("THEM_KHOA_MO = False", src)
        i = src.index('@router.post("/kekhoa")')
        self.assertIn("if not THEM_KHOA_MO:\n        raise HTTPException(400, CHU_THEM_KHOA_CHAN)", src[i:i + 300].replace("\r\n", "\n"))


if __name__ == "__main__":
    unittest.main()
