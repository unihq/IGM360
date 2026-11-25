"""Bài kiểm bản 0.7.7 (QĐ192, Y36; CDA K-VN Đ1–Đ3): đo hạn mức bị động (0 lượt gọi thêm, không đọc khóa đăng nhập) và
dòng "Việc nền chung" (QĐ194). Dữ liệu giả, không gọi CLI thật."""
import json
import os
import subprocess
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
        self.assertTrue(d["da_datlai_luc"])                                                     # Z12 (3): "Đã đặt lại lúc …"

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
        self.assertEqual(dm.macdinh_khoa("dexuat"), ("goi_chatgpt", None))       # bậc (b): theo "Việc nền chung"
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
        self.assertIn('<div class="t12 phu">Cất ở mục&nbsp;Két&nbsp;khóa</div>', js)   # M1: tự xuống dòng được
        lich = (GOC / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("await asyncio.to_thread(congai.quet_codex)", lich)
        cg = (GOC / "maychu/hethong/mohinh/congai.py").read_text(encoding="utf-8")
        self.assertNotIn("credentials", cg)                             # không đọc khóa đăng nhập
        self.assertNotIn("oauth/usage", cg)


class KiemP1(Nen):
    """Y36b P1: hãng từ chối riêng khung 01 mô hình (CLI Claude: rateLimitType seven_day_opus) thì chỉ ghi dấu mô hình,
    tài khoản vẫn dùng mô hình khác. Giả dòng stream-json của CLI (không chạy CLI thật)."""
    def setUp(self):
        super().setUp()
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        dm.danh_sach()
        self.goi, self.khung, self.dat = [], "seven_day_opus", int(time.time()) + 7200

    def chay(self, lenh, env, vao=None, giay=None):
        ma = lenh[lenh.index("--model") + 1] if "--model" in lenh else None
        self.goi.append(ma)
        dong = [{"type": "system", "subtype": "init", "model": "claude-" + (ma or "sonnet") + "-9"}]
        if ma == "opus" or (self.khung == "five_hour"):
            dong += [{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": self.khung, "resetsAt": self.dat}},
                     {"type": "result", "subtype": "success", "is_error": True, "result": "limit reached"}]
        else:
            dong += [{"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "rateLimitType": "five_hour", "utilization": 0.3, "resetsAt": self.dat}},
                     {"type": "result", "subtype": "success", "result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}}]
        return subprocess.CompletedProcess(lenh, 0, "\n".join(json.dumps(x) for x in dong), "")

    def het_tk(self):
        cn = ketnoi.mo("Viecnen")
        try:
            return cn.execute("SELECT da_het_luc FROM nguon_ai WHERE id = ?", (self.c1,)).fetchone()[0]
        finally:
            cn.close()

    def test_doc_khung_tu_cli(self):
        h = congai.han_muc_claude
        self.assertEqual(h({"status": "rejected", "rateLimitType": "seven_day_opus", "resetsAt": 4102444800}),
                         {"het_mh": {"loai": "seven_day_opus", "datlai": 4102444800}})
        self.assertTrue(h({"status": "rejected", "rateLimitType": "five_hour", "utilization": 1.0, "resetsAt": 4102444800})["het"])
        self.assertEqual(h({"status": "rejected"}), {"het_khongro": {"datlai": None}})
        self.assertEqual(h({"status": "rejected", "resetsAt": 4102444800}), {"het_khongro": {"datlai": 4102444800}})   # Y36c P3

    def test_opus_het_sonnet_van_dung(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
            self.assertEqual(self.goi, ["opus", None])                  # Opus từ chối → mặc định cùng tài khoản trả lời
            self.assertTrue(kq["ghim_hong"]["het_hanmuc"])
            self.assertFalse(self.het_tk())                             # KHÔNG đánh dấu cả tài khoản
            self.assertEqual(congai.het_mo_hinh(self.c1, "opus"), self.dat)   # giờ đặt lại của khung Opus
            ds = congai.ds_het_mo_hinh(self.c1)
            self.assertEqual([(x["ma"], x["ten_khung"]) for x in ds], [("opus", "Opus")])
            self.goi.clear()
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|sonnet")
            self.assertEqual((self.goi, kq["chu"]), (["sonnet"], "ok"))   # Sonnet cùng tài khoản dùng được

    def test_mac_dinh_la_opus_het(self):
        self.khung = "seven_day_opus"
        with mock.patch.object(congai, "_chay", side_effect=lambda lenh, env, vao=None, giay=None: self.chay(lenh + ["--model", "opus"], env)):
            kq = congai.goi("hỏi", loai_viec="trochuyen")
            self.assertFalse(kq.get("chu"))   # 01 tài khoản, mô hình mặc định đang hết: không có câu trả lời
        self.assertFalse(self.het_tk())
        self.assertGreater(congai.het_mo_hinh(self.c1, None), time.time())   # "mặc định của nguồn" ghi khóa rỗng
        self.assertEqual(congai.ds_het_mo_hinh(self.c1)[0]["ma"], None)

    def test_ca_tai_khoan_het_van_danh_dau(self):
        self.khung = "five_hour"
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
            self.assertFalse(kq.get("chu"))
        self.assertEqual(self.goi, ["opus"])          # khung 05 giờ của cả tài khoản: không thử tiếp mặc định cùng tài khoản
        self.assertEqual(self.het_tk(), 1)

    def test_giao_dien(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        html = (GD / "index.html").read_text(encoding="utf-8")
        self.assertIn("(p == null ? 'chưa&nbsp;đo' : Math.round(p) + '%')", js)        # N1: "8%", không "08%"
        self.assertNotIn("hai(Math.round(p)) + '%'", js)
        self.assertIn(".ten-i{display:flex;align-items:center;gap:4px}", html)        # N2: (i) cùng dòng với tên
        self.assertIn("const CUM = ['Việc nền',", js)
        self.assertIn("' của tài khoản ' + tk + ' hết hạn mức' + (m.den ? ' đến ' + denLuc(m.den) : '')", js)
        self.assertIn("'<div class=\"tk-dong\"' + tieuHetMh(n, x.taikhoan) + '>", js)
        api = (GOC / "maychu/web/api.py").read_text(encoding="utf-8")
        self.assertIn('n["het_mh"] = congai.ds_het_mo_hinh(n["id"])', api)


TRA = {"chu": "ok", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {}, "mohinh_bao": None}


class KiemY36c(Nen):
    """Y36c (CDO U11b): P2 mốc nghỉ riêng 01 giờ khi hãng không báo khung; P3 có resetsAt thì dùng; N4 chữ dự phòng
    theo mô hình; dòng vàng cho lượt thường đã sang hãng khác. Giả kết quả CLI qua han_muc_claude như đường thật."""
    def setUp(self):
        super().setUp()
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.goi = []

    def claude(self, tu_choi):
        """tu_choi: {(tài khoản, mô hình): rate_limit_info}; mô hình None = mặc định của nguồn."""
        def f(tk, cau, mohinh):
            self.goi.append((tk, mohinh))
            info = tu_choi.get((tk, mohinh))
            if info is not None:
                hm = congai.han_muc_claude(info)
                hm["mh_bao"] = "claude-" + (mohinh or "opus") + "-9"
                raise congai.HetHanMuc("limit reached", hm)
            return dict(TRA, mohinh_bao="claude-" + (mohinh or "sonnet") + "-9")
        return f

    def g06_cu(self, nid):
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET datlai_5gio_luc = ? WHERE id = ?", (_luc(hours=-3), nid))   # giờ đặt lại cũ đã qua
        finally:
            cn.close()

    def test_p2_khong_bao_khung_nghi_01_gio(self):
        self.g06_cu(self.c1)
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude({(1, None): {"status": "rejected"}})):
            kq = congai.goi("hỏi", loai_viec="trochuyen")
            self.assertIn("loi", kq)
            self.assertAlmostEqual(congai.het_tai_khoan(self.c1), time.time() + 3600, delta=5)   # tính từ lúc bị từ chối
            self.goi.clear()
            congai.goi("hỏi", loai_viec="trochuyen")
            self.assertEqual(self.goi, [])                       # không bỏ qua dấu vì giờ đặt lại cũ đã qua
            with mock.patch.object(congai.time, "time", return_value=time.time() + 3700):
                self.assertEqual(congai.het_tai_khoan(self.c1), 0)

    def test_p3_co_resetsat_thi_dung(self):
        dat = int(time.time()) + 5400
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude({(1, None): {"status": "rejected", "resetsAt": dat}})):
            congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(congai.het_tai_khoan(self.c1), dat)
        congai._HET_TK.clear()
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET da_het_luc = 0 WHERE id = ?", (self.c1,))   # bỏ dấu cả tài khoản của bước trước
        finally:
            cn.close()
        dm.danh_sach()
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude({(1, "opus"): {"status": "rejected", "resetsAt": dat}})):
            congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")   # lượt ghim, không rõ khung
        self.assertEqual(congai.het_mo_hinh(self.c1, "opus"), dat)
        self.assertEqual(congai.het_tai_khoan(self.c1), 0)

    def test_khoa_api_429_khong_nghi_01_gio(self):
        k = self.nguon("khoa_openai", "khoa_api", 2, "openai", tran=5)
        with mock.patch.object(congai, "dung_duoc", return_value=(True, "")), \
                mock.patch.object(congai, "_goi_khoa", side_effect=congai.HetHanMuc("OpenAI báo vượt hạn mức (429)")), \
                mock.patch.object(congai, "_goi_claude", side_effect=congai.HetHanMuc("x", {"het": True})):
            congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(congai.het_tai_khoan(k), 0)
        self.assertGreater(congai.het_tai_khoan(self.c1), time.time())

    def test_n4_du_phong_ghi_ten_mo_hinh(self):
        c2 = self.nguon("goi_claude_02", "goi", 1, "anthropic")
        dm.danh_sach()
        dat = int(time.time()) + 3 * 86400
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude(
                {(1, "opus"): {"status": "rejected", "rateLimitType": "seven_day_opus", "resetsAt": dat}})):
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [(1, "opus"), (2, "opus")])
        self.assertEqual((kq["nguon_id"], kq["chay_tk"]), (c2, 2))
        dp = kq["du_phong"]
        self.assertEqual((dp["tk"], dp["rieng"], dp["ma"], dp["ten_khung"]), (1, True, "opus", "Opus"))
        self.assertEqual(dp["den"], datetime.fromtimestamp(dat, MUIGIO_VN).isoformat(timespec="seconds"))

    def test_luot_thuong_sang_hang_khac_co_dong_vang(self):
        c2 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude(
                {(1, None): {"status": "rejected", "rateLimitType": "seven_day_opus", "resetsAt": int(time.time()) + 600}})), \
                mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA, mohinh_bao="gpt-5-codex")):
            kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(kq["nguon_id"], c2)
        self.assertIsNone(kq["ghim_hong"])
        self.assertEqual(kq["md_hong"], {"ma": None, "ten_khung": "Opus", "bao": "claude-opus-9", "nguon_id": self.c1, "het_hanmuc": True})
        # cùng hãng (tài khoản dự phòng) thì không có dòng vàng, chỉ chữ rê chuột
        congai._HET_MH.clear()
        congai._HET_TK.clear()
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude({(1, None): {"status": "rejected", "rateLimitType": "five_hour"}})):
            kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual((kq["chay_tk"], kq["md_hong"]), (2, None))

    def test_giao_dien(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        for chu in ("const denLuc = iso => !iso ? '' : gio(iso) + (String(iso).slice(0, 10) !== homNay() ? ' ngày ' + iso.slice(8, 10) + '/' + iso.slice(5, 7) : '');",
                    "' (dự phòng, ' + (dp.rieng ? chuHetMh(dp, timNguon(x.nguon_id), dp.tk)",
                    "const g = x.ghim_hong || x.md_hong,",
                    "+ (x.ghim_hong || x.md_hong ? '<div class=\"tn-meta mh-vang\"'",
                    "theo dòng \"' + nbsp(LV.viecnen_chung) + '\"'",
                    "'Chọn mô hình · ' + nbsp(D.dsmh.loai_viec[d.doimd])"):
            self.assertIn(chu, js, chu)
        tc = (GOC / "maychu/hethong/mohinh/trochuyen.py").read_text(encoding="utf-8")
        self.assertIn('tl["md_hong"] = kq.get("md_hong")', tc)

    @unittest.skipUnless(__import__("shutil").which("node"), "máy không có node")
    def test_den_luc_khac_ngay(self):
        import subprocess as sp
        import tempfile
        js = (GD / "app.js").read_text(encoding="utf-8")
        lay = lambda dau: js[js.index(dau):js.index("\n", js.index(dau))]
        ma = "\n".join([lay("const gio = "), lay("const homNay = "), lay("const denLuc = "),
                         "const h = homNay(); console.log(JSON.stringify([denLuc(h + 'T20:45:00+07:00'), denLuc('2099-11-26T20:45:00+07:00')]));"])
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = sp.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["20:45", "20:45 ngày 26/11"])


