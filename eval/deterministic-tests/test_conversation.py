import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from check_conversation import check_conversation, validate_endpoint


def test_conversation_resends_only_owned_history():
    calls = []
    responses = iter(["Confirmed PILOT-4827", "Your reference was PILOT-4827", "Unknown"])

    def invoke(messages):
        calls.append(messages)
        return next(responses)

    assert check_conversation(invoke, "PILOT-4827")["passed"] == 3
    assert [len(messages) for messages in calls] == [1, 3, 1]
    assert calls[1][0] == calls[0][0]
    assert calls[1][1] == {"role": "assistant", "content": "Confirmed PILOT-4827"}
    assert "PILOT-4827" not in calls[1][-1]["content"]
    assert "PILOT-4827" not in calls[2][0]["content"]


@pytest.mark.parametrize("responses,error", [
    (["Unknown"], "First response"),
    (["PILOT-4827", "Unknown"], "Follow-up lost"),
    (["PILOT-4827", "PILOT-4827", "PILOT-4827"], "Independent request"),
])
def test_conversation_gate_rejects_context_failures(responses, error):
    outputs = iter(responses)
    with pytest.raises(ValueError, match=error):
        check_conversation(lambda messages: next(outputs), "PILOT-4827")


def test_endpoint_allows_staging_and_explicit_workshop():
    validate_endpoint("https://example-staging.services.ai.azure.com/responses")
    validate_endpoint("https://aif-fha-learn-test.services.ai.azure.com/responses", "aif-fha-learn-test")


@pytest.mark.parametrize("endpoint,account", [
    ("https://production.services.ai.azure.com/responses", None),
    ("https://aif-fha-learn-test.services.ai.azure.com/responses", None),
    ("https://production.services.ai.azure.com/responses", "production"),
    ("https://aif-fha-learn-other.services.ai.azure.com/responses", "aif-fha-learn-test"),
    ("https://example-staging.services.ai.azure.com/responses", "aif-fha-learn-test"),
    ("http://aif-fha-learn-test.services.ai.azure.com/responses", "aif-fha-learn-test"),
    ("https://user@aif-fha-learn-test.services.ai.azure.com/responses", "aif-fha-learn-test"),
])
def test_endpoint_rejects_unsafe_or_mismatched_targets(endpoint, account):
    with pytest.raises(ValueError):
        validate_endpoint(endpoint, account)