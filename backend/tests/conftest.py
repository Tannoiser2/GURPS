"""Shared test fixtures and import stubs for the test suite.

Stubs for heavy external packages (anthropic, openai, dotenv, google-genai, pdfplumber)
so tests can import App modules without the real packages installed.
Only installs stubs that are not already present.
"""
import sys
import types


class _Stub:
    """Universal stub: survives any attribute access, call, or type annotation."""
    def __getattr__(self, name: str) -> "_Stub":
        return _Stub()
    def __call__(self, *a, **kw) -> "_Stub":
        return _Stub()
    def __or__(self, other):  # supports X | None annotations
        return _Stub()
    def __class_getitem__(cls, item):
        return cls


def _install_stubs() -> None:
    # dotenv
    if "dotenv" not in sys.modules:
        m = types.ModuleType("dotenv")
        m.load_dotenv = lambda *a, **kw: None  # type: ignore[attr-defined]
        sys.modules["dotenv"] = m

    # anthropic
    if "anthropic" not in sys.modules:
        m = types.ModuleType("anthropic")
        m.Anthropic = _Stub  # type: ignore[attr-defined]
        for exc in ("APIStatusError", "APIConnectionError", "RateLimitError",
                    "APITimeoutError", "BadRequestError"):
            setattr(m, exc, type(exc, (Exception,), {}))
        sys.modules["anthropic"] = m
        sys.modules["anthropic.types"] = types.ModuleType("anthropic.types")

    # google / google.genai
    for mod in ("google", "google.genai", "google.genai.types"):
        if mod not in sys.modules:
            m = types.ModuleType(mod)
            sys.modules[mod] = m

    # openai
    if "openai" not in sys.modules:
        m = types.ModuleType("openai")
        m.OpenAI = _Stub  # type: ignore[attr-defined]
        sys.modules["openai"] = m

    # pdfplumber
    if "pdfplumber" not in sys.modules:
        sys.modules["pdfplumber"] = types.ModuleType("pdfplumber")


_install_stubs()
