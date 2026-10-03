"""Civil QuantEstimate v2 - run with: python -m streamlit run app.py"""
import copy
from html import escape
import json
import logging
import os
from pathlib import Path
from threading import RLock
import time

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import streamlit as st
from core.calculations import SPECS, default_inputs, make_record, material_totals
from core.project import MAX_RECORDS, boq_rows, boq_csv, export_project, import_project
from ai.providers import DEFAULT_MODEL, AIError, chat

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Civil QuantEstimate | Build with clarity", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="auto")


def init_state():
    defaults = dict(page="Overview", project_name="Untitled project", records=[], rates={},
                    currency="PKR", knowledge=None, document_names=[], document_warnings=[],
                    messages=[], review=None, ai_calls=0, last_ai_at=0.0,
                    last_record=None, uploader_key=0, pdf=None)
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


init_state()
s = st.session_state
if "pending_import" in s:
    restored = s.pop("pending_import")
    s.project_name, s.records, s.rates, s.currency = restored["name"], restored["records"], restored["rates"], restored["currency"]
    s.last_record = s.records[-1] if s.records else None
    s.review, s.pdf, s.messages = None, None, []


def secret(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name, default)


def theme_css():
    # Inherit actual browser theme colors, including on the first render.
    # st.context.theme may describe the previous render while a theme changes.
    values = dict(card="rgba(54,217,155,.025)", text="inherit", muted="inherit",
                  accent="#27b986", border="rgba(54,217,155,.24)", soft="rgba(54,217,155,.06)",
                  hero="linear-gradient(120deg,rgba(54,217,155,.10),rgba(54,217,155,.015))")
    variables = ":root {" + ";".join(f"--cq-{k}:{v}" for k, v in values.items()) + "}"
    st.html("<style>" + variables + ROOT.joinpath("style.css").read_text(encoding="utf-8") + "</style>")


theme_css()


def heading(title, subtitle, eyebrow="YOUR ESTIMATION WORKSPACE"):
    st.html(f'<div class="eyebrow">{escape(eyebrow)}</div><div class="page-heading">{escape(title)}</div>'
            f'<div class="page-subtitle">{escape(subtitle)}</div>')


def navigate(page):
    s.page = page


def invalidate_export():
    s.pdf = None


def can_call_ai(key):
    if not key:
        st.info("CiviGuide is temporarily unavailable. Please contact the app owner.")
        return False
    if s.ai_calls >= 25:
        st.warning("This session has used its 25 AI runs. Calculators and exports remain available.")
        return False
    remaining = 15 - (time.monotonic() - s.last_ai_at)
    if remaining > 0:
        st.info(f"Please wait {int(remaining) + 1} seconds before the next AI run.")
        return False
    s.last_ai_at = time.monotonic()
    s.ai_calls += 1
    return True


def sources_view(sources):
    for source in sources:
        with st.expander(f"[{source['id']}] {source['filename']} · page {source['page']}"):
            st.write(source["text"])
            st.caption("Source excerpt used for this answer.")


@st.cache_resource(show_spinner=False)
def encoder_resource():
    from sentence_transformers import SentenceTransformer
    import torch
    from ai.rag import MODEL_NAME
    torch.set_num_threads(2)
    return SentenceTransformer(MODEL_NAME, device="cpu", trust_remote_code=False), RLock()


class LockedEncoder:
    def __init__(self, model, lock):
        self.model, self.lock = model, lock

    def encode(self, *args, **kwargs):
        with self.lock:
            return self.model.encode(*args, **kwargs)


api_key = secret("GROQ_API_KEY")
model = secret("GROQ_MODEL", DEFAULT_MODEL)
PAGE_LABELS = {"Overview": "Home", "Quantity takeoff": "Estimate materials", "Knowledge base": "Project documents",
               "CiviGuide AI": "Ask CiviGuide", "Agent review": "Review estimate", "Project & exports": "Reports & saved items"}

