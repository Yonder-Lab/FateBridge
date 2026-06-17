"""CLI surface tests — the CLI is built from the same central tool catalog."""

import json

from fatebridge.cli import build_parser, run
from fatebridge.services.tool_catalog import CATALOG


def test_cli_exposes_catalog_commands(capsys):
    """Every CLI-safe catalog tool should be a subcommand."""
    parser = build_parser()
    subparsers = [a for a in parser._actions if a.dest == "command"]
    assert subparsers, "no subparsers found"
    choices = set(subparsers[0].choices)
    assert "list" in choices
    # A representative sample across families is present.
    for cmd in ("bazi_wealth", "bazi_personality", "qimen", "knowledge_read", "solarreturn"):
        assert cmd in choices, cmd


def test_cli_runs_bazi_dimension(capsys):
    code = run([
        "bazi_romance",
        "--birth-year", "1990", "--birth-month", "6", "--birth-day", "15",
        "--birth-hour", "10", "--gender", "male",
        "--dayun-pillar", "壬戌",
    ])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["analysis_type"] == "八字正缘桃花分析"
    assert "romance_analysis" in payload
    assert isinstance(payload.get("run_metadata"), dict)


def test_cli_runs_knowledge_read(capsys):
    code = run(["knowledge_read", "--domain", "bazi", "--category", "wealth", "--key", "财库"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["title"].startswith("财库")


def test_cli_validation_error_returns_nonzero(capsys):
    # Invalid month (passes argparse int parse, fails pydantic le=12) -> exit 1.
    code = run([
        "bazi_wealth",
        "--birth-year", "1990", "--birth-month", "13", "--birth-day", "15",
        "--birth-hour", "10",
    ])
    err = capsys.readouterr().err
    assert code == 1
    assert "error" in err