class KiemY36d(KiemY36c):
    """Y36d (CDO U11c): giờ nghỉ do 01 chỗ quyết. Lượt bị từ chối → mốc nghỉ riêng (`resetsAt`, không có thì 01 giờ);
    giờ đặt lại đã lưu của cửa sổ CHƯA đầy không còn đè mốc đó; cửa sổ đã đầy theo số đo vẫn chặn. P3b: tài khoản
    đang tạm nghỉ thì dòng vàng ghi lý do tài khoản."""
    test_p2_khong_bao_khung_nghi_01_gio = test_p3_co_resetsat_thi_dung = test_khoa_api_429_khong_nghi_01_gio = None
    test_n4_du_phong_ghi_ten_mo_hinh = test_luot_thuong_sang_hang_khac_co_dong_vang = test_giao_dien = test_den_luc_khac_ngay = None

    def dat_g06(self, **cot):
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute(f"UPDATE nguon_ai SET {', '.join(k + ' = ?' for k in cot)} WHERE id = ?", (*cot.values(), self.c1))
        finally:
            cn.close()

    def dung(self, sau=0):
        d = next(x for x in congai._nguon() if x["id"] == self.c1)
        with mock.patch.object(congai.time, "time", return_value=time.time() + sau):
            return congai.dung_duoc(d)[0]

    def tu_choi(self, info):
        with mock.patch.object(congai, "_goi_claude", side_effect=self.claude({(1, None): info})):
            congai.goi("hỏi", loai_viec="trochuyen")

    def test_resetsat_60_giay_khung_chua_day_gio_xa(self):
        self.dat_g06(tyle_5gio=40, datlai_5gio_luc=_luc(hours=3), do_luc=_luc(minutes=-5))   # khung chưa đầy, giờ đặt lại xa
        self.tu_choi({"status": "rejected", "resetsAt": int(time.time()) + 60})
        self.assertAlmostEqual(congai.het_tai_khoan(self.c1), time.time() + 60, delta=3)
        self.assertFalse(self.dung())
        self.assertTrue(self.dung(120))                 # hãng mở lại sau 60 giây: 02 phút sau dùng được, không chặn tới 03 giờ
        cn = ketnoi.mo("Viecnen")
        try:
            self.assertEqual(cn.execute("SELECT da_het_luc FROM nguon_ai WHERE id = ?", (self.c1,)).fetchone()[0], 1)   # vẫn ghi lại
        finally:
            cn.close()

    def test_gio_dat_lai_cu_da_qua(self):            # ca U11b: dấu không bị bỏ qua
        self.dat_g06(tyle_5gio=40, datlai_5gio_luc=_luc(hours=-3), do_luc=_luc(hours=-4))
        self.tu_choi({"status": "rejected"})
        self.assertFalse(self.dung())
        self.assertFalse(self.dung(3500))
        self.assertTrue(self.dung(3700))                # không báo giờ: nghỉ 01 giờ

    def test_khung_chua_day_gio_xa_khong_bao_gio(self):
        self.dat_g06(tyle_tuan=70, datlai_tuan_luc=_luc(days=4), do_luc=_luc(minutes=-1))
        self.tu_choi({"status": "rejected"})
        self.assertTrue(self.dung(3700))                # 01 giờ, không phải 04 ngày theo giờ đặt lại của khung tuần chưa đầy

    def test_khung_da_day_van_chan(self):
        self.dat_g06(tyle_5gio=100, datlai_5gio_luc=_luc(hours=2), do_luc=_luc(minutes=-1))
        self.assertFalse(self.dung())                   # số đo cửa sổ đầy: chặn tới giờ đặt lại
        self.dat_g06(tyle_5gio=100, datlai_5gio_luc=None, do_luc=_luc(minutes=-30))
        self.assertFalse(self.dung())                   # đầy mà không có giờ đặt lại: 60 phút từ lần đo
        self.dat_g06(do_luc=_luc(minutes=-61))
        self.assertTrue(self.dung())
        self.dat_g06(tyle_5gio=40, datlai_5gio_luc=_luc(hours=2), da_het_luc=1)
        self.assertTrue(self.dung())                    # cờ cũ da_het_luc không còn chặn

    def test_p3b_tai_khoan_tam_nghi(self):
        c2 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        den = congai.ghi_het_tai_khoan(self.c1, time.time() + 1800)
        with mock.patch.object(congai, "_goi_claude", side_effect=AssertionError("tài khoản đang nghỉ, không gọi")), \
                mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA, mohinh_bao="gpt-5-codex")):
            kq = congai.goi("hỏi", loai_viec="trochuyen")
            self.assertEqual(kq["nguon_id"], c2)
            g = kq["md_hong"]
            self.assertEqual((g["tk_nghi"], g["nguon_id"], g["den"]), (True, self.c1, datetime.fromtimestamp(den, MUIGIO_VN).isoformat(timespec="seconds")))
            dm.danh_sach()
            kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|sonnet")   # Sonnet chưa bị từ chối
            self.assertEqual(kq["nguon_id"], c2)
            self.assertTrue(kq["ghim_hong"]["tk_nghi"])
            self.assertEqual(kq["ghim_hong"]["nguon_id"], self.c1)
        js = (GD / "app.js").read_text(encoding="utf-8")
        for chu in ("const chuNghi = (g, n0) => 'Tài khoản ' + (n0 && n0.goi ? GOI_NGAN[n0.goi].replace('Gói ', '') : n0 ? tenNguon(n0) : '') + ' đang tạm nghỉ' + (g.den ? ' đến ' + denLuc(g.den) : '');",
                    "if (g.tk_nghi) return esc(chuNghi(g, n0)) + ', đã dùng '",
                    "const tieu = hong && hong.nghi ? chuNghi(hong.nghi, timNguon(hong.nghi.nguon_id)) + ' · tạm dùng '",
                    "nghi: tl.ghim_hong.tk_nghi ? {den: tl.ghim_hong.den, nguon_id: tl.ghim_hong.nguon_id} : null};"):
            self.assertIn(chu, js, chu)


