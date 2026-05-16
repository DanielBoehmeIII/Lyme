from __future__ import annotations

import ast
import math
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .evolution_model import (
    EvolutionModel, EvolutionSnapshot, EvolutionMetrics, EvolutionTrend,
    EvolutionTimeline, TemporalEvent, TemporalEventType, StabilityClass,
)


class EvolutionAnalyzer:
    def analyze(self, repo_path: Path) -> EvolutionModel:
        repo_path = Path(repo_path).resolve()
        model = EvolutionModel(repo_path=str(repo_path))

        events = self._extract_events(repo_path)
        for ev in events:
            model.add_event(ev)

        snapshots = self._create_snapshots(repo_path, events)
        for snap in snapshots:
            model.timeline.add_snapshot(snap)

        trends = self._compute_trends(model.timeline)
        model.timeline.trends = trends

        model.subsystem_history = self._compute_subsystem_history(repo_path, events)

        return model

    def _extract_events(self, repo_path: Path) -> List[TemporalEvent]:
        events: List[TemporalEvent] = []

        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s",
                 "--numstat", "-500"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return events

            lines = result.stdout.splitlines()
            current_hash = ""
            current_author = ""
            current_timestamp = 0.0
            current_msg = ""
            current_files: List[str] = []
            total_added = 0
            total_removed = 0

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if re.match(r"^[a-f0-9]{40}$", line.split("|")[0] if "|" in line else ""):
                    if current_hash and current_files:
                        event = TemporalEvent(
                            event_type=self._classify_event(current_msg),
                            timestamp=current_timestamp,
                            commit_hash=current_hash,
                            author=current_author,
                            message=current_msg,
                            files_changed=len(current_files),
                            lines_added=total_added,
                            lines_removed=total_removed,
                            subsystems=list(set(
                                f.split("/")[0] for f in current_files if "/" in f
                            )),
                        )
                        events.append(event)

                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        current_hash = parts[0]
                        current_author = parts[1]
                        try:
                            current_timestamp = float(parts[2])
                        except ValueError:
                            current_timestamp = time.time()
                        current_msg = parts[3]
                    current_files = []
                    total_added = 0
                    total_removed = 0

                elif re.match(r"^\d+\s+\d+\s+", line):
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        try:
                            added = int(parts[0]) if parts[0] != "-" else 0
                            removed = int(parts[1]) if parts[1] != "-" else 0
                            total_added += added
                            total_removed += removed
                            current_files.append(parts[2])
                        except ValueError:
                            pass

            if current_hash and current_files:
                event = TemporalEvent(
                    event_type=self._classify_event(current_msg),
                    timestamp=current_timestamp,
                    commit_hash=current_hash,
                    author=current_author,
                    message=current_msg,
                    files_changed=len(current_files),
                    lines_added=total_added,
                    lines_removed=total_removed,
                    subsystems=list(set(
                        f.split("/")[0] for f in current_files if "/" in f
                    )),
                )
                events.append(event)

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            pass

        return events

    def _classify_event(self, message: str) -> TemporalEventType:
        msg = message.lower()
        if any(kw in msg for kw in ("refactor", "restructure", "redesign", "rewrite")):
            return TemporalEventType.REFACTOR
        if any(kw in msg for kw in ("migrate", "migration", "upgrade", "port")):
            return TemporalEventType.MIGRATION
        if any(kw in msg for kw in ("fix", "bug", "hotfix", "patch", "issue")):
            return TemporalEventType.BUG_FIX
        if any(kw in msg for kw in ("feat", "feature", "add", "implement")):
            return TemporalEventType.FEATURE_ADD
        if any(kw in msg for kw in ("deprecat", "remove", "delete")):
            return TemporalEventType.DEPRECATION
        if any(kw in msg for kw in ("architect", "modulariz", "extract")):
            return TemporalEventType.ARCHITECTURE_CHANGE
        if any(kw in msg for kw in ("depend", "bump", "update")):
            return TemporalEventType.DEPENDENCY_CHANGE
        if any(kw in msg for kw in ("break", "incompat")):
            return TemporalEventType.BREAKING_CHANGE
        if any(kw in msg for kw in ("perf", "slow", "latency", "optimiz")):
            return TemporalEventType.PERFORMANCE_REGESSION
        return TemporalEventType.COMMIT

    def _create_snapshots(self, repo_path: Path, events: List[TemporalEvent]) -> List[EvolutionSnapshot]:
        if not events:
            return []

        events.sort(key=lambda e: e.timestamp)
        start_time = events[0].timestamp
        end_time = events[-1].timestamp
        duration = end_time - start_time

        num_snapshots = max(5, min(20, len(events) // 25))
        interval = duration / num_snapshots

        snapshots: List[EvolutionSnapshot] = []
        for i in range(num_snapshots):
            period_start = start_time + i * interval
            period_end = period_start + interval

            period_events = [
                e for e in events
                if period_start <= e.timestamp < period_end
            ]

            if not period_events:
                continue

            metrics = self._compute_metrics(repo_path, period_events)
            growth = len(period_events) / max(interval, 1)
            churn = sum(e.lines_added + e.lines_removed for e in period_events) / max(interval, 1)

            snap = EvolutionSnapshot(
                period_start=period_start,
                period_end=period_end,
                metrics=metrics,
                events=period_events[:50],
                growth_rate=growth,
                churn_rate=churn,
            )
            snapshots.append(snap)

        self._classify_stability(snapshots)
        return snapshots

    def _compute_metrics(self, repo_path: Path, events: List[TemporalEvent]) -> EvolutionMetrics:
        total_files = 0
        total_lines = 0
        total_lines_of_code = 0
        dep_count = 0

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            total_files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = len(text.splitlines())
                total_lines += lines

                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        dep_count += 1
            except Exception:
                pass

        authors = set(e.author for e in events)

        return EvolutionMetrics(
            timestamp=time.time(),
            total_files=total_files,
            total_lines=total_lines,
            total_commits=len(events),
            total_authors=len(authors),
            avg_file_complexity=total_lines / max(total_files, 1),
            dependency_count=dep_count,
            subsystem_count=len(set(
                s for e in events for s in e.subsystems
            )),
        )

    def _classify_stability(self, snapshots: List[EvolutionSnapshot]):
        if len(snapshots) < 2:
            return

        for i, snap in enumerate(snapshots):
            if i == 0:
                snap.stability = StabilityClass.EMERGING
                continue

            prev = snapshots[i - 1]
            growth_delta = snap.growth_rate - prev.growth_rate if prev.growth_rate > 0 else snap.growth_rate

            if growth_delta > 0.5:
                snap.stability = StabilityClass.CHAOTIC
            elif growth_delta > 0.1:
                snap.stability = StabilityClass.GROWING
            elif growth_delta < -0.3:
                snap.stability = StabilityClass.DECAYING
            elif abs(growth_delta) <= 0.1:
                snap.stability = StabilityClass.STABLE
            else:
                snap.stability = StabilityClass.UNKNOWN

    def _compute_trends(self, timeline: EvolutionTimeline) -> Dict[str, EvolutionTrend]:
        if not timeline.snapshots:
            return {}

        metrics = ["total_files", "total_lines", "total_commits", "avg_file_complexity"]
        trends: Dict[str, EvolutionTrend] = {}

        for metric in metrics:
            values = [getattr(s.metrics, metric, 0) for s in timeline.snapshots]
            timestamps = [s.period_end for s in timeline.snapshots]

            if len(values) >= 2:
                slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
                mean_val = sum(values) / len(values)
                variance = sum((v - mean_val) ** 2 for v in values) / len(values)
                volatility = math.sqrt(variance) / max(mean_val, 0.01)

                deltas = [values[j] - values[j - 1] for j in range(1, len(values))]
                acceleration = (deltas[-1] - deltas[0]) / max(len(deltas) - 1, 1) if len(deltas) >= 2 else 0

                is_alarming = (
                    (volatility > 0.5 and metric in ("avg_file_complexity", "total_lines")) or
                    (acceleration > 10 and metric == "total_lines")
                )

                trends[metric] = EvolutionTrend(
                    metric=metric,
                    values=values,
                    timestamps=timestamps,
                    slope=slope,
                    volatility=volatility,
                    acceleration=acceleration,
                    is_alarming=is_alarming,
                )

        return trends

    def _compute_subsystem_history(
        self, repo_path: Path, events: List[TemporalEvent]
    ) -> Dict[str, List[EvolutionMetrics]]:
        subsystem_events: Dict[str, List[TemporalEvent]] = defaultdict(list)
        for ev in events:
            for sub in ev.subsystems:
                subsystem_events[sub].append(ev)

        history: Dict[str, List[EvolutionMetrics]] = {}
        for sub, sub_events in subsystem_events.items():
            metrics = self._compute_metrics(repo_path / sub if (repo_path / sub).exists() else repo_path, sub_events)
            history[sub] = [metrics]

        return history


class TrendDetector:
    def detect(self, model: EvolutionModel) -> List[Dict[str, Any]]:
        trends = []
        for metric_name, trend in model.timeline.trends.items():
            if trend.is_alarming:
                trends.append({
                    "metric": metric_name,
                    "severity": "high" if trend.acceleration > 0 else "medium",
                    "signal": f"{metric_name} trending {'up' if trend.slope > 0 else 'down'} "
                              f"(slope={trend.slope:.2f}, volatility={trend.volatility:.2f})",
                    "values": trend.values,
                })
            elif abs(trend.slope) > 0.1:
                trends.append({
                    "metric": metric_name,
                    "severity": "low",
                    "signal": f"{metric_name} showing mild trend (slope={trend.slope:.3f})",
                    "values": trend.values,
                })

        return trends


class StabilityAnalyzer:
    def analyze(self, model: EvolutionModel) -> Dict[str, Any]:
        if not model.timeline.snapshots:
            return {"stability": "unknown", "snapshots_available": 0}

        stability_counts: Counter = Counter()
        for snap in model.timeline.snapshots:
            stability_counts[snap.stability.value] += 1

        total = len(model.timeline.snapshots)
        recent = model.timeline.snapshots[-1] if model.timeline.snapshots else None

        return {
            "current_stability": recent.stability.value if recent else "unknown",
            "stability_distribution": dict(stability_counts),
            "stable_ratio": stability_counts.get("stable", 0) / max(total, 1) * 100,
            "chaotic_ratio": stability_counts.get("chaotic", 0) / max(total, 1) * 100,
            "snapshots_total": total,
        }


class ComplexityTracker:
    def track(self, repo_path: Path) -> Dict[str, Any]:
        file_complexities: List[Dict[str, Any]] = []

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                lines = len(text.splitlines())

                class_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                func_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef))
                import_count = sum(
                    1 for _ in ast.walk(tree)
                    if isinstance(_, (ast.Import, ast.ImportFrom))
                )

                complexity = lines * 0.3 + func_count * 2 + class_count * 5 + import_count * 1
                rel = str(f.relative_to(repo_path))

                file_complexities.append({
                    "file": rel,
                    "lines": lines,
                    "functions": func_count,
                    "classes": class_count,
                    "imports": import_count,
                    "complexity_score": complexity,
                })
            except Exception:
                pass

        file_complexities.sort(key=lambda x: -x["complexity_score"])

        return {
            "total_files_analyzed": len(file_complexities),
            "total_complexity": sum(fc["complexity_score"] for fc in file_complexities),
            "avg_complexity": (
                sum(fc["complexity_score"] for fc in file_complexities) / max(len(file_complexities), 1)
            ),
            "most_complex_files": file_complexities[:20],
        }


