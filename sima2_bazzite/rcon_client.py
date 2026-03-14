from __future__ import annotations

from mcrcon import MCRcon


class RconClient:
    def __init__(self, host: str, password: str, port: int = 25575):
        self.host = host
        self.password = password
        self.port = port

    def run(self, command: str) -> str:
        with MCRcon(self.host, self.password, port=self.port) as mcr:
            return mcr.command(command)
