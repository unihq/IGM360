"""Bài kiểm N0 mốc 2 (QĐ344, QĐ347, QĐ348, QĐ350, QĐ352; CDA KT-N0 (1)–(6), S1–S5, X1–X4, C1–C2, M1): sổ lượt,
01 dòng G02 mỗi lượt, luồng sự kiện, khởi động lại, lượt kẹt (H2), xóa dòng G02 sau 24 giờ, câu báo đang chờ cập nhật.
Không gọi CLI thật: `congai.goi` giả lập.
"""
import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao, maso, timchu
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong import capnhat
from maychu.hethong.mohinh import congai, luot, trochuyen

TL = {"chu": "Trả lời đủ", "nhatky_ai_id": None, "nguon": "Gói thử", "nguon_id": "n1", "mohinh_id": "m1",
      "mohinh": "opus", "ghim_hong": None, "md_hong": None, "ghim_khoa": None, "mohinh_bao": None, "chay_tk": 1,
      "du_phong": None, "bo_qua": []}


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"}))
        khoitao.tao_het(self.dl)
        self.enterContext(mock.patch.object(capnhat, "dang_cho", return_value=False))
        with luot._KHOA:
            luot._DANG.clear()
            luot._DA_XONG.clear()
        self.ng = maso.tao()

    def sql(self, ten, cau, ts=()):
        cn = ketnoi.mo(ten, self.dl)
        try:
            cn.execute("BEGIN IMMEDIATE")
            r = cn.execute(cau, ts).fetchall()
            cn.execute("COMMIT")
            return r
        finally:
            cn.close()

    def g02(self):
        return self.sql("Viecnen", "SELECT id, loai, goi_ai, trangthai, khoa_chongtrung, giu_boi, xong_luc, ketqua_json"
                                   " FROM viecnen ORDER BY tao_luc")

    def tin(self):
        return self.sql("Bot", "SELECT id, vai, noidung, trangthai, tra_loi_cho, phu_json FROM tinnhan ORDER BY luc, rowid")

    def f04(self, lenhcon):
        return self.sql("Nhatky", "SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'trochuyen' AND lenhcon = ?", (lenhcon,))

    def cho_xong(self, luot_id):
        lt = luot.lay(luot_id, self.ng)
        lt.luong.join(10)
        self.assertFalse(lt.luong.is_alive())
        return lt


