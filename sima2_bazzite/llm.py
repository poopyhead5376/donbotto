from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class OllamaConfig:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1"
    timeout_s: float = 20.0


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, timeout: float) -> dict:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class OllamaClient:
    def __init__(self, config: OllamaConfig):
        self.config = config

    def generate_action(self, feature: str, context: str) -> str:
        prompt = (
            "You are a Minecraft modpack automation planner. "
            "Return exactly one short action identifier in snake_case that helps learn or use this feature. "
            f"Feature: {feature}. Context: {context}"
        )
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        body = _post_json(f"{self.config.base_url}/api/generate", payload, self.config.timeout_s)
        text = str(body.get("response", "")).strip().lower()
        normalized = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in text)
        normalized = "_".join(part for part in normalized.split("_") if part)
        return normalized or "observe_mod_usage"

    def available(self) -> bool:
        try:
            data = _get_json(f"{self.config.base_url}/api/tags", 5)
            models = json.dumps(data).lower()
            return self.config.model.lower() in models
        except (URLError, TimeoutError, json.JSONDecodeError):
            return False
