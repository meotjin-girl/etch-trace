import pytest

from agent.alert_text import parse_alert_text


def test_parse_alert_text_preserves_identity_values_and_sensor_gaps():
    text = (
        "[경보] ETCH-02 / CH-A / Lot SIMLOT-20261022-2A151416 / "
        "Wafer SIMLOT-20261022-2A151416-W01 / RCP-OX-ETCH-EDU-01\n"
        "- 15:15:11 FDC FDC_WATCH source_rf_reflected_w z=4.1 (OCAP-ETCH-RF)\n"
        "- 15:15:36 장비 RF_REFLECT_HIGH source_rf_reflected_w=39.4 W "
        "(한계 37 W) (OCAP-ETCH-RF)\n"
        "- source_rf_reflected_w (W, 정상 5.364±0.590): 5.2 - 44.1\n"
    )
    result = parse_alert_text(text)
    assert (result.tool_id, result.chamber_id, result.recipe_id) == (
        "ETCH-02",
        "CH-A",
        "RCP-OX-ETCH-EDU-01",
    )
    assert [item["source"] for item in result.alert_lines] == ["fdc", "equipment"]
    assert result.alert_lines[0]["sensor"] == "source_rf_reflected_w"
    assert result.alert_lines[0]["value"] == "z=4.1"
    assert result.alert_lines[1]["sensor"] == "source_rf_reflected_w"
    assert result.alert_lines[1]["value"] == "39.4 W (한계 37 W)"
    assert result.sensor_lines[0]["points"] == [5.2, None, 44.1]
    assert result.original_text == text


def test_parse_alert_text_rejects_invalid_header():
    with pytest.raises(ValueError, match="경보 헤더"):
        parse_alert_text("ETCH-02 CH-A 경보 내용")
