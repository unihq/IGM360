"""Bài kiểm bản 0.7.7 (QĐ192, Y36; CDA K-VN Đ1–Đ3): đo hạn mức bị động (0 lượt gọi thêm, không đọc khoá đăng nhập) và
dòng "Việc nền · toàn hệ thống". Dữ liệu giả, không gọi CLI thật."""
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
        self.assertEqual(h({"status": "rejected"}), {"het_khongro": True})

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
        self.assertGreater(congai.het_mo_hinh(self.c1, None), time.time())   # "mặc định của nguồn" ghi khoá rỗng
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
        self.assertIn("const CUM = ['toàn hệ thống', 'Việc nền',", js)
        self.assertIn("' của tài khoản ' + tk + ' hết hạn mức đến ' + gio(m.den)", js)
        self.assertIn("'<div class=\"tk-dong\"' + tieuHetMh(n, x.taikhoan) + '>", js)
        api = (GOC / "maychu/web/api.py").read_text(encoding="utf-8")
        self.assertIn('n["het_mh"] = congai.ds_het_mo_hinh(n["id"])', api)


class KiemZ12(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.html = (GD / "index.html").read_text(encoding="utf-8")

    def test_dong_viec_nen_va_ghi_chu(self):
        self.assertEqual(list(dm.LOAI_VIEC)[-1], "viecnen_chung")                       # dòng cuối bảng
        self.assertEqual(self.js.count("Việc nền · toàn hệ thống") + self.js.count("Việc nền chung"), 0)   # tên dòng chỉ ở máy chủ (01 chỗ)
        for chu in ("const CHU_VN = 'Việc nền chưa đặt riêng và bot nền sau này dùng dòng này. Trò chuyện AI không theo.';",
                    "k === 'viecnen_chung' ? ' <button class=\"nut-ico nho\" data-ivn title=\"' + CHU_VN",
                    "if ('ivn' in d) { ev.stopImmediatePropagation(); bao(CHU_VN); return; }",
                    "'Trò chuyện AI chưa đặt thì dùng mặc định của nguồn ưu tiên 1; việc nền chưa đặt riêng theo dòng \"' + LV.viecnen_chung + '\"'",
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
