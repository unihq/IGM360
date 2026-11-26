"""Bài kiểm LOI-NANGCLI-2 (bản sửa lỗi; CPO đồng ý ý (1), loại sửa lỗi QĐ259).

Lỗi: nâng Claude · Code 2.1.332 trên máy chủ báo "kiểm thử chưa đạt" mà F04 không cho biết bước nào trượt (nangcli.py
bb4699d dòng 350–351 nối 04 bước bằng `and`, dòng 341 xóa luôn nhật ký npm, dòng 366 chỉ ghi câu chung).
Sửa: ghi bước trượt (cai_dat | so_ban | dang_nhap | goi_ngan) + đoạn cuối câu lỗi (đã che mã dài hạn, tối đa 200 ký tự)
vào cột `lydo_chan` của dòng F04 và `su_kien.buoc` trong trangthai.json. Chữ dòng F04, chữ giao diện giữ nguyên; 0 lược đồ.
Giả tiến trình như test_y46: KHÔNG gọi npm, CLI, hãng thật.
"""
import json
import subprocess
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.hethong.mohinh import congai, nangcli
from kiemthu.ban084 import test_y46 as y46   # nhập cả mô-đun: bộ tìm bài không chạy lại bài của test_y46

MA = "sk-ant-oat01-" + "A" * 40   # mã dài hạn giả, phải bị che


class ChayLoi(y46.ChayGia):
    """npm trả mã thoát 1 và câu lỗi có lẫn mã dài hạn; `auth status` in email ra stdout."""

    def __init__(self, loi_npm=None, het_gio=False, **kw):
        super().__init__(**kw)
        self.loi_npm, self.het_gio = loi_npm, het_gio

    def __call__(self, lenh, **kw):
        if lenh[0] == "npm" and self.het_gio:
            raise subprocess.TimeoutExpired(lenh, 900)
        if lenh[0] == "npm" and self.loi_npm:
            super().__call__(lenh, **kw)
            return subprocess.CompletedProcess(lenh, 1, "", self.loi_npm)
        if lenh[1:] == ["auth", "status", "--json"] and not getattr(self, "da_noi_moi", True):
            self.lenh.append(lenh)
            return subprocess.CompletedProcess(lenh, 1, json.dumps({"loggedIn": False, "email": "ten" + chr(64) + "mien"}), "het phien")
        return super().__call__(lenh, **kw)


class KiemBuocTruot(y46.Nen):
    def lydo(self, lenhcon):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return [r[0] for r in cn.execute("SELECT lydo_chan FROM nhatky_thaotac WHERE congcu = 'cli' AND lenhcon = ?",
                                             (lenhcon,)).fetchall()]
        finally:
            cn.close()

    def buoc(self):
        return nangcli.doc_trangthai(self.dl)["claude"]["su_kien"].get("buoc")

    def test_cai_dat_ghi_ma_thoat_va_duoi_loi_da_che(self):
        loi = "npm ERR! " + "x" * 300 + f" token {MA} npm ERR! code ETIMEDOUT"
        kq, _ = self.nang(chay=ChayLoi(loi_npm=loi), ngay=True)
        self.assertEqual(kq["kq"], "hong")
        ld = self.lydo("loi")
        self.assertEqual(len(ld), 1)
        self.assertTrue(ld[0].startswith("cai_dat: ma 1: "), ld[0])
        self.assertTrue(ld[0].endswith("npm ERR! code ETIMEDOUT"), ld[0])   # đoạn CUỐI câu lỗi
        self.assertNotIn("A" * 20, ld[0])                                     # mã dài hạn đã che trước khi cắt
        self.assertLessEqual(len(ld[0]), 300)
        self.assertEqual(self.buoc(), "cai_dat")
        self.assertEqual(len(self.f04("loi")), 1)                             # vẫn đúng 01 dòng F04, chữ cũ giữ
        self.assertIn("kiểm thử chưa đạt", self.f04("loi")[0][0])

    def test_cai_dat_het_gio(self):
        kq, _ = self.nang(chay=ChayLoi(het_gio=True), ngay=True)
        self.assertEqual(kq["kq"], "hong")
        self.assertEqual(self.lydo("loi"), ["cai_dat: het gio 900 giay"])
        self.assertEqual(self.buoc(), "cai_dat")

    def test_so_ban_lech(self):
        kq, _ = self.nang(chay=y46.ChayGia(ban_cai="2.1.339"), ngay=True)
        self.assertEqual(kq["kq"], "hong")
        self.assertEqual(self.lydo("loi"), ["so_ban: --version tra 2.1.339, can 2.1.340"])
        self.assertEqual(self.buoc(), "so_ban")

    def test_dang_nhap_khong_ghi_email(self):
        self.trang_thai.return_value = {"da_noi": True}
        chay = ChayLoi()
        chay.da_noi_moi = False
        with mock.patch.object(congai, "_goi_claude", side_effect=AssertionError("không được gọi hãng")):
            kq, _ = self.nang(chay=chay, ngay=True)
        self.assertEqual(kq["kq"], "hong")
        ld = self.lydo("loi")[0]
        self.assertEqual(ld, "dang_nhap: ma 1, loggedIn=None, het phien")
        self.assertNotIn("@", ld)                                             # stdout có email: không ghi
        self.assertEqual(self.buoc(), "dang_nhap")

    def test_goi_ngan_ghi_loai_loi_da_che(self):
        self.trang_thai.return_value = {"da_noi": True}
        with mock.patch.object(congai, "_goi_claude", side_effect=congai.LoiAI("Claude", "ngan", f"chi tiet {MA}")) as g:
            kq, _ = self.nang(ngay=True)
        g.assert_called_once()
        self.assertEqual(kq["kq"], "hong")
        ld = self.lydo("loi")[0]
        self.assertTrue(ld.startswith("goi_ngan: LoiAI: Claude ngan (chi tiet sk-ant-oat01-"), ld)
        self.assertNotIn("A" * 20, ld)
        self.assertEqual(self.buoc(), "goi_ngan")

    def test_ly_do_dung_01_lan_dong_sau_khong_mang(self):
        self.nang(chay=y46.ChayGia(ban_cai="2.1.339"), ngay=True)
        nangcli._f04("thu", "dong sau", "dat", None, self.dl)
        self.assertEqual(self.lydo("thu"), [None])

    def test_dat_va_hoan_khong_ghi_ly_do(self):
        kq, _ = self.nang(ngay=True)
        self.assertEqual(kq["kq"], "dat")
        self.assertEqual(self.lydo("nang"), [None])
        self.assertNotIn("buoc", nangcli.doc_trangthai(self.dl)["claude"]["su_kien"])
        self.trang_thai.return_value = {"da_noi": True}
        with mock.patch.object(congai, "_goi_claude", side_effect=congai.HetHanMuc("het")):
            kq, _ = self.nang(npm={"ban": "2.1.341"}, ngay=True)
        self.assertEqual(kq["kq"], "hoan")                                    # QĐ306 giữ nguyên
        self.assertEqual(self.lydo("hoan"), [None])

    def test_kiem_dang_nhap_goi_cu_van_chay(self):
        """Gọi kiểu cũ (không truyền `ghi`) vẫn trả đúng như trước."""
        self.trang_thai.return_value = {"da_noi": False}
        self.assertTrue(nangcli._kiem_dang_nhap("claude", "khong-co", y46.ChayGia()))
        self.assertEqual(nangcli._kiem_goi_ngan("claude", "khong-co"), "dat")
