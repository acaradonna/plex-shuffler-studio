import io
from types import SimpleNamespace

import pytest

import plex_shuffler.plex_client as plex_client
from plex_shuffler.plex_client import PlexClient


def _xml_container(total_size: int, entries: list[str]) -> bytes:
    parts = [
        f'<MediaContainer totalSize="{total_size}" size="{len(entries)}">',
        *entries,
        "</MediaContainer>",
    ]
    return "".join(parts).encode("utf-8")


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_get_movies_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    page1 = _xml_container(
        3,
        [
            '<Video type="movie" ratingKey="m1" title="Movie 1" />',
            '<Video type="movie" ratingKey="m2" title="Movie 2" />',
        ],
    )
    page2 = _xml_container(
        3,
        [
            '<Video type="movie" ratingKey="m3" title="Movie 3" />',
        ],
    )

    def fake_urlopen(request, timeout=0):
        calls.append(request.full_url)
        if "X-Plex-Container-Start=0" in request.full_url:
            return _FakeResponse(page1)
        if "X-Plex-Container-Start=2" in request.full_url:
            return _FakeResponse(page2)
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    monkeypatch.setattr(plex_client, "urlopen", fake_urlopen)

    client = PlexClient(base_url="http://example", token="t")
    movies = client.get_movies("1")

    assert [m.rating_key for m in movies] == ["m1", "m2", "m3"]
    assert any("X-Plex-Container-Start=0" in url for url in calls)
    assert any("X-Plex-Container-Start=2" in url for url in calls)


def test_client_identifier_header(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_headers = {}

    payload = _xml_container(0, [])

    def fake_urlopen(request, timeout=0):
        nonlocal seen_headers
        seen_headers = dict(request.header_items())
        return _FakeResponse(payload)

    monkeypatch.setattr(plex_client, "urlopen", fake_urlopen)

    client = PlexClient(
        base_url="http://example",
        token="t",
        client_identifier="my-client-id",
    )
    client.get_sections()

    normalized = {str(k).lower(): v for k, v in seen_headers.items()}
    assert normalized.get("x-plex-client-identifier") == "my-client-id"
