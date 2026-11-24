"""K4 (Y46, QĐ263; CDA KT-Y46-KH): kiểm bộ nâng công cụ AI trong ảnh thật, KHÔNG gọi npm, KHÔNG gọi hãng.

Chạy ở bước "Kiểm bộ nâng công cụ AI trong ảnh" (dongimage.yml): `docker exec -i -w /app <vùng chứa> python - < tệp này`.
Cách làm: chép CLI có sẵn trong ảnh (thư mục npm toàn cục) làm "bản nâng giả" vào /dulieu/cli/<gói>/<bản>/, chạy đúng
hàm `nangcli.nang` (bỏ qua bước npm bằng hàm chép), kiểm con trỏ đổi, `--version` chạy được qua đường mới mà cổng AI
dùng, rồi "Về bản trước" thì cổng AI về bản trong gói. Không đăng nhập gói nào (không gọi hãng, 0 hạn mức).
Bài kiểm `kiemthu/ban084/test_y46.py` gọi `chay()` với thư mục npm giả để kiểm chính tệp này trên máy GitHub.
Tệp không tên test_* nên bộ bài kiểm không tự chạy; không nhập gì từ `kiemthu` (ảnh không có thư mục này).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest import mock

GOC_NPM = Path("/usr/local/lib/node_modules")   # Dockerfile: npm install -g


def _chep(goc_nm: Path):
    """Thay `npm install --prefix <dich> <gói>@<bản>`: chép cả phạm vi gói (gồm gói nhị phân theo máy) đã có trong ảnh."""
    that = subprocess.run

    def chay(lenh, **kw):
        if Path(str(lenh[0])).name.split(".")[0] != "npm":
            return that(lenh, **kw)
        dich = Path(lenh[lenh.index("--prefix") + 1]) / "node_modules"
        ten = lenh[-1].rsplit("@", 1)[0]
        dich.mkdir(parents=True, exist_ok=True)
        shutil.copytree(goc_nm / ten.split("/")[0], dich / ten.split("/")[0], symlinks=True)
        pj = json.loads((dich / ten / "package.json").read_text(encoding="utf-8"))
        b = pj.get("bin") or {}
        b = b if isinstance(b, dict) else {ten.split("/")[-1]: b}
        (dich / ".bin").mkdir(exist_ok=True)
        for lenh_ten, rel in b.items():
            os.symlink(os.path.relpath(dich / ten / rel, dich / ".bin"), dich / ".bin" / lenh_ten)
        return subprocess.CompletedProcess(lenh, 0, "", "")
    return chay


def chay(goc_nm: Path = GOC_NPM, thumuc: Path | None = None, in_ra=print) -> int:
    import httpx
    from maychu.hethong.mohinh import dangnhap_goi, nangcli
    for bien in ("IGM360_CLAUDE_CLI", "IGM360_CODEX_CLI"):
        os.environ.pop(bien, None)   # cổng AI chọn đường theo con trỏ, như trên máy chủ
    loi = []
    for goi, c in nangcli.GOI_CLI.items():
        pj = goc_nm / c["npm"] / "package.json"
        if not pj.exists():
            loi.append(f"{goi}: ảnh không có {c['npm']}")
            continue
        ban = json.loads(pj.read_text(encoding="utf-8"))["version"]

        def tra(req, ban=ban):
            assert str(req.url).startswith(nangcli.REGISTRY)
            return httpx.Response(200, json={"dist-tags": {"latest": ban}, "time": {ban: "2020-01-01T00:00:00Z"},
                                             "versions": {ban: {"dist": {"unpackedSize": 0}}}})
        goc_cu = dict(nangcli._GOC)
        nangcli._GOC[goi] = "0.0.1"   # bản trong gói giả thấp hơn để chính bản trong ảnh thành "bản mới"
        try:
            with mock.patch.object(nangcli, "_uoc_giai_nen", return_value=0), \
                    mock.patch.object(dangnhap_goi, "trang_thai", return_value={"da_noi": False}):
                kq = nangcli.nang(goi, thumuc, ngay=True, client=httpx.Client(transport=httpx.MockTransport(tra)),
                                  chay=_chep(goc_nm))
                duong = dangnhap_goi._cli(goi)
                r = subprocess.run([duong, "--version"], capture_output=True, text=True, timeout=60)
                ve = nangcli.ve_ban_truoc(goi, thumuc)
                sau = dangnhap_goi._cli(goi)
        finally:
            nangcli._GOC.clear()
            nangcli._GOC.update(goc_cu)
        dat = (kq.get("kq") == "dat" and str(nangcli.thumuc_cli(thumuc)) in duong and r.returncode == 0
               and ban in (r.stdout + r.stderr) and ve.get("kq") == "ve" and sau == c["lenh"])
        in_ra(f"{'Đạt' if dat else 'CHƯA ĐẠT'} · {goi} {ban}: nâng {kq.get('kq')}, chạy qua bản nâng"
              f" {'được' if r.returncode == 0 else 'không được'}, về bản trước {ve.get('kq')}")
        if not dat:
            loi.append(f"{goi}: {kq} · {r.returncode} · {(r.stdout + r.stderr)[:200]} · {ve} · {sau}")
    for x in loi:
        in_ra("Lỗi: " + x)
    return 1 if loi else 0


def _chan_npm(su_kien, doi_so):
    """Trong ảnh: chặn hẳn mọi lần chạy npm (K4: không gọi npm)."""
    if su_kien == "subprocess.Popen":
        a = doi_so[1] if len(doi_so) > 1 else None
        a = a[0] if isinstance(a, (list, tuple)) and a else a
        if not isinstance(a, (str, bytes, os.PathLike)):
            return
        s = os.fsdecode(a).strip()
        s = s[1:].split('"', 1)[0] if s.startswith('"') else s.split(" ", 1)[0]   # dòng lệnh đã ghép: lấy tên lệnh đầu
        if Path(s).name.split(".")[0] in ("npm", "npx"):
            raise RuntimeError("K4: không được gọi npm")


if __name__ == "__main__":
    sys.path.insert(0, "/app")
    sys.addaudithook(_chan_npm)
    sys.exit(chay())
