"""Tests for Weeks 109-110: Hardware tiers, local parity."""

import pytest
from src.lyme_model.learning.hardware_tiers import (
    HardwareTier, get_hardware_tiers, recommend_tier, HARDWARE_TIERS,
)
from src.lyme_model.learning.local_parity import (
    ParitySlice, find_parity_slice, build_demo_prompt, LOCAL_PARITY_SLICES,
)


class TestHardwareTiers:
    def test_all_tiers_have_required_fields(self):
        for t in HARDWARE_TIERS:
            assert t.name
            assert t.ram_gb > 0
            assert len(t.recommended_models) > 0
            assert len(t.supported_features) > 0

    def test_get_hardware_tiers(self):
        tiers = get_hardware_tiers()
        assert len(tiers) == 8

    def test_recommend_tier_cpu(self):
        t = recommend_tier(ram_gb=8, has_gpu=False)
        assert "8GB RAM" in t.name or "CPU-only" in t.name

    def test_recommend_tier_gpu(self):
        t = recommend_tier(ram_gb=16, vram_gb=8, has_gpu=True)
        assert "8GB VRAM" in t.name or "VRAM" in t.name

    def test_recommend_tier_high_end(self):
        t = recommend_tier(ram_gb=64, vram_gb=24, has_gpu=True)
        assert "24GB VRAM" in t.name or "workstation" in t.name

    def test_each_tier_has_vram_or_cpu_fallback(self):
        for t in HARDWARE_TIERS:
            assert t.vram_gb >= 0


class TestLocalParity:
    def test_slices_defined(self):
        assert "test_failure_explanation" in LOCAL_PARITY_SLICES
        assert "repo_qa" in LOCAL_PARITY_SLICES
        assert "safe_maintenance" in LOCAL_PARITY_SLICES

    def test_all_slices_have_fields(self):
        for name, s in LOCAL_PARITY_SLICES.items():
            assert s.domain == name
            assert s.local_quality > 0
            assert s.frontier_quality > 0
            assert s.parity_ratio > 0

    def test_parity_ratio_reasonable(self):
        for s in LOCAL_PARITY_SLICES.values():
            assert 0 < s.parity_ratio <= 1.0
            assert s.local_quality <= s.frontier_quality

    def test_find_parity_slice_all(self):
        r = find_parity_slice()
        assert "slices" in r
        assert len(r["slices"]) == 3
        assert r["best_parity"] > 0.9

    def test_find_parity_slice_specific(self):
        r = find_parity_slice("repo_qa")
        assert r["domain"] == "repo_qa"
        assert r["parity_ratio"] >= 0.9

    def test_find_parity_slice_not_found(self):
        r = find_parity_slice("nonexistent")
        assert "error" in r

    def test_build_demo_prompt(self):
        prompt = build_demo_prompt("test_failure_explanation")
        assert "Local Parity Demo" in prompt
        assert "test_failure_explanation" in prompt

    def test_build_demo_prompt_not_found(self):
        prompt = build_demo_prompt("nonexistent")
        assert "not found" in prompt