class KiemMoLuot(Nen):
    def test_tra_ngay_chay_nen_ghi_dung_thu_tu(self):
        thu_tu = []
        that_g02, that_tin = luot.mo_g02, trochuyen._ghi_tin
        goi_vao = threading.Event()

        def goi(cau, **k):
            goi_vao.wait(5)
            self.assertIs(congai._NGHE.get(), lt_dang[0].nghe)                   # có người nghe trong luồng lượt
            self.assertNotIn("viecnen_id", k)                                     # CDA (1): giữ ghim
            return dict(TL)
        lt_dang = []
        with mock.patch.object(luot, "mo_g02", side_effect=lambda *a: thu_tu.append("g02") or that_g02(*a)), \
                mock.patch.object(trochuyen, "_ghi_tin", side_effect=lambda *a, **k: thu_tu.append(a[2]) or that_tin(*a, **k)), \
                mock.patch.object(congai, "goi", side_effect=goi):
            kq = trochuyen.bat_luot(None, self.ng, "Câu 01", self.dl)
            lt_dang.append(luot.lay(kq["luot_id"], self.ng))
            self.assertEqual(capnhat.so_viec_ai_dangchay(self.dl), 1)              # cập nhật chế độ chờ thấy lượt
            self.assertTrue(luot.dang_trong_so(kq["luot_id"]))
            goi_vao.set()
            lt = self.cho_xong(kq["luot_id"])
        self.assertEqual(thu_tu, ["g02", "nguoi", "ai"])                          # CDA (4): G02 → tin hỏi → tin trả lời
        g = self.g02()[0]
        self.assertEqual(g[:6], (kq["luot_id"], "trochuyen", 1, "xong", "trochuyen:" + kq["hoithoai_id"], luot.BOOT_ID))
        self.assertTrue(g[6])                                                     # X2: xong_luc
        self.assertEqual(json.loads(g[7]), {"hoithoai_id": kq["hoithoai_id"], "tin_hoi_id": kq["hoi"]["id"]})
        t = self.tin()
        self.assertEqual([(x[1], x[3], x[4]) for x in t], [("nguoi", None, None), ("ai", "xong", kq["hoi"]["id"])])
        self.assertFalse(luot.dang_trong_so(kq["luot_id"]))                       # S1: rời sổ sau khi đóng G02
        loai = [e["loai"] for e in lt.su_kien]
        self.assertEqual((loai[0], loai[-1]), ("bat_dau", "xong"))
        tl = lt.su_kien[-1]["tra_loi"]                                            # CDA (2): đủ trường như `gui` trả hôm nay
        for k in ("ghim_hong", "md_hong", "chay_tk", "du_phong", "ghim_khoa", "mohinh_bao", "nguon_id", "nguon", "mohinh"):
            self.assertIn(k, tl)

    def test_01_luot_moi_cuoc(self):
        cho = threading.Event()
        with mock.patch.object(congai, "goi", side_effect=lambda c, **k: cho.wait(5) and dict(TL)):
            kq = trochuyen.bat_luot(None, self.ng, "Câu 01", self.dl)
            kq2 = trochuyen.bat_luot(kq["hoithoai_id"], self.ng, "Câu 02", self.dl)
            self.assertEqual((kq2["luot_id"], kq2.get("trung"), kq2["hoi"]), (kq["luot_id"], True, None))
            self.assertEqual(len(self.tin()), 1)
            self.assertEqual(len(self.g02()), 1)
            cho.set()
            self.cho_xong(kq["luot_id"])

    def test_g02_da_co_dong_chay_thi_bo_luot_moi_khoi_so(self):
        h = maso.tao()
        self.sql("Bot", "INSERT INTO hoithoai (id, loai, nguoidung_id, trangthai) VALUES (?, 'troly', ?, 'dung')", (h, self.ng))
        self.sql("Viecnen", "INSERT INTO viecnen (id, loai, goi_ai, trangthai, khoa_chongtrung) VALUES ('cu', 'trochuyen', 1,"
                            " 'dangchay', ?)", ("trochuyen:" + h,))
        with mock.patch.object(congai, "goi") as goi:
            kq = trochuyen.bat_luot(h, self.ng, "Câu", self.dl)
        goi.assert_not_called()
        self.assertEqual((kq["luot_id"], kq["trung"]), ("cu", True))
        self.assertEqual(luot._DANG, {})                                          # SOAT-SUA-H2: lượt mới không nằm lại sổ

    def test_ghi_tin_hoi_loi_thi_dong_g02_va_bo_khoi_so(self):
        with mock.patch.object(timchu, "ghi_tin", side_effect=RuntimeError("chỉ mục lỗi giả")), \
                mock.patch.object(congai, "goi") as goi:
            with self.assertRaises(RuntimeError):
                trochuyen.bat_luot(None, self.ng, "Câu", self.dl)
        goi.assert_not_called()
        self.assertEqual([g[3] for g in self.g02()], ["hong"])
        self.assertEqual((self.tin(), luot._DANG), ([], {}))

    def test_h1_dang_cho_cap_nhat_khong_mo_luot(self):
        with mock.patch.object(capnhat, "dang_cho", return_value=True), mock.patch.object(congai, "goi") as goi:
            with self.assertRaises(trochuyen.ChoCapNhat) as e:
                trochuyen.bat_luot(None, self.ng, "Câu", self.dl)
        goi.assert_not_called()
        self.assertEqual(str(e.exception), "Phần mềm đang chờ cập nhật nên chưa nhận câu hỏi mới. Câu hỏi vẫn ở ô nhập,"
                                           " bạn gửi lại sau khi cập nhật xong.")      # QĐ352, đúng từng ký tự
        self.assertEqual((self.g02(), self.tin()), ([], []))                       # QĐ347: 0 dòng G02, 0 tin

    def test_loi_nguon_ghi_hethong_co_tra_loi_cho(self):
        with mock.patch.object(congai, "goi", return_value={"loi": "Chưa có nguồn AI nào dùng được", "bo_qua": []}):
            kq = trochuyen.bat_luot(None, self.ng, "Câu", self.dl)
            self.cho_xong(kq["luot_id"])
        t = self.tin()[1]
        self.assertEqual((t[1], t[3], t[4], t[5]), ("hethong", "loi", kq["hoi"]["id"], None))   # C1; không dấu luot_cat
        self.assertEqual(self.g02()[0][3], "hong")

    def test_dung_ghi_phan_da_co(self):
        def goi(cau, **k):
            congai._NGHE.get().them_chu("Phần đầu")
            raise congai.DaDung()
        with mock.patch.object(congai, "goi", side_effect=goi):
            kq = trochuyen.bat_luot(None, self.ng, "Câu", self.dl)
            lt = self.cho_xong(kq["luot_id"])
        t = self.tin()[1]
        self.assertEqual((t[1], t[2], t[3], t[4]), ("ai", "Phần đầu", "dung", kq["hoi"]["id"]))
        self.assertEqual(self.g02()[0][3], "huy")
        self.assertEqual(len(self.f04("dung_luot")), 1)                           # CDA (6)
        self.assertEqual(lt.su_kien[-1]["loai"], "dung")

    def test_m1_tra_nguoi_nghe_sau_luot(self):
        """SOAT-N0-1 M1: luồng chạy lượt trả `_NGHE` về như cũ bằng token, việc sau trên cùng luồng không mang người nghe."""
        lt = luot.Luot(maso.tao(), maso.tao(), self.ng)
        lt.nghe = congai.Nghe(lt.phat)
        luot.vao_so(lt)
        with mock.patch.object(congai, "goi", side_effect=RuntimeError("lỗi giả")), \
                mock.patch.object(luot, "dong_g02"):
            trochuyen._chay_luot(lt, {"id": "h"}, "câu", None, self.dl)
        self.assertIsNone(congai._NGHE.get())
        self.assertEqual(lt.su_kien[-1]["loai"], "loi")
        self.assertFalse(luot.dang_trong_so(lt.id))

    def test_gui_dong_bo_khong_nguoi_nghe(self):
        seen = []
        with mock.patch.object(congai, "goi", side_effect=lambda c, **k: seen.append(congai._NGHE.get()) or dict(TL)):
            kq = trochuyen.gui(None, self.ng, "Câu", self.dl)
        self.assertEqual((seen, kq["tra_loi"]["noidung"], kq["tra_loi"]["trangthai"]), ([None], "Trả lời đủ", "xong"))


