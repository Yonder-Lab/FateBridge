"""Professional facts, partial responses and faults obey one public contract."""

import asyncio
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaError
from pydantic import ValidationError

import fatebridge.api as api
import fatebridge.core.tool_spec as execution
import fatebridge.mcp_server as mcp
from fatebridge.cli import run as cli_run
from fatebridge.services.tool_catalog import CATALOG
from tests.fixtures.surface_payloads import MCP_CASES, REST_POST_CASES

SPECS = {spec.key: spec for spec in CATALOG}
SNAPSHOTS = Path(__file__).parent / "golden" / "snapshots"
AS_OF = "2026-10-12T02:00:00Z"


@pytest.fixture
def rest(monkeypatch):
    api._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api,
        "API_KEY_AUTHENTICATOR",
        api.ApiKeyAuthenticator(header_name="X-API-Key", api_keys={}),
    )
    return TestClient(api.app)


def inputs(spec):
    factory = (
        REST_POST_CASES[spec.rest_path]
        if spec.rest_path
        else MCP_CASES[spec.tool_name][1]
    )
    return spec.request_model.model_validate(factory()).model_dump(exclude_unset=True)


def rest_spec(spec):
    return SPECS["astro_relative"] if spec.key == "astro_relative_chart" else spec


def call_cli(spec, payload, tmp_path, capsys, flags=()):
    subject = tmp_path / "subject.json"
    subject.write_text(json.dumps(payload, ensure_ascii=False))
    prefix = ["--no-metadata"] if "--no-metadata" in flags else []
    flags = [flag for flag in flags if flag != "--no-metadata"]
    code = cli_run(
        [
            *prefix,
            spec.tool_name,
            "--subject-file",
            str(subject),
            "--as-of",
            AS_OF,
            *flags,
        ]
    )
    return code, json.loads(capsys.readouterr().out)


async def native(spec, payload, **flags):
    async with Client(mcp.app) as client:
        return await client.call_tool(
            spec.tool_name, {**payload, "as_of": AS_OF, **flags}, raise_on_error=False
        )


def business(payload):
    return {k: v for k, v in payload.items() if k != "run_metadata"}


@pytest.mark.parametrize("key", list(SPECS))
def test_existing_golden_business_json_remains_valid_without_rewriting(key):
    spec = SPECS[key]
    filename = (
        spec.rest_path.strip("/").replace("/", "_")
        if spec.rest_path
        else "mcp_" + spec.key
    )
    path = SNAPSHOTS / (filename + ".json")
    if not path.exists():
        # The REST relationship spec has a separate flattened MCP alias.
        assert key == "astro_relative_chart"
        path = SNAPSHOTS / "api_astro_relative.json"
    payload = business(json.loads(path.read_text()))
    before = copy.deepcopy(payload)
    spec.output_model.model_validate(payload)
    Draft202012Validator(spec.output_model.model_json_schema()).validate(payload)
    assert payload == before


BAD_FACTS = [
    ("pd", {"pd": {"timeline": [{"event_age_years": "private-wrong-value"}]}}),
    ("pdchart", {"pdchart": {"bounds_overlay": {"enabled": "yes"}}}),
    ("zr", {"zr": {"fortune": {"level_2_timeline": [{"loosing_of_bond": 1}]}}}),
    ("decennials", {"decennials": {"timeline": [{"sublevel": [{"level": "3"}]}]}}),
    ("astro_harmonic", {"harmonic_chart": {"resonant_conjunctions": ["bad-item"]}}),
    (
        "astro_distributions",
        {
            "distributions": {
                "periods": [{"participants": [{"contact_age_years": "3"}]}]
            }
        },
    ),
    (
        "astro_balbillus",
        {"balbillus": {"periods": [{"sub_periods": [{"duration_years": "3"}]}]}},
    ),
    ("astro_extrareturns", {"extrareturns": {"returns": [{"next_return": "date"}]}}),
    ("astro_horary", {"horary": {"radicality": {"strictures": [{"code": False}]}}}),
    ("astro_guolao", {"guolao": {"god_sign_index": {"天贵": "1"}}}),
    ("astro_chart", {"classical": {"planets": {"Sun": {"essential": {"score": "5"}}}}}),
    ("astro_chart", {"classical_patterns": {"collection_of_light": [{"from": "Sun"}]}}),
    (
        "astro_relative_chart",
        {"in_to_out_midpoint": {"Sun": [{"midpoint": {"longitude": "30"}}]}},
    ),
    ("astro_relative_chart", {"in_to_out_antiscia": [{"delta": "1"}]}),
    (
        "ziwei_birth",
        {"ziwei_birth": {"palaces": [{"stars_detail": [{"brightness": 1}]}]}},
    ),
    ("liureng_gods", {"liureng": {"four_lessons": [{"index": "1"}]}}),
    ("qimen", {"qimen": {"palaces": [{"door_hexagram": {"binary_code": 101}}]}}),
    ("taiyi", {"taiyi": {"core_board": {"guest_count": "12"}}}),
    ("jinkou", {"jinkou": {"rows": [{"power": False}]}}),
    ("sixyao", {"lines": [{"change": "false"}]}),
    ("heluo", {"dayun": {"all": [{"ageStart": "3"}]}}),
    ("suzhan", {"chart": {"objects": [{"house": 1}]}}),
    ("sanshiunited", {"subresults": {"qimen": {"pan": {"ju_number": "9"}}}}),
]


