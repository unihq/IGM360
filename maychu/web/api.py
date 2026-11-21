"""Đường gọi cho màn 01 Đăng nhập, 02 Khung và menu, 09 Cài đặt (ngày 04 GĐ 1, bản vẽ đợt 1 QĐ88).

Bảo vệ: mã phiên ở cookie HttpOnly, SameSite=Strict, Secure; mọi lệnh ghi phải có header X-IGM360
(trang web khác không gửi được header này). Chặn đoán mật khẩu theo địa chỉ IP thật, phiên 30 ngày (QĐ90).
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from maychu.dulieu import ketnoi
from maychu.hethong import capnhat
from maychu.hethong.caidat import thongso
from maychu.hethong.taikhoan import nguoidung, phien

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
def dem_so(p: dict = Depends(can_dang_nhap)):
    """Số trên menu và chuông (màn 02)."""
    cn = ketnoi.mo("Dulieu_Chinh")
    try:
        cuacho = cn.execute("SELECT count(*) FROM cuacho WHERE trangthai IN ('moi', 'choduyet')").fetchone()[0]
        cb = cn.execute("SELECT id, khoa_chongtrung, nguong, giatri, tao_luc FROM canhbao WHERE trangthai = 'moi'"
                        " ORDER BY tao_luc DESC LIMIT 20").fetchall()
    finally:
        cn.close()
    ds = []
    for ma, khoa, nguong, giatri, luc in cb:
        if khoa == "swap_vuot_nguong":
            ds.append({"id": ma, "chu": f"Máy chủ dùng tệp hoán đổi {giatri} MB, quá {nguong} MB", "luc": luc, "di": "09"})
        else:
            ds.append({"id": ma, "chu": "Có cảnh báo mới", "luc": luc, "di": "03"})
    return {"cuacho": cuacho, "canhbao": ds, "ket_ai": 0}


@router.get("/thongso")
def doc_thongso(p: dict = Depends(can_dang_nhap)):
    return thongso.doc_het()


@router.get("/thongso/{ten}/lichsu")
def lichsu_thongso(ten: str, p: dict = Depends(can_dang_nhap)):
    return thongso.lich_su(ten)


@router.post("/thongso/{ten}")
def sua_thongso(ten: str, body: SuaThongSo, p: dict = Depends(can_dang_nhap)):
    kq = thongso.dat(ten, body.giatri, body.hieuluc_tu, body.ghichu, nguoi=p["ten_dangnhap"])
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
