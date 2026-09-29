import ast
import math
import operator
from typing import Any, Callable, Dict, Literal, Optional
from pydantic import BaseModel, Field

VerificationStatusType = Literal["verified", "unverified", "failed"]

MAX_EXPRESSION_LENGTH = 500
MAX_AST_DEPTH = 10
MAX_OPERATION_COUNT = 50
MAX_EXPONENT = 10
MAX_NUMERIC_MAGNITUDE = 1e15


class ArithmeticVerificationError(Exception):
    """Raised when an expression violates safety rules, resource limits, or arithmetic constraints."""
    pass


class VerificationResult(BaseModel):
    status: VerificationStatusType
    computed_value: Optional[float] = None
    expected_value: Optional[float] = None
    tolerance: Optional[float] = None
    reason: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


def _safe_round(x: Any, ndigits: Optional[Any] = None) -> float:
    if ndigits is not None:
        return float(round(float(x), int(ndigits)))
    return float(round(float(x)))


def _pct_change(a: float, b: float) -> float:
    """Calculates percentage change from a to b: ((b - a) / a) * 100."""
    if a == 0:
        raise ArithmeticVerificationError("Percentage change division by zero: baseline value is zero.")
    return ((b - a) / a) * 100.0


class DeterministicArithmeticVerifier:
    """
    Sandboxed AST-based deterministic arithmetic evaluator.
    Enforces strict operator whitelisting and resource limits without arbitrary code execution.
    """

    ALLOWED_BINARY_OPS: Dict[type, Callable[[Any, Any], Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    ALLOWED_UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    ALLOWED_COMPARISONS: Dict[type, Callable[[Any, Any], bool]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    ALLOWED_FUNCTIONS: Dict[str, Callable[..., Any]] = {
        "round": _safe_round,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": lambda *args: sum(args[0]) if len(args) == 1 and isinstance(args[0], (list, tuple)) else sum(args),
        "pct_change": _pct_change,
    }

    def __init__(
        self,
        max_length: int = MAX_EXPRESSION_LENGTH,
        max_depth: int = MAX_AST_DEPTH,
        max_ops: int = MAX_OPERATION_COUNT,
        max_exp: int = MAX_EXPONENT,
        max_magnitude: float = MAX_NUMERIC_MAGNITUDE,
    ):
        self.max_length = max_length
        self.max_depth = max_depth
        self.max_ops = max_ops
        self.max_exp = max_exp
        self.max_magnitude = max_magnitude
        self.op_count = 0

    def evaluate(self, expression: str, variables: Optional[Dict[str, float]] = None) -> float:
        if not expression or not expression.strip():
            raise ArithmeticVerificationError("Expression is empty.")

        expr = expression.strip()
        if len(expr) > self.max_length:
            raise ArithmeticVerificationError(
                f"Expression length ({len(expr)}) exceeds maximum allowed ({self.max_length})."
            )

        try:
            parsed = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ArithmeticVerificationError(f"Expression syntax error: {exc.msg}") from exc

        self.op_count = 0
        vars_dict = variables or {}
        return self._eval_node(parsed.body, depth=1, variables=vars_dict)

    def _eval_node(self, node: ast.AST, depth: int, variables: Dict[str, float]) -> Any:
        if depth > self.max_depth:
            raise ArithmeticVerificationError(
                f"Expression AST depth ({depth}) exceeds maximum limit ({self.max_depth})."
            )

        self.op_count += 1
        if self.op_count > self.max_ops:
            raise ArithmeticVerificationError(
                f"Expression operation count exceeded maximum allowed limit ({self.max_ops})."
            )

        # 1. Literals (Numbers)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                val = float(node.value)
                if abs(val) > self.max_magnitude:
                    raise ArithmeticVerificationError(
                        f"Numeric value ({val}) exceeds maximum magnitude ({self.max_magnitude})."
                    )
                return val
            raise ArithmeticVerificationError(f"Unsupported constant type: {type(node.value).__name__}")

        # 2. Variables (Names)
        if isinstance(node, ast.Name):
            if node.id in variables:
                val = float(variables[node.id])
                if abs(val) > self.max_magnitude:
                    raise ArithmeticVerificationError(
                        f"Variable '{node.id}' value ({val}) exceeds maximum magnitude ({self.max_magnitude})."
                    )
                return val
            raise ArithmeticVerificationError(f"Undefined variable in expression: '{node.id}'")

        # 3. Binary Operations
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_BINARY_OPS:
                raise ArithmeticVerificationError(f"Disallowed binary operator: {op_type.__name__}")

            left = self._eval_node(node.left, depth + 1, variables)
            right = self._eval_node(node.right, depth + 1, variables)

            if op_type is ast.Pow:
                if abs(right) > self.max_exp:
                    raise ArithmeticVerificationError(
                        f"Exponent ({right}) exceeds maximum exponent limit ({self.max_exp})."
                    )

            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ArithmeticVerificationError("Division or modulo by zero.")

            try:
                op_fn = self.ALLOWED_BINARY_OPS[op_type]
                result = float(op_fn(left, right))
            except OverflowError as exc:
                raise ArithmeticVerificationError("Arithmetic operation resulted in overflow.") from exc

            if math.isnan(result) or math.isinf(result) or abs(result) > self.max_magnitude:
                raise ArithmeticVerificationError(f"Computed value ({result}) exceeds magnitude limit or is NaN/Inf.")

            return result

        # 4. Unary Operations
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.ALLOWED_UNARY_OPS:
                raise ArithmeticVerificationError(f"Disallowed unary operator: {op_type.__name__}")

            operand = self._eval_node(node.operand, depth + 1, variables)
            op_fn = self.ALLOWED_UNARY_OPS[op_type]
            result = float(op_fn(operand))
            if abs(result) > self.max_magnitude:
                raise ArithmeticVerificationError(f"Computed value exceeds magnitude limit: {result}")
            return result

        # 5. Function Calls
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ArithmeticVerificationError("Arbitrary function or attribute call expressions are prohibited.")

            fn_name = node.func.id
            if fn_name not in self.ALLOWED_FUNCTIONS:
                raise ArithmeticVerificationError(f"Function '{fn_name}' is not in the safe mathematical whitelist.")

            args = [self._eval_node(arg, depth + 1, variables) for arg in node.args]
            fn = self.ALLOWED_FUNCTIONS[fn_name]
            try:
                res = fn(*args)
                result = float(res)
            except Exception as exc:
                raise ArithmeticVerificationError(f"Error executing function '{fn_name}': {str(exc)}") from exc

            if math.isnan(result) or math.isinf(result) or abs(result) > self.max_magnitude:
                raise ArithmeticVerificationError(f"Function '{fn_name}' returned value exceeding limits: {result}")
            return result

        # Prohibit anything else (attribute access, list comprehension, imports, etc.)
        raise ArithmeticVerificationError(f"Unsupported or unsafe expression element: {type(node).__name__}")


def verify_calculation(
    expression: str,
    expected_value: float,
    tolerance: float = 0.001,
    inputs: Optional[Dict[str, float]] = None,
) -> VerificationResult:
    """
    Evaluates an arithmetic expression and compares the computed value against an expected value.
    Returns a structured VerificationResult.
    """
    verifier = DeterministicArithmeticVerifier()
    try:
        computed = verifier.evaluate(expression, variables=inputs)
        diff = abs(computed - expected_value)
        if diff <= tolerance:
            return VerificationResult(
                status="verified",
                computed_value=computed,
                expected_value=expected_value,
                tolerance=tolerance,
                reason={"match": True, "difference": diff, "tolerance": tolerance},
                metadata={"evaluator": "DeterministicArithmeticVerifier", "expression": expression}
            )
        else:
            return VerificationResult(
                status="failed",
                computed_value=computed,
                expected_value=expected_value,
                tolerance=tolerance,
                reason={"match": False, "difference": diff, "tolerance": tolerance},
                metadata={"evaluator": "DeterministicArithmeticVerifier", "expression": expression}
            )
    except ArithmeticVerificationError as exc:
        return VerificationResult(
            status="unverified",
            computed_value=None,
            expected_value=expected_value,
            tolerance=tolerance,
            reason={"error": str(exc), "expression": expression},
            metadata={"evaluator": "DeterministicArithmeticVerifier", "error_type": "ArithmeticVerificationError"}
        )
    except Exception as exc:
        return VerificationResult(
            status="unverified",
            computed_value=None,
            expected_value=expected_value,
            tolerance=tolerance,
            reason={"error": f"Unexpected verification failure: {str(exc)}", "expression": expression},
            metadata={"evaluator": "DeterministicArithmeticVerifier", "error_type": type(exc).__name__}
        )


def verify_claim(claim_payload: Dict[str, Any]) -> VerificationResult:
    """
    Inspects candidate payload for derivation metadata and runs deterministic verification if present.
    """
    derivation = claim_payload.get("derivation")
    if not derivation or not isinstance(derivation, dict):
        return VerificationResult(
            status="unverified",
            reason={"detail": "No derivation expression found in payload"},
            metadata={"evaluator": "DeterministicArithmeticVerifier"}
        )

    expr = derivation.get("expression")
    if not expr:
        return VerificationResult(
            status="unverified",
            reason={"detail": "Derivation missing 'expression' string"},
            metadata={"evaluator": "DeterministicArithmeticVerifier"}
        )

    expected = derivation.get("expected_value")
    if expected is None:
        return VerificationResult(
            status="unverified",
            reason={"detail": "Derivation missing 'expected_value' to verify against"},
            metadata={"evaluator": "DeterministicArithmeticVerifier"}
        )

    tolerance = derivation.get("tolerance", 0.001)
    inputs = derivation.get("inputs", {})
    return verify_calculation(
        expression=expr,
        expected_value=float(expected),
        tolerance=float(tolerance),
        inputs=inputs
    )
