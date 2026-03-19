from sima2_bazzite.rcon_client import RconClient


def test_run_safe_returns_error_details_on_rcon_failure(monkeypatch) -> None:
    class BrokenMCRcon:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            raise RuntimeError("unpack requires a buffer of 8 bytes")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("sima2_bazzite.rcon_client.MCRcon", BrokenMCRcon)
    client = RconClient("127.0.0.1", "bad", 25575)
    result = client.run_safe("say hello")
    assert not result.ok
    assert "buffer of 8 bytes" in result.error
    assert "--offline" in result.error


def test_run_returns_dry_run_output_when_offline() -> None:
    client = RconClient("127.0.0.1", "", 25575, enabled=False)
    assert client.run("say hello") == "[DRY-RUN] say hello"
