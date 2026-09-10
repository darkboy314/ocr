import json
import os
import ppocr
import cantoeng


def find_files_by_name_keyword(root_dir, keyword, extensions=None) -> list:
    """
    递归查找文件名中包含 keyword 的文件，可限定扩展名。
    extensions: 如 [".py", ".txt"]，为 None 时不限制。
    """
    if extensions is not None:
        # 统一转为小写方便比较
        extensions = {ext.lower() for ext in extensions}

    matched = []
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            # 扩展名过滤
            if extensions is not None:
                _, ext = os.path.splitext(name)
                if ext.lower() not in extensions:
                    continue

            if keyword in name:  # 如需忽略大小写可统一 .lower()
                matched.append(os.path.join(dirpath, name))
    return matched


def main() -> None:
    root_dir = "./"
    output_dir = "./output"
    keyword = "Maintenance Report"
    extensions = [".pdf"]
    
    # Find Files
    files = find_files_by_name_keyword(root_dir, keyword, extensions)
    
    # OCR scan files
    ocr = ppocr.Ocr()
    raw = ocr.start_ocr(files, isfileoutputenable=False)
    
    # Extract info from raw data
    extract = ocr.extract_info(raw)
    
    # Translate content from CN(Canton) to EN
    canton = cantoeng.Canton("en")
    for path, pages in extract:
        for p in pages:
            p["rec_texts"] = canton.start_translate(p["rec_texts"])
    
    with open("output.json", "w", encoding="utf-8") as f:
        json.dumps(extract, f, ensure_ascii=False, indent=2)
        
    return


if __name__ == '__main__':
    main()