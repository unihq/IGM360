"""Cửa chặn tự gộp bản sửa lỗi (QĐ259, QĐ266; danh sách chặn do CDA lập, KT-Y44: 14 đường dẫn + 06 luật).

Chạy trên máy GitHub bằng tệp luồng tugop.yml (bản của main, không chạy mã của nhánh sửa lỗi): chỉ đọc phần đổi giữa
`--goc` (main) và `--dau` (nhánh sualoi/*), tính từ điểm rẽ nhánh (`goc...dau`, CDA KT-Y44c N1: main đi trước nhánh
không bị chặn nhầm); số bản, mục THAYDOI vẫn so với main mới nhất. Có vi phạm thì in từng dòng "Luật …" và trả mã 1: không tự gộp, chuyển loại 2
(CDA, CDO soát, anh duyệt). Chỉ dùng thư viện chuẩn Python.

Luật (số theo Phần 11):
- 01–14 chặn theo đường dẫn.
- 15 lệnh tạo, sửa, xoá cấu trúc dữ liệu; 16 thư viện ngoài mới, nạp module động; 17 dòng "Nâng dữ liệu"; 18 bài kiểm cũ
  (không xoá, không sửa dòng, không thêm lệnh bỏ qua, không trùng tên hàm trong 01 lớp, số bài chạy không ít hơn, số bài bỏ
  qua không nhiều hơn main); 20 thêm, xoá, đổi tên tệp ngoài kiemthu/; 21 chuỗi tiếng Việt có dấu (chữ người dùng thấy)
  trong mã Python (bỏ chuỗi mô tả hàm, chú thích).
- Kèm: nhánh tên sualoi/*, số bản tăng đúng 01 ở số cuối, mục THAYDOI của bản mới có Tóm tắt và ít nhất 01 dòng "- ",
  mỗi dòng "- " theo khuôn "Sửa lỗi <mô tả ngắn>" (QĐ270).
"""
import argparse
import ast
import fnmatch
import re
import subprocess
import sys

CHAN_DUONG_DAN = (   # 11.1: 14 mục
    ("01", "maychu/dulieu/**"), ("02", "maychu/chay.py"), ("03", "maychu/khoidong.py"), ("04", "maychu/hethong/antoan.py"),
    ("05", "maychu/hethong/capnhat.py"), ("06", "maychu/hethong/tiendo.py"), ("07", "maychu/ketnoi/drive.py"),
    ("08", "maychu/hethong/giamsat/lich.py"), ("09", "maychu/hethong/caidat/thongso.py"), ("10", "maychu/ketnoi/hoptin.py"),
    ("11", "requirements.txt"), ("12", "Dockerfile"), ("12", ".dockerignore"), ("12", "docker-compose.yml"),
    ("13", ".github/**"), ("14", "maychu/web/giaodien/**"),
)
MAU_15 = [re.compile(m, re.I) for m in (
    r"\bCREATE\s+(UNIQUE\s+|TEMP(ORARY)?\s+|VIRTUAL\s+)?(TABLE|INDEX|TRIGGER|VIEW)\b", r"\bALTER\s+TABLE\b",
    r"\bDROP\s+(TABLE|INDEX|TRIGGER|VIEW)\b", r"PRAGMA\s+user_version\s*=")]
MAU_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import\b|import\s+([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*))")
MAU_NAP_DONG = re.compile(r"\bimportlib\.import_module\s*\(|\b__import__\s*\(")
MAU_BO_QUA = re.compile(r"\b(skip|skipIf|skipUnless|skipTest|expectedFailure|SkipTest)\b")
CO_DAU = re.compile(r"[À-ÃÈ-ÊÌÍÒ-ÕÙÚÝà-ãè-êìíò-õùúýĂăĐđĨĩŨũƠơƯưẠ-ỹ]")
TEN_GOI_KHAC_MODULE = {"pyyaml": "yaml", "python-dateutil": "dateutil", "beautifulsoup4": "bs4", "pillow": "PIL"}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", check=True).stdout


