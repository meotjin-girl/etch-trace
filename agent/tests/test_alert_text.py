# Copyright 2026 TRACE contributors
"""The copied parser preserves existing alert semantics."""

import pytest

from trace_agent.alert_text import parse_alert_text
from trace_agent.errors import ContractError

from .conftest import ALERT


def test_parser_preserves_observations_units_gaps_and_source() -> None:
    # Given / When: the established equipment/FDC/series envelope.
    parsed = parse_alert_text(ALERT)

    # Then: structured context retains the exact original alongside typed values.
    assert parsed.alert.source_text == ALERT
    assert parsed.alert.tool_id == "ETCH-02"
    assert parsed.alert_lines[0].value == "z=4.1"
    assert parsed.alert_lines[1].value == "39.4 W (한계 37 W)"
    assert parsed.sensor_lines[0].unit == "W"
    assert parsed.sensor_lines[0].points == [5.2, None, 44.1]
    assert parsed.context().metrics == {"source_rf_reflected_w": 44.1}
    assert parsed.unparsed_lines == ["unknown observations retained"]


@pytest.mark.parametrize("text", ["", "ETCH-02 CH-A alert", "[경보] / CH / Lot L / Wafer W / R"])
def test_parser_rejects_invalid_header(text: str) -> None:
    # Given / When / Then: invalid alert syntax fails at the input boundary.
    with pytest.raises(ContractError):
        _ = parse_alert_text(text)
