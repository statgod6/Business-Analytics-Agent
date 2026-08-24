"""Stage-scoped tool mounting.

Tool scope per stage:
  Stage 2      -> Tavily web search + local file read (ingestion happens here)
  Stages 3, 4  -> E2B sandboxed code execution (real computation)
  Stages 1, 5, 6 -> NO tools (pure reasoning / synthesis; interpretation purity
                   is enforced by having no tools at all)
"""
from __future__ import annotations

from langchain_core.tools import tool

from backend.app.config import settings

_E2B_SANDBOX = None


def _get_sandbox():
    """Lazily create one sandbox per process; hold a strong module ref so the
    garbage collector can never finalize it mid-run (see the pooled-resource
    pitfall)."""
    global _E2B_SANDBOX
    if _E2B_SANDBOX is None:
        from e2b_code_interpreter import Sandbox

        _E2B_SANDBOX = Sandbox()
    return _E2B_SANDBOX


@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web for business and industry context. Returns JSON results."""
    if not settings.tavily_api_key:
        return "tool unavailable: set TAVILY_API_KEY in .env"
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    resp = client.search(query=query, max_results=max_results)
    return str(resp.get("results", []))


@tool
def e2b_run_code(code: str) -> str:
    """Execute Python code in a secure sandbox and return stdout/stderr."""
    if not settings.e2b_api_key:
        return "tool unavailable: set E2B_API_KEY in .env"
    execution = _get_sandbox().run_code(code)
    return f"stdout:\n{execution.logs.stdout}\nstderr:\n{execution.logs.stderr}"


@tool
def read_local_file(path: str) -> str:
    """Read a local file (csv/excel/pdf/json/docx) and return its structure."""
    import os

    if not os.path.exists(path):
        return f"file not found: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        import pandas as pd

        df = pd.read_csv(path, nrows=50)
        return f"shape {df.shape}\n{df.head().to_string()}"
    if ext in (".xlsx", ".xls"):
        import pandas as pd

        df = pd.read_excel(path, nrows=50)
        return f"shape {df.shape}\n{df.head().to_string()}"
    if ext == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "")[:2000] for p in pdf.pages[:3])
    if ext == ".docx":
        from docx import Document

        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs[:50])
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()[:5000]


def build_stage_tools(stage: int) -> list:
    """Tools mounted for a stage's mission (the stage-scoped tool belt)."""
    if stage == 2:
        return [tavily_search, read_local_file]
    if stage in (3, 4):
        return [e2b_run_code]
    return []
