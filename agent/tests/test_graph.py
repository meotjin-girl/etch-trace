from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent.graph import build_graph
from agent.models import EducationalSimulationResult, Report, SensorAnalysis
from agent.tests.support import Events, Evidence


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)


def setup_graph(provider=None):
    task_id = str(uuid4())
    events = Events()
    evidence = provider or Evidence()
    saver = InMemorySaver()
    graph = build_graph(saver, evidence, events)
    config: RunnableConfig = {"configurable": {"thread_id": task_id}}
    return task_id, events, evidence, saver, graph, config


def test_clarification_when_scope_missing_survives_graph_reconstruction():
    # Given
    task, events, evidence, saver, graph, config = setup_graph()
    graph.invoke({"task_id": task, "question": "endpoint 지연 94초"}, config)
    assert graph.get_state(config).interrupts[0].value["kind"] == "clarification"
    graph = build_graph(saver, evidence, events)
    # When
    graph.invoke(Command(resume={"text": "ETCH-07 CH-B OX-120"}), config)
    # Then
    snapshot = graph.get_state(config)
    assert snapshot.interrupts[0].value["kind"] == "review"
    assert snapshot.values["context"].metrics == {"endpoint_sec": 94}
    assert [stage.key for stage in snapshot.values["report"].stages] == [
        "scope", "run_comparison", "physics", "sensor", "maintenance", "recommendation",
    ]
    assert snapshot.values["report"].physicsResults[0].status == "needs_more_data"
    assert [event.type for event in events.values] == [
        "QUESTION", "SEARCH_STARTED", "ANALYSIS_STARTED", "REPORT_STARTED", "APPROVAL_REQUIRED",
    ]
    assert evidence.searches == evidence.analyses == evidence.documents == 1


def test_revise_when_reviewing_preserves_evidence_and_publishes_new_approval():
    # Given
    task, events, evidence, _, graph, config = setup_graph()
    graph.invoke({"task_id": task, "question": "ETCH-07 endpoint 지연 94초"}, config)
    original = graph.get_state(config).values["report"]
    # When
    graph.invoke(Command(resume={
        "action": "revise", "comment": "RF 점검을 강조", "by": "검토자",
    }), config)
    # Then
    snapshot = graph.get_state(config)
    revised = snapshot.values["report"]
    assert isinstance(revised, Report)
    assert snapshot.interrupts
    assert revised.feedback == ["RF 점검을 강조"]
    assert revised.scored == original.scored
    assert revised.metrics == original.metrics
    assert revised.documents == original.documents
    assert revised.model_dump()["metrics"][0]["unit"] == "sec"
    assert revised.model_dump()["metrics"][0]["caseIds"] == [case.id for case in evidence.cases]
    assert [case.id for case in revised.causeCases] == ["CASE-1", "CASE-3", "CASE-4"]
    approvals = [event for event in events.values if event.type == "APPROVAL_REQUIRED"]
    assert len(approvals) == 2
    assert approvals[0].event_id != approvals[1].event_id
    assert len({event.event_id for event in events.values}) == len(events.values)
    assert evidence.searches == evidence.analyses == evidence.documents == 1


def test_done_when_engineer_approves_without_replaying_approval_callback():
    # Given
    task, events, _, _, graph, config = setup_graph()
    graph.invoke({"task_id": task, "question": "ETCH-07 endpoint 지연"}, config)
    # When
    graph.invoke(Command(resume={"action": "approve", "comment": "", "by": "engineer"}), config)
    # Then
    assert not graph.get_state(config).next
    assert [event.type for event in events.values].count("APPROVAL_REQUIRED") == 1
    assert events.values[-1].type == "DONE"
    assert events.values[-1].payload["approved"] is True
    assert events.values[-1].payload["by"] == "engineer"
    assert set(events.task_ids) == {task}


def test_incomplete_when_three_clarifications_are_insufficient():
    # Given
    task, events, evidence, _, graph, config = setup_graph()
    graph.invoke({"task_id": task, "question": "조사해 주세요"}, config)
    for _ in range(2):
        graph.invoke(Command(resume={"text": "아직 모릅니다"}), config)
    # When
    graph.invoke(Command(resume={"text": "아직 모릅니다"}), config)
    # Then
    assert not graph.get_state(config).next
    questions = [event for event in events.values if event.type == "QUESTION"]
    assert len(questions) == len({event.event_id for event in questions}) == 3
    assert events.values[-1].type == "INCOMPLETE"
    assert evidence.searches == 0


def test_incomplete_when_search_has_no_case_evidence():
    # Given
    task, events, evidence, _, graph, config = setup_graph(Evidence(cases=[]))
    # When
    graph.invoke({"task_id": task, "question": "ETCH-07 endpoint 지연"}, config)
    # Then
    assert not graph.get_state(config).next
    assert [event.type for event in events.values] == ["SEARCH_STARTED", "INCOMPLETE"]
    assert evidence.analyses == 0


