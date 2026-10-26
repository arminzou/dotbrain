"""Exercise the combined journey without a runtime, credentials, or a sandbox."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import test_opencode_delivery as delivery


@pytest.mark.parametrize("runtime,answer,tool", [
    ("opencode", {"type": "text", "part": {"text": "UAT-convention-1"}},
     {"type": "tool_use", "part": {"tool": "read"}}),
    ("pi", {"type": "message_end", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "UAT-convention-1"}]}},
     {"type": "tool_execution_start", "toolName": "read"}),
    ("cursor", {"type": "result", "result": "UAT-convention-1"},
     {"type": "tool_call", "subtype": "started", "tool_call": {"readToolCall": {}}}),
])
@pytest.mark.parametrize("outcome", ["clean", "tool", "wrong_nonce"])
def test_combined_journey_requires_convention_without_tools(runtime, answer, tool, outcome):
    events = [answer] if outcome != "tool" else [tool, answer]
    sandbox = SimpleNamespace(
        model="test/model",
        convention_nonce="wrong" if outcome == "wrong_nonce" else "UAT-convention-1",
        runtime=Mock(return_value=SimpleNamespace(
            returncode=0, stdout="\n".join(map(json.dumps, events)), stderr="")),
        backend=SimpleNamespace(data_root="unused", run=Mock(return_value=SimpleNamespace(stdout="1"))),
    )
    if outcome == "clean":
        delivery.test_unreachable_remote_does_not_block_and_sync_records_locally(sandbox, runtime)
        assert sandbox.backend.run.call_count == 2
    else:
        with pytest.raises(AssertionError):
            delivery.test_unreachable_remote_does_not_block_and_sync_records_locally(sandbox, runtime)
        sandbox.backend.run.assert_not_called()
    sandbox.runtime.assert_called_once_with(
        *delivery.ADAPTERS[runtime].headless(sandbox.model, delivery.CONVENTION_PROMPT))
