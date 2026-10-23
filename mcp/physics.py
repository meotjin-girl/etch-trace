"""Physics MCP exposing deterministic, versioned etch calculations."""

import os

from fastmcp import FastMCP
from physics_models import PhysicsInputs, PhysicsResult
from physics_models import evaluate_etch_physics as evaluate
from quantitative_models import (
    EtchQuantitativeInputs,
    MetrologyComparisonInput,
    QuantitativeResult,
    RateSeriesInput,
    ReferenceComparisonInput,
)
from quantitative_models import (
    compare_metrology_to_spec as compare_metrology,
)
from quantitative_models import (
    compare_reference_runs as compare_runs,
)
from quantitative_models import (
    evaluate_etch_quantitative as evaluate_quantitative,
)
from quantitative_models import (
    integrate_etch_rate_series as integrate_rates,
)
from simulation_models import EducationalSimulationInput, EducationalSimulationResult
from simulation_models import simulate_educational_etch as simulate_education

mcp = FastMCP("etch-physics", version="1.0.0")


@mcp.tool
def evaluate_etch_physics(inputs: PhysicsInputs) -> list[PhysicsResult]:
    """Validate zero-order etch outcomes from explicit measurements.

    Solves expected removal depth, measured average etch rate, and target-to-mask
    selectivity. Requires explicit time, thickness, or rate inputs with units. It
    reports missing/invalid inputs and does not infer equipment failure, time-varying
    rates, recipe changes, or lot disposition.
    """
    return evaluate(inputs)


@mcp.tool
def compare_reference_runs(inputs: ReferenceComparisonInput) -> QuantitativeResult:
    """Compare a target value with earlier normal runs under identical scope.

    Solves baseline mean/std, absolute and relative deviation, and z-score when the
    variance is meaningful. Future, abnormal, or non-comparable runs are excluded.
    Without an approved control limit it does not issue a pass/fail decision.
    """
    return compare_runs(inputs)


@mcp.tool
def integrate_etch_rate_series(inputs: RateSeriesInput) -> QuantitativeResult:
    """Integrate explicitly supplied interval etch rates into cumulative depth.

    Solves D(t) only from measured rates or clearly marked simulation assumptions.
    RF, gas, pressure, or a single average rate are never converted into an invented
    time-resolved rate series.
    """
    return integrate_rates(inputs)


@mcp.tool
def compare_metrology_to_spec(inputs: MetrologyComparisonInput) -> QuantitativeResult:
    """Compare measured etch output with its target and approved control limit.

    Solves absolute/relative error and approved-limit membership. Missing metrology
    or an unapproved/missing limit returns INSUFFICIENT_DATA and never an automatic
    recipe, equipment, hold, release, or pass/fail action.
    """
    return compare_metrology(inputs)


@mcp.tool
def analyze_etch_quantitatively(inputs: EtchQuantitativeInputs) -> list[QuantitativeResult]:
    """Run supported v2 etch analyses without filling absent measurements.

    Solves measured-versus-target depth validation and explicit R(t) integration.
    Each unavailable analysis returns INSUFFICIENT_DATA; sensor values are never used
    to fabricate metrology or an etch-rate series.
    """
    return evaluate_quantitative(inputs)


@mcp.tool
def simulate_educational_etch(
    inputs: EducationalSimulationInput,
) -> EducationalSimulationResult:
    """Run explicitly unvalidated Level 2/3 educational etch simulation.

    Level 2 applies declared assumption coefficients to relative RF, pressure, gas,
    and temperature changes. Level 3 applies a declared empirical ARDE coefficient,
    then Level 1 integrates the simulated rate. The 2D output is only a fixed-width
    rectangular removal diagram: it does not predict bowing, taper, sidewall angle,
    equipment failure, recipe action, or lot disposition. Results are always marked
    SIMULATED and NOT_VALIDATED.
    """
    return simulate_education(inputs)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")))
