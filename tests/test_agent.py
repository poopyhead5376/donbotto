from pathlib import Path

from sima2_bazzite.agent import AgentConfig, Sima2BazziteAgent


class StubRcon:
    def __init__(self, ok: bool, message: str):
        self.ok = ok
        self.message = message

    def run_safe(self, command: str):
        class Result:
            def __init__(self, ok: bool, output: str, error: str):
                self.ok = ok
                self.output = output
                self.error = error
        if self.ok:
            return Result(True, self.message + command, "")
        return Result(False, "", self.message)


def test_execute_learning_cycle_does_not_crash_on_rcon_failure(tmp_path: Path) -> None:
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    db_path = tmp_path / "knowledge.db"
    agent = Sima2BazziteAgent(
        AgentConfig(
            mods_dir=mods_dir,
            knowledge_db=db_path,
            rcon_host="127.0.0.1",
            rcon_port=25575,
            rcon_password="",
            offline=True,
        )
    )
    agent.learn_modpack = lambda: {"machines": 0.9}
    agent.rcon = StubRcon(False, "boom")
    outputs = agent.execute_learning_cycle()
    assert outputs[0].startswith("[RCON ERROR]")
    assert agent.knowledge.success_rate("machines") == 0.0
    agent.close()
