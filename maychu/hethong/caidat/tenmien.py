"""Tên miền riêng đổi được trên web – QĐ634 (B), chữ QĐ650, QĐ651; CDA PTD-20 mục 2–4.

Cách chạy (học theo mẫu tham khảo ở CDA PTD-20 mục 2.2, viết riêng cho IGM360):
- Cổng HTTPS (Caddy) có 02 khối: khối tên gốc `{$DOMAIN_NAME}` lấy từ tệp .env (LUÔN chạy, đường dự phòng – không tự
  khóa mình ra ngoài) và khối On-Demand TLS cho tên riêng. Trước khi xin chứng chỉ cho 01 tên lạ, Caddy hỏi
  `http://igm360:8360/tls-check?domain=<tên>` (đi thẳng trong mạng nội bộ Docker, không qua đường công khai).
- `/tls-check` chỉ trả 200 khi tên Caddy hỏi = tên riêng đã lưu VÀ lời hỏi không mang tiêu đề chuyển tiếp
  (`X-Forwarded-For`…): mọi lời đi qua đường công khai của Caddy đều có tiêu đề này (`reverse_proxy` luôn đặt), lời
  hỏi `ask` của Caddy thì không. Không lọc được bằng địa chỉ IP vì cả 02 loại lời đều tới từ IP của cổng HTTPS
  (CDA PTD-20 mục 4 điểm 1). Khối công khai của Caddy còn trả 404 cho `/tls-check*` (lớp phụ).
- Tên gốc đọc từ biến `IGM360_TEN_GOC` (tệp compose mới đặt = DOMAIN_NAME). Thiếu biến = máy chủ chưa chạy lệnh nâng
  cấu hình: phần đổi tên miền "chưa bật", tên gốc vẫn chạy.
- Kiểm DNS: `getaddrinfo` trong luồng riêng có hạn giờ (không chặn máy chủ – bài học CDA PTD-20 mục 4 điểm 2a), so TẬP
  địa chỉ của tên riêng với tên gốc, chỉ cảnh báo, không gọi dịch vụ ngoài (QĐ634).
- Kiểm HTTPS: mở kết nối TLS tới cổng HTTPS trong mạng nội bộ (`gateway:443`) với SNI = tên cần đọc, kiểm chuỗi chứng
  chỉ như trình duyệt, đọc ngày hết hạn. Lần đầu đọc tên riêng cũng là lúc Caddy xin chứng chỉ (On-Demand).
"""
import os
import re
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, TimeoutError as HetGio
from pathlib import Path

from maychu.dulieu import muigio