with st.sidebar:
    st.html('<div class="brand"><div class="brand-mark">C</div><div><div class="brand-title">Civil<br><span>QuantEstimate</span></div><div class="brand-caption">BUILD WITH CLARITY</div></div></div>')
    st.text_input("Project name", key="project_name", max_chars=100, on_change=invalidate_export)
    st.caption("WORKSPACE")
    for page in ["Overview", "Quantity takeoff", "Knowledge base", "CiviGuide AI", "Agent review", "Project & exports"]:
        st.button(PAGE_LABELS[page], key=f"nav_{page}", type="primary" if s.page == page else "secondary",
                  width="stretch", on_click=navigate, args=(page,))
    st.divider()
    st.caption("Save a project backup from Reports before closing this tab.")


def overview():
    st.html('<div class="hero"><span class="pill">YOUR NEXT BUILD STARTS HERE</span>'
            '<h1>From quantities<br>to <span>clear decisions.</span></h1>'
            '<p>Estimate materials, explore your project documents, and review the details with your civil engineering AI workspace.</p>'
            '<div class="wire" aria-hidden="true"></div></div>')
    cards = [("Saved takeoffs", len(s.records), "In your current project"),
             ("Indexed documents", len(s.document_names), "Ready for source-based Q&A"),
             ("Materials", len(material_totals(s.records)), "Combined across takeoffs"),
             ("Reviews", int(s.review is not None), "Your latest estimate check")]
    for col, (label, value, note) in zip(st.columns(4), cards):
        with col:
            st.html(f'<div class="stat"><div class="stat-label">{label}</div><div class="stat-value">{value}</div><div class="stat-note">{note}</div></div>')
    st.html('<div class="section-head"><h2>Start with an estimate</h2></div>')
    features = [("1 / ESTIMATE", "Calculate your materials", "Choose brickwork, plaster, concrete or steel. Enter dimensions and save your result.", "Quantity takeoff"),
                ("2 / DOCUMENTS · OPTIONAL", "Add your specification", "Upload your own specification or notes so CiviGuide can answer using your project documents.", "Knowledge base"),
                ("3 / REVIEW · OPTIONAL", "Check your estimate", "Get a simple review of a saved estimate before downloading your report.", "Agent review")]
    for col, (number, title, desc, target) in zip(st.columns(3), features):
        with col, st.container(border=True):
            st.html(f'<div class="feature-number">{number}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div>')
            st.button(PAGE_LABELS[target] + " →", key=f"open_{target}", width="stretch",
                      on_click=navigate, args=(target,))
    st.html('<div class="section-head"><h2>Recent takeoffs</h2></div>')
    if s.records:
        st.dataframe([dict(Item=r["label"], Module=r["module"], Saved=r["created_at"]) for r in s.records[-5:][::-1]], hide_index=True, width="stretch")
    else:
        st.info("Start with a quantity takeoff. Your saved items will appear here.")
    st.caption("All calculations use explicit estimating assumptions. AI reviews are advisory; verify project specifications before use.")


