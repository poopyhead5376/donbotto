from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sima2_bazzite.builder import build_structure, load_blueprint
from sima2_bazzite.knowledge import KnowledgeStore, SkillAttempt
from sima2_bazzite.llm import OllamaClient, OllamaConfig
from sima2_bazzite.mod_scanner import scan_mods, summarize_features
from sima2_bazzite.planner import plan_next_actions
from sima2_bazzite.rcon_client import RconClient
from sima2_bazzite.research import VideoResult, make_feature_queries, youtube_search


@dataclass(slots=True)
class AgentConfig:
    mods_dir: Path
    knowledge_db: Path
    rcon_host: str
    rcon_port: int
    rcon_password: str
    use_ollama: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"


class Sima2BazziteAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.knowledge = KnowledgeStore(config.knowledge_db)
        self.rcon = RconClient(config.rcon_host, config.rcon_password, config.rcon_port)
        self.ollama = None
        if config.use_ollama:
            self.ollama = OllamaClient(OllamaConfig(base_url=config.ollama_url, model=config.ollama_model))

    def learn_modpack(self) -> dict[str, float]:
        mods = scan_mods(self.config.mods_dir)
        return summarize_features(mods)

    def research_tutorials(self, feature_limit: int = 3, per_query_limit: int = 3) -> dict[str, list[VideoResult]]:
        features = list(self.learn_modpack().keys())[:feature_limit]
        queries = make_feature_queries(features)
        findings: dict[str, list[VideoResult]] = {}
        for query in queries:
            findings[query] = youtube_search(query, limit=per_query_limit)
        return findings

    def _llm_action(self, feature: str) -> str:
        if not self.ollama or not self.ollama.available():
            return "observe_mod_usage"
        return self.ollama.generate_action(
            feature,
            context=(
                "Suggest practical action for mod learning, crafting progression, or tutorial-following; "
                "compatible with modded survival gameplay"
            ),
        )

    def execute_learning_cycle(self) -> list[str]:
        outputs: list[str] = []
        features = self.learn_modpack()
        actions = plan_next_actions(features, self.knowledge, llm_action_provider=self._llm_action if self.ollama else None)
        for action in actions:
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
