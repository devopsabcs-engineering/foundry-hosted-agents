import copy
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "evaluation_gate", Path(__file__).parents[1] / "evaluation_gate.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_result():
    run = {
        "status": "completed",
        "error": None,
        "result_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0, "skipped": 0},
    }
    items = [
        {
            "id": "1",
            "status": "completed",
            "sample": {"error": None},
            "results": [{"name": name, "score": 5, "passed": True} for name in MODULE.METRICS],
        }
    ]
    return run, items


def test_valid_results_pass():
    run, items = valid_result()
    for result in items[0]["results"]:
        result["sample"] = None
    assert MODULE.validate_results(run, items, 1) == dict.fromkeys(MODULE.METRICS, 1.0)


def test_completed_but_all_errored_is_not_success():
    run, items = valid_result()
    run["result_counts"].update(total=8, passed=0, errored=8)
    with pytest.raises(ValueError, match="errored"):
        MODULE.validate_results(run, items, 8)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda run, items: run.update(status="failed"),
        lambda run, items: run.update(error={"message": "failed"}),
        lambda run, items: run["result_counts"].update(skipped=1),
        lambda run, items: items.clear(),
        lambda run, items: items.append(copy.deepcopy(items[0])),
        lambda run, items: items[0]["sample"].update(error={"message": "'NoneType' object is not iterable"}),
        lambda run, items: items[0]["results"].pop(),
        lambda run, items: items[0]["results"][0].update(score=None, passed=None),
        lambda run, items: items[0]["results"][0].update(score=float("nan")),
        lambda run, items: items[0]["results"][0].update(status="error"),
        lambda run, items: items[0]["results"][0].update(sample={"error": {"message": "empty response"}}),
        lambda run, items: items[0]["results"][0].update(score=1, passed=False),
    ],
)
def test_invalid_results_fail_closed(mutation):
    run, items = valid_result()
    mutation(run, items)
    with pytest.raises(ValueError):
        MODULE.validate_results(run, items, 1)
