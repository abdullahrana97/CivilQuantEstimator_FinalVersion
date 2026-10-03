Civil QuantEstimate — simpler interface update

No local execution or Git commands are needed.

1. Extract Civil_QuantEstimate_UI_Update.zip.
2. Open your existing GitHub repository on the main branch.
3. Select Add file > Upload files.
4. Upload app.py and the ai and tests folders from this update together.
   They contain these four replacement files:
   app.py
   ai/providers.py
   ai/workflow.py
   tests/test_ui.py
5. Commit the upload directly to main.
6. Wait for Streamlit to pick up the commit. Refresh the app afterward.
   You do not need to delete or redeploy the app for these Python source changes.
7. Keep GROQ_API_KEY and GROQ_MODEL in Streamlit Settings > Secrets.
   No real API key belongs in the GitHub files.

Changes
- Removed public AI connection settings, key input, model picker and model name.
- Removed the demo specification button and demo references from the interface.
- Clearer navigation labels, simpler calculation forms and optional review settings.
- Material assumptions and wastage remain editable; check them before ordering.
- AI requests use only the owner's server-side configuration.
- The latest review result shows no provider or model name.
- Failed reviews log an error reference, exception type, status and code to server logs.
  These added log entries exclude keys, document content and prompts.

Single-agent review
The exact reported error has not been provided, so this update does not claim
that the cause is fixed. If the review fails, send its red error message and the
CQ_REVIEW_FAILED line with the matching reference from Manage app > Logs.
If it says the service could not start, send the CQ_REVIEW_START_FAILED line.
Existing CrewAI/framework logs may contain more detail: avoid sharing credentials.

Checks performed for this update
- Python syntax compilation passed.
- 11 calculation, import, aggregation and PDF tests passed.
- 3 Streamlit UI tests passed: six-page navigation, calculation/PDF/removal,
  and restored-project handling. These UI checks ran under Python 3.12 in this
  verification environment; the deployment requirements still target 3.11.
- No live Groq request was made. The reported agent failure remains unverified.

Using the app
Estimate materials > choose material > enter measurements > Calculate & save.
Project documents is optional; upload your own text-based specification and
click Prepare documents. Ask CiviGuide works without documents for general civil
questions. Review estimate uses one agent by default; enable three agents under
Review options if needed. Download reports and a project backup from Reports &
saved items. Saved work lasts for the current session unless you export it.
