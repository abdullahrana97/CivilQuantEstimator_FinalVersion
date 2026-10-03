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


if __name__ == "__main__":
    unittest.main()
