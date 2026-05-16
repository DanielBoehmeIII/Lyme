#!/usr/bin/env python3
"""Generate all Week 45 standard examples."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.lyme.standards.trace.examples import generate_all_examples as gen_traces
from src.lyme.standards.semantic_diff.examples import generate_all_examples as gen_diffs
from src.lyme.standards.benchmark_spec.registry import build_default_spec

OUTPUT = "lyme-output/standards"

def main():
    print("=== Generating Agent Trace Standard Examples ===")
    gen_traces(os.path.join(OUTPUT, "traces"))

    print("\n=== Generating Semantic Diff Standard Examples ===")
    gen_diffs(os.path.join(OUTPUT, "semantic-diffs"))

    print("\n=== Generating Cognition Benchmark Specification ===")
    spec = build_default_spec()
    spec_path = os.path.join(OUTPUT, "cognition-benchmark-spec.json")
    os.makedirs(os.path.dirname(spec_path), exist_ok=True)
    with open(spec_path, "w") as f:
        f.write(spec.to_json())
    print(f"Wrote {spec_path}")
    print(f"  Tasks: {len(spec.tasks)} across {len(spec.dimensions)} dimensions")

    print("\n=== Validation Demo ===")
    from src.lyme.standards.trace.validator import OpenTraceValidator
    from src.lyme.standards.trace.schema import OpenAgentTrace
    from src.lyme.standards.trace.examples import generate_simple_fix_trace
    validator = OpenTraceValidator()
    trace = generate_simple_fix_trace()
    result = validator.validate(trace)
    print(result.summary())

    print("\n=== Comparison Demo ===")
    from src.lyme.standards.trace.comparison import TraceComparer
    from src.lyme.standards.trace.examples import generate_complex_refactor_trace, generate_simple_fix_trace
    comparer = TraceComparer()
    report = comparer.compare(generate_simple_fix_trace(), generate_complex_refactor_trace())
    print(report.summary)

    print("\n=== Semantic Diff Renderer Demo ===")
    from src.lyme.standards.semantic_diff.renderer import SemanticDiffRenderer
    from src.lyme.standards.semantic_diff.examples import generate_bug_fix_diff
    from src.lyme.standards.semantic_diff.cli_export import DiffCLIExporter
    sd = generate_bug_fix_diff()
    renderer = SemanticDiffRenderer("markdown")
    print(renderer.render(sd)[:500] + "...\n")
    exporter = DiffCLIExporter("console")
    print(exporter.export(sd))

    print("\n=== All Standards Generated Successfully ===")
    print(f"Output directory: {os.path.abspath(OUTPUT)}")

if __name__ == "__main__":
    main()
