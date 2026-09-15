from types import SimpleNamespace

from starlette.requests import Request

from app.core import rate_limit


def _request(peer: str, forwarded: str) -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", forwarded.encode())],
        "client": (peer, 12345),
    })


def test_forwarded_ip_is_used_only_for_caddy(monkeypatch):
    monkeypatch.setattr(rate_limit, "settings", SimpleNamespace(environment="production"))
    monkeypatch.setattr(rate_limit.socket, "gethostbyname", lambda host: "172.20.0.2")

    assert rate_limit.get_client_ip(_request("172.20.0.2", "198.51.100.4")) == "198.51.100.4"
    assert rate_limit.get_client_ip(_request("172.20.0.3", "198.51.100.4")) == "172.20.0.3"


def test_invalid_forwarded_ip_falls_back_to_peer(monkeypatch):
    monkeypatch.setattr(rate_limit, "settings", SimpleNamespace(environment="production"))
    monkeypatch.setattr(rate_limit.socket, "gethostbyname", lambda host: "172.20.0.2")

    assert rate_limit.get_client_ip(_request("172.20.0.2", "not-an-ip")) == "172.20.0.2"
