"""Quét chung thông tin nhạy cảm trên các dòng thêm giữa `--goc` và `--dau` (QĐ259, Y44).

Chỉ chứa mẫu chung (địa chỉ IP công cộng, khoá riêng, mã truy cập, email), KHÔNG chứa giá trị bí mật nào: kho công khai.
Máy quét đầy đủ (mẫu riêng) vẫn chạy trên máy CTO, là 01 bước riêng trước khi đẩy nhánh. Chỉ dùng thư viện chuẩn Python.
"""
import argparse
import ipaddress
import re
import subprocess
import sys

MAU = (
    ("khoá riêng", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("mã GitHub", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("khoá API", re.compile(r"\bsk-(ant-|proj-)?[A-Za-z0-9_-]{20,}\b|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("mã Slack", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
)
MAU_IP = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])")
MAU_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EMAIL_DUOC = re.compile(r"@(users\.noreply\.github\.com|anthropic\.com|vidu\.invalid|example\.(com|org|net)|[a-z0-9.-]+\.invalid)$", re.I)


def ip_nhay_cam(chu: str) -> bool:
    try:
        ip = ipaddress.ip_address(chu)
    except ValueError:
        return False
    # is_global (thư viện chuẩn): False với địa chỉ nội bộ, máy này, dải dành cho tài liệu, dải dành riêng
    return ip.is_global and not ip.is_multicast


def quet(goc: str, dau: str) -> list[str]:
    loi, duong, so = [], "", 0
    out = subprocess.run(["git", "diff", "-U0", "--no-color", goc, dau], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", check=True).stdout
    for d in out.splitlines():
        if d.startswith("+++ "):
            duong = d[6:] if d.startswith("+++ b/") else d[4:]
        elif d.startswith("@@"):
            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", d)
            so = int(m.group(1)) if m else 0
        elif d.startswith("+") and not d.startswith("+++"):
            chu = d[1:]
            for ten, m in MAU:
                if m.search(chu):
                    loi.append(f"{ten}: {duong}:{so}")
            if any(ip_nhay_cam(x) for x in MAU_IP.findall(chu)):
                loi.append(f"địa chỉ IP công cộng: {duong}:{so}")
            if any(not EMAIL_DUOC.search(x) for x in MAU_EMAIL.findall(chu)):
                loi.append(f"email: {duong}:{so}")
            so += 1
    return loi


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--goc", required=True)
    p.add_argument("--dau", required=True)
    a = p.parse_args()
    loi = quet(a.goc, a.dau)
    for x in loi:   # chỉ in loại và vị trí, không in giá trị
        print(x)
    print(f"KẾT QUẢ: {'CHẶN' if loi else 'ĐẠT'} {len(loi)}")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
