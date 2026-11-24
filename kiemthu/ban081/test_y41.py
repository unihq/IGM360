"""Bài kiểm 0.8.1 (Y41; QĐ249, QĐ251): thẻ Cập nhật.

Phần 1 (GAP-080): `choCapNhat` hỏi /suckhoe nhiều lần; bản đổi thì tải lại trang; quá giờ thì báo hỏng.
(0.7.9–0.8.0: câu `const het` bị nối vào chú thích nên vòng hỏi dừng sau 01 lần, thẻ quay mãi.)
Phần 2 (QĐ251, CDA phương án B): tiến độ 08 bước ở khoá phụ `tien_do` của tệp trạng thái; 01 dòng F04 tóm tắt mỗi lượt;
đủ 05 điều kiện CDA (qua antoan.ghi, ≤ 01 lần/giây, ghi lỗi không chặn, bản 0.7.9 đọc được, không ghi đôi dòng tóm tắt).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"
MA_079 = Path(__file__).resolve().parent / "ma_079"

# Môi trường giả cho choCapNhat: đồng hồ ảo, hàng đợi hẹn giờ, /suckhoe trả bản theo kịch bản
NEN_JS = r"""
let T = 0, hen = [], hoi = 0, taiLai = 0;
const S = {}, D = {capnhat: {}}, CHU_CN = {sao: {tai: 'Bước 2/2 · Đang tải bản '}, cho: 'cho'};
const phan = {textContent: ''}, $ = () => phan;
const tieuDangCn = () => {}, ve = () => {}, veQuayVe = () => {}, moHopDrive = () => {};
const location = {reload: () => { taiLai++; }};
const dongHo = {now: () => T};
const hai = n => (Number.isInteger(n) && n >= 0 && n < 10) ? '0' + n : String(n);
const setTimeout = (f, ms) => { hen.push({luc: T + ms, f}); };
const fetch = async () => ({json: async () => { hoi++; return {phienban: KICH_BAN(hoi)}; }});
const api = async () => ({dang_sao: 'tai'});
"""
CHAY_JS = r"""
(async () => {
  choCapNhat('0.8.0', '0.8.1');
  for (let i = 0; i < 2000 && hen.length; i++) {
    hen.sort((a, b) => a.luc - b.luc); const h = hen.shift(); T = h.luc; await h.f();
  }
  console.log(JSON.stringify({hoi, taiLai, cn: S.cn, phut: Math.round(T / 60e3), lydo: phan.textContent}));
})().catch(e => console.log(JSON.stringify({loi: String(e)})));
"""


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemChoCapNhat(unittest.TestCase):
    def chay(self, kich_ban: str) -> dict:
        js = (GD / "app.js").read_text(encoding="utf-8").split("\n")
        a = next(i for i, x in enumerate(js) if x.startswith("function choCapNhat("))
        b = next(i for i in range(a, len(js)) if js[i] == "}")
        ham = "\n".join(js[a:b + 1]).replace("Date.now()", "dongHo.now()")
        ma = NEN_JS + f"const KICH_BAN = {kich_ban};\n" + ham + CHAY_JS
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "cho.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        kq = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertNotIn("loi", kq, kq)
        return kq

    def test_ban_doi_thi_tai_lai_trang(self):
        kq = self.chay("n => n < 25 ? '0.8.0' : '0.8.1'")             # 24 lần còn bản cũ (khoảng 02 phút), lần 25 có bản mới
        self.assertEqual((kq["hoi"], kq["taiLai"]), (25, 1))
        self.assertEqual(kq["cn"], "dangcn")

    def test_qua_gio_thi_bao_hong(self):
        kq = self.chay("n => '0.8.0'")                                # không bao giờ lên bản mới
        self.assertEqual((kq["taiLai"], kq["cn"]), (0, "hong"))
        self.assertGreater(kq["hoi"], 400)                            # hỏi suốt 35 phút (mỗi 05 giây), không dừng sau 01 lần
        self.assertEqual(kq["phut"], 35)                              # QĐ255 điểm 1: chờ 35 phút
        self.assertEqual(kq["lydo"], "Lý do: sau 35 phút máy chủ vẫn chạy bản 0.8.0. Phần mềm vẫn chạy bình thường bằng bản này.")

    def test_so_phut_va_so_ban_theo_bien(self):
        """QĐ255 điểm 1, 2: số phút, số bản không viết cứng; trang không còn ngưỡng 60 phút riêng (máy chủ trả cờ treo)."""
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("sau 35 phút", js)
        self.assertNotIn("60 * 60e3", js)
        self.assertIn("!t.treo", js)

    def test_khong_con_khai_bao_nam_trong_chu_thich(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        for dong in js.split("\n"):
            if "//" in dong:
                self.assertNotRegex(dong.split("//", 1)[1], r"\b(const|let) het\b", dong)


# ---------------- Phần 3: thẻ "Đang cập nhật" hiện % 08 bước (QĐ253, bản vẽ Z18) ----------------
def _ma_the() -> str:
    """Mã chạy được trong node: icon.js, 04 hàm phụ thật của app.js, khối <TD8> và choCapNhat."""
    js = (GD / "app.js").read_text(encoding="utf-8")
    dong = js.split("\n")
    phu = [x for x in dong if x.startswith(("const hai =", "const esc =", "const icoMau ="))]
    khoi = js[js.index("// <TD8>"):js.index("// </TD8>")]
    a = next(i for i, x in enumerate(dong) if x.startswith("function choCapNhat("))
    b = next(i for i in range(a, len(dong)) if dong[i] == "}")
    icon = (GD / "icon.js").read_text(encoding="utf-8").replace("const ICON=", "var ICON=", 1)
    return icon + "\n" + "\n".join(phu) + "\nconst cum = s => esc(s);\n" + khoi + "\n".join(dong[a:b + 1]).replace("Date.now()", "dongHo.now()")


T0 = "2026-11-24T10:00:00+07:00"
DU = {"o_trong": 1, "chup": 20, "drive": 0, "gui": 2, "tai": 300, "khoidong": 15, "nang": 30, "kiem": 40}


def _td(buoc, giay_moc: dict, **them) -> dict:
    """Tiến độ mẫu: giay_moc = {bước: số giây tính từ T0}."""
    from datetime import datetime, timedelta
    g = datetime.fromisoformat(T0)
    moc = {k: (g + timedelta(seconds=v)).isoformat() for k, v in giay_moc.items()}
    return {"buoc": buoc, "moc": moc, "du_kien": DU, "tu": "0.2.0", "den": "0.3.0", "bat_dau": T0, "luc": T0, "chi_tiet": {}, **them}


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemTheTienDo(unittest.TestCase):
    def node(self, ma: str) -> dict:
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "the.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def the(self, td: dict, giay: float, **o) -> dict:
        nen = "const CHU_CN = {kiem: 'Kiểm sau cập nhật: '};\n"
        chay = (f"const td = {json.dumps(td, ensure_ascii=False)};\n"
                f"const o = {{...{json.dumps(o, ensure_ascii=False)}, bay: Date.parse('{T0}') + {giay} * 1000}};\n"
                "console.log(JSON.stringify({html: htmlTienDo(td, o), r: tinhTienDo(td, o.bay)}));\n")
        kq = self.node(_ma_the() + nen + chay)
        self.assertNotIn("undefined", kq["html"])                       # Y41c: chữ thiếu (khoá TD8 bị nuốt vào chú thích)
        return kq

    def test_dang_chay_buoc_2_so_do_that(self):
        k = self.the(_td("chup", {"o_trong": 0, "chup": 2}, chi_tiet={"da": 4, "tong": 7}), 8, cu="0.2.0")
        h = k["html"]
        for chu in ("Đang cập nhật lên 0.3.0", "<b>Bước 2/8:</b> Chụp dữ liệu · 04/07 tệp", "Đã chạy 00:08 · còn khoảng",
                    "phút (ước tính)", "Trang tự tải lại khi xong. Bạn không cần bấm gì thêm.", "04/07 tệp</span>",
                    "lucide-loader", "stroke=\"#1456F0\"", "1. Kiểm ổ trống</span><span class=\"td8-m\">00:02"):
            self.assertIn(chu, h)
        self.assertEqual(h.count("td8-dong"), 8)
        self.assertNotIn("data-cnngay", h)

    def test_buoc_5_uoc_tinh(self):
        k = self.the(_td("tai", {"o_trong": 0, "chup": 1, "gui": 21, "tai": 23}), 23 + 100)
        h = k["html"]
        self.assertIn("<b>Bước 5/8:</b> Tải gói cài (ước tính)", h)
        self.assertIn("5. Tải gói cài</span><span class=\"td8-m\">ước tính", h)
        self.assertIn("3. Bản sao Drive</span><span class=\"td8-m\">chưa nối Drive", h)   # Drive chưa nối: bỏ qua, % cộng ngay (QĐ255 điểm 3)
        self.assertFalse(k["r"]["cham"])

    def test_lau_hon_uoc_tinh(self):
        td = _td("tai", {"o_trong": 0, "chup": 1, "gui": 21, "tai": 23})
        chua = self.the(td, 23 + 1.9 * 300)["r"]
        self.assertFalse(chua["cham"])                                  # dưới 02 lần thời gian dự kiến: vẫn ước tính
        k = self.the(td, 23 + 2.1 * 300)
        h, r = k["html"], k["r"]
        self.assertTrue(r["cham"])
        for chu in ("Tải gói cài (ước tính) lâu hơn thường lệ", "chưa ước tính được thời gian còn lại",
                    "Phần mềm vẫn đang chờ. Bạn không cần bấm gì thêm.", "lâu hơn ước tính</span>", "lucide-clock", "#8F5F00"):
            self.assertIn(chu, h)
        tong = sum(DU.values())
        self.assertLessEqual(r["pt"], int(100 * (23 + 0.95 * 300) / tong))   # % dừng dưới mức cuối của bước 5
        self.assertEqual(r["pt"], self.the(td, 23 + 9 * 300)["r"]["pt"])      # để lâu nữa vẫn đứng yên

    def test_loi_buoc_2_co_nut_thu_lai(self):
        td = _td("chup", {"o_trong": 0, "chup": 2}, chi_tiet={"da": 1, "tong": 7}, loi="chup", loi_ct="tệp Bot",
                 loi_luc="2026-11-24T10:00:15+07:00")
        h = self.the(td, 600, cu="0.2.0")["html"]
        for chu in ("Chưa cập nhật được lên 0.3.0", "<b>Dừng ở bước 2/8:</b> Chụp dữ liệu chưa được (tệp Bot)", "Đã chạy 00:15<",
                    "Chưa gửi lệnh cập nhật nên bản 0.2.0 và dữ liệu giữ nguyên. Lỗi ghi vào nhật ký.", "data-cnngay",
                    "Thử lại</button>", "lucide-circle-alert", "chưa được</span>", "#E22E28"):
            self.assertIn(chu, h)
        self.assertNotIn("còn khoảng", h)

    def test_drive_qua_10_phut(self):
        td = _td("drive", {"o_trong": 0, "chup": 2, "drive": 11}, chi_tiet={"da": 2, "tong": 5})
        h = self.the(td, 612, quaGio=True)["html"]
        for chu in ("<b>Bước 3/8:</b> Bản sao Drive quá 10 phút, chờ bạn chọn", "Đã chạy 10:12<", "Bạn chọn ở hộp đang mở.",
                    "quá 10 phút</span>", "lucide-clock"):
            self.assertIn(chu, h)

    def test_xong(self):
        td = _td("xong", {"o_trong": 0, "chup": 2, "gui": 11, "tai": 12, "khoidong": 200, "nang": 230, "kiem": 352},
                 xong="2026-11-24T10:05:58+07:00")
        k = self.the(td, 999, kiem={"chu": "06/06 đạt", "dat": True})
        h = k["html"]
        for chu in ("Đã lên bản 0.3.0", "<b>Xong 08/08 bước</b> · Kiểm sau cập nhật: 06/06 đạt", "Tổng thời gian 05:58",
                    "Trang tự tải lại sau 03 giây.", ">100%<", "8. Kiểm sau cập nhật</span><span class=\"td8-m\">00:06",
                    "5. Tải gói cài</span><span class=\"td8-m\">xong"):
            self.assertIn(chu, h)
        self.assertEqual(h.count("td8-dong xong"), 7)                     # bước 3: chưa nối Drive (QĐ255 điểm 3)

    def test_drive_chua_noi_va_chua_len_het(self):
        """QĐ255 điểm 3: bước 3 bỏ qua dùng circle-minus xám; Drive chưa nối / Vẫn cập nhật khi quá giờ."""
        moc = {"o_trong": 0, "chup": 2, "gui": 11, "tai": 12}
        h = self.the(_td("tai", moc), 100)["html"]
        self.assertIn('lucide-circle-minus', h)
        self.assertIn('<div class="td8-dong cho">', h.split("3. Bản sao Drive")[0][-1200:])
        self.assertIn("3. Bản sao Drive</span><span class=\"td8-m\">chưa nối Drive", h)
        moc2 = {"o_trong": 0, "chup": 2, "drive": 11, "gui": 640, "tai": 641}
        h2 = self.the(_td("tai", moc2, drive={"da": 2, "tong": 5}), 700)["html"]
        self.assertIn("3. Bản sao Drive</span><span class=\"td8-m\">chưa lên hết", h2)
        h3 = self.the(_td("tai", moc2, drive={"da": 5, "tong": 5}), 700)["html"]
        self.assertIn("3. Bản sao Drive</span><span class=\"td8-m\">10:29", h3)    # lên đủ: ghi thời gian
        self.assertNotIn("lucide-circle-minus", h3)

    def test_loi_buoc_4_ly_do_ngan_hoac_bo_ngoac(self):
        """QĐ255 điểm 4: hết lặp chữ "Gửi lệnh cập nhật chưa được (Chưa gửi được lệnh cập nhật)"."""
        moc = {"o_trong": 0, "chup": 2, "gui": 11}
        h = self.the(_td("gui", moc, loi="gui", loi_ct="máy chủ cập nhật không trả lời", loi_luc=T0), 20)["html"]
        self.assertIn("<b>Dừng ở bước 4/8:</b> Gửi lệnh cập nhật chưa được (máy chủ cập nhật không trả lời)", h)
        h2 = self.the(_td("gui", moc, loi="gui", loi_luc=T0), 20)["html"]
        self.assertIn("<b>Dừng ở bước 4/8:</b> Gửi lệnh cập nhật chưa được</div>", h2)

    def test_xong_ma_kiem_chua_dat(self):
        """QĐ255 điểm 5: "Xong 08/08 bước" giữ xanh lá; phần kiểm sau cập nhật chưa đạt đỏ + circle-alert."""
        td = _td("xong", {"o_trong": 0, "chup": 2, "gui": 11, "tai": 12, "nang": 230, "kiem": 352},
                 xong="2026-11-24T10:05:58+07:00")
        h = self.the(td, 999, kiem={"chu": "05/06 · lịch chạy nền chưa bật", "dat": False})["html"]
        self.assertIn('<div class="td-buoc" style="color:#258832"><b>Xong 08/08 bước</b> · <span style="color:#E22E28">', h)
        do = h.split('<span style="color:#E22E28">', 1)[1].split("</span>", 1)[0]
        self.assertIn("lucide-circle-alert", do)
        self.assertIn("Kiểm sau cập nhật: 05/06 · lịch chạy nền chưa bật", do)
        h2 = self.the(td, 999, kiem={"chu": "06/06 đạt", "dat": True})["html"]
        self.assertNotIn('<span style="color:#E22E28">', h2)

    def luong(self, kich_ban: str) -> dict:
        """Chạy choCapNhat với /suckhoe, /api/capnhat theo kịch bản (n: lần hỏi thứ n; null = máy chủ không trả lời)."""
        nen = r"""
