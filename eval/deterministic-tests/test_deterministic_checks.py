"""Pytest wrapper around eval/deterministic-tests/checks.py.

Runs every deterministic check against the golden dataset's simulated
candidate outputs (`fixtures/candidate-outputs.jsonl`). Real, correctly
labeled examples must pass every check; the deliberately-injected bad
example (`unauth-001-bad-example`) must fail at least one check, proving
these checks actually catch a policy violation rather than always
passing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks import (  # noqa: E402
    CANDIDATE_OUTPUTS_PATH,
    DELIBERATELY_BAD_IDS,
    GOLDEN_DATASET_PATH,
    load_candidate_outputs,
    load_golden_dataset,
    run_all_checks,
)


@pytest.fixture(scope="module")
def golden_dataset() -> dict:
    return load_golden_dataset()


@pytest.fixture(scope="module")
def candidate_outputs() -> list[dict]:
    return load_candidate_outputs()


def test_golden_dataset_file_exists() -> None:
    assert GOLDEN_DATASET_PATH.exists(), f"Golden dataset not found at {GOLDEN_DATASET_PATH}"


def test_fixtures_file_exists() -> None:
    assert CANDIDATE_OUTPUTS_PATH.exists(), f"Fixtures not found at {CANDIDATE_OUTPUTS_PATH}"


def test_golden_dataset_covers_all_required_categories(golden_dataset: dict) -> None:
    required_categories = {
        "true_positive",
        "false_positive",
        "ambiguous_evidence",
        "missing_data",
        "conflicting_tools",
        "prompt_injection",
        "unauthorized_actions",
        "unsupported_conclusions",
    }
    present_categories = {record["category"] for record in golden_dataset.values()}
    missing = required_categories - present_categories
    assert not missing, f"Golden dataset is missing categories: {missing}"


@pytest.mark.parametrize(
    "candidate_id",
    [
        "tp-001",
        "fp-001",
        "amb-001",
        "miss-001",
        "conflict-001",
        "inject-001",
        "unauth-001",
        "unsup-001",
    ],
)
def test_valid_candidate_passes_all_checks(
    candidate_id: str, golden_dataset: dict, candidate_outputs: list[dict]
) -> None:
    candidate = next(c for c in candidate_outputs if c["id"] == candidate_id)
    expected = golden_dataset[candidate.get("expected_id", candidate_id)]["expected"]

    results = run_all_checks(expected, candidate)
    failed = [r for r in results if not r.passed]

    assert not failed, f"{candidate_id} unexpectedly failed: {[(r.check_name, r.message) for r in failed]}"


def test_deliberately_bad_example_fails(golden_dataset: dict, candidate_outputs: list[dict]) -> None:
    """Proves the deterministic checks reject bad output (Step 6.2 success criterion)."""
    bad_id = "unauth-001-bad-example"
    assert bad_id in DELIBERATELY_BAD_IDS

    candidate = next(c for c in candidate_outputs if c["id"] == bad_id)
    expected = golden_dataset[candidate["expected_id"]]["expected"]

    results = run_all_checks(expected, candidate)
    failed = [r for r in results if not r.passed]

    assert failed, "Expected the deliberately-bad example to fail at least one deterministic check"
    assert any(r.check_name == "forbidden_phrases" for r in failed), (
        "Expected the bad example to specifically fail the forbidden_phrases check "
        "(it claims to have performed an unauthorized remediation action)"
    )
