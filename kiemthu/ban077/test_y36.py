"""Bài kiểm bản 0.7.7 (QĐ192, Y36; CDA K-VN Đ1–Đ3): đo hạn mức bị động (0 lượt gọi thêm, không đọc khoá đăng nhập) và
dòng "Việc nền · toàn hệ thống". Dữ liệu giả, không gọi CLI thật."""
import json
import os
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, danhmuc_mohinh as dm
from kiemthu.ban075.test_y31 import Nen

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"


def _luc(**kw) -> str:
    return (datetime.now(MUIGIO_VN) + timedelta(**kw)).isoformat(timespec="seconds")


class KiemDoBiDong(Nen):
    def g06(self, nid):
        cn = ketnoi.mo("Viecnen")
        try:
            return cn.execute("SELECT tyle_5gio, tyle_tuan, do_luc FROM nguon_ai WHERE id = ?", (nid,)).fetchone()
        finally:
            cn.close()

    def phien(self, pct, ten="rollout-1.jsonl"):
        p = self.g / "codex" / "sessions" / "2026" / "11" / "23"
        p.mkdir(parents=True, exist_ok=True)
        (p / ten).write_text(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
            "primary": {"used_percent": pct, "window_minutes": 300, "resets_at": 4102444800},
            "secondary": {"used_percent": 40.0, "window_minutes": 10080, "resets_at": 4102444800}}}}) + "\n", encoding="utf-8")
        return p / ten

    def test_quet_codex_khong_goi_ai(self):
        nid = self.nguon("goi_chatgpt_01", "goi", 1, "openai")
        with mock.patch.object(congai, "_goi_chatgpt", side_effect=AssertionError("không được gọi AI")), \
                mock.patch.object(congai, "_goi_claude", side_effect=AssertionError("không được gọi AI")):
            self.assertEqual(congai.quet_codex(), {"goi_chatgpt_01": "khong_co"})   # chưa có tệp phiên
            tep = self.phien(12.0)
            self.assertEqual(congai.quet_codex(), {"goi_chatgpt_01": "ghi"})
            tl5, tlt, do = self.g06(nid)
            self.assertEqual((tl5, tlt), (12, 40))
            self.assertEqual(do, datetime.fromtimestamp(tep.stat().st_mtime, MUIGIO_VN).isoformat(timespec="seconds"))   # giờ của tệp
            self.assertEqual(congai.quet_codex(), {"goi_chatgpt_01": "khong_doi"})   # tệp không đổi: không đọc lại
            tep = self.phien(55.0)
            os.utime(tep, (time.time() + 5, time.time() + 5))
            self.assertEqual(congai.quet_codex(), {"goi_chatgpt_01": "ghi"})
            self.assertEqual(self.g06(nid)[0], 55)

    def test_qua_gio_dat_lai_hien_0(self):
        nid = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET tyle_5gio = 80, datlai_5gio_luc = ?, tyle_tuan = 60, datlai_tuan_luc = ? WHERE id = ?",
                       (_luc(minutes=-1), _luc(days=2), nid))
        finally:
            cn.close()
        d = next(x for x in dg.danh_sach() if x["id"] == nid)
        self.assertEqual((d["tyle_5gio"], d["datlai_5gio_luc"], d["tyle_tuan"]), (0, None, 60))   # 05 giờ đã đặt lại; tuần chưa

    def test_het_theo_mo_hinh(self):
        c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        dm.danh_sach()
        goi, het = [], {"opus"}

        def claude(tk, cau, mohinh):
            goi.append(mohinh)
            if mohinh in het:
                raise congai.HetHanMuc("limit reached", {"tuan": {"pct": 60, "datlai": time.time() + 7200}})   # từ chối riêng mô hình, tài khoản chưa đầy
            return {"chu": "ok", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {}, "mohinh_bao": None}
        with mock.patch.object(congai, "_goi_claude", side_effect=claude):
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
            self.assertEqual((goi, kq["ghim_hong"]["het_hanmuc"]), (["opus", None], True))
            self.assertGreater(congai.het_mo_hinh(c1, "opus"), time.time() + 7000)   # giờ đặt lại hãng báo
            goi.clear()
            congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
            self.assertEqual(goi, [None])                     # Opus còn "hết": không gọi lại, dùng mặc định
            self.assertEqual(congai.het_mo_hinh(c1, "sonnet"), 0)   # mô hình khác không bị đánh dấu
            het.clear()
            with mock.patch.object(congai.time, "time", return_value=time.time() + 8000):   # qua giờ dùng lại
                self.assertEqual(congai.het_mo_hinh(c1, "opus"), 0)
            congai._HET_MH.clear()
            goi.clear()
            congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
            self.assertEqual(goi, ["opus"])

    def test_het_mac_dinh_01_gio_khi_khong_bao(self):
        c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        congai.ghi_het_mo_hinh(c1, "opus", {})
        self.assertAlmostEqual(congai.het_mo_hinh(c1, "opus"), time.time() + congai.HET_MACDINH_GIAY, delta=5)


