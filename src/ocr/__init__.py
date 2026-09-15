import json
import os


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

            if keyword.casefold() in name.casefold():
                matched.append(os.path.join(dirpath, name))
    return matched


def process_files(root_dir: str, output_dir: str, keyword: str, extensions: list[str]) -> int:
    """Run OCR and export the extracted information for matching files."""
    import pandas as pd

    from ocr import ppocr, textprocess

    files = find_files_by_name_keyword(root_dir, keyword, extensions)
    if not files:
        raise FileNotFoundError("没有找到符合条件的文件")

    ocr = ppocr.Ocr()
    raw = ocr.start_ocr(
        files,
        isfileoutputenable=True,
        output_dir=output_dir,
    )

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
    
    os.makedirs(output_dir, exist_ok=True)
    pd.DataFrame(context_data, columns=column_names).to_csv(
        os.path.join(output_dir, "result.csv"), index=False
    )
    return len(files)


def main() -> None:
    from ocr.gui import OcrGui

    OcrGui().run()

if __name__ == "__main__":
    main()
