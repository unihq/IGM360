"""Công cụ AI tự nâng mỗi ngày (QĐ263 phương án B lai, PTD-14; QĐ264; QĐ271).

Bản nền nằm trong gói (Dockerfile ghim số bản). Bản nâng cài tại máy vào `/dulieu/cli/<gói>/<bản>/`:
  (1) hỏi npm số bản mới nhất của đúng 02 gói chính chủ (ghi cứng địa chỉ, không đọc `.npmrc` – K5);
  (2) chỉ nhận bản đã ra từ 24 giờ, trừ khi bấm "Nâng công cụ AI" (K2, chữ Z20 dòng 6);
  (3) cài đúng số bản bằng npm (npm tự kiểm sha512), Codex bỏ bước cài kèm, Claude chạy bước cài kèm của gói chính
      (PTD-14 mục 5); bộ nhớ đệm npm trong `/dulieu/cli`, xóa sau mỗi lượt (K1c);
  (4) kiểm thử `--version` đúng số bản; đạt thì đổi con trỏ, giữ 01 bản trước; chưa đạt thì về bản trước, nhớ bản
      hỏng, không thử lại.
Không chạy khi đang cập nhật, ở chế độ an toàn, có cờ quay về, tự nâng tạm dừng (K1); thiếu chỗ trống thì không cài
(K1b). Tệp trạng thái riêng `/dulieu/cli/trangthai.json` (không chung tệp trạng thái cập nhật). Mỗi lần nâng, về, hỏng
ghi 01 dòng F04 (`congcu` = `cli`).
"""
import json
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from maychu.dulieu import ketnoi
from maychu.dulieu.saoluu import MUIGIO_VN

REGISTRY = "https://registry.npmjs.org/"   # K5: ghi cứng, không đọc .npmrc
GOI_CLI = {
    "claude": {"npm": "@anthropic-ai/claude-code", "lenh": "claude", "bo_cai_kem": False},
    "chatgpt": {"npm": "@openai/codex", "lenh": "codex", "bo_cai_kem": True},
}
CHO_GIAY = 24 * 3600          # chỉ nhận bản hãng đã ra từ 24 giờ (QĐ263)
CONG_TAC = "tunang_congcu_ai"  # thông số P01, mặc định bật (QĐ263)
TEN_GOI = {"claude": "Claude · Code", "chatgpt": "ChatGPT · Codex"}   # từ điển thuật ngữ (Z20)
GIO_KIEM = 3                  # 03:00 mỗi ngày (QĐ271)
_KHOA = threading.Lock()       # 01 lượt nâng / về bản trước tại 01 lúc
_KHOA_TT = threading.Lock()    # CDA P1: đọc – sửa – ghi tệp trạng thái (tạm dừng giữa lúc đang nâng không bị mất)
_DANG = {"goi": None, "ban": None, "cu": None, "cu_goi": None}   # lượt đang nâng (Z20 dòng 8)
_LUONG = {"t": None}           # luồng nâng của nút "Nâng công cụ AI" (bài kiểm chờ luồng này)
_LYDO = threading.local()      # LOI-NANGCLI-2: bước trượt + đoạn cuối câu lỗi, vào cột lydo_chan của dòng F04 kế tiếp
# QĐ593 (1): trượt do mạng / hết giờ thì hoãn, thử lại lượt sau; tổng THU_MANG_TOIDA lần trượt mạng của cùng 01 bản thì
# lần cuối mới ghi hỏng. Mã lỗi npm: ETIMEDOUT, ECONNRESET, EAI_AGAIN, HTTP 5xx (npm in "code E503").
THU_MANG_TOIDA = 3
MANG_RE = re.compile(r"\b(ETIMEDOUT|ECONNRESET|EAI_AGAIN|E5\d\d)\b")
# QĐ593 (2): gỡ khỏi danh sách hỏng ĐÚNG 01 lần khi lên bản sửa (bản trượt 26/11/2026 15:17 trước khi có nhật ký bước).
GO_HONG_MOT_LAN = {"claude": ("2.1.332",)}
CAU_THU = "Trả lời đúng 01 chữ: OK"   # P3: lượt gọi ngắn kiểm thử bản mới (gửi cho AI, không hiện trên màn)
SO_BAN_RE = re.compile(r"(\d+\.\d+\.\d+)")


def _khoa_so(b: str | None):
    m = SO_BAN_RE.search(b or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0, 0, 0)


def thumuc_cli(thumuc: Path | None = None) -> Path:
    return (thumuc or ketnoi.thumuc_dulieu()) / "cli"


