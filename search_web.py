import argparse
import webbrowser
from urllib.parse import urlencode


WHOIS_URL = "https://whois.inet.vn/whois"


def mo_trang_va_dien_ten_mien(ten_mien: str) -> bool:
    """Mở WHOIS iNET với tên miền để extension điền vào ô tra cứu."""
    if not isinstance(ten_mien, str) or not ten_mien.strip():
        raise ValueError("Tên miền phải là chuỗi không rỗng.")

    query = urlencode({"domain": ten_mien.strip()})
    return webbrowser.open(f"{WHOIS_URL}?{query}", new=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mở trang tra cứu tên miền iNET.")
    parser.add_argument("ten_mien", nargs="?", default="aisec.com.vn")
    args = parser.parse_args()
    mo_trang_va_dien_ten_mien(args.ten_mien)
