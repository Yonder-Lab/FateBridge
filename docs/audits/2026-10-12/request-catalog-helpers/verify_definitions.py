"""Check moved definitions and ordered declarations against original AST hashes."""

import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[3]


def digest(node):
    return hashlib.sha256(ast.dump(node).encode()).hexdigest()


def target(node):
    value = node.targets[0] if isinstance(node, ast.Assign) else node.target
    return value.id if isinstance(value, ast.Name) else None


def definitions():
    counts = Counter()
    for item in json.loads((AUDIT / "definition-baselines.json").read_text())[
        "definitions"
    ]:
        tree = ast.parse((ROOT / item["path"]).read_text())
        found = [
            node
            for node in tree.body
            if (
                isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name == item["original_name"]
            )
            or (
                isinstance(node, (ast.Assign, ast.AnnAssign))
                and target(node) == item["original_name"]
            )
        ]
        assert len(found) == 1, item
        assert digest(found[0]) == item["ast_sha256"], item
        counts[item["original_source"]] += 1
    return dict(counts)


def catalog():
    baseline = json.loads((AUDIT / "catalog-definition-baselines.json").read_text())
    for item in baseline["declarations"]:
        tree = ast.parse((ROOT / item["path"]).read_text())
        specs = next(
            node
            for node in tree.body
            if isinstance(node, ast.AnnAssign) and target(node) == "SPECS"
        )
        assert digest(specs.value.elts[item["local_index"]]) == item["ast_sha256"], item
    tree = ast.parse((ROOT / "src/fatebridge/services/catalog/fengshui.py").read_text())
    loop = next(node for node in tree.body if isinstance(node, ast.For))

    class OriginalListName(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id == "SPECS":
                node.id = "CATALOG"
            return node

    assert digest(OriginalListName().visit(loop)) == baseline["fengshui_loop_sha256"]
    tree = ast.parse((ROOT / "src/fatebridge/services/tool_catalog.py").read_text())
    passes = [
        digest(node)
        for node in tree.body
        if isinstance(node, ast.Assign) and target(node) == "CATALOG"
    ]
    assert passes == baseline["enrichment_passes"]
    return {
        "unchanged_declarations": len(baseline["declarations"]),
        "unchanged_fengshui_loop": True,
        "unchanged_enrichment_passes": len(passes),
    }


if __name__ == "__main__":
    result = {"definitions": definitions(), "catalog": catalog()}
    (AUDIT / "definition-comparison.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))
