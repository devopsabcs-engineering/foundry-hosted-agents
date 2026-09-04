"""Step 7.4 -- deploy the preview EvaluationRule continuous-evaluation example
(research.md lines 246-263) against the deployed threat-assessment-agent.

Retention / redaction policy for this experiment (documented per the plan's
instruction, even though minimal): this PoC uses only synthetic,
non-production incident-description test messages -- no real customer or
employee PII flows through the agent in this experiment or in Phases 1-6
generally. Continuous-evaluation run data is retained under Foundry's own
default evaluation-rule storage policy (not independently confirmed in this
session -- see report.md); no additional redaction is applied beyond using
synthetic data, and this rule is disabled/deleted at the end of the
experiment window rather than left running indefinitely against production
traffic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ContinuousEvaluationRuleAction,
    EvaluationRule,
    EvaluationRuleEventType,
    EvaluationRuleFilter,
)
from azure.identity import DefaultAzureCredential

PROJECT_ENDPOINT = os.environ.get(
    "FOUNDRY_PROJECT_ENDPOINT",
    "https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/proj-air-canada-threat-assessment-poc",
)
AGENT_NAME = os.environ.get("AGENT_NAME", "threat-assessment-agent")
RULE_ID = "threat-assessment-continuous-eval-rule"


def main() -> None:
    client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
    result: dict = {"project_endpoint": PROJECT_ENDPOINT, "agent_name": AGENT_NAME, "rule_id": RULE_ID}

    try:
        openai_client = client.get_openai_client()
        eval_object = openai_client.evals.create(
            name="Continuous Threat Assessment Evaluation (PoC)",
            data_source_config={"type": "azure_ai_source", "scenario": "responses"},
            testing_criteria=[
                {
                    "type": "azure_ai_evaluator",
                    "name": "groundedness",
                    "evaluator_name": "builtin.groundedness",
                    "initialization_parameters": {"deployment_name": os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")},
                },
                {
                    "type": "azure_ai_evaluator",
                    "name": "task_adherence",
                    "evaluator_name": "builtin.task_adherence",
                    "initialization_parameters": {"deployment_name": os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")},
                },
            ],
        )
        result["eval_object_id"] = eval_object.id
        result["eval_create_status"] = "succeeded"
    except Exception as exc:  # noqa: BLE001 - this experiment must record every failure mode
        result["eval_create_status"] = "failed"
        result["eval_create_error"] = f"{type(exc).__name__}: {exc}"
        _write(result)
        raise

    try:
        rule = client.evaluation_rules.create_or_update(
            id=RULE_ID,
            evaluation_rule=EvaluationRule(
                display_name="Threat Assessment Continuous Eval Rule (PoC)",
                action=ContinuousEvaluationRuleAction(eval_id=eval_object.id, max_hourly_runs=10),
                event_type=EvaluationRuleEventType.RESPONSE_COMPLETED,
                filter=EvaluationRuleFilter(agent_name=AGENT_NAME),
                enabled=True,
            ),
        )
        result["rule_create_status"] = "succeeded"
        result["rule_id_confirmed"] = rule.id
        result["rule_enabled"] = rule.enabled
    except Exception as exc:  # noqa: BLE001
        result["rule_create_status"] = "failed"
        result["rule_create_error"] = f"{type(exc).__name__}: {exc}"
        _write(result)
        raise

    try:
        fetched = client.evaluation_rules.get(id=RULE_ID)
        result["rule_get_status"] = "succeeded"
        result["rule_get_display_name"] = fetched.display_name
    except Exception as exc:  # noqa: BLE001
        result["rule_get_status"] = "failed"
        result["rule_get_error"] = f"{type(exc).__name__}: {exc}"

    _write(result)


def _write(result: dict) -> None:
    print(json.dumps(result, indent=2))
    out_path = Path(__file__).parent / "results" / "deployment-outcome.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
