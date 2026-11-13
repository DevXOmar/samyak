"""Static, normalized edit operators for historical buggy→fixed functions."""

import ast
from collections import Counter


def normalized_edit(before, after):
    try:
        a, b = ast.parse(before), ast.parse(after)
    except SyntaxError:
        return "UNSUPPORTED_EDIT"
    old, new = list(ast.walk(a)), list(ast.walk(b))
    ca, cb = Counter(type(n).__name__ for n in old), Counter(type(n).__name__ for n in new)
    if cb["If"] > ca["If"]:
        return "ADD_GUARD"
    old_comps = [type(n.ops[0]).__name__ for n in old if isinstance(n, ast.Compare) and len(n.ops) == 1]
    new_comps = [type(n.ops[0]).__name__ for n in new if isinstance(n, ast.Compare) and len(n.ops) == 1]
    if len(old_comps) == len(new_comps):
        for x, y in zip(old_comps, new_comps):
            if x != y:
                return f"COMPARISON_{x.upper()}_TO_{y.upper()}"
    for node_type, operator in [
        (ast.Return, "REPLACE_RETURN"),
        (ast.Subscript, "INDEX_SHIFT"),
        (ast.BinOp, "CHANGE_ARITHMETIC_OPERATOR"),
        (ast.BoolOp, "CHANGE_BOOLEAN_OPERATOR"),
        (ast.Call, "CHANGE_CALL"),
    ]:
        if [ast.dump(n) for n in old if isinstance(n, node_type)] != [
            ast.dump(n) for n in new if isinstance(n, node_type)
        ]:
            return operator
    return "REPLACE_EXPRESSION"