let T = 0, hen = [], hoi = 0, taiLai = [], ve_ = 0;
const S = {}, D = {capnhat: {}}, CHU_CN = {kiem: 'Kiểm sau cập nhật: ', sao: {tai: 'Bước 2/2 · Đang tải bản '}, cho: 'cho'};
const phan = {textContent: '', innerHTML: '', dataset: {}, classList: {toggle() {}, remove() {}}};
const $ = () => phan;
const tieuDangCn = () => {}, ve = () => {}, veQuayVe = () => {}, moHopDrive = () => {};
const location = {reload: () => { taiLai.push(T); }};
const dongHo = {now: () => T};
const setTimeout = (f, ms) => { hen.push({luc: T + ms, f}); };
""" + kich_ban + r"""
const fetch = async () => { hoi++; const b = BAN(hoi); if (!b) throw new Error('mất kết nối'); return {json: async () => ({phienban: b})}; };
const api = async () => { const s = CN(hoi); if (!s) throw new Error('mất kết nối'); return s; };
(async () => {
  choCapNhat('0.2.0', '0.3.0');
  for (let i = 0; i < 3000 && hen.length; i++) { hen.sort((a, b) => a.luc - b.luc); const h = hen.shift(); T = h.luc; await h.f(); }
  console.log(JSON.stringify({hoi, taiLai, cn: S.cn, html: phan.innerHTML, con: hen.length, phut: Math.round(T / 60e3), lydo: phan.textContent}));
})().catch(e => console.log(JSON.stringify({loi: String(e)})));
"""
        kq = self.node(_ma_the() + nen)
        self.assertNotIn("loi", kq, kq)
        return kq

    def test_luong_ban_moi_chay_buoc_7_8_roi_xong_tu_tai_lai(self):
        cu, moi = (json.dumps(_td(b, m, **x), ensure_ascii=False) for b, m, x in (
            ("tai", {"o_trong": 0, "chup": 1, "gui": 21, "tai": 23}, {}),
            ("kiem", {"o_trong": 0, "chup": 1, "gui": 21, "tai": 23, "nang": 200, "kiem": 230}, {"chi_tiet": {"da": 3, "tong": 6}})))
        xong = json.dumps(_td("xong", {"o_trong": 0, "chup": 1, "gui": 21, "tai": 23, "nang": 200, "kiem": 230},
                              xong="2026-11-24T10:04:30+07:00"), ensure_ascii=False)
        kq = self.luong(f"""
