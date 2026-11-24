"""Bài kiểm 0.8.0 (Y40; QĐ231, QĐ204 PTD-10, QĐ227, QĐ229, QĐ230): lược đồ bản 4, 01 lần nâng 3 → 4.

R5 nâng giữ dữ liệu · V3 số bảng 124 · V4 tệp nâng = tệp mới (so bằng PRAGMA) · V5 tìm đúng `id` sau VACUUM ·
F2 H08 thêm cột giữ `rowid` · K4b H07 `trangthai` lạ thì dừng, trả nguyên trạng · C4 N01 `truoc_capnhat` ·
V1, V1b chế độ an toàn trên dữ liệu bản 3 · K4 kiểm sau cập nhật phủ bản 4 · cụm tìm chữ PTD-02 Q10 (09 câu).
Dữ liệu bản 3 dựng từ `luocdo_ban3/` (đúng lược đồ 0.7.9 `d369e42`). Tên giả, 0 gọi CLI thật.
"""
import json
import secrets
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso, saoluu, timchu
from maychu.hethong import antoan, capnhat
from maychu.hethong.giamsat import thongbao

BAN3 = Path(__file__).resolve().parent / "luocdo_ban3"
MK_THU = secrets.token_urlsafe(18)   # mật khẩu giả sinh mỗi lần chạy, không ghi chữ trong mã
GOC = Path(__file__).resolve().parents[2]
# 07 tin mẫu (tên giả) và 09 câu tìm PTD-02 Q10: chữ gõ → các tin phải ra
TIN = {"t1": "Đơn hàng mới của khách", "t2": "Khách xin đổi địa chỉ giao", "t3": "Giảm giá 10% cho người mua",
       "t4": "Sương ơi kiểm lại đơn", "t5": "Đặt hàng thêm 05 thùng", "t6": "Lương thưởng tháng 11", "t7": "Gửi hoá đơn hàng tuần"}
CAU = {"don hang": {"t1", "t7"}, "doi dia chi": {"t2"}, "giam gia": {"t3"}, "nguoi mua": {"t3"}, "suong oi": {"t4"},
       "dat hang": {"t5"}, "luong thuong": {"t6"}, "đơn hàng": {"t1", "t7"}, "Don": {"t1", "t4", "t7"}}


def dung_ban3(dl: Path, trangthai_h07: str = "dung") -> dict:
    """07 tệp đúng lược đồ bản 3 + dòng mẫu ở H07, H08, G06, N01 (có dòng trước cập nhật của 0.7.9). Trả {tin_id: id}."""
    dl.mkdir(parents=True, exist_ok=True)
    for ten in ketnoi.CAC_FILE:
        cn = ketnoi.mo(ten, dl)
        try:
            cn.executescript((BAN3 / f"{ten}.sql").read_text(encoding="utf-8"))
            cn.execute("PRAGMA user_version=3")
            khoitao._dong_khoitao(cn, ten)
        finally:
            cn.close()
    ma = {k: maso.tao() for k in TIN}
    cn = ketnoi.mo("Bot", dl)
    try:
        h1, h2 = maso.tao(), maso.tao()
        cn.execute("INSERT INTO hoithoai (id, loai, tieude, trangthai) VALUES (?, 'troly', 'Cuộc thử 01', ?)", (h1, trangthai_h07))
        cn.execute("INSERT INTO hoithoai (id, loai, tieude, trangthai) VALUES (?, 'troly', 'Cuộc thử 02', 'dung')", (h2,))
        for i, (k, chu) in enumerate(TIN.items()):
            cn.execute("INSERT INTO tinnhan (id, hoithoai_id, vai, noidung, luc) VALUES (?, ?, 'nguoi', ?, ?)",
                       (ma[k], h1, chu, f"2026-11-2{i}T10:00:00+07:00"))
    finally:
        cn.close()
    cn = ketnoi.mo("Viecnen", dl)
    try:
        cn.execute("INSERT INTO nguon_ai (id, ma, ten, trangthai, hang, cach_goi) VALUES (?, 'goi_claude_01', 'Gói thử', 'dung',"
                   " 'anthropic', 'cli')", (maso.tao(),))
    finally:
        cn.close()
    cn = ketnoi.mo("Nhatky", dl)
    try:
        for luc, buoc in (("2026-11-23T02:00:00+07:00", {}), ("2026-11-24T10:05:00+07:00", {"dip": "truoc_capnhat", "ban": "0.7.9"})):
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua_tungbuoc_json, ketqua) VALUES (?, 'hangngay',"
                       " 'Bot', ?, ?, 'xong_tren_may')", (maso.tao(), luc, json.dumps(buoc)))
    finally:
        cn.close()
    return ma


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.g = Path(self.tam.name)
        self.dl = self.g / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            "IGM360_CLAUDE_CLI": str(self.g / "khong_co_cli_claude"),
                                            "IGM360_CODEX_CLI": str(self.g / "khong_co_cli_codex")})
        bien.start()
        self.addCleanup(bien.stop)
        antoan.CHE_DO.update(an_toan=False, den=None, luc=None, lydo=None)
        self.addCleanup(antoan.CHE_DO.update, an_toan=False, den=None, luc=None, lydo=None)

    def tearDown(self):
        self.tam.cleanup()

    def lay(self, ten, sql, ts=(), dl=None):
        cn = ketnoi.mo(ten, dl or self.dl)
        try:
            return cn.execute(sql, ts).fetchall()
        finally:
            cn.close()

    def ban(self, dl=None):
        return {t: self.lay(t, "PRAGMA user_version", dl=dl)[0][0] for t in ketnoi.CAC_FILE}


