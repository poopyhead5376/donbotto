from pathlib import Path

from sima2_bazzite.knowledge import KnowledgeStore, SkillAttempt


def test_knowledge_tracks_best_action(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.db")
    store.record_attempt(SkillAttempt("machines", "craft_generator", True, "ok"))
    store.record_attempt(SkillAttempt("machines", "craft_generator", True, "ok"))
    store.record_attempt(SkillAttempt("machines", "gather_cobble", False, "bad"))

    assert store.success_rate("machines") > 0.6
    assert store.best_action("machines") == "craft_generator"
    store.close()