class KiemDoiChieu(Nen):
    def dung_luot_do(self, boi, tra_loi=None):
        """Giả 01 lượt dở: cuộc + tin hỏi + dòng G02 `dangchay` mang mã khởi động `boi`; `tra_loi` = vai tin trả lời đã có."""
        h, hoi, ma = maso.tao(), maso.tao(), maso.tao()
        self.sql("Bot", "INSERT INTO hoithoai (id, loai, nguoidung_id, trangthai) VALUES (?, 'troly', ?, 'dung')", (h, self.ng))
        cn = ketnoi.mo("Bot", self.dl)
        try:
            trochuyen._ghi_tin(cn, h, "nguoi", "Câu dở", ma=hoi)
            if tra_loi:
                trochuyen._ghi_tin(cn, h, tra_loi, "Đã trả lời", trangthai="xong" if tra_loi == "ai" else "loi", tra_loi_cho=hoi)
        finally:
            cn.close()
        self.sql("Viecnen", "INSERT INTO viecnen (id, loai, goi_ai, trangthai, khoa_chongtrung, giu_boi, ketqua_json)"
                            " VALUES (?, 'trochuyen', 1, 'dangchay', ?, ?, ?)",
                 (ma, "trochuyen:" + h, boi, json.dumps({"hoithoai_id": h, "tin_hoi_id": hoi})))
        return ma, hoi

    def test_khoi_dong_ghi_tin_bi_cat(self):
        ma, hoi = self.dung_luot_do("khoi-dong-cu")
        self.assertEqual(luot.don_khi_khoidong(self.dl), 1)
        t = self.tin()[-1]
        self.assertEqual((t[1], t[2], t[3], t[4], json.loads(t[5])),
                         ("hethong", "Câu trả lời bị ngắt vì phần mềm khởi động lại. Bạn gửi lại câu hỏi.", "loi", hoi,
                          {"loai": "luot_cat"}))                                  # QĐ352 Đ2, QĐ350
        g = self.g02()[0]
        self.assertEqual(g[3], "hong")
        self.assertTrue(g[6])
        self.assertEqual(len(self.f04("bo_luot_do")), 1)
        self.assertEqual(luot.don_khi_khoidong(self.dl), 0)                       # chạy lại không ghi thêm
        self.assertEqual((len(self.tin()), len(self.f04("bo_luot_do"))), (2, 1))

    def test_khoi_dong_da_co_tra_loi_chi_dong_xong(self):
        for vai in ("ai", "hethong"):                                            # C1: cả tin lỗi cũng là đã có trả lời
            self.dung_luot_do("khoi-dong-cu", tra_loi=vai)
        truoc = len(self.tin())
        luot.don_khi_khoidong(self.dl)
        self.assertEqual(len(self.tin()), truoc)
        self.assertEqual([g[3] for g in self.g02()], ["xong", "xong"])

    def test_h2_chi_dong_dong_khong_con_trong_so(self):
        mo_coi, _ = self.dung_luot_do(luot.BOOT_ID)
        dang, _ = self.dung_luot_do(luot.BOOT_ID)
        khac, _ = self.dung_luot_do("khoi-dong-cu")
        lt = luot.Luot(dang, "h", self.ng)
        luot.vao_so(lt)                                                           # lượt còn trong sổ: đang chờ chỗ / nguồn 02
        self.assertEqual(luot.dong_luot_ket(self.dl), 1)
        tt = {g[0]: g[3] for g in self.g02()}
        self.assertEqual((tt[mo_coi], tt[dang], tt[khac]), ("hong", "dangchay", "dangchay"))
        self.assertEqual(len(self.f04("bo_luot_do")), 1)                          # S3
        self.assertEqual(luot.dong_luot_ket(self.dl), 0)

    def test_c2_dong_da_dong_noi_khac_thi_khong_ghi_tin(self):
        ma, _ = self.dung_luot_do(luot.BOOT_ID)
        luot.dong_g02(ma, "xong", thumuc=self.dl)                                 # lượt vừa tự đóng giữa 02 bước
        truoc = len(self.tin())
        self.assertIsNone(luot.doi_chieu_dong(ma, self.g02()[0][7], self.dl))
        self.assertEqual(len(self.tin()), truoc)


