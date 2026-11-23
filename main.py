import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from search_mst import mo_trang_va_dien_mst
from search_web import mo_trang_va_dien_ten_mien


def doc_thong_tin(duong_dan: Path) -> dict:
    """Trích xuất thông tin từ một PDF hoặc từ các PDF trong thư mục hồ sơ."""
    from read_pdf import find_brand_pdf, find_brn_pdf, read_brand_pdf, read_brn_pdf

    if duong_dan.is_dir():
        pdf_brand = find_brand_pdf(duong_dan)
        pdf_brn = find_brn_pdf(duong_dan)
    else:
        pdf_brand = pdf_brn = duong_dan

    ket_qua = {
        "ten_cong_ty": None,
        "brandname": None,
        "linh_vuc": None,
        "canh_bao": [],
        "trang": None,
        "ma_cong_ty": None,
        "ten_mien": None,
    }

    if pdf_brand is None:
        ket_qua["canh_bao"].append("Không tìm thấy PDF khai báo brandname.")
    else:
        ket_qua.update(read_brand_pdf(pdf_brand))

    if pdf_brn is None:
        ket_qua["canh_bao"].append("Không tìm thấy PDF chứa mã công ty.")
    else:
        ket_qua.update(read_brn_pdf(pdf_brn))

    return ket_qua


def chon_tra_cuu(ket_qua: dict) -> int:
    """Dùng lại dữ liệu vừa đọc cho các lượt tra cứu đến khi chọn thoát."""
    print("\n1. Tra cứu mã công ty")
    print("2. Tra cứu tên miền WHOIS")
    print("0. Thoát")

    while True:
        lua_chon = input("Chọn 1, 2 hoặc 0: ").strip()
        if lua_chon == "0":
            return 0
        if lua_chon == "1":
            ma_cong_ty = ket_qua["ma_cong_ty"]
            if not ma_cong_ty:
                print("Không đọc được mã công ty từ PDF.")
                continue
            da_mo = mo_trang_va_dien_mst(ma_cong_ty)
        elif lua_chon == "2":
            website = ket_qua["ten_mien"] or ""
            url = website if "://" in website else f"//{website}"
            hostname = urlsplit(url).hostname
            if not hostname:
                print("Không đọc được tên miền từ PDF.")
                continue
            da_mo = mo_trang_va_dien_ten_mien(hostname.removeprefix("www."))
        else:
            print("Vui lòng nhập 1, 2 hoặc 0.")
            continue

        if not da_mo:
            print("Không mở được trình duyệt mặc định.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Đọc hồ sơ PDF và mở trang tra cứu.")
    parser.add_argument("duong_dan", nargs="?", help="Đường dẫn đến PDF hoặc thư mục hồ sơ")
    args = parser.parse_args()

    try:
        gia_tri = args.duong_dan or input("Nhập đường dẫn PDF hoặc thư mục hồ sơ: ")
        gia_tri = gia_tri.strip().strip('"').strip()
        if not gia_tri:
            parser.error("Bạn chưa nhập đường dẫn.")

        duong_dan = Path(gia_tri).expanduser()
        if not duong_dan.is_dir() and not (
            duong_dan.is_file() and duong_dan.suffix.lower() == ".pdf"
        ):
            parser.error(f"Không tìm thấy file PDF hoặc thư mục hợp lệ: {duong_dan}")

        ket_qua = doc_thong_tin(duong_dan)
        print(json.dumps(ket_qua, ensure_ascii=False, indent=2))
        return chon_tra_cuu(ket_qua)
    except ModuleNotFoundError as exc:
        print(f"Python đang thiếu thư viện {exc.name}. Hãy dùng môi trường OCR của dự án.", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
