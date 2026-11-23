import json
import re
import unicodedata
from pathlib import Path

import cv2
import pymupdf
import numpy as np
import pytesseract
from pytesseract import Output


# Sửa đường dẫn nếu bạn cài Tesseract ở vị trí khác.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ##################################
# DEBUG_DIR = Path(__file__).resolve().parent / "debug_images"
# DEBUG_DIR.mkdir(parents=True, exist_ok=True)


# def save_debug_image(filename, img, rgb=False):
#     """Lưu ảnh kiểm tra, hỗ trợ đường dẫn tiếng Việt trên Windows."""
#     if img.size == 0:
#         print(f"Ảnh rỗng: {filename}")
#         return

#     # Ảnh màu từ PDF là RGB; OpenCV lưu ảnh theo BGR.
#     if rgb:
#         img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

#     success, encoded = cv2.imencode(".png", img)

#     if not success:
#         raise RuntimeError(f"Không mã hóa được ảnh: {filename}")
##################################



def bo_dau(text):
    """Bỏ dấu để tìm nhãn; không dùng bản này làm dữ liệu đầu ra."""
    # text = unicodedata.normalize("NFC", text) # Ghép chữ và dấu thành ký tự hoàn chỉnh khi có thể	A + dấu mũ → Â
    text = text.replace("đ", "d").replace("Đ", "D") # chữ đ ko tách đc thành d và dấu

    return "".join(
        c
        for c in unicodedata.normalize("NFD", text) # Tách ký tự thành chữ gốc và dấu	Â → A + dấu mũ
        if not unicodedata.combining(c)
    )


def pdf_to_image(pdf_path, page_number=1): # mặc định đọc từ trang đầu
    """Chuyển một trang PDF thành ảnh ở 300 DPI."""
    with pymupdf.open(pdf_path) as doc:
        if not 1 <= page_number <= len(doc):
            raise ValueError(
                f"Trang phải nằm trong khoảng 1 đến {len(doc)}"
            )

        page = doc[page_number - 1]

        pix = page.get_pixmap(
            dpi=300,
            colorspace=pymupdf.csRGB,
            alpha=False,
        ) # vẽ nội dung trang pdf thành 1 ảnh gồm nhiều pixel

        image = np.frombuffer(
            pix.samples, dtype=np.uint8
        ).reshape(pix.height, pix.width, 3).copy()

# # Bước 1: Đọc dữ liệu pixel thành mảng một chiều.
# pixels = np.frombuffer(pix.samples, dtype=np.uint8)

# # Bước 2: Sắp xếp thành chiều cao × chiều rộng × 3 kênh màu.
# image = pixels.reshape(pix.height, pix.width, 3)

# # Bước 3: Tạo bản sao sở hữu dữ liệu riêng, có thể chỉnh sửa.
# image = image.copy()
    return image


def ocr_lines(image):
    """OCR và gom từ thành dòng, giữ tọa độ từng dòng."""
    data = pytesseract.image_to_data(
        image,
        lang="vie+eng",
        config="--psm 6",
        output_type=Output.DICT, # trả kết quả thành 1 dict
        timeout=180,
    )

    groups = {}

    for i, word in enumerate(data["text"]):
        word = unicodedata.normalize("NFC", word).strip() # text = "Te\u0302n công ty" -> e + dấu mũ riêng

        if not word:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]

        if key not in groups: # key là bộ nhận diện (dòng, đoạn, trang), mỗi dòng thay đổi lại có thêm 1 groups[key]
            groups[key] = {
                "words": [],
                "top": y,
                "bottom": y + h,
            }

        groups[key]["words"].append((x, word)) # [(220, "báo:"), (40, "Brandname"), (160, "khai"), (300, "AIS")]___(220, "báo:") là 1 tuple
        groups[key]["top"] = min(groups[key]["top"], y)
        groups[key]["bottom"] = max(
            groups[key]["bottom"], y + h
        ) # mỗi khi gặp 1 từ mới thì sẽ cập nhật vào dòng đã có, cập nhật lại mép trên và dưới nếu có sai lệch

    lines = []

    for group in groups.values(): # groups.values()trả về từng dòng trong pdf
        group["text"] = " ".join(
            word for _, word in sorted(group.pop("words")) # hàm sort sẽ sắp xếp theo giá trị x trong tuple biểu diễn từng từ
        )
        lines.append(group)

    return sorted(lines, key=lambda item: item["top"]) # các dòng với nhau


