import argparse

from playwright.sync_api import Error, sync_playwright

from search_web import WHOIS_URL


O_TEN_MIEN = 'input[type="text"][name="domain"][ng-model="query"]'


def thu_tra_cuu_ten_mien(ten_mien: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            try:
                response = page.goto(WHOIS_URL, wait_until="domcontentloaded", timeout=30_000)
                if response is not None and response.status >= 400:
                    print(f"Trang WHOIS trả HTTP {response.status}.")
                else:
                    textbox = page.locator(O_TEN_MIEN)
                    textbox.fill(ten_mien, timeout=15_000)
                    textbox.press("Enter", timeout=15_000)
                    print(f"Đã điền và nhấn Enter cho tên miền {ten_mien}.")
            except Error as exc:
                print(f"Playwright báo lỗi: {exc}")

            print("Đóng các tab của phiên thử để kết thúc.", flush=True)
            while context.pages:
                context.pages[0].wait_for_event("close", timeout=0)
        finally:
            if browser.is_connected():
                browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thử tra cứu tên miền iNET WHOIS bằng Playwright.")
    parser.add_argument("ten_mien", nargs="?", default="aisec.com.vn", help="Tên miền cần tra cứu")
    args = parser.parse_args()
    ten_mien = args.ten_mien.strip()
    if not ten_mien:
        parser.error("Tên miền không được để trống.")
    try:
        thu_tra_cuu_ten_mien(ten_mien)
    except KeyboardInterrupt:
        pass