def takeoff():
    heading("Estimate materials", "Choose a material, enter your measurements in metres, and calculate. Each result is saved automatically.")
    module = st.selectbox("What are you estimating?", list(SPECS), key="takeoff_module")
    descriptions = {"Brickwork": "Set actual brick dimensions and joint allowance for your local material.",
                    "Plaster": "Count each plastered face as a surface. Openings are a total across every surface.",
                    "Concrete": "Nominal material quantities only. The selected ratio does not certify a concrete strength grade.",
                    "Steel": "Bar mass from an approved cut length. This does not generate a full bar bending schedule."}
    st.html(f'<div class="status-note">{descriptions[module]}</div>')
    with st.form(f"takeoff_{module}"):
        label = st.text_input("Item name", value=f"{module} item", max_chars=100)
        inputs = {}
        advanced_keys = {"wastage", "brick_length_mm", "brick_width_mm", "brick_height_mm", "joint_mm",
                         "dry_factor", "cement_density", "bag_kg", "steel_density"}
        basic = [(key, spec) for key, spec in SPECS[module].items() if key not in advanced_keys]
        advanced = [(key, spec) for key, spec in SPECS[module].items() if key in advanced_keys]
        def fields(items):
            cols = st.columns(2)
            for index, (key, spec) in enumerate(items):
                with cols[index % 2]:
                    if "options" in spec:
                        inputs[key] = st.selectbox(spec["label"], spec["options"], index=spec["options"].index(spec["default"]))
                    else:
                        cast = int if spec["integer"] else float
                        inputs[key] = st.number_input(spec["label"], min_value=cast(spec["minimum"]), max_value=cast(spec["maximum"]),
                                                      value=cast(spec["default"]), step=cast(spec["step"]))
        fields(basic)
        with st.expander("Material settings & wastage (check before ordering)"):
            st.caption("These defaults affect the result. Adjust them for your materials and project specification.")
            fields(advanced)
        submitted = st.form_submit_button("Calculate & save", type="primary", width="stretch")
    if submitted:
        try:
            if len(s.records) >= MAX_RECORDS:
                raise ValueError("The project has 100 takeoffs. Remove an item or start another project.")
            record = make_record(module, inputs, label)
            s.records.append(record)
            s.last_record = record
            s.pdf = None
            st.success("Takeoff calculated and added to your project.")
        except ValueError as exc:
            st.error(str(exc))
    if s.last_record:
        record = s.last_record
        st.subheader(f"Saved result · {record['label']}")
        st.caption("This result uses the saved inputs below. Editing the form does not change it until you calculate again.")
        cols = st.columns(min(3, len(record["result"]["materials"])))
        for col, (material, quantity) in zip(cols, record["result"]["materials"].items()):
            col.metric(material, f"{quantity:,.3f}")
        with st.expander("Show inputs, formulas and assumptions"):
            st.json(record["inputs"])
            st.dataframe([{"Result": k, "Value": v} for k, v in record["result"]["metrics"].items()], hide_index=True)
            for line in record["result"]["formulas"] + record["result"]["notes"]:
                st.write("• " + line)
        st.button("View reports & saved items →", on_click=navigate, args=("Project & exports",))


def knowledge():
    from ai.rag import read_documents, chunk_pages, KnowledgeIndex
    heading("Project documents", "Upload your specification or notes, then click Prepare documents. CiviGuide can use them to answer questions and check estimates.")
    st.caption("PDF / TXT / MD · max 5 files · 5 MB per file · 10 MB total · 100 pages per PDF · 400 chunks")
    uploads = st.file_uploader("Choose project documents", type=["pdf", "txt", "md"], accept_multiple_files=True,
                               key=f"docs_{s.uploader_key}")
    build = st.button("Prepare documents", type="primary", width="stretch", disabled=not uploads)
    if build:
        try:
            files = [(f.name, f.getvalue()) for f in uploads]
            with st.spinner("Preparing your documents. The first upload may take longer…"):
                pages, warnings = read_documents(files)
                encoder, lock = encoder_resource()
                with lock:
                    passages = chunk_pages(pages, encoder.tokenizer)
                index = KnowledgeIndex(passages, LockedEncoder(encoder, lock))
            s.knowledge = index
            s.document_names = list(dict.fromkeys(p[0] for p in pages))
            s.document_warnings = warnings
            s.messages = []
            s.review = None
            s.pdf = None
            st.success(f"{len(s.document_names)} document(s) ready to use.")
            st.button("Ask about your documents →", on_click=navigate, args=("CiviGuide AI",))
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Your documents could not be prepared. Try uploading one smaller text-based file. Previously prepared documents remain available.")
    for warning in s.document_warnings:
        st.warning(warning)
    if s.knowledge:
        st.write("**Ready documents:** " + ", ".join(s.document_names))
        with st.form("retrieval_preview"):
            query = st.text_input("Try a document search", placeholder="What plaster thickness does the specification require?")
            search = st.form_submit_button("Find passages")
        if search and query.strip():
            from ai.rag import source_dict
            hits = s.knowledge.search(query)
            if hits:
                sources_view([source_dict(h) for h in hits])
            else:
                st.info("No closely matching passage was found. Try a more specific question.")
        if st.button("Clear documents and related AI answers"):
            s.knowledge, s.document_names, s.document_warnings = None, [], []
            s.messages, s.review, s.pdf = [], None, None
            s.uploader_key += 1
            st.rerun()
    st.caption("Relevant document excerpts and estimate details are sent to the AI service when you request an answer. Scanned pages and engineering drawings are not supported.")


