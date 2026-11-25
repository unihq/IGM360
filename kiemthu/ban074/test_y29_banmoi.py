"""Bài kiểm bản 0.7.4 (QĐ174, Y29 bổ sung 2): dò bản mới 05 phút. Kho ảnh, kho mã là kho giả trong máy (không gọi
mạng thật); đồng hồ giả để chạy nhanh 24 giờ."""
import asyncio
import unittest
from pathlib import Path
from unittest import mock

import httpx

from maychu.hethong import capnhat
from maychu.hethong.giamsat import lich, thongbao
from maychu.web import api

GOC = Path(__file__).resolve().parents[2]
_CLIENT = httpx.Client
THAYDOI_GIA = "## 0.7.5\nTóm tắt: Bản giả\n- Dòng giả\n\n## 0.7.4\nTóm tắt: Bản đang chạy giả\n"


class KhoGia:
    """ghcr.io + raw.githubusercontent.com giả: ghi lại từng lượt hỏi."""

    def __init__(self):
        self.nhan = ["0.7.3", "0.7.4"]
        self.da_dong = {"0.7.3", "0.7.4"}
        self.loi_mang = False
        self.ma_thaydoi = 200
        self.luot = []

    def xu_ly(self, req: httpx.Request) -> httpx.Response:
        self.luot.append((req.method, req.url.host, req.url.path))
        if self.loi_mang:
            raise httpx.ConnectError("mất mạng giả", request=req)
        p = req.url.path
        if p == "/token":
            return httpx.Response(200, json={"token": "gia"})
        if p.endswith("/tags/list"):
            return httpx.Response(200, json={"tags": self.nhan + ["latest"]})
        if "/manifests/" in p:
            return httpx.Response(200 if p.rsplit("/", 1)[1] in self.da_dong else 404)
        if p.endswith("/THAYDOI.md"):
            return httpx.Response(self.ma_thaydoi, text=THAYDOI_GIA if self.ma_thaydoi == 200 else "")
        return httpx.Response(404)

    def dem(self, host: str | None = None) -> int:
        return sum(1 for x in self.luot if host is None or x[1] == host)


class CoSo(unittest.TestCase):
    def setUp(self):
        self.kho = KhoGia()
        self.gio = [1_000_000.0]
        self.vas = [
            mock.patch.object(capnhat.httpx, "Client", lambda **kw: _CLIENT(transport=httpx.MockTransport(self.kho.xu_ly), **kw)),
            mock.patch.object(capnhat.time, "time", lambda: self.gio[0]),
            mock.patch.object(capnhat, "ban_dang_chay", return_value="0.7.4"),
        ]
        for v in self.vas:
            v.start()
        capnhat._NHO.update(luc=0.0, luc_dat=0.0, ban_moi=None, thaydoi=[], tomtat={}, loi=None, nhan_thaydoi=None)

    def tearDown(self):
        for v in self.vas:
            v.stop()
        capnhat._NHO.update(luc=0.0, luc_dat=0.0, ban_moi=None, thaydoi=[], tomtat={}, loi=None, nhan_thaydoi=None)


