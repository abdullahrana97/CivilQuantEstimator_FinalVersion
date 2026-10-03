Civil QuantEstimate — Groq agent compatibility fix

Confirmed error
Groq rejected messages.0.cache_breakpoint. CrewAI 1.15.23 adds internal cache
metadata that its LiteLLM route sends through to the Groq endpoint.

Fix
ai/providers.py creates a GroqCompatibleLLM subclass for this app. Its request
preparation strips cache_breakpoint from copied messages. Agent history, source
text and native tool calls remain intact. No process-wide framework patch is used.
Keep the existing pinned requirements; recheck this override if CrewAI is upgraded.

GitHub GUI steps
1. Extract this ZIP.
2. Open the existing repository on main.
3. Add file > Upload files.
4. Drag in the ai and tests folders from this ZIP.
   The only replacement application file is ai/providers.py.
   tests/test_groq_compat.py is a new regression test.
5. Commit directly to main.
6. Wait for Streamlit to detect the commit, then Reboot the app and refresh.
7. Recreate/upload the test project as needed and run a single-agent review.
8. If a different error occurs, send the new error reference and matching log.

Verified
Two tests passed using installed CrewAI 1.15.23 and LiteLLM 1.103.2:
- Request preparation strips the marker without mutating original messages,
  native tool-call data, tool-result IDs or tool schemas.
- The real CrewAI LLM completion path sends clean messages to a mocked LiteLLM
  transport and returns the expected response.
No live Groq call was made. This targets the logged cache_breakpoint rejection;
it does not guarantee that later provider limits or other failures cannot occur.
