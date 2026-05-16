"""Week 96 — Lyme Model Dataset v0.1 tests."""

import json
import pytest
from pathlib import Path

from src.lyme_model.learning.dataset_v01 import (
    DatasetV01Generator,
    DatasetExporter,
    DatasetCard,
    generate_dataset_v01,
    SYNTHETIC_REPOS,
)


class TestSyntheticRepos:
    def test_all_repos_have_required_fields(self):
        for name, repo in SYNTHETIC_REPOS.items():
            assert "language" in repo
            assert "framework" in repo
            assert "files" in repo
            assert len(repo["files"]) >= 1

    def test_repo_names_are_unique(self):
        assert len(SYNTHETIC_REPOS) == 5


class TestDatasetCard:
    def test_defaults(self):
        card = DatasetCard()
        assert card.name == "Lyme Model Dataset v0.1"
        assert card.total_examples == 0

    def test_to_dict(self):
        card = DatasetCard(
            total_examples=100,
            train_count=80,
            val_count=10,
            test_count=10,
            by_task_type={"qa": 20, "fix": 80},
            by_difficulty={"easy": 50, "medium": 50},
            by_source={"synthetic": 100},
        )
        d = card.to_dict()
        assert d["total_examples"] == 100
        assert d["train_count"] == 80
        assert d["val_count"] == 10
        assert d["test_count"] == 10

    def test_to_markdown(self):
        card = DatasetCard(total_examples=50, by_task_type={"qa": 25, "fix": 25})
        md = card.to_markdown()
        assert "Dataset Card" in md
        assert "50" in md
        assert "qa" in md


class TestDatasetV01Generator:
    def test_generator_creates_examples(self):
        gen = DatasetV01Generator()
        gen._generate_repo_qa()
        assert len(gen.examples) >= 8

    def test_generate_all_task_types(self):
        gen = DatasetV01Generator()
        gen.generate_all()
        task_types = set(ex.task_type for ex in gen.examples)
        expected = {"qa", "locate_bug", "explain_failure", "plan_patch",
                    "apply_patch", "verify_patch", "recover", "refuse"}
        for t in expected:
            assert t in task_types, f"Missing task type: {t}"

    def test_generate_all_has_repo_state(self):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        examples_with_repo = [ex for ex in dataset.examples if ex.repo_state is not None]
        assert len(examples_with_repo) >= len(dataset.examples) - 3

    def test_difficulties_distributed(self):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        difficulties = set(ex.difficulty for ex in dataset.examples)
        assert "easy" in difficulties
        assert "medium" in difficulties

    def test_each_example_has_id(self):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        for ex in dataset.examples:
            assert ex.example_id.startswith("v01-")

    def test_qa_examples(self):
        gen = DatasetV01Generator()
        gen._generate_repo_qa()
        for ex in gen.examples:
            assert ex.task_type == "qa"
            assert ex.is_correct is True

    def test_refuse_examples(self):
        gen = DatasetV01Generator()
        gen._generate_refuse()
        for ex in gen.examples:
            assert ex.task_type == "refuse"
            assert "cannot" in ex.final_answer.lower() or "Cannot" in ex.final_answer

    def test_apply_patch_examples_have_patches(self):
        gen = DatasetV01Generator()
        gen._generate_apply_patch()
        for ex in gen.examples:
            assert len(ex.patches) >= 1

    def test_plan_patch_examples_have_plans(self):
        gen = DatasetV01Generator()
        gen._generate_plan_patch()
        for ex in gen.examples:
            assert ex.patch_plan is not None

    def test_verify_patch_examples_have_verification(self):
        gen = DatasetV01Generator()
        gen._generate_verify_patch()
        for ex in gen.examples:
            assert ex.verification is not None
            assert ex.verification.passed is True

    def test_recover_examples_have_failure_and_verification(self):
        gen = DatasetV01Generator()
        gen._generate_recover()
        for ex in gen.examples:
            assert len(ex.failure_recoveries) >= 1
            assert ex.verification is not None


class TestDatasetExporter:
    def test_build_card(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        card = DatasetExporter._build_card(dataset)
        assert card.total_examples > 0
        assert card.train_count > 0
        assert card.val_count >= 0
        assert card.test_count >= 0

    def test_export_creates_files(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        paths = DatasetExporter.export_all(dataset, str(tmp_path / "v01"), sanitize=False)
        assert Path(paths["card"]).exists()
        assert Path(paths["full_dataset"]).exists()
        assert Path(paths["train"]).exists()
        assert Path(paths["validation"]).exists()
        assert Path(paths["test"]).exists()

    def test_exported_jsonl_has_examples(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        DatasetExporter.export_all(dataset, str(tmp_path / "v01"), sanitize=False)
        train_dir = tmp_path / "v01" / "train"
        jsonl_files = list(train_dir.glob("*.jsonl"))
        assert len(jsonl_files) >= 1
        for f in jsonl_files:
            content = f.read_text().strip()
            if content:
                assert len(content.split("\n")) >= 1

    def test_exported_card_is_valid_json(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        DatasetExporter.export_all(dataset, str(tmp_path / "v01"), sanitize=False)
        card = json.loads((tmp_path / "v01" / "dataset_card.json").read_text())
        assert card["name"] == "Lyme Model Dataset v0.1"
        assert card["total_examples"] > 0
        assert "by_task_type" in card

    def test_exported_card_markdown(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        DatasetExporter.export_all(dataset, str(tmp_path / "v01"), sanitize=False)
        card_md = (tmp_path / "v01" / "dataset_card.md").read_text()
        assert "Dataset Card" in card_md

    def test_export_sanitized(self, tmp_path):
        gen = DatasetV01Generator()
        dataset = gen.generate_all()
        DatasetExporter.export_all(dataset, str(tmp_path / "sanitized"), sanitize=True)
        assert (tmp_path / "sanitized" / "train" / "examples.jsonl").exists()


class TestGenerateDataset:
    def test_generate_dataset_v01(self, tmp_path):
        output = str(tmp_path / "v01")
        paths = generate_dataset_v01(output_dir=output, sanitize=False)
        assert Path(paths["card"]).exists()
        assert Path(paths["full_dataset"]).exists()
        assert Path(paths["train"]).exists()
        card = json.loads(Path(paths["card"]).read_text())
        assert card["total_examples"] > 0
        assert "known_limitations" in card

    def test_generate_dataset_v01_sanitized(self, tmp_path):
        output = str(tmp_path / "v01-sanitized")
        paths = generate_dataset_v01(output_dir=output, sanitize=True)
        assert Path(paths["card"]).exists()