def doc_trangthai(thumuc: Path | None = None) -> dict:
    p = thumuc_cli(thumuc) / "trangthai.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_trangthai(d: dict, thumuc: Path | None = None) -> None:
    """Ghi nguyên tử: tệp tạm rồi đổi tên 01 lần."""
    goc = thumuc_cli(thumuc)
    goc.mkdir(parents=True, exist_ok=True)
    tam = goc / "trangthai.json.tam"
    tam.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tam, goc / "trangthai.json")


def _sua_goi(goi: str, g: dict, thumuc: Path | None = None) -> None:
    """P1: đọc lại tệp ngay trước khi ghi, chỉ thay phần của 01 gói (giữ cờ tạm dừng do quay về ghi giữa chừng)."""
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        d[goi] = g
        ghi_trangthai(d, thumuc)


def _goi_tt(d: dict, goi: str) -> dict:
    return d.setdefault(goi, {"dang": None, "truoc": None, "hong": [], "lan_cuoi": None, "ket_qua": None})


def _bay() -> datetime:
    return datetime.now(MUIGIO_VN)


def _duoi(chu, n: int = 200) -> str:
    """LOI-NANGCLI-2: n ký tự cuối của câu lỗi, gộp khoảng trắng. Che mã dài hạn TRƯỚC khi cắt (cắt trước có thể để lọt
    nửa mã mà mẫu che không còn nhận ra)."""
    from maychu.hethong.kekhoa.che import che
    return " ".join(che(str(chu or "")).split())[-n:]


def _bin(goi: str, ban: str, thumuc: Path | None = None) -> Path:
    return thumuc_cli(thumuc) / goi / ban / "node_modules" / ".bin" / GOI_CLI[goi]["lenh"]


