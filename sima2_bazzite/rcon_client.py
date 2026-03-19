from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.util import find_spec

if find_spec("mcrcon") is not None:
    MCRcon = import_module("mcrcon").MCRcon
else:
    MCRcon = None


@dataclass(slots=True)
class CommandResult:
    ok: bool
    command: str
    output: str
    error: str = ""


class RconCommandError(RuntimeError):
    def __init__(self, command: str, message: str):
        super().__init__(message)
        self.command = command
        self.message = message


class RconClient:
    def __init__(self, host: str, password: str, port: int = 25575, enabled: bool = True):
        self.host = host
        self.password = password
        self.port = port
        self.enabled = enabled

    def run(self, command: str) -> str:
        if not self.enabled:
            return f"[DRY-RUN] {command}"
        if MCRcon is None:
            raise RconCommandError(
                command,
                "mcrcon is not installed. Install project dependencies or use --offline to skip live server execution.",
            )
        try:
            with MCRcon(self.host, self.password, port=self.port) as mcr:
                return mcr.command(command)
        except Exception as exc:
            raise RconCommandError(command, self._format_error(exc)) from exc

    def run_safe(self, command: str) -> CommandResult:
        try:
            output = self.run(command)
            return CommandResult(ok=True, command=command, output=output)
        except RconCommandError as exc:
            return CommandResult(ok=False, command=command, output="", error=exc.message)

    def _format_error(self, exc: Exception) -> str:
        detail = str(exc).strip() or exc.__class__.__name__
        return (
            f"RCON command failed for host={self.host}:{self.port}. "
            f"Reason: {detail}. "
            "Check server reachability, enable-rcon, rcon.port, and rcon.password. "
            "You can also use --offline to skip live server execution."
        )
