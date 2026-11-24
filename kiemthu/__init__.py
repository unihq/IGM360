"""Khung dùng chung của bộ bài kiểm (CDA KT-Y46-4a, việc 10 Y46).

Móc kiểm (sys.addaudithook) ghi lại mọi lần ghi vào THƯ MỤC DỮ LIỆU MẶC ĐỊNH (`/dulieu`, nơi phần mềm ghi khi không đặt
IGM360_THUMUC_DULIEU): mở tệp để ghi, mở SQLite, tạo, đổi tên, xóa, chép. Bài kiểm phải dùng thư mục tạm; có lần ghi nào
thì bài cuối `kiemthu/test_zz_khong_ghi_dulieu.py` báo hỏng kèm tên bài và đường tệp. Lần ghi bị lỗi rồi bị try/except
nuốt (máy GitHub không ghi được /dulieu) vẫn được ghi lại, vì sự kiện có trước lúc hệ điều hành báo lỗi.
Móc chỉ ghi lại, không chặn, không đổi cách mã chạy.
"""
import os
import sys

DULIEU_MACDINH = os.path.normcase(os.path.abspath("/dulieu"))   # cùng giá trị mặc định của ketnoi.thumuc_dulieu()
GHI_DULIEU_THAT: list[tuple[str, str, str]] = []                  # (bài kiểm, sự kiện, đường tệp)
_TRONG = [False]
_GHI_CO = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_SU_KIEN = {   # sự kiện → vị trí các đối số là đường tệp
    "os.mkdir": (0,), "os.remove": (0,), "os.rmdir": (0,), "os.rename": (0, 1), "os.truncate": (0,), "os.chmod": (0,),
    "os.link": (0, 1), "os.symlink": (0, 1), "os.utime": (0,), "shutil.rmtree": (0,), "shutil.copyfile": (1,),
    "shutil.copytree": (1,), "shutil.move": (0, 1), "sqlite3.connect": (0,),
}


def _trong_dulieu(p) -> str | None:
    if isinstance(p, int) or p is None:
        return None
    try:
        s = os.fsdecode(os.fspath(p))
    except TypeError:
        return None
    if s.startswith("file:"):   # sqlite mở theo dạng địa chỉ tệp
        s = s[5:].split("?", 1)[0]
    if not s or s == ":memory:":
        return None
    a = os.path.normcase(os.path.abspath(s))
    return s if a == DULIEU_MACDINH or a.startswith(DULIEU_MACDINH + os.sep) else None


def _bai_dang_chay() -> str:
    import unittest
    f = sys._getframe(2)
    while f is not None:
        o = f.f_locals.get("self")
        if isinstance(o, unittest.TestCase):
            return o.id()
        f = f.f_back
    return f"{_DANG[0] or '(ngoài bài kiểm: lúc nạp tệp)'} (luồng nền)"


_DANG = [""]   # bài đang chạy, cho lần ghi từ luồng nền (không thấy bài trên ngăn xếp)


def _boc_run():
    import unittest
    goc = unittest.TestCase.run
    if getattr(goc, "_igm360", False):
        return

    def run(self, result=None):
        _DANG[0] = self.id()
        return goc(self, result)
    run._igm360 = True
    unittest.TestCase.run = run


def _moc(su_kien: str, doi_so: tuple) -> None:
    if _TRONG[0]:
        return
    if su_kien == "open":
        duong, che_do, co = (tuple(doi_so) + (None, None, None))[:3]
        ghi = (isinstance(che_do, str) and any(c in che_do for c in "wax+")) or (isinstance(co, int) and co & _GHI_CO)
        vi_tri = (0,) if ghi else ()
    else:
        vi_tri = _SU_KIEN.get(su_kien, ())
    if not vi_tri:
        return
    _TRONG[0] = True
    try:
        for i in vi_tri:
            if i < len(doi_so):
                s = _trong_dulieu(doi_so[i])
                if s:
                    GHI_DULIEU_THAT.append((_bai_dang_chay(), su_kien, s))
    except Exception:  # noqa: BLE001 - móc kiểm không được làm hỏng bài
        pass
    finally:
        _TRONG[0] = False


if not getattr(sys, "_igm360_moc_dulieu", False):
    sys.addaudithook(_moc)
    sys._igm360_moc_dulieu = True
    _boc_run()
