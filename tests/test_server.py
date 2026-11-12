from __future__ import annotations

import httpx
import pytest

from xeno_canto_mcp.client import XenoCantoClient
from xeno_canto_mcp.server import create_server


@pytest.fixture
def mock_client() -> XenoCantoClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "numRecordings": "1",
                "numSpecies": "1",
                "recordings": [
                    {
                        "id": "100",
                        "gen": "Turdus",
                        "sp": "migratorius",
                        "en": "American Robin",
                        "type": "song",
                        "q": "A",
                        "loc": "Central Park",
                        "file": "https://xeno-canto.org/100/download",
                        "sono": {"full": "https://xeno-canto.org/sono.png"},
                    }
                ],
            },
        )

    return XenoCantoClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def failing_client() -> XenoCantoClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Server Error")

    return XenoCantoClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_server_tools(mock_client: XenoCantoClient) -> None:
    server = create_server(mock_client)

    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert "search_recordings" in tool_names
    assert "search_recordings_nearby" in tool_names
    assert "get_recording_details" in tool_names
    assert "get_sonogram_urls" in tool_names
    assert "compare_species_vocalizations" in tool_names

    res = await server.call_tool("search_recordings", {"species": "Turdus migratorius"})
    assert "American Robin" in res.content[0].text

    res = await server.call_tool(
        "search_recordings_nearby", {"lat": 40.7, "lon": -74.0, "radius_km": 25}
    )
    assert "American Robin" in res.content[0].text

    res = await server.call_tool("get_recording_details", {"recording_id": "100"})
    assert "American Robin" in res.content[0].text

    res = await server.call_tool("get_sonogram_urls", {"recording_id": "100"})
    assert "sono.png" in res.content[0].text

    res = await server.call_tool(
        "compare_species_vocalizations", {"species_a": "Robin", "species_b": "Thrush"}
    )
    assert "Comparison" in res.content[0].text


@pytest.mark.asyncio
async def test_server_tool_errors(failing_client: XenoCantoClient) -> None:
    server = create_server(failing_client)

    res = await server.call_tool("search_recordings", {"species": "Bad"})
    assert "failed" in res.content[0].text

    res = await server.call_tool("search_recordings_nearby", {"lat": 0, "lon": 0})
    assert "failed" in res.content[0].text

    res = await server.call_tool("get_recording_details", {"recording_id": "999"})
    assert "failed" in res.content[0].text

    res = await server.call_tool("get_sonogram_urls", {"recording_id": "999"})
    assert "failed" in res.content[0].text

    res = await server.call_tool(
        "compare_species_vocalizations", {"species_a": "A", "species_b": "B"}
    )
    assert "failed" in res.content[0].text
