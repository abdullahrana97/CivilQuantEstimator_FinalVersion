# Build validation

Validation date: **3 October 2026**. This record distinguishes local evidence from checks that still need your account and deployment.

## Completed

| Check | Result |
| --- | --- |
| Isolated Linux installation | Installed on CPython **3.11.16** |
| Dependency consistency | All installed packages passed `uv pip check` |
| Windows Python 3.11 dependency resolution | Succeeded for `x86_64-pc-windows-msvc`; this is a resolver check, not a Windows execution test |
| Python compilation | App, core, AI, scripts and tests compiled |
| Automated suite | **25 tests passed** |
| Formula cases | Independent brick geometry, plaster area, concrete ratio conservation and physical steel mass |
| Input validation | Negative, non-finite, boolean and fractional-count inputs rejected; excess opening area rejected |
| Project restore | Saved result tampering ignored; inputs recalculated; malformed imports rejected |
| Rounding/pricing | Bags aggregated before rounding; missing rates stay unpriced |
| Actual FAISS search | Known vectors ranked correctly; separate indexes retained separate passages |
| Actual MiniLM model | Downloaded public model and encoded sample text on CPU; **384-dimensional vectors** |
| Real demo retrieval | Three chunks indexed; a plaster-thickness query retrieved the passage containing **15 mm** |
| Citation/error behavior | Unknown source IDs rejected; uncited document-only answers withheld; no-hit answers make no model call |
| CrewAI execution | One-agent Flow executed the real Python recalculation tool with a scripted LLM; three-agent mode completed all three tasks |
| CrewAI storage controls | Flow auto-memory opt-out and per-run replay storage covered by tests |
| Streamlit UI | All six pages rendered without a key; save, restore, remove and PDF actions passed |
| Desktop browser | Overview, takeoff submission and project schedule inspected at 1440px |
| Phone browser | 390px viewport inspected; document width matched viewport width and sidebar control remained visible |
| PDF layout | Three-page sample rendered and visually inspected after embedding fonts |

## Important boundaries

**No live Groq inference was performed during this build**, because no user API key was supplied. The tests substitute scripted model responses. Model configuration was instantiated as `groq/openai/gpt-oss-120b` and current primary documentation was checked, but only a live account test can confirm actual request success, rate limits and tool-following behavior.

Run `python scripts/check_live_ai.py` after adding your key. Then use the demo specification to test document Q&A and the three-agent review in the UI. Do not submit an API key in a public repository.

**No GitHub repository was created and no Streamlit Cloud deployment was performed.** The requested instructions are provided in `START_HERE.md`. The target is Linux x86_64 / Python 3.11, with an official CPU-only PyTorch wheel. The cloud resource budget and concurrent-user behavior have not been load-tested.

**Engineering and RAG accuracy are not certified.** Formula tests establish the implemented mathematical behavior for the tested cases, not compliance with a measurement standard. A valid citation ID does not prove entailment. The original v1 utility files were not available for result-by-result comparison.

## Selected installed versions

| Package | Version |
| --- | --- |
| Streamlit | 1.65.0 |
| CrewAI | 1.15.23 |
| Groq SDK | 1.7.0 |
| Sentence Transformers | 6.1.0 |
| FAISS CPU | 1.15.1 |
| NumPy | 2.4.6 |
| PyTorch | 2.8.0+cpu on the Linux target |
| pypdf | 6.19.0 |
| ReportLab | 5.0.1 |

`constraints.txt` records resolved transitive versions. Re-run the suite and live checks when upgrading the stack, especially CrewAI's internal memory/replay integration points.
