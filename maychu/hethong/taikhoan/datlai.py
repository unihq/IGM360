"""Đặt lại mật khẩu quản trị trên VPS (QĐ89 điểm 01; web không có "Quên mật khẩu").

    docker compose exec igm360 python -m maychu.hethong.taikhoan.datlai [--tat-2lop]

Hỏi mật khẩu mới 02 lần (không hiện chữ), thu hồi mọi phiên cũ. --tat-2lop: tắt 02 lớp, lần đăng nhập
sau phần mềm bắt bật lại. Chưa có tài khoản nào thì hỏi thêm tên đăng nhập và tạo tài khoản chủ.
"""
import getpass
import json
import sys
from datetime import datetime

from maychu.dulieu import ketnoi, khoitao, maso
from maychu.dulieu.saoluu import MUIGIO_VN
from maychu.hethong.kekhoa import kho
from maychu.hethong.taikhoan import matkhau, phien


def chay(thamso=None, hoi=getpass.getpass, hoi_chu=input, thumuc=None) -> int:
    thamso = sys.argv[1:] if thamso is None else thamso
    khoitao.tao_het(thumuc)
    moi = hoi("Mật khẩu mới: ")
    loi = matkhau.loi_matkhau_moi(moi, hoi("Nhập lại mật khẩu mới: "))
    if loi:
        print(f"CHƯA ĐẶT LẠI: {loi}")
        return 1
    cn = ketnoi.mo("Baomat", thumuc)
    try:
        cn.execute("BEGIN IMMEDIATE")
        u = cn.execute("SELECT id, totp_khoa_id FROM nguoidung WHERE vaitro = 'chu' ORDER BY tao_luc LIMIT 1").fetchone()
        if not u:
            ten = hoi_chu("Chưa có tài khoản. Tên đăng nhập: ").strip()
            if not ten:
                cn.execute("ROLLBACK")
                print("CHƯA ĐẶT LẠI: chưa có tên đăng nhập")
                return 1
            bay = datetime.now(MUIGIO_VN).isoformat(timespec="seconds")
            ma = maso.tao()
            cn.execute("INSERT INTO nguoidung (id, ma, ten, hieuluc_tu, phienban, nguoi_khai, tao_luc, vaitro, module_xem)"
                       " VALUES (?, ?, ?, ?, 1, 'lenh_vps', ?, 'chu', ?)", (ma, ten, ten, bay[:10], bay, json.dumps(["tatca"])))
            u = (ma, None)
        cn.execute("UPDATE nguoidung SET matkhau_bam = ?, trangthai = 'dung' WHERE id = ?", (matkhau.bam(moi), u[0]))
        if "--tat-2lop" in thamso and u[1]:
            cn.execute("UPDATE nguoidung SET totp_khoa_id = NULL WHERE id = ?", (u[0],))
            kho.xoa(u[1], cn=cn)
        cn.execute("COMMIT")
    except Exception:
        cn.execute("ROLLBACK")
        raise
    finally:
        cn.close()
    so = phien.thu_hoi(u[0], thumuc=thumuc)
    print(f"ĐÃ ĐẶT LẠI MẬT KHẨU. Đã thu hồi {so:02d} phiên đăng nhập cũ."
          + (" Đã tắt 02 lớp, lần đăng nhập sau sẽ bật lại." if "--tat-2lop" in thamso else ""))
    return 0


if __name__ == "__main__":
    sys.exit(chay())
