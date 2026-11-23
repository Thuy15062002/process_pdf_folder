import argparse
import re
from time import monotonic
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Error, Page, Response, TimeoutError, sync_playwright


URL = "https://dangkykinhdoanh.gov.vn/vn/pages/nganhnghe.aspx"
O_MA_DOANH_NGHIEP = "#ctl00_ctl36_txtSearchTerm_entHD"
MAY_CHU_KET_QUA = "dichvuthongtin.dkkd.gov.vn"
DUONG_DAN_KET_QUA = "/inf/default.aspx"
O_TIM_KIEM_KET_QUA = "#ctl00_FldSearch"


def in_phan_hoi(response: Response) -> None:
    request = response.request
    if request.resource_type == "document" or (
        request.resource_type in {"xhr", "fetch"} and response.status in {403, 429}
    ):
        url = urlsplit(response.url)
        print(f"HTTP {response.status} {request.method} {url.netloc}{url.path}", flush=True)


def cho_trang_ket_qua(context: BrowserContext) -> Page:
    """Tìm trang Dịch vụ thông tin trong cùng tab hoặc tab mới."""
    han_cho = monotonic() + 30
    while monotonic() < han_cho:
        pages = context.pages
        if not pages:
            raise Error("Các tab của phiên thử đã đóng.")
        for page in reversed(pages):
            url = urlsplit(page.url)
            if url.hostname == MAY_CHU_KET_QUA and url.path.lower() == DUONG_DAN_KET_QUA:
                return page
        pages[-1].wait_for_timeout(200)
    raise TimeoutError("Không thấy trang Dịch vụ thông tin mở sau khi nhấn Enter.")


def chon_goi_y(page: Page, ma_so: str) -> None:
    page.wait_for_load_state("domcontentloaded", timeout=30_000)
    textbox = page.locator(O_TIM_KIEM_KET_QUA)
    textbox.fill("", timeout=15_000)
    textbox.press_sequentially(ma_so, timeout=15_000)

    dung_ma_so = re.compile(
        rf"Mã\s+số\s+doanh\s+nghiệp\s*:\s*{re.escape(ma_so)}(?![\d-])",
        re.IGNORECASE,
    )
    goi_y = page.locator(".ui-autocomplete:visible").get_by_text(dung_ma_so)
    print(f"Đang chờ gợi ý có mã doanh nghiệp {ma_so}...", flush=True)
    goi_y.click(timeout=20_000)
    print(f"Đã bấm vào gợi ý có mã doanh nghiệp {ma_so}.", flush=True)


def thu_tra_cuu(ma_so: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=False)
        try:
            context = browser.new_context()
            context.on("response", in_phan_hoi)
            page = context.new_page()

            try:
                response = page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
                if response is not None and response.status >= 400:
                    print(f"Trang ban đầu trả HTTP {response.status}. Hãy xem nội dung trên Chrome.")
                else:
                    textbox = page.locator(O_MA_DOANH_NGHIEP)
                    textbox.fill(ma_so, timeout=15_000)
                    print("Đã điền mã số. Đang nhấn Enter...", flush=True)
                    textbox.press("Enter", timeout=15_000)
                    trang_ket_qua = cho_trang_ket_qua(context)
                    chon_goi_y(trang_ket_qua, ma_so)
            except TimeoutError as exc:
                print(f"Hết thời gian chờ. Hãy kiểm tra cửa sổ Chrome.\n{exc}")
            except Error as exc:
                print(f"Playwright báo lỗi: {exc}")

            print("Đóng các tab của phiên thử để kết thúc.", flush=True)
            while context.pages:
                context.pages[0].wait_for_event("close", timeout=0)
        finally:
            if browser.is_connected():
                browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Thử tra cứu mã doanh nghiệp bằng Playwright.")
    parser.add_argument("ma_so", nargs="?", default="0305191655", help="Mã số doanh nghiệp cần thử")
    args = parser.parse_args()
    ma_so = args.ma_so.strip()
    if not ma_so:
        parser.error("Mã số doanh nghiệp không được để trống.")
    try:
        thu_tra_cuu(ma_so)
    except KeyboardInterrupt:
        pass
