"""Bài đo giao diện như người dùng chạy trên máy GitHub (0.10.1 P7, QĐ683; điều kiện bảo mật CDA K1–K8).

Dựng máy thử trong thư mục tạm của hệ điều hành (0 dữ liệu thật, 0 ghi /dulieu): tài khoản thử + mật khẩu ngẫu nhiên tạo lúc
chạy; khóa 02 lớp do máy chủ tạo ở lần đăng nhập đầu (bước "bat2lop") – 0 khóa viết sẵn trong kho. Chạy bộ đo chay_do.mjs với
tệp ca ca_giaodien.mjs (trình duyệt có sẵn của máy), chấm ngưỡng từng bài, ghi bảng số đo vào $GITHUB_STEP_SUMMARY (không tải
ảnh lên – K8 cách B). Mã thoát 1 khi có bài không đạt. Không phải tệp test_* (unittest không chạy tệp này).
Cách gọi (từ gốc kho): python kiemthu/giaodien/maythu_ci.py
"""
import http.cookiejar
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
DAY = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
from maychu.hethong.taikhoan import totp  # noqa: E402

CONG = os.environ.get("CONG_DO", "8365")
NODE = shutil.which("node") or "node"
TRINHDUYET = os.environ.get("TRINHDUYET") or shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"

# Các lượt đo (bài, biến môi trường): bộ gọn cho máy GitHub, cùng phép đo với bộ tự kiểm trên máy
LUOT = [
    ("M01", {"BAI": "M01", "KHO": "1440,390"}),
    ("M02", {"BAI": "M02", "KHO": "1440,390"}),
    ("M03", {"BAI": "M03", "KHO": "1440,1024,390"}),
    ("M03", {"BAI": "M03", "KHO": "390", "CHEDO": "toi"}),   # L02-05PX: vạch 01 px chỉ thấy ở Tối
    ("M05", {"BAI": "M05,M05D", "KHO": "1440,1024"}),
    ("M06", {"BAI": "M06", "KHO": "1440", "MAN": "03,08,09"}),
    ("M07", {"BAI": "M07", "KHO": "1440,1024,390"}),
    ("M08", {"BAI": "M08", "KHO": "1440,1280,1024"}),
    ("M10", {"BAI": "M10", "KHO": "1440"}),
    ("M11", {"BAI": "M11", "KHO": "1440,1024"}),
    ("M12", {"BAI": "M12", "KHO": "1440"}),
]


def gan(a, b, sai=0.5):
    return a is not None and b is not None and abs(a - b) <= sai


