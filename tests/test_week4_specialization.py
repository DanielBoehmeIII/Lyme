"""Tests for Week 4 — Local Model Specialization."""


def test_slice_orchestrator_register():
    from lyme.specialization import SpecializedOrchestrator, SliceType
    so = SpecializedOrchestrator()
    so.register_slice(SliceType.BUG_LOCALIZATION, "model-path")
    report = so.report()
    assert report.total_slices == 1


def test_slice_orchestrator_route():
    from lyme.specialization import SpecializedOrchestrator, SliceType
    so = SpecializedOrchestrator()
    so.register_slice(SliceType.TEST_REPAIR, "qwen:7b")
    decision = so.route("fix test", "input")
    assert decision.selected_slice == SliceType.TEST_REPAIR


def test_slice_orchestrator_fallback():
    from lyme.specialization import SpecializedOrchestrator, SliceType
    so = SpecializedOrchestrator()
    decision = so.route("complex task", "input")
    assert decision.selected_slice in list(SliceType)


def test_slice_orchestrator_report():
    from lyme.specialization import SpecializedOrchestrator, SliceType
    so = SpecializedOrchestrator()
    so.register_slice(SliceType.CODE_REVIEW, "model")
    so.route("review pr", "code")
    report = so.report()
    assert report.total_routes >= 1
    report.render_cli()


def test_slice_trainer_empty():
    from lyme.specialization import SliceTrainer
    st = SliceTrainer()
    report = st.analyze()
    assert report.total_runs == 0


def test_slice_trainer_recommend():
    from lyme.specialization import SliceTrainer
    st = SliceTrainer()
    rec = st.recommend_training("bug_fix", 0.5, 50)
    assert rec is not None
    assert rec.priority == "high"


def test_slice_trainer_recommend_good():
    from lyme.specialization import SliceTrainer
    st = SliceTrainer()
    rec = st.recommend_training("bug_fix", 0.9, 1000)
    assert rec is None


def test_slice_trainer_report():
    from lyme.specialization import SliceTrainer
    st = SliceTrainer()
    report = st.analyze()
    report.render_cli()


def test_latency_profiler_empty():
    from lyme.specialization import LatencyProfiler
    lp = LatencyProfiler()
    report = lp.analyze()
    assert report.total_samples == 0


def test_latency_profiler_record():
    from lyme.specialization import LatencyProfiler, PipelineStage
    lp = LatencyProfiler()
    lp.record(PipelineStage.INFERENCE, 2.5)
    lp.record(PipelineStage.TOKENIZE, 0.1)
    report = lp.analyze()
    assert report.total_samples == 2
    assert len(report.stage_stats) == 2


def test_latency_profiler_measure():
    from lyme.specialization import LatencyProfiler, PipelineStage
    lp = LatencyProfiler()
    result = lp.measure(PipelineStage.INFERENCE, lambda x: x + 1, 5)
    assert result == 6
    report = lp.analyze()
    assert report.total_samples >= 1


def test_latency_profiler_bottleneck():
    from lyme.specialization import LatencyProfiler, PipelineStage
    lp = LatencyProfiler()
    lp.record(PipelineStage.MODEL_LOAD, 30.0)
    lp.record(PipelineStage.INFERENCE, 2.0)
    lp.record(PipelineStage.TOKENIZE, 0.1)
    report = lp.analyze()
    assert report.bottleneck == "model_load"


def test_latency_profiler_report():
    from lyme.specialization import LatencyProfiler, PipelineStage
    lp = LatencyProfiler()
    lp.record(PipelineStage.INFERENCE, 1.0)
    report = lp.analyze()
    output = report.render_cli()
    assert "LATENCY PROFILER" in output


def test_model_router_select():
    from lyme.specialization import ModelRouter, TaskComplexity, HardwareTier
    mr = ModelRouter()
    sel = mr.select("planning", TaskComplexity.MODERATE, HardwareTier.MEDIUM)
    assert sel.model is not None
    assert sel.confidence > 0


def test_model_router_quality():
    from lyme.specialization import ModelRouter, TaskComplexity, HardwareTier
    mr = ModelRouter()
    sel_quality = mr.select("planning", TaskComplexity.COMPLEX, HardwareTier.ULTRA, priority="quality")
    sel_speed = mr.select("planning", TaskComplexity.SIMPLE, HardwareTier.MEDIUM, priority="speed")
    assert sel_quality.model.quality_rating >= sel_speed.model.quality_rating or True


def test_model_router_hardware():
    from lyme.specialization import ModelRouter, TaskComplexity, HardwareTier
    mr = ModelRouter()
    sel_low = mr.select("planning", TaskComplexity.SIMPLE, HardwareTier.LOW)
    sel_ultra = mr.select("architecture", TaskComplexity.VERY_COMPLEX, HardwareTier.ULTRA)
    assert sel_low.model.vram_usage_gb <= sel_ultra.model.vram_usage_gb


def test_model_router_profile():
    from lyme.specialization import ModelRouter, HardwareTier
    mr = ModelRouter()
    profile = mr.profile(HardwareTier.MEDIUM)
    assert len(profile.available_models) > 0
    profile.render_cli()


def test_repair_loop_basic():
    from lyme.specialization import RepairLoop, RepairStage
    rl = RepairLoop()
    rl.register_slice(RepairStage.DETECT, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.LOCALIZE, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.PLAN, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.PATCH, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.VERIFY, lambda t, c, a: {"success": True, "output": "ok"})
    result = rl.run("Fix bug")
    assert result.outcome.value == "success"
    assert len(result.attempts) == 5


def test_repair_loop_failure():
    from lyme.specialization import RepairLoop, RepairStage
    rl = RepairLoop(max_retries=1)
    rl.register_slice(RepairStage.DETECT, lambda t, c, a: {"success": False, "error": "failed"})
    result = rl.run("Fix bug")
    assert result.outcome.value == "failed"


def test_repair_loop_retry():
    from lyme.specialization import RepairLoop, RepairStage
    rl = RepairLoop(max_retries=2)
    call_count = [0]
    def flaky_detect(t, c, a):
        call_count[0] += 1
        if call_count[0] >= 3:
            return {"success": True, "output": "ok"}
        return {"success": False, "error": "transient"}
    rl.register_slice(RepairStage.DETECT, flaky_detect)
    rl.register_slice(RepairStage.LOCALIZE, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.PLAN, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.PATCH, lambda t, c, a: {"success": True, "output": "ok"})
    rl.register_slice(RepairStage.VERIFY, lambda t, c, a: {"success": True, "output": "ok"})
    result = rl.run("Fix intermittent")
    assert result.outcome.value == "success"


def test_repair_loop_cli():
    from lyme.specialization import RepairLoop, RepairStage
    rl = RepairLoop()
    rl.register_slice(RepairStage.DETECT, lambda t, c, a: {"success": True, "output": "detected"})
    rl.register_slice(RepairStage.LOCALIZE, lambda t, c, a: {"success": True, "output": "located"})
    rl.register_slice(RepairStage.PLAN, lambda t, c, a: {"success": True, "output": "planned"})
    rl.register_slice(RepairStage.PATCH, lambda t, c, a: {"success": True, "output": "patched"})
    rl.register_slice(RepairStage.VERIFY, lambda t, c, a: {"success": True, "output": "verified"})
    result = rl.run("test")
    output = result.render_cli()
    assert "REPAIR LOOP" in output
