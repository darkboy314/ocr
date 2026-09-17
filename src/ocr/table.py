"""Extract maintenance-report fields from PaddleOCR text and bounding boxes."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class _Item:
    text: str
    left: float
    top: float
    right: float
    bottom: float
    page: int


@dataclass(frozen=True)
class _Field:
    name: str
    labels: tuple[str, ...]
    kind: str = "text"


_FIELDS = (
    _Field("report_month", ("報告月份和年份", "Reporting month & year"), "month"),
    _Field("agreement_no", ("資助協議編號", "Subsidy Agreement No.")),
    _Field("company", ("受資助者名稱", "Subsidy recipient name"), "company"),
    _Field("license_plate", ("車牌號碼", "Vehicle Registration No.")),
    _Field("model", ("車輛型號", "Vehicle model")),
    _Field("service_route", ("服務路線", "Service route")),
    _Field(
        "odometer_reading",
        ("維修時里程表讀數/公里", "Odometer reading at maintenance/km"),
        "number",
    ),
    _Field("maintenance_company", ("維修公司名稱", "Maintenance company name")),
    _Field("maintenance_datetime", ("維修日期和時間", "Maintenance date & time"), "date"),
    _Field("main_downtime", ("停運時間/小時", "Operation down time/hour"), "number"),
    _Field(
        "accident_details",
        (
            "事故地點、經過及當時採取的對應措施",
            "Location, course of the incident and countermeasures taken",
        ),
        "long",
    ),
    _Field("accident_cause", ("事故原因", "Cause of incident"), "long"),
)
_ACCIDENT_DATETIME_FIELD = _Field(
    "accident_datetime", ("事故發生日期及時間", "Date & time"), "date"
)
_ALL_LABELS = tuple(label for field in _FIELDS for label in field.labels) + (
    *_ACCIDENT_DATETIME_FIELD.labels,
    "維修項目",
    "Maintenance items",
    "修理",
    "Repaired",
    "更換",
    "Replaced",
    "費用",
    "Cost/HK$",
    "總維修費用",
    "Total maintenance cost",
    "原因",
    "Reason",
)
_UNCHECKED_MARKERS = {"", "口", "□", "☐", "o", "O"}
_MAX_VALUE_LEFT = {"service_route": 640}


def _value(item: object, key: str, default: object = None) -> object:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _normalise(value: str) -> str:
    return re.sub(r"[\s:：/／（）()、，,.*^_\-]+", "", value).casefold()


def _matches(text: str, labels: tuple[str, ...]) -> bool:
    normalised = _normalise(text)
    return any(
        (
            _normalise(label) in normalised
            or (
                len(normalised) >= 8
                and normalised in _normalise(label)
            )
            or SequenceMatcher(None, normalised, _normalise(label)).ratio() >= 0.82
        )
        for label in labels
        if normalised
    )


def _items(results: list[object]) -> list[_Item]:
    items: list[_Item] = []
    for page, result in enumerate(results):
        texts = _value(result, "rec_texts", [])
        boxes = _value(result, "rec_boxes", [])
        if not isinstance(texts, list) or not hasattr(boxes, "__iter__"):
            raise TypeError("PaddleOCR result must contain rec_texts and rec_boxes")
        for text, box in zip(texts, boxes):
            if not str(text).strip() or len(box) < 4:
                continue
            left, top, right, bottom = (float(value) for value in box[:4])
            items.append(_Item(str(text).strip(), left, top, right, bottom, page))
    return items


def _inline_value(item: _Item, labels: tuple[str, ...]) -> str:
    if ":" in item.text or "：" in item.text:
        return re.split(r"[:：]", item.text, maxsplit=1)[1].strip()
    for label in labels:
        match = re.search(re.escape(label), item.text, re.IGNORECASE)
        if match:
            return item.text[match.end() :].lstrip(" :：")
    return ""


def _valid_value(field: _Field, value: str) -> bool:
    if not value or value in {"口", "□", "☐", "o", "O", "由", "至", "from", "to"}:
        return False
    if _matches(value, _ALL_LABELS):
        return False
    if field.kind == "month":
        return bool(re.search(r"\d{4}|[A-Za-z]{3,9}", value))
    if field.kind == "date":
        return bool(
            re.search(r"\d{1,4}[/.\-]\d{1,2}", value)
            or re.search(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}", value)
        )
    if field.kind == "number":
        return bool(re.search(r"\d", value)) or value.casefold() == "nil"
    if field.kind == "company":
        return any(character.isalpha() for character in value) and not re.match(
            r"^\d{3,}-\d{3,}\b", value
        )
    return True


def _field_value(items: list[_Item], field: _Field) -> str:
    """Take inline text or the closest value to the right of a form label."""
    for label in (item for item in items if _matches(item.text, field.labels)):
        inline = _inline_value(label, field.labels)
        if _valid_value(field, inline):
            return inline
        candidates = [
            candidate
            for candidate in items
            if candidate.page == label.page
            and candidate.left > label.right
            and candidate.left < _MAX_VALUE_LEFT.get(field.name, float("inf"))
            and candidate.bottom >= label.top - 15
            and candidate.top <= label.bottom + 40
            and not _matches(candidate.text, _ALL_LABELS)
            and _valid_value(field, candidate.text)
        ]
        if candidates:
            value = min(
                candidates,
                key=lambda candidate: candidate.left - label.right
                + abs(candidate.top - label.top) * 2,
            )
            if field.name == "model":
                continuation = [
                    candidate
                    for candidate in candidates
                    if candidate.left >= value.left - 20
                    and candidate.left <= value.right + 20
                    and candidate.top > value.bottom
                ]
                return " ".join(
                    candidate.text
                    for candidate in sorted([value, *continuation], key=lambda candidate: candidate.top)
                )
            return value.text
    return ""


def _maintenance_rows(items: list[_Item]) -> tuple[list[str], list[str], list[str]]:
    """Read rows from the raw OCR maintenance table using its header columns."""
    headers = [item for item in items if _matches(item.text, ("維修項目", "Maintenance items"))]
    if not headers:
        return [], [], []
    header = min(headers, key=lambda item: item.top)
    total_labels = [
        item
        for item in items
        if item.page == header.page
        and item.top > header.bottom
        and _matches(item.text, ("總維修費用", "Total maintenance cost"))
    ]
    table_bottom = min((item.top for item in total_labels), default=float("inf"))
    descriptions_in_column = [
        item
        for item in items
        if item.page == header.page
        and item.top >= header.top + 35
        and item.bottom < table_bottom
        and 150 <= item.left < 640
        and not re.fullmatch(r"\d+\s*[.．]", item.text)
        and not _matches(item.text, _ALL_LABELS)
    ]
    descriptions: list[str] = []
    types: list[str] = []
    costs: list[str] = []
    for description_item in sorted(
        descriptions_in_column, key=lambda item: (item.top, item.left)
    )[:20]:
        description = re.sub(r"^\s*\d+\s*[.．]\s*", "", description_item.text).strip()
        if not description or not any(character.isalpha() for character in description):
            continue
        row_items = [
            candidate
            for candidate in items
            if candidate.page == description_item.page
            and candidate.top <= description_item.bottom + 28
            and candidate.bottom >= description_item.top - 28
        ]
        repaired = any(
            640 <= candidate.left < 745
            and _is_checked_marker(candidate.text)
            for candidate in row_items
        )
        replaced = any(
            745 <= candidate.left < 860
            and _is_checked_marker(candidate.text)
            for candidate in row_items
        )
        cost = next(
            (
                candidate.text
                for candidate in sorted(
                    row_items, key=lambda candidate: candidate.left, reverse=True
                )
                if candidate.left >= 830
                and re.fullmatch(r"\$?\s*[\d,]+(?:\.\d+)?", candidate.text)
            ),
            "",
        )
        descriptions.append(description)
        types.append("repair" if repaired else "replace" if replaced else "")
        costs.append(cost)
    return descriptions, types, costs


def _is_checked_marker(value: str) -> bool:
    """Treat short, non-empty OCR marks in checkbox columns as checked."""
    return value.strip() not in _UNCHECKED_MARKERS and len(value.strip()) <= 3


def _reason_has_content(items: list[_Item]) -> bool:
    reason_labels = [item for item in items if _matches(item.text, ("原因", "Reason"))]
    for label in reason_labels:
        candidates = [
            item
            for item in items
            if item.page == label.page
            and label.top - 25 <= item.top <= label.bottom + 50
            and item.left > label.right
        ]
        if any(_is_checked_marker(item.text) for item in candidates):
            return True
        typed = [
            item.text
            for item in candidates
            if not _matches(item.text, ("交通意外", "Traffic accident", "其他（請註明）", "Others"))
        ]
        if typed:
            return True
    return False


def _split_dates(value: str) -> tuple[str, str]:
    parts = re.sub(r"由|至|from|to", " ", value, flags=re.IGNORECASE).split()
    return (parts[0], parts[1]) if len(parts) >= 2 else (parts[0], "") if parts else ("", "")


def _maintenance_dates(items: list[_Item]) -> tuple[str, str]:
    """Extract left/from and right/to values between the two form-row labels."""
    start_labels = [
        item for item in items if _matches(item.text, ("維修日期和時間",))
    ]
    end_labels = [
        item for item in items if _matches(item.text, ("停運時間/小時",))
    ]
    for start in start_labels:
        end = next(
            (
                item
                for item in end_labels
                if item.page == start.page and item.top > start.top
            ),
            None,
        )
        if end is None:
            continue
        from_labels = [
            item
            for item in items
            if item.page == start.page
            and start.top - 12 <= item.top <= end.top
            and _matches(item.text, ("由", "from"))
        ]
        to_labels = [
            item
            for item in items
            if item.page == start.page
            and start.top - 12 <= item.top <= end.top
            and _matches(item.text, ("至", "to"))
        ]
        if not from_labels or not to_labels:
            continue
        date_field = _Field("maintenance_datetime", (), "date")

        def inline_date(labels: list[_Item], label_text: tuple[str, ...]) -> str:
            return next(
                (
                    value
                    for label in labels
                    if _valid_value(
                        date_field,
                        value := _inline_value(label, label_text),
                    )
                ),
                "",
            )

        main_date_from = inline_date(from_labels, ("由", "from"))
        main_date_to = inline_date(to_labels, ("至", "to"))
        if main_date_from and main_date_to:
            return main_date_from, main_date_to

        from_label = from_labels[0]
        to_label = to_labels[0]
        values = [
            item
            for item in items
            if item.page == start.page
            and item.top >= start.top - 12
            and item.bottom <= end.bottom
            and _valid_value(date_field, item.text)
        ]
        from_values = [item for item in values if item.left >= from_label.right]
        to_values = [item for item in values if item.left >= to_label.right]
        from_value = min(
            from_values,
            key=lambda item: item.left - from_label.right + abs(item.top - start.top),
            default=None,
        )
        to_value = min(
            to_values,
            key=lambda item: item.left - to_label.right + abs(item.top - start.top),
            default=None,
        )
        return (
            main_date_from or (from_value.text if from_value else ""),
            main_date_to or (to_value.text if to_value else ""),
        )
    return "", ""


def _accident_datetime(items: list[_Item]) -> str:
    """Extract the date/time between the accident-date and accident-detail rows."""
    start_labels = [
        item
        for item in items
        if _matches(item.text, ("事故發生日期及時間",))
    ]
    end_labels = [
        item
        for item in items
        if _matches(item.text, ("事故地點、經過及當時採取的對應措施",))
    ]
    for start in start_labels:
        inline = _inline_value(start, _ACCIDENT_DATETIME_FIELD.labels)
        if _valid_value(_ACCIDENT_DATETIME_FIELD, inline):
            return inline
        end = next(
            (
                item
                for item in end_labels
                if item.page == start.page and item.top > start.bottom
            ),
            None,
        )
        if end is None:
            continue
        candidates = [
            item
            for item in items
            if item.page == start.page
            and item.top >= start.bottom
            and item.bottom <= end.top
            and _valid_value(_ACCIDENT_DATETIME_FIELD, item.text)
        ]
        if candidates:
            return min(candidates, key=lambda item: (item.top, item.left)).text
    return ""


def extract_document(results: list[object]) -> dict[str, str | list[str]]:
    """Extract one report from all of its page-level PaddleOCR results."""
    if not results:
        raise ValueError("Cannot extract a document without PaddleOCR results")
    items = _items(results)
    values: dict[str, str | list[str]] = {
        field.name: _field_value(items, field) for field in _FIELDS
    }
    main_date_from, main_date_to = _maintenance_dates(items)
    if not main_date_from and not main_date_to:
        main_date_from, main_date_to = _split_dates(str(values["maintenance_datetime"]))
    values.pop("maintenance_datetime")
    values["main_date_from"] = main_date_from
    values["main_date_to"] = main_date_to
    values["accident_datetime"] = _accident_datetime(items)
    descriptions, types, costs = _maintenance_rows(items)
    values["main_descs"] = descriptions
    values["main_types"] = types
    values["main_costs"] = costs
    values["total_main_type"] = (
        "no" if not descriptions else "no_sch" if _reason_has_content(items) else "sch"
    )
    values["total_cost"] = _field_value(
        items, _Field("total_cost", ("總維修費用", "Total maintenance cost"), "number")
    )
    input_path = str(_value(results[0], "input_path", ""))
    values["input_path"] = input_path
    filename = os.path.basename(input_path).upper()
    values["veh_type"] = "EV" if "(EV)" in filename else "CV" if "(CV)" in filename else ""
    return values


def extract_documents(results: list[object]) -> list[dict[str, str | list[str]]]:
    """Group page results by source file and extract one CSV record per file."""
    grouped: dict[str, list[object]] = {}
    for result in results:
        path = str(_value(result, "input_path", ""))
        grouped.setdefault(path, []).append(result)
    return [extract_document(document) for document in grouped.values()]
