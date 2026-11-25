"""Bài kiểm N0 mốc 3 (QĐ349, QĐ351; CDA K1–K7, K1a–K1e; SOAT-N0-1 M3): ChatGPT qua `codex app-server` cho lượt có
người nghe, quay về `codex exec` khi chưa bắt đầu được, kiểm thử bản CLI mới thêm 01 lượt app-server.
Không gọi CLI thật: `as_gia.py` (app-server giả) và `cli_gia.py` (exec giả) chạy bằng trình Python của bài kiểm.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi, khoitao
from maychu.hethong.mohinh import congai, dangnhap_goi, nangcli

DAY = Path(__file__).resolve().parent
PY = [sys.executable, "-X", "utf8"]


class NgheGhi(congai.Nghe):
    def __init__(self):
        self.su_kien = []
        super().__init__(lambda loai, **du: self.su_kien.append((loai, du)))


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.ghi = str(Path(self.tam.name) / "ghi.json")
        self.enterContext(mock.patch.object(dangnhap_goi, "_env", return_value=dict(os.environ)))
        self.enterContext(mock.patch.object(dangnhap_goi, "_cli", return_value="cli-khong-co"))
        self.enterContext(mock.patch.object(congai, "_doc_han_muc_codex", return_value={"tu": "tep"}))
        self.enterContext(mock.patch.object(congai, "_mohinh_codex", return_value=None))

    def doi_as(self, kich_ban, **k):
        goc = congai._chay_as

        def chay(lenh, env, cau, mohinh, nghe, giay=congai.GIAY_TOIDA, giay_khoi_dau=congai.GIAY_KHOI_DAU_AS):
            chay.lenh = list(lenh)
            return goc([*PY, str(DAY / "as_gia.py"), kich_ban, self.ghi], env, cau, mohinh, nghe,
                       k.get("giay", giay), k.get("giay_khoi_dau", giay_khoi_dau))
        return chay

    def da_ghi(self):
        return json.loads(Path(self.ghi).read_text(encoding="utf-8"))

    def goi(self, kich_ban, nghe, mohinh="gpt-5", **k):
        tok = congai._NGHE.set(nghe)
        try:
            with mock.patch.object(congai, "_chay_as", side_effect=self.doi_as(kich_ban, **k)) as cs:
                return congai._goi_chatgpt(1, "câu hỏi", mohinh), cs
        finally:
            congai._NGHE.reset(tok)


class KiemAppServer(Nen):
    def test_chu_dan_va_ket_qua_day_du(self):
        n = NgheGhi()
        bd = time.monotonic()
        kq, cs = self.goi("thuong", n)
        self.assertLess(time.monotonic() - bd, 30)                               # K2: tự dừng tiến trình sau lượt
        self.assertEqual(cs.call_args[0][0][1], "app-server")
        self.assertEqual(kq["chu"], "Xin chào bạn\nĐoạn sau")                    # K5: chữ lưu là tin đầy đủ
        self.assertEqual((kq["vao"], kq["ra"], kq["mohinh_bao"]), (7, 3, "gpt-5"))
        self.assertIn("5gio", kq["hanmuc"])                                      # K5: đọc thông báo hạn mức
        self.assertEqual([du["them"] for l, du in n.su_kien if l == "chu"], ["Xin ", "chào ", "bạn", "\n\n", "Đoạn sau"])
        self.assertIn(("buoc", {"ten": "webSearch"}), n.su_kien)
        g = self.da_ghi()
        self.assertEqual({k: g["thread_start"].get(k) for k in ("sandbox", "approvalPolicy", "model")},
                         {"sandbox": "read-only", "approvalPolicy": "never", "model": "gpt-5"})   # K3, K4
        self.assertEqual((g["tra_duyet"]["id"], g["tra_duyet"]["error"]["code"]), (99, -32601))  # K3: từ chối ngay
        self.assertEqual(g["cau"], "câu hỏi")

    def test_het_han_muc(self):
        with self.assertRaises(congai.HetHanMuc):
            self.goi("het_hanmuc", NgheGhi())

    def test_k7_chua_bat_dau_duoc_thi_chay_exec(self):
        for kb, k in (("thoat", {}), ("khong_tra_loi", {"giay_khoi_dau": 1})):
            ra = '{"type": "item.completed", "item": {"type": "agent_message", "text": "Từ exec"}}\n'
            with mock.patch.object(congai, "_chay_dan", return_value=subprocess.CompletedProcess([], 0, ra, "")) as ex:
                kq, _ = self.goi(kb, NgheGhi(), **k)
            self.assertEqual(kq["chu"], "Từ exec", kb)
            self.assertEqual(ex.call_args[0][0][1], "exec")

    def test_dung_giua_luot(self):
        n = NgheGhi()
        threading.Timer(1.5, n.dung.set).start()
        bd = time.monotonic()
        with self.assertRaises(congai.DaDung):
            self.goi("ngu", n)
        self.assertLess(time.monotonic() - bd, 10)
        self.assertEqual(n.chu_da_co(), "Xin chào bạn")

    def test_n4_tra_tu_choi_loi_ong_van_ra_dung(self):
        """CDA SOAT-N0-3 N4: ghi trả từ chối lỗi ống (tiến trình đang bị dừng) không làm hỏng lượt; Dừng vẫn ra DaDung."""
        that = congai.json.dumps

        def dumps(o, *a, **k):
            if isinstance(o, dict) and o.get("error"):
                raise BrokenPipeError("ống đã đóng")
            return that(o, *a, **k)
        n = NgheGhi()
        threading.Timer(1.5, n.dung.set).start()
        with mock.patch.object(congai.json, "dumps", side_effect=dumps), self.assertRaises(congai.DaDung):
            self.goi("thuong", n)

    def test_dung_luc_khoi_dau_khong_chay_exec(self):
        n = NgheGhi()
        threading.Timer(0.5, n.dung.set).start()
        with mock.patch.object(congai, "_chay_dan") as ex, self.assertRaises(congai.DaDung):
            self.goi("khong_tra_loi", n)
        ex.assert_not_called()

    def test_qua_gio(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.goi("ngu", NgheGhi(), giay=2)

    def test_khong_nguoi_nghe_van_exec(self):
        ra = '{"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}\n'
        with mock.patch.object(congai, "_chay", return_value=subprocess.CompletedProcess([], 0, ra, "")), \
                mock.patch.object(congai, "_chay_as") as cs:
            self.assertEqual(congai._goi_chatgpt(1, "x", None)["chu"], "ok")
        cs.assert_not_called()


class KiemThuBanMoi(Nen):
    """K1a–K1e: kiểm thử bản CLI mới thêm 01 lượt app-server thật của bản đó."""

    def kiem(self, kich_ban, **k):
        goc = congai._chay_as

        def chay(lenh, env, cau, mohinh, nghe, giay=congai.GIAY_TOIDA, giay_khoi_dau=congai.GIAY_KHOI_DAU_AS):
            chay.lenh, chay.giay = list(lenh), giay
            return goc([*PY, str(DAY / "as_gia.py"), kich_ban, self.ghi], env, cau, mohinh, nghe,
                       k.get("giay", giay), k.get("giay_khoi_dau", giay_khoi_dau))
        with mock.patch.object(congai, "_chay_as", side_effect=chay):
            kq = congai.kiem_app_server(1, nangcli.CAU_THU, "ban-moi")
        return kq, chay

    def test_k1a_chay_app_server_cua_ban_moi(self):
        kq, chay = self.kiem("thuong")
        self.assertEqual(chay.lenh, ["ban-moi", "app-server", "--disable", "shell_tool"])   # QĐ374 (a): thêm cờ tắt công cụ chạy lệnh
        self.assertEqual(chay.giay, 300)                                         # K1e
        self.assertEqual(kq, "Xin chào bạn\nĐoạn sau")
        g = self.da_ghi()
        self.assertEqual((g["thread_start"]["sandbox"], g["thread_start"]["approvalPolicy"], g["cau"]),
                         ("read-only", "never", nangcli.CAU_THU))

    def test_k1b_k1e_ket_qua_buoc_kiem(self):
        dang_noi = {"da_noi": True}
        with mock.patch.object(dangnhap_goi, "trang_thai", return_value=dang_noi), \
                mock.patch.object(congai, "_goi_chatgpt", return_value={}):
            for loi, mong in ((None, "dat"), (congai.HetHanMuc("hết"), "hoan"), (RuntimeError("hỏng"), "loi"),
                              (subprocess.TimeoutExpired("x", 300), "loi")):
                with mock.patch.object(congai, "kiem_app_server", side_effect=loi) as ka:
                    self.assertEqual(nangcli._kiem_goi_ngan("chatgpt", "ban-moi"), mong)
                ka.assert_called_once_with(1, nangcli.CAU_THU, "ban-moi")
            with mock.patch.object(congai, "_goi_claude", return_value={}), \
                    mock.patch.object(congai, "kiem_app_server") as ka:
                self.assertEqual(nangcli._kiem_goi_ngan("claude", "ban-moi"), "dat")
            ka.assert_not_called()                                               # chỉ Codex có app-server
        with mock.patch.object(dangnhap_goi, "trang_thai", return_value={"da_noi": False}), \
                mock.patch.object(congai, "kiem_app_server") as ka:
            self.assertEqual(nangcli._kiem_goi_ngan("chatgpt", "ban-moi"), "dat")   # K1b: chưa đăng nhập thì bỏ qua
        ka.assert_not_called()

    def test_k1e_qua_gio_va_loi_khoi_dau(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.kiem("ngu", giay=2)
        with self.assertRaises(RuntimeError):
            self.kiem("thoat")
        with self.assertRaises(congai.HetHanMuc):
            self.kiem("het_hanmuc")

    def test_k1c_khong_ghi_g02_g04(self):
        dl = Path(self.tam.name) / "dl"
        dl.mkdir()
        with mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(dl), "IGM360_LICH": "tat"}):
            khoitao.tao_het(dl)
            self.kiem("thuong")
            for ten, cau in (("Viecnen", "SELECT count(*) FROM viecnen"), ("Nhatky", "SELECT count(*) FROM nhatky_ai")):
                cn = ketnoi.mo(ten, dl)
                try:
                    self.assertEqual(cn.execute(cau).fetchone()[0], 0, ten)
                finally:
                    cn.close()


if __name__ == "__main__":
    unittest.main()
