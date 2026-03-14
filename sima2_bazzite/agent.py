from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sima2_bazzite.builder import build_structure, load_blueprint
from sima2_bazzite.knowledge import KnowledgeStore, SkillAttempt
from sima2_bazzite.mod_scanner import scan_mods, summarize_features
from sima2_bazzite.planner import plan_next_actions
from sima2_bazzite.rcon_client import RconClient


@dataclass(slots=True)
class AgentConfig:
    mods_dir: Path
    knowledge_db: Path
    rcon_host: str
    rcon_port: int
    rcon_password: str


class Sima2BazziteAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.knowledge = KnowledgeStore(config.knowledge_db)
        self.rcon = RconClient(config.rcon_host, config.rcon_password, config.rcon_port)

    def learn_modpack(self) -> dict[str, float]:
        mods = scan_mods(self.config.mods_dir)
        return summarize_features(mods)

    def execute_learning_cycle(self) -> list[str]:
        outputs: list[str] = []
        features = self.learn_modpack()
        actions = plan_next_actions(features, self.knowledge)
        for action in actions:
            # Placeholder strategy: emit command through say; replace with macro integrations.
            server_cmd = f"say [SIMA2] feature={action.feature} action={action.command}"
            result = self.rcon.run(server_cmd)
            outputs.append(result)
            self.knowledge.record_attempt(
                SkillAttempt(
                    feature=action.feature,
                    action=action.command,
                    success=True,
                    notes=action.rationale,
                )
            )
        return outputs

    def build(self, blueprint_path: Path, origin: tuple[int, int, int]) -> list[str]:
        blueprint = load_blueprint(blueprint_path)
        return build_structure(self.rcon, blueprint, origin)

    def close(self) -> None:
        self.knowledge.close()
