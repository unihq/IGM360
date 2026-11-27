"""Lệnh đo máy, chạy trong máy và in số ra cửa sổ lệnh (không mở ra ngoài mạng).

Cách chạy trên VPS:
    docker compose exec igm360 python -m maychu.hethong.giamsat.domay
Thêm --json để in dạng máy đọc.

Số của cả máy lấy từ hệ điều hành; số của riêng container IGM360 lấy từ cgroup v2.
"""
import json
import os
import sys
from pathlib import Path

import psutil

from maychu.dulieu import muigio

MB = 1024 * 1024
CGROUP = Path("/sys/fs/cgroup")
TEN_TIENTRINH_AI = ("claude", "codex")
NGUONG_SWAP_MB = 100  # dùng tệp hoán đổi quá mức này thì ghi 01 cảnh báo (kế hoạch GĐ 1 Phần 5, QĐ87)


def _doc_so(tep: Path):
    """Đọc 01 số từ tệp cgroup. Tệp không có thì trả None; tệp ghi 'max' (không đặt trần) thì trả 'max'."""
    try:
        giatri = tep.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if giatri == "max":
        return "max"
    return int(giatri) if giatri.isdigit() else None


def _dem_oom(tep: Path):
    """Số lần hệ điều hành tắt tiến trình trong container vì hết RAM."""
    try:
        for dong in tep.read_text(encoding="utf-8").splitlines():
            ten, _, so = dong.partition(" ")
            if ten == "oom_kill":
                return int(so)
    except (OSError, ValueError):
        return None
    return None


def _dem_tientrinh_ai() -> int:
    dem = 0
    for tt in psutil.process_iter(["name", "cmdline"]):
        try:
            ten = (tt.info.get("name") or "").lower()
            lenh = " ".join(tt.info.get("cmdline") or []).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if any(t == ten or f"/{t} " in f"{lenh} " or lenh.startswith(f"{t} ") for t in TEN_TIENTRINH_AI):
            dem += 1
    return dem


def do_may(thumuc_dulieu: str | None = None) -> dict:
    """Đo 01 lần, trả về các số (MB, %)."""
    thumuc = thumuc_dulieu or os.environ.get("IGM360_THUMUC_DULIEU", "/")
    if not os.path.isdir(thumuc):
        thumuc = "/"
    ram = psutil.virtual_memory()
    hoandoi = psutil.swap_memory()
    o = psutil.disk_usage(thumuc)
    tai = os.getloadavg()
    return {
        "luc": muigio.bay_chon().strftime("%d/%m/%Y %H:%M:%S"),   # ③ QĐ636
        "may_ram_tong_mb": ram.total // MB,
        "may_ram_dung_mb": (ram.total - ram.available) // MB,
        "may_ram_con_mb": ram.available // MB,
        "may_ram_con_tyle": round(ram.available * 100 / ram.total, 1),
        "may_hoandoi_tong_mb": hoandoi.total // MB,
        "may_hoandoi_dung_mb": hoandoi.used // MB,
        "may_cpu_soloi": psutil.cpu_count(),
        "may_tai_1_5_15": [round(x, 2) for x in tai],
        "ocung_thumuc": thumuc,
        "ocung_tong_mb": o.total // MB,
        "ocung_dung_tyle": round(o.percent, 1),
        "container_ram_dung_mb": _mb(_doc_so(CGROUP / "memory.current")),
        "container_ram_caonhat_mb": _mb(_doc_so(CGROUP / "memory.peak")),
        "container_ram_tran_mb": _mb(_doc_so(CGROUP / "memory.max")),
        "container_bi_tat_vi_het_ram": _dem_oom(CGROUP / "memory.events"),
        "so_tientrinh_ai": _dem_tientrinh_ai(),
    }


def _mb(so):
    return so if so in (None, "max") else so // MB


def _so(x) -> str:
    """Số kiểu Việt Nam: chấm ngăn nghìn, phẩy thập phân, bỏ số 0 thừa."""
    if x is None:
        return "không đo được"
    if isinstance(x, float):
        nguyen, _, le = f"{x:.1f}".partition(".")
        nguyen = f"{int(nguyen):,}".replace(",", ".")
        return nguyen if le == "0" else f"{nguyen},{le}"
    return f"{x:,}".replace(",", ".")


def _mb_chu(x) -> str:
    if x == "max":
        return "không đặt"
    return _so(x) if x is None else f"{_so(x)} MB"


