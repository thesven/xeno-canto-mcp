from __future__ import annotations

import httpx
import pytest

from xeno_canto_mcp.client import XenoCantoClient, XenoCantoError


def test_client_init() -> None:
    client = XenoCantoClient(base_url="https://xeno-canto.org/api/2/")
    assert client.base_url == "https://xeno-canto.org/api/2"
    assert client.timeout == 30.0


def test_search_recordings() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/2/recordings"
        return httpx.Response(
            200,
            json={
                "numRecordings": "1",
                "numSpecies": "1",
                "recordings": [
                    {
                        "id": "123456",
                        "gen": "Turdus",
                        "sp": "migratorius",
                        "en": "American Robin",
                        "rec": "Jane Naturalist",
                        "cnt": "Canada",
                        "loc": "Algonquin Park",
                        "lat": "45.55",
                        "lng": "-78.35",
                        "type": "song",
                        "url": "//xeno-canto.org/123456",
                        "file": "//xeno-canto.org/123456/download",
                        "sono": {"full": "//xeno-canto.org/sounds/fftf.png"},
                        "q": "A",
                        "length": "0:30",
                        "date": "2024-05-01",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = XenoCantoClient(transport=transport)
    res = client.search_recordings(
        species="Turdus migratorius", vocalization_type="song", quality_rating="A"
    )
    assert res["total_recordings"] == 1
    assert len(res["recordings"]) == 1
    rec = res["recordings"][0]
    assert rec["id"] == "123456"
    assert rec["scientific_name"] == "Turdus migratorius"
    assert rec["audio_url"] == "https://xeno-canto.org/123456/download"
    assert rec["sonograms"]["full"] == "https://xeno-canto.org/sounds/fftf.png"
    assert rec["latitude"] == 45.55


def test_search_recordings_nearby() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "box:" in request.url.params["query"]
        return httpx.Response(
            200,
            json={
                "numRecordings": "1",
                "numSpecies": "1",
                "recordings": [
                    {
                        "id": "222",
                        "gen": "Poecile",
                        "sp": "atricapillus",
                        "en": "Black-capped Chickadee",
                        "type": "call",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = XenoCantoClient(transport=transport)
    res = client.search_recordings_nearby(45.0, -75.0, radius_km=25, species="Chickadee")
    assert res["total_recordings"] == 1
    assert res["recordings"][0]["scientific_name"] == "Poecile atricapillus"


def test_get_recording_details() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["query"] == "nr:123"
        return httpx.Response(
            200,
            json={
                "numRecordings": "1",
                "recordings": [
                    {
                        "id": "123",
                        "gen": "Turdus",
                        "sp": "migratorius",
                        "en": "American Robin",
                        "type": "song",
                        "file": "https://xeno-canto.org/123/download",
                        "sono": {"small": "https://xeno-canto.org/small.png"},
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = XenoCantoClient(transport=transport)
    rec = client.get_recording_details("123")
    assert rec["id"] == "123"

    sono_data = client.get_sonogram_urls("123")
    assert sono_data["recording_id"] == "123"
    assert sono_data["sonograms"]["small"] == "https://xeno-canto.org/small.png"


def test_get_recording_details_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"numRecordings": "0", "recordings": []})

    transport = httpx.MockTransport(handler)
    client = XenoCantoClient(transport=transport)
    with pytest.raises(XenoCantoError, match="not found"):
        client.get_recording_details("9999999")


def test_compare_species_vocalizations() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        q = request.url.params.get("query", "")
        return httpx.Response(
            200,
            json={
                "numRecordings": "1",
                "recordings": [
                    {
                        "id": "1",
                        "gen": "Species",
                        "sp": "one" if "one" in q else "two",
                        "type": "song",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    client = XenoCantoClient(transport=transport)
    comp = client.compare_species_vocalizations("Species one", "Species two")
    assert comp["species_a"]["name"] == "Species one"
    assert comp["species_b"]["name"] == "Species two"


def test_error_handling() -> None:
    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Server Error")

    client = XenoCantoClient(transport=httpx.MockTransport(handler_500))
    with pytest.raises(XenoCantoError, match="API request failed"):
        client.search_recordings("test")

    def handler_bad_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"invalid{")

    client2 = XenoCantoClient(transport=httpx.MockTransport(handler_bad_json))
    with pytest.raises(XenoCantoError, match="Invalid JSON"):
        client2.search_recordings("test")
