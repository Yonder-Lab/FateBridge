import json
from pathlib import Path
from fatebridge.services.tool_catalog import CATALOG
from fatebridge.core.schema_cache import contract_fingerprint,model_schema
from fatebridge.services.replay_metadata import digest
facts=[]
for spec in CATALOG:
    request=spec.request_model.model_json_schema()
    output=spec.output_model.model_json_schema() if spec.output_model else None
    assert model_schema(spec.request_model)==request
    if spec.output_model: assert model_schema(spec.output_model)==output
    expected=digest({'input':request,'output':output})
    actual=contract_fingerprint(spec.request_model,spec.output_model)
    assert actual==expected,spec.key
    facts.append({'tool':spec.key,'cached_equals_uncached':True,'contract_sha256':actual})
report={'checked':len(facts),'all_match_uncached_contract':True,'facts':facts}
Path('/audit/linux-catalog-contracts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checked':len(facts),'all_match_uncached_contract':True}))