def extract_company(text):
    """
    Theo câu trong mẫu:
    '... cán bộ công nhân viên CÔNG TY ... nhận được tin nhắn ...'

    Không lấy công ty V2M ở dòng 'Kính gửi'.
    """
    text = unicodedata.normalize("NFC", text)
    flat = re.sub(r"\s+", " ", text).strip()
    plain = bo_dau(flat).lower()

    pattern = (
        # r"(?:can bo\s+)?cong nhan vien\s+"
        # r"(?P<company>cong ty\b.+?)"
        # r"\s+nhan duoc\s+tin nhan"
        r"can\sbo\scong\snhan\svien\s"
        r"(?P<company>.+?)"
        r"\snhan\sduoc\stin\snhan"
    ) # chữ r ở trc dấu là để giữ nguyên dấu /

    match = re.search(pattern, plain)

    if not match:
        return None

    # Lấy từ bản gốc để giữ nguyên dấu tiếng Việt.
    start, end = match.span("company")
    return flat[start:end].strip(" ,.;:")# strip(" ,.;:"): loại bỏ các ký tự này ở đầu và cuối


def extract_brandname(text):
    """Tìm dòng 'Brandname khai báo: AIS'."""
    text = unicodedata.normalize("NFC", text)
    flat = re.sub(r"\s+", " ", text).strip()
    plain = bo_dau(flat).lower()

    pattern = (
        r"\bbrandname\s+(?:khai\s+bao|xin\s+cap)\s*:?\s*"
        r"(?P<brandname>.+?)"
        r"(?=\s+(?:loai\s+tin\s+nhan\s*:|nham\s+tao\b))"
    )
    match = re.search(pattern, plain)

    if not match:
        return None

    # Lấy từ bản gốc để giữ nguyên dấu tiếng Việt.
    start, end = match.span("brandname")
    return flat[start:end].strip(" ,.;:")# strip(" ,.;:"): loại bỏ các ký tự này ở đầu và cuối


def extract_fields(image, lines): # line là danh sách các dòng do ocr_lines(image) trả về
    """
    Tìm checkbox giữa 'Lĩnh vực' và 'Nhà mạng'.
    Đọc nội dung bên phải những ô có dấu tích.

    Ngưỡng tỷ lệ mực là kinh nghiệm ban đầu,
    cần hiệu chỉnh theo chất lượng scan thực tế.
    """
    warnings = []
    height, width = image.shape[:2] # lấy index 0,1

    start = next(
        (
            line
            for line in lines
            if bo_dau(line["text"]).lower().strip().startswith(
                "linh vuc:"
            )
        ),
        None,
    ) # startswith tìm dòng có ký tự đầu tiên là linh vuc
      # next(..., None): lấy dòng đầu tiên thỏa mãn điều kiện, nếu ko tìm đc thì trả về None

    if start is None:
        return None, [], ["Không tìm thấy nhãn Lĩnh vực"]

    end = next(
        (
            line
            for line in lines
            if line["top"] > start["bottom"]
            and bo_dau(line["text"]).lower().strip().startswith(
                "nha mang:"
            )
        ),
        None,
    )

    if end is None:
        return None, [], ["Không tìm thấy nhãn Nhà mạng"]

    y_start = start["bottom"]
    y_end = end["top"]

    # Checkbox trong mẫu nằm về phía trái trang.
    x_end = int(width * 0.20) # chỉ lấy 20% phía bên trái bởi vì check box nằm ở phía bên trái
    region = image[y_start:y_end, :x_end] # cắt ảnh
    ###########################

    # save_debug_image("01_region.png", region, rgb=True)

    ########################
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)

    _, binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    boxes = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
