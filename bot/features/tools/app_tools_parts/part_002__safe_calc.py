from ast import ast

# Auto-split part 2: _safe_calc
def _safe_calc(node: ast.AST, depth: int = 0):
    if depth > 32:
        raise ValueError("expression too deep")
    if isinstance(node, ast.Expression):
        return _safe_calc(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        if abs(node.value) > 10**100:
            raise ValueError("number too large")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_UNARY:
        return _CALC_UNARY[type(node.op)](_safe_calc(node.operand, depth + 1))
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_BINOPS:
        left = _safe_calc(node.left, depth + 1)
        right = _safe_calc(node.right, depth + 1)
        if isinstance(node.op, ast.Pow):
            if abs(right) > 1000 or abs(left) > 10**6:
                raise ValueError("power too large")
        result = _CALC_BINOPS[type(node.op)](left, right)
        if isinstance(result, complex) or not math.isfinite(float(result)) or abs(result) > 10**200:
            raise ValueError("result too large")
        return result
    raise ValueError("unsupported expression")
