"""Validate the saved wheel's domain contracts using the current dependencies."""

import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
wheel = Path(
    "/tmp/fatebridge-p2-domain-contracts-wheel/fatebridge-0.2.0-py3-none-any.whl"
)
with tempfile.TemporaryDirectory(prefix="fatebridge-domain-wheel-") as tmp:
    with zipfile.ZipFile(wheel) as package:
        package.extractall(tmp)
    sys.path.insert(0, tmp)
    import fatebridge.core.output_bazi as bazi
    import fatebridge.core.output_reference as reference
    from fatebridge.services.tool_catalog import CATALOG

    assert Path(bazi.__file__).is_relative_to(tmp)
    assert Path(reference.__file__).is_relative_to(tmp)
    keys = [
        "bazi_" + field.removesuffix("_analysis") for field in bazi.BAZI_FIELDS
    ] + list(reference.REFERENCE_TOOL_FIELDS)
    specs = {spec.key: spec for spec in CATALOG}
    for key in keys:
        spec = specs[key]
        filename = spec.rest_path.strip("/").replace("/", "_") + ".json"
        payload = json.loads((ROOT / "tests/golden/snapshots" / filename).read_text())
        payload.pop("run_metadata", None)
        spec.output_model.model_validate(payload)
    result = {
        "wheel": wheel.name,
        "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "domain_contracts_validated": keys,
        "packaged_models_imported": True,
        "dependencies": "Current project virtual environment; extracted wheel, not a fresh dependency installation",
    }
    (OUT / "wheel-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