class KiemNangBan4(Nen):
    def test_r5_nang_giu_du_lieu_dung_so_bang(self):
        ma = dung_ban3(self.dl)
        truoc = {}
        for k in ("Bot.hoithoai", "Bot.tinnhan", "Viecnen.nguon_ai", "Nhatky.saoluu"):
            ten, bang = k.split(".", 1)
            truoc[k] = self.lay(ten, f"SELECT count(*) FROM {bang}")[0][0]
        kq = khoitao.tao_het(self.dl)
        self.assertEqual(kq, ketnoi.SO_BANG)
        self.assertEqual(sum(kq.values()), 124)                                       # V3: 118 bảng + cụm tìm chữ
        self.assertEqual(set(self.ban().values()), {4})
        for k, so in truoc.items():
            ten, bang = k.split(".", 1)
            self.assertEqual(self.lay(ten, f"SELECT count(*) FROM {bang}")[0][0], so, k)
            self.assertEqual(self.lay(ten, "PRAGMA foreign_key_check"), [], ten)
        self.assertEqual(self.lay("Bot", "SELECT count(*) FROM tinnhan WHERE trangthai IS NOT NULL OR phu_json IS NOT NULL"
                                         " OR tra_loi_cho IS NOT NULL OR kenh_nguon IS NOT NULL")[0][0], 0)
        self.assertEqual(self.lay("Viecnen", "SELECT goi_ten, giahan_ngay, giahan_trangthai, chuky, phi_ky, phi_tien_ma,"
                                             " khoanchi_ma, ma, hang FROM nguon_ai"),
                         [(None,) * 7 + ("goi_claude_01", "anthropic")])
        self.assertEqual(len(self.lay("Viecnen", "PRAGMA table_info(nguon_ai)")), 30)   # G06 23 → 30 cột
        self.assertEqual(len(self.lay("Bot", "PRAGMA table_info(hoithoai)")), 20)
        self.assertEqual(len(self.lay("Bot", "PRAGMA table_info(tinnhan)")), 12)
        self.assertEqual(sorted(r[0] for r in self.lay("Nhatky", "SELECT loai FROM saoluu")), ["hangngay", "truoc_capnhat"])   # C4
        cn = ketnoi.mo("Bot", self.dl)
        try:
            self.assertEqual(set(timchu.tim(cn, "don hang")), {ma["t1"], ma["t7"]})
        finally:
            cn.close()
        n = antoan.doc(self.dl)["nang_luocdo"]
        self.assertEqual((n["den"], n["so_dong"]), (4, truoc))                       # K4: số dòng lúc nâng
        self.assertTrue((self.dl / "saoluu" / "truoc_nangcap_v04" / "Bot.sqlite3").exists())

    def test_v4_tep_nang_giong_tep_moi_theo_pragma(self):
        dung_ban3(self.dl)
        khoitao.tao_het(self.dl)
        moi = self.g / "moi"
        khoitao.tao_het(moi)

        def hinh(dl):
            ra = {}
            for ten in ketnoi.CAC_FILE:
                cn = ketnoi.mo(ten, dl)
                try:
                    ten_bang = sorted(cn.execute("SELECT type, name, tbl_name FROM sqlite_master").fetchall())
                    for _loai, ten_dt, _b in ten_bang:
                        if _loai == "table":
                            ra[f"{ten}.{ten_dt}.cot"] = cn.execute(f"PRAGMA table_info('{ten_dt}')").fetchall()
                            ra[f"{ten}.{ten_dt}.khoangoai"] = sorted(cn.execute(f"PRAGMA foreign_key_list('{ten_dt}')").fetchall())
                            ds = sorted(cn.execute(f"PRAGMA index_list('{ten_dt}')").fetchall(), key=lambda r: r[1])
                            ra[f"{ten}.{ten_dt}.chimuc"] = [(r[1], r[2], r[3], cn.execute(f"PRAGMA index_info('{r[1]}')").fetchall())
                                                           for r in ds]
                    ra[f"{ten}.ten"] = ten_bang
                finally:
                    cn.close()
            return ra
        a, b = hinh(self.dl), hinh(moi)
        self.assertEqual(sorted(a), sorted(b))
        for k in a:
            self.assertEqual(a[k], b[k], k)
        self.assertIn(("index", "tinnhan_cuoc", "tinnhan"), a["Bot.ten"])                # V4: chỉ mục có ở tệp nâng
        self.assertIn(("table", "tinnhan_tim", "tinnhan_tim"), a["Bot.ten"])             # V4: bảng ảo có ở tệp nâng

    def test_f2_h08_them_cot_giu_rowid(self):
        dung_ban3(self.dl)
        truoc = self.lay("Bot", "SELECT rowid, id FROM tinnhan ORDER BY rowid")
        khoitao.tao_het(self.dl)
        self.assertEqual(self.lay("Bot", "SELECT rowid, id FROM tinnhan ORDER BY rowid"), truoc)
        cot = [r[1] for r in self.lay("Bot", "PRAGMA table_info(tinnhan)")]
        self.assertEqual(cot[-4:], ["trangthai", "phu_json", "tra_loi_cho", "kenh_nguon"])
        with self.assertRaises(sqlite3.IntegrityError):                              # CHECK cột thêm còn chặn
            cn = ketnoi.mo("Bot", self.dl)
            try:
                cn.execute("UPDATE tinnhan SET trangthai = 'la' WHERE rowid = 1")
            finally:
                cn.close()

    def test_k4b_h07_trangthai_la_thi_dung_tra_nguyen_trang(self):
        dung_ban3(self.dl, trangthai_h07="cu_la")
        with self.assertRaises(RuntimeError) as loi:
            khoitao.tao_het(self.dl)
        self.assertIn("K4b", str(loi.exception))
        self.assertNotIn("cu_la", str(loi.exception))                                 # không in giá trị
        self.assertEqual(set(self.ban().values()), {3})                               # cả 07 tệp về bản 3
        self.assertEqual(self.lay("Nhatky", "SELECT count(*) FROM saoluu WHERE loai = 'hangngay'")[0][0], 2)
        self.assertNotIn("dang_nang", antoan.doc(self.dl))

    def test_v5_tim_dung_id_sau_vacuum_va_q10(self):
        ma = dung_ban3(self.dl)
        khoitao.tao_het(self.dl)
        cn = ketnoi.mo("Bot", self.dl)
        try:
            cn.execute("VACUUM")
            nguoc = {v: k for k, v in ma.items()}
            for chu, mong in CAU.items():
                self.assertEqual({nguoc[i] for i in timchu.tim(cn, chu)}, mong, chu)   # 09/09 câu PTD-02 Q10
            self.assertEqual(timchu.tim(cn, 'don" OR "khach'), [])                    # Q7: chữ gõ không thành lệnh
            self.assertEqual(cn.execute("SELECT count(*) FROM tinnhan_tim_noi").fetchone()[0], 7)
        finally:
            cn.close()

    def test_ghi_tin_ghi_chi_muc_va_xoa_tin(self):
        from maychu.hethong.mohinh import trochuyen
        dung_ban3(self.dl)
        khoitao.tao_het(self.dl)
        cn = ketnoi.mo("Bot", self.dl)
        try:
            h = cn.execute("SELECT id FROM hoithoai LIMIT 1").fetchone()[0]
            cn.execute("BEGIN IMMEDIATE")
            t = trochuyen._ghi_tin(cn, h, "nguoi", "Đổi đơn hàng sang tuần sau")
            cn.execute("COMMIT")
            self.assertIn(t["id"], timchu.tim(cn, "doi don hang"))
            self.assertEqual(cn.execute("SELECT count(*) FROM tinnhan").fetchone()[0],
                             cn.execute("SELECT count(*) FROM tinnhan_tim_noi").fetchone()[0])
            timchu.xoa_tin(cn, t["id"])                                               # X3 (lúc bật): xoá cụm tìm chữ của tin
            self.assertNotIn(t["id"], timchu.tim(cn, "doi don hang"))
        finally:
            cn.close()

    def test_moi_tao_du_124(self):
        kq = khoitao.tao_het(self.dl)
        self.assertEqual((kq, set(self.ban().values())), (ketnoi.SO_BANG, {4}))
        self.assertEqual(sum(ketnoi.SO_BANG.values()), 124)


