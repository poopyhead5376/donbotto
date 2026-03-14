from __future__ import annotations

from dataclasses import dataclass

from sima2_bazzite.knowledge import KnowledgeStore


@dataclass(slots=True)
class PlanAction:
    feature: str
    command: str
    rationale: str


DEFAULT_ACTIONS: dict[str, list[str]] = {
    "machines": ["collect_iron", "craft_generator", "place_power_network"],
    "magic": ["collect_crystals", "build_altar", "perform_basic_ritual"],
    "storage": ["craft_storage_crates", "organize_items", "expand_warehouse"],
    "farming": ["till_field", "plant_crops", "automate_harvest"],
    "building": ["gather_blocks", "construct_blueprint", "decorate_structure"],
    "combat": ["craft_armor", "forge_weapon", "hunt_mobs"],
    "exploration": ["craft_supplies", "map_surroundings", "enter_new_dimension"],
}


def plan_next_actions(features: dict[str, float], knowledge: KnowledgeStore, limit: int = 5) -> list[PlanAction]:
    candidates: list[PlanAction] = []
    for feature, confidence in sorted(features.items(), key=lambda kv: kv[1], reverse=True):
        preferred = knowledge.best_action(feature)
        if preferred:
            candidates.append(
                PlanAction(
                    feature=feature,
                    command=preferred,
                    rationale=f"Reusing learned best action (confidence={confidence:.2f}).",
                )
            )
            continue

        for cmd in DEFAULT_ACTIONS.get(feature, ["observe_mod_usage"]):
            candidates.append(
                PlanAction(
                    feature=feature,
                    command=cmd,
                    rationale=f"New action for detected feature (confidence={confidence:.2f}).",
                )
            )

    return candidates[:limit]
