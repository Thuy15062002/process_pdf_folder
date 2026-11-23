import webbrowser
from urllib.parse import quote


def mo_trang_va_dien_mst(
    ma_so_thue: str,
    url: str = "https://dangkykinhdoanh.gov.vn/vn/pages/nganhnghe.aspx",
) -> bool:
    """Mo trang tra cuu; extension se dien MST tu URL fragment."""
    if not isinstance(ma_so_thue, str) or not ma_so_thue.strip():
        raise ValueError("Ma so thue phai la chuoi khong rong.")

    mst_fragment = quote(ma_so_thue.strip(), safe="")
    print("Extension se tu dien MST. Ban chi can nhan Enter.")
    return webbrowser.open(f"{url}#mst={mst_fragment}", new=2)


if __name__ == "__main__":
    mo_trang_va_dien_mst("0305191655")
