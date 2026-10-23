"""Parse the documented human-readable alert bundle without regular expressions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedAlertText:
    original_text: str
    tool_id: str
    chamber_id: str
    lot_id: str
    wafer_id: str
    recipe_id: str
    alert_lines: tuple[dict[str, str], ...]
    sensor_lines: tuple[dict[str, object], ...]
    unparsed_lines: tuple[str, ...]

    @property
    def summary(self) -> str:
        symptoms = list(
            dict.fromkeys(line["sensor"] for line in self.alert_lines if line["sensor"] != "-")
        )
        return "; ".join(symptoms) or "경보 이벤트 확인 필요"


def _header_value(segment: str, prefix: str) -> str:
    value = segment.strip()
    if not value.startswith(prefix):
        raise ValueError(f"경보 헤더에서 {prefix.strip()} 항목을 찾을 수 없습니다.")
    result = value[len(prefix) :].strip()
    if not result:
        raise ValueError(f"경보 헤더의 {prefix.strip()} 값이 비어 있습니다.")
    return result


def _parse_header(line: str) -> tuple[str, str, str, str, str]:
    parts = [part.strip() for part in line.split("/")]
    if len(parts) != 5 or not parts[0].startswith("[경보]"):
        raise ValueError(
            "경보 헤더 형식이 올바르지 않습니다: "
            "[경보] tool / chamber / Lot ... / Wafer ... / recipe"
        )
    tool = parts[0][len("[경보]") :].strip()
    if not tool:
        raise ValueError("경보 헤더의 tool 값이 비어 있습니다.")
    return (
        tool,
        parts[1],
        _header_value(parts[2], "Lot "),
        _header_value(parts[3], "Wafer "),
        parts[4],
    )


def _parse_clock(value: str) -> bool:
    fields = value.split(":")
    if len(fields) != 3 or any(not field.isdigit() for field in fields):
        return False
    hour, minute, second = (int(field) for field in fields)
    return 0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60


def _parse_alarm(line: str) -> dict[str, str] | None:
    if not line.startswith("- "):
        return None
    prefix = line[2:].split(maxsplit=2)
    if len(prefix) != 3 or not _parse_clock(prefix[0]) or prefix[1] not in {"FDC", "장비"}:
        return None
    rule_and_values = prefix[2].split(maxsplit=1)
    if len(rule_and_values) != 2:
        return None
    rule, value_and_ocap = rule_and_values
    delimiter = value_and_ocap.rfind(" (")
    if delimiter < 1 or not value_and_ocap.endswith(")"):
        return None
    value = value_and_ocap[:delimiter].strip()
    ocap = value_and_ocap[delimiter + 2 : -1].strip()
    if not value or not ocap:
        return None
    value_parts = value.split(maxsplit=1)
    sensor_value = value_parts[0]
    if "=" in sensor_value:
        sensor, first_value = sensor_value.split("=", maxsplit=1)
        observed_value = " ".join([first_value, *value_parts[1:]]).strip()
    else:
        if len(value_parts) != 2:
            return None
        sensor, observed_value = sensor_value, value_parts[1]
    return {
        "time": prefix[0],
        "source": "fdc" if prefix[1] == "FDC" else "equipment",
        "rule": rule,
        "sensor": sensor,
        "value": observed_value,
        "ocap": ocap,
    }


def _parse_sensor(line: str) -> dict[str, object] | None:
    if not line.startswith("- ") or "):" not in line:
        return None
    label, raw_points = line[2:].split("):", maxsplit=1)
    if " (" not in label:
        return None
    sensor, metadata = label.split(" (", maxsplit=1)
    metadata = metadata.strip()
    unit_and_normal = metadata.split(",", maxsplit=1)
    if len(unit_and_normal) != 2 or "±" not in unit_and_normal[1]:
        return None
    normal_label = unit_and_normal[1].strip()
    if not normal_label.startswith("정상 "):
        return None
    mean_and_sd = normal_label[len("정상 ") :].split("±", maxsplit=1)
    try:
        normal_mean, normal_sd = float(mean_and_sd[0]), float(mean_and_sd[1])
        points = [None if value == "-" else float(value) for value in raw_points.split()]
    except (ValueError, IndexError):
        raise ValueError(f"센서 줄의 수치 형식이 올바르지 않습니다: {line}")
    if not sensor.strip() or not unit_and_normal[0].strip():
        return None
    return {
        "sensor": sensor.strip(),
        "unit": unit_and_normal[0].strip(),
        "normal_mean": normal_mean,
        "normal_sd": normal_sd,
        "points": points,
    }


def parse_alert_text(text: str) -> ParsedAlertText:
    """Parse header, alarms and sensor series; retain source order and unknown lines."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("경보 입력이 비어 있습니다.")
    tool, chamber, lot, wafer, recipe = _parse_header(lines[0])

    alerts: list[dict[str, str]] = []
    sensors: list[dict[str, object]] = []
    unknown: list[str] = []
    for line in lines[1:]:
        alarm = _parse_alarm(line)
        if alarm is not None:
            alerts.append(alarm)
            continue
        sensor = _parse_sensor(line)
        if sensor is not None:
            sensors.append(sensor)
            continue
        unknown.append(line)

    alerts.sort(key=lambda item: item["time"])
    return ParsedAlertText(
        original_text=text,
        tool_id=tool,
        chamber_id=chamber,
        lot_id=lot,
        wafer_id=wafer,
        recipe_id=recipe,
        alert_lines=tuple(alerts),
        sensor_lines=tuple(sensors),
        unparsed_lines=tuple(unknown),
    )
