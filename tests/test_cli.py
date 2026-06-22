"""CLI surface tests — the CLI is built from the same central tool catalog."""

import json

from fatebridge.cli import build_parser, run
from fatebridge.core.tool_spec import ToolSpec, result_is_error
from fatebridge.services.tool_catalog import CATALOG


def test_nested_model_tool_gives_hint_not_crash(capsys):
    # astro_relative uses a nested request model -> CLI-unsupported, but should
    # print a helpful hint (pointing at the flat variant) and exit 2. The hint
    # is JSON on stdout so a json.loads(stdout) consumer parses it cleanly.
    code = run(["astro_relative"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 2
    assert payload["error_code"] == "cli_unsupported"
    assert "astro_relative_chart" in payload["error"]


def test_missing_required_flag_emits_json_on_stdout(capsys):
    # A missing required flag is an argparse-level error. It must still land on
    # stdout as valid JSON (not an empty stdout + usage text on stderr), so an
    # agent that parses stdout gets actionable feedback instead of a PARSE-ERR.
    code = run(["bazi_wealth", "--birth-year", "1990"])  # missing month/day/hour
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 2
    assert payload["error_code"] == "usage_error"
    assert "birth" in payload["error"]


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


def test_cli_fields_projection_trims_payload(capsys):
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
            "--fields",
            "analysis_type",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    # Only the requested key survives; run_metadata is always preserved.
    assert set(payload) <= {"analysis_type", "run_metadata"}
    assert payload["analysis_type"] == "八字正缘桃花分析"
    assert "romance_analysis" not in payload


def test_cli_fields_dotted_subpath_prunes_block(capsys):
    code = run(
        [
            "bazi_birth",
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
            "--fields",
            "bazi_birth.day_master",
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    # The heavy bazi_birth block is pruned to just the requested sub-key.
    assert set(payload) <= {"bazi_birth", "run_metadata"}
    assert set(payload["bazi_birth"]) == {"day_master"}
    assert "element" in payload["bazi_birth"]["day_master"]
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
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["error_code"] == "unknown_tool"
    assert "no_such_tool" in payload["error"]


def test_describe_without_tool_returns_usage(capsys):
    code = run(["describe"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["error_code"] == "usage_error"
    assert "describe" in payload["error"]


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
    # The structured error shares stdout with success output (see
    # _JsonErrorParser / _emit_error): a json.loads(stdout) consumer never sees
    # an empty stdout and so never raises "Expecting value: line 1 column 1".
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 1
    assert payload["error_code"] == "validation_error"


def test_cli_invalid_input_renders_clean_error_shape(capsys):
    # M2: bad input renders the same generic, structured error shape REST/MCP
    # use (status_code 400, validation_error) instead of a raw exception string.
    code = run(
        [
            "bazi_wealth",
            "--birth-year",
            "1990",
            "--birth-month",
            "2",
            "--birth-day",
            "31",  # Feb 31: passes argparse + pydantic le=31, fails monthrange
            "--birth-hour",
            "10",
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    payload = json.loads(out)
    assert payload["status_code"] == 400
    assert payload["error_code"] == "validation_error"


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_subject_file_supplies_required_and_optional_fields(tmp_path, capsys):
    # A JSON profile alone (no birth flags on the command line) must drive a
    # full run: required fields satisfy argparse via relaxation, and optional
    # fields like gender reach the model instead of being shadowed by defaults.
    subject = _write(
        tmp_path / "lived.json",
        json.dumps(
            {
                "name": "Lived",
                "gender": "女",
                "birth_year": 2001,
                "birth_month": 10,
                "birth_day": 12,
                "birth_hour": 11,
                "birth_minute": 40,
                "birth_longitude": 108.71,
                "birth_timezone": "Asia/Shanghai",
                "use_true_solar_time": True,
            }
        ),
    )
    code = run(["bazi_birth", "--subject-file", subject])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    chart = payload["bazi_birth"]
    assert chart["person_info"]["name"] == "Lived"
    assert chart["person_info"]["gender"] == "女"  # optional field not shadowed
    assert chart["time_algorithm"] == "真太阳时"
    hour = chart["four_pillars"]["hour"]
    assert hour["stem"] + hour["branch"] == "戊午"


def test_cli_flag_overrides_subject_file(tmp_path, capsys):
    subject = _write(
        tmp_path / "s.json",
        json.dumps(
            {
                "gender": "女",
                "birth_year": 2001,
                "birth_month": 10,
                "birth_day": 12,
                "birth_hour": 11,
            }
        ),
    )
    # Explicit --birth-year must win over the file's 2001.
    code = run(["bazi_birth", "--subject-file", subject, "--birth-year", "1990"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    year = payload["bazi_birth"]["four_pillars"]["year"]
    assert year["stem"] + year["branch"] == "庚午"  # 1990, not 2001 (辛巳)


def test_subject_file_reused_across_tools(tmp_path, capsys):
    subject = _write(
        tmp_path / "s.json",
        json.dumps(
            {
                "gender": "女",
                "birth_year": 2001,
                "birth_month": 10,
                "birth_day": 12,
                "birth_hour": 11,
                "birth_minute": 40,
                "birth_longitude": 108.71,
                "birth_timezone": "Asia/Shanghai",
                "use_true_solar_time": True,
            }
        ),
    )
    code = run(["ziwei_birth", "--subject-file", subject])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["ziwei_birth"]["ming_gong"]["ganzhi"] == "壬辰"


def test_subject_file_missing_path_is_usage_error(capsys):
    code = run(["bazi_birth", "--subject-file", "/no/such/file.json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["error_code"] == "usage_error"


def test_subject_file_yaml_is_supported(tmp_path, capsys):
    import importlib.util

    if importlib.util.find_spec("yaml") is None:  # optional dependency
        import pytest

        pytest.skip("pyyaml not installed")
    subject = _write(
        tmp_path / "s.yaml",
        "gender: 女\nbirth_year: 2001\nbirth_month: 10\nbirth_day: 12\n"
        "birth_hour: 11\n",
    )
    code = run(["bazi_birth", "--subject-file", subject])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["bazi_birth"]["person_info"]["gender"] == "女"
