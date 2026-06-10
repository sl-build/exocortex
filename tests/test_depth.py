"""Tests for brain.depth module."""

import pytest

from brain.depth import VALID_DEPTHS, get_depth_config, merge_depth_into_params


class TestDepthConfigs:
    """Depth presets must cover article's implied depth levels."""

    def test_all_depths_exist(self):
        assert set(VALID_DEPTHS) == {"quick", "normal", "deep", "exhaustive"}

    def test_quick_is_light(self):
        cfg = get_depth_config("quick")
        assert cfg["max_tokens"] == 4096
        assert cfg["reasoning_effort"] == "low"

    def test_deep_is_heavy(self):
        cfg = get_depth_config("deep")
        assert cfg["max_tokens"] == 16384
        assert cfg["reasoning_effort"] == "high"

    def test_exhaustive_is_max(self):
        cfg = get_depth_config("exhaustive")
        assert cfg["max_tokens"] == 32768

    def test_invalid_depth_raises(self):
        with pytest.raises(ValueError, match="Unknown depth"):
            get_depth_config("super_deep")


class TestMergeDepthIntoParams:
    """Merging depth config into API params."""

    def test_merge_adds_max_tokens(self):
        params = {"model": "test", "messages": []}
        merged = merge_depth_into_params(params, "deep")
        assert merged["max_tokens"] == 16384

    def test_no_temperature_or_reasoning_effort(self):
        params = {"model": "test", "messages": []}
        merged = merge_depth_into_params(params, "deep")
        assert "temperature" not in merged
        assert "reasoning_effort" not in merged

    def test_existing_max_tokens_not_overridden(self):
        params = {"model": "test", "messages": [], "max_tokens": 999}
        merged = merge_depth_into_params(params, "deep")
        assert merged["max_tokens"] == 999
