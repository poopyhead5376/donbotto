from sima2_bazzite.llm import OllamaClient, OllamaConfig


def test_ollama_generate_action_normalizes(monkeypatch) -> None:
    monkeypatch.setattr(
        "sima2_bazzite.llm._post_json",
        lambda *args, **kwargs: {"response": "Craft Generator!!!"},
    )
    client = OllamaClient(OllamaConfig())
    action = client.generate_action("machines", "context")
    assert action == "craft_generator"


def test_ollama_available(monkeypatch) -> None:
    monkeypatch.setattr(
        "sima2_bazzite.llm._get_json",
        lambda *args, **kwargs: {"models": [{"name": "llama3.1"}]},
    )
    client = OllamaClient(OllamaConfig(model="llama3.1"))
    assert client.available()