class KiemC4V1b(Nen):
    def test_v1b_nhatky_ban3_ghi_nhu_079(self):
        dung_ban3(self.dl)
        self.assertEqual(saoluu._loai_n01(self.dl, "0.8.0"), "hangngay")
        kq = saoluu.chay(self.dl, truoc_ban="0.8.0")                                  # CHECK bản 3 không chặn
        self.assertEqual(kq["ketqua"], "xong_tren_may")
        d = self.lay("Nhatky", "SELECT loai, ketqua_tungbuoc_json FROM saoluu WHERE ketqua_tungbuoc_json LIKE '%0.8.0%'")
        self.assertEqual(len(d), len(ketnoi.CAC_FILE))
        self.assertTrue(all(x[0] == "hangngay" and json.loads(x[1])["dip"] == "truoc_capnhat" for x in d))

    def test_c4_ban4_ghi_truoc_capnhat_chuong_bo_qua(self):
        khoitao.tao_het(self.dl)
        self.assertEqual((saoluu._loai_n01(self.dl, "0.8.1"), saoluu._loai_n01(self.dl, None)), ("truoc_capnhat", "hangngay"))
        cn = ketnoi.mo("Nhatky", self.dl)
        try:   # sao lưu hằng ngày hỏng lúc 02:00, rồi lượt trước cập nhật đạt lúc 10:05: chuông vẫn báo đỏ
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua) VALUES (?, 'hangngay', 'Bot',"
                       " '2026-11-24T02:00:00+07:00', 'loi')", (maso.tao(),))
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua) VALUES (?, 'truoc_capnhat', 'Bot',"
                       " '2026-11-24T10:05:00+07:00', 'xong_tren_may')", (maso.tao(),))
        finally:
            cn.close()
        thongbao.quet_saoluu(self.dl)
        self.assertTrue([d for d in thongbao.danh_sach(thumuc=self.dl)["ds"] if d["loai"] == "saoluu_loi" and d.get("mo", True)])


