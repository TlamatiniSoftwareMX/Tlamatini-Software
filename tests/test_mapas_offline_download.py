import requests

from core.mapas_offline import OfflineMapsService


class _FakeStreamResponse:
    def __init__(self, status_code=206, chunks=(b"x",)):
        self.status_code = status_code
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size=1):
        yield from self._chunks


def test_remote_download_ready_falls_back_to_range_get_when_head_fails(monkeypatch):
    calls = {"get": 0}

    def fake_head(*_args, **_kwargs):
        raise requests.Timeout("head timeout")

    def fake_get(_url, **kwargs):
        calls["get"] += 1
        assert kwargs["stream"] is True
        assert kwargs["headers"]["Range"] == "bytes=0-0"
        return _FakeStreamResponse(status_code=206)

    monkeypatch.setattr("core.mapas_offline.requests.head", fake_head)
    monkeypatch.setattr("core.mapas_offline.requests.get", fake_get)

    assert OfflineMapsService()._remote_download_ready("https://example.test/map.zip") is True
    assert calls["get"] == 1


def test_remote_download_ready_returns_false_for_not_found_without_get(monkeypatch):
    calls = {"get": 0}

    class FakeHead:
        status_code = 404

    def fake_get(*_args, **_kwargs):
        calls["get"] += 1
        return _FakeStreamResponse(status_code=200)

    monkeypatch.setattr("core.mapas_offline.requests.head", lambda *_args, **_kwargs: FakeHead())
    monkeypatch.setattr("core.mapas_offline.requests.get", fake_get)

    assert OfflineMapsService()._remote_download_ready("https://example.test/map.zip") is False
    assert calls["get"] == 0