@pytest.mark.parametrize("key,payload", BAD_FACTS)
def test_nested_fact_faults_are_internal_failures_on_all_surfaces(
    key, payload, rest, monkeypatch, tmp_path, capsys
):
    spec = SPECS[key]
    with pytest.raises(ValidationError):
        spec.output_model.model_validate(payload)
    with pytest.raises(SchemaError):
        Draft202012Validator(spec.output_model.model_json_schema()).validate(payload)

    original = execution.execute_spec

    def broken_output(actual, request):
        if actual.key in {key, rest_spec(spec).key}:
            actual = replace(
                actual, bind=lambda _: (lambda: copy.deepcopy(payload), (), {})
            )
        return original(actual, request)

    monkeypatch.setattr(execution, "execute_spec", broken_output)
    request = inputs(spec)
    # Selecting an unrelated field cannot hide corrupt professional facts:
    # validation is performed before projection in the shared execution unit.
    http = rest.post(
        rest_spec(spec).rest_path,
        json=inputs(rest_spec(spec)),
        params={"as_of": AS_OF, "fields": "analysis_type", "trace_id": "nested-fault"},
    )
    protocol = asyncio.run(
        native(spec, request, fields=["analysis_type"], trace_id="nested-fault")
    )
    code, output = call_cli(
        spec,
        request,
        tmp_path,
        capsys,
        ["--fields", "analysis_type", "--trace-id", "nested-fault"],
    )
    assert http.status_code == 500 and protocol.is_error and code == 1
    assert {
        k: v for k, v in protocol.structured_content.items() if k != "operation"
    } == output
    assert http.json() == {
        k: v for k, v in output.items() if k not in {"operation", "status_code"}
    }
    assert output["status_code"] == 500
    assert output["error_code"] == "internal_error"
    assert output["trace_id"] == "nested-fault"
    assert "private-wrong-value" not in json.dumps(output)
    assert json.loads(protocol.content[0].text) == protocol.structured_content


PROJECTIONS = [
    ("pd", "pd.current_coordinate_points.Ascendant.coordinate_degrees"),
    ("pdchart", "pdchart.bounds_overlay.enabled"),
    ("decennials", "decennials.current_level_1.sublevel"),
    ("zr", "zr.fortune.current_level_2.loosing_of_bond"),
    ("astro_distributions", "distributions.periods"),
    ("astro_extrareturns", "extrareturns.returns"),
    ("astro_horary", "horary.moon.next_aspect"),
    ("astro_guolao", "guolao.god_sign_index"),
    ("astro_relative_chart", "in_to_out_midpoint.Sun"),
    ("ziwei_birth", "ziwei_birth.palaces"),
    ("liureng_gods", "liureng.three_transmissions.initial.branch"),
    ("qimen", "qimen.zhifu.star"),
    ("taiyi", "taiyi.core_board.guest_count"),
    ("sixyao", "lines"),
    ("suzhan", "chart.objects"),
    ("sanshiunited", "subresults.qimen.pan.ju_number"),
]