const BAN = n => n <= 3 ? '0.2.0' : n <= 6 ? null : '0.3.0';      // 03 lần bản cũ · 03 lần đang thay bản · bản mới
const CN = n => n <= 3 ? {{dang_sao: 'tai', tien_do: {cu}}} : n <= 6 ? null : n <= 8 ? {{tien_do: {moi}}}
  : {{tien_do: {xong}, kiem_hien: {{chu: '06/06 đạt', dat: true}}}};
""")
        self.assertEqual(kq["hoi"], 9)
        self.assertEqual(len(kq["taiLai"]), 1)                           # tải lại đúng 01 lần
        self.assertEqual(kq["taiLai"][0], 9 * 5000 + 3000)                # sau khi hiện "xong" 03 giây
        self.assertIn("Xong 08/08 bước", kq["html"])
        self.assertEqual(kq["con"], 0)                                    # dừng hỏi

    def test_luong_loi_dung_hoi_va_hien_thu_lai(self):
        loi = json.dumps(_td("chup", {"o_trong": 0, "chup": 2}, loi="chup", loi_ct="tệp Bot", loi_luc=T0), ensure_ascii=False)
        kq = self.luong(f"""
const BAN = n => '0.2.0';
const CN = n => n < 2 ? {{dang_sao: 'chup', tien_do: {loi}}} : {{dang_sao: null, sao_loi: 'chưa chụp được', tien_do: {loi}}};
""")
        self.assertEqual((kq["hoi"], kq["taiLai"], kq["cn"], kq["con"]), (2, [], "dangcn", 0))
        self.assertIn("data-cnngay", kq["html"])

    # Y41d (CDA N6): 35 phút tính từ bước 5; bước 3, 4 theo giới hạn riêng (Drive 10 phút + chờ bạn chọn, chờ việc AI 30 phút)
    TD_DONG = f"""
