"""Giá trị "ai bấm" cho 54 cột người thao tác (thiết kế mục 0.4, 0.7; QĐ108).

Chỉ nhận `id` tài khoản F01 (mã dòng ULID 26 ký tự) hoặc 01 trong 04 mã máy cố định. Không ghi chữ `anh`,
không ghi tên đăng nhập: F01 nối 01-01 với A18 nên vẫn tra ra người. Mọi chỗ ghi cột "ai bấm" gọi `kiem`.
"""
import re
from pathlib import Path

MA_MAY = ("hethong", "bot", "viecnen", "ai")
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
# Tên cột "ai bấm" (thiết kế mục 0.4). `nguoi_id` chỉ là cột "ai bấm" ở F04; các bảng khác `nguoi_id` trỏ A18.
TEN_COT = ("nguoi_khai", "nguoi_duyet", "nguoi_tao", "nguoi_nhap", "nguoi_dat", "nguoi_chot", "nguoi_xuat",
           "nguoi_ketluan", "nguoi_ghi", "nguoi_xuly", "nguoi_gui")
_LUOCDO = Path(__file__).resolve().parent / "luocdo"
# Giá trị cũ bản 0.5.0 trở về trước, đổi khi nâng lên lược đồ bản 3 (thiết kế mục 0.7): 'anh' và tên đăng nhập
# của chủ → `id` tài khoản chủ; 'lenh_vps' (lệnh đặt lại mật khẩu) → 'hethong'. Giá trị lạ khác: dừng nâng.
DOI_CU_MAY = {"lenh_vps": "hethong"}


def cac_cot(ten_file: str) -> list[tuple[str, str]]:
    """[(bảng, cột)] "ai bấm" của 01 file, đọc từ lược đồ hiện hành."""
    sql = (_LUOCDO / f"{ten_file}.sql").read_text(encoding="utf-8")
    ra = []
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\n\);", sql, re.S):
        for cot in re.findall(r"^\s+(\w+) ", m.group(2), re.M):
            if cot in TEN_COT or (cot == "nguoi_id" and m.group(1) == "nhatky_thaotac"):
                ra.append((m.group(1), cot))
    return ra


def bang_doi_cu(chu: tuple | None) -> dict[str, str]:
    """{giá trị cũ: giá trị mới}. `chu` = (id, ma, ten) tài khoản chủ ở F01, hoặc None khi chưa có tài khoản."""
    doi = dict(DOI_CU_MAY)
    if chu:
        for k in ("anh", chu[1], chu[2]):
            if k and k not in MA_MAY and not _ULID.match(k):
                doi[k] = chu[0]
    return doi


def la_hop_le(giatri) -> bool:
    return isinstance(giatri, str) and (giatri in MA_MAY or bool(_ULID.match(giatri)))


def kiem(giatri) -> str:
    """Trả lại giá trị nếu hợp lệ; sai thì ValueError (không ghi im lặng giá trị lạ)."""
    if not la_hop_le(giatri):
        raise ValueError(f"giá trị 'ai bấm' phải là mã tài khoản hoặc 01 trong {', '.join(MA_MAY)}")
    return giatri
