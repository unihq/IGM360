"""Bài kiểm 0.10.1 phần P0 – lỗi đã gặp ở 0.10.0 thành bài kiểm tự chặn cả LOẠI lỗi (QĐ681 (4)).

G01 trùng tên lớp CSS (.tb-dong, .md-chip) · G02 khai báo JS trùng / dùng trước khi khai (CHU_MD, svgLucide) ·
G03 (= PD25) câu lỗi 02 dấu chấm · G07 cụm 03 nút nổi đè nút (L14 a) · G08 vùng cuộn sai chỗ (L14 b, c) ·
G09 lớp của #app có 02 chủ. G04 (tràn, cắt), G05 (vùng bấm nhỏ), G06 (yêu cầu bị bỏ sót) không bắt được bằng đọc mã:
đo bằng trình duyệt và bằng phiếu dựng ở ngoài kho.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"

# Mốc main 0.10.0: 13 lớp đã có >= 02 luật trần (".ten{" cấp ngoài cùng) – số luật được phép giữ, không thêm
TRUNG_CO_SAN = {"btn-chu": 2, "cg-mg": 2, "cg-onhap": 2, "cham-xanh": 2, "chip": 2, "gd-sau": 2, "lk": 2, "logo-o": 2,
                "nhom": 2, "o-nhap": 2, "tc-nhap": 2, "thanh-tren": 2, "the": 3}
# Mốc main 0.10.0: tên lớp đang dùng (CSS hoặc mã vẽ) mà CHƯA có luật trần – luật trần mới không được lấy lại các tên này
# (lỗi .tb-dong 0.10.0: hộp báo mới đặt luật trần ".tb-dong{…}" trùng tên dòng của bảng chuông → bảng chuông vỡ)
KHONG_TRAN_CO_SAN = set((
    "a ai an-dt an-mb b bang-gs bat be bong-cau c c-loi c-xong canh canh2 cd-con cd-ct cd-menu cd-td chay che "
    "chi-chua chi-dt chinh cho chon chua cl5 cls cn-dang cn-moi co-trang cu cuon d1 d2 d3 dang dat dia dien-thoai "
    "do do-v dom dong-li dong-tu dt dt-cho dung duong4 dv gap gd-sau0 giot go-tk hat huy jpg k-luc kb kb-ai kb-gan "
    "kb-giua kb-hang kb-mat kb-trang kb-vat kb-xa keo kh4 khau-hieu khoa khung-logo kk-dau kx kx-bay kx-cuoi kx-dau "
    "kx-sk lb logo-bt logo-chu logo-giua logo-ngang loi lon lucide lucide-arrow-down-wide-narrow lucide-arrow-up "
    "lucide-badge-check lucide-blocks lucide-book-key lucide-bot-message-square lucide-brain-circuit "
    "lucide-calendar lucide-chevron-down lucide-chevron-left lucide-chevron-right lucide-circle-alert "
    "lucide-circle-check lucide-clock-alert lucide-cloud-download lucide-database lucide-eye-off lucide-filter "
    "lucide-gauge lucide-inbox lucide-info lucide-layers lucide-layout-dashboard lucide-layout-grid "
    "lucide-list-checks lucide-loader lucide-lock lucide-lock-keyhole lucide-log-out lucide-menu "
    "lucide-message-square-plus lucide-messages-square lucide-panel-left-close lucide-plus "
    "lucide-rectangle-ellipsis lucide-refresh-cw lucide-rotate-ccw lucide-search lucide-settings "
    "lucide-shield-check lucide-sliders-horizontal lucide-sparkles lucide-square lucide-upload lucide-user-round "
    "lucide-wifi-off lucide-wrench lucide-x lv lv-canh lv-cau lv-cham lv-dat lv-goc lv-mat lv-nguoi lv-o lv-vai "
    "lv-xanh m m-cuoi m-lo m-thuong ma-lenh man2 mat-truoc mb md-ns mdHet menu mh-ds mh-hop mh-phu mh-vang mi-cuoi "
    "mi-lo mi-thang mi-thuong mini mo moi mui nay nd3 nen nen-doi nen-gan nen-giua nen-lop nen-xa ng nh nho "
    "nho-bang nho3 nhom-bao nhom-ds nhom-mt nhom-nut nhom-ten on org phu-de pt0 qd qd-goc qd1 qd2 r rieng ro rong "
    "rong-mb sai sai-ma sk sk-dt tat tay tay-phai tay-trai tb-dong tb-ds ten the-dau the-doi thu tieu-de tin tn-noi "
    "toi trong v1 vai-phai vai-trai vang vang-ngoai vong-lon vong-nho w3 x xam xem xem-v xong "
).split())
# Tên được phép dùng lại có chủ ý (ghi lý do): hiện chưa có
CHO_PHEP_DUNG_LAI = {}


def doc_css(html):
    """Trả [(bộ chọn, số dòng)] của mọi luật cấp ngoài cùng trong các thẻ <style> (bỏ chú thích, giữ số dòng)."""
    kq = []
    for m in re.finditer(r"<style>(.*?)</style>", html, re.S):
        goc = html[:m.start(1)].count("\n")
        css = re.sub(r"/\*.*?\*/", lambda x: "\n" * x.group(0).count("\n"), m.group(1), flags=re.S)
        sau, bat = 0, 0
        for k, ch in enumerate(css):
            if ch == "{":
                if sau == 0:
                    for s in css[bat:k].split(","):
                        kq.append((s.strip(), goc + css[:k].count("\n") + 1))
                sau += 1
            elif ch == "}":
                sau -= 1
                if sau == 0:
                    bat = k + 1
            elif ch == ";" and sau == 0:
                bat = k + 1
    return kq


def luat_tran(html):
    ds = {}
    for s, d in doc_css(html):
        if re.fullmatch(r"\.[A-Za-z0-9_-]+", s):
            ds.setdefault(s[1:], []).append(d)
    return ds


def quy_tac(html):
    """[(bộ chọn đầy đủ, thân luật)] của mọi luật không lồng (đủ cho luật trong @media)."""
    css = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.S))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


class G01KhongTrungLop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_g01_moi_lop_toi_da_mot_luat_tran(self):
        thua = {k: v for k, v in luat_tran(self.html).items() if len(v) > TRUNG_CO_SAN.get(k, 1)}
        self.assertEqual(thua, {}, "lớp có thêm luật trần thứ 02 (dễ đè luật cũ ở chỗ khác): {tên: [dòng]}")

    def test_g01_luat_tran_moi_khong_lay_ten_dang_dung(self):
        lay = sorted(k for k in luat_tran(self.html) if k in KHONG_TRAN_CO_SAN and k not in CHO_PHEP_DUNG_LAI)
        self.assertEqual(lay, [], "luật trần mới đặt cho tên lớp đang dùng ở chỗ khác – đổi tên lớp mới")

    def test_g01_bai_bat_duoc_loi_cu(self):   # chứng minh bài kiểm bắt đúng 02 lỗi đã gặp
        cu = self.html.replace("</style>", ".md-chip{color:red}.tb-dong{width:1px}</style>", 1)
        self.assertIn("md-chip", {k for k, v in luat_tran(cu).items() if len(v) > TRUNG_CO_SAN.get(k, 1)})
        self.assertIn("tb-dong", {k for k in luat_tran(cu) if k in KHONG_TRAN_CO_SAN})


class G02KhaiBaoJs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_g02_node_doc_duoc(self):
        r = subprocess.run(["node", "--check", str(GD / "app.js")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_g02_ten_dau_dong_khong_trung(self):
        ten = re.findall(r"^(?:async function|function|const|let)\s+([A-Za-z_$][\w$]*)", self.js, re.M)
        self.assertEqual(sorted({t for t in ten if ten.count(t) > 1}), [])

    @staticmethod
    def dung_truoc_khai(js):
        dong = js.split("\n")
        mau = r"^(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
        ham = re.compile(mau)
        dinh_nghia = re.compile(r"^(?:async\s+)?function\b|" + mau)
        loi = []
        for i, l in enumerate(dong):
            m = ham.match(l)
            if not m:
                continue
            x = re.compile(r"(?<![\w.$])" + re.escape(m.group(1)) + r"\(")
            for j in range(i):
                t = dong[j]
                if t and t[0] not in " \t})/*" and not dinh_nghia.match(t) and x.search(t):
                    loi.append((m.group(1), j + 1, i + 1))
        return loi

    def test_g02_khong_goi_ham_truoc_khi_khai(self):   # lỗi svgLucide 0.10.0: gọi ở cấp ngoài cùng trước dòng khai
        self.assertEqual(self.dung_truoc_khai(self.js), [], "(tên, dòng gọi, dòng khai)")

    def test_g02_bai_bat_duoc_loi_cu(self):
        gia = "ICON.x = veX('a');\nfunction f() { return veX('b'); }\nconst veX = t => t;\n"
        self.assertEqual(self.dung_truoc_khai(gia), [("veX", 1, 3)])


class G03MotDauCham(unittest.TestCase):   # = PD25 (F8 CPO chốt): 01 cách thêm dấu chấm duy nhất là cau()
    @classmethod
    def setUpClass(cls):
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_g03_pd25_khong_tu_them_dau_cham(self):
        self.assertEqual(re.findall(r"e\.message \+ '\.'", self.js), [])
        self.assertGreaterEqual(self.js.count("cau(e.message)"), 29)

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_g03_pd25_cau_chi_them_khi_thieu(self):
        a = self.js
        ham = a[a.index("const cau = "):a.index("\n", a.index("const cau = "))]
        thu = "['A', 'A.', 'A?', 'A!', 'A\\u2026', 'A. ']"
        r = subprocess.run(["node", "-e", ham + "\nconsole.log(JSON.stringify(" + thu + ".map(cau)));"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["A.", "A.", "A?", "A!", "A…", "A. "])


class G07G08G09(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (GD / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.js = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.qt = quy_tac(cls.html)

    def test_g07_cum_nut_khong_noi_tren_may_tinh(self):   # L14 (a): .vi-tri absolute đè nút "Thêm nguồn AI"
        noi = [x for s, b in self.qt for x in s.split(",") if re.search(r"\.vi-tri$", x.strip())
               and ".mb" not in x.replace(":not(.mb)", "") and re.search(r"position:\s*(absolute|fixed)", b)]
        self.assertEqual(noi, [])

    def test_g08_dau_man_va_o_nhap_khong_trong_vung_cuon(self):   # L14 (b), (c)
        self.assertTrue('<div class="dau-man" id="dau-man"></div>' in self.html, "thiếu ô đầu màn ngoài vùng cuộn")
        self.assertTrue("function datDauMan() {" in self.js, "thiếu hàm datDauMan")
        than = [b for s, b in self.qt if s == "#app:not(.mb) #p08 .tc-than"]
        self.assertTrue(than and "overflow-y:auto" in than[-1], than)
        day = [b for s, b in self.qt if s == ".tc-day"]
        self.assertTrue(day and "flex:none" in day[-1], day)

    def test_g09_lop_cua_app_mot_cho_gan(self):   # lớp tự thêm vào #app bị ve() ghi đè (app.className = …)
        self.assertEqual(len(re.findall(r"\bapp\.className\s*=", self.js)), 1)
        self.assertEqual(re.findall(r"(?:\$\('#app'\)|\bapp)\.classList\.(?:add|toggle|remove)", self.js), [])


if __name__ == "__main__":
    unittest.main()