def in_chu(s: dict) -> str:
    dong = [
        f"IGM360 - đo máy lúc {s['luc']} (giờ Việt Nam)",
        "CẢ MÁY",
        f"  RAM tổng: {_so(s['may_ram_tong_mb'])} MB; đang dùng: {_so(s['may_ram_dung_mb'])} MB; "
        f"còn dùng được: {_so(s['may_ram_con_mb'])} MB ({_so(s['may_ram_con_tyle'])}%)",
        f"  Tệp hoán đổi: {_so(s['may_hoandoi_tong_mb'])} MB; đang dùng: {_so(s['may_hoandoi_dung_mb'])} MB",
        f"  CPU: {_so(s['may_cpu_soloi'])} lõi; tải 1, 5, 15 phút: "
        + ", ".join(_so(float(x)) for x in s["may_tai_1_5_15"]),
        f"  Ổ cứng ({s['ocung_thumuc']}): tổng {_so(s['ocung_tong_mb'])} MB; đã dùng {_so(s['ocung_dung_tyle'])}%",
        "RIÊNG CONTAINER IGM360",
        f"  RAM đang dùng: {_mb_chu(s['container_ram_dung_mb'])}; cao nhất từ lúc chạy: {_mb_chu(s['container_ram_caonhat_mb'])}; "
        f"trần: {_mb_chu(s['container_ram_tran_mb'])}",
        f"  Số lần bị tắt vì hết RAM: {_so(s['container_bi_tat_vi_het_ram'])}",
        f"  Số tiến trình AI đang chạy: {_so(s['so_tientrinh_ai'])}",
    ]
    return "\n".join(dong)


def ghi_n02(thumuc=None) -> dict:
    """Đo 01 lần và ghi 01 dòng N02 (lịch chạy mỗi giờ). Tỷ lệ lưu dạng % × 100, RAM lưu MB."""
    from maychu.dulieu import ketnoi, maso
    import time
    s = do_may(str(thumuc) if thumuc else None)
    viec = ketnoi.mo("Viecnen", thumuc)
    try:
        so_viec = viec.execute("SELECT count(*) FROM viecnen WHERE trangthai = 'dangchay'").fetchone()[0]
        so_viec_ai = viec.execute(
            "SELECT count(*) FROM viecnen WHERE trangthai = 'dangchay' AND goi_ai = 1").fetchone()[0]
    finally:
        viec.close()
    chinh = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        bd = time.perf_counter()
        chinh.execute("BEGIN IMMEDIATE")
        cho_ms = int((time.perf_counter() - bd) * 1000)
        chinh.execute("ROLLBACK")
    finally:
        chinh.close()
    dong = {
        "id": maso.tao(), "luc": muigio.gio_luu(),
        "tyle_ocung": int(round(s["ocung_dung_tyle"] * 100)), "ram_dung": s["may_ram_dung_mb"],
        "so_viec_dangchay": so_viec, "so_viec_ai_dangchay": so_viec_ai, "thoigian_cho_ghi_ms": cho_ms,
        "swap_dung": s["may_hoandoi_dung_mb"],
    }
    nk = ketnoi.mo("Nhatky", thumuc)
    try:
        nk.execute("BEGIN IMMEDIATE")
        nk.execute(f"INSERT INTO theodoi_maychu ({', '.join(dong)}) VALUES ({', '.join('?' * len(dong))})",
                   list(dong.values()))
        nk.execute("COMMIT")
    finally:
        nk.close()
    if dong["swap_dung"] > NGUONG_SWAP_MB:
        _canhbao_swap(dong, thumuc)
    return dong


def _canhbao_swap(dong: dict, thumuc=None) -> None:
    """Ghi 01 cảnh báo D03 loại sự kiện; còn cảnh báo cùng loại đang mở thì không ghi thêm (không báo lặp)."""
    from maychu.dulieu import ketnoi, maso
    khoa = "swap_vuot_nguong"
    cn = ketnoi.mo("Dulieu_Chinh", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        con_mo = cn.execute("SELECT 1 FROM canhbao WHERE khoa_chongtrung = ? AND trangthai IN ('moi', 'dabao', 'dagiao_task')",
                            (khoa,)).fetchone()
        if not con_mo:
            cn.execute("INSERT INTO canhbao (id, loai, nguong, giatri, chieu, bang_nguon, dong_nguon_id, khoa_chongtrung, trangthai, tao_luc)"
                       " VALUES (?, 'sukien', ?, ?, 'tren', 'theodoi_maychu', ?, ?, 'moi', ?)",
                       (maso.tao(), NGUONG_SWAP_MB, dong["swap_dung"], dong["id"], khoa, dong["luc"]))
        cn.execute("COMMIT")
    finally:
        cn.close()


def main(thamso=None) -> int:
    thamso = sys.argv[1:] if thamso is None else thamso
    s = do_may()
    print(json.dumps(s, ensure_ascii=False) if "--json" in thamso else in_chu(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