class KiemXoaDongCu(Nen):
    def test_x1_x4(self):
        bay = datetime.now(MUIGIO_VN)
        luc = lambda gio: (bay - timedelta(hours=gio)).isoformat(timespec="seconds")   # noqa: E731
        dong = [("cu", "trochuyen", "xong", luc(25)), ("moi", "trochuyen", "huy", luc(23)), ("chay", "trochuyen", "dangchay", None),
                ("khac", "baocao", "xong", luc(30)), ("trong", "trochuyen", "hong", None), ("suco", "trochuyen", "hong", luc(26))]
        for d in dong:
            self.sql("Viecnen", "INSERT INTO viecnen (id, loai, goi_ai, trangthai, xong_luc) VALUES (?, ?, 1, ?, ?)", d)
        self.sql("Viecnen", "INSERT INTO suco (id, viecnen_id) VALUES (?, 'suco')", (maso.tao(),))
        f04 = self.sql("Nhatky", "SELECT count(*) FROM nhatky_thaotac")[0][0]
        self.assertEqual(luot.xoa_dong_cu(self.dl), 1)                            # X3: dòng có sự cố trỏ tới giữ, không lỗi
        self.assertEqual(sorted(g[0] for g in self.g02()), ["chay", "khac", "moi", "suco", "trong"])
        self.assertEqual(luot.xoa_dong_cu(self.dl), 0)                            # X4: chạy lại không đổi gì
        self.assertEqual(self.sql("Nhatky", "SELECT count(*) FROM nhatky_thaotac")[0][0], f04)   # không ghi F04