# x	Tọa độ mép trái, tính từ bên trái ảnh
# y	Tọa độ mép trên, tính từ trên cùng ảnh
# w	Chiều rộng của khung, tính bằng pixel
# h	Chiều cao của khung, tính bằng pixel

        # Lọc hình gần vuông, kích thước tương ứng mẫu.
        if not 0.75 <= w / max(h, 1) <= 1.30:
            continue

        if not width * 0.012 <= w <= width * 0.035:
            continue

        if not width * 0.012 <= h <= width * 0.035:
            continue

        # Kiểm tra bốn cạnh để tránh nhận chữ thành checkbox.
        patch = binary[y:y + h, x:x + w]
        border = max(1, round(min(w, h) * 0.15))

        edge_scores = [
            np.mean(np.any(patch[:border, :] > 0, axis=0)),
            np.mean(np.any(patch[-border:, :] > 0, axis=0)),
            np.mean(np.any(patch[:, :border] > 0, axis=1)),
            np.mean(np.any(patch[:, -border:] > 0, axis=1)),
        ]

        if min(edge_scores) < 0.7:
            continue # chỉ lấy ảnh có hơn 65% mực ở cả 4 viền

        gap = max(2, round(w * 0.10))

        left_end = max(0, x - gap)
        left_region = binary[y:y + h, :left_end]

        if left_region.size > 0:
            # Tỷ lệ các hàng có xuất hiện nét mực bên trái.
            occupied_rows = np.any(left_region > 0, axis=1)
            left_ink_rows_ratio = float(np.mean(occupied_rows))

            # Nếu mực bên trái xuất hiện trên hơn 20% chiều cao,
            # loại hình đang xét.
            if left_ink_rows_ratio > 0.20:
                continue
        
        # Bỏ viền ô, chỉ đo phần bên trong.
        margin = max(2, round(min(w, h) * 0.22))
        inside = patch[margin:h - margin, margin:w - margin]

        if inside.size == 0:
            continue

        ink_ratio = float(np.mean(inside > 0))

        boxes.append({
            "x": x,
            "y": y + y_start,
            "w": w,
            "h": h,
            "ink_ratio": ink_ratio,
        })

    boxes.sort(key=lambda box: box["y"])

    if not boxes:
        return None, [], ["Không tìm thấy checkbox lĩnh vực"]

    selected = []

    for index, box in enumerate(boxes):
        x, y = box["x"], box["y"]
        w, h = box["w"], box["h"]
        ratio = box["ink_ratio"]

        # Ô trống: rất ít mực bên trong.
        if ratio <= 0.04:
            box["state"] = "empty"
            continue

        # Khoảng chưa rõ: không tự kết luận.
        if ratio < 0.12:
            box["state"] = "uncertain"
            warnings.append(
                f"Checkbox {index + 1} chưa rõ dấu tích"
            )
            continue

        box["state"] = "marked"

        # Cắt dòng chữ bên phải checkbox.
        padding = max(2, round(h * 0.15))
        top = max(y_start, y - padding) # mở rộng lên trên
        bottom = min(y_end, y + h + padding) # mở rộng xg dưới

        if index + 1 < len(boxes):
            bottom = min(bottom, boxes[index + 1]["y"]) # nếu chưa tới ô cuối cùng thì giới hạn để ko lẹm vào nội dung ô bên dưới

        text_image = image[
            top:bottom,
            x + w + 3:int(width * 1.0),
        ]
        #image[y_bắt_đầu:y_kết_thúc, x_bắt_đầu:x_kết_thúc]; cắt ảnh

        value = pytesseract.image_to_string(
            text_image,
            lang="vie+eng",
            config="--psm 7",
            timeout=60,
        ).strip()

        value = re.sub(r"\s+", " ", value)
        box["text"] = value

        if value:
        #     selected.append ({
        #         "linh_vuc": value,
        #         "ratio": round(ratio, 4),
            selected.append(value)
        # })
        else:
            warnings.append(
                f"Không đọc được chữ ở checkbox {index + 1}"
            )

    # Mẫu bạn gửi có 8 lựa chọn lĩnh vực.
    if len(boxes) != 8:
        warnings.append(
            f"Tìm thấy {len(boxes)}/8 checkbox; cần kiểm tra ảnh"
        )

    if not selected:
        warnings.append("Chưa xác định được lĩnh vực đã chọn")

    return selected if selected else None, boxes, warnings