TEN = "tenmien_rieng"            # 01 thông số P01 (QĐ634), trống = chỉ tên gốc
BIEN_GOC = "IGM360_TEN_GOC"      # tệp compose mới đặt; thiếu = chưa nâng cấu hình
BIEN_CONG = "IGM360_CONG_HTTPS"  # tên dịch vụ cổng HTTPS trong mạng nội bộ (mặc định "gateway" theo docker-compose.yml)
HAN_DNS = 5                      # giây chờ 01 lần dò DNS
HAN_HTTPS = 25                   # giây chờ 01 lần đọc chứng chỉ (lần đầu Caddy xin chứng chỉ ngay trong lần bắt tay)
TIEUDE_CHUYENTIEP = ("x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "forwarded")

# Dạng tên miền: các nhãn a-z 0-9 gạch nối, đuôi chữ 02–63 ký tự (địa chỉ IP không hợp lệ)
_DANG = re.compile(r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_LUONG = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tenmien_dns")      # dò DNS
_LUONG_DONG = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tenmien_dong")  # 02 dòng bảng kiểm song song

# Chữ máy chủ trả về. Dòng có "TẠM" chưa có trong bảng chữ anh duyệt (QĐ648: hỏi khi dựng ngăn Chung).
CHU_TENMIEN = {
    "chua_bat": "Chưa bật đổi tên miền: máy chủ cần chạy 01 lệnh nâng cấu hình. Tên gốc vẫn chạy.",   # QĐ651
    "sai_dang": "Tên miền chưa đúng dạng.",                                                      # TẠM
    "trung_goc": "Tên này đang là tên gốc, không cần thêm.",                                       # TẠM
}


def chuan(ten: str | None) -> str:
    """Chuẩn hóa: bỏ http(s)://, đường dẫn, cổng, dấu chấm cuối; chữ thường; tên có dấu tiếng
    Việt đổi sang dạng quốc tế (xn--)."""
    d = (ten or "").strip().lower()
    for dau in ("https://", "http://"):
        if d.startswith(dau):
            d = d[len(dau):]
    d = d.split("/")[0].split("?")[0].split(":")[0].strip().strip(".")
    if d and not d.isascii():
        try:
            d = d.encode("idna").decode("ascii")
        except UnicodeError:
            return d
    return d


def dung_dang(ten: str) -> bool:
    return bool(_DANG.match(ten or ""))


def ten_goc(host: str | None = None) -> str:
    """Tên gốc: biến `IGM360_TEN_GOC`; chưa nâng cấu hình thì lấy tên trên thanh địa chỉ (tiêu đề Host) để hiện."""
    return chuan(os.environ.get(BIEN_GOC)) or chuan(host)


def da_bat() -> bool:
    """Phần đổi tên miền chỉ bật khi tệp compose đã nâng (có khối On-Demand + biến tên gốc)."""
    return bool(chuan(os.environ.get(BIEN_GOC)))


def ten_rieng(thumuc: Path | None = None) -> str:
    from maychu.hethong.caidat import thongso
    return chuan(thongso.doc_mot(TEN, "", thumuc))


def kiem_luu(ten: str) -> str | None:
    """Kiểm trước khi lưu (đã chuẩn hóa). Trống = bỏ tên riêng, luôn được. Trả câu lỗi hoặc None."""
    if not da_bat():
        return CHU_TENMIEN["chua_bat"]
    if not ten:
        return None
    if not dung_dang(ten):
        return CHU_TENMIEN["sai_dang"]
    if ten == ten_goc():
        return CHU_TENMIEN["trung_goc"]
    return None


def co_chuyentiep(tieude) -> bool:
    """Lời hỏi đi qua đường công khai của Caddy (có tiêu đề chuyển tiếp)."""
    return any(tieude.get(k) for k in TIEUDE_CHUYENTIEP)


def cho_cap(ten: str | None, tieude, thumuc: Path | None = None) -> bool:
    """`/tls-check`: True (trả 200) chỉ khi lời hỏi không qua đường công khai VÀ tên = tên riêng đã lưu."""
    if co_chuyentiep(tieude):
        return False
    try:
        rieng = ten_rieng(thumuc)
    except Exception:   # noqa: BLE001 - đọc thông số lỗi thì không cho cấp (đóng an toàn)
        return False
    return bool(rieng) and chuan(ten) == rieng


# ---------------- Kiểm DNS (chỉ cảnh báo) ----------------
def _dia_chi(ten: str) -> set[str]:
    return {a[4][0] for a in socket.getaddrinfo(ten, 443, proto=socket.IPPROTO_TCP)}


def _dia_chi_han(ten: str, han: float) -> set[str]:
    return _LUONG.submit(_dia_chi, ten).result(timeout=han)


def kiem_dns(moi: str, goc: str, han: float = HAN_DNS) -> str:
    """"dung": mọi địa chỉ của tên mới nằm trong tập địa chỉ của tên gốc · "chua": tên mới chưa có bản ghi hoặc trỏ nơi
    khác · "khong_ro": dò không xong trong hạn giờ hoặc lỗi mạng. Chỉ để cảnh báo, không chặn lưu (CDA PTD-20 mục 4
    điểm 2: tên đi qua dịch vụ trung gian cho địa chỉ khác dù đúng; DNS mới đổi có độ trễ)."""
    khong_co = {socket.EAI_NONAME, getattr(socket, "EAI_NODATA", socket.EAI_NONAME)}
    try:
        ip_moi = _dia_chi_han(moi, han)
    except socket.gaierror as e:
        return "chua" if e.errno in khong_co else "khong_ro"
    except (HetGio, OSError):
        return "khong_ro"
    try:
        ip_goc = _dia_chi_han(goc, han)
    except (HetGio, OSError):
        return "khong_ro"
    return "dung" if ip_moi and ip_moi <= ip_goc else "chua"


# ---------------- Kiểm HTTPS (hạn chứng chỉ) ----------------
def doc_han(ten: str, han: float = HAN_HTTPS) -> str | None:
    """Ngày hết hạn chứng chỉ (YYYY-MM-DD, theo múi đã chọn ③) mà cổng HTTPS đang trả cho `ten`; None = chưa đọc được
    (chưa cấp, chuỗi chứng chỉ không hợp lệ, không kết nối được)."""
    may = os.environ.get(BIEN_CONG, "gateway")
    try:
        with socket.create_connection((may, 443), timeout=han) as s:
            with ssl.create_default_context().wrap_socket(s, server_hostname=ten) as t:
                het = t.getpeercert().get("notAfter")
        return muigio.ngay_cua(muigio.tu_so_giay(ssl.cert_time_to_seconds(het))) if het else None
    except (OSError, ValueError):   # ssl.SSLError là OSError
        return None


def _mot_dong(ten: str, la_goc: bool, goc: str) -> dict:
    dns = "dung" if la_goc else kiem_dns(ten, goc)
    den = doc_han(ten)
    if den:
        https = "chay"
    elif dns != "dung":
        https = "cho_dns"     # QĐ650 "Chờ DNS"
    else:
        https = "chua_doc"    # QĐ650 "Chưa đọc được"
    return {"ten": ten, "dns": dns, "https": https, "den": den}


def kiem(host: str | None = None, thumuc: Path | None = None) -> dict:
    """Bảng tên miền (QĐ651 "Địa chỉ · DNS · HTTPS", dòng "Tên gốc · Tên riêng"). 02 dòng kiểm song song."""
    goc, rieng = ten_goc(host), ten_rieng(thumuc)
    viec = {"goc": _LUONG_DONG.submit(_mot_dong, goc, True, goc) if goc else None,
            "rieng": _LUONG_DONG.submit(_mot_dong, rieng, False, goc) if rieng else None}
    kq = {}
    for k, v in viec.items():
        try:
            kq[k] = v.result(timeout=HAN_DNS * 2 + HAN_HTTPS + 5) if v else None
        except HetGio:
            ten = goc if k == "goc" else rieng
            kq[k] = {"ten": ten, "dns": "dung" if k == "goc" else "khong_ro", "https": "chua_doc", "den": None}
    return {"bat": da_bat(), **kq}
