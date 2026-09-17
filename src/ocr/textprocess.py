import os
import re
from html.parser import HTMLParser
from collections.abc import Mapping


class _TableTextParser(HTMLParser):
    """Extract cell text from the HTML table content returned by PP-Structure."""

    def __init__(self) -> None:
        super().__init__()
        self.cells: list[str] = []
        self.rows: list[list[str]] = []
        self._row: list[str] = []
        self._parts: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        super().handle_starttag(tag, _attrs)
        if tag == "tr":
            self._row = []
        if tag in {"td", "th"}:
            self._in_cell = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            cell = " ".join("".join(self._parts).split())
            self.cells.append(cell)
            self._row.append(cell)
            self._parts = []
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._parts.append(data)


def _value(item: object, key: str, default: object = None) -> object:
    if isinstance(item, Mapping):
        return item.get(key, default)
    value = getattr(item, key, default)
    if value is not default:
        return value
    aliases = {
        "block_label": "label",
        "block_content": "content",
    }
    return getattr(item, aliases.get(key, key), default)


def _block_text(block: object) -> str:
    """Return text from either the usual block_content or OCR text fields."""
    content = _value(block, "block_content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        return " ".join(str(value) for value in content.values()).strip()
    if isinstance(content, list):
        return " ".join(str(value) for value in content).strip()
    return str(content).strip() if content else ""


def _table_cells(content: str) -> list[str]:
    parser = _TableTextParser()
    parser.feed(content)
    if parser.cells:
        return parser.cells
    cells = []
    for line in content.splitlines():
        cells.extend(part.strip() for part in line.split("|") if part.strip())
    return cells


def _table_rows(content: str) -> list[list[str]]:
    parser = _TableTextParser()
    parser.feed(content)
    if parser.rows:
        return parser.rows
    return [
        [part.strip() for part in line.split("|") if part.strip()]
        for line in content.splitlines()
        if line.strip()
    ]


def _is_field_label(value: str) -> bool:
    labels = (
        "資助協議編號", "受資助者名稱", "車牌號碼", "車輛型號", "服務路線",
        "維修時里程表讀數", "維修公司名稱", "維修日期和時間", "停運時間/小時",
        "維修類型", "事故發生日期及時間", "事故地點", "事故原因",
        "Subsidy Agreement No.", "Subsidy recipient name", "Vehicle Registration No.",
        "Vehicle model", "Service route", "Odometer reading at maintenance/km", 
        "Maintenance company name", "Maintenance date & time", "Operation down time/hour",
        "Maintenance type", "Date & time", 
        "Location, course of the incident and countermeasures taken",
        "Cause of incident"
    )
    return any(label in value for label in labels)


def _ocr_fallback_value(data: dict, field_label: str) -> str:
    for ocr_result in data.get("_overall_ocr_results", []):
        texts = _value(ocr_result, "rec_texts", [])
        if not isinstance(texts, list):
            continue
        for index, text in enumerate(texts):
            if field_label not in str(text):
                continue
            candidates = []
            for candidate in texts[index + 1:]:
                candidate = str(candidate).strip()
                if not candidate or _is_field_label(candidate):
                    continue
                if candidate.casefold() in {"maintenance company", "name"}:
                    continue
                candidates.append(candidate)
                if len(candidates) == 1:
                    return candidates[0]
    return ""


def _split_maintenance_datetime(value: str) -> tuple[str, str]:
    cleaned = re.sub(r"由|至|from|to", " ", value, flags=re.IGNORECASE)
    parts = cleaned.split()
    return (parts[0], parts[1]) if len(parts) >= 2 else (
        parts[0] if parts else "",
        "",
    )


def extract_fields_from_ppstructure(data: dict) -> dict[str, str | list[str]]:
    """Extract one document row from a PP-Structure result dictionary.

    ``data`` is expected to contain ``input_path`` and ``parsing_res_list``.
    PP-Structure may return one result per PDF page, so callers can merge
    dictionaries with the same input path using ``extract_documents``.
    """
    blocks = data.get("parsing_res_list", [])
    if not isinstance(blocks, list):
        raise TypeError("parsing_res_list must be a list")

    text_blocks = [
        _block_text(block)
        for block in blocks
        if _value(block, "block_label") == "text"
    ]
    table_blocks = [
        _block_text(block)
        for block in blocks
        if _value(block, "block_label") == "table"
    ]
    page_text = " ".join(text_blocks)
    report_month = ""
    match = re.search(
        r"[:：]\s*("
        r"[0-9]{4}\s*[年/\-.]\s*[0-9]{1,2}(?:\s*月)?"
        r"|[0-9]{4}\s+[A-Za-z]{3,9}"
        r"|[A-Za-z]{3,9}\s+[0-9]{4}"
        r")",
        page_text,
    )
    if match:
        report_month = re.sub(r"\s+", "", match.group(1))

    table_contents = [_table_cells(content) for content in table_blocks]
    cells = [cell for table in table_contents for cell in table]
    labels = (
        ("agreement_no", ("資助協議編號",)),
        ("company", ("受資助者名稱",)),
        ("license_plate", ("車牌號碼",)),
        ("model", ("車輛型號",)),
        ("service_route", ("服務路線",)),
        ("odometer_reading", ("維修時里程表讀數/公里", "Odometer reading at")),
        ("maintenance_company", ("維修公司名稱",)),
        ("maintenance_datetime", ("維修日期和時間",)),
        ("main_downtime", ("停運時間/小時",)),
        ("total_main_type", ("維修類型",)),
        ("accident_datetime", ("事故發生日期及時間",)),
        (
            "accident_details",
            ("事故地點、經過及當時採取的對應措施", "事故地點、經過及當時採取嘅對應措施"),
        ),
        ("accident_cause", ("事故原因",)),
    )
    values: dict[str, str | list[str]] = {"report_month": report_month}
    for name, label_patterns in labels:
        value = ""
        for index, cell in enumerate(cells):
            if any(pattern.casefold() in cell.casefold() for pattern in label_patterns):
                suffix = re.split(r"[:：]", cell, maxsplit=1)
                if len(suffix) == 2 and suffix[1].strip():
                    value = suffix[1].strip()
                elif len(suffix) == 1 and index + 1 < len(cells):
                    value = cells[index + 1]
                if _is_field_label(value):
                    value = _ocr_fallback_value(data, label_patterns[0])
                break
        values[name] = value

    maintenance_from, maintenance_to = _split_maintenance_datetime(
        str(values.get("maintenance_datetime", ""))
    )
    values["main_date_from"] = maintenance_from
    values["main_date_to"] = maintenance_to
    values.pop("maintenance_datetime", None)

    item_start = next(
        (index for index, cell in enumerate(cells) if "維修項目" in cell or "maintenance item" in cell.casefold()),
        -1,
    )
    total_index = next(
        (index for index, cell in enumerate(cells) if "總維修費用" in cell or "total maintenance" in cell.casefold()),
        len(cells),
    )
    item_cells = cells[item_start + 1:total_index] if item_start >= 0 else []
    item_values: list[str] = []
    categories: list[str] = []
    costs: list[str] = []
    category_values = {"修理", "更換", "年檢"}
    row_items = [
        row for content in table_blocks for row in _table_rows(content)
        if row and re.search(r"\d+\s*[.．]", row[0])
    ]
    if row_items:
        for row in row_items[:20]:
            item = re.sub(r"^\s*\d+\s*[.．]\s*", "", row[0]).strip()
            item = re.sub(r"\s*\d+\s*[.．]\s*$", "", item).strip()
            markers = row[1:-1]
            category = ""
            if len(markers) >= 2:
                if markers[0] in {"☑", "✓", "是"}:
                    category = "修理"
                elif markers[1] in {"☑", "✓", "是"}:
                    category = "更換"
            cost = next(
                (cell for cell in reversed(row) if re.fullmatch(r"\$?\s*[\d,]+(?:\.\d+)?", cell)),
                "",
            )
            item_values.append(item)
            categories.append(category)
            costs.append(cost)
    else:
        pending: list[str] = []
        for cell in item_cells:
            if re.fullmatch(r"\$?\s*[\d,]+(?:\.\d+)?", cell):
                category = next((value for value in pending if value in category_values), "")
                item = " ".join(value for value in pending if value not in category_values and value != "空")
                item_values.append(item)
                categories.append(category)
                costs.append(cell)
                pending = []
            elif cell not in {"空"}:
                pending.append(cell)
    values["main_descs"] = item_values[:20]
    values["main_types"] = categories[:20]
    values["main_costs"] = costs[:20]
    values["total_cost"] = cells[total_index + 1] if total_index < len(cells) - 1 else ""
    input_path = str(_value(data, "input_path", ""))
    filename = os.path.basename(input_path).upper()
    values["input_path"] = input_path
    if "(EV)" in filename:
        values["veh_type"] = "EV"
    elif "(CV)" in filename:
        values["veh_type"] = "CV"
    else:
        values["veh_type"] = ""
    return values


def extract_documents(results: list[dict]) -> list[dict[str, str | list[str]]]:
    """Group page results by input path and return one extracted row per file."""
    grouped: dict[str, dict] = {}
    for result in results:
        path = str(_value(result, "input_path", ""))
        if path not in grouped:
            grouped[path] = {
                "input_path": path,
                "parsing_res_list": [],
                "_overall_ocr_results": [],
            }
        blocks = _value(result, "parsing_res_list", [])
        if not isinstance(blocks, list):
            raise TypeError("parsing_res_list must be a list")
        grouped[path]["parsing_res_list"].extend(blocks)
        overall_ocr = _value(result, "overall_ocr_res", None)
        if overall_ocr is not None:
            grouped[path]["_overall_ocr_results"].append(overall_ocr)
    return [extract_fields_from_ppstructure(data) for data in grouped.values()]