class KiemDoBanMoi(CoSo):
    def test_01_nho_05_phut(self):
        self.assertEqual(capnhat.nhip_kiem_giay(), 300)
        capnhat.kiem_tra()
        n = self.kho.dem()
        self.gio[0] += 299
        capnhat.kiem_tra()
        self.assertEqual(self.kho.dem(), n)          # trong 05 phút: không hỏi kho
        self.gio[0] += 2
        capnhat.kiem_tra()
        self.assertGreater(self.kho.dem(), n)        # quá 05 phút: hỏi lại
        n = self.kho.dem()
        capnhat.kiem_tra(bat_buoc=True)              # nút Kiểm tra lại: hỏi ngay
        self.assertGreater(self.kho.dem(), n)

    def test_02_chuong_quet_rieng_05_phut(self):
        src = (GOC / "maychu/hethong/giamsat/lich.py").read_text(encoding="utf-8")
        self.assertIn("capnhat.nhip_kiem_giay()", src)
        self.assertIn("await asyncio.to_thread(thongbao.quet_banmoi, None, True)", src)
        self.assertEqual(lich.NHIP_THONGBAO_GIAY, 600)   # loại tin khác giữ 10 phút

    def test_03_mo_chuong_hoi_ngay_khi_cu(self):
        cn = mock.Mock()
        cn.execute.return_value.fetchone.return_value = (0,)
        with mock.patch.object(api.ketnoi, "mo", return_value=cn), \
                mock.patch.object(api.thongbao, "danh_sach", return_value={"ds": [], "so_moi": 0}), \
                mock.patch.object(api.thongbao, "quet_banmoi") as qb:
            api.dem_so(mo=0, p={"nguoidung_id": "x"})
            self.assertEqual(qb.call_count, 0)           # 60 giây/lần: không dò
            api.dem_so(mo=1, p={"nguoidung_id": "x"})
            self.assertEqual(qb.call_count, 1)           # mở chuông: dò (kết quả dưới 05 phút thì không hỏi kho)
            qb.side_effect = RuntimeError("hỏng")
            api.dem_so(mo=1, p={"nguoidung_id": "x"})    # dò lỗi không làm hỏng chuông
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        self.assertIn("if (v) demSo(true); }", js)
        self.assertIn("api('/demso' + (mo ? '?mo=1' : ''))", js)
        # Màn Cập nhật gọi /api/capnhat → kiem_tra(): quá 05 phút thì hỏi (test_01)

    def test_04_chi_bao_khi_goi_da_dong(self):
        self.kho.nhan.append("0.7.5")                    # nhãn có nhưng gói đang đóng
        kq = capnhat.kiem_tra(bat_buoc=True)
        self.assertEqual((kq["ban_moi"], kq["co_ban_moi"]), ("0.7.4", False))
        self.assertIn(("HEAD", "ghcr.io", "/v2/unihq/igm360/manifests/0.7.5"), self.kho.luot)
        self.assertIn("Chưa có bản mới đóng gói xong", capnhat.yeu_cau("x", "ngay")["loi"])
        self.kho.da_dong.add("0.7.5")
        self.gio[0] += 301
        kq = capnhat.kiem_tra()
        self.assertEqual((kq["ban_moi"], kq["co_ban_moi"]), ("0.7.5", True))
        self.assertEqual(kq["thaydoi"][0]["ban"], "0.7.5")

    def test_05_thaydoi_chi_tai_khi_co_nhan_moi(self):
        capnhat.kiem_tra()
        self.assertEqual(self.kho.dem("raw.githubusercontent.com"), 1)   # lần đầu: lấy chữ tóm tắt cho lịch sử
        for _ in range(5):
            self.gio[0] += 301
            n = self.kho.dem()
            capnhat.kiem_tra()
            self.assertEqual(self.kho.dem() - n, 2)                        # bình thường: 02 lượt (khóa + danh sách nhãn)
        self.assertEqual(self.kho.dem("raw.githubusercontent.com"), 1)
        self.kho.nhan.append("0.7.5")
        self.kho.da_dong.add("0.7.5")
        self.gio[0] += 301
        capnhat.kiem_tra()
        self.assertEqual(self.kho.dem("raw.githubusercontent.com"), 2)   # có nhãn mới: tải lại 01 lần

    def test_06_loi_giu_ket_qua_cu(self):
        self.kho.loi_mang = True
        kq = capnhat.kiem_tra()
        self.assertIn("Chưa kiểm được bản mới", kq["loi"])               # chưa từng kiểm được: nói rõ
        self.kho.loi_mang = False
        self.gio[0] += 301
        self.kho.nhan.append("0.7.5")
        self.kho.da_dong.add("0.7.5")
        kq = capnhat.kiem_tra()
        luc = kq["luc_kiem"]
        self.assertEqual((kq["ban_moi"], kq["loi"]), ("0.7.5", None))
        self.kho.loi_mang = True                                          # GitHub từ chối / mất mạng
        self.gio[0] += 301
        kq = capnhat.kiem_tra()
        self.assertEqual((kq["ban_moi"], kq["co_ban_moi"], kq["loi"], kq["luc_kiem"]), ("0.7.5", True, None, luc))
        n = self.kho.dem()
        self.gio[0] += 301
        capnhat.kiem_tra()
        self.assertGreater(self.kho.dem(), n)                             # lượt sau hỏi lại
        # THAYDOI bị từ chối khi đã có nội dung cũ: giữ, không báo, lượt sau tải lại
        self.kho.loi_mang = False
        self.kho.nhan.append("0.7.6")
        self.kho.da_dong.add("0.7.6")
        self.kho.ma_thaydoi = 429
        self.gio[0] += 301
        kq = capnhat.kiem_tra()
        self.assertEqual((kq["ban_moi"], kq["loi"]), ("0.7.6", None))
        self.assertEqual(kq["tomtat"].get("0.7.5"), "Bản giả")
        r = self.kho.dem("raw.githubusercontent.com")
        self.kho.ma_thaydoi = 200
        self.gio[0] += 301
        capnhat.kiem_tra()
        self.assertEqual(self.kho.dem("raw.githubusercontent.com"), r + 1)

    def test_07_nhip_o_01_cho(self):
        with mock.patch.object(capnhat, "NHIP_KIEM_GIAY", 60):
            capnhat.kiem_tra()
            n = self.kho.dem()
            self.gio[0] += 61
            kq = capnhat.kiem_tra()
            self.assertGreater(self.kho.dem(), n)
            self.assertEqual(kq["nhip_phut"], 1)
        src = (GOC / "maychu/hethong/capnhat.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("NHIP_KIEM_GIAY"), 2)   # 01 dòng gán + 01 dòng đọc trong nhip_kiem_giay()

    def test_08_chu_man_cap_nhat(self):
        html = (GOC / "maychu/web/giaodien/index.html").read_text(encoding="utf-8")
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        self.assertNotIn("06&nbsp;giờ", html)
        self.assertIn('tự kiểm tra mỗi <span id="cn-nhip">05&nbsp;phút</span>', html)
        self.assertIn("$('#cn-nhip').innerHTML = hai(d.nhip_phut) + '&nbsp;phút'", js)


class Do24Gio(CoSo):
    """Chạy lịch nền thật (`lich.chay_mai`) 24 giờ trên đồng hồ giả, đếm lượt hỏi kho. Kèm 30 lần mở chuông, 10 lần
    mở màn Cập nhật rải trong ngày (kết quả còn mới thì không hỏi kho)."""

    def chay(self, so_phut: int = 24 * 60) -> None:
        vong = [0]

        async def ngu(_giay):
            vong[0] += 1
            self.gio[0] += 60
            if vong[0] % 48 == 0:
                api.thongbao.quet_banmoi()           # mở chuông
            if vong[0] % 144 == 0:
                capnhat.kiem_tra()                    # mở màn Cập nhật
            if vong[0] >= so_phut:
                raise asyncio.CancelledError

        async def chinh():
            loop = asyncio.get_running_loop()
            loop.time = lambda: self.gio[0]
            await lich.chay_mai()

        thua = mock.Mock(return_value={"dat": "dat"})
        with mock.patch.object(lich.asyncio, "sleep", ngu), \
                mock.patch.object(lich.domay, "ghi_n02"), mock.patch.object(lich.thongbao, "quet_maychu"), \
                mock.patch.object(lich.capnhat, "xu_ly_cho"), mock.patch.object(lich.saoluu, "da_co_hom_nay", return_value=True), \
                mock.patch.object(lich.thongbao, "quet", thua), mock.patch.object(lich.drive, "day_hang_cho", return_value={}), \
                mock.patch.object(thongbao, "_Ghi"), \
                mock.patch.object(lich.nangcli, "da_kiem_hom_nay", return_value=True), \
                mock.patch.object(lich.thongso, "drive_bat", return_value=False), \
                mock.patch.object(lich.congai, "quet_codex"):   # Y46 móc /dulieu: bài này chỉ đo dò bản mới, không mở dữ liệu
            try:
                asyncio.run(chinh())
            except asyncio.CancelledError:
                pass

    def test_dem_luot_hoi_24_gio(self):
        self.chay()
        lan_kiem = sum(1 for x in self.kho.luot if x[2] == "/token")
        self.assertEqual(lan_kiem, 288)                                   # 24 × 60 / 05
        self.assertEqual(self.kho.dem("ghcr.io"), 576)                     # 02 lượt mỗi lần
        self.assertEqual(self.kho.dem("raw.githubusercontent.com"), 1)     # THAYDOI 01 lần (chưa có nhãn mới)
        print(f"\n[Y29 đo 24 giờ, không có bản mới] lần kiểm {lan_kiem}, ghcr.io {self.kho.dem('ghcr.io')}, "
              f"raw {self.kho.dem('raw.githubusercontent.com')}, tổng {self.kho.dem()}")

    def test_dem_luot_hoi_24_gio_co_ban_moi(self):
        self.kho.nhan.append("0.7.5")
        self.kho.da_dong.add("0.7.5")
        self.chay()
        self.assertEqual(sum(1 for x in self.kho.luot if x[2] == "/token"), 288)
        self.assertEqual(self.kho.dem("ghcr.io"), 864)                     # 03 lượt: thêm hỏi đúng nhãn 0.7.5
        print(f"\n[Y29 đo 24 giờ, có bản mới chưa cài] ghcr.io {self.kho.dem('ghcr.io')}, "
              f"raw {self.kho.dem('raw.githubusercontent.com')}, tổng {self.kho.dem()}")


if __name__ == "__main__":
    unittest.main()
