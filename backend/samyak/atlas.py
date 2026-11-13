"""Bounded inspectable AST, independent of numeric training features."""

import ast


def syntax_tree(source, limit=200):
    tree = ast.parse(source)
    nodes, edges = [], []

    def visit(node, parent=None, field="root", depth=0):
        if len(nodes) >= limit:
            return
        ident = "ast:" + str(len(nodes))
        row = {
            "id": ident,
            "kind": "AST",
            "ast_type": type(node).__name__,
            "depth": depth,
            "start_line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
        }
        if isinstance(node, (ast.FunctionDef, ast.Name, ast.arg)):
            row["name"] = getattr(node, "name", getattr(node, "id", getattr(node, "arg", "")))
        nodes.append(row)
        if parent:
            edges.append({"source": parent, "target": ident, "kind": field})
        for name, value in ast.iter_fields(node):
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST) and not isinstance(
                    child, (ast.expr_context, ast.operator, ast.cmpop, ast.boolop, ast.unaryop)
                ):
                    visit(child, ident, name, depth + 1)

    visit(tree)
    return {"nodes": nodes, "edges": edges, "limit": limit, "truncated": len(list(ast.walk(tree))) > limit}