@pytest.mark.parametrize("key,field", PROJECTIONS)
def test_professional_partial_output_matches_transports_and_no_metadata(
    key, field, rest, tmp_path, capsys
):
    spec = SPECS[key]
    request = inputs(spec)
    http = rest.post(
        rest_spec(spec).rest_path,
        json=inputs(rest_spec(spec)),
        params={
            "as_of": AS_OF,
            "fields": field,
            "strict_fields": True,
            "include_snapshot_text": False,
        },
    )
    protocol = asyncio.run(
        native(
            spec,
            request,
            fields=[field],
            strict_fields=True,
            include_snapshot_text=False,
        )
    )
    code, output = call_cli(
        spec,
        request,
        tmp_path,
        capsys,
        [
            "--fields",
            field,
            "--strict-fields",
            "--no-include-snapshot-text",
            "--no-metadata",
        ],
    )
    assert http.status_code == 200 and not protocol.is_error and code == 0
    assert business(http.json()) == business(protocol.structured_content) == output
    assert "run_metadata" not in output and "snapshot_text" not in output
    assert "projection_warnings" not in output
    schema = spec.output_model.model_json_schema()
    for result in [http.json(), protocol.structured_content, output]:
        spec.output_model.model_validate(result)
        Draft202012Validator(schema).validate(result)


@pytest.mark.parametrize(
    "key,patch",
    [
        ("pd", {"pd_method": "legacy_equatorial", "pd_type": 1}),
        (
            "pdchart",
            {"pd_method": "fatebridge_mundane_semiarc", "show_pd_bounds": False},
        ),
        ("astro_harmonic", {"harmonic": 1, "orb": 15.0}),
        ("astro_triplicity_rulers", {"division": "halves"}),
        (
            "astro_planetary_ages",
            {"analysis_year": 2026, "analysis_month": 10, "analysis_day": 12},
        ),
        ("sixyao", {"seed": 42, "method": "coin", "gua_code": None, "lines": []}),
        ("gua_lookup", {"query": "坤为地"}),
    ],
)
def test_non_default_professional_branches_obey_the_same_contract(key, patch):
    spec = SPECS[key]
    request = spec.request_model.model_validate({**inputs(spec), **patch})
    result = execution.execute_tool(spec, request)
    assert "error" not in result, result
    spec.output_model.model_validate(result)
    Draft202012Validator(spec.output_model.model_json_schema()).validate(result)


def test_extensions_nulls_empty_lists_and_numeric_wire_values_are_preserved():
    spec = SPECS["decennials"]
    payload = {
        "decennials": {
            "current_level_2": None,
            "timeline": [
                {
                    "level": 1,
                    "sublevel": [
                        {"level": 2, "sublevel": [], "vendor_note": {"x": 0.25}}
                    ],
                },
            ],
            "vendor_system": {"revision": 3},
        },
        "future_root": {"enabled": True},
    }
    before = copy.deepcopy(payload)
    fake = replace(spec, bind=lambda _: (lambda: payload, (), {}))
    result = execution.execute_spec(
        fake, spec.request_model.model_validate(inputs(spec))
    )
    assert result is payload and result == before
    assert "current_level_1" not in result["decennials"]
    Draft202012Validator(spec.output_model.model_json_schema()).validate(result)


def schema_leaf(root, node, path):
    """Resolve optional models, map values and list items without unrolling recursion."""

    def unwrap(value):
        while True:
            if "$ref" in value:
                ref = value["$ref"]
                assert ref.startswith("#/")
                value = root
                for part in ref[2:].split("/"):
                    value = value[part.replace("~1", "/").replace("~0", "~")]
            elif "anyOf" in value:
                candidates = [v for v in value["anyOf"] if v.get("type") != "null"]
                assert len(candidates) == 1
                value = candidates[0]
            else:
                return value

    for part in path.split("."):
        node = unwrap(node)
        node = (
            node["items"]
            if part == "[]"
            else (
                node["additionalProperties"]
                if part == "{}"
                else node["properties"][part]
            )
        )
    return unwrap(node)


