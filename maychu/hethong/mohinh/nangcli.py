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
GIO_KIEM = 3                  # 03:00 mỗi ngày (QĐ271)
_KHOA = threading.Lock()       # 01 lượt nâng / về bản trước tại 01 lúc
_KHOA_TT = threading.Lock()    # CDA P1: đọc – sửa – ghi tệp trạng thái (tạm dừng giữa lúc đang nâng không bị mất)
_DANG = {"goi": None}
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


def _kiem_dang_nhap(goi: str, duong: str, chay=subprocess.run) -> bool:
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
            return r.returncode == 0 and (json.loads((r.stdout or "").strip() or "{}").get("loggedIn") is True
                                          or dg.trang_thai(goi, 1).get("ma_daihan") is True)
        return r.returncode == 0 and "logged in using chatgpt" in dg.MAU_RE.sub("", chu).lower()
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False


def _kiem_goi_ngan(goi: str, duong: str) -> bool:
    """CDA P3 (việc 2, QĐ263): khi tài khoản 01 đã đăng nhập, bản mới trả lời 01 câu rất ngắn qua đúng cách cổng AI gọi.
    Hết hạn mức tức là CLI đã tới được hãng bằng tệp đăng nhập → tính là chạy được. Lỗi khác → chưa đạt."""
    from maychu.hethong.mohinh import congai, dangnhap_goi as dg
    try:
        if not dg.trang_thai(goi, 1).get("da_noi"):
            return True
        (congai._goi_claude if goi == "claude" else congai._goi_chatgpt)(1, CAU_THU, None, cli=duong)
        return True
    except congai.HetHanMuc:
        return True
    except Exception:  # noqa: BLE001 - LoiAI, hết giờ, lỗi chạy: bản mới chưa đạt
        return False


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
    if td and not td.get("xong") and not td.get("loi") and td.get("den") and td.get("den") != capnhat.ban_dang_chay():
        return "dang_cap_nhat"
    if doc_trangthai(thumuc).get("tam_dung"):
        return "tam_dung"
    return None


def dang_nang() -> str | None:
    """Gói đang nâng dở (K1: cập nhật phần mềm chờ)."""
    return _DANG["goi"]