def find_brand_pdf(folder_path):
    """
    Tìm PDF chứa đầy đủ các từ khóa trên cùng một trang.

    Trả về:
        {"ten_file": "...pdf", "trang": 1}
    hoặc None nếu không tìm thấy.
    """
    folder_path = Path(folder_path)

    if not folder_path.is_dir():
        raise NotADirectoryError(
            f"Folder không tồn tại: {folder_path}"
        )

    pdf_files = sorted(
        (
            path
            for path in folder_path.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.name.lower(),
    )
    result_check = {}
    for pdf_path in pdf_files:
        result_check.clear()
        image = pdf_to_image(pdf_path)
        lines = ocr_lines(image)
        full_text = "\n".join(line["text"] for line in lines)
        company = extract_company(full_text)
        brandname = extract_brandname(full_text)
        fields, boxes, warnings = extract_fields(image, lines)
        result_check.update({
            "ten_cong_ty": company,
            "brandname": brandname,
            "linh_vuc": fields              
            })
        
        if sum(value is not None for value in result_check.values()) >= 2:
            return pdf_path
        
    return None

def read_brand_pdf(pdf_path, page_number=1):
    image = pdf_to_image(pdf_path, page_number)
    lines = ocr_lines(image)

    full_text = "\n".join(line["text"] for line in lines)

    company = extract_company(full_text)
    brandname = extract_brandname(full_text)
    fields, boxes, warnings = extract_fields(image, lines)

    if not company:
        warnings.append("Không đọc được tên công ty")

    if not brandname:
        warnings.append("Không đọc được brandname")

    # Lưu chữ OCR để xem lỗi nhận dạng.
    Path("ocr_text.txt").write_text(
        full_text, encoding="utf-8"
    )

    # Vẽ các ô được phát hiện để kiểm tra trực quan.
    debug = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    for box in boxes:
        x, y, w, h = (
            box["x"], box["y"], box["w"], box["h"]
        )

        color = (
            (0, 180, 0)
            if box["state"] == "marked"
            else (0, 0, 255)
        )

        cv2.rectangle(
            debug, (x, y), (x + w, y + h), color, 2
        )

        cv2.putText(
            debug,
            f'{box["ink_ratio"]:.2f}',
            (x + w + 5, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
        )

    cv2.imwrite("kiem_tra_checkbox.png", debug)

    return {
        "ten_cong_ty": company,
        "brandname": brandname,
        "linh_vuc": fields,
        "canh_bao": warnings,
        "trang": page_number,
    }

def extract_BRN(text):
    """Tìm mã số doanh nghiệp trong kết quả OCR đã tiền xử lý."""
    text = unicodedata.normalize("NFC", text)
    flat = re.sub(r"\s+", " ", text).strip()
    plain = bo_dau(flat).lower()

    pattern = (
        r"\bma so doanh nghiep\s*[:：]?\s*"
        r"(?P<brn>\d(?:[\s.-]?\d){9,12})"
    )
    match = re.search(pattern, plain)

    if not match:
        return None

    start, end = match.span("brn")
    brn = re.sub(r"\D", "", flat[start:end])
    return brn if len(brn) in (10, 13) else None


def extract_web(text):
    """Tìm website nằm sau nhãn Website trong văn bản OCR toàn trang."""
    if not isinstance(text, str) or not text.strip():
        return None

    text = unicodedata.normalize("NFKC", text)
    flat = re.sub(r"\s+", " ", text).strip()

    domain_label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    pattern = re.compile(
        r"\b(?:web\s*site|webs[i1l]te|trang\s*web)\b"
        r"\s*[:\-]?\s*"
        r"(?P<web>"
        r"(?:https?\s*:\s*/\s*/\s*)?"
        r"(?:www\s*\.\s*)?"
        rf"(?:{domain_label}\s*\.\s*)+[a-z]{{2,63}}"
        r")",
        re.IGNORECASE,
    )
    match = pattern.search(flat)

    if not match:
        return None

    website = re.sub(r"\s+", "", match.group("web"))
    return website.rstrip(".,;:!?").lower()


def extract_brn_web_from_image(image):
    """OCR  trả về mã doanh nghiệp và tên miền."""
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Chữ có màu tối, còn hoa văn nền màu vàng có mức xám cao.
    # Ngưỡng cố định này loại được phần lớn watermark của mẫu hiện tại.
    _, clean = cv2.threshold(
        gray,
        170,
        255,
        cv2.THRESH_BINARY,
    )

    text = pytesseract.image_to_string(
        clean,
        lang="vie+eng",
        config="--psm 6",
        timeout=60,
    )

    brn = extract_BRN(text)
    web = extract_web(text)
    return brn, web


def find_brn_pdf(folder_path):
    """
    Tìm PDF chứa đầy đủ các từ khóa trên cùng một trang.

    Trả về:
        {"ten_file": "...pdf", "trang": 1}
    hoặc None nếu không tìm thấy.
    """
    folder_path = Path(folder_path)

    if not folder_path.is_dir():
        raise NotADirectoryError(
            f"Folder không tồn tại: {folder_path}"
        )

    pdf_files = sorted(
        (
            path
            for path in folder_path.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.name.lower(),
    )
    result_check = {}
    for pdf_path in pdf_files:
        result_check.clear()
        image = pdf_to_image(pdf_path)
        brn, web = extract_brn_web_from_image(image)
        result_check.update({
            "ma_cong_ty": brn,
            "ten_mien": web
            })
        
        if brn is not None:
            return pdf_path
        
    return None

def read_brn_pdf(pdf_path, page_number=1):
    image = pdf_to_image(pdf_path, page_number)
    brn, web = extract_brn_web_from_image(image)

    if not brn:
        print("Không đọc được mã công ty")

    if not web:
        print("Không đọc được tên miền")


    return {
        "ma_cong_ty": brn,
        "ten_mien": web
    }


if __name__ == "__main__": # hàm này sẽ chạy khi file read_pdf.py đc chạy, nếu là file khác chạy thì sẽ bỏ qua
    Folder_PATH = r"D:\Tổ AI_ auto\auto_flow_agent\auto_brandname\AIS"
    PDF_PATH_brand = find_brand_pdf(Folder_PATH)
    PDF_PATH_brn = find_brn_pdf(Folder_PATH)

    PAGE_NUMBER = 1

    if PDF_PATH_brand is None:
        raise FileNotFoundError(
            "Không tìm thấy PDF chứa thông tin brandname"
        )

    if PDF_PATH_brn is None:
        raise FileNotFoundError(
            "Không tìm thấy PDF chứa mã công ty"
        )

    result_brand = read_brand_pdf(PDF_PATH_brand, PAGE_NUMBER)
    result_brn = read_brn_pdf(PDF_PATH_brn, PAGE_NUMBER)
    result = {**result_brand, **result_brn}

    print(json.dumps(result, ensure_ascii=False, indent=2))

    Path("ket_qua.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
