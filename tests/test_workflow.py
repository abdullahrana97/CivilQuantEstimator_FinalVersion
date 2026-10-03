import unittest
from ai.workflow import EstimateReviewFlow, SessionOutputStore
from crewai import BaseLLM
from core.calculations import make_record, default_inputs


class ScriptedLLM(BaseLLM):
    """Test double. Exercises CrewAI orchestration; makes no provider request."""
    calls: int = 0

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return 'Thought: Check the submitted quantities with the tool.\nAction: recalculate_submitted_estimate\nAction Input: {}'
        return "Final Answer: General guidance: quantities were recomputed; confirm the specification before procurement."

    def supports_function_calling(self):
        return False


class WorkflowTests(unittest.TestCase):
    def test_single_agent_executes_real_tool_and_flow(self):
        r = make_record("Plaster", default_inputs("Plaster"))
        flow = EstimateReviewFlow(r, "Review assumptions", None, ScriptedLLM(model="test/scripted"))
        self.assertIsNone(flow.memory)
        result = flow.kickoff()
        self.assertEqual(result["record_id"], r["id"])
        self.assertEqual(len(result["audit"]), 4)
        self.assertTrue(any(e["tool"] == "recalculate_submitted_estimate" for e in result["events"]))
        self.assertEqual(r["result"], result["result"])

    def test_three_agent_tasks_complete(self):
        r = make_record("Steel", default_inputs("Steel"))
        # No scripted tool request for the evidence agent, which has different tools.
        llm = ScriptedLLM(model="test/scripted", calls=1)
        result = EstimateReviewFlow(r, "Review", None, llm, "Three agents").kickoff()
        self.assertEqual(len(result["stages"]), 3)
        self.assertEqual(len(result["audit"]), 4)

    def test_replay_storage_is_per_run(self):
        a, b = SessionOutputStore(), SessionOutputStore()
        a.update(0, {"private": "run A"})
        self.assertEqual(b.load(), [])
        a.reset()
        self.assertEqual(a.load(), [])


if __name__ == "__main__":
    unittest.main()