class KiemY36e(Nen):
    """Y36e (QĐ195, lỗi H17): trò chuyện của anh gọi Claude không trần lượt, được tra web, cấm lệnh máy và ghi/sửa tệp;
    Gọi thử, việc nền giữ 01 lượt; lỗi ghi đúng loại (`subtype` + `errors`). Giả đầu ra CLI qua `_chay`."""
    def setUp(self):
        super().setUp()
        # tài khoản 02 trở lên tạo thư mục riêng: đặt trong thư mục tạm (Linux không ghi được /home/igm/.claude)
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_CLAUDE": str(self.g / "claude")})
        bien.start()
        self.addCleanup(bien.stop)
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        dm.danh_sach()
        self.lenh, self.dau_ra = [], None

    def chay(self, lenh, env, vao=None, giay=None):
        self.lenh.append(lenh)
        dong = self.dau_ra or [{"type": "result", "subtype": "success", "result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}}]
        return subprocess.CompletedProcess(lenh, 0, "\n".join(json.dumps(x) for x in dong), "")

    def kiem_tra_web(self, l):
        self.assertNotIn("--max-turns", l)
        self.assertEqual(l[l.index("--tools") + 1], "WebSearch,WebFetch")
        self.assertEqual(l[l.index("--allowedTools") + 1], "WebSearch,WebFetch")
        cam = l[l.index("--disallowedTools") + 1].split(",")
        for x in ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit"):
            self.assertIn(x, cam)
        self.assertIn("--strict-mcp-config", l)

    def test_a_lenh_tro_chuyen_va_viec_khac(self):
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            self.assertEqual(congai.goi("tỷ giá MYR tuần này", loai_viec="trochuyen")["chu"], "ok")
            self.kiem_tra_web(self.lenh[-1])
            for kw in ({"chi_nguon_id": self.c1}, {"loai_viec": "dexuat"}, {"loai_viec": "baocaosang"}, {}):   # Gọi thử, việc nền
                congai.goi("x", **kw)
                l = self.lenh[-1]
                self.assertEqual(l[l.index("--max-turns") + 1], "1", kw)
                self.assertNotIn("--tools", l, kw)
        self.assertFalse(congai._TRA_WEB.get())     # trả lại như cũ sau lượt gọi

    def test_b_loi_dung_loai(self):
        self.dau_ra = [{"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 2,
                        "errors": ["Reached maximum number of turns (1)"]}]
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            kq = congai.goi("x", loai_viec="dexuat")
        b = kq["bo_qua"][0]
        self.assertEqual(b["lydo"], "Claude chạm trần số lượt (error_max_turns: Reached maximum number of turns (1))")
        self.assertEqual((b["loi"], b["loi_ct"]), ("chạm trần số lượt", "error_max_turns: Reached maximum number of turns (1)"))
        self.assertEqual(congai._loi_claude(None, subprocess.CompletedProcess([], 1, '{"type":"x"}', '{"a":1}\nclaude: lỗi mạng\n')),
                         ("không trả kết quả", "claude: lỗi mạng"))   # không lấy chữ JSON

    def test_c_ghim_va_mac_dinh_deu_ap(self):
        self.dau_ra = [{"type": "result", "subtype": "error_during_execution", "is_error": True, "errors": ["boom"]}]
        c2 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        with mock.patch.object(congai, "_chay", side_effect=self.chay), \
                mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA, mohinh_bao="gpt-6-luna")):
            kq = congai.goi("tỷ giá", loai_viec="trochuyen", mohinh_id="goi_claude|sonnet")
        self.assertEqual(kq["nguon_id"], c2)
        self.assertEqual(len(self.lenh), 2)                       # lượt ghim Sonnet rồi lượt mặc định Claude
        self.assertIn("sonnet", self.lenh[0])
        for l in self.lenh:
            self.kiem_tra_web(l)
        g = kq["ghim_hong"]
        self.assertEqual((g["het_hanmuc"], g["loi"], g["loi_ct"]), (False, "lỗi khi chạy", "error_during_execution: boom"))

    def test_n5_man13_tai_khoan_tam_nghi(self):
        n = lambda: next(x for x in dg.danh_sach() if x["id"] == self.c1)
        congai.ghi_het_mo_hinh(self.c1, "opus", {})
        self.assertIsNone(congai.tk_nghi_den(n()))                  # chỉ 01 mô hình hết riêng: giữ chữ "Opus … hết hạn mức"
        den = congai.ghi_het_tai_khoan(self.c1, time.time() + 1800)
        self.assertEqual(congai.tk_nghi_den(n()), datetime.fromtimestamp(den, MUIGIO_VN).isoformat(timespec="seconds"))
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("const tieuHetMh = (n, tk) => n.tk_nghi_den ? ' title=\"' + esc('Tài khoản ' + tk + ' đang tạm nghỉ đến ' + denLuc(n.tk_nghi_den)) + '\"'", js)
        api = (GOC / "maychu/web/api.py").read_text(encoding="utf-8")
        self.assertIn('n["tk_nghi_den"] = congai.tk_nghi_den(n)', api)

    def test_giao_dien_va_thaydoi(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("'chưa dùng được' + (g.loi ? ' (' + esc(nbsp(g.loi)) + ')' : '')", js)
        self.assertIn("((x.ghim_hong || x.md_hong || {}).loi_ct ? ' title=\"' + esc((x.ghim_hong || x.md_hong).loi_ct) + '\"' : '')", js)
        td = (GOC / "THAYDOI.md").read_text(encoding="utf-8").split("## 0.7.6")[0]
        self.assertIn("- Trò chuyện AI qua Claude được tra web", td)


class KiemY36f(KiemY36e):
    """Y36f (CDO U11e): N6 dòng vàng khi lượt thường lỗi (không phải hạn mức) rồi sang hãng khác; N7 bỏ "cho tới khi
    đặt lại" khi lý do không phải hạn mức; N8 dự phòng vì cả tài khoản tạm nghỉ ghi "đang tạm nghỉ"."""
    test_a_lenh_tro_chuyen_va_viec_khac = test_b_loi_dung_loai = test_c_ghim_va_mac_dinh_deu_ap = None
    test_n5_man13_tai_khoan_tam_nghi = test_giao_dien_va_thaydoi = None

    def test_n6_luot_thuong_loi_sang_hang_khac(self):
        self.dau_ra = [{"type": "result", "subtype": "error_during_execution", "is_error": True, "errors": ["boom"]}]
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        c3 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        with mock.patch.object(congai, "_chay", side_effect=self.chay),                 mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA, mohinh_bao="gpt-6-luna")):
            kq = congai.goi("x", loai_viec="trochuyen")
        self.assertEqual((kq["nguon_id"], len(self.lenh)), (c3, 2))          # 02 tài khoản Claude lỗi rồi sang ChatGPT
        self.assertIsNone(kq["ghim_hong"])
        self.assertEqual(kq["md_hong"], {"nguon_id": self.c1, "het_hanmuc": False, "loi": "lỗi khi chạy",
                                         "loi_ct": "error_during_execution: boom"})
        with mock.patch.object(congai, "_chay", side_effect=subprocess.TimeoutExpired("claude", 600)),                 mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA)):
            kq = congai.goi("x", loai_viec="trochuyen")
        self.assertEqual((kq["md_hong"]["loi"], kq["md_hong"]["het_hanmuc"]), ("quá giờ", False))
        with mock.patch.object(congai, "_chay", side_effect=self.chay):   # cùng hãng (Claude) trả lời được: không có dòng vàng
            self.dau_ra = None
            self.assertIsNone(congai.goi("x", loai_viec="trochuyen")["md_hong"])
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("if (x.md_hong && !g.het_hanmuc)", js)
        self.assertIn("' chưa dùng được'\n      + (g.loi ? ' (' + esc(nbsp(g.loi)) + ')' : '') + ', đã dùng '", js)

    def test_n7_khong_cho_toi_khi_dat_lai_khi_loi(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("' (mặc định)' + (hong.het ? ' cho tới khi đặt lại' : '')", js)
        self.assertNotIn("' (mặc định) cho tới khi đặt lại'", js)

    def test_n8_du_phong_tai_khoan_tam_nghi(self):
        c2 = self.nguon("goi_claude_02", "goi", 1, "anthropic")
        den = congai.ghi_het_tai_khoan(self.c1, time.time() + 1800)
        with mock.patch.object(congai, "_chay", side_effect=self.chay):
            kq = congai.goi("x", loai_viec="trochuyen")
        self.assertEqual((kq["nguon_id"], kq["chay_tk"]), (c2, 2))
        self.assertEqual(kq["du_phong"], {"tk": 1, "den": datetime.fromtimestamp(den, MUIGIO_VN).isoformat(timespec="seconds")})
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("'tài khoản ' + dp.tk + ' đang tạm nghỉ' + (dp.den ? ' đến ' + denLuc(dp.den) : '')", js)


class KiemY36g(KiemY36e):
    """Y36g N9 (CDO U11f): lượt ghim lỗi ở cả 02 tài khoản thì vòng mặc định không gọi lại đúng mô hình đó ở cùng tài
    khoản (mọi loại lỗi); mô hình mặc định khác mô hình ghim thì vẫn gọi."""
    test_a_lenh_tro_chuyen_va_viec_khac = test_b_loi_dung_loai = test_c_ghim_va_mac_dinh_deu_ap = None
    test_n5_man13_tai_khoan_tam_nghi = test_giao_dien_va_thaydoi = None

    def chay_loi(self, lenh, env, vao=None, giay=None):
        self.lenh.append(lenh)
        ma = lenh[lenh.index("--model") + 1] if "--model" in lenh else None
        if ma == "sonnet":
            dong = [{"type": "result", "subtype": "error_during_execution", "is_error": True, "errors": ["boom"]}]
        else:
            dong = [{"type": "result", "subtype": "success", "result": "ok", "usage": {"input_tokens": 1, "output_tokens": 1}}]
        return subprocess.CompletedProcess(lenh, 0, "\n".join(json.dumps(x) for x in dong), "")

    def mo_hinh_goi(self):
        return [l[l.index("--model") + 1] if "--model" in l else None for l in self.lenh]

    def test_trung_mo_hinh_khong_goi_lai(self):
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        c3 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        dm.danh_sach()
        dm.dat_macdinh("trochuyen", khoa="goi_claude|sonnet")   # QĐ190: chọn ở chat làm luôn mặc định Trò chuyện AI
        with mock.patch.object(congai, "_chay", side_effect=self.chay_loi),                 mock.patch.object(congai, "_goi_chatgpt", return_value=dict(TRA)):
            kq = congai.goi("x", loai_viec="trochuyen", mohinh_id="goi_claude|sonnet")
        self.assertEqual(self.mo_hinh_goi(), ["sonnet", "sonnet"])   # mỗi tài khoản 01 lần, không gọi lại ở vòng mặc định
        self.assertEqual(kq["nguon_id"], c3)                          # QĐ193: sang hãng khác

    def test_khac_mo_hinh_van_goi(self):
        self.nguon("goi_claude_02", "goi", 1, "anthropic")
        dm.danh_sach()
        dm.dat_macdinh("trochuyen", khoa="goi_claude|opus")
        with mock.patch.object(congai, "_chay", side_effect=self.chay_loi):
            kq = congai.goi("x", loai_viec="trochuyen", mohinh_id="goi_claude|sonnet")
        self.assertEqual(self.mo_hinh_goi(), ["sonnet", "sonnet", "opus"])   # mặc định Opus khác Sonnet: vẫn gọi
        self.assertEqual((kq["nguon_id"], kq["chu"]), (self.c1, "ok"))


class KiemZ12(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.html = (GD / "index.html").read_text(encoding="utf-8")

    def test_dong_viec_nen_va_ghi_chu(self):
        self.assertEqual(list(dm.LOAI_VIEC)[-1], "viecnen_chung")                       # dòng cuối bảng
        self.assertEqual(dm.LOAI_VIEC["viecnen_chung"], "Việc nền chung")   # QĐ194
        self.assertEqual(self.js.count("Việc nền · toàn hệ thống") + self.js.count("Việc nền chung"), 0)   # tên dòng chỉ ở máy chủ (01 chỗ)
        for chu in ("const CHU_VN = 'Việc nền chưa đặt riêng và bot nền sau này dùng dòng này. Trò chuyện AI không theo.';",
                    "k === 'viecnen_chung' ? ' <button class=\"nut-ico nho\" data-ivn title=\"' + CHU_VN",
                    "if ('ivn' in d) { ev.stopImmediatePropagation(); bao(CHU_VN); return; }",
                    "'Trò chuyện AI chưa đặt thì dùng mặc định của nguồn ưu tiên 1; việc nền chưa đặt riêng theo dòng \"' + nbsp(LV.viecnen_chung) + '\"'",
                    "bao('Đã đổi mô hình cho \"' + D.dsmh.loai_viec[lv] + '\": ' + ten + ' · ' + tn + '.');"):
            self.assertIn(chu, self.js, chu)
        self.assertIn('id="md-ghichu"', self.html)

    def test_han_muc_03_tinh_huong(self):
        for chu in ("'Đo lúc ' + esc(luc(n.do_luc))", "'&nbsp;· đặt lại 05&nbsp;giờ lúc '",
                    ">Đã đặt lại lúc ' + esc(gio(n.da_datlai_luc)) + '&nbsp;· số mới có sau lượt gọi AI kế&nbsp;tiếp</div>'",
                    'title="Số đo sau mỗi lượt gọi AI; màn này tự làm mới 01 phút/lần"',
                    'title="Qua giờ đặt lại: khung 05 giờ mới bắt đầu, số dùng về 0%"'):
            self.assertIn(chu, self.js, chu)
        self.assertIn(".tdf{height:100%;background:var(--xanh);border-radius:5px;transition:width .4s ease}", self.html)

    @unittest.skipUnless(__import__("shutil").which("node"), "máy không có node")
    def test_thanh_truot_tu_so_cu(self):
        import subprocess
        import tempfile
        i = self.js.index("const pct = ")
        ham = self.js[i:self.js.index("\n// N09", i) if "\n// N09" in self.js[i:] else self.js.index("\nfunction theGoi", i)]
        ma = ("const D = {}; const hai = n => String(n);\n" + ham
              + "\nconst a = thanhHm('x', 42, 'k'); const b = thanhHm('x', 47, 'k');"
              + "\nconsole.log(JSON.stringify([/width:(\\d+)%/.exec(a)[1], /width:(\\d+)%/.exec(b)[1], /data-w=\"(\\d+)\"/.exec(b)[1]]));")
        with tempfile.TemporaryDirectory() as tm:
            p = Path(tm) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["42", "42", "47"])   # vẽ lại giữ 42% rồi trượt tới 47%


if __name__ == "__main__":
    unittest.main()
