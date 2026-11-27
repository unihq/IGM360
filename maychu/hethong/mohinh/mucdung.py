"""Ngăn Cài đặt › Mức dùng (QĐ564 B, QĐ416; CDA phiếu 06 mục 13, PTD-20 mục 5.5). 0 bảng, 0 cột.

Số lấy từ G04 `nhatky_ai` (luc, nguon_ai_id, luong_vao, luong_ra, sotien, tien_ma) và G06 `nguon_ai` (% hạn mức gói từ
hãng, phí kỳ gói). Luật giờ (QĐ636):
- cửa sổ 05 giờ, đỉnh 60 ngày: theo THỜI ĐIỂM TUYỆT ĐỐI (không phụ thuộc múi);
- ô giờ của "24 giờ qua", "Giờ bận · 07 ngày": đổi `luc` sang múi đã chọn rồi mới lấy giờ (③) – không cắt chuỗi;
- tiền tháng: tháng theo ngày số liệu (②).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from maychu.dulieu import ketnoi, muigio

TRIEU = 1_000_000            # tiền lưu phần triệu (G04 sotien, G06 phi_ky)
NAM_GIO = timedelta(hours=5)
# Khung "Chưa đủ lượt để so": chỉ khi đỉnh 60 ngày = 0 (không lượt nào có token) (CPO NGUONG-AP; CDA phiếu 06 mục 13.5)


def _doc_g04(thumuc: Path | None, tu: datetime) -> list[tuple[datetime, str | None, int, int | None, str | None]]:
    cn = ketnoi.mo("Nhatky", thumuc)
    try:
        ds = cn.execute("SELECT luc, nguon_ai_id, coalesce(luong_vao, 0) + coalesce(luong_ra, 0), sotien, tien_ma"
                        " FROM nhatky_ai WHERE luc >= ?", (muigio.gio_luu(tu),)).fetchall()
    finally:
        cn.close()
    ra = []
    for luc, ng, tok, tien, ma in ds:
        try:
            t = datetime.fromisoformat(luc)
        except (TypeError, ValueError):
            continue
        if t.tzinfo is None:
            t = datetime.fromisoformat(muigio.gio_luu(t))   # không múi: coi là giờ lưu
        ra.append((t, ng, int(tok or 0), tien, ma))
    ra.sort(key=lambda x: x[0])
    return ra


def _dinh(ds: list, bay: datetime) -> tuple[int, datetime | None, datetime | None]:
    """Đỉnh = tổng token cửa sổ trượt 05 giờ nặng nhất trong 60 ngày, cộng theo giờ (giờ trống = 0) – CPO NGUONG-AP
    (CDA phiếu 06 mục 13.5). Giờ là giờ tuyệt đối (không phụ thuộc múi). Trả (đỉnh, đầu cửa sổ, cuối cửa sổ)."""
    o: dict[int, int] = {}
    for t, _, tok, _, _ in ds:
        if t <= bay:
            k = int(t.timestamp() // 3600)
            o[k] = o.get(k, 0) + tok
    best, bk = 0, None
    for k in o:   # cửa sổ 05 giờ chứa giờ k: bắt đầu từ k-4 tới k
        for d in range(k - 4, k + 1):
            v = sum(o.get(d + i, 0) for i in range(5))
            if v > best:
                best, bk = v, d
    if bk is None:
        return 0, None, None
    co = [k for k in range(bk, bk + 5) if o.get(k)]   # khoảng hiện: giờ đầu – giờ cuối có token trong cửa sổ
    return best, datetime.fromisoformat(muigio.tu_so_giay(co[0] * 3600)), datetime.fromisoformat(muigio.tu_so_giay((co[-1] + 1) * 3600))


def _goi(thumuc: Path | None) -> tuple[list[dict], int]:
    """% hạn mức gói từ hãng (G06) + tổng phí kỳ khai báo của gói quy ra tháng (phần triệu)."""
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        dong = cn.execute("SELECT id, ma, ten, hang, tyle_5gio, tyle_tuan, do_luc, datlai_5gio_luc, phi_ky, chuky, phi_tien_ma"
                          " FROM nguon_ai WHERE trangthai = 'dung' AND loai = 'goi' ORDER BY coalesce(uutien, 99), rowid").fetchall()
    finally:
        cn.close()
    goi, phi = [], 0
    for _id, ma, ten, hang, t5, tt, do, dl5, pk, ck, pma in dong:
        goi.append({"id": _id, "ma": ma, "ten": ten, "hang": hang, "tyle_5gio": t5, "tyle_tuan": tt, "do_luc": do,
                    "datlai_5gio_luc": dl5})
        if pk and (pma or "USD") == "USD":
            phi += pk // 12 if ck == "nam" else pk
    return goi, phi


def tong_hop(thumuc: Path | None = None, bay: datetime | None = None, nguon: str | None = None) -> dict:
    """Số cho ngăn Mức dùng. `nguon`: lọc biểu đồ "Token mỗi giờ" theo 01 nguồn (None = tất cả)."""
    bay = bay or muigio.bay()
    mui = muigio.chon(thumuc)
    ds = _doc_g04(thumuc, bay - timedelta(days=60))
    nay5 = sum(tok for t, _, tok, _, _ in ds if bay - NAM_GIO < t <= bay)
    dinh, ds_tu, ds_den = _dinh(ds, bay)
    # 24 ô giờ theo múi đã chọn (③): ô cuối là giờ hiện tại (tính tới lúc này)
    gio_nay = bay.astimezone(mui).replace(minute=0, second=0, microsecond=0)
    moc = [gio_nay - timedelta(hours=23 - i) for i in range(24)]
    tok_gio, cs_gio, nguon_co = [0] * 24, [], set()
    tu24 = moc[0]
    for t, ng, tok, _, _ in ds:
        if t < tu24 or t > bay:
            continue
        nguon_co.add(ng)
        if nguon and ng != nguon:
            continue
        i = int((t - tu24).total_seconds() // 3600)
        if 0 <= i < 24:
            tok_gio[i] += tok
    for i in range(24):
        het = bay if i == 23 else moc[i] + timedelta(hours=1)
        cs_gio.append(sum(tok for t, _, tok, _, _ in ds if het - NAM_GIO < t <= het))
    # giờ bận 07 ngày: trung bình token theo giờ trong ngày (múi đã chọn)
    ban = [0] * 24
    for t, _, tok, _, _ in ds:
        if bay - timedelta(days=7) < t <= bay:
            ban[t.astimezone(mui).hour] += tok
    ban = [round(x / 7) for x in ban]
    # tiền tháng theo ngày số liệu (②): khóa API (G04 sotien, USD) + phí kỳ gói
    thang = muigio.ngay_so_lieu(bay, thumuc).strftime("%Y-%m")
    tien_api = sum(tien or 0 for t, _, _, tien, ma in ds
                   if (ma or "USD") == "USD" and muigio.ngay_so_lieu(t, thumuc).strftime("%Y-%m") == thang)
    goi, phi_goi = _goi(thumuc)
    cn = ketnoi.mo("Viecnen", thumuc)
    try:
        ten_ng = dict(cn.execute("SELECT id, coalesce(ten, ma) FROM nguon_ai").fetchall())
    finally:
        cn.close()
    from maychu.hethong.caidat import thongso
    tran_thang = thongso.doc_mot("tran_tien_thang_khoa_api", None, thumuc)
    return {
        "bay": muigio.gio_luu(bay), "gio": [m.hour for m in moc], "luot_24h": sum(1 for t, *_ in ds if t > bay - timedelta(hours=24)),
        "du": dinh > 0, "cua_so": nay5, "cs_gio": cs_gio, "tok_gio": tok_gio, "ban": ban,
        "dinh": dinh, "dinh_tu": muigio.gio_luu(ds_tu) if ds_tu else None, "dinh_den": muigio.gio_luu(ds_den) if ds_den else None,
        "tran": thongso.doc_tran_5gio(thumuc), "goi": goi, "nguon_co": [{"id": x, "ten": ten_ng.get(x) or x} for x in sorted(x for x in nguon_co if x)], "nguon": nguon,
        "thang": int(thang[5:]), "tien_api": tien_api, "phi_goi": phi_goi, "tien_thang": tien_api + phi_goi,
        "tran_tien_thang": int(tran_thang) if tran_thang and str(tran_thang).isdigit() else None,
    }
