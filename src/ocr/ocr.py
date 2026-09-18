import csv
import os
import re
from collections.abc import Collection
from pathlib import Path

from . import pp, table


def _csv_columns() -> list[str]:
    columns = [
        "input_path",
        "report_month",
        "agreement_no",
        "company",
        "license_plate",
        "model",
        "veh_type",
        "service_route",
        "odometer_reading",
        "maintenance_company",
        "main_date_from",
        "main_date_to",
        "main_downtime",
        "total_main_type",
        "accident_datetime",
        "accident_details",
        "accident_cause",
    ]
    columns.extend(f"main_desc_{index}" for index in range(1, 21))
    columns.extend(f"main_type_{index}" for index in range(1, 21))
    columns.extend(f"main_cost_{index}" for index in range(1, 21))
    columns.append("total_cost")
    return columns



def _csv_row(record: dict) -> dict[str, str]:
    row = {column: "" for column in _csv_columns()}
    for column in (
        "input_path",
        "report_month",
        "agreement_no",
        "company",
        "license_plate",
        "model",
        "veh_type",
        "service_route",
        "odometer_reading",
        "maintenance_company",
        "main_date_from",
        "main_date_to",
        "main_downtime",
        "total_main_type",
        "accident_datetime",
        "accident_details",
        "accident_cause",
        "total_cost",
    ):
        row[column] = str(record.get(column, ""))
    for prefix, source in (
        ("main_desc", "main_descs"),
        ("main_type", "main_types"),
        ("main_cost", "main_costs"),
    ):
        values = record.get(source, [])
        if isinstance(values, list):
            for index, value in enumerate(values[:20], start=1):
                row[f"{prefix}_{index}"] = str(value)
    return row


def find_files_by_name_keyword(
    root_dir: str,
    include: str,
    extensions: Collection[str] | None = None,
) -> list[str]:
    """Recursively find files whose names match ``include`` and extensions."""
    pattern = re.compile(include, re.IGNORECASE)
    normalized_extensions = (
        {extension.casefold() for extension in extensions} if extensions else None
    )
    return [
        str(path)
        for path in Path(root_dir).rglob("*")
        if path.is_file()
        and pattern.search(path.name)
        and (normalized_extensions is None or path.suffix.casefold() in normalized_extensions)
    ]


def process_files(
    root_dir: str,
    output_dir: str,
    keyword: str,
    extensions: Collection[str] | None = None,
) -> int:
    """Run OCR and export the extracted information for matching files."""

    files = find_files_by_name_keyword(root_dir, keyword, extensions)
    if not files:
        raise FileNotFoundError("没有找到符合条件的文件")

    raw = pp.start_ppocr(
        files,
        output_dir=output_dir,
        save_image=True,
        save_json=True,
    )

    records = table.extract_documents(list(raw))
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
        root_dir="input/Final_Algorithm",
        output_dir="output",
        keyword=r"^(?!.*CS).*Maintenance Report.*\.pdf$", # 正则表达式，筛选Maintenance Report但是不包含充电桩的Report
    )

    # OcrGui().run()

if __name__ == "__main__":
    main()
