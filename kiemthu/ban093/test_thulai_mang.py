"""Bài kiểm QĐ593 (LOI-NANGCLI-4; anh "A. Thử lại cả 2"):
(1) nâng công cụ AI trượt do mạng / hết giờ (npm ETIMEDOUT, ECONNRESET, EAI_AGAIN, 5xx, quá 900 giây; lượt gọi ngắn hết giờ)
    → hoãn, thử lại lượt sau; tổng 03 lần trượt mạng của cùng 01 bản thì lần thứ 03 ghi hỏng; lỗi thật vẫn ghi hỏng ngay;
    hết hạn mức giữ QĐ306 (hoãn, không đếm).
(2) gỡ 2.1.332 khỏi danh sách hỏng ĐÚNG 01 lần khi lên bản sửa, chỉ đúng bản đó.
Giả tiến trình như test_y46: KHÔNG gọi npm, CLI, hãng thật.
"""
import subprocess
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.hethong.mohinh import congai, nangcli
from kiemthu.ban084 import test_y46 as y46            # nhập cả mô-đun: bộ tìm bài không chạy lại bài cũ
from kiemthu.ban092 import test_nangcli_buoc as b092


class Nen093(y46.Nen):
    def dong(self, lenhcon):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return cn.execute("SELECT thamso_tomtat, lydo_chan FROM nhatky_thaotac WHERE congcu = 'cli' AND lenhcon = ?",
                              (lenhcon,)).fetchall()
        finally:
            cn.close()

    def tt(self):
        return nangcli.doc_trangthai(self.dl)["claude"]


class KiemHoanMang(Nen093):
    def test_moi_ma_loi_mang_la_hoan(self):
        for i, ma in enumerate(("ETIMEDOUT", "ECONNRESET", "EAI_AGAIN", "E503", "E500")):
            with self.subTest(ma=ma):
                ban = f"2.1.34{i}"
                with mock.patch.object(nangcli, "_bao") as bao:
                    kq, _ = self.nang(chay=b092.ChayLoi(loi_npm=f"npm error code {ma}\nnpm error network"),
                                      npm={"ban": ban}, ngay=True)
                self.assertEqual(kq, {"kq": "hoan_mang", "ban": ban, "giu": "2.1.331", "lan": 1})
                tt = self.tt()
                self.assertNotIn(ban, tt["hong"])
                self.assertIsNone(tt["su_kien"])                 # màn Cập nhật hiện dòng "có bản … Tự nâng lúc …"
                self.assertEqual(tt["thu_mang"]["lan"], 1)
                bao.assert_not_called()                           # hoãn: không chuông

    def test_ba_lan_moi_ghi_hong(self):
        chay = b092.ChayLoi(loi_npm="npm error code ECONNRESET")
        k1, _ = self.nang(chay=chay, ngay=True)
        k2, _ = self.nang(chay=chay, ngay=True)
        k3, _ = self.nang(chay=chay, ngay=True)
        self.assertEqual([k["kq"] for k in (k1, k2, k3)], ["hoan_mang", "hoan_mang", "hong"])
        self.assertEqual(k2["lan"], 2)
        tt = self.tt()
        self.assertIn("2.1.340", tt["hong"])
        self.assertEqual(tt["su_kien"]["loai"], "hong")
        self.assertNotIn("thu_mang", tt)
        self.assertEqual(len(self.dong("hoan_mang")), 2)
        self.assertEqual(len(self.dong("loi")), 1)
        self.assertTrue(self.dong("loi")[0][1].startswith("cai_dat: ma 1: "))
        k4, _ = self.nang(chay=chay, ngay=True)
        self.assertEqual(k4["kq"], "da_hong")                    # đã hỏng thì không thử lại nữa

    def test_doi_ban_dem_lai(self):
        chay = b092.ChayLoi(loi_npm="npm error code ETIMEDOUT")
        self.nang(chay=chay, ngay=True)
        self.nang(chay=chay, ngay=True)
        kq, _ = self.nang(chay=chay, npm={"ban": "2.1.341"}, ngay=True)
        self.assertEqual((kq["kq"], kq["lan"]), ("hoan_mang", 1))

    def test_dat_sau_hoan_xoa_dem(self):
        self.nang(chay=b092.ChayLoi(loi_npm="npm error code EAI_AGAIN"), ngay=True)
        kq, _ = self.nang(ngay=True)
        self.assertEqual(kq["kq"], "dat")
        self.assertNotIn("thu_mang", self.tt())

    def test_het_gio_npm_va_goi_ngan_het_gio(self):
        kq, _ = self.nang(chay=b092.ChayLoi(het_gio=True), ngay=True)
        self.assertEqual((kq["kq"], self.tt()["thu_mang"]["buoc"]), ("hoan_mang", "cai_dat"))
        self.trang_thai.return_value = {"da_noi": True}
        with mock.patch.object(congai, "_goi_claude", side_effect=subprocess.TimeoutExpired("claude", 600)):
            kq, _ = self.nang(npm={"ban": "2.1.341"}, ngay=True)
        self.assertEqual((kq["kq"], self.tt()["thu_mang"]["buoc"]), ("hoan_mang", "goi_ngan"))

    def test_loi_that_van_hong_ngay(self):
        self.trang_thai.return_value = {"da_noi": True}
        ca = {
            "npm_eresolve": dict(chay=b092.ChayLoi(loi_npm="npm error code ERESOLVE")),
            "so_ban": dict(chay=y46.ChayGia(ban_cai="2.1.339")),
            "goi_ngan_loi_ai": dict(),
        }
        for i, (ten, kw) in enumerate(ca.items()):
            with self.subTest(ten=ten):
                with mock.patch.object(congai, "_goi_claude", side_effect=congai.LoiAI("Claude", "ngan", "x")):
                    kq, _ = self.nang(npm={"ban": f"2.1.35{i}"}, ngay=True, **kw)
                self.assertEqual(kq["kq"], "hong")
                self.assertNotIn("thu_mang", self.tt())

    def test_dang_nhap_that_bai_van_hong_ngay(self):
        self.trang_thai.return_value = {"da_noi": True}
        chay = b092.ChayLoi()
        chay.da_noi_moi = False
        kq, _ = self.nang(chay=chay, ngay=True)
        self.assertEqual(kq["kq"], "hong")

    def test_het_han_muc_giu_qd306_khong_dem(self):
        self.trang_thai.return_value = {"da_noi": True}
        with mock.patch.object(congai, "_goi_claude", side_effect=congai.HetHanMuc("het")):
            kq = [self.nang(ngay=True)[0]["kq"] for _ in range(4)]
        self.assertEqual(kq, ["hoan"] * 4)
        self.assertNotIn("2.1.340", self.tt()["hong"])