class RefactorWaveDetector:
    def detect(self, events: List[TemporalEvent]) -> List[Dict[str, Any]]:
        if not events:
            return []

        refactor_events = sorted(
            [e for e in events if e.event_type == TemporalEventType.REFACTOR],
            key=lambda e: e.timestamp,
        )

        if not refactor_events:
            return []

        waves: List[Dict[str, Any]] = []
        current_wave: List[TemporalEvent] = [refactor_events[0]]
        wave_start = refactor_events[0].timestamp
        gap_threshold = 86400 * 14

        for ev in refactor_events[1:]:
            if ev.timestamp - wave_start < gap_threshold * 2:
                current_wave.append(ev)
            else:
                if len(current_wave) >= 3:
                    waves.append({
                        "start": current_wave[0].timestamp,
                        "end": current_wave[-1].timestamp,
                        "refactor_count": len(current_wave),
                        "authors": list(set(e.author for e in current_wave)),
                        "intensity": len(current_wave) / max(
                            (current_wave[-1].timestamp - current_wave[0].timestamp) / 86400, 1
                        ),
                    })
                current_wave = [ev]
                wave_start = ev.timestamp

        if len(current_wave) >= 3:
            waves.append({
                "start": current_wave[0].timestamp,
                "end": current_wave[-1].timestamp,
                "refactor_count": len(current_wave),
                "authors": list(set(e.author for e in current_wave)),
                "intensity": len(current_wave) / max(
                    (current_wave[-1].timestamp - current_wave[0].timestamp) / 86400, 1
                ),
            })

        return sorted(waves, key=lambda w: -w["intensity"])[:10]