class KiemViecNen(Nen):
    def setUp(self):
        super().setUp()
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.g1 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        dm.danh_sach()
        self.goi = []
        self.vas3 = [mock.patch.object(congai, "_goi_claude", side_effect=lambda tk, cau, mh: self.goi.append(("claude", mh)) or self._ok()),
                     mock.patch.object(congai, "_goi_chatgpt", side_effect=lambda tk, cau, mh: self.goi.append(("gpt", mh)) or self._ok())]
        for v in self.vas3:
            v.start()

    def tearDown(self):
        for v in self.vas3:
            v.stop()
        super().tearDown()

    @staticmethod
    def _ok():
        return {"chu": "ok", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {}, "mohinh_bao": None}

    def test_chua_dat_mac_dinh_theo_thu_tu_nguon(self):
        self.assertIn("viecnen_chung", dm.danh_sach()["loai_viec"])
        self.assertIsNone(dm.macdinh_khoa("dexuat"))                    # bậc (c): chưa đặt gì
        congai.goi("hỏi", loai_viec="dexuat")
        self.assertEqual(self.goi, [("claude", None)])                  # theo thứ tự nguồn Đ5

    def test_03_bac(self):
        dm.dat_macdinh("viecnen_chung", khoa="goi_chatgpt|")
        self.assertEqual(dm.macdinh_khoa("dexuat"), ("goi_chatgpt", None))       # bậc (b): theo việc nền toàn hệ thống
        self.assertEqual(dm.macdinh_khoa("baocaosang"), ("goi_chatgpt", None))
        self.assertIsNone(dm.macdinh_khoa("trochuyen"))                          # trò chuyện không theo
        dm.dat_macdinh("dexuat", khoa="goi_claude|opus")
        self.assertEqual(dm.macdinh_khoa("dexuat"), ("goi_claude", "opus"))      # bậc (a): đặt riêng thắng
        congai.goi("hỏi", loai_viec="baocaosang")
        self.assertEqual(self.goi[-1], ("gpt", None))
        congai.goi("hỏi", loai_viec="dexuat")
        self.assertEqual(self.goi[-1], ("claude", "opus"))

    def test_bac_mat_xuong_bac_sau(self):
        dm.dat_macdinh("viecnen_chung", khoa="goi_chatgpt|")
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET trangthai = 'ngung' WHERE id = ?", (self.g1,))
        finally:
            cn.close()
        self.assertIsNone(dm.macdinh_khoa("dexuat"))                   # nhóm đã mất: xuống bậc (c)

    def test_viec_nen_khong_doc_ghim(self):
        congai.goi("hỏi", loai_viec="dexuat", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [("claude", None)])                  # Đ2: bỏ ghim ở cổng
        self.goi.clear()
        congai.goi("hỏi", viecnen_id="vn_gia", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [("claude", None)])
        self.goi.clear()
        congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [("claude", "opus")])                # trò chuyện vẫn đọc ghim


class KiemGiaoDien077(unittest.TestCase):
    def test_lam_moi_60_giay_va_m2(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        html = (GD / "index.html").read_text(encoding="utf-8")
        self.assertIn("lamMoi13(), demSo(); }, 60e3);", js)
        self.assertEqual(js.count("demSo(); }, 60"), 1)
        for chu in ("if (S.trang !== '13' || !D.md) return;", "Object.values(D.dn || {}).some(x => x && x.url)",
                    "$$('.lop').some(e => !e.hidden)", "a.closest('#p13')"):
            self.assertIn(chu, js)
        self.assertIn(".mb .thongbao{position:fixed;left:16px;right:16px;bottom:76px;transform:none;max-width:none}", html)   # M2
        self.assertIn('<div class="t12 phu">Cất ở mục&nbsp;Két&nbsp;khoá</div>', js)   # M1: tự xuống dòng được
        lich = (GOC / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("await asyncio.to_thread(congai.quet_codex)", lich)
        cg = (GOC / "maychu/hethong/mohinh/congai.py").read_text(encoding="utf-8")
        self.assertNotIn("credentials", cg)                             # không đọc khoá đăng nhập
        self.assertNotIn("oauth/usage", cg)


if __name__ == "__main__":
    unittest.main()
