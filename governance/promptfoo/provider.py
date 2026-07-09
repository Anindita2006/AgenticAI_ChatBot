"""Promptfoo custom Python provider (Day 5, Session 4, Exercises 2 and 4) --
wraps the real chatbot pipeline exactly like giskard_scan.py does, so every
framework in this governance audit exercises the same code path as the live
app, never a mock.

Referenced from promptfooconfig.yaml as `file://provider.py` (verified
against Promptfoo's current docs: providers use the `file://` protocol, not
a `python:` prefix). Signature and return shape match Promptfoo's Python
provider contract: `call_api(prompt, options, context) -> {"output": ...}`.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from pipeline import answer_question


def call_api(prompt: str, options: dict, context: dict) -> dict:
    try:
        result = answer_question(prompt)
        return {"output": result["answer"]}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
