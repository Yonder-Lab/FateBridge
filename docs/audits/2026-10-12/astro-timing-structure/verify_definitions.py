"""Verify extracted definitions against saved pre-refactor AST fingerprints."""

import ast
import hashlib
import json
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[3]


def verify():
    baseline = json.loads((AUDIT / "definition-baselines.json").read_text())
    inverse = {new: old for old, new in baseline["renames"].items()}

    class Normalize(ast.NodeTransformer):
        def visit_Attribute(self, node):
            node = self.generic_visit(node)
            if isinstance(node.value, ast.Name) and node.value.id == "runtime":
                return ast.copy_location(ast.Name(id=node.attr, ctx=node.ctx), node)
            return node

        def visit_Name(self, node):
            node.id = inverse.get(node.id, node.id)
            return node

        def visit_FunctionDef(self, node):
            node = self.generic_visit(node)
            node.name = inverse.get(node.name, node.name)
            return node

    counts = {}
    for item in baseline["definitions"]:
        tree = ast.parse((ROOT / item["path"]).read_text())
        matches = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                name = node.name
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                target = (
                    node.targets[0] if isinstance(node, ast.Assign) else node.target
                )
                name = target.id if isinstance(target, ast.Name) else None
            else:
                continue
            if name == item["current_name"]:
                matches.append(node)
        assert len(matches) == 1, item
        normalized = Normalize().visit(matches[0])
        actual = hashlib.sha256(ast.dump(normalized).encode()).hexdigest()
        assert actual == item["ast_sha256"], item
        original = item["original_source"]
        counts[original] = counts.get(original, 0) + 1
    return counts


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