const G0 = Date.parse('{T0}'), P = 60e3;
const TD = (buoc, moc, them) => ({{buoc, du_kien: {json.dumps(DU)}, tu: '0.2.0', den: '0.3.0', bat_dau: '{T0}', chi_tiet: {{}},
  luc: new Date(G0 + T).toISOString(), moc: Object.fromEntries(Object.entries(moc).map(([k, v]) => [k, new Date(G0 + v * P).toISOString()])), ...them}});
"""

    def test_luong_cho_viec_ai_25_phut_roi_tai_20_phut_khong_bao_hong(self):
        kq = self.luong(self.TD_DONG + """
const BAN = n => T < 45 * P ? '0.2.0' : '0.3.0';
const CN = n => T < 25 * P ? {dang_sao: 'cho_viec', tien_do: TD('gui', {o_trong: 0, chup: 0, gui: 0.5})}
  : T < 45 * P ? {dang_sao: 'tai', tien_do: TD('tai', {o_trong: 0, chup: 0, gui: 0.5, tai: 25})}
  : {tien_do: TD('xong', {o_trong: 0, chup: 0, gui: 0.5, tai: 25, nang: 44, kiem: 44.5}, {xong: new Date(G0 + 45 * P).toISOString()}),
     kiem_hien: {chu: '06/06 đạt', dat: true}};
