"""Bài kiểm N0 mốc 1 (QĐ344, QĐ349, QĐ351; kế hoạch Kehoach_Luot_Chaynen mục 2.1, 2.2): đọc dần đầu ra CLI cho lượt
trò chuyện có người nghe, dừng cả nhóm tiến trình, quá giờ, bỏ chữ dở khi sang nguồn kế, giữ chỗ chạy.

Không gọi CLI thật: thay tệp chạy bằng `cli_gia.py` (Python in dòng mẫu) chạy bằng chính trình Python của bài kiểm.
"""
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
from maychu.hethong.mohinh import congai

GIA = str(Path(__file__).resolve().parent / "cli_gia.py")
PY = [sys.executable, "-X", "utf8"]   # CLI thật in UTF-8; trình Python trên Windows mặc định không


def doi_lenh(kich_ban):
    """Bọc `_chay_dan` thật: đổi tệp chạy CLI thành `python cli_gia.py <kịch bản>`, giữ nguyên các đối số còn lại."""
    goc = congai._chay_dan

    def chay(lenh, env, vao, giay, nghe, moi_dong):
        chay.lenh = list(lenh)
        return goc([*PY, GIA, kich_ban, *lenh[1:]], dict(os.environ), vao, giay, nghe, moi_dong)
    return chay


class NgheGhi(congai.Nghe):
    def __init__(self):
        self.su_kien = []
        super().__init__(lambda loai, **du: self.su_kien.append((round(time.monotonic(), 2), loai, du)))


class KiemDocDan(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch.object(congai.dangnhap_goi, "_env", return_value={}))
        self.enterContext(mock.patch.object(congai.dangnhap_goi, "_cli", return_value="cli-khong-co"))

    def test_claude_doc_dan_tung_manh_va_giu_ket_qua_cu(self):
        n, chay = NgheGhi(), doi_lenh("claude")
        tok = congai._NGHE.set(n)
        try:
            with mock.patch.object(congai, "_chay_dan", side_effect=chay), mock.patch.object(congai, "_chay") as cu:
                kq = congai._goi_claude(1, "câu hỏi", None)
        finally:
            congai._NGHE.reset(tok)
        cu.assert_not_called()
        self.assertIn("--include-partial-messages", chay.lenh)
        self.assertEqual(kq["chu"], "Xin chào bạn (7)")                       # chữ lưu lấy từ dòng `result` như cũ
        self.assertEqual(kq["mohinh_bao"], "claude-gia")
        chu = [du["them"] for _, loai, du in n.su_kien if loai == "chu"]
        self.assertEqual(chu, ["Xin ", "chào ", "bạn"])                       # bỏ mẩu của tác tử con
        self.assertIn(("buoc", {"ten": "web_search"}), [(l, d) for _, l, d in n.su_kien])
        moc = [t for t, l, _ in n.su_kien if l == "chu"]
        self.assertGreater(moc[-1] - moc[0], 0.4)                             # nhận dần, không đợi CLI thoát

    def test_khong_nguoi_nghe_di_duong_cu(self):
        ra = '{"type": "result", "subtype": "success", "result": "ok", "usage": {}}\n'
        with mock.patch.object(congai, "_chay", return_value=subprocess.CompletedProcess([], 0, ra, "")) as cu, \
                mock.patch.object(congai, "_chay_dan") as moi:
            self.assertEqual(congai._goi_claude(1, "x", None)["chu"], "ok")
        moi.assert_not_called()
        self.assertNotIn("--include-partial-messages", cu.call_args[0][0])

    def test_kiem_ban_cli_moi_khong_doc_dan_du_co_nguoi_nghe(self):
        """K1: kiểm thử bản CLI mới (truyền `cli`) luôn đi `_chay` như cũ."""
        tok = congai._NGHE.set(NgheGhi())
        ra = '{"type": "result", "subtype": "success", "result": "ok", "usage": {}}\n'
        try:
            with mock.patch.object(congai, "_chay", return_value=subprocess.CompletedProcess([], 0, ra, "")) as cu, \
                    mock.patch.object(congai, "_chay_dan") as moi:
                congai._goi_claude(1, "x", None, cli="ban-moi")
        finally:
            congai._NGHE.reset(tok)
        moi.assert_not_called()
        cu.assert_called_once()

    def test_codex_exec_ra_theo_doan(self):
        n, chay = NgheGhi(), doi_lenh("codex")
        tok = congai._NGHE.set(n)
        try:
            with mock.patch.object(congai, "_chay_dan", side_effect=chay), \
                    mock.patch.object(congai, "_doc_han_muc_codex", return_value={}), \
                    mock.patch.object(congai, "_mohinh_codex", return_value=None):
                kq = congai._goi_chatgpt(1, "câu", None)
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual(kq["chu"], "Đoạn 01\nĐoạn 02")                       # chữ lưu như cũ
        self.assertEqual([du["them"] for _, l, du in n.su_kien if l == "chu"], ["Đoạn 01", "\n\n", "Đoạn 02"])
        self.assertIn(("buoc", {"ten": "web_search"}), [(l, d) for _, l, d in n.su_kien])
        self.assertEqual((kq["vao"], kq["ra"]), (4, 5))

    def test_dung_giua_chung_dung_ca_tien_trinh(self):
        n = NgheGhi()
        threading.Timer(0.8, n.dung.set).start()
        bd = time.monotonic()
        with self.assertRaises(congai.DaDung):
            congai._chay_dan([*PY, GIA, "ngu_lau"], dict(os.environ), "x", 60, n, congai._doc_dan_claude(n))
        self.assertLess(time.monotonic() - bd, 8)                             # TERM, chờ 02 giây, KILL
        self.assertEqual(n.chu_da_co(), "Bắt đầu")                            # phần chữ đã có (ghi khi Dừng, TC46)

    def test_qua_gio_dung_ca_tien_trinh(self):
        n = NgheGhi()
        bd = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            congai._chay_dan([*PY, GIA, "ngu_lau"], dict(os.environ), "x", 1, n, lambda d: None)
        self.assertLess(time.monotonic() - bd, 8)

    @unittest.skipIf(os.name == "nt", "nhóm tiến trình kiểu POSIX: chạy trên máy GitHub (Linux)")
    def test_dung_ca_tien_trinh_con_trong_nhom(self):
        tam = tempfile.TemporaryDirectory()
        self.addCleanup(tam.cleanup)
        tep = Path(tam.name) / "con.pid"
        ma = ("import subprocess,sys,time;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);"
              f"open({str(tep)!r},'w').write(str(p.pid));print('x',flush=True);time.sleep(120)")
        n = NgheGhi()
        threading.Timer(0.8, n.dung.set).start()
        with self.assertRaises(congai.DaDung):
            congai._chay_dan([sys.executable, "-c", ma], dict(os.environ), None, 60, n, lambda d: None)
        pid = int(tep.read_text())
        time.sleep(0.3)
        with self.assertRaises(ProcessLookupError):                          # con cháu trong nhóm cũng đã dừng
            os.kill(pid, 0)


