# Architecture and data boundaries

The original project was a calculator plus an LLM answer. This version adds a retrieval pipeline and tool-using agent reviews. The agents run inside the app only when a user starts a review.

## Calculation path

Streamlit form -> numeric validation -> Python formula -> saved takeoff snapshot -> combined material schedule -> export.

An LLM cannot overwrite the snapshot. Project JSON imports recalculate every result from validated inputs. Rates are supplied by the user. Full precision is retained during calculations; rounding is for display and procurement quantities.

## Document path

PDF/TXT/MD -> extracted text with filename/page -> chunks of up to 200 tokenizer tokens with 32-token overlap -> normalized MiniLM embeddings -> FAISS inner-product search.

Chunk boundaries use tokenizer offsets into the extracted text, preserving wording and casing. Each retrieved passage has an ID such as `S0001`. The same ID can exist in a different session/index; it is only meaningful within its accompanying source snapshot.

Document-only chat retrieves up to three passages at cosine similarity >= 0.25. No relevant hits means an abstention without a model request. The model returns structured answer text and source IDs. Unknown IDs are rejected. An uncited document-only response is replaced with an abstention. These controls do not prove semantic support; the UI exposes the passages for checking.

## Agent path

`EstimateReviewFlow` has four stages:

1. `validate`: recalculate the selected record with Python.
2. `retrieve`: gather initial document evidence.
3. `review`: run a one-agent or three-agent sequential Crew.
4. `package`: validate cited IDs and package the AI text, unchanged quantities, sources and action log.

The tools are real `crewai.tools.tool` functions:

- `search_project_documents(query)` searches only the current user's FAISS index.
- `recalculate_submitted_estimate()` runs the fixed Python calculator on the selected snapshot.

The model chooses tool calls inside CrewAI's bounded execution loop. Validation and initial retrieval are guaranteed workflow steps; additional tool use is selected by the model. The UI records actual tool calls rather than simulating an agent conversation.

Single-agent mode minimizes calls. Three-agent mode separates evidence analysis, quantity review and report writing. It may exceed free-tier token limits even when the number of requests is small. Each agent has a small iteration limit and timeout; CrewAI also applies its own bounded transient-error retry policy.

## Session and provider isolation

- Only the public embedding model and its lock are cached globally.
- Documents, FAISS indexes, API-key overrides, messages and project records live in Streamlit session state.
- A user's Groq key is passed directly to the request/LLM constructor; it is not written to process environment variables.
- CrewAI memory and planning are disabled. The Flow's auto-memory backend is opted out.
- The default shared replay output handler is replaced by a per-run in-memory store. This uses two internal integration points in the pinned CrewAI release: `_skip_auto_memory` and `_task_output_handler`. Tests cover these; re-check them before upgrading CrewAI.
- CrewAI telemetry/tracing and Hugging Face telemetry are disabled by default. Framework initialization may create empty local runtime/configuration files. The application does not use these to persist project content.
- Groq receives the question, selected estimate and retrieved passages needed for AI generation. Review provider data policies before sending confidential project information.
- There is no account database or tenant authentication in this demo. Per-session throttling is a convenience, not an organization-wide abuse-prevention system.

## Before a commercial launch

Complete live Groq tests, verify the target Streamlit deployment's memory usage and concurrency, evaluate retrieval on representative project documents, have the formulas reviewed by a civil engineer, and decide how user accounts and durable project storage should work. Add service monitoring and organization-level quotas if making a shared API key public. The current package does not claim certified engineering, production load testing or a paid-service uptime guarantee.
