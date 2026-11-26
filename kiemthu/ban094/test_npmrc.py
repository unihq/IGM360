"""Bài kiểm LOI-NANGCLI-8 (bản 0.9.4): npm 10.9.9 (@npmcli/config 9.0.0 lib/index.js 541-544) từ chối khi
npm_config_userconfig và npm_config_globalconfig cùng trỏ 01 tệp ("double-loading config"); 0.8.4–0.9.3 đặt cả 02 = os.devnull
nên mọi lần nâng thật trượt ở bước cài. Sửa: user = devnull, global = 01 tệp rỗng riêng ghi đè trước mỗi lần chạy (giữ K5).
Gỡ 2.1.332 thêm 01 lần (dấu riêng da_go_hong_npmrc). Giả tiến trình như test_y46: KHÔNG gọi npm thật.
"""
import os
from pathlib import Path

from maychu.dulieu import ketnoi
from maychu.hethong.mohinh import nangcli
from kiemthu.ban084 import test_y46 as y46            # nhập cả mô-đun: bộ tìm bài không chạy lại bài cũ


class ChayGhi(y46.ChayGia):
    """Ghi lại nội dung tệp cấu hình toàn cục ĐÚNG lúc npm được gọi."""

    def __call__(self, lenh, **kw):
        if lenh[0] == "npm":
            env = kw.get("env") or {}
            g = env.get("npm_config_globalconfig")
            self.luc_goi = {"user": env.get("npm_config_userconfig"), "global": g,
                            "global_co": bool(g) and Path(g).is_file(),
                            "global_byte": Path(g).read_bytes() if g and Path(g).is_file() else None}
        return super().__call__(lenh, **kw)


class KiemNpmrc(y46.Nen):
    def test_hai_bien_khong_trung_va_tep_global_rong(self):
        for goi, ban in (("claude", "2.1.340"), ("chatgpt", "0.180.0")):
            with self.subTest(goi=goi):
                rong = nangcli.thumuc_cli(self.dl) / nangcli.NPMRC_RONG
                rong.parent.mkdir(parents=True, exist_ok=True)
                rong.write_text("registry=https://vi-du.invalid/" + chr(10), encoding="utf-8")   # có chữ cũ: phải bị ghi đè rỗng
                chay = ChayGhi()
                kq, _ = self.nang(goi=goi, chay=chay, npm={"ban": ban}, ngay=True)
                self.assertEqual(kq["kq"], "dat")
                l = chay.luc_goi
                self.assertEqual(l["user"], os.devnull)                      # bài cũ test_y46 dòng 122 giữ nguyên
                self.assertNotEqual(os.path.normcase(os.path.abspath(l["user"])),
                                    os.path.normcase(os.path.abspath(l["global"])))   # npm không double-loading
                self.assertTrue(l["global_co"])
                self.assertEqual(l["global_byte"], b"")                      # K5: không đọc cấu hình nào

    def test_luat_khong_dat_trung_trong_ma(self):
        ma = (Path(nangcli.__file__)).read_text(encoding="utf-8")
        self.assertNotIn('"npm_config_globalconfig": os.devnull', ma)


class KiemGoHongNpmrc(y46.Nen):
    def dong_go(self):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'cli' AND lenhcon = 'go_hong'").fetchall()
        finally:
            cn.close()

    def dat(self, claude):
        d = nangcli.doc_trangthai(self.dl)
        d["claude"] = claude
        nangcli.ghi_trangthai(d, self.dl)

    def tt(self):
        return nangcli.doc_trangthai(self.dl)["claude"]

    def test_go_them_01_lan_du_da_go_qd593(self):
        sk = {"loai": "hong", "luc": "2026-11-26T16:57:08+07:00", "ban": "2.1.332", "giu": "2.1.331", "buoc": "cai_dat"}
        self.dat({"dang": None, "hong": ["2.1.330", "2.1.332"], "da_go_hong": ["2.1.332"], "su_kien": dict(sk)})
        self.assertEqual(nangcli.go_hong_mot_lan(self.dl), [])                # dấu QĐ593 đã có: hàm cũ không gỡ nữa
        self.assertEqual(nangcli.go_hong_loi_npmrc(self.dl), [("claude", "2.1.332")])
        tt = self.tt()
        self.assertEqual(tt["hong"], ["2.1.330"])                             # chỉ đúng 2.1.332
        self.assertIsNone(tt["su_kien"])
        self.assertEqual(tt["da_go_hong_npmrc"], ["2.1.332"])
        self.assertEqual(tt["da_go_hong"], ["2.1.332"])                      # dấu QĐ593 giữ nguyên
        d = nangcli.doc_trangthai(self.dl)
        d["claude"]["hong"].append("2.1.332")
        nangcli.ghi_trangthai(d, self.dl)
        self.assertEqual(nangcli.go_hong_loi_npmrc(self.dl), [])              # không gỡ lần nữa
        self.assertEqual(len(self.dong_go()), 1)

    def test_khoi_dong_chay_ca_02_ham(self):
        self.dat({"dang": None, "hong": ["2.1.332"], "da_go_hong": ["2.1.332"]})
        nangcli.mo_lai_neu_len_ban_moi("0.9.4", self.dl)
        self.assertEqual(self.tt()["hong"], [])
        kq, _ = self.nang(npm={"ban": "2.1.332"}, ngay=True)
        self.assertEqual(kq["kq"], "dat")

    def test_chua_co_muc_claude_khong_loi(self):
        self.assertEqual(nangcli.go_hong_loi_npmrc(self.dl), [])