def tep(ref: str, duong: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{duong}"], capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else None


def chan(duong: str) -> str | None:
    for so, mau in CHAN_DUONG_DAN:
        if fnmatch.fnmatchcase(duong, mau) or (mau.endswith("/**") and duong.startswith(mau[:-2])):
            return so
    return None


def dong_doi(goc: str, dau: str, duong: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(dòng thêm ở bản đầu, dòng bớt ở bản gốc), mỗi dòng (số dòng, chữ)."""
    them, bot = [], []
    so_goc = so_dau = 0
    for d in git("diff", "-U0", "--no-color", f"{goc}...{dau}", "--", duong).splitlines():
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", d)
        if m:
            so_goc, so_dau = int(m.group(1)), int(m.group(2))
        elif d.startswith("+") and not d.startswith("+++"):
            them.append((so_dau, d[1:])); so_dau += 1
        elif d.startswith("-") and not d.startswith("---"):
            bot.append((so_goc, d[1:])); so_goc += 1
    return them, bot


def module_cho_phep(goc: str) -> set[str]:
    ds = set(sys.stdlib_module_names) | {"maychu", "kiemthu", "__future__"}
    for d in (tep(goc, "requirements.txt") or "").splitlines():
        ten = re.split(r"[=<>!~\[;\s]", d.strip(), maxsplit=1)[0].lower()
        if ten and not ten.startswith("#"):
            ds.add(TEN_GOI_KHAC_MODULE.get(ten, ten.replace("-", "_")))
    for d in git("grep", "-hE", r"^\s*(import|from)\s+[A-Za-z_]", goc, "--", "*.py").splitlines():   # module đã dùng sẵn trên main
        m = MAU_IMPORT.match(d)
        if m:
            for x in ((m.group(1),) if m.group(1) else re.split(r"\s*,\s*", m.group(2))):
                ds.add(x.split(".")[0])
    return ds


def chuoi_co_dau(nguon: str) -> list[tuple[int, int]]:
    """Khoảng dòng của các chuỗi có chữ tiếng Việt có dấu, trừ chuỗi mô tả (module, lớp, hàm)."""
    cay = ast.parse(nguon)
    mo_ta = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body \
                and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            mo_ta.add(id(n.body[0].value))
    return [(n.lineno, n.end_lineno or n.lineno) for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in mo_ta and CO_DAU.search(n.value)]


def ten_ham_trung(nguon: str) -> list[str]:
    ra = []
    for n in ast.walk(ast.parse(nguon)):
        if isinstance(n, ast.ClassDef):
            ten = [x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
            ra += [f"{n.name}.{t}" for t in sorted({t for t in ten if ten.count(t) > 1})]
    return ra


def muc_thaydoi(chu: str) -> dict[str, dict]:
    ra, cur = {}, None
    for d in chu.splitlines():
        m = re.match(r"^##\s+(\d+\.\d+\.\d+)", d)
        if m:
            cur = ra.setdefault(m.group(1), {"tomtat": None, "nang": None, "dong": 0, "cau": []})
        elif cur is not None and d.strip().startswith("Tóm tắt:"):
            cur["tomtat"] = d.strip()[len("Tóm tắt:"):].strip() or None
        elif cur is not None and d.strip().startswith("Nâng dữ liệu:"):
            cur["nang"] = d.strip()[len("Nâng dữ liệu:"):].strip()
        elif cur is not None and d.strip().startswith("- "):
            cur["dong"] += 1
            cur["cau"].append(d.strip()[2:])
    return ra


def kiem(goc: str, dau: str, nhanh: str, so_bai: dict | None = None) -> list[str]:
    loi = []
    if not nhanh.startswith("sualoi/"):
        loi.append(f"Nhánh: chỉ nhánh sualoi/* được tự gộp (đang là {nhanh})")
    tep_doi = []
    for d in git("diff", "--name-status", "-M", f"{goc}...{dau}").splitlines():
        p = d.split("\t")
        trang, duong = p[0], p[1:]
        tep_doi.append((trang[0], duong[-1]))
        for x in duong:
            so = chan(x)
            if so:
                loi.append(f"Luật {so}: chạm {x}")
        if trang[0] in "ADRC" and not all(x.startswith("kiemthu/") for x in duong):
            loi.append(f"Luật 20: {'thêm' if trang[0] == 'A' else 'xoá' if trang[0] == 'D' else 'đổi tên'} tệp ngoài kiemthu/: {' → '.join(duong)}")
    cho_phep = None
    for trang, duong in tep_doi:
        if trang == "D":
            continue
        them, bot = dong_doi(goc, dau, duong)
        if not duong.startswith("kiemthu/"):
            for so, chu in them:
                if any(m.search(chu) for m in MAU_15):
                    loi.append(f"Luật 15: {duong}:{so} đổi cấu trúc dữ liệu")
        if duong.endswith(".py"):
            for so, chu in them:
                if MAU_NAP_DONG.search(chu):
                    loi.append(f"Luật 16: {duong}:{so} nạp module động")
                m = MAU_IMPORT.match(chu)
                if m:
                    cho_phep = cho_phep if cho_phep is not None else module_cho_phep(goc)
                    for x in ((m.group(1),) if m.group(1) else re.split(r"\s*,\s*", m.group(2))):
                        if x.split(".")[0] not in cho_phep:
                            loi.append(f"Luật 16: {duong}:{so} thư viện ngoài mới {x.split('.')[0]}")
        if duong.startswith("kiemthu/"):
            if trang == "M" and bot:
                loi.append(f"Luật 18: {duong} xoá hoặc sửa {len(bot):02d} dòng của bài kiểm cũ")
            for so, chu in them:
                if MAU_BO_QUA.search(chu):
                    loi.append(f"Luật 18: {duong}:{so} thêm lệnh bỏ qua bài kiểm")
            if duong.endswith(".py"):
                try:
                    for t in ten_ham_trung(tep(dau, duong) or ""):
                        loi.append(f"Luật 18: {duong} trùng tên hàm {t}")
                except SyntaxError:
                    loi.append(f"Luật 18: {duong} không đọc được")
        if duong.startswith("maychu/") and duong.endswith(".py"):
            for ref, dong, nhan in ((dau, them, "thêm"), (goc, bot, "bớt")):
                so_dong = {s for s, _ in dong}
                if not so_dong:
                    continue
                try:
                    khoang = chuoi_co_dau(tep(ref, duong) or "")
                except SyntaxError:
                    loi.append(f"Luật 21: {duong} không đọc được (nghiêng về chặn)")
                    continue
                if any(a <= s <= b for a, b in khoang for s in so_dong):
                    loi.append(f"Luật 21: {duong} {nhan} chữ tiếng Việt người dùng thấy")
    # Luật 17 + số bản + mục THAYDOI
    goc_td, dau_td = muc_thaydoi(tep(goc, "THAYDOI.md") or ""), muc_thaydoi(tep(dau, "THAYDOI.md") or "")
    for ban, m in goc_td.items():
        if ban in dau_td and dau_td[ban]["nang"] != m["nang"]:
            loi.append(f"Luật 17: đổi dòng \"Nâng dữ liệu\" của bản {ban}")
    ban_goc, ban_dau = (tep(goc, "VERSION") or "").strip(), (tep(dau, "VERSION") or "").strip()
    try:
        a, b = [int(x) for x in ban_goc.split(".")], [int(x) for x in ban_dau.split(".")]
        if not (b[:2] == a[:2] and b[2] == a[2] + 1):
            loi.append(f"Số bản: bản sửa lỗi phải là {a[0]}.{a[1]}.{a[2] + 1} (đang là {ban_dau})")
    except (ValueError, IndexError):
        loi.append(f"Số bản: không đọc được VERSION ({ban_goc} → {ban_dau})")
    m = dau_td.get(ban_dau)
    if not m:
        loi.append(f"THAYDOI: thiếu mục ## {ban_dau}")
    else:
        if m["nang"] != "không":
            loi.append(f"Luật 17: mục {ban_dau} phải ghi \"Nâng dữ liệu: không\" (đang: {m['nang'] or 'thiếu'})")
        if not m["tomtat"] or not m["dong"]:
            loi.append(f"THAYDOI: mục {ban_dau} thiếu Tóm tắt hoặc dòng \"- \"")
        for c in m["cau"]:   # QĐ270 (anh "Chọn A"): mỗi dòng "Có gì mới" theo khuôn "Sửa lỗi <mô tả ngắn>"
            if not c.startswith("Sửa lỗi "):
                loi.append(f"THAYDOI: dòng \"- {c[:40]}\" chưa theo khuôn \"Sửa lỗi <mô tả ngắn>\" (QĐ270)")
    if so_bai is not None:
        if so_bai.get("ran_dau") is None or so_bai.get("ran_goc") is None:
            loi.append("Luật 18: không đọc được số bài kiểm của main hoặc của nhánh")
        else:
            if so_bai["ran_dau"] < so_bai["ran_goc"]:
                loi.append(f"Luật 18: số bài chạy {so_bai['ran_dau']} ít hơn main {so_bai['ran_goc']}")
            if so_bai.get("bo_dau", 0) > so_bai.get("bo_goc", 0):
                loi.append(f"Luật 18: số bài bỏ qua {so_bai.get('bo_dau', 0)} nhiều hơn main {so_bai.get('bo_goc', 0)}")
    return loi


def doc_so_bai(chu: str | None) -> tuple[int | None, int]:
    """Từ chú thích CI "Ran N tests in …s OK (skipped=K)". CDA KT-Y44c N2: lấy dòng "Ran" CUỐI (dòng tổng kết thật của
    unittest in sau cùng; bài kiểm in sẵn 01 dòng "Ran …" ở đầu không giả được), số bỏ qua chỉ đọc sau dòng đó."""
    cac = list(re.finditer(r"Ran (\d+) tests?", chu or ""))
    if not cac:
        return None, 0
    k = re.search(r"skipped=(\d+)", (chu or "")[cac[-1].end():])
    return int(cac[-1].group(1)), (int(k.group(1)) if k else 0)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--goc", required=True)
    p.add_argument("--dau", required=True)
    p.add_argument("--nhanh", required=True)
    p.add_argument("--kiem-goc", help='dòng "Ran N tests … OK (skipped=K)" của main ở điểm rẽ nhánh (Y44e N4)')
    p.add_argument("--kiem-dau", help="như trên, của nhánh")
    a = p.parse_args()
    so_bai = None
    if a.kiem_goc is not None or a.kiem_dau is not None:
        rg, bg = doc_so_bai(a.kiem_goc)
        rd, bd = doc_so_bai(a.kiem_dau)
        so_bai = {"ran_goc": rg, "bo_goc": bg, "ran_dau": rd, "bo_dau": bd}
    loi = kiem(a.goc, a.dau, a.nhanh, so_bai)
    for x in loi:
        print(x)
    print(f"KẾT QUẢ: {'CHẶN' if loi else 'ĐẠT'} {len(loi)}")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
