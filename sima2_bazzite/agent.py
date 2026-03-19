from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sima2_bazzite.builder import load_blueprint
from sima2_bazzite.knowledge import KnowledgeStore, SkillAttempt
from sima2_bazzite.llm import OllamaClient, OllamaConfig
from sima2_bazzite.mod_scanner import scan_mods, summarize_features
from sima2_bazzite.network import auto_detect_rcon_host
from sima2_bazzite.planner import plan_next_actions
from sima2_bazzite.rcon_client import RconClient
from sima2_bazzite.research import VideoResult, make_feature_queries, youtube_search


@dataclass(slots=True)
class AgentConfig:
    mods_dir: Path
    knowledge_db: Path
    rcon_host: str = "auto"
    rcon_port: int = 25575
    rcon_password: str = ""
    offline: bool = False
    use_ollama: bool = False
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"


class Sima2BazziteAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        resolved_host = auto_detect_rcon_host() if config.rcon_host == "auto" else config.rcon_host
        self.knowledge = KnowledgeStore(config.knowledge_db)
        self.rcon = RconClient(
            resolved_host,
            config.rcon_password,
            config.rcon_port,
            enabled=not config.offline,
        )
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
            result = self.rcon.run_safe(server_cmd)
            if result.ok:
                outputs.append(result.output)
                success = True
                notes = action.rationale
            else:
                outputs.append(f"[RCON ERROR] {result.error}")
                success = False
                notes = f"{action.rationale} | {result.error}"
            self.knowledge.record_attempt(
                SkillAttempt(
                    feature=action.feature,
                    action=action.command,
                    success=success,
                    notes=notes,
                )
            )
        return outputs

    def build(self, blueprint_path: Path, origin: tuple[int, int, int]) -> list[str]:
        blueprint = load_blueprint(blueprint_path)
        outputs: list[str] = []
        for step in blueprint:
            command = f"setblock {origin[0] + step.x} {origin[1] + step.y} {origin[2] + step.z} {step.block}"
            result = self.rcon.run_safe(command)
            outputs.append(result.output if result.ok else f"[RCON ERROR] {result.error}")
        return outputs

    def close(self) -> None:
        self.knowledge.close()