class AnomalyDetector:
    def detect(self, model: EvolutionModel) -> List[Dict[str, Any]]:
        anomalies: List[Dict[str, Any]] = []

        if len(model.events) < 10:
            return anomalies

        weekly_counts: Dict[int, int] = defaultdict(int)
        for ev in model.events:
            week_key = int(ev.timestamp / (86400 * 7))
            weekly_counts[week_key] += 1

        if weekly_counts:
            counts = list(weekly_counts.values())
            mean = sum(counts) / len(counts)
            std = math.sqrt(sum((c - mean) ** 2 for c in counts) / len(counts)) if counts else 0

            for week, count in weekly_counts.items():
                if std > 0 and count > mean + 2 * std:
                    anomalies.append({
                        "type": "commit_burst",
                        "week": week,
                        "commit_count": count,
                        "expected": mean,
                        "severity": "high" if count > mean + 3 * std else "medium",
                        "description": f"Unusual commit burst: {count} commits (expected {mean:.0f})",
                    })

        refactor_events = [e for e in model.events if e.event_type == TemporalEventType.REFACTOR]
        bug_events = [e for e in model.events if e.event_type == TemporalEventType.BUG_FIX]

        if len(refactor_events) > len(model.events) * 0.3 and len(refactor_events) > 10:
            anomalies.append({
                "type": "refactor_density",
                "refactor_count": len(refactor_events),
                "total_count": len(model.events),
                "severity": "medium",
                "description": f"High refactor density: {len(refactor_events)}/{len(model.events)} commits are refactors",
            })

        if bug_events and refactor_events:
            recent_bugs = len([e for e in bug_events if e.timestamp > model.events[-1].timestamp - 86400 * 30])
            if recent_bugs > len(bug_events) * 0.5 and recent_bugs > 5:
                anomalies.append({
                    "type": "bug_acceleration",
                    "recent_bugs": recent_bugs,
                    "severity": "high",
                    "description": f"Bug fix acceleration: {recent_bugs} bugs in last 30 days",
                })

        return anomalies[:20]
