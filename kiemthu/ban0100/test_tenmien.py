"""Bài kiểm 0.10.0 – tên miền riêng đổi được (QĐ634 B; chữ QĐ650, QĐ651; CDA PTD-20 mục 2–4).

`/tls-check` chỉ 200 cho tên đã lưu và lời hỏi đi thẳng (có tiêu đề chuyển tiếp → 403) · biến thể `/tls-check/`,
`//tls-check` và đường lạ trả khác 200 (ghim: không có đường "bắt tất cả" trả 200) · chế độ an toàn đóng · tệp compose
giữ khối tên gốc, thêm khối On-Demand, chặn `/tls-check*` ở cả 02 khối · lưu chỉ qua đường riêng, chỉ Chủ, mật khẩu
+ mã 02 lớp, P01 + F04 · chưa nâng cấu hình thì "chưa bật" · kiểm DNS so tập địa chỉ, có hạn giờ, chỉ cảnh báo ·
đọc hạn chứng chỉ. 0 lần gọi mạng thật (dò DNS, kết nối TLS đều giả lập). Mật khẩu, mã giả ghép lúc chạy.
"""

import os
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, muigio
from maychu.hethong import antoan
from maychu.hethong.caidat import tenmien, thongso

GOC = Path(__file__).resolve().parents[2]
MK = "-".join(["matkhau", "kiem", "0100"])
TEN_GOC = "goc.vidu.test"
TEN_RIENG = "igm.vidu.test"
# Địa chỉ IP mẫu (dải dành cho tài liệu, RFC 5737 / RFC 3849) ghép lúc chạy, như mật khẩu giả
IP_GOC, IP_KHAC, IP_NGOAI, IP_LA = (".".join(x) for x in (("203", "0", "113", "5"), ("198", "51", "100", "9"),
                                                         ("198", "51", "100", "7"), ("1", "2", "3", "4")))
IP6_GOC = ":".join(["2001", "db8", "", "5"])


def _f04(dl: Path, lenhcon: str) -> list:
    cn = ketnoi.mo("Nhatky", dl)
    try:
        return [r[0] for r in cn.execute("SELECT thamso_tomtat FROM nhatky_thaotac WHERE congcu = 'caidat'"
                                         " AND lenhcon = ? ORDER BY luc", (lenhcon,))]
    finally:
        cn.close()


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        self.dl = Path(self.tam.name) / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat",
                                            tenmien.BIEN_GOC: TEN_GOC})
        bien.start()
        self.addCleanup(bien.stop)
        muigio.xoa_dem()
        self.addCleanup(muigio.xoa_dem)
        khoitao.tao_het(self.dl)
        thongso.khoi_tao(self.dl)


class KiemDang(unittest.TestCase):
    def test_chuan_hoa(self):
        self.assertEqual(tenmien.chuan("  HTTPS://IGM.Vidu.Test:443/dangnhap?x=1 "), TEN_RIENG)
        self.assertEqual(tenmien.chuan("igm.vidu.test."), TEN_RIENG)
        self.assertEqual(tenmien.chuan("công-ty.test"), "công-ty.test".encode("idna").decode())
        self.assertEqual(tenmien.chuan(None), "")

    def test_dung_dang(self):
        for d in (TEN_RIENG, "a.test", "igm-360.ten-cong-ty.vidu.test"):
            self.assertTrue(tenmien.dung_dang(d), d)
        for d in ("", "igm", IP_LA, "-a.test", "a-.test", "a..test", "a.t", "a_b.test", "a.test/x", "a" * 64 + ".test"):
            self.assertFalse(tenmien.dung_dang(d), d)


