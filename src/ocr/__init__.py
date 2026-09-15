import json
import os
import pandas as pd
from ocr import ppocr
from ocr import textprocess
from ocr import cantoeng


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
    current_path = os.getcwd()
    print(current_path)

    output_dir = "./output"
    keyword = "test"
    extensions = [".pdf"]
    
    # Find Files
    files = find_files_by_name_keyword(root_dir, keyword, extensions)
    # files = ["input/test1.pdf", "input/test2.pdf"]
    
    # OCR scan files
    ocr = ppocr.Ocr()
    raw = ocr.start_ocr(files, isfileoutputenable=True)
    
    # Extract info from raw data
    process = textprocess.TextProcess()
    extract = process.process_info(raw)
    context_data = process.extract_info_from_data(extract)
    column_names = [
        "agree_numbers", "recipients", "veh_reg_numbers", "veh_models",
        "service_routes", "meter_readings", "maintenance_companies",
        "maintenance_dates_from", "maintenance_dates_to", "down_times",
        "maintenance_types", "reasons", "accident_dates", "accident_locations",
        "accident_descriptions", "accident_causes", "maintenance_lists",
        "maintenance_costs", "total_costs",
    ]
    
    # Translate content from CN(Cantonese) to EN
    # canton = cantoeng.Canton("en")
    # for _, pages in extract.items():
    #     for index, page in enumerate(pages):
    #         pages[index] = canton.start_translate(page)
    #         print(pages[index])
    
    # export to file
    pd.DataFrame(context_data, columns=column_names).to_csv(
        os.path.join(output_dir, "result.csv"), index=False
    )
        
    return

if __name__ == "__main__":
    main()