def cham(bai, d):
    """Trả danh sách lỗi (rỗng = đạt) của 01 ca theo ngưỡng của phiếu dựng mục 5.2."""
    g, kq = d.get("gt") or {}, []
    if d.get("loi"):
        return ["lỗi chạy: " + str(d["loi"])[:120]]
    dt = d["kho"].startswith("390")
    if bai == "M01":
        if g.get("so_de"):
            kq.append(f"đè {g['so_de']}: {g['de'][:2]}")
        if g.get("so_che"):
            kq.append(f"che {g['so_che']}: {g['che'][:2]}")
    elif bai == "M02":
        for i, x in enumerate(g.get("lech") or []):
            if x is not None and x > 0.5:
                kq.append(("thanh trên" if dt and i == 0 else "thanh tab" if dt else "đầu màn" if i == 0 else "cụm nút") + f" lệch {x}")
        if g.get("cum_trong_khung") is False and not dt:
            kq.append("cụm 03 nút ra ngoài khung")
    elif bai == "M03":
        for x in g.get("kq") or []:
            if x.get("ngoai_px"):
                kq.append(f"ô nhập ngoài khung {x['ngoai_px']} px (vị trí {x['vt']})")
        ds = [x for x in g.get("kq") or [] if x.get("mep_tab") is not None]   # 390: SOAT-GD-0101 (02) – hở 4,5 px, nhảy khi cuộn (4c73aa0)
        if dt and (len(ds) != 3 or any(x.get("day_khoi") is None or x["day_khoi"] != x["mep_tab"] for x in ds)   # L02-05PX: khít 0 px
                   or len({x["day_khoi"] for x in ds}) != 1):
            kq.append(f"đáy khối nhập ≠ mép trên thanh tab / đổi khi cuộn: {[(x.get('vt'), x.get('day_khoi'), x.get('mep_tab')) for x in ds]}")
    elif bai == "M05":
        if g.get("so_vuot"):
            kq.append(f"vượt mép {g['so_vuot']}: {g['vuot'][:2]}")
        if g.get("so_cat_khong_cham"):
            kq.append(f"chữ cắt không dấu …: {g['cat_khong_cham'][:2]}")
        if g.get("cuon_ngang"):
            kq.append("trang cuộn ngang")
        if g.get("so_vach_trai"):
            kq.append(f"vạch màu mép trái: {g['vach'][:2]}")
        for n in g.get("nhom") or []:
            if n.get("co") != "13px" or n.get("icon") != [16, 16] or (n.get("stroke_icon") and n["stroke_icon"] != n.get("mau_chu")):
                kq.append(f"nhóm {n.get('ten')}: cỡ {n.get('co')}, icon {n.get('icon')}, nét {n.get('stroke_icon')} / chữ {n.get('mau_chu')}")
    elif bai == "M06":
        for k in ("dau_man", "tc_hang", "logo"):
            if g.get(k) and not gan(g[k]["tam"], 37):
                kq.append(f"{k} tâm {g[k]['tam']} (cần 37)")
        for k in ("muc_tc", "tc_tim"):
            if g.get(k) and not (gan(g[k]["hop"][1], 74) and gan(g[k]["hop"][3], 40)):
                kq.append(f"{k} {g[k]['hop']} (cần 74–114)")
        if g.get("chan") and not gan(g["chan"]["hop"][3], 52):
            kq.append(f"chân cao {g['chan']['hop'][3]} (cần 52)")
        if g.get("chan") and g.get("tc_nhap") and not gan(g["chan"]["hop"][1] + g["chan"]["hop"][3], g["tc_nhap"]["hop"][1] + g["tc_nhap"]["hop"][3]):
            kq.append("đáy chân ≠ đáy ô nhập")
    elif bai == "M07":
        if d["ten"] == "M07_390":
            if g.get("vach_hien") or g.get("dai_hien"):
                kq.append("điện thoại còn vạch kéo / dải thu")
        else:
            tran = min(420, (g.get("tc") or 0) - 8 - 480)
            mong = {"0_macdinh": 260, "1_keo_nho": 240, "2_keo_lon": tran, "3_phim": min(292, tran), "4_bam_dup": 260,
                    "5_nho_tai_lai": min(300, tran), "6_thu": 56, "7_thu_tai_lai": 56, "8_mo_lai": 260, "9_don": 260}
            k = d["ten"].replace("M07_", "")
            if k in mong:
                can = 56 if k in ("6_thu", "7_thu_tai_lai") else max(240, mong[k])
                if g.get("cot") != can:
                    kq.append(f"{k}: cột {g.get('cot')} (cần {can})")
            if k in ("6_thu", "7_thu_tai_lai") and len(g.get("dai_nut") or []) != 3:
                kq.append(f"{k}: dải có {len(g.get('dai_nut') or [])} nút (cần 03)")
    elif bai == "M08":
        if len(set(g.get("top") or [])) > 1 or len(set(g.get("cao") or [])) > 1:
            kq.append(f"03 thẻ lệch: top {g.get('top')}, cao {g.get('cao')}")
        r = g.get("rong") or []
        if r and max(r) - min(r) > 1:
            kq.append(f"03 thẻ khác rộng {r}")
        if not dt:
            nut = [x for x in g.get("nut_chinh") or [] if x]
            if len({x[0] for x in nut}) > 1:
                kq.append(f"nút chính khác đường {nut}")
            hang = [x for x in g.get("hang_nut") or [] if x]
            cp = [x for x in g.get("chi_phi") or [] if x]
            if hang and cp and not gan(max(x[1] for x in hang), cp[0][1], 1):
                kq.append(f"dòng Chi phí {cp[0]} không cùng đáy hàng nút {hang}")
        for x in (g.get("ten") or []) + (g.get("mo_ta") or []):
            if x and x.get("vo_tung_tu"):
                kq.append("chữ vỡ từng từ")
    elif bai == "M10":
        if not (g.get("lech_day", 9) <= 0.5 and g.get("muc_cuoi_tron") is not False and not g.get("trang_troi")):
            kq.append(f"lệch đáy {g.get('lech_day')}, mục cuối trọn {g.get('muc_cuoi_tron')}, trang trôi {g.get('trang_troi')}")
    elif bai == "M11":
        mo, thu = g.get("mo") or {}, g.get("thu") or {}
        if not (mo.get("logo") and gan(mo["logo"]["tam"], 37)):
            kq.append(f"logo {mo.get('logo')}")
        if not (mo.get("ghim") and gan(mo["ghim"]["hop"][1], 74)):
            kq.append(f"ghim {mo.get('ghim')}")
        if not (mo.get("chan") and gan(mo["chan"]["hop"][3], 52)) or mo.get("chu_thu_gon_hien"):
            kq.append(f"chân {mo.get('chan')}, chữ Thu gọn menu hiện {mo.get('chu_thu_gon_hien')}")
        ht = g.get("hien_them") or {}
        if ht and mo.get("he_thong") and ht.get("he_thong") and not gan(mo["he_thong"]["hop"][1], ht["he_thong"]["hop"][1]):
            kq.append("HỆ THỐNG trôi khi mở Hiện thêm")
        if thu.get("nav_rong") != 68 or not (thu.get("ghim") and gan(thu["ghim"]["hop"][1], 74)):
            kq.append(f"thu gọn: rộng {thu.get('nav_rong')}, ghim {thu.get('ghim')}")
        if thu.get("gd") or thu.get("chu_cat"):   # LOI-THU-GDSAU (4c73aa0): thu gọn còn lộ ô Hiện thêm, chữ bị cắt
            kq.append(f"thu gọn: ô Hiện thêm {thu.get('gd')}, chữ cắt {thu.get('chu_cat')}")
        if mo.get("chu_cat"):
            kq.append(f"chữ cắt / tràn thanh trái: {mo.get('chu_cat')}")
    elif bai == "M12":
        if d["ten"] == "M12_thongbao":
            if not g.get("co_chan") or not g.get("cd_chan") or not g.get("chan_trai") or not gan(g["cd_chan"][1], g["chan_trai"][1]):
                kq.append(f"dải chân {g.get('cd_chan')} ≠ chân thanh trái {g.get('chan_trai')}")
        elif g.get("co_chan"):
            kq.append("ngăn không có ghi chú mà có dải")
        for k in ("khoi_menu", "khoi_ct"):
            if g.get(k) and g.get("chan_trai") and not gan(g[k][1] + g[k][3], g["chan_trai"][1] + g["chan_trai"][3]):
                kq.append(f"đáy {k} ≠ đáy chân thanh trái")
    return kq


