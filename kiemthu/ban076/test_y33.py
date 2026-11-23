"""Bài kiểm bản 0.7.6 (QĐ187, PTD-08 Đ1, Đ5, Đ6; CDA K-MH5; bản vẽ Z11): chọn theo mô hình, không chia tài khoản.
Mã loại nguồn 01 hàm, thứ tự 03 tầng, danh sách gộp theo loại, mặc định đọc theo loại + mã, ghim thử lần lượt tài khoản
cùng loại, ghim dạng cũ đổi sang khoá; N1–N3. Dữ liệu giả, không gọi CLI thật."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maychu.dulieu import ketnoi
from maychu.hethong.mohinh import congai, dangnhap_goi as dg, danhmuc_mohinh as dm, trochuyen
from kiemthu.ban075.test_y31 import Nen

GOC = Path(__file__).resolve().parents[2]
GD = GOC / "maychu/web/giaodien"


class KiemThuTu(unittest.TestCase):
    def test_ma_loai_nguon_01_ham(self):
        self.assertEqual([dg.loai_nguon({"ma": m}) for m in ("goi_claude_01", "goi_claude_02", "goi_chatgpt_01", "khoa_anthropic_01",
                                                             "khoa_openai_02", "nguon_tu_khai")],
                         ["goi_claude", "goi_claude", "goi_chatgpt", "khoa_anthropic", "khoa_openai", "nguon_tu_khai"])

    def test_thu_tu_03_tang(self):
        ds = [{"ma": "goi_claude_01", "loai": "goi", "uutien": 1}, {"ma": "goi_chatgpt_01", "loai": "goi", "uutien": 2},
              {"ma": "goi_claude_02", "loai": "goi", "uutien": 3}, {"ma": "khoa_anthropic_01", "loai": "khoa_api", "uutien": 0}]
        self.assertEqual([d["ma"] for d in dg.thu_tu(ds)], ["goi_claude_01", "goi_claude_02", "goi_chatgpt_01", "khoa_anthropic_01"])


class KiemTheoMoHinh(Nen):
    def setUp(self):
        super().setUp()
        self.c1 = self.nguon("goi_claude_01", "goi", 1, "anthropic")
        self.g1 = self.nguon("goi_chatgpt_01", "goi", 2, "openai")
        self.c2 = self.nguon("goi_claude_02", "goi", 3, "anthropic")
        self.goi, self.het = [], set()

        def claude(tk, cau, mohinh):
            self.goi.append((tk, mohinh))
            if (tk, mohinh) in self.het or (tk, "*") in self.het:
                raise congai.HetHanMuc("limit reached", {})
            return {"chu": "ok", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {},
                    "mohinh_bao": None}
        self.vas2 = [mock.patch.object(congai, "_goi_claude", side_effect=claude),
                     mock.patch.object(congai, "_goi_chatgpt", side_effect=lambda tk, cau, mh: self.goi.append(("gpt", mh)) or {
                         "chu": "gpt", "vao": 1, "ra": 1, "sotien": None, "sotien_thamkhao": None, "tien_ma": "USD", "hanmuc": {},
                         "mohinh_bao": None})]
        for v in self.vas2:
            v.start()

    def tearDown(self):
        for v in self.vas2:
            v.stop()
        super().tearDown()

    def ngung(self, nid):
        cn = ketnoi.mo("Viecnen")
        try:
            cn.execute("UPDATE nguon_ai SET trangthai = 'ngung' WHERE id = ?", (nid,))
        finally:
            cn.close()

    def test_gop_nhom_theo_loai(self):
        ds = dm.danh_sach()
        self.assertEqual([g["nhom"] for g in ds["nhom"]], ["goi_claude", "goi_chatgpt"])   # 01 nhóm mỗi loại, thứ tự Đ5
        cl = ds["nhom"][0]
        self.assertEqual((cl["nguon_ids"], cl["khoa_md"], cl["chinh"]), ([self.c1, self.c2], "goi_claude|", True))
        self.assertEqual([m["khoa"] for m in cl["mohinh"]], ["goi_claude|haiku", "goi_claude|sonnet", "goi_claude|opus", "goi_claude|fable"])
        self.assertEqual(len(cl["mohinh"][1]["ids"]), 2)                    # sonnet của cả 02 tài khoản

    def test_mac_dinh_theo_loai_va_ma_D6(self):
        dm.danh_sach()
        dm.dat_macdinh("trochuyen", khoa="goi_claude|sonnet")
        ct = dm.macdinh_chi_tiet()["trochuyen"]
        self.assertEqual((ct["khoa"], ct["nhom"], ct["ma"], ct["mat"]), ("goi_claude|sonnet", "goi_claude", "sonnet", False))
        self.ngung(self.c1)                                                 # gỡ tài khoản đang giữ dấu
        self.assertFalse(dm.macdinh_chi_tiet()["trochuyen"]["mat"])        # tài khoản cùng loại còn: mặc định còn
        congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi[-1], (2, "sonnet"))                       # chạy trên Claude 2
        self.ngung(self.c2)
        self.assertTrue(dm.macdinh_chi_tiet()["trochuyen"]["mat"])         # cả nhóm mất: về nguồn ưu tiên 1, có báo
        self.assertIsNone(dm.macdinh_khoa("trochuyen"))
        congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi[-1], ("gpt", None))
        dm.dat_macdinh("dexuat", khoa="goi_chatgpt|")                       # mặc định của loại nguồn
        self.assertEqual(dm.macdinh_chi_tiet()["dexuat"]["khoa"], "goi_chatgpt|")
        with self.assertRaisesRegex(ValueError, "Nguồn không còn dùng được"):
            dm.dat_macdinh("dexuat", khoa="goi_claude|sonnet")

    def test_het_han_muc_sang_tai_khoan_cung_loai_D5(self):
        self.het.add((1, "*"))
        kq = congai.goi("hỏi", loai_viec="trochuyen")
        self.assertEqual(self.goi, [(1, None), (2, None)])                  # Claude 1 hết → Claude 2, chưa sang ChatGPT
        self.assertEqual(kq["nguon_id"], self.c2)

    def test_ghim_thu_moi_tai_khoan_cung_loai_D1(self):
        dm.danh_sach()
        self.het.add((1, "opus"))
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [(1, "opus"), (2, "opus")])
        self.assertEqual((kq["nguon_id"], kq["mohinh"], kq["ghim_hong"], kq["ghim_khoa"]), (self.c2, "opus", None, "goi_claude|opus"))
        cn = ketnoi.mo("Nhatky")
        try:
            moi = cn.execute("SELECT nguon_ai_id, mohinh_id FROM nhatky_ai ORDER BY rowid DESC LIMIT 1").fetchone()
        finally:
            cn.close()
        self.assertEqual(moi, (self.c2, dm.dong_cua(self.c2, "opus")["id"]))   # G04 ghi đúng tài khoản thực chạy
        self.goi.clear()
        self.het.add((2, "opus"))
        kq = congai.goi("hỏi", loai_viec="trochuyen", mohinh_id="goi_claude|opus")
        self.assertEqual(self.goi, [(1, "opus"), (2, "opus"), (1, None)])  # hết mọi tài khoản cùng loại mới về mặc định (QĐ183)
        self.assertEqual(kq["ghim_hong"], {"khoa": "goi_claude|opus", "ma": "opus", "het_hanmuc": True, "lydo": "hết hạn mức"})

    def test_ghim_dang_cu_doi_sang_khoa(self):
        dm.danh_sach()
        cu = dm.dong_cua(self.c1, "haiku")["id"]                             # id G08 của 0.7.5
        self.assertEqual(dm.chuan_khoa(cu), "goi_claude|haiku")
        self.assertIsNone(dm.chuan_khoa("goi_claude|"))                     # khoá mặc định không phải ghim
        kq = trochuyen.gui(None, "nguoi_gia", "Chào", mohinh_id=cu)
        self.assertEqual((kq["tra_loi"]["mohinh"], kq["tra_loi"]["ghim_khoa"]), ("haiku", "goi_claude|haiku"))


class KiemGiaoDien076(unittest.TestCase):
    def setUp(self):
        self.js = (GD / "app.js").read_text(encoding="utf-8")

    def test_z11_n1_n3(self):
        for chu in ("'Nhiều tài khoản cùng loại: dùng tài khoản đang chạy, hết hạn mức mới sang tài khoản dự phòng\">'",
                    "data-mhnhom=\"' + esc(g.nhom) + '\"", "data-mhchon=\"' + esc(m.khoa) + '\"", "{loai_viec: lv, khoa: x.m.khoa}",
                    "{loai_viec: lv, khoa: g.khoa_md}", "const ghimKhoa = () =>", "gh = ghimKhoa();",
                    "(MH.dich && mdLoai(MH.dich)) || {g: nhomChinh(), m: null}",                     # N1
                    "(noi === 'chat' ? !dang.ghim : !dang.m)",                                       # N2
                    "(mh ? tenMh(mh, n.id, n, true) : 'Mặc định')", "tenMh(mhThucDung(x), x.nguon_id, n, true)",   # N3
                    "' title=\"Bản cụ thể: ' + esc(mhThucDung(x))"):
            self.assertIn(chu, self.js, chu)
        self.assertNotIn("g.nguon_id === g.nguon_id", self.js)
        self.assertEqual((GOC / "VERSION").read_text(encoding="utf-8").strip(), "0.7.6")

    @unittest.skipUnless(shutil.which("node"), "máy không có node")
    def test_n3_ten_ngan_chay_that(self):
        lay = lambda ten: self.js[self.js.index("const " + ten + " "):self.js.index("\nconst ", self.js.index("const " + ten + " ") + 5)]
        ham = "\n".join(lay(t) for t in ("NB", "TEN_NGUON_GOI", "TEN_NGUON_HANG", "tenNguon", "chuHoa", "laSo", "phanMh", "hangCua",
                                         "gocMh", "nhomMh", "tenHang", "tenMh", "timNguon"))
        nhom = [{"nhom": "goi_claude", "nguon_ids": ["c1", "c2"], "goi": "claude",
                 "mohinh": [{"ma": "sonnet"}, {"ma": "claude-sonnet-4-5"}]}]
        ma = ("const esc = s => s; const D = {md: null, dsmh: {nhom: " + json.dumps(nhom) + "}};\n" + ham
              + "\nconsole.log(JSON.stringify([tenMh('claude-sonnet-4-5-20250929', 'c2', null, true), tenMh('claude-sonnet-4-5', 'goi_claude'),"
              + " tenMh('sonnet', 'goi_claude')]));")
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "thu.js"
            p.write_text(ma, encoding="utf-8")
            r = subprocess.run(["node", str(p)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ["Sonnet", "Sonnet 4.5", "Sonnet"])   # dòng nguồn: tên ngắn; bảng: số bản khi trùng


if __name__ == "__main__":
    unittest.main()
