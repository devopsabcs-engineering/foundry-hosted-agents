"""Fail closed on incomplete, errored, unscored, or below-policy evaluations."""

import math

METRICS = ("coherence", "groundedness", "task_adherence")


def validate_results(
    run: dict, items: list[dict], expected_count: int, minimum_pass_rate: float = 1.0
) -> dict:
    if expected_count < 1 or not 0 < minimum_pass_rate <= 1:
        raise ValueError("A nonempty dataset and pass rate in (0, 1] are required")
    if run.get("status") != "completed" or run.get("error"):
        raise ValueError(f"Evaluation did not complete successfully: {run.get('error')}")
    counts = run.get("result_counts", {})
    if counts.get("total") != expected_count or counts.get("errored") != 0 or counts.get("skipped") != 0:
        raise ValueError(f"Incomplete or errored evaluation: {counts}")
    if len(items) != expected_count or len({item.get("id") for item in items}) != expected_count:
        raise ValueError("Missing or duplicate evaluation output items")
    passes = dict.fromkeys(METRICS, 0)
    for item in items:
        if item.get("status") != "completed" or item.get("error") or (item.get("sample") or {}).get("error"):
            raise ValueError(f"Response generation failed for item {item.get('id')}: {item.get('sample')}")
        results = item.get("results", [])
        if len(results) != len(METRICS) or {result.get("name") for result in results} != set(METRICS):
            raise ValueError(f"Missing or duplicate evaluator results for item {item.get('id')}")
        for result in results:
            score = result.get("score")
            if (
                result.get("status") == "error"
                or (result.get("sample") or {}).get("error")
                or result.get("error")
                or type(score) not in (int, float)
                or not math.isfinite(score)
                or type(result.get("passed")) is not bool
            ):
                raise ValueError(f"Unscored or errored evaluator result: {result}")
            passes[result["name"]] += int(result["passed"])
    rates = {metric: passed / expected_count for metric, passed in passes.items()}
    if any(rate < minimum_pass_rate for rate in rates.values()):
        raise ValueError(f"Quality threshold {minimum_pass_rate:.0%} not met: {rates}")
    return rates
