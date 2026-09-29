import pytest
from app.services.research.verification import (
    DeterministicArithmeticVerifier,
    ArithmeticVerificationError,
    verify_calculation,
    verify_claim,
)


def test_arithmetic_verifier_basic_ops():
    verifier = DeterministicArithmeticVerifier()
    assert verifier.evaluate("2 + 3 * 4") == 14.0
    assert verifier.evaluate("(10 - 2) / 4") == 2.0
    assert verifier.evaluate("7 % 3") == 1.0
    assert verifier.evaluate("7 // 3") == 2.0
    assert verifier.evaluate("2 ** 3") == 8.0
    assert verifier.evaluate("-5 + 10") == 5.0


def test_arithmetic_verifier_whitelisted_functions():
    verifier = DeterministicArithmeticVerifier()
    assert verifier.evaluate("round(14.567, 2)") == 14.57
    assert verifier.evaluate("abs(-42)") == 42.0
    assert verifier.evaluate("min(10, 5, 20)") == 5.0
    assert verifier.evaluate("max(10, 5, 20)") == 20.0
    assert verifier.evaluate("pct_change(100, 125)") == 25.0
    assert verifier.evaluate("pct_change(1.20, 1.42)") == pytest.approx(18.3333, rel=1e-3)


def test_arithmetic_verifier_variables():
    verifier = DeterministicArithmeticVerifier()
    result = verifier.evaluate("mass * (velocity ** 2) / 2", variables={"mass": 10.0, "velocity": 3.0})
    assert result == 45.0


def test_arithmetic_verifier_safety_rejections():
    verifier = DeterministicArithmeticVerifier()

    # Rejects imports and globals
    with pytest.raises(ArithmeticVerificationError):
        verifier.evaluate("__import__('os').system('calc')")

    # Rejects attribute access
    with pytest.raises(ArithmeticVerificationError):
        verifier.evaluate("math.sqrt(16)")

    # Rejects non-whitelisted function
    with pytest.raises(ArithmeticVerificationError):
        verifier.evaluate("eval('2 + 2')")

    # Rejects division by zero
    with pytest.raises(ArithmeticVerificationError):
        verifier.evaluate("10 / 0")

    # Rejects excessive exponent
    with pytest.raises(ArithmeticVerificationError):
        verifier.evaluate("2 ** 11")


def test_arithmetic_verifier_resource_limits():
    verifier = DeterministicArithmeticVerifier(max_length=50, max_depth=3, max_ops=5)

    # Exceeds max length
    with pytest.raises(ArithmeticVerificationError, match="exceeds maximum allowed"):
        verifier.evaluate("1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1")

    # Exceeds AST depth
    with pytest.raises(ArithmeticVerificationError, match="depth"):
        verifier.evaluate("1 + (2 + (3 + (4 + 5)))")

    # Exceeds operation count
    verifier_ops = DeterministicArithmeticVerifier(max_depth=10, max_ops=3)
    with pytest.raises(ArithmeticVerificationError, match="operation count"):
        verifier_ops.evaluate("1 + 2 + 3 + 4")


def test_verify_calculation_verified_and_failed():
    # Verified within tolerance
    res_verified = verify_calculation("(1.42 / 1.20 - 1) * 100", 18.33, tolerance=0.01)
    assert res_verified.status == "verified"
    assert res_verified.computed_value == pytest.approx(18.3333, rel=1e-3)
    assert res_verified.reason["match"] is True

    # Failed (difference exceeds tolerance)
    res_failed = verify_calculation("100 * 1.5", 160.0, tolerance=0.1)
    assert res_failed.status == "failed"
    assert res_failed.computed_value == 150.0
    assert res_failed.expected_value == 160.0
    assert res_failed.reason["match"] is False

    # Unverified on error
    res_unverified = verify_calculation("100 / 0", 100.0)
    assert res_unverified.status == "unverified"
    assert "Division or modulo by zero" in res_unverified.reason["error"]


def test_verify_claim():
    # Valid derivation payload
    payload_valid = {
        "derivation": {
            "expression": "weight / (height ** 2)",
            "expected_value": 24.22,
            "tolerance": 0.01,
            "inputs": {"weight": 70.0, "height": 1.7}
        }
    }
    res_valid = verify_claim(payload_valid)
    assert res_valid.status == "verified"

    # Missing derivation
    res_missing = verify_claim({"text": "Just plain text"})
    assert res_missing.status == "unverified"
