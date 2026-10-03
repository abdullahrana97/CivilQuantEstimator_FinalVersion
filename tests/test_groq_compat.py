"""Regression for Groq rejecting CrewAI cache metadata; no live API calls."""
import copy
import os
import unittest
from unittest.mock import patch
from ai.providers import crew_llm, DEFAULT_MODEL

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")


class GroqCompatibilityTests(unittest.TestCase):
    def test_preparation_strips_marker_without_changing_history_or_tools(self):
        llm = crew_llm("test-key-not-a-real-key", DEFAULT_MODEL)
        messages = [
            {"role": "system", "content": "Civil assistant", "cache_breakpoint": True},
            {"role": "assistant", "content": "", "cache_breakpoint": True,
             "tool_calls": [{"id": "call1", "type": "function", "function": {"name": "check", "arguments": "{}"}}]},
            {"role": "tool", "content": "Checked", "tool_call_id": "call1"},
        ]
        original = copy.deepcopy(messages)
        tools = [{"type": "function", "function": {"name": "check", "description": "Check", "parameters": {"type": "object", "properties": {}}}}]
        params = llm._prepare_completion_params(messages, tools=tools, skip_file_processing=True)
        self.assertTrue(all("cache_breakpoint" not in msg for msg in params["messages"]))
        self.assertEqual(messages, original)
        self.assertEqual(params["messages"][1]["tool_calls"], messages[1]["tool_calls"])
        self.assertEqual(params["messages"][2]["tool_call_id"], "call1")
        self.assertEqual(params["tools"], tools)

    def test_actual_completion_boundary_has_no_cache_marker(self):
        import litellm
        llm = crew_llm("test-key-not-a-real-key", DEFAULT_MODEL)
        response = litellm.ModelResponse(choices=[{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "Checked the estimate."}}])
        messages = [{"role": "system", "content": "Check the estimate", "cache_breakpoint": True},
                    {"role": "user", "content": "Review plaster", "cache_breakpoint": True}]
        with patch("litellm.completion", return_value=response) as completion:
            self.assertEqual(llm.call(messages), "Checked the estimate.")
        outgoing = completion.call_args.kwargs["messages"]
        self.assertTrue(all("cache_breakpoint" not in msg for msg in outgoing))
        self.assertTrue(messages[0]["cache_breakpoint"])

    def test_native_agent_recalculation_has_valid_schema_and_executes(self):
        import litellm
        from ai.workflow import EstimateReviewFlow
        from core.calculations import make_record, default_inputs
        record = make_record("Plaster", default_inputs("Plaster"))
        llm = crew_llm("test-key-not-a-real-key", DEFAULT_MODEL)
        tool_response = litellm.ModelResponse(choices=[{"index": 0, "finish_reason": "tool_calls",
            "message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": "call_test", "type": "function", "function": {
                    "name": "recalculate_submitted_estimate", "arguments": '{"scope":"submitted"}'}}
            ]}}])
        final_response = litellm.ModelResponse(choices=[{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "General guidance: quantities checked; confirm your specification."}}])
        with patch("litellm.completion", side_effect=[tool_response, final_response]) as completion:
            result = EstimateReviewFlow(record, "Check quantities", None, llm).kickoff()
        self.assertTrue(any(e["tool"] == "recalculate_submitted_estimate" for e in result["events"]))
        self.assertEqual(record["result"], result["result"])
        outgoing = completion.call_args_list[0].kwargs
        tool = next(t for t in outgoing["tools"] if t["function"]["name"] == "recalculate_submitted_estimate")
        self.assertIn("scope", tool["function"]["parameters"]["properties"])
        for call in completion.call_args_list:
            self.assertTrue(all("cache_breakpoint" not in msg for msg in call.kwargs["messages"]))


if __name__ == "__main__":
    unittest.main()
