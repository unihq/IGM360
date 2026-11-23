"""Bài kiểm bản 0.7.0 (Y17; QĐ162): chống trình duyệt giữ mã giao diện cũ, báo lỗi "Kiểm tra lại", thứ tự nguồn AI
(QĐ160), dòng nguồn màn 08 (N15), 05 lỗi nhỏ (N10, N12, N14, T1, T2), chữ theo từ điển (QĐ137, QĐ139, QĐ159) và bài
kiểm chặn chữ cũ. Dữ liệu thử chỉ dùng mã, tên giả (QĐ126)."""
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, maso, phienban
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.mohinh import congai, dangnhap_goi

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu" / "web" / "giaodien"

# Cách gọi cũ (cột "Cách gọi cũ, không dùng" của từ điển `Tudien_Thuatngu.md`, các dòng có trên giao diện GĐ 1 và
# những cách gọi cũ không được quay lại). Giao diện còn chữ nào ở đây thì bài kiểm hỏng.
CHU_CU = ("Cửa chờ", "Tiền thật", "tiền thật", "Trả cố định theo tháng", "Việc cần anh", "chốt kỳ", "Chốt số kỳ",
          "Model", "trần tiền", "Trần tiền", "Tiền và giá", "Báo cáo và lấy dữ liệu", "Ngưỡng tiền để AI",
          "Cách chia chi phí mua hàng", "Theo số chiếc", "Việc máy chưa tự làm được", "Hồ thô", "Kho sạch",
          "Lớp điều chỉnh", "Shop chết", "Lãi nằm ở đâu", "Giá vốn tạm", "Giá vốn thật", "Lệch ngưỡng", "Nợ quảng cáo",
          "Tiền trên sàn", "Tiền chờ về", "Tiền bị giữ", "Chi phí nuôi shop", "Dữ liệu nhạy cảm")


class KiemChanBanCu(unittest.TestCase):
    """(b) QĐ130: đường tệp mã giao diện có số bản; /tainguyen gửi no-cache; trang chính no-store."""

    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH")}
        os.environ.update(IGM360_THUMUC_DULIEU=self.tam.name, IGM360_LICH="tat")
        from fastapi.testclient import TestClient
        from maychu import khoidong
        self.kd = khoidong
        self.c = TestClient(khoidong.app)
        self.c.__enter__()

    def tearDown(self):
        self.c.__exit__(None, None, None)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tam.cleanup()

    def test_so_ban_trong_duong_tep_va_no_cache(self):
        ban = (GOC / "VERSION").read_text(encoding="utf-8").strip()
        r = self.c.get("/")
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertIn(f'src="/tainguyen/app.js?v={ban}"', r.text)
        self.assertIn(f'src="/tainguyen/icon.js?v={ban}"', r.text)
        self.assertNotIn('src="/tainguyen/app.js"', r.text)
        for tep in (f"/tainguyen/app.js?v={ban}", "/tainguyen/icon.js", "/tainguyen/logo/claude.svg"):
            with self.subTest(tep=tep):
                r = self.c.get(tep)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers["cache-control"], "no-cache")
        self.assertNotIn("cache-control", {k.lower() for k in self.c.get("/suckhoe").headers})


class KiemBaoLoiKiemTra(unittest.TestCase):
    """(e) tải tệp thay đổi không được thì báo rõ kèm mã trả về; (c), (d) giao diện không nuốt lỗi."""

    def setUp(self):
        capnhat._NHO.update(luc=0.0, luc_dat=0.0, ban_moi=None, thaydoi=[], tomtat={}, loi=None, nhan_thaydoi=None)

    tearDown = setUp

    def kiem(self, ma_tra):
        het = [{"ban": "0.7.0", "tomtat": "Bản thử", "dong": ["Dòng thử"]}] if ma_tra == 200 else []
        with mock.patch.object(capnhat, "_hoi_ghcr", return_value=("0.7.0", "0.7.0")), \
                mock.patch.object(capnhat, "_tai_thaydoi_kq", return_value=(het, ma_tra)):
            return capnhat.kiem_tra(bat_buoc=True)

    def test_loi_tai_tep_thay_doi(self):
        kq = self.kiem(404)
        self.assertIn("mã trả về 404", kq["loi"])    # chưa có nội dung cũ: nói rõ (QĐ174 giữ, chỉ im khi đã có bản cũ)
        self.assertEqual(kq["ban_moi"], "0.7.0")      # số bản mới vẫn đúng
        kq = self.kiem(200)
        self.assertIsNone(kq["loi"])
        self.assertEqual(kq["tomtat"], {"0.7.0": "Bản thử"})

    def test_giao_dien_khong_nuot_loi(self):
        js = (GD / "app.js").read_text(encoding="utf-8")
        html = (GD / "index.html").read_text(encoding="utf-8")
        dong = next(x for x in js.splitlines() if "'/capnhat/kiemtra'" in x)
        self.assertNotIn("catch (e) { /* */ }", dong)   # nút Kiểm tra lại không còn nuốt lỗi
        self.assertIn("Kiểm tra lại chưa được: ", js)
        self.assertIn('id="cn-loi"', html)
        self.assertIn("$('#cn-loi').textContent = d.loi", js)


