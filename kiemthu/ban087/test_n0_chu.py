"""Bài kiểm ghim chữ bản 0.8.7 (QĐ358, anh "Duyệt A cả 02"; bảng chữ CDO "Câu Có gì mới 0.8.7" CGM-087b và
"02 câu báo lỗi mới của N0 0.8.7"): VERSION, mục THAYDOI 0.8.7 đúng từng ký tự, 02 câu báo lỗi N2 (không dấu chấm cuối).
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import khoitao, maso
from maychu.hethong.mohinh import trochuyen

GOC = Path(__file__).resolve().parents[2]
C1 = "AI đang trả lời câu hỏi trước. Bạn gửi câu mới khi câu trả lời xong"
C2 = "Câu trả lời này đã xong hoặc không còn chạy. Bạn mở lại hội thoại để xem"


class KiemChu087(unittest.TestCase):
    def test_version_va_muc_087_nguyen_van_qd358(self):
        so = tuple(int(x) for x in (GOC / "VERSION").read_text(encoding="utf-8").strip().split("."))
        self.assertGreaterEqual(so, (0, 8, 7))                                    # bản sau giữ mục 0.8.7 nguyên văn (QĐ376)
        dong = (GOC / "THAYDOI.md").read_text(encoding="utf-8").splitlines()
        i = dong.index("## 0.8.7")
        self.assertEqual(dong[i:i + 8], [
            "## 0.8.7",
            "Tóm tắt: Trả lời chạy nền",
            "Nâng dữ liệu: không",
            "- Claude và ChatGPT hiện chữ chạy dần trong lúc trả lời.",
            "- Câu trả lời của AI chạy trên máy chủ: bạn tải lại hoặc đóng trang giữa chừng, câu trả lời vẫn chạy tiếp và tự lưu;"
            " mở lại hội thoại, câu trả lời hiện khi xong.",
            "- Khi phần mềm đang chờ cập nhật, câu hỏi mới chưa được nhận: khung chat báo ngay dưới câu hỏi, câu hỏi vẫn ở ô nhập"
            " để bạn gửi lại sau khi cập nhật xong.",
            "- Phần mềm khởi động lại giữa lúc AI đang trả lời thì hội thoại có tin báo câu trả lời bị ngắt để bạn gửi lại câu"
            " hỏi; tin này không có nút \"Mở Mô hình AI\".",
            "",
        ])                                                                        # QĐ358 (A), đúng từng ký tự
        self.assertEqual(dong[i + 8], "## 0.8.6")
        self.assertLess(dong.index("## 0.8.7"), dong.index("## 0.8.6"))           # mục mới ở đầu

    def test_n2_cau_1_gui_dong_bo_khi_dang_tra_loi(self):
        ma = (GOC / "maychu/hethong/mohinh/trochuyen.py").read_text(encoding="utf-8")
        self.assertIn('raise DangTraLoi("' + C1 + '")', ma)
        self.assertFalse(C1.endswith("."))                                        # báo nổi tự thêm dấu chấm
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        self.assertIn("$('#ds-tin').innerHTML = cu.map(tinHtml).join(''); o.value = nd;", js)   # câu hỏi trở lại ô nhập (SUA-BT7: mọi lỗi)

    def test_n2_cau_2_luong_su_kien_khong_con(self):
        from fastapi.testclient import TestClient
        from maychu import khoidong
        from maychu.web import api
        tam = tempfile.TemporaryDirectory()
        self.addCleanup(tam.cleanup)
        with mock.patch.dict(os.environ, {"IGM360_THUMUC_DULIEU": tam.name, "IGM360_LICH": "tat"}):
            khoitao.tao_het(Path(tam.name))
            khoidong.app.dependency_overrides[api.can_dang_nhap] = lambda: {"nguoidung_id": maso.tao()}
            self.addCleanup(khoidong.app.dependency_overrides.clear)
            r = TestClient(khoidong.app).get("/api/trochuyen/luot/khong-co/sukien")
        self.assertEqual((r.status_code, r.json()["detail"]), (404, C2))
        self.assertFalse(C2.endswith("."))
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        self.assertIn("moHt(D.htId).catch(async () => {", js)                     # chỉ hiện khi tải lại hội thoại cũng lỗi
        self.assertIn("await api('/trochuyen/luot/' + encodeURIComponent(id) + '/sukien'); } catch (e) { bao(e.message + '.', 'loi'); }", js)

    def test_qd361_cau_bao_mat_ket_noi(self):
        js = (GOC / "maychu/web/giaodien/app.js").read_text(encoding="utf-8")
        cau = "Mất kết nối máy chủ, thao tác này chưa lưu được. Bạn thử lại khi đã nối lại"
        self.assertIn("} catch (e) { S.k = 'matketnoi'; ve();", js)                # dải đỏ giữ như cũ
        i = js.index("const m = new Error('") + len("const m = new Error('")
        nguon = js[i:js.index("')", i)]                                           # chữ trong mã, U+00A0 viết dạng mã JS
        hien = nguon.replace("\\u00a0", "\u00a0")
        self.assertEqual(hien.replace("\u00a0", " "), cau)                     # QĐ361 (A): đổi U+00A0 về cách thường thì đúng bảng chữ
        self.assertEqual(hien.count("\u00a0"), 1)                                # SUA-NBSP: đúng 01 chỗ
        self.assertIn("nối\u00a0lại", hien)                                     # ở cụm "nối lại" (Phần 3: không tách cụm)
        self.assertFalse(cau.endswith("."))                                         # báo nổi tự thêm dấu chấm
        self.assertEqual(js.count("bao(e.message + '.', 'loi')"), 23)                      # 18 chỗ + 03 chỗ ngăn Chung (QĐ627) + 02 chỗ ngăn Két khóa (0.10.0) cùng hiện câu này

    def test_khong_con_chu_cu(self):
        for tep in ("maychu/hethong/mohinh/trochuyen.py", "maychu/web/api.py"):
            ma = (GOC / tep).read_text(encoding="utf-8")
            self.assertNotIn("Cuộc trò chuyện đang có câu trả lời chưa xong", ma)
            self.assertNotIn("Không có lượt trả lời này", ma)
        self.assertTrue(issubclass(trochuyen.DangTraLoi, Exception))


if __name__ == "__main__":
    unittest.main()
