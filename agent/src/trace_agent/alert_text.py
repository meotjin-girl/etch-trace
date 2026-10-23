# Copyright 2026 TRACE contributors
"""Self-contained version of agent/alert_text.py's fixed alert parser."""

from datetime import time

from .errors import ContractError
from .models import Alert, Context, Model


class Alarm(Model):
    """One timestamped equipment or FDC observation."""

    time: str
    source: str
    rule: str
    sensor: str
    value: str
    ocap: str


class Sensor(Model):
    """A sensor series retains units and missing samples."""

    sensor: str
    unit: str
    normal_mean: float
    normal_sd: float
    points: list[float | None]


class ParsedAlert(Model):
    """Parsed context supplements, but never replaces, the original alert."""

    alert: Alert
    alert_lines: list[Alarm]
    sensor_lines: list[Sensor]
    unparsed_lines: list[str]

    def context(self) -> Context:
        """Use the last observed sample, retaining all samples in the parsed alert."""
        metrics: dict[str, float] = {}
        for sensor in self.sensor_lines:
            observed = next((point for point in reversed(sensor.points) if point is not None), None)
            if observed is not None:
                metrics[sensor.sensor] = observed
        symptoms = dict.fromkeys(line.sensor for line in self.alert_lines if line.sensor != "-")
        return Context(
            equipment=self.alert.tool_id,
            chamber=self.alert.chamber_id,
            recipe=self.alert.recipe_id,
            symptom="; ".join(symptoms) or "경보 이벤트 확인 필요",
            metrics=metrics,
        )


def _header_value(segment: str, prefix: str) -> str:
    value = segment.strip()
    if not value.startswith(prefix) or not value[len(prefix) :].strip():
        raise ContractError(detail=f"경보 헤더의 {prefix.strip()} 항목이 없거나 비어 있습니다.")
    return value[len(prefix) :].strip()


def _clock(value: str) -> bool:
    fields = value.split(":")
    if len(fields) != len(("hour", "minute", "second")) or any(
        not field.isdigit() for field in fields
    ):
        return False
    hour, minute, second = (int(field) for field in fields)
    try:
        _ = time(hour, minute, second)
    except ValueError:
        return False
    return True


def _alarm(line: str) -> Alarm | None:
    prefix = line[2:].split(maxsplit=2)
    if (
        not line.startswith("- ")
        or len(prefix) != len(("time", "source", "rule"))
        or not _clock(prefix[0])
        or prefix[1] not in {"FDC", "장비"}
    ):
        return None
    rule_and_values = prefix[2].split(maxsplit=1)
    if len(rule_and_values) != len(("rule", "values")):
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
        if len(value_parts) != len(("sensor", "value")):
            return None
        sensor, observed_value = sensor_value, value_parts[1]
    return Alarm(
        time=prefix[0],
        source="fdc" if prefix[1] == "FDC" else "equipment",
        rule=rule,
        sensor=sensor,
        value=observed_value,
        ocap=ocap,
    )


def _sensor(line: str) -> Sensor | None:
    if not line.startswith("- ") or "):" not in line:
        return None
    label, raw_points = line[2:].split("):", maxsplit=1)
    if " (" not in label:
        return None
    sensor, metadata = label.split(" (", maxsplit=1)
    unit_and_normal = metadata.strip().split(",", maxsplit=1)
    if len(unit_and_normal) != len(("unit", "normal")) or "±" not in unit_and_normal[1]:
        return None
    normal_label = unit_and_normal[1].strip()
    if not normal_label.startswith("정상 "):
        return None
    mean_and_sd = normal_label[len("정상 ") :].split("±", maxsplit=1)
    try:
        normal_mean, normal_sd = float(mean_and_sd[0]), float(mean_and_sd[1])
        points = [None if value == "-" else float(value) for value in raw_points.split()]
    except (ValueError, IndexError) as error:
        raise ContractError(detail=f"센서 줄의 수치 형식이 올바르지 않습니다: {line}") from error
    if not sensor.strip() or not unit_and_normal[0].strip():
        return None
    return Sensor(
        sensor=sensor.strip(),
        unit=unit_and_normal[0].strip(),
        normal_mean=normal_mean,
        normal_sd=normal_sd,
        points=points,
    )


def parse_alert_text(text: str) -> ParsedAlert:
    """Parse the legacy header/alarm/series grammar without losing source text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ContractError(detail="경보 입력이 비어 있습니다.")
    parts = [part.strip() for part in lines[0].split("/")]
    if len(parts) != len(("tool", "chamber", "lot", "wafer", "recipe")) or not parts[0].startswith(
        "[경보]"
    ):
        raise ContractError(
            detail="경보 헤더 형식 오류: [경보] tool / chamber / Lot ... / Wafer ... / recipe"
        )
    tool_id = parts[0][len("[경보]") :].strip()
    if not tool_id:
        raise ContractError(detail="경보 헤더의 tool 값이 비어 있습니다.")
    alert = Alert(
        tool_id=tool_id,
        chamber_id=parts[1],
        lot_id=_header_value(parts[2], "Lot "),
        wafer_id=_header_value(parts[3], "Wafer "),
        recipe_id=parts[4],
        source_text=text,
    )
    alarms: list[Alarm] = []
    sensors: list[Sensor] = []
    unknown: list[str] = []
    for line in lines[1:]:
        alarm = _alarm(line)
        if alarm is not None:
            alarms.append(alarm)
            continue
        sensor = _sensor(line)
        if sensor is not None:
            sensors.append(sensor)
            continue
        unknown.append(line)
    return ParsedAlert(
        alert=alert,
        alert_lines=sorted(alarms, key=lambda item: item.time),
        sensor_lines=sensors,
        unparsed_lines=unknown,
    )