class KiemThuTuNguon(unittest.TestCase):
    """N10 b, QĐ160: gói (phí cố định tháng) luôn trước Khoá API (phí theo lượt), kể cả khi `uutien` của gói lớn hơn."""

    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.thumuc = Path(self.tam.name)
        khoitao.tao_het(self.thumuc)
        cn = ketnoi.mo("Viecnen", self.thumuc)
        try:
            for ma, loai, uu, hang, cach in (("khoa_anthropic_01", "khoa_api", 1, "anthropic", "anthropic"),
                                             ("goi_chatgpt_01", "goi", 4, "openai", "cli"),
                                             ("nguon_thu_tuchay", "tuchay", 2, "ollama", "openai"),
                                             ("goi_claude_01", "goi", 3, "anthropic", "cli")):
                phienban.them(cn, "nguon_ai", {"ma": ma, "ten": ma, "hieuluc_tu": "2026-11-23", "loai": loai,
                                               "uutien": uu, "hang": hang, "cach_goi": cach})
        finally:
            cn.close()

    def tearDown(self):
        self.tam.cleanup()

    def test_goi_truoc_khoa_api(self):
        mong = ["goi_claude_01", "goi_chatgpt_01", "nguon_thu_tuchay", "khoa_anthropic_01"]
        self.assertEqual([d["ma"] for d in congai._nguon(self.thumuc)], mong)
        with mock.patch.object(dangnhap_goi, "trang_thai", return_value={}):
            self.assertEqual([d["ma"] for d in dangnhap_goi.danh_sach(self.thumuc)], mong)

    def test_mo_hinh_gan_nhat_tu_g04(self):
        """N15: dòng nguồn màn 08 lấy tên mô hình của lần gọi gần nhất (G04 → G08)."""
        cn = ketnoi.mo("Viecnen", self.thumuc)
        try:
            nid = cn.execute("SELECT id FROM nguon_ai WHERE ma = 'goi_claude_01'").fetchone()[0]
            m1, m2 = maso.tao(), maso.tao()
            for m, ten in ((m1, "mo-hinh-cu-1"), (m2, "mo-hinh-moi-2")):
                cn.execute("INSERT INTO mohinh_ai (id, nguon_ai_id, ma_mohinh, trangthai) VALUES (?, ?, ?, 'dung')", (m, nid, ten))
        finally:
            cn.close()
        nk = ketnoi.mo("Nhatky", self.thumuc)
        try:
            for luc, m in (("2026-11-23T08:00:00+07:00", m1), ("2026-11-23T09:00:00+07:00", m2),
                           ("2026-11-23T10:00:00+07:00", None)):   # lần gọi không ghi mô hình không đè
                nk.execute("INSERT INTO nhatky_ai (id, luc, nguon_ai_id, mohinh_id, ketqua) VALUES (?, ?, ?, ?, 'xong')",
                           (maso.tao(), luc, nid, m))
        finally:
            nk.close()
        with mock.patch.object(dangnhap_goi, "trang_thai", return_value={}):
            ds = {d["ma"]: d["mohinh_gannhat"] for d in dangnhap_goi.danh_sach(self.thumuc)}
        self.assertEqual(ds["goi_claude_01"], "mo-hinh-moi-2")
        self.assertIsNone(ds["goi_chatgpt_01"])
        js = (GD / "app.js").read_text(encoding="utf-8")
        self.assertIn("cum(dongNguon(dau))", js)
        self.assertIn("'mô hình mặc định'", js)