class KiemThuNguon(unittest.TestCase):
    """`_thu`: Dừng ghi G04 `huy` và không thử nguồn sau; mỗi lần thử 01 nguồn bỏ chữ dở của nguồn trước."""

    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name)
        self.enterContext(mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"}))
        khoitao.tao_het(self.dl)
        self.enterContext(mock.patch.object(congai, "dung_duoc", return_value=(True, "")))
        self.enterContext(mock.patch.object(congai, "het_mo_hinh", return_value=0))
        self.d = {"id": "n1", "ten": "Gói Claude 01", "ma": "goi_claude_01", "loai": "goi", "mohinh": {"id": "m1", "ma": "opus"}}

    def g04(self):
        cn = ketnoi.mo("Nhatky", self.dl)
        try:
            return [r[0] for r in cn.execute("SELECT ketqua FROM nhatky_ai")]
        finally:
            cn.close()

    def test_dung_ghi_huy_va_day_len(self):
        n = NgheGhi()
        tok = congai._NGHE.set(n)
        try:
            with mock.patch.object(congai, "_goi_claude", side_effect=congai.DaDung()):
                with self.assertRaises(congai.DaDung):
                    congai._thu(self.d, "câu", [], thumuc=self.dl)
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual(self.g04(), ["huy"])

    def test_sang_nguon_ke_phat_lam_lai(self):
        n = NgheGhi()
        n.them_chu("chữ dở của nguồn trước")
        tok = congai._NGHE.set(n)
        try:
            with mock.patch.object(congai, "_goi_claude", side_effect=congai.LoiAI("Claude", "lỗi khi chạy")):
                self.assertEqual(congai._thu(self.d, "câu", [], thumuc=self.dl), "lỗi")
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual([l for _, l, _ in n.su_kien], ["chu", "lam_lai"])
        self.assertEqual(n.chu_da_co(), "")


class KiemGiuCho(unittest.TestCase):
    def test_cho_cho_phat_cho_va_dung_duoc(self):
        sem = threading.BoundedSemaphore(1)
        sem.acquire()
        n = NgheGhi()
        threading.Timer(0.6, n.dung.set).start()
        tok = congai._NGHE.set(n)
        try:
            with self.assertRaises(congai.DaDung):
                with congai._ChoCho(sem):
                    pass
        finally:
            congai._NGHE.reset(tok)
        self.assertEqual([l for _, l, _ in n.su_kien], ["cho"])
        sem.release()
        with congai._ChoCho(sem):                                             # không người nghe: như `with sem`
            self.assertFalse(sem.acquire(blocking=False))
        self.assertTrue(sem.acquire(blocking=False))


if __name__ == "__main__":
    unittest.main()
