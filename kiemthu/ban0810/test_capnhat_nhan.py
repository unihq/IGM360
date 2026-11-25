"""Bài kiểm bản sửa lỗi 0.8.10 – lỗi ghi nhãn cập nhật (QĐ386, anh "A. Sửa ngay 0.8.10"; LOI-CN-089; CDA bản đồ 16b).

Lúc bấm, kết quả kiểm (nhớ 05 phút) ghi bản yêu cầu X; watchtower kéo `latest` là bản Y. Nguyên tắc sửa: Y ≥ X là đã lên.
03 chỗ (`antoan.kiem_sau_capnhat`, `tiendo.vao_ban_moi` / `xong`, `nangcli.chan_vi`) × 03 ca: Y > X, Y = X, Y < X (quay về,
vẫn chưa đạt); lượt quá 02 giờ không chặn nâng; lượt treo đang có trên máy chủ (X 0.8.8, Y 0.8.9) bị lượt mới ghi đè khi lên
0.8.10; giao diện không còn vòng tải lại. Không gọi CLI thật (`_kiem_cli` giả), không gọi watchtower, không mạng.
"""
import json
import shutil
import subprocess
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from kiemthu.ban079.test_y38 import NenAT
from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import antoan, capnhat, tiendo
from maychu.hethong.mohinh import nangcli

GD = Path(__file__).resolve().parents[2] / "maychu" / "web" / "giaodien"


