"""Đường gọi cho màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt (ngày 04), két khóa và màn 11 Nguồn dữ liệu (ngày 05).

Bảo vệ: mã phiên ở cookie HttpOnly, SameSite=Strict, Secure; mọi lệnh ghi phải có header X-IGM360
(trang web khác không gửi được header này). Chặn đoán mật khẩu theo địa chỉ IP thật, phiên 30 ngày (QĐ90).
"""
import asyncio
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from maychu.dulieu import muigio
from maychu.dulieu import ketnoi
from maychu.hethong import capnhat
from maychu.hethong.caidat import tenmien, thongso
from maychu.hethong.kekhoa import kho
from maychu.hethong.giamsat import thongbao
from maychu.hethong.mohinh import congai, dangnhap_goi, danhmuc_mohinh, luot, madaihan, trochuyen
from maychu.hethong.nhatky import ghi as ghi_f04
from maychu.hethong.taikhoan import nguoidung, phien
from maychu.ketnoi import drive

COOKIE = "igm360_phien"
router = APIRouter(prefix="/api")


def _an_toan(request: Request) -> None:
    if request.method != "GET" and request.headers.get("x-igm360") != "1":
        raise HTTPException(403, "Thiếu dấu của trang IGM360")


def can_dang_nhap(request: Request) -> dict:
    _an_toan(request)
    p = phien.tim(request.cookies.get(COOKIE))
    if not p:
        raise HTTPException(401, "Chưa đăng nhập")
    return p


def _dat_cookie(res: Response, ma: str) -> None:
    res.set_cookie(COOKIE, ma, httponly=True, samesite="strict", path="/", max_age=phien.NGAY_TOIDA * 86400,
                   secure=os.environ.get("IGM360_COOKIE_SECURE", "1") != "0")


def _ip(request: Request) -> str:
    """Địa chỉ thật: uvicorn chỉ tin X-Forwarded-For từ cổng HTTPS (biến FORWARDED_ALLOW_IPS)."""
    return request.client.host if request.client else "khong_ro"


def _loi_dangnhap(kq: dict):
    if kq["loi"] == "khoa":
        raise HTTPException(429, {"loi": "khoa", **kq["khoa"]})
    raise HTTPException(400, {"loi": kq["loi"], "con_lai": kq.get("con_lai")})


class DangNhap(BaseModel):
    ten: str
    matkhau: str


class Ma2Lop(BaseModel):
    ma_tam: str
    ma: str


class SuaThongSo(BaseModel):
    giatri: str = ""
    hieuluc_tu: str
    ghichu: str = ""


class DoiMatKhau(BaseModel):
    cu: str
    moi: str
    nhap_lai: str


class MaCu(BaseModel):
    ma: str


class CheDoCapNhat(BaseModel):
    che_do: str = "cho"
    van_capnhat: bool = False   # QĐ218 dòng 34: anh bấm "Vẫn cập nhật" khi Drive chưa kết nối


class TiepTuc(BaseModel):
    van: bool = False


@router.post("/dangnhap")
def dang_nhap(body: DangNhap, request: Request, response: Response):
    _an_toan(request)
    kq = nguoidung.buoc_matkhau(body.ten.strip(), body.matkhau, _ip(request),
                                thietbi=phien.thietbi_tu(request.headers.get("user-agent")))
    if "loi" in kq:
        _loi_dangnhap(kq)
    if kq.get("buoc") == "vao":   # QĐ390: 02 lớp đang tắt → tạo phiên, đặt cookie ngay; không trả mã phiên
        _dat_cookie(response, kq.pop("ma_phien"))
    return kq