def assistant_page():
    heading("CiviGuide AI", "Ask about your documents or get a clear explanation of your latest estimate.")
    use_docs = st.checkbox("Answer using my project documents", value=s.knowledge is not None, disabled=s.knowledge is None)
    mode = "Documents only" if use_docs else "General civil guidance"
    if mode == "Documents only" and not s.knowledge:
        st.info("Upload and prepare a file in Project documents to ask questions about it.")
    if s.last_record:
        st.caption(f"Calculation context: {s.last_record['label']} ({s.last_record['module']})")
    for message in s.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["text"])
            if message.get("mode"):
                st.caption(message["mode"])
            sources_view(message.get("sources", []))
    question = st.chat_input("Ask a civil engineering question…", max_chars=2000)
    if question:
        if mode == "Documents only" and not s.knowledge:
            st.warning("Please prepare a project document first.")
            return
        if not can_call_ai(api_key):
            return
        s.messages.append(dict(role="user", text=question, mode=mode))
        with st.chat_message("user"):
            st.write(question)
        try:
            with st.spinner("Finding evidence and preparing your answer…"):
                hits = s.knowledge.search(question) if mode == "Documents only" else []
                context = json.dumps(s.last_record, ensure_ascii=False) if s.last_record and mode != "Documents only" else ""
                result = chat(api_key, model, question, context=context, hits=hits, document_only=mode == "Documents only")
            s.messages.append(dict(role="assistant", text=result["answer"], sources=result["sources"], mode=mode))
            s.messages = s.messages[-20:]
            with st.chat_message("assistant"):
                st.markdown(result["answer"])
                sources_view(result["sources"])
        except AIError as exc:
            st.error(str(exc))
    st.caption("Each question is answered independently. Restate the topic in follow-up questions. Source IDs are checked; this does not guarantee that every AI claim is supported.")


def agents_page():
    heading("Review estimate", "Choose a saved estimate and run a check. CiviGuide checks the quantities and assumptions, using your documents when available.")
    if not s.records:
        st.info("Save a takeoff first. The agents review the measurements you provide.")
        return
    labels = {r["id"]: f"{i}. {r['label']} · {r['module']}" for i, r in enumerate(s.records, 1)}
    record_id = st.selectbox("Takeoff to review", list(labels), format_func=lambda rid: labels[rid])
    record = next(r for r in s.records if r["id"] == record_id)
    with st.expander("Review options"):
        team_review = st.checkbox("Use a team of three agents for a detailed review", value=False)
        st.caption("A team review takes longer and uses more AI requests.")
        question = st.text_area("Anything specific to check?", value="Check the assumptions, compare with any uploaded specification, and list missing information before procurement.", max_chars=1200)
    mode = "Three agents" if team_review else "Single agent"
    if not s.knowledge:
        st.info("No project documents added. The review will check your estimate and assumptions. Add a specification in Project documents to compare its requirements.")
    if st.button("Run estimate review", type="primary", width="stretch"):
        if not question.strip():
            st.warning("Enter a review question.")
        elif can_call_ai(api_key):
            try:
                with st.status("Review in progress…", expanded=True) as status:
                    st.write("Checking your saved measurements and available project documents…")
                    from ai.workflow import run_review
                    result = run_review(copy.deepcopy(record), question, s.knowledge, api_key, model, mode)
                    result.update(model=model, label=record["label"], question=question)
                    s.review, s.pdf = result, None
                    status.update(label="Review complete", state="complete", expanded=False)
            except AIError as exc:
                st.error(str(exc))
            except Exception:
                logging.getLogger(__name__).error("CQ_REVIEW_START_FAILED: review service initialization failed")
                st.error("The review service could not start. Please contact the app owner. Your estimate is still saved.")
    if s.review:
        review = s.review
        st.subheader(f"Review · {review['label']}")
        st.caption(f"Completed in {review['elapsed_seconds']} seconds")
        if record_id != review["record_id"]:
            st.info("The displayed review belongs to a different saved item. Run a review to check your current selection.")
        st.markdown(review["answer"])
        with st.expander("Workflow record and actual tool calls"):
            for event in review["audit"]:
                st.write(event)
            st.json(review["events"])
            st.caption("This shows actions and outputs, not hidden reasoning. An agent may use only some of the available tools.")
        with st.expander("Individual agent outputs"):
            for stage in review["stages"]:
                st.write("**" + stage["agent"] + "**")
                st.markdown(stage["answer"])
        st.subheader("Retrieved evidence")
        sources_view(review["sources"])