SCHEMA_LEAVES = [
    (
        "pd",
        "pd.timeline.[].coordinate_context.promissor_current.coordinate_degrees",
        "number",
    ),
    ("pdchart", "pdchart.bounds_overlay.points.{}.bound_lord", "string"),
    ("decennials", "decennials.timeline.[].sublevel.[].sublevel.[].level", "integer"),
    ("zr", "zr.fortune.level_2_timeline.[].loosing_of_bond", "boolean"),
    (
        "astro_distributions",
        "distributions.periods.[].participants.[].contact_age_years",
        "number",
    ),
    ("astro_balbillus", "balbillus.periods.[].sub_periods.[].duration_years", "number"),
    (
        "astro_extrareturns",
        "extrareturns.returns.[].next_return.datetime_utc",
        "string",
    ),
    ("astro_chart", "classical.planets.{}.essential.peregrine", "boolean"),
    ("astro_guolao", "guolao.god_sign_index.{}", "integer"),
    ("astro_relative_chart", "in_to_out_midpoint.{}.[].midpoint.longitude", "number"),
    ("ziwei_birth", "ziwei_birth.palaces.[].stars_detail.[].brightness", "string"),
    ("liureng_gods", "liureng.four_lessons.[].relations.{}", "string"),
    ("qimen", "qimen.palaces.[].door_hexagram.binary_code", "string"),
    ("taiyi", "taiyi.core_board.guest_count", "integer"),
    ("jinkou", "jinkou.rows.[].power", "string"),
    ("sixyao", "lines.[].change", "boolean"),
    ("heluo", "dayun.all.[].ageStart", "integer"),
    ("suzhan", "chart.objects.[].house", "string"),
    ("sanshiunited", "subresults.qimen.pan.ju_number", "integer"),
]


def test_nested_schema_facts_are_discoverable_identically_on_all_transports(
    rest, capsys
):
    openapi = rest.get("/openapi.json").json()
    manifest = rest.get("/api/tools").json()
    advertised = {tool["tool"]: tool["output_schema"] for tool in manifest["tools"]}

    async def schemas():
        async with Client(mcp.app) as client:
            return {tool.name: tool.outputSchema for tool in await client.list_tools()}

    native_schemas = asyncio.run(schemas())
    for key, path, expected_type in SCHEMA_LEAVES:
        spec = SPECS[key]
        central = spec.output_model.model_json_schema()
        assert cli_run(["describe", spec.tool_name]) == 0
        cli_schema = json.loads(capsys.readouterr().out)["output_schema"]
        assert central == cli_schema == advertised[spec.tool_name]
        for root in [central, cli_schema, native_schemas[spec.tool_name]]:
            Draft202012Validator.check_schema(root)
            assert schema_leaf(root, root, path)["type"] == expected_type
        endpoint = rest_spec(spec).rest_path
        http_schema = openapi["paths"][endpoint]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert schema_leaf(openapi, http_schema, path)["type"] == expected_type

    # Published native schemas also reject corrupt facts, including recursive
    # levels, keyword aliases and normally empty lists (not just model schemas).
    for key, payload in BAD_FACTS:
        with pytest.raises(SchemaError):
            Draft202012Validator(native_schemas[SPECS[key].tool_name]).validate(payload)


def test_recursive_schema_inliner_fallback_preserves_a_valid_wire_contract(monkeypatch):
    from fastmcp.utilities import json_schema

    from fatebridge.mcp_transport import _serializable_schema

    schema = SPECS["decennials"].output_model.model_json_schema()
    cycle = {"type": "object"}
    cycle["properties"] = {"child": cycle}
    monkeypatch.setattr(json_schema, "dereference_refs", lambda value: cycle)
    published = _serializable_schema(schema)
    assert published is schema
    json.dumps(published)
    Draft202012Validator(published).validate(
        {"decennials": {"timeline": [{"level": 1, "sublevel": [{"level": 2}]}]}}
    )


def test_numeric_relationship_mode_keeps_legacy_wire_type_on_all_surfaces(
    rest, tmp_path, capsys
):
    spec = SPECS["astro_relative_chart"]
    request = {**inputs(spec), "relative_mode": 0, "relationship_mode": 0}
    nested = {**inputs(rest_spec(spec)), "relative_mode": 0, "relationship_mode": 0}
    field = "relationship_profile.relative_mode_input"
    http = rest.post(
        rest_spec(spec).rest_path, json=nested, params={"as_of": AS_OF, "fields": field}
    )
    protocol = asyncio.run(native(spec, request, fields=[field]))
    code, output = call_cli(spec, request, tmp_path, capsys, ["--fields", field])
    assert http.status_code == 200 and not protocol.is_error and code == 0
    assert (
        business(http.json())
        == business(protocol.structured_content)
        == business(output)
    )
    assert type(output["relationship_profile"]["relative_mode_input"]) is int