class KiemChuGiaoDien(unittest.TestCase):
    def setUp(self):
        self.html = (GD / "index.html").read_text(encoding="utf-8")
        self.js = (GD / "app.js").read_text(encoding="utf-8")
        self.ico = (GD / "icon.js").read_text(encoding="utf-8")

    def test_chan_chu_cu(self):
        for tep, chu in (("index.html", self.html), ("app.js", self.js), ("icon.js", self.ico)):
            for cu in CHU_CU:
                with self.subTest(tep=tep, cu=cu):
                    self.assertNotIn(cu, re.sub(r"<svg.*?</svg>", "", chu, flags=re.S))
        nhan = [d[2] for d in thongso.DANHMUC] + list(thongso.NHOM) + list(thongso.KHONG_SUA.values())
        nhan += [v for d in thongso.DANHMUC if d[6] for v in d[6].values()] + [d[7] for d in thongso.DANHMUC]
        for cu in CHU_CU:
            with self.subTest(thongso=cu):
                self.assertFalse(any(cu in x for x in nhan), cu)

    def test_chu_moi_theo_tu_dien(self):
        for moi in ("Chờ duyệt", "Mô hình AI", "Phí theo lượt", "Phí cố định tháng", "Chi phí AI tháng", "Chưa đặt hạn mức",
                    "mục Chờ duyệt", "mục&nbsp;Két&nbsp;khoá", "Mở Mô hình AI", "Tài chính", "Báo cáo, dữ liệu"):
            with self.subTest(moi=moi):
                self.assertTrue(moi in self.html or moi in self.js or moi in self.ico, moi)
        self.assertIn("Ngoại lệ cần duyệt: đề xuất AI hoặc 01&nbsp;trong 03&nbsp;cách xử lý", self.html)
        self.assertIn("(đổi ở Cài&nbsp;đặt&nbsp;›&nbsp;Thông&nbsp;số)", self.html)   # đường dẫn có "›": không thêm "mục"
        self.assertIn("Két khoá có ở bản sau (cùng màn 11&nbsp;Nguồn dữ liệu)", self.html)   # CPO xác nhận giữ
        self.assertEqual(thongso.NHOM, ("Tài chính", "Máy chủ và bảo mật", "AI", "Báo cáo, dữ liệu"))
        self.assertEqual(congai.dung_duoc({"ma": "khoa_thu_01", "loai": "khoa_api", "tran_tien_thang": None, "id": "x"})[1], "chưa đặt hạn mức")

    def test_05_loi_nho(self):
        self.assertIn("<b>Chưa có tài&nbsp;khoản</b>", self.js)                         # N10 a
        self.assertIn("ưu&nbsp;tiên&nbsp;2", self.html)                                       # N14
        for c in ("'Mở trang'", "'TikTok Shop'", "'mã sàn'"):                                 # N12, T1
            self.assertIn(c, self.js)
        self.assertIn("ChatGPT&nbsp;·&nbsp;Codex", self.html)                                 # T2 → QĐ172 (Z9)
        # U4 (CDO, S1–S3): không tách cụm "mục Két khoá ·", "tài khoản Claude", "mục Bộ mã chung"
        self.assertIn("Cất ở mục&nbsp;Két&nbsp;khoá&nbsp;· ưu&nbsp;tiên&nbsp;", self.js)
        self.assertIn("tài&nbsp;khoản&nbsp;Claude của anh.", self.js)
        self.assertIn("mục&nbsp;Bộ&nbsp;mã&nbsp;chung", self.html)
        self.assertIn("'mục Chờ duyệt', 'mục Két khoá', 'mục Bộ mã chung'", self.js)
        self.assertIn("chatgpt: 'ChatGPT' + NB + '·' + NB + 'Codex'", self.js)               # QĐ172 (Z9)
        nguon = (GOC / "maychu" / "hethong" / "mohinh" / "dangnhap_goi.py").read_text(encoding="utf-8")
        self.assertIn('Bấm \\"Mở trang\\" lấy mã mới rồi dán lại."', nguon)                # N12: dấu chấm cuối