class KiemDuongGoi(Nen):
    def setUp(self):
        super().setUp()
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.web import api
        self.nguoi = {"nguoidung_id": self.ng}
        khoidong.app.dependency_overrides[api.can_dang_nhap] = lambda: self.nguoi
        self.addCleanup(khoidong.app.dependency_overrides.clear)
        self.c = TestClient(khoidong.app)

    def doc(self, duong, **k):
        with self.c.stream("GET", duong, **k) as r:
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers["cache-control"], "no-cache")
            self.assertTrue(r.headers["content-type"].startswith("text/event-stream"))
            return [json.loads(d[6:]) for d in r.iter_lines() if d.startswith("data: ")]

    def test_gui_tra_ngay_roi_theo_luong(self):
        with mock.patch.object(congai, "goi", side_effect=lambda c, **k: time.sleep(0.3) or dict(TL)):
            r = self.c.post("/api/trochuyen", json={"noidung": "Câu 01", "nen": True}, headers={"X-IGM360": "1"})
            self.assertEqual(r.status_code, 200, r.text)
            kq = r.json()
            ev = self.doc(f"/api/trochuyen/luot/{kq['luot_id']}/sukien")
        self.assertEqual((ev[0]["loai"], ev[-1]["loai"], ev[-1]["tra_loi"]["noidung"]), ("bat_dau", "xong", "Trả lời đủ"))
        lai = self.doc(f"/api/trochuyen/luot/{kq['luot_id']}/sukien", headers={"Last-Event-ID": "1"})
        self.assertEqual([e["so"] for e in lai], [e["so"] for e in ev[1:]])       # phát lại từ sau số 1
        self.nguoi = {"nguoidung_id": "nguoi-khac"}
        self.assertEqual(self.c.get(f"/api/trochuyen/luot/{kq['luot_id']}/sukien").status_code, 404)

    def test_n2_gui_trung_luot_tra_409(self):
        cho = threading.Event()
        with mock.patch.object(congai, "goi", side_effect=lambda c, **k: cho.wait(5) and dict(TL)):
            kq = self.c.post("/api/trochuyen", json={"noidung": "Câu", "nen": True}, headers={"X-IGM360": "1"}).json()
            r = self.c.post("/api/trochuyen", json={"noidung": "Câu 02", "hoithoai_id": kq["hoithoai_id"]},
                            headers={"X-IGM360": "1"})
            cho.set()
            self.cho_xong(kq["luot_id"])
        self.assertEqual((r.status_code, r.json()["detail"]), (409, "AI đang trả lời câu hỏi trước. Bạn gửi câu mới khi câu trả lời xong"))   # QĐ358

    def test_khong_gui_nen_thi_tra_loi_dong_bo_nhu_cu(self):
        with mock.patch.object(congai, "goi", return_value=dict(TL)):
            r = self.c.post("/api/trochuyen", json={"noidung": "Câu"}, headers={"X-IGM360": "1"}).json()
        self.assertEqual((r["tra_loi"]["noidung"], "luot_id" in r), ("Trả lời đủ", False))

    def test_h1_tra_409_kem_ma(self):
        with mock.patch.object(capnhat, "dang_cho", return_value=True):
            r = self.c.post("/api/trochuyen", json={"noidung": "Câu", "nen": True}, headers={"X-IGM360": "1"})
            r2 = self.c.post("/api/trochuyen", json={"noidung": "Câu"}, headers={"X-IGM360": "1"})   # đường đồng bộ cũ cũng chặn
        self.assertEqual((r.status_code, r.json()["ma"], r2.status_code), (409, "cho_capnhat", 409))
        self.assertEqual(r.json()["detail"], luot.CHU_CHO_CAPNHAT)

    def test_xem_tra_luot_dang_va_phu(self):
        cho = threading.Event()
        with mock.patch.object(congai, "goi", side_effect=lambda c, **k: cho.wait(5) and dict(TL)):
            kq = self.c.post("/api/trochuyen", json={"noidung": "Câu", "nen": True}, headers={"X-IGM360": "1"}).json()
            x = self.c.get("/api/trochuyen/" + kq["hoithoai_id"]).json()
            self.assertEqual(x["luot_dang"], kq["luot_id"])
            cho.set()
            self.cho_xong(kq["luot_id"])
        x = self.c.get("/api/trochuyen/" + kq["hoithoai_id"]).json()
        self.assertIsNone(x["luot_dang"])
        self.assertEqual([(t["vai"], t["trangthai"], t["phu"]) for t in x["tinnhan"]], [("nguoi", None, None), ("ai", "xong", None)])


class KiemCho(unittest.TestCase):
    def test_lich_goi_rieng_bang_to_thread(self):
        ma = (Path(__file__).resolve().parents[2] / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("await asyncio.to_thread(luot.dong_luot_ket)", ma)          # S4
        self.assertIn("await asyncio.to_thread(luot.xoa_dong_cu)", ma)            # X4
        kd = (Path(__file__).resolve().parents[2] / "maychu/khoidong.py").read_text(encoding="utf-8")
        self.assertLess(kd.index('if not antoan.CHE_DO["an_toan"]:'), kd.index("luot.don_khi_khoidong()"))


if __name__ == "__main__":
    unittest.main()
