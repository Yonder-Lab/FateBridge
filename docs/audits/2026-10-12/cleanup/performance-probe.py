"""Read-only local cleanup audit probe; does not edit FateBridge or publish data."""

import asyncio
import contextlib
import io
import json
import logging
import statistics
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

from fatebridge.application.discovery import discover_specs
from fatebridge.application.execution import execute_tool
from fatebridge.application.description import spec_is_cli_safe
from fatebridge.services import replay_metadata
from fatebridge.services.tool_catalog import CATALOG, mcp_specs, rest_specs
from tests.fixtures.surface_payloads import MCP_CASES, REST_POST_CASES


def run():
    result = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'root': str(ROOT),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'scope': 'current working tree; macOS local probes only; fixture inputs',
        'versions': {name: version(name) for name in ['fatebridge', 'fastmcp', 'mcp', 'pydantic', 'kerykeion']},
        'counts': {'catalog': len(CATALOG), 'rest': len(rest_specs()), 'mcp': len(mcp_specs()), 'cli': sum(spec_is_cli_safe(s) for s in CATALOG)},
        'discovery': {},
        'execution': {},
    }
    for name, options in [('summary', {'detail': 'summary'}), ('full', {'detail': 'full'}), ('one_full', {'detail': 'full', 'tool': 'bazi_birth'})]:
        samples = []
        for _ in range(3):
            start = time.perf_counter()
            body = discover_specs(CATALOG, **options)
            samples.append(round((time.perf_counter() - start) * 1000, 3))
        result['discovery'][name] = {'bytes_utf8_compact': len(json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()), 'samples_ms': samples}

    original_receipt = replay_metadata.execution_receipt
    receipt_samples = []

    def measured_receipt(*args, **kwargs):
        start = time.perf_counter()
        body = original_receipt(*args, **kwargs)
        receipt_samples.append((time.perf_counter() - start) * 1000)
        return body

    replay_metadata.execution_receipt = measured_receipt
    try:
        for key in ['gua_lookup', 'bazi_birth', 'fengshui_directions']:
            spec = next(s for s in CATALOG if s.key == key)
            request = spec.request_model.model_validate(MCP_CASES[spec.tool_name][1]())
            execute_tool(spec, request)
            receipt_samples.clear()
            total_samples = []
            service_samples = []
            for _ in range(5):
                start = time.perf_counter()
                body = execute_tool(spec, request)
                total_samples.append((time.perf_counter() - start) * 1000)
                service_samples.append(body['run_metadata']['duration_ms'])
            result['execution'][key] = {name: round(statistics.median(values), 3) for name, values in [('median_total_ms', total_samples), ('median_recorded_service_ms', service_samples), ('median_receipt_ms', receipt_samples)]}
    finally:
        replay_metadata.execution_receipt = original_receipt

    from fastapi.testclient import TestClient
    from fastmcp import Client
    import fatebridge.api as api
    import fatebridge.mcp_server as mcp
    import fatebridge.application.execution as tool_spec

    logging.getLogger().setLevel(logging.ERROR)
    original_validate = tool_spec.validate_output
    calls = []

    def measured_validate(spec, body):
        start = time.perf_counter()
        original_validate(spec, body)
        calls.append({'key': spec.key, 'has_metadata': 'run_metadata' in body, 'ms': round((time.perf_counter() - start) * 1000, 3)})

    tool_spec.validate_output = measured_validate
    try:
        # This is a process-local TestClient; no real server is started.
        api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(header_name='X-API-Key', api_keys={})
        with TestClient(api.app) as client:
            response = client.post('/api/cn/bazi/birth', json=REST_POST_CASES['/api/cn/bazi/birth']())
            result['rest_validation'] = {'status': response.status_code, 'calls': list(calls)}
        calls.clear()

        async def native_call():
            async with Client(mcp.app) as client:
                response = await client.call_tool('bazi_birth', MCP_CASES['bazi_birth'][1]())
                result['mcp_validation'] = {'is_error': response.is_error, 'calls': list(calls), 'text_equals_structured': json.loads(response.content[0].text) == response.structured_content}

        asyncio.run(native_call())
    finally:
        tool_spec.validate_output = original_validate

    child_code = '''import asyncio, warnings, gc
with warnings.catch_warnings(record=True) as captured:
 warnings.simplefilter('always', RuntimeWarning)
 async def main():
  import fatebridge.mcp_server
 asyncio.run(main()); gc.collect()
 print([str(w.message) for w in captured if 'never awaited' in str(w.message)])
'''
    child = subprocess.run([sys.executable, '-c', child_code], cwd=ROOT, text=True, capture_output=True, check=True)
    result['async_import_warning'] = child.stdout.strip()
    return result


if __name__ == '__main__':
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()):
        warnings.simplefilter('ignore')
        evidence = run()
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(output)