def test_sensor_evidence_allows_analysis_without_matching_cases():
    class SensorOnlyEvidence(Evidence):
        def analyze_sensor_run(self, context):
            return SensorAnalysis.model_validate({
                "problem": "센서 시계열 정량 분석", "status": "CALCULATED",
                "target_run_id": "RUN-SENSOR-ONLY",
                "signals": [{
                    "sensor": "pressure_pv_mtorr", "unit": "mTorr",
                    "minimum": 25, "maximum": 34, "mean": 29,
                    "first_anomaly_sec": 45, "anomaly_duration_sec": 15,
                    "cooccurring_sensors": ["rf_reflected_w"],
                    "related_alarms": ["PRESSURE_HIGH"],
                    "ocap_ids": ["OCAP-ETCH-PRS"],
                    "threshold_source": "equipment_alarm",
                }],
            })

    provider = SensorOnlyEvidence(cases=[])
    _, events, _, _, graph, config = setup_graph(provider)
    graph.invoke({
        "task_id": config["configurable"]["thread_id"],
        "question": "ETCH-01 CH-A RCP-OX-ETCH-EDU-01 압력 상승",
    }, config)

    snapshot = graph.get_state(config)
    report = snapshot.values["report"]
    assert snapshot.interrupts[0].value["kind"] == "review"
    assert report.scored == []
    assert report.sensorAnalysis is not None
    assert report.sensorAnalysis.target_run_id == "RUN-SENSOR-ONLY"
    assert [event.type for event in events.values] == [
        "SEARCH_STARTED", "ANALYSIS_STARTED", "REPORT_STARTED", "APPROVAL_REQUIRED",
    ]


def test_callback_failure_when_publishing_is_not_swallowed():
    # Given
    task = str(uuid4())
    attempted = []

    def unavailable(task_id, event):
        attempted.append(event)
        raise ConnectionError("backend unavailable")

    saver = InMemorySaver()
    graph = build_graph(saver, Evidence(), unavailable)
    config: RunnableConfig = {"configurable": {"thread_id": task}}
    # When / Then
    with pytest.raises(ConnectionError, match="backend unavailable"):
        graph.invoke({"task_id": task, "question": "ETCH-07 endpoint 지연"}, config)
    assert graph.get_state(config).next == ("search_started",)

    # Replaying the failed callback uses the identical event ID.
    events = Events()
    graph = build_graph(saver, Evidence(), events)
    graph.invoke(None, config)
    assert attempted[0].event_id == events.values[0].event_id


def test_v2_quantitative_and_sensor_results_reach_review_report():
    class IntegratedEvidence(Evidence):
        def analyze_sensor_run(self, context):
            return SensorAnalysis.model_validate({
                "problem": "센서 시계열 정량 분석", "status": "CALCULATED",
                "target_run_id": "RUN-1",
                "signals": [{
                    "sensor": "pressure_pv_mtorr", "unit": "mTorr",
                    "minimum": 25, "maximum": 31, "mean": 28,
                    "first_anomaly_sec": 50, "anomaly_duration_sec": 20,
                    "cooccurring_sensors": [], "related_alarms": ["PRESSURE_HIGH"],
                    "ocap_ids": ["OCAP-ETCH-PRS"],
                    "threshold_source": "equipment_alarm",
                }],
            })

    _, _, _, _, graph, config = setup_graph(IntegratedEvidence())
    graph.invoke({
        "task_id": config["configurable"]["thread_id"],
        "question": (
            "ETCH-07 CH-B OX-120 식각 속도 저하, 실측 식각 깊이 920 nm, "
            "목표 식각 깊이 1000 nm, 승인 관리 범위 950~1050 nm"
        ),
    }, config)
    report = graph.get_state(config).values["report"]
    assert report.quantitativeResults[0].status == "CALCULATED"
    assert report.quantitativeResults[0].within_control_limit is False
    assert report.sensorAnalysis is not None
    assert report.sensorAnalysis.target_run_id == "RUN-1"


def test_level_1_to_3_education_simulation_stays_separate_in_report():
    class SimulationEvidence(Evidence):
        def analyze_sensor_run(self, context):
            return SensorAnalysis(
                problem="센서 시계열 정량 분석", status="CALCULATED",
                target_run_id="MOCK-RUN-1",
            )

        def simulate_etch_education(self, context, sensor):
            return EducationalSimulationResult.model_validate({
                "status": "SIMULATED", "completed_levels": [1, 2, 3],
                "source_run_id": "MOCK-RUN-1",
                "formulas": ["D[n+1] = D[n] + R[n] * dt / 60"],
                "coefficients": [{
                    "variable": "source_rf", "value": 0.35,
                    "source": "TRACE educational assumption v1",
                    "calibrated": False,
                }],
                "relative_rate_series": [{
                    "offset_sec": 0, "relative_rate": 1,
                    "simulated_process_rate_nm_min": 100,
                    "source": "mock_fab_sensor",
                }],
                "profile_frames": [{
                    "offset_sec": 60, "depth_nm": 95,
                    "opening_width_nm": 80, "aspect_ratio": 1.1875,
                    "simulated_arde_rate_nm_min": 89,
                    "removed_region": [
                        {"x_nm": -40, "y_nm": 0}, {"x_nm": 40, "y_nm": 0},
                        {"x_nm": 40, "y_nm": 95}, {"x_nm": -40, "y_nm": 95},
                    ],
                }],
                "assumptions": ["교육용 가정"],
                "warnings": ["실측값 또는 검증된 예측값이 아닙니다."],
            })

    _, _, _, _, graph, config = setup_graph(SimulationEvidence())
    graph.invoke({
        "task_id": config["configurable"]["thread_id"],
        "question": (
            "ETCH-01 CH-A RCP-OX-ETCH-EDU-01 ARDE 형상 시뮬레이션, "
            "식각 속도 100 nm/min, 패턴 폭 80 nm"
        ),
    }, config)
    report = graph.get_state(config).values["report"]
    assert report.educationalSimulation is not None
    assert report.educationalSimulation.status == "SIMULATED"
    assert report.educationalSimulation.validation_status == "NOT_VALIDATED"
    assert report.sensorAnalysis is not None
    assert any("실측·원인 분석 결과가 아님" in item for item in report.stages[2].findings)
