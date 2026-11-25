import re
from time import monotonic
from urllib.parse import urlsplit

from playwright.sync_api import (
    BrowserContext,
    Error,
    Page,
    Response,
    TimeoutError,
    sync_playwright,
)


TRANG_TRA_CUU_NGANH_NGHE = "https://dangkykinhdoanh.gov.vn/vn/pages/nganhnghe.aspx"
O_NHAP_MA_DOANH_NGHIEP = "#ctl00_ctl36_txtSearchTerm_entHD"
MAY_CHU_KET_QUA = "dichvuthongtin.dkkd.gov.vn"
DUONG_DAN_KET_QUA = "/inf/default.aspx"
O_TIM_KIEM_KET_QUA = "#ctl00_FldSearch"


def ghi_nhat_ky_phan_hoi_http(response: Response) -> None:
    """In các phản hồi điều hướng và lỗi giới hạn truy cập để dễ theo dõi."""
    request = response.request
    if request.resource_type == "document" or (
        request.resource_type in {"xhr", "fetch"} and response.status in {403, 429}
    ):
        url = urlsplit(response.url)
        print(
            f"HTTP {response.status} {request.method} {url.netloc}{url.path}",
            flush=True,
        )


def doi_trang_ket_qua(context: BrowserContext) -> Page:
    """Đợi trang Dịch vụ thông tin xuất hiện trong tab hiện tại hoặc tab mới."""
    han_cho = monotonic() + 30
    while monotonic() < han_cho:
        cac_trang = context.pages
        if not cac_trang:
            raise Error("Các tab của phiên tra cứu đã đóng.")

        for page in reversed(cac_trang):
            url = urlsplit(page.url)
            if (
                url.hostname == MAY_CHU_KET_QUA
                and url.path.lower() == DUONG_DAN_KET_QUA
            ):
                return page

        cac_trang[-1].wait_for_timeout(200)

    raise TimeoutError(
        "Không thấy trang Dịch vụ thông tin mở sau khi gửi mã doanh nghiệp."
    )


def chon_goi_y_doanh_nghiep(page: Page, ma_doanh_nghiep: str) -> None:
    """Tìm và chọn đúng doanh nghiệp trong danh sách gợi ý."""
    page.wait_for_load_state("domcontentloaded", timeout=30_000)
    o_tim_kiem = page.locator(O_TIM_KIEM_KET_QUA)
    o_tim_kiem.fill("", timeout=15_000)
    o_tim_kiem.press_sequentially(ma_doanh_nghiep, timeout=15_000)

    dung_ma_doanh_nghiep = re.compile(
        rf"Mã\s+số\s+doanh\s+nghiệp\s*:\s*{re.escape(ma_doanh_nghiep)}(?![\d-])",
        re.IGNORECASE,
    )
    goi_y = page.locator(".ui-autocomplete:visible").get_by_text(
        dung_ma_doanh_nghiep
    )
    print(
        f"Đang chờ gợi ý có mã doanh nghiệp {ma_doanh_nghiep}...",
        flush=True,
    )
    goi_y.click(timeout=20_000)
    print(
        f"Đã chọn doanh nghiệp có mã {ma_doanh_nghiep}.",
        flush=True,
    )


def doi_dong_cua_so_tra_cuu(context: BrowserContext) -> None:
    """Giữ phiên hoạt động cho đến khi người dùng đóng các tab tra cứu."""
    print("Đóng các tab tra cứu để quay lại menu.", flush=True)
    while context.pages:
        try:
            context.pages[0].wait_for_event("close", timeout=0)
        except Error:
            break


def tra_cuu_ma_doanh_nghiep(ma_doanh_nghiep: str) -> bool:
    """Mở Chrome, nhập mã doanh nghiệp và chọn đúng kết quả gợi ý."""
    if not isinstance(ma_doanh_nghiep, str) or not ma_doanh_nghiep.strip():
        raise ValueError("Mã doanh nghiệp phải là chuỗi không rỗng.")

    ma_doanh_nghiep = ma_doanh_nghiep.strip()
    tra_cuu_thanh_cong = False

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=False)
            try:
                context = browser.new_context()
                context.on("response", ghi_nhat_ky_phan_hoi_http)
                page = context.new_page()

                try:
                    response = page.goto(
                        TRANG_TRA_CUU_NGANH_NGHE,
                        wait_until="domcontentloaded",
                        timeout=30_000,
                    )
                    if response is not None and response.status >= 400:
                        print(
                            f"Trang tra cứu trả HTTP {response.status}. "
                            "Hãy kiểm tra nội dung trên Chrome."
                        )
                    else:
                        o_nhap_ma = page.locator(O_NHAP_MA_DOANH_NGHIEP)
                        o_nhap_ma.fill(ma_doanh_nghiep, timeout=15_000)
                        print("Đã điền mã doanh nghiệp. Đang nhấn Enter...", flush=True)
                        o_nhap_ma.press("Enter", timeout=15_000)
                        trang_ket_qua = doi_trang_ket_qua(context)
                        chon_goi_y_doanh_nghiep(trang_ket_qua, ma_doanh_nghiep)
                        tra_cuu_thanh_cong = True
                except TimeoutError as exc:
                    print(f"Hết thời gian chờ. Hãy kiểm tra cửa sổ Chrome.\n{exc}")
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
        ma_doanh_nghiep = input("Nhập mã doanh nghiệp cần tra cứu: ").strip()
        if ma_doanh_nghiep:
            tra_cuu_ma_doanh_nghiep(ma_doanh_nghiep)
        else:
            print("Mã doanh nghiệp không được để trống.")
    except (EOFError, KeyboardInterrupt):
        pass