def _f04(lenhcon: str, tom: str, ketqua: str = "dat", nguoi: str | None = None, thumuc: Path | None = None) -> None:
    from maychu.hethong import nhatky
    nhatky.ghi("cli", lenhcon, tom, ketqua=ketqua, nguoi_id=nguoi, thumuc=thumuc)


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
        moi = hoi_npm(goi, client)
        ban = moi["ban"]
        goc_ban = ban_trong_goi(goi, chay)
        dang = max((x for x in (g.get("dang"), goc_ban) if x), key=_khoa_so, default=None)   # CDA P2: bản cao hơn
        _don_ban_cu(goi, tuple(x for x in (g.get("dang"), g.get("truoc")) if x), thumuc)   # P5: bản sót lượt trước
        if _khoa_so(ban) <= _khoa_so(dang):
            return {"kq": "moi_nhat", "ban": dang}
        if ban in (g.get("hong") or []):
            return {"kq": "da_hong", "ban": ban}
        if not ngay:
            try:
                ra = datetime.fromisoformat(str(moi["ra_luc"]).replace("Z", "+00:00"))
            except ValueError:
                return {"kq": "chua_ro_gio_ra", "ban": ban}
            if bay - ra < timedelta(seconds=CHO_GIAY):
                return {"kq": "chua_du_24_gio", "ban": ban, "ra_luc": moi["ra_luc"]}
        goc = thumuc_cli(thumuc)
        goc.mkdir(parents=True, exist_ok=True)
        can = antoan.o_trong(thumuc)["can"] + _uoc_giai_nen(goi, moi["co_giai_nen"])
        if shutil.disk_usage(goc).free < can:   # K1b
            _f04("thieu_o", f"{goi} {ban}: thiếu chỗ trống, cần {can} byte", "bichan", nguoi, thumuc)
            g.update(lan_cuoi=bay.isoformat(timespec="seconds"), ket_qua="thieu_o")
            _sua_goi(goi, g, thumuc)
            return {"kq": "thieu_o", "ban": ban, "can": can}
        dich, dem = goc / goi / ban, goc / ".npm_dem"
        lenh = ["npm", "install", "--prefix", str(dich), "--registry", REGISTRY, "--cache", str(dem),
                "--no-audit", "--no-fund", "--omit=dev"] + (["--ignore-scripts"] if GOI_CLI[goi]["bo_cai_kem"] else []) \
            + [f"{GOI_CLI[goi]['npm']}@{ban}"]
        moi_truong = {**os.environ, "npm_config_userconfig": os.devnull, "npm_config_globalconfig": os.devnull}   # K5
        try:
            r = chay(lenh, capture_output=True, text=True, timeout=900, env=moi_truong)
            cai_dat = r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            cai_dat = False
        finally:
            shutil.rmtree(dem, ignore_errors=True)   # K1c
        dat = cai_dat and ban_cua(str(_bin(goi, ban, thumuc)), chay) == ban \
            and _kiem_dang_nhap(goi, str(_bin(goi, ban, thumuc)), chay) and _kiem_goi_ngan(goi, str(_bin(goi, ban, thumuc)))
        g["lan_cuoi"] = bay.isoformat(timespec="seconds")
        if not dat:
            g["hong"] = sorted(set(g.get("hong") or []) | {ban}, key=_khoa_so)
            g["ket_qua"] = "hong"
            shutil.rmtree(dich, ignore_errors=True)
            _sua_goi(goi, g, thumuc)
            _f04("loi", f"{goi} {ban}: kiểm thử chưa đạt, giữ bản {dang}", "loi", nguoi, thumuc)
            return {"kq": "hong", "ban": ban, "giu": dang}
        cu = g.get("dang")
        g.update(truoc=cu, dang=ban, ket_qua="dat", nang_luc=g["lan_cuoi"])
        _sua_goi(goi, g, thumuc)
        _don_ban_cu(goi, tuple(x for x in (ban, cu) if x), thumuc)
        _f04("nang", f"{goi} {cu or 'trong gói ' + str(dang)} → {ban}", "dat", nguoi, thumuc)
        return {"kq": "dat", "ban": ban, "truoc": cu or dang}
    finally:
        _DANG["goi"] = None
        _KHOA.release()


def ve_ban_truoc(goi: str, thumuc: Path | None = None, nguoi: str | None = None) -> dict:
    """Nút "Về bản trước" (Z20 dòng 11): dùng bản trước (hoặc bản trong gói); bản đang dùng không tự nâng lại."""
    thumuc = thumuc or ketnoi.thumuc_dulieu()
    with _KHOA:
        d = doc_trangthai(thumuc)
        g = _goi_tt(d, goi)
        dang, truoc = g.get("dang"), g.get("truoc")
        if not dang:
            return {"kq": "khong_co"}
        g["hong"] = sorted(set(g.get("hong") or []) | {dang}, key=_khoa_so)
        g.update(dang=truoc if truoc and _bin(goi, truoc, thumuc).exists() else None, truoc=None, ket_qua="ve",
                 lan_cuoi=_bay().isoformat(timespec="seconds"))
        _sua_goi(goi, g, thumuc)
        _f04("ve", f"{goi} {dang} → {g['dang'] or 'trong gói'}", "dat", nguoi, thumuc)
        return {"kq": "ve", "tu": dang, "ve": g["dang"]}


def tam_dung(ban_igm: str, thumuc: Path | None = None) -> None:
    """QĐ264: quay về bản trước của IGM360 → công cụ AI dùng bản trong gói, tự nâng tạm dừng."""
    with _KHOA_TT:
        d = doc_trangthai(thumuc)
        d.update(tam_dung=True, tam_dung_ban=ban_igm)
        ghi_trangthai(d, thumuc)
    _f04("tam_dung", f"quay về bản {ban_igm}: dùng bản trong gói, tự nâng tạm dừng", "dat", None, thumuc)


def mo_lai_neu_len_ban_moi(ban_dang: str, thumuc: Path | None = None) -> None:
    """QĐ264: lên bản IGM360 mới hơn bản đã quay về thì bỏ tạm dừng (gọi lúc khởi động)."""
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