@router.post("/dangnhap/ma2lop")
def dang_nhap_ma(body: Ma2Lop, request: Request, response: Response):
    _an_toan(request)
    kq = nguoidung.buoc_ma2lop(body.ma_tam, body.ma, phien.thietbi_tu(request.headers.get("user-agent")), _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
    _dat_cookie(response, kq["ma_phien"])
    return {"ok": True}


@router.post("/dangxuat")
def dang_xuat(response: Response, p: dict = Depends(can_dang_nhap)):
    phien.thu_hoi(p["nguoidung_id"], phien_id=p["phien_id"])
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/toi")
def toi(p: dict = Depends(can_dang_nhap)):
    return {**nguoidung.thong_tin(p["nguoidung_id"]), "phien_id": p["phien_id"], "het_luc": p["het_luc"],
            "muigio": thongso.doc_mot(muigio.TEN, muigio.MAC_DINH)}   # QĐ636: giao diện hiện giờ theo múi đã chọn


@router.post("/phien/giahan")
def gia_han(p: dict = Depends(can_dang_nhap)):
    """Nút "Ở lại": mỗi lần gọi đã tính là có thao tác; hạn tối đa 30 ngày không đổi."""
    return {"het_luc": p["het_luc"]}


@router.post("/phien/thuhoi_khac")
def thu_hoi_khac(p: dict = Depends(can_dang_nhap)):
    return {"so": phien.thu_hoi(p["nguoidung_id"], tru_id=p["phien_id"])}


@router.get("/demso")
def dem_so(p: dict = Depends(can_dang_nhap), mo: int = 0):
    """Số trên menu và chuông (màn 02). Chuông bước 1 (QĐ165, Z7b): dòng D03 còn mở qua 01 hàm lọc quyền,
    số = dòng tạo sau mốc đọc. Giao diện hỏi lại mỗi 60 giây (không hỏi kho). `mo=1` (anh mở chuông, QĐ174):
    dò bản mới trước, kết quả còn mới (dưới 05 phút) thì không hỏi kho."""
    if mo:
        try:
            thongbao.quet_banmoi()
        except Exception:   # lỗi dò bản mới không được làm hỏng chuông
            pass
    cn = ketnoi.mo("Dulieu_Chinh")
    try:
        cuacho = cn.execute("SELECT count(*) FROM cuacho WHERE trangthai IN ('moi', 'choduyet')").fetchone()[0]
    finally:
        cn.close()
    tb = thongbao.danh_sach(p["nguoidung_id"])
    try:
        tamtat = thongso.cong_tac_bat("chuong_tamtat")   # QĐ551
    except Exception:   # noqa: BLE001 - đọc cờ lỗi thì coi như chưa tạm tắt (vẫn báo – an toàn hơn im)
        tamtat = False
    return {"cuacho": cuacho, "thongbao": tb["ds"], "so_moi": tb["so_moi"], "ket_ai": 0,
            "tamtat": tamtat, "ban": capnhat.ban_dang_chay()}   # QĐ553 (3): chân bảng có số bản


@router.post("/thongbao/dochet")
def doc_het_thongbao(p: dict = Depends(can_dang_nhap)):
    """Nút "Đọc hết": đặt mốc đọc = lúc bấm (QĐ165); không đổi trạng thái cảnh báo, kể cả tin sự kiện (CPO TIN-TM-MG-SUA)."""
    return {"moc_doc": thongso.dat_moc_doc(nguoi=p["nguoidung_id"])}


@router.get("/thongso")
def doc_thongso(p: dict = Depends(can_dang_nhap)):
    from maychu.ketnoi import drive
    try:
        noi = drive.dang_noi()
    except Exception:  # noqa: BLE001
        noi = False
    return {**thongso.doc_het(), "drive_noi": noi}   # QĐ278 Z21 dòng 2: bật mà chưa nối thì hiện dòng nhắc


@router.get("/thongso/{ten}/lichsu")
def lichsu_thongso(ten: str, p: dict = Depends(can_dang_nhap)):
    return thongso.lich_su(ten)


class GatCongTac(BaseModel):
    bat: bool


@router.post("/thongso/{ten}/gat")
def gat_cong_tac(ten: str, body: GatCongTac, p: dict = Depends(can_dang_nhap)):
    """QĐ278 (Z21): gạt công tắc có hiệu lực ngay; ghi F04 01 dòng (ai, lúc, bật hay tắt) – PTD-15 mục 3."""
    kq = thongso.gat(ten, body.bat, nguoi=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq)
    if kq.get("doi"):
        ghi_f04("thongso", "gat", f"{ten} → {'bật' if body.bat else 'tắt'}", nguoi_id=p["nguoidung_id"])
    if ten == "tunang_congcu_ai" and body.bat:   # QĐ264 (Z20 dòng 13): gạt bật lại thì bỏ tạm dừng sau quay về
        from maychu.hethong.mohinh import nangcli
        nangcli.mo_lai(ly_do="bạn bật lại công tắc")
    return kq


@router.post("/thongso/{ten}")
def sua_thongso(ten: str, body: SuaThongSo, p: dict = Depends(can_dang_nhap)):
    kq = thongso.dat(ten, body.giatri, body.hieuluc_tu, body.ghichu, nguoi=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq)
    return kq


@router.get("/taikhoan")
def tai_khoan(p: dict = Depends(can_dang_nhap)):
    return {**nguoidung.thong_tin(p["nguoidung_id"]), "phien_id": p["phien_id"], "phien": phien.danh_sach(p["nguoidung_id"])}


@router.post("/phien/{ma}/thuhoi")
def thu_hoi(ma: str, p: dict = Depends(can_dang_nhap)):
    if ma == p["phien_id"]:
        raise HTTPException(400, "Phiên đang dùng thì bấm Đăng xuất")
    return {"so": phien.thu_hoi(p["nguoidung_id"], phien_id=ma)}


@router.post("/matkhau")
def doi_mat_khau(body: DoiMatKhau, p: dict = Depends(can_dang_nhap)):
    kq = nguoidung.doi_matkhau(p["nguoidung_id"], body.cu, body.moi, body.nhap_lai, p["phien_id"])
    if "loi" in kq:
        raise HTTPException(400, kq)
    return kq


def _loi_2lop(kq: dict):
    """Lỗi đường đổi máy nhận mã: đang khóa (QĐ393 (4)) trả 429 như đăng nhập; còn lại 400 với câu báo."""
    if kq["loi"] == "khoa":
        _loi_dangnhap(kq)
    raise HTTPException(400, kq["loi"])


@router.post("/2lop/doimay/batdau")
def doi_may_batdau(body: MaCu, request: Request, p: dict = Depends(can_dang_nhap)):
    """Bước 1: nhập mã trên máy cũ; đúng thì trả QR của khóa mới. QĐ398: 02 lớp đang tắt thì từ chối."""
    kq = nguoidung.kiem_ma_hien_tai(p["nguoidung_id"], body.ma, ip=_ip(request))
    if "loi" in kq:
        _loi_2lop(kq)
    kq = nguoidung.bat_doi_may(p["nguoidung_id"])
    if "loi" in kq:
        _loi_2lop(kq)
    return kq


@router.post("/2lop/doimay/xacnhan")
def doi_may_xacnhan(body: Ma2Lop, request: Request, p: dict = Depends(can_dang_nhap)):
    kq = nguoidung.xac_nhan_doi_may(p["nguoidung_id"], body.ma_tam, body.ma, ip=_ip(request))
    if "loi" in kq:
        _loi_2lop(kq)
    return kq


class DoiMuiGio(BaseModel):
    ten: str = muigio.TEN
    giatri: str = ""
    matkhau: str = ""
    ma: str = ""


@router.get("/muigio")
def xem_muigio(p: dict = Depends(can_dang_nhap)):
    """QĐ636: múi đang dùng (② ngày số liệu, ③ giờ hiện) + múi đối soát + danh sách chọn cho thẻ Chung."""
    return {"muigio": thongso.doc_mot(muigio.TEN, muigio.MAC_DINH), "muigio_doisoat": thongso.doc_mot(muigio.TEN_DOISOAT, muigio.MAC_DINH),
            "danh_sach": muigio.danh_sach(), "quoc_gia": muigio.quoc_gia(), "hom_nay": muigio.hom_nay(), "ban": muigio.ly_do_ban(),
            "la_chu": p.get("vaitro") == "chu"}


@router.get("/caidat/chung")
def xem_chung(p: dict = Depends(can_dang_nhap)):
    """QĐ627 (3), QĐ649: công tắc "Giữ dấu ảnh AI" của ngăn Chung (gạt qua đường gạt chung /thongso/{ten}/gat)."""
    return {"c2pa": thongso.cong_tac_bat("anh_ai_giu_dau_c2pa")}


@router.post("/muigio")
def doi_muigio(body: DoiMuiGio, request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ636: chỉ Chủ, nhập lại mật khẩu + mã 02 lớp; đang nạp / chốt kỳ thì từ chối; ghi P01 + F04 (thongso.doi_muigio)."""
    ban = muigio.ly_do_ban()
    if ban:
        raise HTTPException(409, ban)
    kq = nguoidung.xac_minh_lai(p["nguoidung_id"], body.matkhau, body.ma, "muigio", _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
    kq = thongso.doi_muigio(body.ten, body.giatri, p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return {**kq, "hom_nay": muigio.hom_nay()}


class DoiTenMien(BaseModel):
    ten: str = ""     # trống = bỏ tên riêng
    matkhau: str = ""
    ma: str = ""


def _host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0]


@router.get("/tenmien")
def xem_tenmien(request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ634: tên gốc, tên riêng đã lưu, đã bật đổi tên miền chưa (nhanh, không dò mạng)."""
    return {"bat": tenmien.da_bat(), "goc": tenmien.ten_goc(_host(request)), "rieng": tenmien.ten_rieng() or None,
            "la_chu": p.get("vaitro") == "chu"}


@router.get("/tenmien/kiem")
def kiem_tenmien(request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ634, QĐ650: bảng "Địa chỉ · DNS · HTTPS" – dò DNS (chỉ cảnh báo) và đọc hạn chứng chỉ của 02 tên."""
    return tenmien.kiem(_host(request))


@router.post("/tenmien")
def doi_tenmien(body: DoiTenMien, request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ634: chỉ Chủ, nhập lại mật khẩu + mã 02 lớp; chưa nâng cấu hình thì từ chối (409); ghi P01 + F04; lưu xong
    kiểm luôn ("Lưu và kiểm tra", QĐ651)."""
    if not tenmien.da_bat():
        raise HTTPException(409, tenmien.CHU_TENMIEN["chua_bat"])
    kq = nguoidung.xac_minh_lai(p["nguoidung_id"], body.matkhau, body.ma, "tenmien", _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
    kq = thongso.doi_tenmien(body.ten, p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return {**kq, "kiem": tenmien.kiem(_host(request))}


class Tat2Lop(BaseModel):
    matkhau: str = ""
    ma: str = ""


@router.post("/2lop/tat")
def tat_2lop(body: Tat2Lop, request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ390: tắt 02 lớp – chỉ phiên đăng nhập, hỏi mật khẩu + mã hiện tại. Chế độ an toàn: không cho tắt (CDA 16g (4))."""
    from maychu.hethong import antoan
    if antoan.CHE_DO["an_toan"]:
        raise HTTPException(403, nguoidung.CHU_2LOP["an_toan"])
    kq = nguoidung.tat_2lop(p["nguoidung_id"], body.matkhau, body.ma, _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
    return kq


@router.post("/2lop/bat")
def bat_2lop(body: MaCu, request: Request, p: dict = Depends(can_dang_nhap)):
    """QĐ390, QĐ393 (1): bật lại bằng 01 mã của khóa cũ; mọi máy khác tự đăng xuất. Chế độ an toàn vẫn cho bật."""
    kq = nguoidung.bat_lai_2lop(p["nguoidung_id"], body.ma, p["phien_id"], _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
    return kq


def _them_antoan() -> dict:
    """0.7.9: ổ trống (lớp 1), Drive đã nối (lớp 5), bước bản sao đang chạy, chế độ an toàn (lớp 2), quay về (lớp 3)."""
    from maychu.hethong import antoan
    from maychu.ketnoi import drive
    o = antoan.o_trong()
    try:
        noi = drive.dang_noi()
    except Exception:  # noqa: BLE001 - ở chế độ an toàn bảng kết nối có thể chưa đọc được
        noi = False
    return {"o_trong": {"du": o["du"], "chu": o["chu"], "lam": None if o["du"] else antoan.CHU["o_thieu_lam"]}, "drive_noi": noi, "drive_bat": thongso.drive_bat(), "chu_drive": None if noi else antoan.CHU["drive_chua_noi"], "chu_qua_gio": antoan.CHU["drive_qua_gio"],
            **capnhat.trang_thai_sao(), "an_toan": antoan.chu_an_toan(), "quay_ve": antoan.thong_tin_quayve(),
            "quayve_loi": antoan.quay_ve_loi_gan(), "kiem_hien": next((x.get("kiem") for x in capnhat.lich_su() if x["ban"] == capnhat.ban_dang_chay()), None),
            "tien_do": _tien_do()}


def _tien_do() -> dict | None:
    """QĐ251: tiến độ 08 bước của lượt cập nhật (bước 5–7 là ước tính). Đọc lỗi thì không trả, không chặn màn."""
    try:
        from maychu.hethong import tiendo
        return tiendo.hien()
    except Exception:  # noqa: BLE001
        return None


@router.get("/capnhat")
def xem_capnhat(p: dict = Depends(can_dang_nhap)):
    return {**capnhat.kiem_tra(), "lichsu": capnhat.lich_su(), "so_viec_ai": capnhat.so_viec_ai_dangchay(), **_them_antoan()}


@router.post("/capnhat/kiemtra")
def kiem_lai(p: dict = Depends(can_dang_nhap)):
    return {**capnhat.kiem_tra(bat_buoc=True), "lichsu": capnhat.lich_su(), "so_viec_ai": capnhat.so_viec_ai_dangchay(),
            **_them_antoan()}


class GoiCli(BaseModel):
    goi: str


@router.get("/capnhat/congcu_ai")
def xem_congcu_ai(p: dict = Depends(can_dang_nhap)):
    """Y46 (Z20): khối Công cụ AI ở màn Cập nhật."""
    from maychu.hethong.mohinh import nangcli
    return nangcli.xem()


@router.post("/capnhat/congcu_ai/nang")
def nang_congcu_ai(body: GoiCli, p: dict = Depends(can_dang_nhap)):
    """Nút "Nâng công cụ AI" (Z20 dòng 7): chạy nền, F04 ghi trong bộ nâng (người bấm)."""
    from maychu.hethong.mohinh import nangcli
    if body.goi not in nangcli.GOI_CLI:
        raise HTTPException(400, "Không có công cụ này")
    kq = nangcli.nang_nen(body.goi, nguoi=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(409, {"loi": kq["loi"]})
    return kq


@router.post("/capnhat/congcu_ai/ve")
def ve_congcu_ai(body: GoiCli, p: dict = Depends(can_dang_nhap)):
    """Nút "Về bản trước" (Z20 dòng 11)."""
    from maychu.hethong.mohinh import nangcli
    if body.goi not in nangcli.GOI_CLI:
        raise HTTPException(400, "Không có công cụ này")
    kq = nangcli.ve_ban_truoc(body.goi, nguoi=p["nguoidung_id"])
    if kq["kq"] != "ve":
        raise HTTPException(409, {"loi": kq.get("ly_do") or kq["kq"]})
    return kq


class QuayVe(BaseModel):
    dong_y_mat: bool = False


@router.post("/capnhat/quayve")
def quay_ve(body: QuayVe, p: dict = Depends(can_dang_nhap)):
    """0.7.9 lớp 3 (QĐ215): quay về bản liền trước để sẵn trong ảnh."""
    from maychu.hethong import antoan
    kq = antoan.quay_ve(p["nguoidung_id"], body.dong_y_mat)
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


@router.post("/capnhat")
def cap_nhat(body: CheDoCapNhat, p: dict = Depends(can_dang_nhap)):
    kq = capnhat.yeu_cau(p["nguoidung_id"], body.che_do, van_capnhat=body.van_capnhat)
    if kq.get("can_chon"):
        return kq   # giao diện mở hộp "Cập nhật khi chưa có bản sao Drive?"
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


@router.post("/capnhat/tieptuc")
def tiep_tuc_capnhat(body: TiepTuc, p: dict = Depends(can_dang_nhap)):
    kq = capnhat.tiep_tuc(p["nguoidung_id"], body.van)
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


# ---- Két khóa (màn 09, ngày 05) ----
class KhoaMoi(BaseModel):
    dichvu: str
    giatri: str
    han: str | None = None


class DoiKhoa(BaseModel):
    giatri: str
    han: str | None = None


def _songay() -> int:
    try:
        return int(thongso.doc_mot("songay_baotruoc_khoa_hethan", "5"))
    except ValueError:
        return 5


def _kiem_han(han: str | None) -> str | None:
    if not han:
        return None
    from datetime import date
    try:
        return date.fromisoformat(muigio.ngay_cua(han)).isoformat()   # ③ QĐ636: ngày hết hạn theo múi đã chọn
    except ValueError:
        raise HTTPException(400, "Hạn khóa phải là ngày (năm-tháng-ngày)")


@router.get("/kekhoa")
def xem_kekhoa(p: dict = Depends(can_dang_nhap)):
    n = _songay()
    ds = kho.danh_sach(songay_baotruoc=n)
    dem = {k: sum(1 for x in ds if x["tinhtrang"] == k) for k in ("dung", "khong_han", "saphet", "hethan")}
    return {"ds": ds, "dem": dem, "tong": len(ds), "songay_baotruoc": n}


@router.post("/kekhoa")
def them_khoa(body: KhoaMoi, p: dict = Depends(can_dang_nhap)):
    if not body.giatri.strip() or not body.dichvu.strip() or body.dichvu in kho.NOIBO:
        raise HTTPException(400, "Thiếu tên dịch vụ hoặc giá trị khóa")
    ma = kho.cat(body.dichvu.strip(), body.giatri.strip(), han=_kiem_han(body.han), nguoi_nhap=p["nguoidung_id"])
    ghi_f04("kekhoa", "them", f"dịch vụ {body.dichvu.strip()}", nguoi_id=p["nguoidung_id"])
    return {"id": ma}


@router.post("/kekhoa/{ma}/doi")
def doi_khoa(ma: str, body: DoiKhoa, p: dict = Depends(can_dang_nhap)):
    if not body.giatri.strip() or ma not in {x["id"] for x in kho.danh_sach()}:
        raise HTTPException(400, "Không đổi được khóa này")
    kho.doi(ma, body.giatri.strip(), han=_kiem_han(body.han))
    ghi_f04("kekhoa", "doi", f"khóa {ma}", nguoi_id=p["nguoidung_id"])
    return {"id": ma}


@router.post("/kekhoa/{ma}/xoa")
def xoa_khoa(ma: str, p: dict = Depends(can_dang_nhap)):
    """Xóa hẳn (không lấy lại được); nguồn dùng khóa này ngừng lấy số."""
    if ma not in {x["id"] for x in kho.danh_sach()}:
        raise HTTPException(400, "Không xóa được khóa này")
    kho.xoa(ma)
    cn = ketnoi.mo("Ketnoi")
    try:
        so = cn.execute("UPDATE ketnoi SET trangthai_phien = 'mat_khoa', loi_cuoi = 'Khóa đã bị xóa ở Két khóa'"
                        " WHERE khoa_id = ?", (ma,)).rowcount
    finally:
        cn.close()
    ghi_f04("kekhoa", "xoa", f"khóa {ma}; {so:02d} nguồn ngừng lấy số", nguoi_id=p["nguoidung_id"])
    return {"id": ma, "so_nguon_ngung": so}


# ---- Nguồn dữ liệu (màn 11, ngày 05): GĐ 1 chỉ có Google Drive ----
class UngDungGoogle(BaseModel):
    client_id: str
    client_secret: str


def _duong_ve(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/ketnoi/drive/vetrang"


@router.get("/nguon")
def xem_nguon(request: Request, p: dict = Depends(can_dang_nhap)):
    return {"drive": drive.tinh_hinh(), "duong_ve": _duong_ve(request)}


@router.post("/ketnoi/drive/ungdung")
def luu_ung_dung(body: UngDungGoogle, p: dict = Depends(can_dang_nhap)):
    try:
        drive.luu_ungdung(body.client_id, body.client_secret)
    except ValueError as e:
        raise HTTPException(400, str(e))
    ghi_f04("ketnoi", "drive_ungdung", "lưu mã ứng dụng Google", nguoi_id=p["nguoidung_id"])
    return {"ok": True}


@router.post("/ketnoi/drive/batdau")
def bat_dau_drive(request: Request, p: dict = Depends(can_dang_nhap)):
    try:
        return {"url": drive.bat_dau(_duong_ve(request), p["nguoidung_id"])}
    except LookupError as e:
        raise HTTPException(400, str(e))


@router.get("/ketnoi/drive/vetrang", response_class=HTMLResponse)
def ve_trang_drive(code: str = "", state: str = "", error: str = ""):
    """Google chuyển về đây (không mang cookie vì SameSite=Strict); kiểm bằng mã chống giả dùng 01 lần."""
    if error:
        kq, ok = "Bạn chưa cấp quyền cho IGM360 trên Google.", False
    else:
        try:
            drive.ve_trang(code, state)
            kq, ok = "Đã kết nối Google Drive.", True
            ghi_f04("ketnoi", "drive_noi", "kết nối Google Drive (quyền drive.file)")
        except (PermissionError, RuntimeError, LookupError) as e:
            kq, ok = str(e), False
    import html
    dich = "/#nguon" if ok else "/#nguon-loi"   # trang mới mở từ trang này (cùng trang web) thì trình duyệt gửi cookie
    return HTMLResponse(f'<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="1;url={dich}">'
                        f'<title>IGM360</title><p>{html.escape(kq)}</p><p><a href="{dich}">Về IGM360</a></p>',
                        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.post("/ketnoi/drive/daythu")
def day_ngay(p: dict = Depends(can_dang_nhap)):
    return drive.day_hang_cho()


@router.post("/ketnoi/drive/ngung")
def ngung_drive(p: dict = Depends(can_dang_nhap)):
    drive.ngung()
    ghi_f04("ketnoi", "drive_ngung", "ngừng Google Drive", nguoi_id=p["nguoidung_id"])
    return {"ok": True}


# ---- Màn 13 Model (ngày 06): đăng nhập gói trên giao diện ----
class TaiKhoanGoi(BaseModel):
    taikhoan: int = 1


class MaGoi(BaseModel):
    taikhoan: int = 1
    ma: str


def _goi(goi: str, taikhoan: int):
    try:
        dangnhap_goi._kiem(goi, taikhoan)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/mohinh")
def xem_mohinh(p: dict = Depends(can_dang_nhap)):
    goi = dangnhap_goi.tinh_hinh_goi()
    nguon = dangnhap_goi.danh_sach()
    for n in nguon:
        n["het_mh"] = congai.ds_het_mo_hinh(n["id"])   # Y36b: "Opus của tài khoản 1 hết hạn mức đến …"
        n["tk_nghi_den"] = congai.tk_nghi_den(n)       # N5: "Tài khoản 1 đang tạm nghỉ đến …"
    return {"goi": goi, "nguon": nguon, "so_viec_ai_songsong": thongso.doc_mot("so_viec_ai_songsong"),
            "tuan": congai.tom_tat_tuan(), "thang": congai.tom_tat_thang(),
            "ty_gia_usd": None}   # QĐ122: lấy tỷ giá USD làm ở ngày 18; tới đó giao diện ghi "chưa có tỷ giá"


@router.post("/mohinh/goi/{goi}/batdau")
def goi_bat_dau(goi: str, body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    _goi(goi, body.taikhoan)
    kq = dangnhap_goi.bat_dau(goi, body.taikhoan)
    # QĐ164 ý 3: ghi F04 cả lúc bắt đầu đăng nhập (không ghi đường link, mã)
    ghi_f04("mohinh", "batdau_goi", dangnhap_goi.nhan_dangnhap(goi, body.taikhoan), ketqua="loi" if "loi" in kq else "dat",
            nguoi_id=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


def _loi_dn(goi: str, taikhoan: int, kq: dict, p: dict) -> HTTPException:
    """QĐ164 ý 1: lượt bị chặn vì trùng ghi F04 kết quả `bichan`, chỉ ghi số ô bị trùng, không ghi định danh."""
    if kq.get("trung_voi"):
        ghi_f04("mohinh", "dangnhap_goi", dangnhap_goi.nhan_dangnhap(goi, taikhoan), ketqua="bichan",
                lydo=f"trùng tài khoản {kq['trung_voi']:02d}", nguoi_id=p["nguoidung_id"])
        return HTTPException(409, {"loi": kq["loi"], "trung_voi": kq["trung_voi"],
                                   **({"chu_rieng": True} if kq.get("chu_rieng") else {}),
                                   **({"lay_lai": True} if kq.get("lay_lai") else {})})   # dải báo trùng; Y38d N41 câu riêng; Y38f L3
    return HTTPException(400, kq["loi"])


@router.post("/mohinh/goi/claude/ma")
def goi_dan_ma(body: MaGoi, p: dict = Depends(can_dang_nhap)):
    _goi("claude", body.taikhoan)
    kq = dangnhap_goi.dan_ma("claude", body.taikhoan, body.ma, nguoi=p["nguoidung_id"])
    if "loi" in kq:
        raise _loi_dn("claude", body.taikhoan, kq, p)
    ghi_f04("mohinh", "dangnhap_goi", dangnhap_goi.nhan_dangnhap("claude", body.taikhoan), nguoi_id=p["nguoidung_id"])
    return kq


@router.post("/mohinh/goi/chatgpt/hoi")
def goi_hoi(body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    _goi("chatgpt", body.taikhoan)
    kq = dangnhap_goi.hoi("chatgpt", body.taikhoan, nguoi=p["nguoidung_id"])
    if "loi" in kq:
        raise _loi_dn("chatgpt", body.taikhoan, kq, p)
    if kq.get("xong"):
        ghi_f04("mohinh", "dangnhap_goi", dangnhap_goi.nhan_dangnhap("chatgpt", body.taikhoan), nguoi_id=p["nguoidung_id"])
    return kq


@router.post("/mohinh/goi/{goi}/huy")
def goi_huy(goi: str, body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    _goi(goi, body.taikhoan)
    dangnhap_goi.huy(goi, body.taikhoan)
    return {"ok": True}


@router.post("/mohinh/goi/{goi}/go")
def goi_go(goi: str, body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    """QĐ164 ý 2: gỡ tài khoản gói (giao diện đã hỏi lại 01 lần)."""
    _goi(goi, body.taikhoan)
    kq = dangnhap_goi.go(goi, body.taikhoan)
    if goi == "claude" and "loi" not in kq:
        thongbao.quet_madaihan()   # N24: mã đã xóa thì đóng ngay tin "hết hạn", không chờ lần quét kế tiếp
    ghi_f04("mohinh", "go_goi", dangnhap_goi.nhan_dangnhap(goi, body.taikhoan), ketqua="loi" if "loi" in kq else "dat",
            nguoi_id=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


# ---- 0.7.8 (QĐ198, PTD-09): mã dài hạn gói Claude. Không đường nào trả mã ra; F04 chỉ ghi "mã dài hạn" ----
def _md_nhan(tk: int) -> str:
    return f"{dangnhap_goi.nhan_dangnhap('claude', tk)} · mã dài hạn"


def _md_xong(tk: int, ma: str, p: dict) -> dict:
    try:
        kq = madaihan.ket_noi(tk, ma, nguoi=p["nguoidung_id"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        madaihan.huy_lay(tk)   # Đ3: quên đầu ra của lệnh lấy mã
    if "loi" in kq:   # QĐ216 N4: trùng tài khoản thì không lưu mã
        raise HTTPException(400, kq["loi"])
    ghi_f04("mohinh", "luu_madaihan", _md_nhan(tk), nguoi_id=p["nguoidung_id"])
    thongbao.quet_madaihan()   # mã mới: đóng ngay tin "hết hạn", "sắp hết hạn" cũ
    if kq.get("goi_thu"):
        ghi_f04("mohinh", "dangnhap_goi", dangnhap_goi.nhan_dangnhap("claude", tk), nguoi_id=p["nguoidung_id"])   # "Đăng nhập lúc"
    return kq


@router.post("/mohinh/goi/claude/madaihan/batdau")
def md_bat_dau(body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    _goi("claude", body.taikhoan)
    kq = madaihan.bat_dau_lay(body.taikhoan, dangnhap_goi._env("claude", body.taikhoan, ma_daihan=False))
    ghi_f04("mohinh", "batdau_madaihan", _md_nhan(body.taikhoan), ketqua="loi" if "loi" in kq else "dat",
            nguoi_id=p["nguoidung_id"])
    if kq.get("khong_ho_tro"):
        return {"khong_ho_tro": True, "loi": kq["loi"]}
    if "loi" in kq:
        raise HTTPException(400, {"loi": kq["loi"], "chi_tiet": kq.get("chi_tiet") or ""})   # N17: câu gốc để rê chuột
    if kq.get("xong"):   # lệnh in mã ngay, không cần mã trang đăng nhập
        r = madaihan.gui_ma(body.taikhoan, "")
        if "ma" in r:
            return _md_xong(body.taikhoan, r["ma"], p)
    return {"url": kq["url"]}


@router.post("/mohinh/goi/claude/madaihan/ma")
def md_gui_ma(body: MaGoi, p: dict = Depends(can_dang_nhap)):
    """Mã trang đăng nhập hiện → lệnh in mã dài hạn → lưu Két khóa, gọi thử."""
    _goi("claude", body.taikhoan)
    r = madaihan.gui_ma(body.taikhoan, body.ma)
    if "loi" in r:
        raise HTTPException(400, {"loi": r["loi"], "chi_tiet": r.get("chi_tiet") or ""})
    return _md_xong(body.taikhoan, r["ma"], p)


@router.post("/mohinh/goi/claude/madaihan/dan")
def md_dan(body: MaGoi, p: dict = Depends(can_dang_nhap)):
    """Dán mã dài hạn làm ở nơi khác (`claude setup-token` trên máy anh)."""
    _goi("claude", body.taikhoan)
    if not madaihan.hop_le(body.ma):
        raise HTTPException(400, madaihan.chu_loi_dan(body.ma))   # N28 (c)
    return _md_xong(body.taikhoan, madaihan.lam_sach(body.ma), p)


@router.post("/mohinh/goi/claude/madaihan/huy")
def md_huy(body: TaiKhoanGoi, p: dict = Depends(can_dang_nhap)):
    _goi("claude", body.taikhoan)
    madaihan.huy_lay(body.taikhoan)
    return {"ok": True}


@router.get("/mohinh/danhsach")
def ds_mohinh(p: dict = Depends(can_dang_nhap)):
    """Ô chọn mô hình màn 08 và hộp "Đổi" màn 13 dùng chung 01 danh sách (QĐ178, Z10)."""
    return danhmuc_mohinh.danh_sach()


class MacDinh(BaseModel):
    loai_viec: str
    mohinh_id: str | None = None
    nguon_id: str | None = None   # Z10c: mohinh_id trống + nguon_id = "mặc định của nguồn" đó
    khoa: str | None = None       # 0.7.6 (QĐ187): "loại nguồn|mã mô hình"; "loại|" = mặc định của loại nguồn


@router.post("/mohinh/macdinh")
def dat_macdinh(body: MacDinh, p: dict = Depends(can_dang_nhap)):
    try:
        kq = danhmuc_mohinh.dat_macdinh(body.loai_viec, body.mohinh_id, nguon_id=body.nguon_id, khoa=body.khoa)
    except ValueError as e:
        raise HTTPException(400, str(e))
    ghi_f04("mohinh", "doi_macdinh", f"{body.loai_viec}: {body.khoa or body.mohinh_id or ('mặc định của nguồn ' + body.nguon_id if body.nguon_id else 'theo ưu tiên')}",
            nguoi_id=p["nguoidung_id"])
    return {"macdinh": kq}


@router.post("/mohinh/{nguon_id}/goithu")
def goi_thu(nguon_id: str, p: dict = Depends(can_dang_nhap)):
    kq = congai.goi("Trả lời đúng 01 câu ngắn bằng tiếng Việt: IGM360 gọi thử nguồn AI.", chi_nguon_id=nguon_id)
    if "loi" in kq:
        raise HTTPException(400, "; ".join(b["lydo"] for b in kq["bo_qua"]) or kq["loi"])
    return {"chu": kq["chu"], "nguon": kq["nguon"]}


# ---- F35 Trò chuyện (ngày 06) ----
class TinMoi(BaseModel):
    hoithoai_id: str | None = None
    noidung: str
    mohinh_id: str | None = None   # QĐ180: mô hình ghim cho cuộc này (trình duyệt nhớ)
    nen: bool = False   # N0: giao diện gửi true → lượt chạy nền, trả ngay luot_id; không gửi → trả lời đồng bộ như trước


@router.get("/trochuyen")
def ds_trochuyen(p: dict = Depends(can_dang_nhap)):
    return {"hoithoai": trochuyen.danh_sach(p["nguoidung_id"])}


@router.get("/trochuyen/{ma}")
def xem_trochuyen(ma: str, p: dict = Depends(can_dang_nhap)):
    kq = trochuyen.xem(ma, p["nguoidung_id"])
    if kq is None:
        raise HTTPException(404, "Không có cuộc trò chuyện này")
    return kq


@router.post("/trochuyen")
def gui_tin(body: TinMoi, p: dict = Depends(can_dang_nhap)):
    """N0: `nen` = true → mở 01 lượt chạy nền, trả ngay {hoithoai_id, hoi, luot_id}, trang theo dõi qua luồng sự kiện.
    Không có `nen` → đường đồng bộ cũ, trả {hoithoai_id, hoi, tra_loi} như trước N0 (giữ người gọi cũ)."""
    try:
        if body.nen:
            return trochuyen.bat_luot(body.hoithoai_id, p["nguoidung_id"], body.noidung, mohinh_id=body.mohinh_id)
        return trochuyen.gui(body.hoithoai_id, p["nguoidung_id"], body.noidung, mohinh_id=body.mohinh_id)
    except trochuyen.ChoCapNhat as e:   # QĐ347 H1, QĐ352: giao diện hiện câu báo trong khung chat, giữ câu hỏi ở ô nhập
        return JSONResponse({"detail": str(e), "ma": "cho_capnhat"}, status_code=409)
    except trochuyen.DangTraLoi as e:   # N2: gửi trùng lượt là 409, không phải 404
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(404, str(e))


@router.get("/trochuyen/luot/{luot_id}/sukien")
async def su_kien_luot(luot_id: str, request: Request, tu: int = 0, p: dict = Depends(can_dang_nhap)):
    """Luồng sự kiện (SSE) của 01 lượt: bat_dau, cho, chu, buoc, lam_lai, xong, dung, loi. Có số thứ tự (`id:`), phát
    lại từ `tu` hoặc `Last-Event-ID`; 15 giây không có gì thì gửi 01 dòng giữ kết nối. Lượt của người khác: 404."""
    lt = luot.lay(luot_id, p["nguoidung_id"])
    if lt is None:
        raise HTTPException(404, "Câu trả lời này đã xong hoặc không còn chạy. Bạn mở lại hội thoại để xem")   # QĐ358 (N2 câu 2), không dấu chấm cuối
    try:
        tu = max(tu, int(request.headers.get("last-event-id") or 0))
    except ValueError:
        pass

    async def phat():
        da = tu
        while True:
            ds = await asyncio.to_thread(lt.doi, da, 15)
            if not ds:
                if lt.ket_thuc:
                    return
                yield ": giu\n\n"
                continue
            for ev in ds:
                da = ev["so"]
                yield f"id: {ev['so']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev["loai"] in luot.KET_THUC:
                    return

    return StreamingResponse(phat(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