def gui(mo, duong, du_lieu):
    r = urllib.request.Request(f"http://127.0.0.1:{CONG}/api{duong}", data=json.dumps(du_lieu).encode(),
                               headers={"Content-Type": "application/json", "X-IGM360": "1", "User-Agent": "dogiaodien"})
    with mo.open(r, timeout=30) as t:
        return json.loads(t.read().decode())


def _thoat(t):   # lệnh chú thích của máy GitHub: %, xuống dòng phải mã hóa
    return str(t).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def chu_thich(dong_bang, ca_do):
    """Dòng chú thích lượt chạy (đọc được qua API kho công khai, không cần đăng nhập – DOC-KQ-CONGKHAI).
    Tiêu đề "Do giao dien" – KHÁC "Ket qua bai kiem" (tugop.yml đếm theo tiêu đề đó, CDA K2). Mỗi bài đỏ 01 ::error
    (tối đa 09, máy GitHub nhận tối đa 10 chú thích lỗi mỗi bước) kèm số đo ca đỏ đầu tiên; 01 ::notice tổng kết."""
    dong = []
    for bai, so, dat, loi in [x for x in dong_bang if x[3]][:9]:
        d = next((x for b, x in ca_do if b == bai), None)
        so_do = json.dumps(d.get("gt"), ensure_ascii=False)[:1500] if d else ""
        dong.append(f"::error title=Do giao dien {bai}::{_thoat(f'{dat}/{so} ca đạt; ' + '; '.join(loi[:3]) + (chr(10) + 'Số đo ca đỏ đầu: ' + so_do if so_do else ''))}")
    tong = sum(x[1] for x in dong_bang)
    dat = sum(x[2] for x in dong_bang)
    dong.append(f"::notice title=Do giao dien::{_thoat(f'{dat}/{tong} ca đạt; ' + ', '.join(f'{b} {d}/{n}' for b, n, d, _ in dong_bang))}")
    return dong


