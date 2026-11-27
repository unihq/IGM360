"""Bài kiểm 0.10.0 – QUAYVE-CAIMOI-A (CPO áp theo QĐ284, QĐ287; CDA phiếu 16 mục 9.42).

Dữ liệu mang số lược đồ mới hơn bản trước mà không có bản chụp trước khi nâng (cài mới ở bản 5) → nút Quay về hiện nhưng
khóa, máy chủ từ chối (cả đường gọi). Nâng 4 → 5 có bản chụp: như cũ. Bản chụp đã dọn: câu QĐ287. Số lược đồ bản trước
đọc từ CHỮ trong mã bản trước (không chạy mã cũ); cùng lược đồ hoặc không đọc được thì không khóa.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, ketnoi, muigio
from maychu.hethong import antoan, capnhat


class Nen(unittest.TestCase):
    def setUp(self):
        self.tam = tempfile.TemporaryDirectory()
        self.addCleanup(self.tam.cleanup)
        t = Path(self.tam.name)
        self.dl = t / "dulieu"
        bien = mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": str(self.dl), "IGM360_LICH": "tat"})
        bien.start()
        self.addCleanup(bien.stop)
        muigio.xoa_dem()
        self.addCleanup(muigio.xoa_dem)
        khoitao.tao_het(self.dl)   # cài mới: 07 tệp tạo thẳng ở lược đồ bản này
        self.g = t / "app"
        (self.g / "ban_truoc" / "maychu" / "dulieu").mkdir(parents=True)
        (self.g / "VERSION").write_text("0.10.0\n", encoding="utf-8")
        (self.g / "ban_truoc" / "VERSION").write_text("0.9.4\n", encoding="utf-8")
        self.ma_cu(f"PHIENBAN_LUOCDO = {khoitao.PHIENBAN_LUOCDO - 1}\n")
        for vao in (mock.patch.object(antoan, "GOC_MA", self.g), mock.patch.object(capnhat, "ban_dang_chay", return_value="0.10.0"),
                    mock.patch.object(antoan, "_thoat")):
            vao.start()
            self.addCleanup(vao.stop)
        self.addCleanup(antoan.CHE_DO.update, an_toan=False)

    def ma_cu(self, chu: str | None):
        p = self.g / "ban_truoc" / "maychu" / "dulieu" / "khoitao.py"
        if chu is None:
            p.unlink(missing_ok=True)
        else:
            p.write_text('"""mã bản trước – chỉ đọc chữ"""\nimport os\n' + chu + "raise SystemExit('không được chạy')\n",
                         encoding="utf-8")


class KiemQuayVe(Nen):
    def test_cai_moi_ban_moi_khoa_va_tu_choi(self):
        self.assertEqual((antoan.luocdo_ban_truoc(), antoan.luocdo_dulieu(self.dl)),
                         (khoitao.PHIENBAN_LUOCDO - 1, khoitao.PHIENBAN_LUOCDO))
        q = antoan.thong_tin_quayve(self.dl)
        self.assertEqual(q, {"co": True, "khoa": True, "ban": "0.9.4", "mat_tu": None, "chu": antoan.CHU["qv_luocdo_moi"]})
        self.assertEqual(antoan.quay_ve("nguoi", True, self.dl), {"loi": antoan.CHU["qv_luocdo_moi"]})
        self.assertNotIn("chay_ban_truoc", antoan.doc(self.dl))   # không ghi cờ chạy bản trước

    def test_nang_4_len_5_co_ban_chup_nhu_cu(self):
        khoitao._chup_het(self.dl, ketnoi.CAC_FILE)
        antoan.ghi(self.dl, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": "0.10.0", "luc": "2026-11-27T10:05:00+07:00"})
        q = antoan.thong_tin_quayve(self.dl)
        self.assertEqual((q["co"], q.get("khoa"), q["mat_tu"][:16]), (True, None, "2026-11-27T10:05"))
        self.assertEqual(antoan.quay_ve("nguoi", False, self.dl)["loi"], antoan.CHU["qv_can_dong_y"])

    def test_ban_chup_da_don_cau_qd287(self):
        antoan.ghi(self.dl, nang_luocdo={"den": khoitao.PHIENBAN_LUOCDO, "ban": "0.10.0", "luc": "2026-11-27T10:05:00+07:00"})
        q = antoan.thong_tin_quayve(self.dl)
        self.assertTrue(q["khoa"])
        self.assertTrue(q["chu"] == antoan.CHU["qv_het_han_khong_ngay"] or q["chu"].startswith("Không còn dữ liệu bản sao"),
                        q["chu"])   # câu QĐ287 / QĐ296, không phải câu mới

    def test_cung_luoc_do_hoac_khong_doc_duoc_thi_khong_khoa(self):
        for chu in (f"PHIENBAN_LUOCDO = {khoitao.PHIENBAN_LUOCDO}\n", None, "PHIENBAN_LUOCDO = khoitao_moi()\n"):
            self.ma_cu(chu)
            q = antoan.thong_tin_quayve(self.dl)
            self.assertEqual((q.get("khoa"), q["chu"]), (None, antoan.CHU["qv_giu"]), chu)

    def test_duong_goi_tu_choi(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.web import api
        khoidong.app.dependency_overrides[api.can_dang_nhap] = lambda: {"nguoidung_id": "nguoi"}
        self.addCleanup(khoidong.app.dependency_overrides.clear)
        with TestClient(khoidong.app) as c:
            r = c.post("/api/capnhat/quayve", json={"dong_y_mat": True}, headers={"X-IGM360": "1"})
        self.assertEqual((r.status_code, r.json()["detail"]), (400, antoan.CHU["qv_luocdo_moi"]))
        self.assertNotIn("chay_ban_truoc", antoan.doc(self.dl))

    def test_chu_qd655(self):
        self.assertEqual(antoan.CHU["qv_luocdo_moi"],
                         "Không quay về được bản trước. Lý do: phần mềm cài mới trên máy chủ này, chưa có dữ liệu của bản trước.")
        self.assertNotIn("TẠM", (Path(antoan.__file__)).read_text(encoding="utf-8").split('"qv_luocdo_moi"')[0][-300:])

    def test_dong_tu_mat_o_lan_cap_nhat_dau(self):
        """QĐ655: lên bản sau cùng lược đồ (bản trước = bản cài mới) → dòng khóa mất, hiện qv_giu."""
        (self.g / "ban_truoc" / "VERSION").write_text("0.10.0\n", encoding="utf-8")
        self.ma_cu(f"PHIENBAN_LUOCDO = {khoitao.PHIENBAN_LUOCDO}\n")
        with mock.patch.object(capnhat, "ban_dang_chay", return_value="0.10.1"):
            q = antoan.thong_tin_quayve(self.dl)
        self.assertEqual((q.get("khoa"), q["ban"], q["chu"]), (None, "0.10.0", antoan.CHU["qv_giu"]))


if __name__ == "__main__":
    unittest.main()
