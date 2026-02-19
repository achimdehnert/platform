"""Tests for Onboarding Coach (Agent A5)."""
from __future__ import annotations

from agents.onboarding_coach import (
    MODULE_MAP,
    MODULES,
    OnboardingProgress,
    list_modules_markdown,
)


class TestModules:
    def test_should_have_five_modules(self):
        assert len(MODULES) == 5

    def test_should_have_sequential_ids(self):
        ids = [m.id for m in MODULES]
        assert ids == ["M1", "M2", "M3", "M4", "M5"]

    def test_should_have_module_map(self):
        assert "M1" in MODULE_MAP
        assert "M5" in MODULE_MAP
        assert MODULE_MAP["M1"].title == "Platform-\u00dcberblick"

    def test_should_have_exercises(self):
        for m in MODULES:
            assert len(m.exercises) >= 1, (
                f"{m.id} has no exercises"
            )

    def test_should_have_quiz_questions(self):
        for m in MODULES:
            assert len(m.quiz) >= 1, (
                f"{m.id} has no quiz questions"
            )


class TestModuleRendering:
    def test_should_render_markdown(self):
        m = MODULE_MAP["M1"]
        md = m.to_markdown()
        assert "M1: Platform-\u00dcberblick" in md
        assert "\u00dcbungen" in md

    def test_should_render_dict(self):
        m = MODULE_MAP["M1"]
        d = m.to_dict()
        assert d["id"] == "M1"
        assert d["duration"] == "30min"
        assert d["exercises"] >= 1
        assert d["quiz_questions"] >= 1


class TestOnboardingProgress:
    def test_should_start_at_zero(self):
        progress = OnboardingProgress()
        assert progress.completion_pct == 0.0
        assert progress.completed_modules == []

    def test_should_track_completion(self):
        progress = OnboardingProgress(
            completed_modules=["M1", "M2"],
            quiz_scores={"M1": 100.0, "M2": 50.0},
        )
        assert progress.completion_pct == 40.0

    def test_should_render_markdown(self):
        progress = OnboardingProgress(
            completed_modules=["M1"],
            quiz_scores={"M1": 100.0},
        )
        md = progress.to_markdown()
        assert "Onboarding Fortschritt" in md
        assert "1/5" in md

    def test_should_render_dict(self):
        progress = OnboardingProgress(
            completed_modules=["M1", "M2", "M3"],
        )
        d = progress.to_dict()
        assert d["total_modules"] == 5
        assert d["completion_pct"] == 60.0

    def test_should_show_full_completion(self):
        progress = OnboardingProgress(
            completed_modules=[
                "M1", "M2", "M3", "M4", "M5",
            ],
        )
        assert progress.completion_pct == 100.0


class TestListModules:
    def test_should_list_all_modules(self):
        md = list_modules_markdown()
        assert "Onboarding Curriculum" in md
        assert "M1" in md
        assert "M5" in md
        assert "3 Stunden" in md


class TestQuizQuestions:
    def test_should_have_valid_correct_index(self):
        for m in MODULES:
            for q in m.quiz:
                assert 0 <= q.correct < len(q.options), (
                    f"{m.id}: correct index {q.correct} "
                    f"out of range for {len(q.options)} "
                    f"options"
                )

    def test_should_have_explanations(self):
        for m in MODULES:
            for q in m.quiz:
                assert q.explanation, (
                    f"{m.id}: quiz missing explanation"
                )