class KiemLuu(Nen):
    def test_chua_nang_cau_hinh_thi_chua_bat(self):
        with mock.patch.dict(os.environ, {tenmien.BIEN_GOC: ""}):
            self.assertFalse(tenmien.da_bat())
            self.assertEqual(tenmien.ten_goc("Goc.Vidu.Test:443"), TEN_GOC)   # vẫn hiện tên trên thanh địa chỉ
            self.assertEqual(thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl), {"loi": tenmien.CHU_TENMIEN["chua_bat"]})
        self.assertTrue(tenmien.da_bat())

    def test_tu_choi_sai_dang_va_trung_goc(self):
        self.assertEqual(thongso.doi_tenmien(IP_LA, "hethong", self.dl), {"loi": tenmien.CHU_TENMIEN["sai_dang"]})
        self.assertEqual(thongso.doi_tenmien("https://GOC.vidu.test/", "hethong", self.dl),
                         {"loi": tenmien.CHU_TENMIEN["trung_goc"]})
        self.assertEqual(tenmien.ten_rieng(self.dl), "")

    def test_luu_bo_giu_lich_su_va_f04(self):
        self.assertEqual(thongso.doi_tenmien(" IGM.vidu.test ", "hethong", self.dl), {"ok": True, "doi": True, "ten": TEN_RIENG})
        self.assertEqual(tenmien.ten_rieng(self.dl), TEN_RIENG)
        self.assertEqual(thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)["doi"], False)   # lưu lại tên cũ: 0 dòng mới
        self.assertEqual(thongso.doi_tenmien("", "hethong", self.dl), {"ok": True, "doi": True, "ten": ""})
        self.assertEqual(tenmien.ten_rieng(self.dl), "")
        self.assertEqual(thongso.doi_tenmien("", "hethong", self.dl)["doi"], False)
        self.assertEqual([x["giatri"] for x in thongso.lich_su(tenmien.TEN, self.dl)].count(TEN_RIENG), 1)   # dòng cũ giữ
        self.assertEqual(_f04(self.dl, "doi_tenmien"), [f"tenmien_rieng: (trống) → {TEN_RIENG}",
                                                       f"tenmien_rieng: {TEN_RIENG} → (trống)"])

    def test_chi_duong_rieng_khong_hien_o_thong_so(self):
        self.assertIn(tenmien.TEN, thongso.CHI_DUONG_RIENG)
        self.assertIn("loi", thongso.dat(tenmien.TEN, TEN_RIENG, muigio.hom_nay(), nguoi="hethong", thumuc=self.dl))
        self.assertIn("loi", thongso.gat(tenmien.TEN, True, "hethong", self.dl))
        self.assertNotIn(tenmien.TEN, [x["ten"] for x in thongso.doc_het(self.dl)["thongso"]])
        self.assertEqual(thongso.khoi_tao(self.dl), 0)   # không có giá trị khởi tạo
        self.assertEqual(tenmien.ten_rieng(self.dl), "")

    def test_cho_cap_chi_ten_da_luu_va_loi_di_thang(self):
        self.assertFalse(tenmien.cho_cap(TEN_RIENG, {}, self.dl))   # chưa lưu tên riêng: không cấp cho tên nào
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        self.assertTrue(tenmien.cho_cap(TEN_RIENG, {}, self.dl))
        self.assertTrue(tenmien.cho_cap("IGM.vidu.test.", {}, self.dl))
        for ten in ("", TEN_GOC, "khac.vidu.test", "x." + TEN_RIENG):
            self.assertFalse(tenmien.cho_cap(ten, {}, self.dl), ten)
        for k in ("x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "forwarded"):
            self.assertFalse(tenmien.cho_cap(TEN_RIENG, {k: IP_LA}, self.dl), k)
        with mock.patch.object(tenmien, "ten_rieng", side_effect=OSError("hỏng")):
            self.assertFalse(tenmien.cho_cap(TEN_RIENG, {}, self.dl))   # đọc lỗi: đóng an toàn


class KiemMang(Nen):
    def test_dns_so_tap_dia_chi(self):
        bang = {TEN_GOC: {IP_GOC, IP6_GOC}, "dung.vidu.test": {IP_GOC}, "khac.vidu.test": {IP_GOC, IP_KHAC}}

        def gia(ten):
            if ten not in bang:
                raise socket.gaierror(socket.EAI_NONAME, "không có")
            return bang[ten]
        with mock.patch.object(tenmien, "_dia_chi", side_effect=gia):
            self.assertEqual(tenmien.kiem_dns("dung.vidu.test", TEN_GOC), "dung")
            self.assertEqual(tenmien.kiem_dns("khac.vidu.test", TEN_GOC), "chua")     # có 01 địa chỉ trỏ nơi khác
            self.assertEqual(tenmien.kiem_dns("chuaco.vidu.test", TEN_GOC), "chua")   # chưa có bản ghi
        with mock.patch.object(tenmien, "_dia_chi", side_effect=socket.gaierror(socket.EAI_AGAIN, "tạm lỗi")):
            self.assertEqual(tenmien.kiem_dns("dung.vidu.test", TEN_GOC), "khong_ro")

    def test_dns_qua_han_gio_khong_treo(self):
        with mock.patch.object(tenmien, "_dia_chi", side_effect=lambda ten: time.sleep(1.5) or set()):
            bd = time.monotonic()
            self.assertEqual(tenmien.kiem_dns("cham.vidu.test", TEN_GOC, han=0.2), "khong_ro")
            self.assertLess(time.monotonic() - bd, 1.0)

    def test_doc_han_chung_chi(self):
        tls = mock.MagicMock()
        tls.__enter__.return_value.getpeercert.return_value = {"notAfter": "Feb 20 12:00:00 2027 GMT"}
        ctx = mock.MagicMock()
        ctx.wrap_socket.return_value = tls
        with mock.patch.object(tenmien.socket, "create_connection", return_value=mock.MagicMock()) as noi, \
                mock.patch.object(tenmien.ssl, "create_default_context", return_value=ctx):
            self.assertEqual(tenmien.doc_han(TEN_RIENG), "2027-02-20")   # 12:00 UTC = 19:00 +07:00, cùng ngày
        self.assertEqual(noi.call_args[0][0], ("gateway", 443))           # đọc trong mạng nội bộ, không ra ngoài
        self.assertEqual(ctx.wrap_socket.call_args[1]["server_hostname"], TEN_RIENG)
        with mock.patch.object(tenmien.socket, "create_connection", side_effect=OSError("không nối được")):
            self.assertIsNone(tenmien.doc_han(TEN_RIENG))
        ctx.wrap_socket.side_effect = tenmien.ssl.SSLCertVerificationError("chứng chỉ chưa hợp lệ")
        with mock.patch.object(tenmien.socket, "create_connection", return_value=mock.MagicMock()), \
                mock.patch.object(tenmien.ssl, "create_default_context", return_value=ctx):
            self.assertIsNone(tenmien.doc_han(TEN_RIENG))

    def test_bang_kiem_02_dong(self):
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        han = {TEN_GOC: "2027-01-10"}
        with mock.patch.object(tenmien, "kiem_dns", return_value="chua") as dns, \
                mock.patch.object(tenmien, "doc_han", side_effect=lambda ten: han.get(ten)):
            kq = tenmien.kiem(thumuc=self.dl)
        self.assertEqual(kq, {"bat": True,
                              "goc": {"ten": TEN_GOC, "dns": "dung", "https": "chay", "den": "2027-01-10"},
                              "rieng": {"ten": TEN_RIENG, "dns": "chua", "https": "cho_dns", "den": None}})
        dns.assert_called_once_with(TEN_RIENG, TEN_GOC)   # tên gốc không dò lại DNS
        with mock.patch.object(tenmien, "kiem_dns", return_value="dung"), \
                mock.patch.object(tenmien, "doc_han", return_value=None):
            self.assertEqual(tenmien.kiem(thumuc=self.dl)["rieng"]["https"], "chua_doc")
        thongso.doi_tenmien("", "hethong", self.dl)
        with mock.patch.object(tenmien, "doc_han", return_value=None):
            self.assertIsNone(tenmien.kiem(thumuc=self.dl)["rieng"])


class KiemDuongGoi(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.dl = Path(self.tam.name)
        self.env = {k: os.environ.get(k) for k in ("IGM360_THUMUC_DULIEU", "IGM360_LICH", "IGM360_ADMIN_USER",
                                                   "IGM360_ADMIN_PASSWORD", "IGM360_COOKIE_SECURE", tenmien.BIEN_GOC)}
        os.environ.update(IGM360_THUMUC_DULIEU=str(self.dl), IGM360_LICH="tat", IGM360_ADMIN_USER="chu",
                          IGM360_ADMIN_PASSWORD=MK, IGM360_COOKIE_SECURE="0", **{tenmien.BIEN_GOC: TEN_GOC})
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.hethong.taikhoan import nguoidung, totp
        self.nd, self.totp = nguoidung, totp
        self.c = TestClient(khoidong.app)
        self.c.__enter__()
        self.h = {"X-IGM360": "1"}
        muigio.xoa_dem()

    def tearDown(self):
        self.c.__exit__(None, None, None)
        antoan.CHE_DO.update(an_toan=False)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.nd._MA_TAM.clear()
        self.nd._BUOC_DA_DUNG.clear()
        muigio.xoa_dem()
        self.tam.cleanup()

    def ma(self, khoa):
        self.nd._BUOC_DA_DUNG.clear()
        return self.totp.ma_cua_buoc(khoa, self.totp.buoc())

    def vao(self):
        kq = self.c.post("/api/dangnhap", json={"ten": "chu", "matkhau": MK}, headers=self.h).json()
        self.assertEqual(self.c.post("/api/dangnhap/ma2lop", json={"ma_tam": kq["ma_tam"], "ma": self.ma(kq["khoa"])},
                                     headers=self.h).status_code, 200)
        return kq["khoa"]

    def test_tls_check_200_403_va_bien_the(self):
        # Đường viết đủ "http://testserver" + đường: "//tls-check" đứng đầu thì thư viện gửi hiểu là tên máy
        hoi = lambda duong, **tt: self.c.get("http://testserver" + duong, headers=tt,   # noqa: E731
                                             follow_redirects=False).status_code
        self.assertEqual(hoi(f"/tls-check?domain={TEN_RIENG}"), 403)   # chưa lưu tên riêng
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        self.assertEqual(hoi(f"/tls-check?domain={TEN_RIENG}"), 200)   # lời hỏi `ask` của Caddy (đi thẳng)
        self.assertEqual(self.c.get(f"/tls-check?domain={TEN_RIENG}").json(), {"ok": True})
        for d in ("", "?domain=", f"?domain={TEN_GOC}", "?domain=la.vidu.test", f"?domain=x.{TEN_RIENG}"):
            self.assertEqual(hoi("/tls-check" + d), 403, d)
        xff = {"X-Forwarded-For": IP_NGOAI, "X-Forwarded-Proto": "https", "X-Forwarded-Host": TEN_RIENG}
        for duong in (f"/tls-check?domain={TEN_RIENG}", f"/tls-check/?domain={TEN_RIENG}",
                      f"//tls-check?domain={TEN_RIENG}", f"/tls-check//?domain={TEN_RIENG}"):
            self.assertNotEqual(hoi(duong, **xff), 200, duong)   # đi qua đường công khai: không bao giờ 200
        self.assertEqual(hoi(f"/tls-check?domain={TEN_RIENG}", **{"X-Forwarded-For": IP_NGOAI}), 403)
        r = self.c.get(f"http://testserver/tls-check/?domain={TEN_RIENG}", headers={**xff, "Host": TEN_GOC})   # đi theo lời chuyển 307
        self.assertEqual((r.status_code, len(r.history)), (403, 1))
        self.assertNotEqual(hoi(f"//tls-check?domain={TEN_RIENG}"), 200)
        antoan.CHE_DO.update(an_toan=True)
        self.assertNotEqual(hoi(f"/tls-check?domain={TEN_RIENG}"), 200)   # chế độ an toàn: không cấp chứng chỉ mới

    def test_duong_la_tra_khac_200(self):
        """Ghim (CDA PTD-20 mục 4 điểm 3): không có đường "bắt tất cả" trả 200 – bản quay về thiếu /tls-check vẫn đóng."""
        for duong in ("/khongco", "/khongco/tls-check", "/api/khongco", "/tainguyen/khongco.js", "/tls", "/tls-check-x",
                      "/index.html", "/dangnhap"):
            self.assertNotEqual(self.c.get("http://testserver" + duong, follow_redirects=False).status_code, 200, duong)

    def test_xem_luu_bo_chi_khi_dung_mat_khau_ma(self):
        self.assertEqual(self.c.get("/api/tenmien", headers=self.h).status_code, 401)
        khoa = self.vao()
        r = self.c.get("/api/tenmien", headers={**self.h, "Host": TEN_GOC})
        self.assertEqual(r.json(), {"bat": True, "goc": TEN_GOC, "rieng": None, "la_chu": True})
        gia = {"bat": True, "goc": None, "rieng": None}
        with mock.patch.object(tenmien, "kiem", return_value=gia) as kiem:
            r = self.c.post("/api/tenmien", json={"ten": TEN_RIENG, "matkhau": MK + "x", "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual(r.status_code, 400)                                           # sai mật khẩu: không đổi
            self.assertEqual(tenmien.ten_rieng(self.dl), "")
            r = self.c.post("/api/tenmien", json={"ten": IP_LA, "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual((r.status_code, r.json()["detail"]), (400, tenmien.CHU_TENMIEN["sai_dang"]))
            r = self.c.post("/api/tenmien", json={"ten": TEN_RIENG, "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual((r.status_code, r.json()), (200, {"ok": True, "doi": True, "ten": TEN_RIENG, "kiem": gia}))
            self.assertEqual(kiem.call_count, 1)                                           # "Lưu và kiểm tra"
            self.assertEqual(self.c.get("/api/tenmien", headers=self.h).json()["rieng"], TEN_RIENG)
            r = self.c.post("/api/tenmien", json={"ten": "", "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual((r.status_code, r.json()["ten"]), (200, ""))                   # "Bỏ tên riêng"
            r = self.c.post("/api/tenmien", json={"ten": TEN_RIENG, "matkhau": MK, "ma": self.ma(khoa)})
            self.assertEqual(r.status_code, 403)                                           # thiếu dấu trang IGM360
        self.assertEqual(len(_f04(self.dl, "doi_tenmien")), 2)
        with mock.patch.dict(os.environ, {tenmien.BIEN_GOC: ""}):
            self.assertFalse(self.c.get("/api/tenmien", headers=self.h).json()["bat"])
            r = self.c.post("/api/tenmien", json={"ten": TEN_RIENG, "matkhau": MK, "ma": self.ma(khoa)}, headers=self.h)
            self.assertEqual((r.status_code, r.json()["detail"]), (409, tenmien.CHU_TENMIEN["chua_bat"]))

    def test_chu_da_duyet(self):
        self.assertEqual(self.nd.CHU_XACMINH["tenmien"], "Chỉ tài khoản Chủ đổi tên miền")   # QĐ651
        self.assertEqual(tenmien.CHU_TENMIEN["chua_bat"],
                         "Chưa bật đổi tên miền: máy chủ cần chạy 01 lệnh nâng cấu hình. Tên gốc vẫn chạy.")   # QĐ651


class KiemTenHost(unittest.TestCase):
    """QĐ656 (bổ sung QĐ634): lời qua cổng HTTPS mang tên lạ → 421; tên gốc, tên riêng đang lưu → qua."""
    setUp, tearDown = KiemDuongGoi.setUp, KiemDuongGoi.tearDown   # dùng chung máy chủ thử, không chạy lại bài của lớp kia

    def hoi(self, host, duong="/", xff=True):
        tt = {"Host": host, **({"X-Forwarded-For": IP_NGOAI, "X-Forwarded-Proto": "https"} if xff else {})}
        return self.c.get("http://testserver" + duong, headers=tt, follow_redirects=False)

    def test_ten_goc_rieng_qua_ten_la_421(self):
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        for host in (TEN_GOC, TEN_GOC.upper() + ".:443", TEN_RIENG, "IGM.vidu.test:443"):
            self.assertEqual(self.hoi(host).status_code, 200, host)
        r = self.hoi("la.vidu.test")
        self.assertEqual((r.status_code, r.text), (421, tenmien.CHU_TENMIEN["sai_host"]))
        self.assertEqual(self.hoi("la.vidu.test", "/api/toi").status_code, 421)   # đường gọi cũng chặn
        self.assertEqual(self.hoi("").status_code, 421)                              # thiếu Host

    def test_bo_ten_rieng_chan_ngay(self):
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        self.assertEqual(self.hoi(TEN_RIENG).status_code, 200)
        thongso.doi_tenmien("", "hethong", self.dl)
        self.assertEqual(self.hoi(TEN_RIENG).status_code, 421)   # Caddy còn giữ chứng chỉ, máy chủ vẫn chặn
        self.assertEqual(self.hoi(TEN_GOC).status_code, 200)     # tên gốc luôn vào được

    def test_khong_kiem(self):
        self.assertEqual(self.hoi("la.vidu.test", xff=False).status_code, 200)              # lời đi thẳng trong mạng nội bộ
        self.assertNotEqual(self.hoi("la.vidu.test", f"/tls-check?domain={TEN_RIENG}").status_code, 421)
        self.assertEqual(self.c.get("http://testserver/suckhoe", headers={"Host": "la.vidu.test"}).status_code, 200)   # /suckhoe đi thẳng
        with mock.patch.dict(os.environ, {tenmien.BIEN_GOC: ""}):
            self.assertEqual(self.hoi("la.vidu.test").status_code, 200)                      # compose cũ: chưa bật
        with mock.patch.object(tenmien, "ten_rieng", side_effect=OSError("hỏng")):
            self.assertEqual(self.hoi("la.vidu.test").status_code, 200)                      # đọc lỗi: không tự khóa
            self.assertEqual(self.hoi(TEN_GOC).status_code, 200)

    def test_suckhoe_mien_theo_loi_di_thang(self):
        """CPO chốt QD656-SUCKHOE (CDA PTD-20 mục 6; QA C11b (6b)): miễn theo lời đi thẳng, không theo đường."""
        thongso.doi_tenmien(TEN_RIENG, "hethong", self.dl)
        self.assertEqual(self.hoi("la.vidu.test", "/suckhoe").status_code, 421)   # qua cổng HTTPS + tên lạ
        for host in (TEN_GOC, TEN_RIENG):
            self.assertEqual(self.hoi(host, "/suckhoe").status_code, 200, host)
        self.assertEqual(self.hoi("la.vidu.test", "/suckhoe", xff=False).status_code, 200)   # Docker HEALTHCHECK, chay.py
        thongso.doi_tenmien("", "hethong", self.dl)
        self.assertEqual(self.hoi(TEN_RIENG, "/suckhoe").status_code, 421)   # tên vừa bỏ
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        self.assertEqual(js.count("if (r.status === 421) { const e = new Error(await r.text()); e.s421 = true; throw e; }"), 2)   # 02 vòng chờ
        self.assertIn("if (e.s421) { tieuDangCn(e.message); return; }", js)    # gặp 421: dừng chờ, hiện chữ
        self.assertIn("if (e.s421) { S.cn = 'hong'; $('#cn-lydo').textContent = e.message; ve(); return; }", js)

    def test_chu_tam(self):
        src = (GOC / "maychu/hethong/caidat/tenmien.py").read_text(encoding="utf-8")
        self.assertIn("# TẠM (QĐ656: DM soạn A/B)", src.split('"sai_host"')[1].split("\n")[0])


class KiemCompose(unittest.TestCase):
    """Tệp compose (QĐ634): giữ khối tên gốc, thêm khối On-Demand + `ask`, chặn /tls-check* ở cả 02 khối."""

    def setUp(self):
        self.dc = (GOC / "docker-compose.yml").read_text(encoding="utf-8")
        self.cf = self.dc[self.dc.index("    content: |"):self.dc.index("\nservices:")]

    def khoi(self, dau: str) -> str:
        i = self.cf.index("\n      " + dau + " {")
        return self.cf[i:self.cf.index("\n      }", i)]

    def test_hai_khoi_va_cong_gac(self):
        self.assertIn("ask http://igm360:8360/tls-check\n", self.cf)
        self.assertEqual(self.cf.count("ask "), 1)
        for dau in ("{$$DOMAIN_NAME}", "https://"):
            k = self.khoi(dau)
            self.assertIn("respond /tls-check* 404", k, dau)
            self.assertLess(k.index("respond /tls-check* 404"), k.index("reverse_proxy igm360:8360"), dau)
        self.assertIn("on_demand", self.khoi("https://"))
        self.assertNotIn("on_demand", self.khoi("{$$DOMAIN_NAME}"))   # tên gốc cấp chứng chỉ như cũ, không qua ask
        self.assertEqual(self.cf.count("reverse_proxy "), 2)
        self.assertNotIn("header_up", self.cf)   # QĐ656: Caddy chuyển nguyên Host (kiểm tên ở máy chủ dựa vào đây)
        self.assertIn("http:// {\n        redir https://{host}{uri} 308\n      }", self.cf)   # cùng 308 như tên gốc (QA T11)

    def test_bien_ten_goc_chi_o_igm360(self):
        igm = self.dc[self.dc.index("\n  igm360:"):self.dc.index("\n  gateway:")]
        self.assertIn("\n      IGM360_TEN_GOC: ${DOMAIN_NAME:-}", igm)
        self.assertEqual(self.dc.count("IGM360_TEN_GOC:"), 1)
        self.assertIn("DOMAIN_NAME: ${DOMAIN_NAME:?", self.dc[self.dc.index("\n  gateway:"):])   # gateway giữ như cũ


if __name__ == "__main__":
    unittest.main()