""")
        self.assertNotEqual(kq["cn"], "hong")                            # cách cũ (35 phút từ lúc bấm) báo hỏng ở phút 35
        self.assertEqual(len(kq["taiLai"]), 1)
        self.assertIn("Xong 08/08 bước", kq["html"])

    def test_luong_tai_qua_35_phut_thi_bao_hong(self):
        kq = self.luong(self.TD_DONG + """
const BAN = n => '0.2.0';
const CN = n => T < 25 * P ? {dang_sao: 'cho_viec', tien_do: TD('gui', {o_trong: 0, chup: 0, gui: 0.5})}
  : {dang_sao: 'tai', tien_do: TD('tai', {o_trong: 0, chup: 0, gui: 0.5, tai: 25})};
""")
        self.assertEqual((kq["cn"], kq["taiLai"], kq["con"]), ("hong", [], 0))
        self.assertEqual(kq["phut"], 25 + 35)                            # 35 phút tính từ bước 5
        self.assertEqual(kq["lydo"], "Lý do: sau 35 phút máy chủ vẫn chạy bản 0.2.0. Phần mềm vẫn chạy bình thường bằng bản này.")

    def test_luong_cho_ban_chon_drive_khong_bao_hong(self):
        kq = self.luong(self.TD_DONG + """
const BAN = n => T < 50 * P ? '0.2.0' : '0.3.0';
const CN = n => T < 10 * P ? {dang_sao: 'day', tien_do: TD('drive', {o_trong: 0, chup: 0, drive: 0.2}, {chi_tiet: {da: 1, tong: 5}})}
  : T < 45 * P ? {dang_sao: 'qua_gio', tien_do: TD('drive', {o_trong: 0, chup: 0, drive: 0.2}, {chi_tiet: {da: 1, tong: 5}})}
  : T < 50 * P ? {dang_sao: 'tai', tien_do: TD('tai', {o_trong: 0, chup: 0, drive: 0.2, gui: 45, tai: 45})}
  : {tien_do: TD('xong', {o_trong: 0, chup: 0, drive: 0.2, gui: 45, tai: 45, nang: 49}, {xong: new Date(G0 + 50 * P).toISOString()})};