class KiemV1K4(Nen):
    def test_v1_che_do_an_toan_tren_du_lieu_ban3(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        dung_ban3(self.dl)
        with mock.patch.dict(os.environ, {"IGM360_ADMIN_USER": "chu_thu", "IGM360_ADMIN_PASSWORD": MK_THU}):
            from maychu.hethong.taikhoan import nguoidung
            self.assertTrue(nguoidung.tao_quantri_tu_env(self.dl))                    # tài khoản có sẵn trên dữ liệu bản 3
        that = khoitao.tao_mot

        def hong(ten, thumuc, chu=None):
            if ten == "Baomat":                                                       # tệp cuối nâng hỏng → trả cả 07 tệp
                raise RuntimeError("nâng hỏng ở tệp cuối")
            return that(ten, thumuc, chu)
        with mock.patch.object(khoitao, "tao_mot", side_effect=hong):
            with TestClient(khoidong.app) as c:
                self.assertTrue(c.get("/suckhoe").json()["an_toan"])
                self.assertEqual(set(self.ban().values()), {3})                       # mã 0.8.0 chạy trên dữ liệu bản 3
                r = c.post("/api/dangnhap", json={"ten": "chu_thu", "matkhau": MK_THU}, headers={"X-IGM360": "1"})
                self.assertEqual(r.status_code, 200, r.text)                           # F01, F05, F04 bản 3 dùng được
                self.assertEqual(c.get("/api/capnhat").status_code, 401)              # không bị chặn, không lỗi 500
                kq = saoluu.chay(self.dl, truoc_ban="0.8.1")                          # V1b: sao lưu trước cập nhật được
                self.assertEqual(kq["ketqua"], "xong_tren_may")

    def test_k4_kiem_sau_capnhat_phu_ban_4(self):
        dung_ban3(self.dl)
        khoitao.tao_het(self.dl)
        tt = antoan.doc(self.dl)
        ban = capnhat.ban_dang_chay()
        self.assertTrue(antoan._luocdo_ban4_du(tt, ban, self.dl))
        cn = ketnoi.mo("Bot", self.dl)
        try:
            cn.execute("DELETE FROM tinnhan_tim_noi WHERE so = (SELECT max(so) FROM tinnhan_tim_noi)")   # chỉ mục thiếu 01 tin
        finally:
            cn.close()
        self.assertFalse(antoan._luocdo_ban4_du(tt, ban, self.dl))
        tt["nang_luocdo"]["so_dong"]["Viecnen.nguon_ai"] = 5                         # số dòng sau nâng ít hơn lúc nâng
        cn = ketnoi.mo("Bot", self.dl)
        try:
            timchu.dung_lai(cn)
        finally:
            cn.close()
        self.assertFalse(antoan._luocdo_ban4_du(tt, ban, self.dl))
        tt["nang_luocdo"]["so_dong"]["Viecnen.nguon_ai"] = 1
        self.assertTrue(antoan._luocdo_ban4_du(tt, ban, self.dl))


class KiemY40b(Nen):
    """CDA KT-Y40 (PTD-10 mục 15): L1 ghi tin + chỉ mục 01 giao dịch; L2 so chỉ mục chỉ ở lần kiểm bản vừa nâng; L3 đọc theo lô."""

    def test_l1_chi_muc_loi_thi_khong_them_tin(self):
        from maychu.hethong.mohinh import trochuyen
        khoitao.tao_het(self.dl)
        dem = lambda: (self.lay("Bot", "SELECT count(*) FROM hoithoai")[0][0], self.lay("Bot", "SELECT count(*) FROM tinnhan")[0][0])   # noqa: E731
        truoc = dem()
        with mock.patch.object(timchu, "ghi_tin", side_effect=sqlite3.OperationalError("chỉ mục lỗi giả")), \
                mock.patch.object(trochuyen.congai, "goi") as goi:
            with self.assertRaises(sqlite3.OperationalError):
                trochuyen.gui(None, maso.tao(), "Câu thử 01")                          # cuộc mới + tin hỏi
        goi.assert_not_called()
        self.assertEqual(dem(), truoc)                                                 # không thêm cuộc, không thêm tin
        h = maso.tao()
        cn = ketnoi.mo("Bot", self.dl)
        try:
            cn.execute("INSERT INTO hoithoai (id, loai, trangthai) VALUES (?, 'troly', 'dung')", (h,))
            with mock.patch.object(timchu, "ghi_tin", side_effect=sqlite3.OperationalError("chỉ mục lỗi giả")):
                with self.assertRaises(sqlite3.OperationalError):
                    trochuyen._ghi_tin(cn, h, "ai", "Trả lời thử")                       # lượt trả lời (tự mở giao dịch)
            self.assertFalse(cn.in_transaction)
            self.assertEqual(cn.execute("SELECT count(*) FROM tinnhan WHERE hoithoai_id = ?", (h,)).fetchone()[0], 0)
            trochuyen._ghi_tin(cn, h, "ai", "Trả lời thử")                               # bình thường: tin + chỉ mục cùng chốt
            self.assertEqual(cn.execute("SELECT count(*) FROM tinnhan").fetchone()[0],
                             cn.execute("SELECT count(*) FROM tinnhan_tim_noi").fetchone()[0])
        finally:
            cn.close()

    def test_l2_chi_so_chi_muc_o_lan_kiem_ban_vua_nang(self):
        dung_ban3(self.dl)
        khoitao.tao_het(self.dl)
        tt = antoan.doc(self.dl)
        ban = capnhat.ban_dang_chay()
        cn = ketnoi.mo("Bot", self.dl)
        try:
            cn.execute("DELETE FROM tinnhan_tim_noi WHERE so = (SELECT max(so) FROM tinnhan_tim_noi)")
        finally:
            cn.close()
        self.assertFalse(antoan._luocdo_ban4_du(tt, ban, self.dl))                    # bản vừa nâng: lệch thì chưa đạt
        self.assertTrue(antoan._luocdo_ban4_du(tt, "99.0.0", self.dl))                # bản sau (không nâng lược đồ): không so. 0.8.1: không viết cứng số bản kế tiếp

    def test_l3_dung_lai_doc_theo_lo(self):
        khoitao.tao_het(self.dl)
        cn = ketnoi.mo("Bot", self.dl)
        try:
            h = maso.tao()
            cn.execute("BEGIN IMMEDIATE")
            cn.execute("INSERT INTO hoithoai (id, loai, trangthai) VALUES (?, 'troly', 'dung')", (h,))
            so = timchu.LO_DUNG_LAI * 2 + 7
            cn.executemany("INSERT INTO tinnhan (id, hoithoai_id, vai, noidung, luc) VALUES (?, ?, 'nguoi', ?, ?)",
                           [(maso.tao(), h, f"Đơn hàng số {i}", f"2026-11-24T10:{i % 60:02d}:00+07:00") for i in range(so)])
            self.assertEqual(timchu.dung_lai(cn), so)
            cn.execute("COMMIT")
            self.assertEqual(cn.execute("SELECT count(*) FROM tinnhan_tim_noi").fetchone()[0], so)
            self.assertEqual(len(timchu.tim(cn, "don hang", gioi_han=so)), so)
        finally:
            cn.close()
        self.assertNotIn("fetchall", Path(timchu.__file__).read_text(encoding="utf-8").split("def dung_lai", 1)[1].split("def tim", 1)[0])


class KiemY40c(Nen):
    """QĐ237 (G1, cách C): quay về có trả dữ liệu vẫn giữ 05 sổ nhật ký (F04, G04, H05, N01, N02) và M01 loại 'saoluu'
    ghi sau giờ chụp; N01 về lược đồ 3 thì 'truoc_capnhat' → 'hangngay' + "dip"; ghi nối lỗi không chặn quay về."""
    LUC = "2026-11-24T09:00:00+07:00"

    def dung(self):
        from datetime import datetime, timedelta
        from maychu import chay
        dung_ban3(self.dl)
        khoitao.tao_het(self.dl)                         # chụp truoc_nangcap_v04 (dữ liệu bản 3) rồi nâng lên bản 4
        # dòng ghi trên 0.8.0: sau giờ chụp, trước lúc quay về (giữ theo `id`, giờ chỉ để xếp lịch sử)
        self.LUC = (datetime.now(saoluu.MUIGIO_VN) - timedelta(seconds=2)).isoformat(timespec="seconds")
        g = self.g / "app"
        (g / "ban_truoc" / "maychu").mkdir(parents=True)
        (g / "VERSION").write_text("0.8.0", encoding="utf-8")
        (g / "ban_truoc" / "VERSION").write_text("0.7.9", encoding="utf-8")
        self.id = {k: maso.tao() for k in ("f04", "g04", "h05", "n02", "n01a", "n01b", "m_co", "m_mat", "m_goc")}
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            cn.execute("INSERT INTO nhatky_thaotac (id, luc, congcu, lenhcon, thamso_tomtat, ketqua) VALUES (?, ?, 'capnhat',"
                       " 'khoidong', '0.8.0', 'dat')", (self.id["f04"], self.LUC))
            for bang, k in (("nhatky_ai", "g04"), ("nhatky_noihayim", "h05"), ("theodoi_maychu", "n02")):
                cn.execute(f"INSERT INTO {bang} (id, luc) VALUES (?, ?)", (self.id[k], self.LUC))
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua_tungbuoc_json, ketqua) VALUES (?, 'truoc_capnhat',"
                       " 'Bot', ?, ?, 'xong_tren_may')", (self.id["n01a"], self.LUC, json.dumps({"dip": "truoc_capnhat", "ban": "0.8.1"})))
            cn.execute("INSERT INTO saoluu (id, loai, file_dulieu, chup_luc, ketqua_tungbuoc_json, ketqua) VALUES (?, 'truoc_capnhat',"
                       " 'Hotho', ?, '{}', 'xong_tren_may')", (self.id["n01b"], self.LUC))
        finally:
            cn.close()
        tep_co = self.dl / "saoluu" / "2026-11-25" / "Bot.sqlite3.enc"
        tep_co.parent.mkdir(parents=True, exist_ok=True)
        tep_co.write_bytes(b"ban sao gia")
        cn = ketnoi.mo("Hotho", self.dl)
        try:
            for k, loai, duong in (("m_co", "saoluu", str(tep_co)), ("m_mat", "saoluu", str(self.dl / "khong_co.enc")),
                                   ("m_goc", "filegoc", str(tep_co))):
                cn.execute("INSERT INTO cho_day_drive (id, loai, duongdan_tam, trangthai, tao_luc) VALUES (?, ?, ?, 'cho', ?)",
                           (self.id[k], loai, duong, self.LUC))
        finally:
            cn.close()
        antoan.ghi(self.dl, chay_ban_truoc={"ban_anh": "0.8.0", "ban_truoc": "0.7.9", "nguoi": None,
                                            "tra_du_lieu": {"thumuc": "truoc_nangcap_v04", "tep": list(ketnoi.CAC_FILE)}})
        return chay, g

    def co(self, ten, bang, k):
        return bool(self.lay(ten, f"SELECT 1 FROM {bang} WHERE id = ?", (self.id[k],)))

    def test_giu_05_so_m01_va_n01_ve_ban_3(self):
        chay, g = self.dung()
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")
        self.assertEqual(self.ban()["Nhatky"], 3)                                      # dữ liệu đã trả về bản 3
        for bang, k in (("nhatky_thaotac", "f04"), ("nhatky_ai", "g04"), ("nhatky_noihayim", "h05"), ("theodoi_maychu", "n02")):
            self.assertTrue(self.co("Nhatky", bang, k), bang)
        n01 = dict(self.lay("Nhatky", "SELECT id, loai || '|' || ketqua_tungbuoc_json FROM saoluu WHERE id IN (?, ?)",
                            (self.id["n01a"], self.id["n01b"])))
        for k in ("n01a", "n01b"):
            loai, js = n01[self.id[k]].split("|", 1)
            self.assertEqual((loai, json.loads(js)["dip"]), ("hangngay", "truoc_capnhat"), k)   # CHECK bản 3, giữ "dip"
        self.assertTrue(self.co("Hotho", "cho_day_drive", "m_co"))                       # M01 'saoluu' còn tệp: giữ
        self.assertFalse(self.co("Hotho", "cho_day_drive", "m_mat"))                     # mất tệp: bỏ
        self.assertFalse(self.co("Hotho", "cho_day_drive", "m_goc"))                     # 'filegoc': không chép
        self.assertFalse((self.dl / chay.TEP_GIU).exists())
        self.assertNotIn("giu_nhatky", antoan.doc(self.dl))
        qv = self.lay("Nhatky", "SELECT luc, thamso_tomtat FROM nhatky_thaotac WHERE lenhcon = 'quayve'")
        self.assertEqual(len(qv), 1)
        self.assertGreater(qv[0][0], self.LUC)                                           # dòng "quayve" ghi sau dòng đã giữ
        self.assertNotIn("chưa giữ được", qv[0][1])

    def test_lich_su_co_dong_ban_vua_lui(self):
        chay, g = self.dung()
        chay.chon(self.dl, g)
        with mock.patch.object(capnhat, "ban_dang_chay", return_value="0.7.9"):          # như 0.7.9 khởi động
            capnhat.ghi_khoi_dong(self.dl)
            self.assertEqual([x["ban"] for x in capnhat.lich_su(self.dl)][:2], ["0.7.9", "0.8.0"])

    def test_ghi_noi_loi_khong_chan_lan_sau_ghi_lai(self):
        chay, g = self.dung()
        with mock.patch.object(chay, "_noi_bang", side_effect=sqlite3.OperationalError("khoá giả")):
            self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")                      # vẫn quay về
        self.assertTrue((self.dl / chay.TEP_GIU).exists())
        self.assertEqual(antoan.doc(self.dl)["giu_nhatky"]["loi"], "OperationalError")
        self.assertFalse(self.co("Nhatky", "nhatky_thaotac", "f04"))
        self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")                          # lần khởi động sau: ghi lại
        self.assertTrue(self.co("Nhatky", "nhatky_thaotac", "f04"))
        self.assertTrue(self.co("Hotho", "cho_day_drive", "m_co"))
        self.assertFalse((self.dl / chay.TEP_GIU).exists())
        self.assertNotIn("giu_nhatky", antoan.doc(self.dl))

    def test_chay_02_lan_khong_ghi_doi(self):
        import shutil
        chay, g = self.dung()
        chay._chep_giu(self.dl, self.dl / "saoluu" / "truoc_nangcap_v04")
        luu = self.g / "giu_luu.sqlite3"
        shutil.copy(self.dl / chay.TEP_GIU, luu)
        chay.chon(self.dl, g)
        dem = lambda: [self.lay("Nhatky", f"SELECT count(*) FROM {b}")[0][0] for b in chay.BANG_GIU] + \
            [self.lay("Hotho", "SELECT count(*) FROM cho_day_drive")[0][0]]   # noqa: E731
        truoc = dem()
        shutil.copy(luu, self.dl / chay.TEP_GIU)
        chay._ghi_noi_giu(self.dl)                                                     # ghi nối lần 02
        self.assertEqual(dem(), truoc)

    def test_chep_loi_van_quay_ve_ghi_chu(self):
        chay, g = self.dung()
        with mock.patch.object(chay, "_chep_giu", side_effect=OSError("đĩa giả lỗi")):
            self.assertEqual(chay.chon(self.dl, g), g / "ban_truoc")
        qv = self.lay("Nhatky", "SELECT thamso_tomtat FROM nhatky_thaotac WHERE lenhcon = 'quayve'")
        self.assertIn("chưa giữ được nhật ký sau giờ nâng", qv[0][0])
        self.assertFalse((self.dl / chay.TEP_GIU).exists())

    def test_tra_loi_thi_bo_tep_giu(self):
        chay, g = self.dung()
        with mock.patch.object(chay, "tra_du_lieu", return_value="không trả được dữ liệu: OSError"):
            self.assertEqual(chay.chon(self.dl, g), g)                                    # không trả: chạy bản mới
        self.assertFalse((self.dl / chay.TEP_GIU).exists())
        self.assertTrue(self.co("Nhatky", "nhatky_thaotac", "f04"))                      # nhật ký vẫn ở tệp đang chạy

    def test_nhatky_ban_4_giu_truoc_capnhat(self):
        from maychu import chay
        khoitao.tao_het(self.dl)
        giu = self.dl / chay.TEP_GIU
        cn = sqlite3.connect(giu)
        try:
            cn.execute("CREATE TABLE saoluu (id TEXT, loai TEXT, chup_luc TEXT, ketqua_tungbuoc_json TEXT)")
            cn.execute("INSERT INTO saoluu VALUES ('x1', 'truoc_capnhat', ?, '{}')", (self.LUC,))
            cn.commit()
        finally:
            cn.close()
        chay._ghi_noi_giu(self.dl)
        self.assertEqual(self.lay("Nhatky", "SELECT loai, ketqua_tungbuoc_json FROM saoluu WHERE id = 'x1'"),
                         [("truoc_capnhat", "{}")])                                    # lược đồ 4: giữ nguyên giá trị


class KiemImage(unittest.TestCase):
    def test_ghim_trixie_va_buoc_kiem_sqlite(self):
        self.assertIn("\nFROM python:3.12-slim-trixie\n", (GOC / "Dockerfile").read_text(encoding="utf-8"))
        ci = (GOC / ".github/workflows/dongimage.yml").read_text(encoding="utf-8")
        self.assertIn("Kiểm bản SQLite trong image", ci)
        self.assertIn("(3, 43, 0)", ci)
        self.assertLess(ci.index("Kiểm bản SQLite trong image"), ci.index("- name: Đẩy image"))

    def test_sqlite_may_kiem_co_contentless_delete(self):
        self.assertGreaterEqual(tuple(map(int, sqlite3.sqlite_version.split("."))), (3, 43, 0))


if __name__ == "__main__":
    unittest.main()
