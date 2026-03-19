from sima2_bazzite.network import auto_detect_rcon_host


class FakeSocket:
    def __init__(self, ip: str = "192.168.1.23", fail: bool = False):
        self.ip = ip
        self.fail = fail
        self.closed = False

    def connect(self, target):
        if self.fail:
            raise OSError("no network")

    def getsockname(self):
        return (self.ip, 12345)

    def close(self):
        self.closed = True


def test_auto_detect_rcon_host_uses_socket_ip(monkeypatch) -> None:
    monkeypatch.setattr("sima2_bazzite.network.socket.socket", lambda *args, **kwargs: FakeSocket())
    assert auto_detect_rcon_host() == "192.168.1.23"


def test_auto_detect_rcon_host_falls_back_to_localhost(monkeypatch) -> None:
    monkeypatch.setattr("sima2_bazzite.network.socket.socket", lambda *args, **kwargs: FakeSocket(fail=True))
    assert auto_detect_rcon_host() == "127.0.0.1"
