from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Error, sync_playwright


TRANG_TRA_CUU_WHOIS = "https://whois.inet.vn/whois"
O_NHAP_TEN_MIEN = 'input[type="text"][name="domain"][ng-model="query"]'


def chuan_hoa_ten_mien(website: str) -> str:
    """Lấy tên miền chuẩn từ tên miền hoặc địa chỉ website đầy đủ."""
    if not isinstance(website, str) or not website.strip():
        raise ValueError("Địa chỉ website phải là chuỗi không rỗng.")

    website = website.strip()
    url = website if "://" in website else f"//{website}"
    hostname = urlsplit(url).hostname
    if hostname is None:
        raise ValueError(f"Địa chỉ website không hợp lệ: {website}")

    return hostname.removeprefix("www.")


def doi_dong_cua_so_tra_cuu(context: BrowserContext) -> None:
    """Giữ phiên hoạt động cho đến khi người dùng đóng các tab tra cứu."""
    print("Đóng các tab tra cứu để quay lại menu.", flush=True)
    while context.pages:
        try:
            context.pages[0].wait_for_event("close", timeout=0)
        except Error:
            break


def tra_cuu_ten_mien(website: str) -> bool:
    """Chuẩn hóa website, mở Chrome và gửi yêu cầu tra cứu WHOIS."""
    ten_mien = chuan_hoa_ten_mien(website)
    tra_cuu_thanh_cong = False

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=False)
            try:
                context = browser.new_context()
                page = context.new_page()
                try:
                    response = page.goto(
                        TRANG_TRA_CUU_WHOIS,
                        wait_until="domcontentloaded",
                        timeout=30_000,
                    )
                    if response is not None and response.status >= 400:
                        print(f"Trang WHOIS trả HTTP {response.status}.")
                    else:
                        o_nhap_ten_mien = page.locator(O_NHAP_TEN_MIEN)
                        o_nhap_ten_mien.fill(ten_mien, timeout=15_000)
                        o_nhap_ten_mien.press("Enter", timeout=15_000)
                        print(
                            f"Đã gửi yêu cầu tra cứu tên miền {ten_mien}.",
                            flush=True,
                        )
                        tra_cuu_thanh_cong = True
                except Error as exc:
                    print(f"Playwright báo lỗi: {exc}")

                doi_dong_cua_so_tra_cuu(context)
            finally:
                if browser.is_connected():
                    browser.close()
    except Error as exc:
        print(f"Không thể khởi tạo phiên tra cứu trên Chrome: {exc}")
        return False

    return tra_cuu_thanh_cong


if __name__ == "__main__":
    try:
        website = input("Nhập tên miền cần tra cứu: ").strip()
        if website:
            tra_cuu_ten_mien(website)
        else:
            print("Tên miền không được để trống.")
    except (EOFError, KeyboardInterrupt):
        pass
