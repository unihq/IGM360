"""Đường gọi cho màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt (ngày 04), két khoá và màn 11 Nguồn dữ liệu (ngày 05).

Bảo vệ: mã phiên ở cookie HttpOnly, SameSite=Strict, Secure; mọi lệnh ghi phải có header X-IGM360
(trang web khác không gửi được header này). Chặn đoán mật khẩu theo địa chỉ IP thật, phiên 30 ngày (QĐ90).
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from maychu.dulieu import ketnoi
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.kekhoa import kho
from maychu.hethong.giamsat import thongbao
from maychu.hethong.mohinh import congai, dangnhap_goi, danhmuc_mohinh, trochuyen
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


@router.post("/dangnhap")
def dang_nhap(body: DangNhap, request: Request):
    _an_toan(request)
    kq = nguoidung.buoc_matkhau(body.ten.strip(), body.matkhau, _ip(request))
    if "loi" in kq:
        _loi_dangnhap(kq)
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
    return {**nguoidung.thong_tin(p["nguoidung_id"]), "phien_id": p["phien_id"], "het_luc": p["het_luc"]}


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
    return {"cuacho": cuacho, "thongbao": tb["ds"], "so_moi": tb["so_moi"], "ket_ai": 0}


@router.post("/thongbao/dochet")
def doc_het_thongbao(p: dict = Depends(can_dang_nhap)):
    """Nút "Đọc hết": đặt mốc đọc = lúc bấm (QĐ165); không đổi trạng thái cảnh báo."""
    return {"moc_doc": thongso.dat_moc_doc(nguoi=p["nguoidung_id"])}


@router.get("/thongso")
def doc_thongso(p: dict = Depends(can_dang_nhap)):
    return thongso.doc_het()


@router.get("/thongso/{ten}/lichsu")
def lichsu_thongso(ten: str, p: dict = Depends(can_dang_nhap)):
    return thongso.lich_su(ten)


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


@router.post("/2lop/doimay/batdau")
def doi_may_batdau(body: MaCu, p: dict = Depends(can_dang_nhap)):
    """Bước 1: nhập mã trên máy cũ; đúng thì trả QR của khoá mới."""
    kq = nguoidung.kiem_ma_hien_tai(p["nguoidung_id"], body.ma)
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return nguoidung.bat_doi_may(p["nguoidung_id"])


@router.post("/2lop/doimay/xacnhan")
def doi_may_xacnhan(body: Ma2Lop, p: dict = Depends(can_dang_nhap)):
    kq = nguoidung.xac_nhan_doi_may(p["nguoidung_id"], body.ma_tam, body.ma)
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


@router.get("/capnhat")
def xem_capnhat(p: dict = Depends(can_dang_nhap)):
    return {**capnhat.kiem_tra(), "lichsu": capnhat.lich_su(), "so_viec_ai": capnhat.so_viec_ai_dangchay()}


@router.post("/capnhat/kiemtra")
def kiem_lai(p: dict = Depends(can_dang_nhap)):
    return {**capnhat.kiem_tra(bat_buoc=True), "lichsu": capnhat.lich_su(), "so_viec_ai": capnhat.so_viec_ai_dangchay()}


@router.post("/capnhat")
def cap_nhat(body: CheDoCapNhat, p: dict = Depends(can_dang_nhap)):
    kq = capnhat.yeu_cau(p["nguoidung_id"], body.che_do)
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


# ---- Két khoá (màn 09, ngày 05) ----
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
        return date.fromisoformat(han[:10]).isoformat()
    except ValueError:
        raise HTTPException(400, "Hạn khoá phải là ngày (năm-tháng-ngày)")


@router.get("/kekhoa")
def xem_kekhoa(p: dict = Depends(can_dang_nhap)):
    n = _songay()
    ds = kho.danh_sach(songay_baotruoc=n)
    dem = {k: sum(1 for x in ds if x["tinhtrang"] == k) for k in ("dung", "khong_han", "saphet", "hethan")}
    return {"ds": ds, "dem": dem, "tong": len(ds), "songay_baotruoc": n}


@router.post("/kekhoa")
def them_khoa(body: KhoaMoi, p: dict = Depends(can_dang_nhap)):
    if not body.giatri.strip() or not body.dichvu.strip() or body.dichvu in kho.NOIBO:
        raise HTTPException(400, "Thiếu tên dịch vụ hoặc giá trị khoá")
    ma = kho.cat(body.dichvu.strip(), body.giatri.strip(), han=_kiem_han(body.han), nguoi_nhap=p["nguoidung_id"])
    ghi_f04("kekhoa", "them", f"dịch vụ {body.dichvu.strip()}", nguoi_id=p["nguoidung_id"])
    return {"id": ma}


@router.post("/kekhoa/{ma}/doi")
def doi_khoa(ma: str, body: DoiKhoa, p: dict = Depends(can_dang_nhap)):
    if not body.giatri.strip() or ma not in {x["id"] for x in kho.danh_sach()}:
        raise HTTPException(400, "Không đổi được khoá này")
    kho.doi(ma, body.giatri.strip(), han=_kiem_han(body.han))
    ghi_f04("kekhoa", "doi", f"khoá {ma}", nguoi_id=p["nguoidung_id"])
    return {"id": ma}


@router.post("/kekhoa/{ma}/xoa")
def xoa_khoa(ma: str, p: dict = Depends(can_dang_nhap)):
    """Xoá hẳn (không lấy lại được); nguồn dùng khoá này ngừng lấy số."""
    if ma not in {x["id"] for x in kho.danh_sach()}:
        raise HTTPException(400, "Không xoá được khoá này")
    kho.xoa(ma)
    cn = ketnoi.mo("Ketnoi")
    try:
        so = cn.execute("UPDATE ketnoi SET trangthai_phien = 'mat_khoa', loi_cuoi = 'Khoá đã bị xoá ở Két khoá'"
                        " WHERE khoa_id = ?", (ma,)).rowcount
    finally:
        cn.close()
    ghi_f04("kekhoa", "xoa", f"khoá {ma}; {so:02d} nguồn ngừng lấy số", nguoi_id=p["nguoidung_id"])
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
        kq, ok = "Anh chưa cấp quyền cho IGM360 trên Google.", False
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
    return {"goi": goi, "nguon": dangnhap_goi.danh_sach(), "so_viec_ai_songsong": thongso.doc_mot("so_viec_ai_songsong"),
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
        return HTTPException(409, {"loi": kq["loi"], "trung_voi": kq["trung_voi"]})   # giao diện hiện dải báo trùng
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
    ghi_f04("mohinh", "go_goi", dangnhap_goi.nhan_dangnhap(goi, body.taikhoan), ketqua="loi" if "loi" in kq else "dat",
            nguoi_id=p["nguoidung_id"])
    if "loi" in kq:
        raise HTTPException(400, kq["loi"])
    return kq


@router.get("/mohinh/danhsach")
def ds_mohinh(p: dict = Depends(can_dang_nhap)):
    """Ô chọn mô hình màn 08 và hộp "Đổi" màn 13 dùng chung 01 danh sách (QĐ178, Z10)."""
    return danhmuc_mohinh.danh_sach()


class MacDinh(BaseModel):
    loai_viec: str
    mohinh_id: str | None = None
    nguon_id: str | None = None   # Z10c: mohinh_id trống + nguon_id = "mặc định của nguồn" đó


@router.post("/mohinh/macdinh")
def dat_macdinh(body: MacDinh, p: dict = Depends(can_dang_nhap)):
    try:
        kq = danhmuc_mohinh.dat_macdinh(body.loai_viec, body.mohinh_id, nguon_id=body.nguon_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    ghi_f04("mohinh", "doi_macdinh", f"{body.loai_viec}: {body.mohinh_id or ('mặc định của nguồn ' + body.nguon_id if body.nguon_id else 'theo ưu tiên')}",
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
    try:
        return trochuyen.gui(body.hoithoai_id, p["nguoidung_id"], body.noidung, mohinh_id=body.mohinh_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(404, str(e))
