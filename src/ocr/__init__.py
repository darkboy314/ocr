import csv
import os


def _csv_columns() -> list[str]:
    columns = [
        "input_path",
        "report_month",
        "agreement_number",
        "recipient_name",
        "vehicle_registration_number",
        "vehicle_model",
        "service_route",
        "odometer_reading",
        "maintenance_company",
        "maintenance_from",
        "maintenance_to",
        "downtime_hours",
        "maintenance_type",
        "accident_datetime",
        "accident_details",
        "accident_cause",
    ]
    columns.extend(f"maintenance_{index}" for index in range(1, 21))
    columns.extend(f"maintenance_category_{index}" for index in range(1, 21))
    columns.extend(f"maintenance_cost_{index}" for index in range(1, 21))
    columns.append("total_cost")
    return columns


def _csv_row(record: dict) -> dict[str, str]:
    row = {column: "" for column in _csv_columns()}
    for column in (
        "input_path",
        "report_month",
        "agreement_number",
        "recipient_name",
        "vehicle_registration_number",
        "vehicle_model",
        "service_route",
        "odometer_reading",
        "maintenance_company",
        "maintenance_from",
        "maintenance_to",
        "downtime_hours",
        "maintenance_type",
        "accident_datetime",
        "accident_details",
        "accident_cause",
        "total_cost",
    ):
        row[column] = str(record.get(column, ""))
    for prefix, source in (
        ("maintenance", "maintenance_items"),
        ("maintenance_category", "maintenance_categories"),
        ("maintenance_cost", "maintenance_costs"),
    ):
        values = record.get(source, [])
        if isinstance(values, list):
            for index, value in enumerate(values[:20], start=1):
                row[f"{prefix}_{index}"] = str(value)
    return row


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
    from ocr import ppocr, textprocess

    files = find_files_by_name_keyword(root_dir, keyword, extensions)
    if not files:
        raise FileNotFoundError("没有找到符合条件的文件")

    ocr = ppocr.Ocr()
    # raw = ocr.start_ocr(
    #     files,
    #     isfileoutputenabled=True,
    #     output_dir=output_dir,
    # )
    
    raw = ocr.start_ocr(
        files,
        output_dir=output_dir,
        save_image=True,
        save_json=True,
        save_markdown=True,
    )

    records = textprocess.extract_documents(list(raw))
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "result.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        columns = _csv_columns()
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(_csv_row(record) for record in records)
    return len(files)


def main() -> None:
    process_files(
        root_dir="../Final_Algorithm",
        output_dir="output",
        keyword="Maintenance Report",
        extensions=[".pdf"],
    )

    # from ocr.gui import OcrGui

    # OcrGui().run()

if __name__ == "__main__":
    main()
