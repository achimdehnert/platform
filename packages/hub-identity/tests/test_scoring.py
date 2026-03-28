"""Tests for composite score tree (Design #2)."""

from __future__ import annotations

from hub_identity.core.scoring import ScoreNode, ScoreTree


class TestScoreNode:

    def test_should_compute_leaf_score(self):
        node = ScoreNode(name="Typography", raw_score=30.0)
        assert node.weighted_score == 30.0

    def test_should_cap_at_max(self):
        node = ScoreNode(name="test", raw_score=150.0)
        assert node.weighted_score == 100.0

    def test_should_compute_weighted_children(self):
        root = ScoreNode(
            name="Root",
            children=[
                ScoreNode(name="A", weight=0.6, raw_score=40.0),
                ScoreNode(name="B", weight=0.4, raw_score=20.0),
            ],
        )
        # (40*0.6 + 20*0.4) / (0.6+0.4) = 32.0
        assert abs(root.weighted_score - 32.0) < 0.1

    def test_should_grade_correctly(self):
        assert ScoreNode(name="a", raw_score=10).grade == "A"
        assert ScoreNode(name="b", raw_score=20).grade == "B"
        assert ScoreNode(name="c", raw_score=30).grade == "C"
        assert ScoreNode(name="d", raw_score=40).grade == "D"
        assert ScoreNode(name="f", raw_score=60).grade == "F"

    def test_should_pass_for_grade_a_or_b(self):
        assert ScoreNode(name="a", raw_score=10).passed is True
        assert ScoreNode(name="b", raw_score=20).passed is True
        assert ScoreNode(name="c", raw_score=30).passed is False

    def test_should_find_nested_node(self):
        tree = ScoreTree.create()
        typo = tree.find("Typography")
        assert typo is not None
        assert typo.name == "Typography"

    def test_should_return_none_for_missing(self):
        tree = ScoreTree.create()
        assert tree.find("Nonexistent") is None

    def test_should_explain_tree(self):
        tree = ScoreTree.create()
        typo = tree.find("Typography")
        typo.raw_score = 45.0
        typo.details = ["TYP-001: Inter font detected"]
        explanation = tree.explain()
        assert "Typography" in explanation
        assert "TYP-001" in explanation

    def test_should_serialize_to_dict(self):
        tree = ScoreTree.create()
        d = tree.to_dict()
        assert d["name"] == "HubIdentityScore"
        assert "children" in d
        assert len(d["children"]) == 2


class TestScoreTree:

    def test_should_create_standard_tree(self):
        tree = ScoreTree.create()
        assert tree.name == "HubIdentityScore"
        assert len(tree.children) == 2
        visual = tree.children[0]
        assert visual.name == "VisualScore"
        assert visual.weight == 0.4
        assert len(visual.children) == 3
        linguistic = tree.children[1]
        assert linguistic.name == "LinguisticScore"
        assert linguistic.weight == 0.6
        assert len(linguistic.children) == 3
