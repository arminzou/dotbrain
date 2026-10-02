"""Human layouts preserve result data while remaining usable in small/plain terminals."""
from dataclasses import asdict
import io
import json
import re

import pytest
from rich.console import Console
from typer.testing import CliRunner
from typer.main import get_command

from dotbrain import doctor, presentation
from dotbrain.cli import app
from dotbrain.results import CommandResult, TargetResult, render


def capture(monkeypatch, callback, width=96):
    buffer = io.StringIO()
    monkeypatch.setattr(presentation, "console", lambda: Console(file=buffer, width=width, color_system=None))
    callback()
    value = buffer.getvalue()
    assert "\x1b" not in value
    assert all(len(line) <= width for line in value.splitlines())
    return value


def project(name, runtime="codex", mode="none"):
    return {"project": name, "checkout": None, "brain_only": True, "runtimes": [runtime],
            "beads": {"mode": mode}, "wiring": {}}


def test_operations_put_failures_first_indent_wraps_and_preserve_data(tmp_path, monkeypatch):
    monkeypatch.setattr(presentation.Path, "home", classmethod(lambda cls: tmp_path))
    checkout = str(tmp_path / "repo")
    error = "[red]missing[/red]\nsecond line " + "configuration " * 8
    result = CommandResult("refresh", "partial", targets=[TargetResult(project="healthy", checkout=checkout),
        TargetResult(project="broken", checkout=checkout, status="failure", errors=[error, error],
                     changes=[f"updated {checkout}/.codex/agents/reviewer.toml"])])
    before = asdict(result)
    output = capture(monkeypatch, lambda: render(result), 48)
    assert output.index("broken") < output.index("healthy")
    assert "[red]missing[/red]" in output and "2occurrences" in "".join(output.split())
    assert "~/repo" in output and "./.codex/agents" in output
    assert "Already up to date" in output
    body = output[output.index("  error:"):output.index("  updated")]
    assert all(not line or line.startswith("  ") for line in body.splitlines())
    assert asdict(result) == before


def test_doctor_orders_findings_condenses_runtime_warnings_and_keeps_json(monkeypatch, tmp_path):
    report = doctor.DoctorReport(machine=[doctor.Finding("ok", "git available"),
        doctor.Finding("warn", "claude-code: hook activation unknown", "inspect hooks"),
        doctor.Finding("warn", "codex: hook activation unknown", "inspect hooks")],
        projects={"example": [doctor.Finding("error", "missing link", "run dotbrain refresh")]})
    output = capture(monkeypatch, lambda: presentation.render_doctor(report))
    assert output.index("missing link") < output.index("hook activation unknown")
    assert output.count("hook activation unknown") == 1 and "Claude, Codex" in output
    assert "Fix: run dotbrain refresh" in output and "Next: inspect hooks" in output
    assert "git available" not in output and "1 check passed" in output and "2 warnings" in output
    verbose = capture(monkeypatch, lambda: presentation.render_doctor(report, verbose=True))
    assert "git available" in verbose
    monkeypatch.setattr(doctor, "run_doctor", lambda *args, **kwargs: report)
    runner = CliRunner()
    payloads = []
    for flags in ([], ["-v"]):
        result = runner.invoke(app, ["doctor", "--all", "--home", str(tmp_path), "--json", *flags])
        assert result.exit_code == 1
        payloads.append(json.loads(result.stdout))
    assert payloads[0] == payloads[1] == asdict(doctor.as_result(report))


@pytest.mark.parametrize("different", [False, True])
def test_project_table_shared_footer_or_explicit_differences(monkeypatch, different):
    records = [project("one"), project("two", "claude" if different else "codex", "server" if different else "none")]
    result = CommandResult("projects list", targets=[TargetResult(project=row["project"], data=row) for row in records])
    before = asdict(result)
    output = capture(monkeypatch, lambda: render(result))
    assert "one" in output and "two" in output and "Brain-only" in output
    assert "success" not in output and "2 projects" in output
    if different:
        assert "Runtimes" in output and "Tracker" in output and "Claude" in output and "server" in output
    else:
        assert output.count("Codex") == 1 and "Runtimes: Codex" in output
        assert output.count("none") == 1 and "Tracker: none" in output
    assert asdict(result) == before


