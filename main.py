import json
import sys
from pathlib import Path

from search_mst import tra_cuu_ma_doanh_nghiep
from search_web import tra_cuu_ten_mien


def trich_xuat_thong_tin_ho_so(duong_dan: Path) -> dict:
    """Trích xuất thông tin từ một PDF hoặc các PDF trong thư mục hồ sơ."""
    from read_pdf import find_brand_pdf, find_brn_pdf, read_brand_pdf, read_brn_pdf

    if duong_dan.is_dir():
        pdf_brandname = find_brand_pdf(duong_dan)
        pdf_doanh_nghiep = find_brn_pdf(duong_dan)
    else:
        pdf_brandname = pdf_doanh_nghiep = duong_dan

    thong_tin_ho_so = {
        "ten_cong_ty": None,
        "brandname": None,
        "linh_vuc": None,
        "canh_bao": [],
        "trang": None,
        "ma_cong_ty": None,
        "ten_mien": None,
    }

    if pdf_brandname is None:
        thong_tin_ho_so["canh_bao"].append(
            "Không tìm thấy PDF khai báo brandname."
        )
    else:
        thong_tin_ho_so.update(read_brand_pdf(pdf_brandname))

    if pdf_doanh_nghiep is None:
        thong_tin_ho_so["canh_bao"].append(
            "Không tìm thấy PDF chứa mã doanh nghiệp."
        )
    else:
        thong_tin_ho_so.update(read_brn_pdf(pdf_doanh_nghiep))

    return thong_tin_ho_so


def hien_thi_menu_tra_cuu(thong_tin_ho_so: dict) -> int:
    """Cho phép tra cứu nhiều lần bằng dữ liệu đã trích xuất từ hồ sơ."""
    print("\n1. Tra cứu mã doanh nghiệp")
    print("2. Tra cứu tên miền WHOIS")
    print("0. Thoát")

    while True:
        lua_chon = input("Chọn 1, 2 hoặc 0: ").strip()
        if lua_chon == "0":
            return 0

        if lua_chon == "1":
            ma_doanh_nghiep = thong_tin_ho_so["ma_cong_ty"]
            if not ma_doanh_nghiep:
                print("Không đọc được mã doanh nghiệp từ PDF.")
                continue
            tra_cuu_thanh_cong = tra_cuu_ma_doanh_nghiep(ma_doanh_nghiep)
        elif lua_chon == "2":
            website = thong_tin_ho_so["ten_mien"] or ""
            if not website:
                print("Không đọc được tên miền từ PDF.")
                continue
            tra_cuu_thanh_cong = tra_cuu_ten_mien(website)
        else:
            print("Vui lòng nhập 1, 2 hoặc 0.")
            continue

        if not tra_cuu_thanh_cong:
            print("Không thể hoàn tất thao tác tra cứu.", file=sys.stderr)


def nhap_duong_dan_ho_so() -> Path:
    """Yêu cầu nhập lại cho đến khi nhận được PDF hoặc thư mục hợp lệ."""
    while True:
        gia_tri_duong_dan = input("Nhập đường dẫn PDF hoặc thư mục hồ sơ: ")
        gia_tri_duong_dan = gia_tri_duong_dan.strip().strip('"').strip()

        if not gia_tri_duong_dan:
            print("Bạn chưa nhập đường dẫn.", file=sys.stderr)
            continue

        duong_dan = Path(gia_tri_duong_dan).expanduser()
        if duong_dan.is_dir() or (
            duong_dan.is_file() and duong_dan.suffix.lower() == ".pdf"
        ):
            return duong_dan

        print(
            f"Không tìm thấy file PDF hoặc thư mục hợp lệ: {duong_dan}",
            file=sys.stderr,
        )


def main() -> int:
    try:
        duong_dan = nhap_duong_dan_ho_so()
        thong_tin_ho_so = trich_xuat_thong_tin_ho_so(duong_dan)
        print(json.dumps(thong_tin_ho_so, ensure_ascii=False, indent=2))
        return hien_thi_menu_tra_cuu(thong_tin_ho_so)
    except ModuleNotFoundError as exc:
        print(
            f"Python đang thiếu thư viện {exc.name}. "
            "Hãy dùng môi trường OCR của dự án.",
            file=sys.stderr,
        )
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
