from sima2_bazzite.research import VideoResult
from sima2_bazzite.tutorial_builder import infer_build_plan, plan_build_from_tutorial


def test_infer_build_plan_matches_tower_keyword() -> None:
    plan = infer_build_plan(
        "watch tower",
        [VideoResult(title="Minecraft Watch Tower Tutorial", url="https://youtube.test/watch?v=1")],
    )
    assert plan.source_video is not None
    assert "tower" in plan.rationale.lower()
    assert len(plan.placements) > 0
    assert any(block.block == "stone_bricks" for block in plan.placements)


def test_plan_build_from_tutorial_uses_search_results(monkeypatch) -> None:
    monkeypatch.setattr(
        "sima2_bazzite.tutorial_builder.youtube_search",
        lambda *args, **kwargs: [VideoResult(title="Starter House Tutorial", url="https://youtube.test/watch?v=2")],
    )
    plan = plan_build_from_tutorial("starter house")
    assert plan.source_video is not None
    assert "house" in plan.rationale.lower()
    assert len(plan.placements) > 10
