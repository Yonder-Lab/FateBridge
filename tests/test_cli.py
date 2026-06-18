"""CLI surface tests — the CLI is built from the same central tool catalog."""

import json

from fatebridge.cli import build_parser, run
from fatebridge.core.tool_spec import ToolSpec, result_is_error
from fatebridge.services.tool_catalog import CATALOG


def test_nested_model_tool_gives_hint_not_crash(capsys):
    # astro_relative uses a nested request model -> CLI-unsupported, but should
    # print a helpful hint (pointing at the flat variant) and exit 2.
    code = run(["astro_relative"])
    err = capsys.readouterr().err
    assert code == 2
    assert "astro_relative_chart" in err


def test_result_is_error_honors_error_is_fatal():
    base = next(s for s in CATALOG if s.rest_path == "/api/cn/bazi/wealth")
    # Default: "error" key marks an error.
    assert result_is_error(base, {"error": "x"}) is True
    assert result_is_error(base, {"ok": 1}) is False
    # error_is_fatal override is honored uniformly (the contract REST already used).
    lenient = ToolSpec(
        key="t",
        bind=base.bind,
        request_model=base.request_model,
        summary="t",
        operation_label_zh="t",
        family="t",
        error_is_fatal=lambda r: False,
    )
    assert result_is_error(lenient, {"error": "non-fatal"}) is False


def test_cli_exposes_catalog_commands(capsys):
    """Every CLI-safe catalog tool should be a subcommand."""
    parser = build_parser()
    subparsers = [a for a in parser._actions if a.dest == "command"]
    assert subparsers, "no subparsers found"
    choices = set(subparsers[0].choices)
    assert "list" in choices
    # A representative sample across families is present.
    for cmd in (
        "bazi_wealth",
        "bazi_personality",
        "qimen",
        "knowledge_read",
        "solarreturn",
    ):
        assert cmd in choices, cmd


def test_cli_runs_bazi_dimension(capsys):
    code = run(
        [
            "bazi_romance",
            "--birth-year",
            "1990",
            "--birth-month",
            "6",
            "--birth-day",
            "15",
            "--birth-hour",
            "10",
            "--gender",
            "male",
            "--dayun-pillar",
            "壬戌",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["analysis_type"] == "八字正缘桃花分析"
    assert "romance_analysis" in payload
    assert isinstance(payload.get("run_metadata"), dict)


def test_cli_runs_knowledge_read(capsys):
    code = run(
        ["knowledge_read", "--domain", "bazi", "--category", "wealth", "--key", "财库"]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["title"].startswith("财库")


def test_describe_is_a_subcommand():
    parser = build_parser()
    subparsers = [a for a in parser._actions if a.dest == "command"]
    assert "describe" in set(subparsers[0].choices)


def test_describe_flat_tool_emits_schema_and_example(capsys):
    code = run(["describe", "bazi_wealth"])
    out = capsys.readouterr().out
    info = json.loads(out)
    assert code == 0
    assert info["tool"] == "bazi_wealth"
    assert info["surfaces"]["cli"] is True
    assert info["surfaces"]["rest_path"] == "/api/cn/bazi/wealth"
    # birth_year is a required int parameter with a flag and description.
    by = next(p for p in info["parameters"] if p["name"] == "birth_year")
    assert by["required"] is True
    assert by["type"] == "int"
    assert by["flag"] == "--birth-year"
    assert by["description"]
    # A runnable example is offered for CLI-safe tools.
    assert info["cli_example"].startswith("fatebridge bazi_wealth")
    assert "--birth-year" in info["cli_example"]


def test_describe_nested_tool_still_describes_with_hint(capsys):
    # Nested-model tools can't run on the CLI, but describe must still work and
    # point the agent at the right surface.
    code = run(["describe", "astro_relative"])
    out = capsys.readouterr().out
    info = json.loads(out)
    assert code == 0
    assert info["surfaces"]["cli"] is False
    assert "cli_hint" in info
    assert "cli_example" not in info


def test_describe_unknown_tool_returns_nonzero(capsys):
    code = run(["describe", "no_such_tool"])
    err = capsys.readouterr().err
    assert code == 2
    assert "no_such_tool" in err


def test_describe_without_tool_returns_usage(capsys):
    code = run(["describe"])
    err = capsys.readouterr().err
    assert code == 2
    assert "describe" in err


def test_cli_validation_error_returns_nonzero(capsys):
    # Invalid month (passes argparse int parse, fails pydantic le=12) -> exit 1.
    code = run(
        [
            "bazi_wealth",
            "--birth-year",
            "1990",
            "--birth-month",
            "13",
            "--birth-day",
            "15",
            "--birth-hour",
            "10",
        ]
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "error" in err