def ban_cua(duong: str, chay=subprocess.run) -> str | None:
    """Số bản của 01 tệp chạy CLI (`--version`, 0 hạn mức)."""
    try:
        r = chay([duong, "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = SO_BAN_RE.search(r.stdout or "") if r.returncode == 0 else None
    return m.group(1) if m else None


_GOC = {}


def ban_trong_goi(goi: str, chay=subprocess.run) -> str | None:
    """Bản nền trong gói (không đổi trong 01 lần chạy vùng chứa, nhớ lại sau lần hỏi đầu)."""
    if not _GOC.get(goi):   # CDA P4: không nhớ kết quả None (hỏi lại lần sau)
        b = ban_cua(GOI_CLI[goi]["lenh"], chay)
        if b:
            _GOC[goi] = b
        return b
    return _GOC[goi]


def duong_cli(goi: str, thumuc: Path | None = None) -> str | None:
    """Đường tệp chạy bản nâng đang dùng, hoặc None (dùng bản trong gói). K3: bản trong gói cao hơn bản đã nâng thì
    dùng bản trong gói. Tự nâng tạm dừng sau quay về (QĐ264) thì dùng bản trong gói."""
    try:
        d = doc_trangthai(thumuc)
        if d.get("tam_dung"):
            return None
        dang = (d.get(goi) or {}).get("dang")
        if not dang or not _bin(goi, dang, thumuc).exists():
            return None
        goc = ban_trong_goi(goi)
        if goc and _khoa_so(goc) >= _khoa_so(dang):
            return None
        return str(_bin(goi, dang, thumuc))
    except Exception:  # noqa: BLE001 - lỗi đọc con trỏ thì về bản trong gói, không làm hỏng lượt gọi AI
        return None


def _ban_dung(goi: str, g: dict, d: dict | None = None) -> tuple[str | None, bool]:
    """(số bản, là bản trong gói) mà lượt AI mới sẽ dùng – cùng quy tắc `duong_cli` (K3, QĐ264)."""
    goc = ban_trong_goi(goi)
    dang = g.get("dang")
    if dang and not (d or {}).get("tam_dung") and (not goc or _khoa_so(dang) > _khoa_so(goc)):
        return dang, False
    return goc, True


def _sau_giu(ban: str, giu: tuple) -> str:
    """Khóa chuông cli_loi: "<bản hỏng>:<bản giữ>" hoặc "<bản hỏng>:goi:<bản trong gói hoặc trống>" (QĐ307 dòng 15b)."""
    so, trong_goi = giu
    return f"{ban}:goi:{so or ''}" if trong_goi else f"{ban}:{so}"


def ban_cli(goi: str, thumuc: Path | None = None) -> tuple[str | None, str | None]:
    """(bản lượt AI mới dùng, bản dùng trước lần nâng gần nhất) – phần D (QĐ265): so với bản tối thiểu của mô hình.
    Đang dùng bản trong gói thì không có "bản trước"."""
    d = doc_trangthai(thumuc)
    g = d.get(goi) or {}
    so, trong_goi = _ban_dung(goi, g, d)
    return so, None if trong_goi else (g.get("truoc") or ban_trong_goi(goi))


def hoi_npm(goi: str, client=None) -> dict:
    """{ban, ra_luc, co_giai_nen} của bản mới nhất (dist-tags.latest) trên npm."""
    import httpx
    c = client or httpx.Client(timeout=20)
    r = c.get(REGISTRY + quote(GOI_CLI[goi]["npm"], safe="@"), headers={"Accept": "application/json"})
    r.raise_for_status()
    j = r.json()
    ban = j["dist-tags"]["latest"]
    return {"ban": ban, "ra_luc": (j.get("time") or {}).get(ban),
            "co_giai_nen": ((j.get("versions") or {}).get(ban, {}).get("dist") or {}).get("unpackedSize") or 0}


def _thu_muc_byte(p: Path) -> int:
    tong = 0
    for duong, _t, ds in os.walk(p) if p.exists() else []:
        for ten in ds:
            try:
                tong += (Path(duong) / ten).stat(follow_symlinks=False).st_size
            except OSError:
                pass
    return tong


def _uoc_giai_nen(goi: str, co_npm: int) -> int:
    """K1b: cỡ giải nén ước theo dữ kiện có thật: số npm ghi (gói chính) hoặc cỡ bản trong gói đang có trên ổ (gồm gói
    nhị phân theo máy), lấy số lớn hơn."""
    da_cai = 0
    try:
        goc = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, timeout=20).stdout.strip()
        da_cai = _thu_muc_byte(Path(goc) / GOI_CLI[goi]["npm"]) if goc else 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    return max(int(co_npm or 0), da_cai)


def _kiem_dang_nhap(goi: str, duong: str, chay=subprocess.run, ghi: dict | None = None) -> bool:
    """Kiểm thử thêm khi tài khoản 01 đã đăng nhập (PTD-14 mục 5: CLI mới đọc được tệp đăng nhập cũ không): bản mới
    chạy lệnh xem trạng thái đăng nhập (0 hạn mức) với đúng thư mục đăng nhập; phải còn báo đã đăng nhập.
    Chưa đăng nhập thì bỏ qua (chỉ `--version`)."""
    from maychu.hethong.mohinh import dangnhap_goi as dg
    try:
        if not dg.trang_thai(goi, 1, bo_nho=True).get("da_noi"):
            return True
        lenh = ["auth", "status", "--json"] if goi == "claude" else ["login", "status"]
        r = chay([duong, *lenh], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
                 env=dg._env(goi, 1, tao=False))
        chu = (r.stdout or "") + (r.stderr or "")
        if goi == "claude":
            dn = json.loads((r.stdout or "").strip() or "{}").get("loggedIn") if r.returncode == 0 else None
            dat = r.returncode == 0 and (dn is True or dg.trang_thai(goi, 1).get("ma_daihan") is True)
            vet = f"loggedIn={dn}"
        else:
            dat = r.returncode == 0 and "logged in using chatgpt" in dg.MAU_RE.sub("", chu).lower()
            vet = "khong co dong logged in using chatgpt"
        if not dat and ghi is not None:   # LOI-NANGCLI-2: không ghi stdout (có thể có email), chỉ đuôi stderr khi mã thoát khác 0
            ghi["chu"] = f"ma {r.returncode}, {vet}" + (f", {_duoi(r.stderr, 120)}" if r.returncode and r.stderr else "")
        return dat
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        if ghi is not None:
            ghi["chu"] = f"{type(e).__name__}: {_duoi(e, 160)}"
        return False


def _kiem_goi_ngan(goi: str, duong: str, ghi: dict | None = None) -> str:
    """CDA P3 (việc 2, QĐ263): khi tài khoản 01 đã đăng nhập, bản mới trả lời 01 câu rất ngắn qua đúng cách cổng AI gọi.
    Trả "dat" | "hoan" | "loi". QĐ306 (anh chọn B): hết hạn mức thì chưa kiểm được → "hoan" (giữ bản cũ, lượt sau thử
    lại), không tính đạt, không tính hỏng. Lỗi khác → "loi" (chưa đạt)."""
    from maychu.hethong.mohinh import congai, dangnhap_goi as dg
    try:
        if not dg.trang_thai(goi, 1).get("da_noi"):
            return "dat"
        (congai._goi_claude if goi == "claude" else congai._goi_chatgpt)(1, CAU_THU, None, cli=duong)
        if goi == "chatgpt":   # QĐ351, K1a–K1e: thêm 01 lượt app-server thật của bản mới (đường exec ở trên giữ như cũ)
            congai.kiem_app_server(1, CAU_THU, duong)
        return "dat"
    except congai.HetHanMuc:
        return "hoan"
    except Exception as e:  # noqa: BLE001 - LoiAI, hết giờ, lỗi chạy: bản mới chưa đạt
        if ghi is not None:   # LOI-NANGCLI-2
            ghi["chu"] = f"{type(e).__name__}: {_duoi(e)}"
            ghi["mang"] = isinstance(e, subprocess.TimeoutExpired)   # QĐ593: lượt gọi ngắn hết giờ
        return "loi"


def _don_ban_cu(goi: str, giu: tuple, thumuc: Path | None = None) -> None:
    """Giữ đúng bản đang dùng và 01 bản trước. CDA P5: đang có việc AI chạy thì chưa xóa (lượt sau xóa)."""
    from maychu.hethong import capnhat
    goc = thumuc_cli(thumuc) / goi
    if not goc.is_dir() or capnhat.so_viec_ai_dangchay(thumuc) > 0:
        return
    for p in goc.iterdir():
        if p.is_dir() and p.name not in giu:
            shutil.rmtree(p, ignore_errors=True)


def chan_vi(thumuc: Path | None = None) -> str | None:
    """K1: lý do không chạy bộ nâng lúc này (None = được chạy)."""
    from maychu.hethong import antoan, capnhat, tiendo
    if antoan.CHE_DO["an_toan"]:
        return "che_do_an_toan"
    tt = antoan.doc(thumuc)
    if tt.get("chay_ban_truoc"):
        return "co_quay_ve"
    if capnhat.dang_cho():
        return "dang_cap_nhat"
    td = tiendo.doc(thumuc)
    # QĐ386 (LOI-CN-089): chỉ chặn khi lượt cập nhật còn hiệu lực (chưa quá 02 giờ) VÀ bản chạy còn thấp hơn bản yêu cầu
    if td and not td.get("xong") and not td.get("loi") and td.get("den") \
            and not tiendo.da_len(capnhat.ban_dang_chay(), td.get("den")) \
            and (tiendo._giay(td.get("bat_dau"), tiendo._bay()) or 0) <= tiendo.TOI_DA_LUOT_GIAY:
        return "dang_cap_nhat"
    if doc_trangthai(thumuc).get("tam_dung"):
        return "tam_dung"
    return None


def dang_nang() -> str | None:
    """Gói đang nâng dở (K1: cập nhật phần mềm chờ). CDA KT-Y46-4 A1: tính cả luồng nút "Nâng công cụ AI" vừa bấm,
    chưa tới bước khóa (như xem())."""
    if _DANG["goi"]:
        return _DANG["goi"]
    t = _LUONG["t"]
    return _LUONG.get("goi") if t is not None and t.is_alive() else None


def _f04(lenhcon: str, tom: str, ketqua: str = "dat", nguoi: str | None = None, thumuc: Path | None = None) -> None:
    from maychu.hethong import nhatky
    lydo, _LYDO.chu = getattr(_LYDO, "chu", None), None   # LOI-NANGCLI-2: dùng 01 lần, dòng F04 sau không mang theo
    nhatky.ghi("cli", lenhcon, tom, ketqua=ketqua, nguoi_id=nguoi, lydo=lydo, thumuc=thumuc)


def nang(goi: str, thumuc: Path | None = None, ngay: bool = False, nguoi: str | None = None, client=None,
         chay=subprocess.run, bay: datetime | None = None) -> dict:
    """01 lượt nâng 01 gói. `ngay` = bấm "Nâng công cụ AI" (bỏ qua 24 giờ chờ, bỏ qua công tắc). Trả {kq, ...}."""
    from maychu.hethong import antoan
    from maychu.hethong.caidat import thongso
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    if not ngay and not thongso.cong_tac_bat(CONG_TAC, thumuc):
        return {"kq": "tat"}
    ly_do = chan_vi(thumuc)
    if ly_do:
        return {"kq": "khong_chay", "ly_do": ly_do}
    if not _KHOA.acquire(blocking=False):
        return {"kq": "khong_chay", "ly_do": "dang_nang"}
    try:
        _DANG["goi"] = goi
        d = doc_trangthai(thumuc)
        g = _goi_tt(d, goi)
        bay = bay or _bay()
        try:
            moi = hoi_npm(goi, client)
        except Exception as e:
            import httpx
            if isinstance(e, httpx.HTTPError):   # QĐ307 Z20 dòng 19: mở 01 lần, hỏi lại được thì tự đóng
                _bao_khac("mo_mang", thumuc)
            raise
        _bao_khac("dong_mang", thumuc)
        ban = moi["ban"]
        g.update(hang={"ban": ban, "ra_luc": moi["ra_luc"]}, hoi_luc=bay.isoformat(timespec="seconds"))
        _sua_goi(goi, g, thumuc)
        goc_ban = ban_trong_goi(goi, chay)
        dang = max((x for x in (g.get("dang"), goc_ban) if x), key=_khoa_so, default=None)   # CDA P2: bản cao hơn
        _don_ban_cu(goi, tuple(x for x in (g.get("dang"), g.get("truoc")) if x), thumuc)   # P5: bản sót lượt trước
        if _khoa_so(ban) <= _khoa_so(dang):
            _bao_khac("dong_o", thumuc, goi)   # không còn bản để nâng: chuông thiếu ổ của gói này hết đúng
            return {"kq": "moi_nhat", "ban": dang}
        if ban in (g.get("hong") or []):
            return {"kq": "da_hong", "ban": ban}
        g["hang"]["uoc"] = _uoc_giai_nen(goi, moi["co_giai_nen"])   # hộp "Nâng công cụ AI": "tải khoảng …"
        _sua_goi(goi, g, thumuc)
        if not ngay:
            try:
                ra = datetime.fromisoformat(str(moi["ra_luc"]).replace("Z", "+00:00"))
            except ValueError:
                return {"kq": "chua_ro_gio_ra", "ban": ban}
            if bay - ra < timedelta(seconds=CHO_GIAY):
                return {"kq": "chua_du_24_gio", "ban": ban, "ra_luc": moi["ra_luc"]}
        goc = thumuc_cli(thumuc)
        goc.mkdir(parents=True, exist_ok=True)
        can = antoan.o_trong(thumuc)["can"] + g["hang"]["uoc"]
        trong = shutil.disk_usage(goc).free
        if trong < can:   # K1b
            _f04("thieu_o", f"{goi} {ban}: thiếu chỗ trống, cần {can} byte", "bichan", nguoi, thumuc)
            g.update(lan_cuoi=bay.isoformat(timespec="seconds"), ket_qua="thieu_o")
            _sua_goi(goi, g, thumuc)
            _bao_khac("mo_o", thumuc, goi, ban, trong, can)   # QĐ307 Z20 dòng 18
            return {"kq": "thieu_o", "ban": ban, "can": can}
        _bao_khac("dong_o", thumuc, goi)   # ổ đủ thì tự đóng
        _DANG.update(ban=ban, cu=dang, cu_goi=_ban_dung(goi, g)[1])
        dich, dem = goc / goi / ban, goc / ".npm_dem"
        lenh = ["npm", "install", "--prefix", str(dich), "--registry", REGISTRY, "--cache", str(dem),
                "--no-audit", "--no-fund", "--omit=dev"] + (["--ignore-scripts"] if GOI_CLI[goi]["bo_cai_kem"] else []) \
            + [f"{GOI_CLI[goi]['npm']}@{ban}"]
        from maychu.hethong.mohinh import dangnhap_goi as dg
        moi_truong = {**dg.moi_truong_sach(), **{k: v for k, v in os.environ.items() if k.lower().startswith("npm_config_")},
                      "npm_config_userconfig": os.devnull, "npm_config_globalconfig": os.devnull}   # K5; QĐ374 (b) danh sách trắng
        try:
            r = chay(lenh, capture_output=True, text=True, timeout=900, env=moi_truong)
            cai_dat = r.returncode == 0
            ra_npm = f"{getattr(r, 'stderr', '') or ''} {getattr(r, 'stdout', '') or ''}"
            vet = "" if cai_dat else f"ma {r.returncode}: " + _duoi(ra_npm)
            mang = not cai_dat and bool(MANG_RE.search(ra_npm))   # QĐ593
        except subprocess.TimeoutExpired:
            cai_dat, vet, mang = False, "het gio 900 giay", True
        except OSError as e:
            cai_dat, vet, mang = False, f"{type(e).__name__}: {_duoi(e)}", False
        finally:
            shutil.rmtree(dem, ignore_errors=True)   # K1c
        duong_moi = str(_bin(goi, ban, thumuc))
        ct, buoc = {}, None   # LOI-NANGCLI-2: cai_dat | so_ban | dang_nhap | goi_ngan
        if not cai_dat:
            buoc = "cai_dat"
        elif (so := ban_cua(duong_moi, chay)) != ban:
            buoc, vet = "so_ban", f"--version tra {so}, can {ban}"
        elif not _kiem_dang_nhap(goi, duong_moi, chay, ghi=ct):
            buoc, vet = "dang_nhap", ct.get("chu", "")
        thu = _kiem_goi_ngan(goi, duong_moi, ghi=ct) if buoc is None else "loi"
        if thu == "loi" and buoc is None:
            buoc, vet = "goi_ngan", ct.get("chu", "")
        g["lan_cuoi"] = bay.isoformat(timespec="seconds")
        g.pop("hoan_ban", None)
        giu = _ban_dung(goi, g)
        if thu == "hoan":   # QĐ306: không đổi con trỏ, không ghi bản hỏng; lượt sau (03:00 hoặc bấm nút) thử lại
            g.update(ket_qua="hoan", hoan_ban=ban,
                     su_kien={"loai": "hoan", "luc": g["lan_cuoi"], "ban": ban, "giu": giu[0], "giu_goi": giu[1]})
            shutil.rmtree(dich, ignore_errors=True)
            _sua_goi(goi, g, thumuc)
            _f04("hoan", f"{goi} {ban}: hoãn: hết hạn mức, giữ bản {dang}", "bichan", nguoi, thumuc)
            return {"kq": "hoan", "ban": ban, "giu": dang}
        mang = (buoc == "cai_dat" and mang) or (buoc == "goi_ngan" and bool(ct.get("mang")))
        tm = g.pop("thu_mang", None)
        if thu != "dat" and mang:   # QĐ593 (1): đếm theo đúng bản; đổi bản thì đếm lại từ 01
            lan = (tm["lan"] if tm and tm.get("ban") == ban else 0) + 1
            if lan < THU_MANG_TOIDA:   # hoãn: không ghi hỏng, không đổi con trỏ, không chuông; su_kien bỏ để màn Cập nhật
                # hiện dòng "có bản … Tự nâng lúc …" đã duyệt (dòng "hoan" của app.js nói hết hạn mức – không đúng ở đây)
                g.update(ket_qua="hoan_mang", su_kien=None,
                         thu_mang={"ban": ban, "lan": lan, "luc": g["lan_cuoi"], "buoc": buoc})
                shutil.rmtree(dich, ignore_errors=True)
                _sua_goi(goi, g, thumuc)
                _LYDO.chu = f"{buoc}: {vet}"[:300]
                _f04("hoan_mang", f"{goi} {ban}: lan {lan:02d}/{THU_MANG_TOIDA:02d}, giu ban {dang}", "bichan", nguoi, thumuc)
                return {"kq": "hoan_mang", "ban": ban, "giu": dang, "lan": lan}
        if thu != "dat":
            g["hong"] = sorted(set(g.get("hong") or []) | {ban}, key=_khoa_so)
            g["ket_qua"] = "hong"
            g["su_kien"] = {"loai": "hong", "luc": g["lan_cuoi"], "ban": ban, "giu": giu[0], "giu_goi": giu[1], "buoc": buoc}
            shutil.rmtree(dich, ignore_errors=True)
            _sua_goi(goi, g, thumuc)
            _LYDO.chu = f"{buoc}: {vet}"[:300]
            _f04("loi", f"{goi} {ban}: kiểm thử chưa đạt, giữ bản {dang}", "loi", nguoi, thumuc)
            _bao(goi, "cli_loi", _sau_giu(ban, giu), thumuc)
            return {"kq": "hong", "ban": ban, "giu": dang}
        cu = g.get("dang")
        g.update(truoc=cu, dang=ban, ket_qua="dat", nang_luc=g["lan_cuoi"],
                 su_kien={"loai": "dat", "luc": g["lan_cuoi"], "ban": ban})
        _sua_goi(goi, g, thumuc)
        _don_ban_cu(goi, tuple(x for x in (ban, cu) if x), thumuc)
        _f04("nang", f"{goi} {cu or 'trong gói ' + str(dang)} → {ban}", "dat", nguoi, thumuc)
        _bao(goi, "cli_nang", ban, thumuc)
        return {"kq": "dat", "ban": ban, "truoc": cu or dang}
    finally:
        _DANG.update(goi=None, ban=None, cu=None, cu_goi=None)
        _KHOA.release()


def _bao(goi: str, loai: str, sau: str, thumuc: Path | None = None) -> None:
    """Chuông Z20 dòng 14 (nâng xong) và 15 (Công cụ AI lỗi, vàng – QĐ271). Lỗi chuông không làm hỏng lượt nâng."""
    try:
        from maychu.hethong.giamsat import thongbao
        thongbao.bao_cli(goi, loai, sau, thumuc)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("chuông công cụ AI lỗi")


def _bao_khac(viec: str, thumuc: Path | None = None, *doi) -> None:
    """Chuông Z20 dòng 18 (thiếu ổ trống) và 19 (không kết nối được máy chủ của hãng), QĐ307. Lỗi chuông không làm
    hỏng lượt nâng."""
    try:
        from maychu.hethong.giamsat import thongbao
        if viec == "mo_o":
            thongbao.bao_cli_o(*doi, thumuc=thumuc)
        elif viec == "dong_o":
            thongbao.dong_cli(f"cli_o:{doi[0]}:", "Ổ trống đủ hoặc không còn bản để nâng", thumuc)
        elif viec == "mo_mang":
            thongbao.bao_cli_mang(thumuc)
        elif viec == "dong_mang":
            thongbao.dong_cli("cli_mang", "Đã hỏi lại được máy chủ của hãng", thumuc)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("chuông công cụ AI lỗi")


def da_kiem_hom_nay(bay: datetime | None = None, thumuc: Path | None = None) -> bool:
    return doc_trangthai(thumuc).get("kiem_ngay") == (bay or _bay()).strftime("%Y-%m-%d")


def luot_hang_ngay(thumuc: Path | None = None, bay: datetime | None = None) -> dict:
    """QĐ271: tự kiểm bản mới 03:00 mỗi ngày (lịch gọi khi đã qua 03:00 mà hôm nay chưa kiểm, nên máy tắt lúc 03:00 thì
    kiểm khi bật lại). Ghi ngày kiểm trước (01 lần/ngày dù lỗi mạng). Lỗi 01 gói không dừng gói kia."""
    bay = bay or _bay()
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        d["kiem_ngay"] = bay.strftime("%Y-%m-%d")
        ghi_trangthai(d, thumuc)
    ra = {}
    for goi in GOI_CLI:
        try:
            ra[goi] = nang(goi, thumuc, bay=bay)
        except Exception as e:  # noqa: BLE001 - mất mạng, npm lỗi: ghi F04, mai thử lại
            ra[goi] = {"kq": "loi", "loi": type(e).__name__}
            _f04("hoi_loi", f"{goi}: không hỏi được bản mới ({type(e).__name__})", "loi", None, thumuc)
    return ra


def ve_ban_truoc(goi: str, thumuc: Path | None = None, nguoi: str | None = None) -> dict:
    """Nút "Về bản trước" (Z20 dòng 11): dùng bản trước (hoặc bản trong gói); bản đang dùng không tự nâng lại."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    ly_do = chan_vi(thumuc)   # CDA KT-Y46-4 A2 (QĐ218 dòng 37: chế độ an toàn chặn việc ghi khác Cập nhật), K1
    if ly_do and ly_do != "tam_dung":   # tạm dừng: không có bản nâng để về (trả khong_co như cũ)
        return {"kq": "khong_chay", "ly_do": ly_do}
    if not _KHOA.acquire(blocking=False):   # đang nâng: không chờ (nút đã ẩn trong lúc nâng)
        return {"kq": "khong_chay", "ly_do": "dang_nang"}
    try:
        d = doc_trangthai(thumuc)
        g = _goi_tt(d, goi)
        dang, truoc = g.get("dang"), g.get("truoc")
        if not dang or d.get("tam_dung"):
            return {"kq": "khong_co"}
        g["hong"] = sorted(set(g.get("hong") or []) | {dang}, key=_khoa_so)
        g["ve_tay"] = sorted(set(g.get("ve_tay") or []) | {dang}, key=_khoa_so)   # ô bản mới: "không tự nâng lại"
        g.update(dang=truoc if truoc and _bin(goi, truoc, thumuc).exists() else None, truoc=None, ket_qua="ve",
                 lan_cuoi=_bay().isoformat(timespec="seconds"))
        giu = _ban_dung(goi, g, d)
        g["su_kien"] = {"loai": "ve", "luc": g["lan_cuoi"], "ban": dang, "giu": giu[0], "giu_goi": giu[1]}
        _sua_goi(goi, g, thumuc)
        _f04("ve", f"{goi} {dang} → {g['dang'] or 'trong gói'}", "dat", nguoi, thumuc)
        return {"kq": "ve", "tu": dang, "ve": g["dang"]}
    finally:
        _KHOA.release()


def nang_nen(goi: str, thumuc: Path | None = None, nguoi: str | None = None) -> dict:
    """Nút "Nâng công cụ AI" (Z20 dòng 7, K2): chạy lượt nâng ở luồng riêng (npm tải lâu), trả ngay. Bị chặn thì trả
    {"loi": lý do} và không chạy."""
    ly_do = chan_vi(thumuc) or ("dang_nang" if _DANG["goi"] or (_LUONG["t"] and _LUONG["t"].is_alive()) else None)
    if ly_do:
        return {"loi": ly_do}

    def chay():
        try:
            nang(goi, thumuc, ngay=True, nguoi=nguoi)
        except Exception as e:  # noqa: BLE001 - mất mạng, npm lỗi: ghi F04 (chuông dòng 19 đã mở nếu lỗi mạng)
            _f04("hoi_loi", f"{goi}: không hỏi được bản mới ({type(e).__name__})", "loi", nguoi, thumuc)
    _LUONG.update(t=threading.Thread(target=chay, name="nang_congcu_ai", daemon=True), goi=goi)
    _LUONG["t"].start()
    return {"bat_dau": True, "goi": goi}


def xem(thumuc: Path | None = None) -> dict:
    """Dữ liệu khối "Công cụ AI" ở màn Cập nhật (Z20). Chữ do giao diện ghép (app.js, khối CA)."""
    from maychu.hethong import antoan
    from maychu.hethong.caidat import thongso
    d = doc_trangthai(thumuc)
    dang = dict(_DANG) if _DANG["goi"] else None
    if not dang and _LUONG["t"] and _LUONG["t"].is_alive():   # nút vừa bấm, luồng nâng chưa tới bước khóa
        dang = {"goi": _LUONG.get("goi"), "ban": None, "cu": None, "cu_goi": None}
    ra = {"bat": thongso.cong_tac_bat(CONG_TAC, thumuc), "tam_dung": bool(d.get("tam_dung")),
          "tam_dung_ban": d.get("tam_dung_ban"), "kiem_ngay": d.get("kiem_ngay"), "gio_kiem": GIO_KIEM,
          "cho_gio": CHO_GIAY // 3600, "chan": chan_vi(thumuc), "dang_nang": dang, "goi": []}
    if ra["chan"] == "dang_cap_nhat":   # QĐ308 điểm 10: "Đang cập nhật lên <bản>"
        from maychu.hethong import tiendo
        ra["cap_nhat_len"] = (tiendo.doc(thumuc) or {}).get("den")
    for goi in GOI_CLI:
        g = d.get(goi) or {}
        so, trong_goi = _ban_dung(goi, g, d)
        hang = dict(g.get("hang") or {}) or None
        if hang and hang.get("uoc"):
            hang["uoc_chu"] = antoan.chu_dungluong(hang["uoc"])
        ra["goi"].append({"goi": goi, "ten": TEN_GOI[goi], "ban": so, "trong_goi": trong_goi, "ban_goi": ban_trong_goi(goi),
                          "truoc": None if trong_goi else g.get("truoc"), "truoc_goi": not trong_goi and not g.get("truoc"),
                          "hang": hang, "hong": g.get("hong") or [],
                          "ve_tay": g.get("ve_tay") or [], "nang_luc": g.get("nang_luc"), "lan_cuoi": g.get("lan_cuoi"),
                          "su_kien": g.get("su_kien")})
    return ra


def tam_dung(ban_igm: str, thumuc: Path | None = None) -> None:
    """QĐ264: quay về bản trước của IGM360 → công cụ AI dùng bản trong gói, tự nâng tạm dừng."""
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        d.update(tam_dung=True, tam_dung_ban=ban_igm)
        ghi_trangthai(d, thumuc)
    _f04("tam_dung", f"quay về bản {ban_igm}: dùng bản trong gói, tự nâng tạm dừng", "dat", None, thumuc)


def go_hong_mot_lan(thumuc: Path | None = None) -> list:
    """QĐ593 (2): gỡ các bản trong GO_HONG_MOT_LAN khỏi danh sách hỏng ĐÚNG 01 lần (đánh dấu `da_go_hong`); chỉ gỡ đúng bản
    đó, không xóa cả danh sách. Sự kiện hỏng của chính bản đó bỏ đi để màn Cập nhật hiện lại dòng "có bản …". Trả các bản đã gỡ."""
    go = []
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        doi = False
        for goi, ds in GO_HONG_MOT_LAN.items():
            g = d.get(goi)
            if not isinstance(g, dict):
                continue
            da = g.setdefault("da_go_hong", [])
            for ban in ds:
                if ban in da:
                    continue
                da.append(ban)
                doi = True
                if ban in (g.get("hong") or []):
                    g["hong"] = [x for x in g["hong"] if x != ban]
                    sk = g.get("su_kien") or {}
                    if sk.get("loai") == "hong" and sk.get("ban") == ban:
                        g["su_kien"] = None
                    go.append((goi, ban))
        if doi:
            ghi_trangthai(d, thumuc)
    for goi, ban in go:
        _f04("go_hong", f"{goi} {ban}: QĐ593", "dat", None, thumuc)
    return go


def mo_lai_neu_len_ban_moi(ban_dang: str, thumuc: Path | None = None) -> None:
    """QĐ264: lên bản IGM360 mới hơn bản đã quay về thì bỏ tạm dừng (gọi lúc khởi động). QĐ593 (2): trước đó gỡ 01 lần
    bản hỏng trong GO_HONG_MOT_LAN (lỗi gỡ không chặn phần QĐ264)."""
    try:
        go_hong_mot_lan(thumuc)
    except Exception:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("go_hong_mot_lan")
    d = doc_trangthai(thumuc)
    if d.get("tam_dung") and _khoa_so(ban_dang) > _khoa_so(d.get("tam_dung_ban")):
        mo_lai(thumuc, f"lên bản {ban_dang}")


def mo_lai(thumuc: Path | None = None, ly_do: str = "bat_lai") -> None:
    """Bỏ tạm dừng: anh gạt công tắc bật lại, hoặc lên bản IGM360 mới (QĐ264)."""
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        if not d.get("tam_dung"):
            return
        d.update(tam_dung=False, tam_dung_ban=None)
        ghi_trangthai(d, thumuc)
    _f04("mo_lai", ly_do, "dat", None, thumuc)
