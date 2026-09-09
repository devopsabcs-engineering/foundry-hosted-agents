import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from check_conversation import check_conversation


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