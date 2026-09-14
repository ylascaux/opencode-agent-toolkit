import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "oc2_usage.py"
spec = importlib.util.spec_from_file_location("oc2_usage", MODULE)
oc2_usage = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(oc2_usage)

TokenPricing = oc2_usage.TokenPricing
TokenUsage = oc2_usage.TokenUsage
estimate_cost_usd = oc2_usage.estimate_cost_usd


def test_estimates_input_output_reasoning_and_cache():
    pricing = {"provider/model": TokenPricing(input=2, output=10, cache_read=0.2, cache_write=2.5)}
    usage = TokenUsage(input=1_000_000, output=100_000, reasoning=50_000, cache_read=500_000, cache_write=20_000)
    assert estimate_cost_usd("provider/model", usage, pricing) == 3.65


def test_unknown_model_is_not_reported_as_zero_cost():
    assert estimate_cost_usd("provider/unknown", TokenUsage(input=1000), {}) is None


def test_rejects_negative_token_counts():
    pricing = {"provider/model": TokenPricing(input=1, output=1)}
    try:
        estimate_cost_usd("provider/model", TokenUsage(input=-1), pricing)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative token counts must be rejected")
