"""F35 Trò chuyện (ngày 06): anh hỏi, Cổng AI trả lời; lưu H07 cuộc trò chuyện, H08 từng tin (chỉ ghi thêm).

Mỗi lượt gửi kèm các tin trước của cùng cuộc trò chuyện (tối đa khoảng 24.000 chữ gần nhất). Tin AI ghi
`nhatky_ai_id` (G04) để truy được nguồn AI, tiền. Không có nguồn AI dùng được thì ghi 01 tin hệ thống nêu lý do.

N0 (QĐ344, QĐ347, QĐ350; kế hoạch Kehoach_Luot_Chaynen mục 2, 8): `bat_luot` ghi tin hỏi rồi trả ngay, lượt chạy nền
(`luot.py`, 01 dòng G02); `gui` (đường đồng bộ cũ, không người nghe) mở lượt rồi chờ xong, trả như trước.
Tin trả lời ghi `trangthai` (`xong`, `dung`) và `tra_loi_cho` = mã tin hỏi; tin hệ thống lỗi cũng ghi `tra_loi_cho` (C1).
"""
import json
import threading
from datetime import datetime

from maychu.dulieu import ketnoi, maso, timchu
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.mohinh import congai, luot

GIU_CHU = 24_000
VAI_CHU = {"nguoi": "Bạn", "ai": "Trợ lý"}   # QĐ221: lời gửi AI xưng "bạn"


class ChoCapNhat(Exception):
    """QĐ347 H1: phần mềm đang chờ cập nhật – không mở lượt, không ghi tin; câu báo `luot.CHU_CHO_CAPNHAT` (QĐ352)."""


def _bay_gio() -> str:
    return datetime.now(MUIGIO_VN).isoformat(timespec="seconds")


def _ghi_tin(cn, hoithoai_id: str, vai: str, noidung: str, nhatky_ai_id=None, *, ma: str | None = None,
             trangthai: str | None = None, tra_loi_cho: str | None = None, phu: dict | None = None) -> dict:
    """Hàm ghi H08 duy nhất (thiết kế 0.8 Q5). Y40b L1: tin + bảng nối + bảng ảo + `cap_nhat_luc` trong 01 giao dịch; người gọi
    chưa mở giao dịch thì hàm tự mở `BEGIN IMMEDIATE`, lỗi ở bước nào thì `ROLLBACK` (không còn tin thiếu chỉ mục).
    N0: `ma` (mã tin định sẵn, để G02 ghi trước tin hỏi), `trangthai`, `tra_loi_cho`, `phu` (H08 `phu_json`, QĐ350)."""
    t = {"id": ma or maso.tao(), "hoithoai_id": hoithoai_id, "vai": vai, "noidung": noidung, "nhatky_ai_id": nhatky_ai_id,
         "luc": _bay_gio(), "trangthai": trangthai, "tra_loi_cho": tra_loi_cho, "phu": phu}
    tu_mo = not cn.in_transaction
    if tu_mo:
        cn.execute("BEGIN IMMEDIATE")
    try:
        cn.execute("INSERT INTO tinnhan (id, hoithoai_id, vai, noidung, nhatky_ai_id, luc, trangthai, tra_loi_cho, phu_json)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (t["id"], hoithoai_id, vai, noidung, nhatky_ai_id, t["luc"], trangthai, tra_loi_cho,
                    json.dumps(phu, ensure_ascii=False) if phu else None))
        timchu.ghi_tin(cn, t["id"], noidung)   # 0.8.0 (QĐ229): chỉ mục tìm chữ cùng giao dịch
        cn.execute("UPDATE hoithoai SET cap_nhat_luc = ? WHERE id = ?", (t["luc"], hoithoai_id))
        if tu_mo:
            cn.execute("COMMIT")
    except Exception:
        if tu_mo:
            cn.execute("ROLLBACK")
        raise
    return t


def _cua(cn, hoithoai_id: str, nguoidung_id: str) -> bool:
    return bool(cn.execute("SELECT 1 FROM hoithoai WHERE id = ? AND nguoidung_id = ?", (hoithoai_id, nguoidung_id)).fetchone())