class Nen(NenAT):
    def setUp(self):
        super().setUp()
        tiendo._NHO.update(td=None, ghi_luc=0.0)
        self.addCleanup(tiendo._NHO.update, td=None, ghi_luc=0.0)

    def luot(self, den, phut=10, tu="0.8.7"):
        """Lượt cập nhật như lúc bấm: bước 1–5 xong ở bản `tu`, yêu cầu `den`, bắt đầu cách đây `phut` phút."""
        luc = (datetime.now(MUIGIO_VN) - timedelta(minutes=phut)).isoformat(timespec="seconds")
        tiendo.bat_dau(tu, den, luc)
        for b in ("drive", "gui", "tai"):
            tiendo.sang(b)
        antoan.ghi(None, yeu_cau={"tu": tu, "den": den, "luc": luc, "drive": False})
        tiendo._NHO["td"] = None                                       # bản mới là tiến trình khác: đọc từ tệp

    def chay(self, ban):
        return mock.patch.object(capnhat, "ban_dang_chay", return_value=ban)

    def kiem(self):
        with mock.patch.object(antoan, "_kiem_cli", return_value=True):
            return antoan.kiem_sau_capnhat(True)

    def f04_tiendo(self):
        cn = ketnoi.mo("Nhatky")
        try:
            return [d[0] for d in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE lenhcon = 'tiendo' ORDER BY luc")]
        finally:
            cn.close()


class KiemBaChoBaCa(Nen):
    def test_y_lon_hon_x_dat(self):                                     # ca máy chủ 25/11: yêu cầu 0.8.8, lên 0.8.9
        self.luot("0.8.8")
        with self.chay("0.8.9"):
            self.assertIsNone(nangcli.chan_vi())                       # không chặn nâng công cụ AI
            self.assertTrue(tiendo.vao_ban_moi("0.8.9"))               # nối lượt, sang bước 7
            kq = self.kiem()
            self.assertTrue(kq["diem"]["ban"])                         # điểm "bản" đạt
            self.assertEqual((kq["dat"], kq["tong"]), (6, 6))
            td = tiendo.doc()
            self.assertTrue(td.get("xong"))                            # lượt đóng
            self.assertEqual((td["den"], td["den_yc"]), ("0.8.9", "0.8.8"))   # CDA 16b: bản thật đã lên, giữ bản yêu cầu
            self.assertIn("0.8.7 → 0.8.9 (yêu cầu 0.8.8) · ", self.f04_tiendo()[0])
            self.assertEqual(tiendo.hien()["phan_tram"], 100)
            self.assertIsNone(nangcli.chan_vi())

    def test_y_bang_x_nhu_cu(self):
        self.luot("0.8.9")
        with self.chay("0.8.9"):
            self.assertTrue(tiendo.vao_ban_moi("0.8.9"))
            kq = self.kiem()
            self.assertTrue(kq["diem"]["ban"])
            td = tiendo.doc()
            self.assertTrue(td.get("xong"))
            self.assertNotIn("den_yc", td)
            dong = self.f04_tiendo()
            self.assertIn("0.8.7 → 0.8.9 · ", dong[0])
            self.assertNotIn("yêu cầu", dong[0])

    def test_y_nho_hon_x_quay_ve_van_chua_dat(self):
        self.luot("0.8.9")
        with self.chay("0.8.8"):
            self.assertEqual(nangcli.chan_vi(), "dang_cap_nhat")       # lượt còn hiệu lực, bản chạy thấp hơn: vẫn chặn
            self.assertFalse(tiendo.vao_ban_moi("0.8.8"))
            kq = self.kiem()
            self.assertFalse(kq["diem"]["ban"])                        # vẫn "chưa lên đúng bản"
            self.assertIn(antoan.TEN_DIEM["ban"], kq["loi"])
            self.assertFalse(tiendo.doc().get("xong"))                 # lượt không đóng
            self.assertEqual(self.f04_tiendo(), [])

    def test_so_ban_hai_chu_so(self):                                   # 0.8.10 > 0.8.9 (so từng phần số, không so chữ)
        self.assertTrue(tiendo.da_len("0.8.10", "0.8.9"))
        self.assertFalse(tiendo.da_len("0.8.9", "0.8.10"))
        self.assertTrue(tiendo.da_len("0.9.0", "0.8.10"))
        self.assertTrue(tiendo.da_len("0.8.9", None))


class KiemChanNang(Nen):
    def test_luot_qua_02_gio_khong_chan_nang(self):
        self.luot("0.8.9", phut=tiendo.TOI_DA_LUOT_GIAY // 60 + 1)
        with self.chay("0.8.8"):
            self.assertIsNone(nangcli.chan_vi())                       # lượt treo cũ không chặn mãi
            self.assertTrue(tiendo.hien()["treo"])

    def test_luot_con_hieu_luc_van_chan(self):
        self.luot("0.8.9", phut=tiendo.TOI_DA_LUOT_GIAY // 60 - 10)
        with self.chay("0.8.8"):
            self.assertEqual(nangcli.chan_vi(), "dang_cap_nhat")


class KiemLuotTreoMayChu(Nen):
    """Máy chủ đang có lượt treo (tu 0.8.7, den 0.8.8, bước 5, bản chạy 0.8.9). Lên 0.8.10: lượt mới ghi đè, không chặn."""
    def test_len_0810_ghi_de_luot_treo(self):
        self.luot("0.8.8", phut=30)
        with self.chay("0.8.9"):
            self.assertIsNone(nangcli.chan_vi())                       # mã 0.8.10 đọc lượt treo này: không chặn nâng
            self.assertFalse(capnhat.dang_cho())                       # lần cập nhật sau không bị chặn
            luc = tiendo._bay()
            tiendo.bat_dau("0.8.9", "0.8.10", luc)                     # bước 1 của lần bấm lên 0.8.10 (capnhat.yeu_cau)
            td = tiendo.doc()
            self.assertEqual((td["tu"], td["den"], td["bat_dau"]), ("0.8.9", "0.8.10", luc))   # ghi đè lượt treo
            for b in ("gui", "tai"):
                tiendo.sang(b)
            antoan.ghi(None, yeu_cau={"tu": "0.8.9", "den": "0.8.10", "luc": luc, "drive": False})
            tiendo._NHO["td"] = None
        with self.chay("0.8.10"):
            self.assertTrue(tiendo.vao_ban_moi("0.8.10"))
            kq = self.kiem()
            self.assertTrue(kq["diem"]["ban"])
            self.assertTrue(tiendo.doc().get("xong"))
            self.assertIsNone(nangcli.chan_vi())


@unittest.skipUnless(shutil.which("node"), "máy không có node")
class KiemGiaoDien(unittest.TestCase):
    """app.js 481: lượt có `den` thấp hơn bản đang chạy không còn gọi choCapNhat (vòng tải lại mỗi 05 giây)."""
    @classmethod
    def setUpClass(cls):
        a = (GD / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
        cls.app = a
        cls.so = a[a.index("const caSo = "):a.index("const daLen = ")] + a[a.index("const daLen = "):a.index("\n", a.index("const daLen = ")) + 1]
        i = a.index("  const t = d.tien_do;   // QĐ253")
        cls.chon = a[i:a.index("\n", a.index("theoKiem();   // QĐ258", i)) + 1]

    def chay(self, den, dang, buoc="tai", treo=False):
        ma = (self.so + "let goi = [];\nconst choCapNhat = (tu, den) => goi.push('cho:' + den), theoKiem = () => goi.push('kiem');\n"
              "function veCN(d, sl, S) {\n" + self.chon + "}\n"
              "veCN({ban_dang: " + json.dumps(dang) + ", tien_do: {tu: '0.8.7', den: " + json.dumps(den) + ", buoc: "
              + json.dumps(buoc) + ", treo: " + json.dumps(treo) + "}}, {}, {cn: 'moinhat'});\nconsole.log(JSON.stringify(goi));")
        r = subprocess.run(["node", "-e", ma], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_den_thap_hon_ban_chay_khong_tai_lai(self):
        self.assertEqual(self.chay("0.8.8", "0.8.9"), [])             # lượt treo máy chủ 25/11: không gọi choCapNhat
        self.assertEqual(self.chay("0.8.9", "0.8.10"), [])
        self.assertEqual(self.chay("0.8.9", "0.8.9", "nang"), ["kiem"])   # máy chủ đã ghi den = bản thật: theo kiểm như cũ

    def test_ban_cu_con_chay_van_hien_tien_do(self):
        self.assertEqual(self.chay("0.8.9", "0.8.8"), ["cho:0.8.9"])   # bản cũ còn chạy: hiện tiếp tiến độ như nay
        self.assertEqual(self.chay("0.8.9", "0.8.8", treo=True), [])  # lượt treo: không theo

    def test_chi_nhanh_ban_cu_con_chay_doi(self):
        self.assertNotIn("t.den !== d.ban_dang", self.app)                # 481: so số bản, hết vòng tải lại
        self.assertEqual(self.app.count("daLen(d.ban_dang, "), 1)
        for giu in ("tdk.den === d.ban_dang", "else if ((dangLuot && t.den === d.ban_dang) || sl.keoDrive) theoKiem();",
                    "const co = !!(e && t && t.den === d.ban_dang"):   # 443, 481, 496 giữ: máy chủ ghi den = bản thật
            self.assertIn(giu, self.app)


if __name__ == "__main__":
    unittest.main()
