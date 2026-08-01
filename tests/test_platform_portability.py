"""Static guards for platform-neutral text and subprocess boundaries."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "dotbrain"


def _keyword_names(call: ast.Call) -> set[str | None]:
    return {keyword.arg for keyword in call.keywords}


def _string_keyword(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value if isinstance(keyword.value.value, str) else None
    return None


def test_production_text_io_is_explicitly_utf8_and_lf() -> None:
    violations: list[str] = []

    for source in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            if not isinstance(call.func, ast.Attribute):
                continue
            if call.func.attr in {"read_text", "write_text"}:
                if _string_keyword(call, "encoding") != "utf-8":
                    violations.append(
                        f"{source.relative_to(SOURCE_ROOT)}:{call.lineno}: encoding must be utf-8"
                    )
            if call.func.attr == "write_text" and _string_keyword(call, "newline") != "\n":
                violations.append(
                    f"{source.relative_to(SOURCE_ROOT)}:{call.lineno}: newline must be LF"
                )
            if call.func.attr == "open":
                mode = "r"
                if call.args and isinstance(call.args[0], ast.Constant):
                    mode = call.args[0].value
                if isinstance(mode, str) and "b" not in mode:
                    if _string_keyword(call, "encoding") != "utf-8":
                        violations.append(
                            f"{source.relative_to(SOURCE_ROOT)}:{call.lineno}: encoding must be utf-8"
                        )
                    writes = any(flag in mode for flag in "wax+")
                    if writes and _string_keyword(call, "newline") != "\n":
                        violations.append(
                            f"{source.relative_to(SOURCE_ROOT)}:{call.lineno}: newline must be LF"
                        )

    assert violations == []


def test_captured_subprocess_output_is_explicitly_decoded() -> None:
    violations: list[str] = []

    for source in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            if not isinstance(call.func, ast.Attribute) or call.func.attr != "run":
                continue
            keywords = _keyword_names(call)
            if "capture_output" in keywords and _string_keyword(call, "encoding") != "utf-8":
                violations.append(
                    f"{source.relative_to(SOURCE_ROOT)}:{call.lineno}: encoding must be utf-8"
                )

    assert violations == []
