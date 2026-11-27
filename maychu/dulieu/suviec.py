"""T01 Sổ sự việc `bn_suviec` (bản 5; QĐ96, QĐ632; thiết kế mục 1.4).

Sổ chỉ ghi thêm. Ngoại lệ duy nhất (QĐ632): 02 cột `trangthai_xuly`, `xuly_luc` đổi 01 chiều `moi` → `dahoc` hoặc
`boqua` (02 trạng thái cuối, không đổi qua lại). Chặn 02 tầng (QA L14, CDA phiếu 16 mục 9.40): máy chủ chỉ có 01 hàm
ghi, 01 hàm đổi trạng thái; trong tệp có 02 trigger dưới đây làm lưới an toàn. Không chặn xóa dòng (chưa có QĐ xóa
dòng T01). Hàm ghi dùng `INSERT … ON CONFLICT(khoa_chongtrung) DO NOTHING`; cấm `OR REPLACE` với T01 (thay dòng sẽ đi
vòng trigger sửa). Bảng dựng lại thì mất trigger nên `tao_trigger` chạy lại sau mỗi lần tạo, nâng (chạy lại không sao).
"""
import sqlite3

BANG = "bn_suviec"
# 20 cột sự thật (cột 1–20 thiết kế mục 1.4): chỉ ghi thêm, không sửa.
COT_SUTHAT = ("id", "luc", "loai", "nguon_loai", "bang_nguon", "dong_nguon_id", "khoa_chongtrung", "bonao", "doituong",
              "nguoi_id", "co_dlcn", "shop_id", "kenh_id", "nhatky_ai_id", "lydo_ma", "lydo_chu", "so_lan_sua",
              "trithuc_ma", "danhgia", "moc_json")
TRANGTHAI_CUOI = ("dahoc", "boqua")


def tao_trigger(cn: sqlite3.Connection) -> None:
    """02 trigger T01 (QĐ632, L14). `IS NOT 'moi'` để dòng có trạng thái trống cũng bị chặn (CDA L14 sửa 1).
    Tệp chưa có T01 (tệp bản cũ đang chờ nâng, bài kiểm dựng bản cũ): bỏ qua, như `phienban.tao_trigger` chỉ chạy
    trên bảng đang có."""
    if not cn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (BANG,)).fetchone():
        return
    cn.execute(f"CREATE TRIGGER IF NOT EXISTS sv__suthat BEFORE UPDATE OF {', '.join(COT_SUTHAT)} ON {BANG}"
               " BEGIN SELECT RAISE(ABORT, 'bn_suviec: phần sự thật chỉ ghi thêm, không sửa (QĐ96, QĐ632)'); END")
    cuoi = ", ".join(f"'{g}'" for g in TRANGTHAI_CUOI)
    cn.execute(f"CREATE TRIGGER IF NOT EXISTS sv__xuly BEFORE UPDATE OF trangthai_xuly, xuly_luc ON {BANG}"
               f" WHEN OLD.trangthai_xuly IS NOT 'moi' OR NEW.trangthai_xuly NOT IN ({cuoi}) OR NEW.xuly_luc IS NULL"
               " BEGIN SELECT RAISE(ABORT, 'bn_suviec: trạng thái xử lý chỉ đi 01 chiều moi → dahoc / boqua (QĐ632)'); END")
