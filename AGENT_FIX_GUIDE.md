Civil QuantEstimate — agent fix, revision 2

This package includes BOTH confirmed compatibility fixes:
1. ai/providers.py strips CrewAI cache_breakpoint metadata from outgoing Groq messages.
2. ai/workflow.py gives the recalculation tool an explicit scope input, ensuring
   its schema has properties. It accepts scope="submitted" and recalculates only
   the saved estimate. Agent prompts specify this input.

GitHub GUI installation
1. Download this updated ZIP and extract it.
2. Open the existing repository, main branch.
3. Add file > Upload files.
4. Upload the ai and tests folders from this ZIP.
   Replace ai/providers.py and ai/workflow.py; update tests/test_groq_compat.py.
5. Commit directly to main.
6. Wait for Streamlit to pull the commit, then Reboot the app and refresh.
7. Upload the test specification, save the plaster estimate, and run the review.
No requirements or Secrets changes are required by these fixes.

Verification
All three regression tests passed using CrewAI 1.15.23 and LiteLLM 1.103.2.
The new test runs the actual CrewAI Flow, agent and native tool-call path against
scripted provider responses. It checks the outgoing tool schema and confirms
that the Python recalculation tool executes and the saved result stays unchanged.
The existing tests check removal of cache metadata without changing tool-call
payloads or the agent's original history.
No live Groq request was made; verify the deployed result and report any new error.
