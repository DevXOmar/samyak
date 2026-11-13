import ast
import copy
import difflib

FAMILIES = [
    "BOUNDARY_COMPARISON",
    "CONDITION_NEGATION",
    "INDEX_OFFSET",
    "GUARD_REMOVAL",
    "ARITHMETIC_OPERATOR",
    "RETURN_VALUE",
]


def mutations(source, target_name, per_family=2):
    tree = ast.parse(source)
    target = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == target_name)
    counts = dict.fromkeys(FAMILIES, 0)
    candidates = []
    for n in ast.walk(target):
        variants = []
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            swap = {
                ast.Lt: ast.LtE,
                ast.LtE: ast.Lt,
                ast.Gt: ast.GtE,
                ast.GtE: ast.Gt,
                ast.Eq: ast.NotEq,
                ast.NotEq: ast.Eq,
            }
            if type(n.ops[0]) in swap:
                changed = copy.deepcopy(n)
                changed.ops[0] = swap[type(n.ops[0])]()
                variants.append(
                    (
                        "BOUNDARY_COMPARISON",
                        changed,
                        f"COMPARISON_{type(changed.ops[0]).__name__.upper()}_TO_{type(n.ops[0]).__name__.upper()}",
                    )
                )
        if isinstance(n, (ast.If, ast.While)):
            changed = copy.deepcopy(n)
            changed.test = ast.UnaryOp(op=ast.Not(), operand=changed.test)
            variants.append(("CONDITION_NEGATION", changed, "CHANGE_BOOLEAN_OPERATOR"))
        if isinstance(n, ast.If) and any(isinstance(x, (ast.Raise, ast.Return)) for x in n.body):
            changed = copy.deepcopy(n)
            changed.test = ast.Constant(value=False)
            variants.append(("GUARD_REMOVAL", changed, "ADD_GUARD"))
        if isinstance(n, ast.Subscript) and not isinstance(n.slice, ast.Slice):
            changed = copy.deepcopy(n)
            changed.slice = ast.BinOp(left=changed.slice, op=ast.Add(), right=ast.Constant(value=1))
            variants.append(("INDEX_OFFSET", changed, "INDEX_SHIFT"))
        if isinstance(n, ast.BinOp):
            swap = {
                ast.Add: ast.Sub,
                ast.Sub: ast.Add,
                ast.Mult: ast.Add,
                ast.Div: ast.Mult,
                ast.FloorDiv: ast.Mult,
                ast.Mod: ast.FloorDiv,
            }
            if type(n.op) in swap:
                changed = copy.deepcopy(n)
                changed.op = swap[type(n.op)]()
                variants.append(("ARITHMETIC_OPERATOR", changed, "CHANGE_ARITHMETIC_OPERATOR"))
        if isinstance(n, ast.Return) and n.value is not None:
            changed = copy.deepcopy(n)
            changed.value = ast.Constant(value=0)
            variants.append(("RETURN_VALUE", changed, "REPLACE_RETURN"))
        for family, replacement, operator in variants:
            if counts[family] >= per_family:
                continue

            # Replace by unique AST type/location after copying the tree.
            class PositionedReplace(ast.NodeTransformer):
                def generic_visit(self, node):
                    if (
                        type(node) is type(n)
                        and getattr(node, "lineno", None) == n.lineno
                        and getattr(node, "col_offset", None) == n.col_offset
                    ):
                        return copy.deepcopy(replacement)
                    return super().generic_visit(node)

            changed_tree = ast.fix_missing_locations(PositionedReplace().visit(copy.deepcopy(tree)))
            buggy = ast.unparse(changed_tree) + "\n"
            fixed = ast.unparse(tree) + "\n"
            if ast.dump(changed_tree) == ast.dump(tree):
                continue
            fault_lines = []
            for tag, i, j, _, _ in difflib.SequenceMatcher(
                None, buggy.splitlines(), fixed.splitlines()
            ).get_opcodes():
                if tag != "equal":
                    fault_lines.extend(range(i + 1, max(i + 2, j + 1)))
            candidates.append(
                {
                    "buggy": buggy,
                    "fixed": fixed,
                    "family": family,
                    "operator": operator,
                    "fault_lines": fault_lines,
                }
            )
            counts[family] += 1
    return candidates
