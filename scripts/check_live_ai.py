"""Optional real Groq smoke test. Uses your account's API quota."""
from pathlib import Path
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai.providers import AIError, DEFAULT_MODEL, chat
from core.calculations import default_inputs, make_record


def main():
    settings = {}
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        settings = tomllib.loads(secrets.read_text(encoding="utf-8"))
    key = os.getenv("GROQ_API_KEY") or settings.get("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL") or settings.get("GROQ_MODEL", DEFAULT_MODEL)
    if not key or "paste-" in key:
        print("Set GROQ_API_KEY in .streamlit/secrets.toml or the environment first.")
        return 1
    try:
        print(f"Checking direct Groq chat: {model}")
        result = chat(key, model, "In one sentence, explain why plaster thickness affects mortar quantity.")
        print(result["answer"])
        print("Checking the CrewAI single-agent workflow (uses additional quota)…")
        from ai.workflow import run_review
        review = run_review(make_record("Plaster", default_inputs("Plaster")),
                            "Use the recalculation tool and briefly review the plaster estimate.",
                            None, key, model, "Single agent")
        print(review["answer"])
        print("Tool events:", review["events"])
        print("Live requests completed. Read the outputs; this is a connectivity check, not an accuracy guarantee.")
        return 0
    except AIError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