def project_page():
    heading("Reports & saved items", "View your materials, add supplier prices if needed, and download your report.")
    s.currency = st.selectbox("Currency label (no conversion)", ["PKR", "USD", "EUR", "GBP", "AED", "SAR"],
                              index=["PKR", "USD", "EUR", "GBP", "AED", "SAR"].index(s.currency), on_change=invalidate_export)
    if s.records:
        st.dataframe([dict(ID=r["id"], Item=r["label"], Module=r["module"], Saved=r["created_at"]) for r in s.records], hide_index=True, width="stretch")
        totals = material_totals(s.records)
        with st.expander("Enter material prices", expanded=False):
            st.caption("Use your supplier's price per displayed unit. Zero means unpriced. These are not live market prices.")
            with st.form("rates_form"):
                rates = {}
                for material in sorted(totals):
                    rates[material] = st.number_input(f"{material} · {s.currency} per unit", min_value=0.0, max_value=1e9,
                                                     value=float(s.rates.get(material, 0)), step=1.0)
                if st.form_submit_button("Save material prices"):
                    s.rates, s.pdf = rates, None
        rows = boq_rows(s.records, s.rates)
        st.subheader("Material schedule")
        st.dataframe(rows, hide_index=True, width="stretch")
        unpriced = sum(row["Your unit rate"] is None for row in rows)
        st.metric("Priced-material subtotal", f"{s.currency} {sum(row['Material amount'] or 0 for row in rows):,.2f}")
        st.caption(f"{unpriced} material(s) unpriced. Labour, equipment, transport, tax and overheads are excluded. Cement bags are rounded up after combining items by bag size.")
        c1, c2 = st.columns(2)
        c1.download_button("Download project JSON", export_project(s.project_name, s.records, s.rates, s.currency),
                            file_name="civil_quantestimate_project.json", mime="application/json", width="stretch")
        c2.download_button("Download material CSV", boq_csv(s.records, s.rates),
                            file_name="civil_quantestimate_materials.csv", mime="text/csv", width="stretch")
        if st.button("Prepare PDF report", width="stretch"):
            from core.reports import make_pdf
            with st.spinner("Preparing your report…"):
                s.pdf = make_pdf(s.project_name, s.records, s.rates, s.currency, s.review)
        if s.pdf:
            st.download_button("Download PDF report", s.pdf, file_name="civil_quantestimate_report.pdf", mime="application/pdf", type="primary", width="stretch")
        with st.expander("Remove a saved takeoff"):
            labels = {r["id"]: f"{r['label']} · {r['id']}" for r in s.records}
            remove_id = st.selectbox("Item to remove", list(labels), format_func=lambda rid: labels[rid])
            if st.button("Remove selected item"):
                s.records = [r for r in s.records if r["id"] != remove_id]
                if s.last_record and s.last_record["id"] == remove_id:
                    s.last_record = s.records[-1] if s.records else None
                if s.review and s.review["record_id"] == remove_id:
                    s.review = None
                s.pdf = None
                st.rerun()
    else:
        st.info("There are no saved takeoffs yet. Calculate one or import a project below.")
    with st.expander("Restore a project JSON"):
        uploaded = st.file_uploader("Choose an exported v2 project", type=["json"], key="project_import")
        replace = st.checkbox("Replace the current project with this file")
        if st.button("Import and recalculate", disabled=not (uploaded and replace)):
            try:
                restored = import_project(uploaded.getvalue())
                # Sidebar widgets have already rendered. Apply their values on the next rerun.
                s.pending_import = restored
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


pages = {"Overview": overview, "Quantity takeoff": takeoff, "Knowledge base": knowledge,
         "CiviGuide AI": assistant_page, "Agent review": agents_page, "Project & exports": project_page}
pages[s.page]()
st.html('<div class="footer">Civil QuantEstimate · Build smarter. Estimate faster.<br>Preliminary quantity estimates with visible assumptions. Verify project requirements before procurement.</div>')