def bat_luot(hoithoai_id: str | None, nguoidung_id: str, noidung: str, thumuc=None, mohinh_id: str | None = None,
             nghe: bool = True) -> dict:
    """Mở 01 lượt: ghi G02 `dangchay` → tin hỏi (thứ tự CDA (4)) rồi chạy nền, trả ngay {hoithoai_id, hoi, luot_id}.
    `nghe`: lượt có người nghe (trang mở luồng sự kiện) thì đọc dần đầu ra CLI. Cuộc đang có lượt chạy thì trả lượt đó."""
    from maychu.hethong import capnhat
    noidung = (noidung or "").strip()
    if not noidung:
        raise ValueError("Chưa có nội dung")
    if capnhat.dang_cho():   # QĐ347 H1: 0 dòng G02, 0 tin
        raise ChoCapNhat(luot.CHU_CHO_CAPNHAT)
    if hoithoai_id is not None:
        cn = ketnoi.mo("Bot", thumuc)
        try:
            if not _cua(cn, hoithoai_id, nguoidung_id):
                raise PermissionError("Không có cuộc trò chuyện này")
        finally:
            cn.close()
        dang = luot.dang_chay_cua(hoithoai_id)
        if dang:
            return {"hoithoai_id": hoithoai_id, "hoi": None, "luot_id": dang, "trung": True}
    moi = hoithoai_id is None
    hoithoai_id = hoithoai_id or maso.tao()
    lt = luot.Luot(maso.tao(), hoithoai_id, nguoidung_id)
    tin_hoi_id = maso.tao()
    luot.vao_so(lt)   # S1: vào sổ TRƯỚC khi ghi G02
    try:
        cu = luot.mo_g02(lt.id, hoithoai_id, tin_hoi_id, thumuc)
    except BaseException:
        luot.roi_so(lt, giu=False)
        raise
    if cu:   # cuộc đã có lượt chạy (01 lượt/cuộc): bỏ lượt mới khỏi sổ ngay (SOAT-SUA-H2)
        luot.roi_so(lt, giu=False)
        return {"hoithoai_id": hoithoai_id, "hoi": None, "luot_id": cu, "trung": True}
    cn = ketnoi.mo("Bot", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")   # Y40b L1: tạo cuộc (nếu mới) + tin hỏi + chỉ mục: 01 giao dịch
        if moi:
            bay = _bay_gio()
            cn.execute("INSERT INTO hoithoai (id, loai, nguoidung_id, tieude, trangthai, tao_luc, cap_nhat_luc)"
                       " VALUES (?, 'troly', ?, ?, 'dung', ?, ?)", (hoithoai_id, nguoidung_id, noidung[:80], bay, bay))
        truoc = cn.execute("SELECT vai, noidung FROM tinnhan WHERE hoithoai_id = ? AND vai IN ('nguoi', 'ai') ORDER BY luc, rowid",
                           (hoithoai_id,)).fetchall()
        hoi = _ghi_tin(cn, hoithoai_id, "nguoi", noidung, ma=tin_hoi_id)
        cn.execute("COMMIT")
    except BaseException:
        if cn.in_transaction:
            cn.execute("ROLLBACK")
        luot.dong_g02(lt.id, "hong", "ghi tin hỏi lỗi", thumuc)   # không để dòng G02 treo
        luot.roi_so(lt, giu=False)
        raise
    finally:
        cn.close()
    lich_su = "\n\n".join(f"{VAI_CHU[v]}: {n}" for v, n in truoc)[-GIU_CHU:]
    cau = (f"Các lượt trước của cuộc trò chuyện:\n{lich_su}\n\nBạn hỏi tiếp:\n{noidung}" if lich_su else noidung)
    if nghe:
        lt.nghe = congai.Nghe(lt.phat)
    lt.phat("bat_dau", luot_id=lt.id, hoithoai_id=hoithoai_id)
    lt.luong = threading.Thread(target=_chay_luot, args=(lt, hoi, cau, mohinh_id, thumuc), daemon=True,
                                name="igm360-luot-" + lt.id)
    lt.luong.start()
    return {"hoithoai_id": hoithoai_id, "hoi": hoi, "luot_id": lt.id}


def _tra_loi(kq: dict, hoithoai_id: str, tin_hoi_id: str, thumuc=None) -> dict:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        if "loi" in kq:
            ly = "; ".join(f"{b['nguon']}: {b['lydo']}" for b in kq["bo_qua"])
            return _ghi_tin(cn, hoithoai_id, "hethong", kq["loi"] + (f" ({ly})" if ly else "") + ". Mở mục Mô hình AI để kiểm nguồn AI.",
                            trangthai="loi", tra_loi_cho=tin_hoi_id)
        tl = _ghi_tin(cn, hoithoai_id, "ai", kq["chu"], kq["nhatky_ai_id"], trangthai="xong", tra_loi_cho=tin_hoi_id)
        tl["nguon"], tl["nguon_id"] = kq["nguon"], kq.get("nguon_id")   # Z10a: giao diện đặt chữ theo mã nguồn
        tl["mohinh_id"], tl["mohinh"], tl["ghim_hong"] = kq.get("mohinh_id"), kq.get("mohinh"), kq.get("ghim_hong")
        tl["md_hong"] = kq.get("md_hong")   # Y36c: lượt thường đã sang hãng khác vì mô hình mặc định hết hạn mức
        tl["mohinh_bao"] = kq.get("mohinh_bao")   # Y31c S4: mô hình công cụ báo về
        tl["ghim_khoa"] = kq.get("ghim_khoa")     # 0.7.6: khóa ghim chuẩn, giao diện lưu lại thay dạng cũ
        tl["chay_tk"], tl["du_phong"] = kq.get("chay_tk"), kq.get("du_phong")   # QĐ189: chỉ hiện khi rê chuột
        return tl
    finally:
        cn.close()


def _chay_luot(lt, hoi: dict, cau: str, mohinh_id, thumuc) -> None:
    """Luồng nền của 01 lượt. Ghi tin đúng 01 lần (CDA (3)), rồi mới đóng G02 (CDA (4)), rồi rời sổ (S1)."""
    tok = congai._NGHE.set(lt.nghe) if lt.nghe is not None else None
    try:
        try:
            kq = congai.goi(cau, thumuc=thumuc, loai_viec="trochuyen", mohinh_id=mohinh_id)   # CDA (1): không viecnen_id
        except congai.DaDung:   # nền TC46: ghi phần chữ đã có
            cn = ketnoi.mo("Bot", thumuc)
            try:
                tl = _ghi_tin(cn, lt.hoithoai_id, "ai", lt.nghe.chu_da_co() if lt.nghe else "", trangthai="dung",
                              tra_loi_cho=hoi["id"])
            finally:
                cn.close()
            luot.dong_g02(lt.id, "huy", thumuc=thumuc)
            from maychu.hethong import nhatky
            nhatky.ghi(luot.LOAI, "dung_luot", "dừng 01 lượt trò chuyện", nguoi_id=lt.nguoidung_id, thumuc=thumuc)
            lt.ket_qua = {"hoithoai_id": lt.hoithoai_id, "hoi": hoi, "tra_loi": tl}
            lt.phat("dung", tra_loi=tl)
            return
        tl = _tra_loi(kq, lt.hoithoai_id, hoi["id"], thumuc)
        luot.dong_g02(lt.id, "hong" if "loi" in kq else "xong", "không nguồn AI nào trả lời" if "loi" in kq else None, thumuc)
        lt.ket_qua = {"hoithoai_id": lt.hoithoai_id, "hoi": hoi, "tra_loi": tl}
        lt.phat("xong", tra_loi=tl)
    except BaseException as e:  # noqa: BLE001 - lỗi không lường trước: đóng G02, báo trang tải lại cuộc
        lt.loi_ngoai = e
        try:
            luot.dong_g02(lt.id, "hong", "lỗi khi chạy lượt", thumuc)
        except Exception:  # noqa: BLE001
            pass
        lt.phat("loi")
    finally:
        if tok is not None:
            congai._NGHE.reset(tok)
        luot.roi_so(lt)   # S1: rời sổ SAU khi đã đóng G02


def gui(hoithoai_id: str | None, nguoidung_id: str, noidung: str, thumuc=None, mohinh_id: str | None = None) -> dict:
    """Đường đồng bộ (không người nghe): mở lượt rồi chờ xong, trả {hoithoai_id, hoi, tra_loi} như trước N0.
    `mohinh_id`: mô hình anh ghim cho cuộc này (GĐ 1 trình duyệt nhớ, gửi kèm mỗi tin; QĐ180)."""
    kq = bat_luot(hoithoai_id, nguoidung_id, noidung, thumuc, mohinh_id, nghe=False)
    lt = luot.lay(kq["luot_id"], nguoidung_id)
    if lt is None or kq.get("trung"):
        raise PermissionError("Cuộc trò chuyện đang có câu trả lời chưa xong")
    lt.luong.join()
    if lt.loi_ngoai is not None:
        raise lt.loi_ngoai
    return lt.ket_qua


def danh_sach(nguoidung_id: str, thumuc=None) -> list[dict]:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        return [dict(zip(("id", "tieude", "cap_nhat_luc"), r)) for r in cn.execute(
            "SELECT id, tieude, cap_nhat_luc FROM hoithoai WHERE nguoidung_id = ? AND loai = 'troly'"
            " ORDER BY cap_nhat_luc DESC LIMIT 100", (nguoidung_id,))]
    finally:
        cn.close()


def _doc_phu(chu: str | None) -> dict | None:
    try:
        o = json.loads(chu) if chu else None
    except ValueError:
        return None
    return o if isinstance(o, dict) else None


def xem(hoithoai_id: str, nguoidung_id: str, thumuc=None) -> dict | None:
    cn = ketnoi.mo("Bot", thumuc)
    try:
        if not _cua(cn, hoithoai_id, nguoidung_id):
            return None
        tin = [dict(zip(("id", "vai", "noidung", "nhatky_ai_id", "luc", "trangthai"), r[:6]), phu=_doc_phu(r[6])) for r in cn.execute(
            "SELECT id, vai, noidung, nhatky_ai_id, luc, trangthai, phu_json FROM tinnhan WHERE hoithoai_id = ? ORDER BY luc, rowid",
            (hoithoai_id,))]
        td = cn.execute("SELECT tieude FROM hoithoai WHERE id = ?", (hoithoai_id,)).fetchone()[0]
    finally:
        cn.close()
    return {"id": hoithoai_id, "tieude": td, "tinnhan": tin, "luot_dang": luot.dang_chay_cua(hoithoai_id)}