def test_catalog_selection_empty_states_and_literal_paths(monkeypatch):
    rows = [{"name": "[red]review[/red]", "selected": True, "source": "/skills/review", "runtimes": ["codex"]}]
    result = CommandResult("skills list", targets=[TargetResult(project="example", scope="catalog", data={"assets": rows})])
    output = capture(monkeypatch, lambda: render(result))
    assert "[red]review[/red]" in output and "Selected" in output and "yes" in output and "1 skill available" in output
    result.targets[0].project = None
    output = capture(monkeypatch, lambda: render(result))
    assert "Selected" not in output
    result.targets[0].data["assets"] = []
    assert "No skills found" in capture(monkeypatch, lambda: render(result))
    empty_db = CommandResult("beads list-db", targets=[TargetResult(scope="remote", data={"databases": []})])
    assert "No databases found" in capture(monkeypatch, lambda: render(empty_db))
    preview = CommandResult("beads sync", targets=[TargetResult(project="example")])
    output = capture(monkeypatch, lambda: render(preview, preview=True))
    assert "Preview" in output and "No actions planned" in output and "Completed" not in output


def test_narrow_tables_preserve_all_fields_without_truncation(monkeypatch):
    rows = [["example", "/long/path/" + "checkout" * 8, "missing .brain"]]
    output = capture(monkeypatch, lambda: presentation.table(presentation.console(), ["Project", "Checkout", "Wiring"], rows), 32)
    compact = "".join(output.split())
    assert "Checkout:" in output and rows[0][1] in compact and "Wiring:" in output


def test_legacy_encoding_escapes_unrepresentable_text_and_uses_ascii_symbols(monkeypatch):
    buffer = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(presentation, "console", lambda: Console(file=buffer, width=80, color_system=None))
    presentation.render_doctor(doctor.DoctorReport(machine=[doctor.Finding("ok", "valid"), doctor.Finding("warn", "file ☃ [red]")]))
    buffer.flush()
    output = buffer.buffer.getvalue().decode("cp1252")
    assert r"\u2603" in output and "[red]" in output and "[ok]" in output


def test_redirected_output_remains_plain_even_with_forced_color(monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    result = CliRunner().invoke(app, ["bootstrap", "--runtime", "invalid"])
    assert result.exit_code == 2 and "\x1b" not in result.stdout


def test_preview_only_changes_text_not_json(capsys):
    result = CommandResult("beads sync", targets=[TargetResult(project="example")])
    render(result, json_output=True, preview=True)
    assert json.loads(capsys.readouterr().out) == asdict(result)


@pytest.mark.parametrize("width", [40, 100])
def test_help_preserves_command_descriptions_and_parameter_records(monkeypatch, width):
    monkeypatch.setattr(presentation, "console", lambda: Console(width=width, color_system=None))
    root = get_command(app)
    def check(command, ctx):
        output = command.get_help(ctx)
        compact = "".join(output.split())
        assert all(len(line) <= width for line in output.splitlines())
        if command.help:
            assert "".join(command.help.split()) in compact
        for param in command.get_params(ctx):
            record = param.get_help_record(ctx)
            if record:
                assert "".join(record[1].split()) in compact
        if hasattr(command, "list_commands"):
            assert output.index("Usage:") < output.index("Commands:") < output.lower().index("options:")
            for name in command.list_commands(ctx):
                child = command.get_command(ctx, name)
                if child and not child.hidden:
                    assert name in compact
                    if child.help:
                        assert "".join(child.help.split()) in compact
                    check(child, child.context_class(child, info_name=name, parent=ctx))
    check(root, root.context_class(root, info_name="dotbrain"))


def test_help_colors_headings_and_names_only_in_terminal(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(presentation, "console", lambda: Console(width=100, force_terminal=True, color_system="standard"))
    root = get_command(app)
    ctx = root.context_class(root, info_name="dotbrain", **root.context_settings)
    output = root.get_help(ctx)
    assert "\x1b[1;32mCommands:" in output and "\x1b[1;36mbootstrap" in output
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
    assert plain.startswith(root.help + "\n\nUsage:")
    assert "<COMMAND>" in plain and "-h, --help" in plain
    ctx.color = False
    assert "\x1b" not in root.get_help(ctx)
