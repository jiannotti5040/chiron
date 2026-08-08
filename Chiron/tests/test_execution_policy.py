# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Regression gates for the model/console execution boundary.

Run: python3 Chiron/tests/test_execution_policy.py
"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import assistant_server
import console_server
import president_grow as pg


def _model_action(action, args=None):
    cfg = pg.LLMConfig(provider="gemini", api_key="TEST", model="test",
                       base_url=pg.DEFAULTS["gemini"][0])
    plan = json.dumps({"action": action, "args": args or {}, "say": "model response"})
    return assistant_server.chat("untrusted request", cfg=cfg, transport=pg._mock_gemini(plan))


def test_model_json_cannot_dispatch_an_arbitrary_script():
    result = _model_action("run", {"module": "arbitrary_script", "argv": ["now"]})
    assert "run" not in assistant_server.ACTIONS
    assert result["policy"] == "escalated"
    assert result["result"]["status"] == "escalated"
    assert result["reply"] == result["result"]["reason"]


def test_model_json_cannot_invoke_growth():
    result = _model_action("grow", {"target": "/tmp/never-run"})
    assert result["policy"] == "escalated"
    assert result["result"]["action"] == "grow"


def test_unknown_model_action_is_refused():
    result = _model_action("arbitrary_script")
    assert result["policy"] == "refused"
    assert result["result"]["status"] == "refused"


def test_console_escalates_growth_without_spawning_a_process():
    with patch.object(console_server.subprocess, "run",
                      side_effect=AssertionError("blocked request reached subprocess")):
        result = console_server.run("grow_clean", ["file"], "./notes.txt")
    assert result["ok"] is False
    assert result["policy"] == "escalated"


def test_console_refuses_unlisted_script_and_option_injection():
    with patch.object(console_server.subprocess, "run",
                      side_effect=AssertionError("blocked request reached subprocess")):
        script = console_server.run("legal_corpus", ["selftest"])
        options = console_server.run("chiron", ["collapse"], "--memory /tmp/other.json")
    assert script["policy"] == "refused"
    assert options["policy"] == "refused"


def test_console_records_read_only_input_as_a_redacted_witness():
    import run_ledger

    completed = type("Completed", (), {
        "returncode": 0, "stdout": "safe output", "stderr": "",
    })()
    with patch.object(console_server.subprocess, "run", return_value=completed), \
         patch.object(run_ledger, "record") as record:
        result = console_server.run("chiron", ["collapse"], "private input 2 4 6 8")
    assert result["ok"] is True
    assert record.call_args.kwargs["redact"] is True
    assert record.call_args.kwargs["verdict"] == "exit 0"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok -", fn.__name__)
    print("ALL PASSED (%d)" % len(fns))