def che(gt):   # CDA DOC-CHUTHICH-KQ (đề nghị phụ): đăng ký che giá trị bí mật TRƯỚC mọi lần in – máy GitHub tự thay bằng ***
    if gt and os.environ.get("GITHUB_ACTIONS") == "true":
        print("::add-mask::" + str(gt), flush=True)


def main():
    tam = Path(tempfile.mkdtemp(prefix="maythu-do-"))
    dl, ra = tam / "dulieu", tam / "ketqua"
    dl.mkdir()
    ten, mk = "chu_thu", secrets.token_urlsafe(18)   # tài khoản thử, mật khẩu ngẫu nhiên mỗi lượt
    che(mk)
    moi = dict(os.environ, IGM360_THUMUC_DULIEU=str(dl), IGM360_LICH="tat", IGM360_COOKIE_SECURE="0",
               IGM360_ADMIN_USER=ten, IGM360_ADMIN_PASSWORD=mk)
    mc = subprocess.Popen([sys.executable, "-m", "uvicorn", "maychu.khoidong:app", "--host", "127.0.0.1", "--port", CONG], cwd=GOC, env=moi,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dong_bang, loi_tong, ca_do = [], 0, []
    try:
        for _ in range(240):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{CONG}/api/demso", timeout=2)
                break
            except urllib.error.HTTPError:
                break   # 401 = máy chủ đã lên
            except Exception:
                time.sleep(0.5)
        kho = http.cookiejar.CookieJar()
        mo = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(kho))
        b1 = gui(mo, "/dangnhap", {"ten": ten, "matkhau": mk})
        if b1.get("buoc") in ("bat2lop", "ma2lop"):
            khoa = b1.get("khoa")
            che(khoa)
            if not khoa:
                raise SystemExit("đăng nhập đòi mã 02 lớp nhưng không có khóa vừa tạo")
            gui(mo, "/dangnhap/ma2lop", {"ma_tam": b1["ma_tam"], "ma": totp.ma_cua_buoc(khoa, totp.buoc())})
        phien = next(c.value for c in kho if c.name == "igm360_phien")
        che(phien)
        for bai, bien in LUOT:
            thu_muc = ra / bai
            env = dict(os.environ, CONG=CONG, PHIEN=phien, TRINHDUYET=TRINHDUYET, KHONG_ANH="1", **bien)
            r = subprocess.run([NODE, str(DAY / "chay_do.mjs"), str(DAY / "ca_giaodien.mjs"), str(thu_muc)], env=env, capture_output=True, text=True,
                               encoding="utf-8", timeout=1800)
            tep = thu_muc / "ketqua.json"
            if r.returncode != 0 or not tep.exists():
                dong_bang.append((bai, 0, 0, ["bộ đo không chạy xong: " + (r.stderr or "")[-200:].replace("\n", " ")]))
                loi_tong += 1
                continue
            ca = json.loads(tep.read_text(encoding="utf-8"))
            loi = [f"{d['ten']} {d['kho']} {d['chedo']}: {x}" for d in ca for x in cham(bai, d)]
            ca_do += [(bai, d) for d in ca if cham(bai, d)]
            dong_bang.append((bai, len(ca), len(ca) - len({x.split(':')[0] for x in loi}), loi))
            loi_tong += bool(loi)
    finally:
        mc.terminate()
        try:
            mc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            mc.kill()
        shutil.rmtree(tam, ignore_errors=True)
    bang = ["## Đo giao diện như người dùng (0.10.1, QĐ683)", "", "| Bài | Số ca | Ca đạt | Lỗi (tối đa 03) |", "|---|---|---|---|"]
    for bai, so, dat, loi in dong_bang:
        bang.append(f"| {bai} | {so} | {dat} | {'; '.join(x.replace('|', '/') for x in loi[:3]) or '0'} |")
    bang.append("")
    bang.append("**KẾT LUẬN: " + ("ĐẠT" if not loi_tong else f"CHƯA ĐẠT – {loi_tong} bài có lỗi") + "**")
    noi = "\n".join(bang) + "\n"
    print(noi)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(chr(10).join(chu_thich(dong_bang, ca_do)))
    tom = os.environ.get("GITHUB_STEP_SUMMARY")
    if tom:
        with open(tom, "a", encoding="utf-8") as f:
            f.write(noi)
    return 1 if loi_tong else 0


if __name__ == "__main__":
    sys.exit(main())
