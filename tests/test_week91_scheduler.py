"""Tests for Week 91 — Hardware-Aware Scheduling."""

import pytest
from src.lyme_model.hardware import (
    HardwareScheduler, SchedulingDecision, HardwareState,
    TaskRequirements, HardwareMonitor, detect_all, estimate_vram,
)
from src.lyme_model.hardware.scheduler import (
    ComputeBackend, TaskDifficulty, MODEL_CATALOG,
)


class TestSchedulingDecision:
    def test_decision_defaults(self):
        d = SchedulingDecision()
        assert d.model == ""
        assert d.quantization == "Q4"
        assert d.backend == ComputeBackend.GPU
        assert d.fallback_enabled is True

    def test_decision_to_dict(self):
        d = SchedulingDecision(
            model="qwen2.5-coder:7b",
            quantization="Q4",
            backend=ComputeBackend.CPU,
            max_context=2048,
        )
        dd = d.to_dict()
        assert dd["model"] == "qwen2.5-coder:7b"
        assert dd["quantization"] == "Q4"
        assert dd["max_context"] == 2048

    def test_decision_summary(self):
        d = SchedulingDecision(
            model="test-model",
            reasoning=["GPU available", "Sufficient VRAM"],
        )
        s = d.summary()
        assert "test-model" in s
        assert "GPU available" in s


class TestHardwareState:
    def test_state_defaults(self):
        s = HardwareState()
        assert s.vram_total_mb == 0
        assert s.gpu_present is False

    def test_can_use_gpu_true(self):
        s = HardwareState(gpu_present=True, vram_available_mb=4000)
        assert s.can_use_gpu is True

    def test_can_use_gpu_false_no_gpu(self):
        s = HardwareState(gpu_present=False, vram_available_mb=4000)
        assert s.can_use_gpu is False

    def test_can_use_gpu_false_low_vram(self):
        s = HardwareState(gpu_present=True, vram_available_mb=1000)
        assert s.can_use_gpu is False


class TestHardwareScheduler:
    def test_scheduler_initializes(self):
        s = HardwareScheduler()
        assert s.decisions == []

    def test_decide_with_gpu(self):
        s = HardwareScheduler()
        state = HardwareState(
            vram_total_mb=8000, vram_available_mb=7000,
            gpu_present=True, gpu_name="RTX 4060",
            ram_total_gb=32, cpu_cores=8,
        )
        decision = s.decide(state)
        assert decision.backend == ComputeBackend.GPU
        assert decision.model != ""
        assert len(decision.reasoning) >= 3

    def test_decide_without_gpu(self):
        s = HardwareScheduler()
        state = HardwareState(
            vram_total_mb=0, vram_available_mb=0,
            gpu_present=False, ram_total_gb=16, cpu_cores=8,
        )
        decision = s.decide(state)
        assert decision.backend == ComputeBackend.CPU
        assert decision.fallback_enabled is True

    def test_decide_easy_task(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=8000, gpu_present=True)
        task = TaskRequirements(difficulty=TaskDifficulty.EASY, estimated_context=2048)
        decision = s.decide(state, task)
        assert decision.model != ""

    def test_decide_complex_task(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=12000, gpu_present=True)
        task = TaskRequirements(difficulty=TaskDifficulty.COMPLEX, estimated_context=8192)
        decision = s.decide(state, task)
        assert decision.model != ""

    def test_decide_limited_vram(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=3000, gpu_present=True, vram_available_mb=2500)
        decision = s.decide(state)
        assert decision.quantization == "Q4"
        assert decision.fallback_enabled is True

    def test_decide_abundant_vram(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=24000, gpu_present=True, vram_available_mb=22000)
        decision = s.decide(state)
        assert decision.quantization == "Q8"

    def test_should_unload_true(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=3000, model_loaded=True, loaded_model="test")
        assert s.should_unload(state, idle_seconds=150) is True

    def test_should_unload_false(self):
        s = HardwareScheduler()
        state = HardwareState(model_loaded=True, loaded_model="test")
        assert s.should_unload(state, idle_seconds=10) is False

    def test_should_unload_no_model(self):
        s = HardwareScheduler()
        state = HardwareState(model_loaded=False)
        assert s.should_unload(state, idle_seconds=500) is False

    def test_should_unload_low_vram_threshold(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=3000, model_loaded=True)
        assert s.should_unload(state, idle_seconds=150) is True
        assert s.should_unload(state, idle_seconds=100) is False

    def test_decisions_tracked(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=8000, gpu_present=True)
        s.decide(state)
        s.decide(state)
        assert len(s.decisions) == 2

    def test_select_quantization_low(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=2000)
        assert s.select_quantization(state) == "Q4"

    def test_select_quantization_medium(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=6000)
        assert s.select_quantization(state) == "Q4"

    def test_select_quantization_high(self):
        s = HardwareScheduler()
        state = HardwareState(vram_total_mb=12000)
        assert s.select_quantization(state) == "Q8"

    def test_track_decision_confidence(self):
        s = HardwareScheduler()
        state_gpu = HardwareState(vram_total_mb=8000, gpu_present=True)
        state_cpu = HardwareState(vram_total_mb=0, gpu_present=False)
        d_gpu = s.decide(state_gpu)
        d_cpu = s.decide(state_cpu)
        assert d_gpu.confidence >= d_cpu.confidence

    def test_model_catalog_has_entries(self):
        assert len(MODEL_CATALOG) >= 5

    def test_each_model_has_quality_score(self):
        for model in MODEL_CATALOG:
            assert 0 <= model["quality"] <= 1.0


class TestHardwareIntegration:
    def test_detect_all_runs(self):
        profile = detect_all()
        assert profile.platform != ""
        assert profile.cpu.cores > 0

    def test_estimate_vram_positive(self):
        vram = estimate_vram(7.0, 4)
        assert vram > 0

    def test_hardware_monitor_initializes(self):
        m = HardwareMonitor()
        assert m is not None