class KiemGoHongMotLan(Nen093):
    def dat(self, claude):
        d = nangcli.doc_trangthai(self.dl)
        d["claude"] = claude
        d["chatgpt"] = {"dang": None, "truoc": None, "hong": ["0.180.0"], "lan_cuoi": None, "ket_qua": None}
        nangcli.ghi_trangthai(d, self.dl)

    def test_go_dung_2_1_332_dung_01_lan(self):
        self.dat({"dang": None, "truoc": None, "hong": ["2.1.330", "2.1.332", "2.1.340"], "ket_qua": "hong",
                  "su_kien": {"loai": "hong", "luc": "2026-11-26T15:17:00+07:00", "ban": "2.1.332", "giu": "2.1.331"}})
        self.assertEqual(nangcli.go_hong_mot_lan(self.dl), [("claude", "2.1.332")])
        tt = self.tt()
        self.assertEqual(tt["hong"], ["2.1.330", "2.1.340"])          # chỉ đúng 2.1.332, không xóa cả danh sách
        self.assertIsNone(tt["su_kien"])
        self.assertEqual(tt["da_go_hong"], ["2.1.332"])
        self.assertEqual(nangcli.doc_trangthai(self.dl)["chatgpt"]["hong"], ["0.180.0"])   # gói khác không đụng
        self.assertEqual(len(self.dong("go_hong")), 1)
        d = nangcli.doc_trangthai(self.dl)                            # trượt lại 2.1.332 sau khi gỡ
        d["claude"]["hong"].append("2.1.332")
        nangcli.ghi_trangthai(d, self.dl)
        self.assertEqual(nangcli.go_hong_mot_lan(self.dl), [])        # không gỡ lần 02
        self.assertIn("2.1.332", self.tt()["hong"])
        self.assertEqual(len(self.dong("go_hong")), 1)

    def test_su_kien_ban_khac_giu_nguyen(self):
        sk = {"loai": "hong", "luc": "2026-11-27T03:00:00+07:00", "ban": "2.1.340", "giu": "2.1.331"}
        self.dat({"dang": None, "hong": ["2.1.332", "2.1.340"], "su_kien": dict(sk)})
        nangcli.go_hong_mot_lan(self.dl)
        self.assertEqual(self.tt()["su_kien"], sk)

    def test_chay_luc_khoi_dong_qua_mo_lai(self):
        self.dat({"dang": None, "hong": ["2.1.332"]})
        nangcli.mo_lai_neu_len_ban_moi("0.9.3", self.dl)
        self.assertEqual(self.tt()["hong"], [])

    def test_chua_co_muc_claude_khong_loi(self):
        self.assertEqual(nangcli.go_hong_mot_lan(self.dl), [])
        self.assertEqual(self.dong("go_hong"), [])

    def test_bam_nang_sau_khi_go_thu_lai_2_1_332(self):
        self.dat({"dang": None, "hong": ["2.1.332"]})
        nangcli.go_hong_mot_lan(self.dl)
        kq, _ = self.nang(npm={"ban": "2.1.332"}, ngay=True)
        self.assertEqual(kq["kq"], "dat")