const moHopDrive = () => {};
""".replace("const moHopDrive = () => {};", ""))
        self.assertNotEqual(kq["cn"], "hong")                            # chờ bạn chọn 35 phút: không tính giờ
        self.assertEqual(len(kq["taiLai"]), 1)

    def test_luong_may_chu_khong_co_tien_do_van_nhu_cu(self):
        kq = self.luong("const BAN = n => n < 3 ? '0.2.0' : '0.3.0';\nconst CN = n => ({dang_sao: 'tai'});\n")
        self.assertEqual((kq["hoi"], len(kq["taiLai"])), (3, 1))         # bản 0.8.0 trở về trước: tải lại ngay như cũ


# ---------------- Phần 2: tiến độ 08 bước ----------------
class NenTD(unittest.TestCase):
    def setUp(self):
        from maychu.dulieu import khoitao
        from maychu.hethong import capnhat, tiendo
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.g = Path(self.tam.name)
        self.dl = self.g / "dulieu"
        self.dl.mkdir()
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            "IGM360_CLAUDE_CLI": str(self.g / "khong_co_cli_claude"),
                                            "IGM360_CODEX_CLI": str(self.g / "khong_co_cli_codex")})
        bien.start()
        self.addCleanup(bien.stop)
        khoitao.tao_het(self.dl)
        tiendo._NHO.update(td=None, ghi_luc=0.0)
        self.addCleanup(tiendo._NHO.update, td=None, ghi_luc=0.0)
        nhip = mock.patch.object(tiendo, "NHIP_GHI_GIAY", 0.0)   # bài kiểm nhịp ghi đặt lại 01 giây riêng
        nhip.start()
        self.addCleanup(nhip.stop)
        cu = dict(capnhat._SAO)
        self.addCleanup(lambda: (capnhat._SAO.clear(), capnhat._SAO.update(cu)))

    def f04(self, lenhcon: str) -> list:
        from maychu.dulieu import ketnoi
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return [r[0] for r in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'capnhat'"
                                             " AND lenhcon = ? ORDER BY luc", (lenhcon,))]
        finally:
            cn.close()


class KiemTienDo(NenTD):
    def test_buoc_1_den_5_ban_dang_chay(self):
        from maychu.dulieu import maso
        from maychu.hethong import capnhat, tiendo
        with mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.8.9"}), \
                mock.patch.object(capnhat, "cap_nhat_ngay", return_value={"ok": True}), \
                mock.patch("maychu.ketnoi.drive.dang_noi", return_value=False):
            self.assertTrue(capnhat.yeu_cau(maso.tao(), "ngay", thumuc=self.dl, van_capnhat=True)["ok"])
            het = time.time() + 30
            while capnhat._SAO["buoc"] != "tai" and time.time() < het:
                time.sleep(0.1)
        self.assertEqual(capnhat._SAO["buoc"], "tai")
        td = tiendo.doc(self.dl)
        self.assertEqual(td["den"], "0.8.9")
        self.assertEqual([b for b in tiendo.BUOC if b in td["moc"]], ["o_trong", "chup", "gui", "tai"])   # Drive chưa nối: 0 bước 3
        self.assertEqual(td["chi_tiet"]["chup"], {"da": 7, "tong": 7, "xong": True})            # số thật: 07/07 tệp
        h = tiendo.hien(self.dl)
        self.assertEqual((h["buoc"], h["so_buoc"], h["uoc_tinh"]), ("tai", 5, True))            # bước 5 là ước tính
        self.assertTrue(0 < h["phan_tram"] < 100)

    def test_buoc_6_den_8_ban_moi_va_dong_f04(self):
        from maychu.hethong import tiendo
        luc = tiendo._bay()                                            # Y41b: lượt mới (quá 02 giờ là lượt treo, không nối)
        tiendo.bat_dau("0.8.0", "0.8.9", luc, self.dl)
        for b in ("gui", "tai"):
            tiendo.sang(b, self.dl)
        tiendo._NHO["td"] = None                                       # bản mới là tiến trình khác: đọc từ tệp
        self.assertFalse(tiendo.vao_ban_moi("0.8.8", self.dl))         # lượt không phải của bản này
        self.assertTrue(tiendo.vao_ban_moi("0.8.9", self.dl))
        self.assertIn("khoidong", tiendo.doc(self.dl)["moc"])
        tiendo.chi_tiet("nang", self.dl, da=7, tong=7, xong=True)
        tiendo.sang("kiem", self.dl, da=0, tong=6)
        self.assertEqual(tiendo.hien(self.dl)["so_buoc"], 8)
        tiendo.chi_tiet("kiem", self.dl, da=6, tong=6, xong=True)
        tiendo.xong("0.8.9", self.dl)
        tiendo.xong("0.8.9", self.dl)                                  # gọi lại không ghi đôi
        tiendo._ghi_f04(tiendo.doc(self.dl), self.dl)                  # ghi thẳng lần nữa: vẫn 01 dòng
        dong = self.f04("tiendo")
        self.assertEqual(len(dong), 1)
        for k in ("0.8.0 → 0.8.9", "o_trong=", "chup=", "gui=", "tai_khoidong=", "nang=", "kiem=", "tong=",
                  "bat_dau=" + luc):
            self.assertIn(k, dong[0])
        self.assertEqual(tiendo.hien(self.dl)["phan_tram"], 100)

    def test_lan_kiem_khong_do_cap_nhat_khong_dung(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.xong("0.8.7", self.dl)                                  # bản khác: không kết thúc lượt
        self.assertFalse(tiendo.doc(self.dl).get("xong"))
        self.assertEqual(self.f04("tiendo"), [])

    def test_trong_so_tu_f04_cac_lan_truoc(self):
        from maychu.hethong import capnhat, tiendo
        self.assertEqual(tiendo.trong_so(self.dl), {k: float(v) for k, v in tiendo.MAC_DINH_GIAY.items()})   # lần đầu: mặc định
        for i, (tk, ng) in enumerate(((200, 40), (400, 60))):
            capnhat._ghi_f04("tiendo", f"0.8.{i} → 0.8.{i + 1} · o_trong=1 chup=10 gui=2 tai_khoidong={tk} nang={ng} kiem=40"
                                       f" · tong=0 giây · bat_dau=2026-11-2{i}T10:00:00+07:00", "dat", thumuc=self.dl)
        du = tiendo.trong_so(self.dl)
        self.assertEqual((du["nang"], du["chup"], du["kiem"]), (50.0, 10.0, 40.0))
        self.assertEqual(du["tai"] + du["khoidong"], 300.0)            # trung bình (200 + 400) / 2
        self.assertEqual(du["khoidong"], float(tiendo.MAC_DINH_GIAY["khoidong"]))
        self.assertEqual(du["drive"], float(tiendo.MAC_DINH_GIAY["drive"]))   # bước chưa có số: mặc định

    def test_luot_treo_khong_noi_lai(self):
        """Y41b N1: lượt cũ treo (bắt đầu quá 02 giờ) thì bản mới không nối lại, không ghi dòng F04 sai."""
        from datetime import datetime, timedelta
        from maychu.dulieu.saoluu import MUIGIO_VN
        from maychu.hethong import tiendo
        cu = (datetime.now(MUIGIO_VN) - timedelta(seconds=tiendo.TOI_DA_LUOT_GIAY + 60)).isoformat(timespec="seconds")
        tiendo.bat_dau("0.8.0", "0.8.9", cu, self.dl)
        tiendo.sang("tai", self.dl)
        tiendo._NHO["td"] = None
        self.assertFalse(tiendo.vao_ban_moi("0.8.9", self.dl))
        self.assertIsNone(tiendo.doc(self.dl))                         # bỏ lượt treo khỏi tệp trạng thái
        tiendo.xong("0.8.9", self.dl)
        self.assertEqual(self.f04("tiendo"), [])
        vua = (datetime.now(MUIGIO_VN) - timedelta(seconds=tiendo.TOI_DA_LUOT_GIAY - 600)).isoformat(timespec="seconds")
        tiendo.bat_dau("0.8.0", "0.8.9", vua, self.dl)                 # lượt dài nhưng còn trong 02 giờ: vẫn nối
        tiendo.sang("tai", self.dl)
        tiendo._NHO["td"] = None
        self.assertTrue(tiendo.vao_ban_moi("0.8.9", self.dl))

    def test_trong_so_bo_gia_tri_bat_thuong(self):
        """Y41b N1: số CDA thử (bước kiểm 255.255 giây) và lượt quá 02 giờ không làm lệch thời gian dự kiến."""
        from maychu.hethong import capnhat, tiendo
        dong = ("o_trong=1 chup=10 gui=2 tai_khoidong=200 nang=40 kiem=40 · tong=293",
                "o_trong=1 chup=10 gui=2 tai_khoidong=400 nang=60 kiem=255255 · tong=255728",    # lượt treo: bỏ cả dòng
                "o_trong=1 chup=12 gui=1800 tai_khoidong=300 nang=50 kiem=999 · tong=3162",      # gửi lệnh gồm 30 phút chờ việc AI
                "o_trong=1 chup=14 drive=4000 gui=4 tai_khoidong=500 nang=60 kiem=60 · tong=4639")  # Drive gồm lúc chờ bạn chọn
        for i, d in enumerate(dong):
            capnhat._ghi_f04("tiendo", f"0.8.{i} → 0.8.{i + 1} · {d} giây · bat_dau=2026-11-2{i}T10:00:00+07:00", "dat",
                             thumuc=self.dl)
        du = tiendo.trong_so(self.dl)
        self.assertEqual(du["kiem"], 50.0)                             # (40 + 60) / 2: bỏ 255255 và 999
        self.assertEqual(du["gui"], 3.0)                               # (2 + 4) / 2: bỏ 1800
        self.assertEqual(du["drive"], float(tiendo.MAC_DINH_GIAY["drive"]))   # 4000 vượt trần: chưa có số hợp lệ
        self.assertEqual(du["chup"], 12.0)                             # (10 + 12 + 14) / 3
        self.assertAlmostEqual(du["tai"] + du["khoidong"], 1000 / 3, places=0)
        self.assertNotIn("tong", du)

    def test_hien_so_do_that_va_uoc_tinh(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.chi_tiet("chup", self.dl, da=3, tong=7)
        h = tiendo.hien(self.dl)
        self.assertEqual((h["so_buoc"], h["uoc_tinh"], h["chi_tiet"]), (2, False, {"da": 3, "tong": 7}))   # có số đo thật
        tiendo.sang("nang", self.dl)
        h2 = tiendo.hien(self.dl)
        self.assertEqual((h2["so_buoc"], h2["uoc_tinh"]), (7, True))   # bước 7 chưa có số đo: ước tính theo giờ
        self.assertGreater(h2["phan_tram"], h["phan_tram"])
        tiendo.loi("tai", self.dl)
        self.assertEqual(tiendo.hien(self.dl)["loi"], "tai")

    def test_nhip_ghi_toi_da_01_lan_moi_giay(self):
        from maychu.hethong import antoan, tiendo
        with mock.patch.object(tiendo, "NHIP_GHI_GIAY", 1.0), mock.patch.object(antoan, "ghi", wraps=antoan.ghi) as g:
            tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)   # ghi 01
            t0 = time.monotonic()
            for i in range(1, 6):
                tiendo.chi_tiet("chup", self.dl, da=i, tong=7)         # không bắt buộc: trong 01 giây thì bỏ qua
            self.assertEqual(g.call_count, 1)
            tiendo.sang("gui", self.dl)                                # bắt buộc: chờ đủ 01 giây rồi ghi
            self.assertGreaterEqual(time.monotonic() - t0, 0.9)
            self.assertEqual(g.call_count, 2)
        self.assertEqual(tiendo.doc(self.dl)["chi_tiet"]["chup"]["da"], 5)   # số mới nhất trong bộ nhớ được ghi kèm

    def test_ghi_loi_khong_chan(self):
        from maychu.hethong import antoan, tiendo
        with mock.patch.object(antoan, "ghi", side_effect=OSError("đĩa giả lỗi")):
            tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
            tiendo.sang("gui", self.dl)
            tiendo.xong("0.8.9", self.dl)
        self.assertIsNone(tiendo.doc(self.dl))

    def test_co_treo_tu_may_chu(self):
        """QĐ255 điểm 2 (CDA N5-B): hien() trả cờ treo theo cùng ngưỡng 02 giờ của máy chủ."""
        from datetime import datetime, timedelta
        from maychu.dulieu.saoluu import MUIGIO_VN
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        self.assertFalse(tiendo.hien(self.dl)["treo"])
        cu = (datetime.now(MUIGIO_VN) - timedelta(seconds=tiendo.TOI_DA_LUOT_GIAY + 60)).isoformat(timespec="seconds")
        tiendo.bat_dau("0.8.0", "0.8.9", cu, self.dl)
        self.assertTrue(tiendo.hien(self.dl)["treo"])

    def test_loi_gui_lenh_ghi_ly_do_ngan(self):
        """QĐ255 điểm 4: thiếu mã cập nhật / máy chủ cập nhật không trả lời."""
        import httpx
        from maychu.dulieu import maso
        from maychu.hethong import capnhat, tiendo
        for gia, ngan in ((None, "thiếu mã cập nhật"), (httpx.ConnectError("giả"), "máy chủ cập nhật không trả lời")):
            tiendo._NHO.update(td=None, ghi_luc=0.0)
            capnhat._SAO.update(buoc=None, loi=None)
            env = {"WATCHTOWER_TOKEN": ""} if gia is None else {"WATCHTOWER_TOKEN": "khoa-gia-kiem-thu"}
            with mock.patch.dict(os.environ, env),                     mock.patch.object(capnhat, "kiem_tra", return_value={"co_ban_moi": True, "ban_moi": "0.8.9"}),                     mock.patch("maychu.ketnoi.drive.dang_noi", return_value=False),                     mock.patch("httpx.post", side_effect=gia):
                capnhat.yeu_cau(maso.tao(), "ngay", thumuc=self.dl, van_capnhat=True)
                het = time.time() + 30
                while not capnhat._SAO["loi"] and time.time() < het:
                    time.sleep(0.1)
                time.sleep(0.3)
            td = tiendo.doc(self.dl)
            self.assertEqual((td["buoc"], td["loi"], td.get("loi_ct")), ("gui", "gui", ngan))

    def test_api_tra_tien_do(self):
        from maychu.hethong import tiendo
        from maychu.web import api
        self.assertIsNone(api._tien_do())
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        self.assertEqual(api._tien_do()["buoc"], "chup")
        with mock.patch.object(tiendo, "hien", side_effect=ValueError("giả lỗi")):
            self.assertIsNone(api._tien_do())                          # đọc lỗi không chặn màn

    def test_chay_ghi_moc_khoi_dong(self):
        from maychu import chay
        from maychu.hethong import tiendo
        g = self.g / "app"
        g.mkdir()
        (g / "VERSION").write_text("0.8.9", encoding="utf-8")
        tiendo.bat_dau("0.8.0", "0.8.9", tiendo._bay(), self.dl)
        tiendo.sang("tai", self.dl)
        chay.moc_khoidong(self.dl, self.g / "khac")                    # ảnh khác bản: không ghi
        self.assertNotIn("khoidong", tiendo.doc(self.dl)["moc"])
        chay.moc_khoidong(self.dl, g)
        td = tiendo.doc(self.dl)
        self.assertEqual((td["buoc"], "khoidong" in td["moc"]), ("khoidong", True))
        chay.moc_khoidong(self.g / "khong_co", g)                      # không có tệp: bỏ qua, không lỗi

    def test_khoi_dong_ban_moi_ghi_buoc_7_va_ket_thuc(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.7.9", khoidong.PHIENBAN, tiendo._bay(), self.dl)
        tiendo.sang("tai", self.dl)
        tiendo._NHO["td"] = None
        with TestClient(khoidong.app) as c:
            c.get("/suckhoe")
        td = tiendo.doc(self.dl)
        self.assertIn("nang", td["moc"])
        self.assertTrue(td.get("xong"))                                # lịch tắt: không chạy kiểm, kết thúc sau bước 7
        self.assertEqual(len(self.f04("tiendo")), 1)


class KiemWatchtower30Phut(unittest.TestCase):
    """QĐ252: watchtower chờ lệnh cập nhật tối đa 30 phút; chỉ đặt ở dịch vụ watchtower, không đụng dịch vụ igm360."""

    def test_dong_compose(self):
        dc = (GOC / "docker-compose.yml").read_text(encoding="utf-8")
        wt = dc[dc.index("\n  watchtower:"):]
        self.assertIn("\n      WATCHTOWER_HTTP_API_UPDATE_TIMEOUT: 30m\n", wt)
        self.assertEqual(dc.count("WATCHTOWER_HTTP_API_UPDATE_TIMEOUT:"), 1)


class KiemBan079DocDuoc(NenTD):
    """Điều kiện CDA: bản quay về 0.7.9 gặp tệp trạng thái có khoá phụ `tien_do` vẫn chạy và không làm mất khoá."""

    def nap(self, ten: str):
        spec = importlib.util.spec_from_file_location(f"ma079_{ten}", MA_079 / f"{ten}_079.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_antoan_079_giu_khoa_tien_do(self):
        from maychu.hethong import tiendo
        tiendo.bat_dau("0.8.1", "0.8.2", tiendo._bay(), self.dl)
        cu = self.nap("antoan")
        self.assertEqual(cu.doc(self.dl)["tien_do"]["den"], "0.8.2")
        cu.ghi(self.dl, kiem_ban="0.7.9")                              # 0.7.9 ghi mục của nó
        self.assertEqual(tiendo.doc(self.dl)["den"], "0.8.2")

    def test_chay_079_chon_va_giu_khoa(self):
        from maychu.hethong import antoan, tiendo
        tiendo.bat_dau("0.8.1", "0.8.2", tiendo._bay(), self.dl)
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "khac", "ban_truoc": "0.8.1"})   # cờ lệch ảnh: 0.7.9 bỏ cờ, ghi lại tệp
        cu = self.nap("chay")
        g = self.g / "app"
        g.mkdir()
        self.assertEqual(cu.chon(self.dl, g), g)
        tt = antoan.doc(self.dl)
        self.assertNotIn("chay_ban_truoc", tt)
        self.assertEqual(tt["tien_do"]["den"], "0.8.2")


if __name__ == "__main__":
    unittest.main()
