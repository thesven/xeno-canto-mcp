from __future__ import annotations

import argparse
import sys
from typing import Any

from mcp.server import MCPServer

from . import __version__
from .client import XenoCantoClient, XenoCantoError

DEFAULT_INSTRUCTIONS = """
Xeno-canto MCP Server: Access the world's largest community bioacoustics database of wildlife
audio recordings (birds, bats, grasshoppers, frogs) and sonogram spectrograms.

Key Best Practices:
1. When a user asks what a bird or animal sounds like, call `search_recordings` with `species`
   and optionally filter by `vocalization_type` ('song', 'call') or `quality_rating` ('A').
2. To explore what wildlife sounds have been recorded in a region, use `search_recordings_nearby`
   with `lat`, `lon`, and `radius_km`.
3. To inspect audio visual signatures with multimodal vision capabilities, call `get_sonogram_urls`
   to obtain spectrogram image URLs.
4. Use `compare_species_vocalizations` when distinguishing between similar vocalizing species
   (e.g., confusing warblers, sparrows, or thrushes).
""".strip()


def _format_recordings_summary(recordings: list[dict[str, Any]]) -> str:
    if not recordings:
        return "No recordings found."
    lines = []
    for r in recordings[:10]:
        name = r.get("common_name") or r.get("scientific_name") or "Unknown"
        v_type = r.get("vocalization_type") or "sound"
        q = r.get("quality") or "?"
        loc = r.get("locality") or r.get("country") or "unknown location"
        length = r.get("length") or "--:--"
        lines.append(f"- [XC{r.get('id')}] {name} ({v_type}, Q:{q}, {length}) at {loc}")
    return "\n".join(lines)


def create_server(client: XenoCantoClient | None = None) -> MCPServer:
    """Create and configure the Xeno-canto MCPServer instance."""
    api = client or XenoCantoClient()

    server = MCPServer(
        "xeno-canto",
        version=__version__,
        instructions=DEFAULT_INSTRUCTIONS,
    )

    @server.tool()
    def search_recordings(
        query: str = "",
        species: str | None = None,
        country: str | None = None,
        vocalization_type: str | None = None,
        quality_rating: str | None = None,
        taxonomic_group: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search wildlife audio recordings by species, geography, vocalization, rating, or taxa."""
        try:
            res = api.search_recordings(
                query=query,
                species=species,
                country=country,
                vocalization_type=vocalization_type,
                quality_rating=quality_rating,
                taxonomic_group=taxonomic_group,
                limit=limit,
            )
            res["summary"] = _format_recordings_summary(res["recordings"])
            return res
        except XenoCantoError as exc:
            return {
                "error": str(exc),
                "recordings": [],
                "total_recordings": 0,
                "summary": f"Search failed: {exc}",
            }

    @server.tool()
    def search_recordings_nearby(
        lat: float,
        lon: float,
        radius_km: int = 50,
        species: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search recordings within a geographic bounding box around GPS coordinates."""
        try:
            res = api.search_recordings_nearby(
                lat=lat, lon=lon, radius_km=radius_km, species=species, limit=limit
            )
            res["summary"] = _format_recordings_summary(res["recordings"])
            return res
        except XenoCantoError as exc:
            return {
                "error": str(exc),
                "recordings": [],
                "total_recordings": 0,
                "summary": f"Nearby search failed: {exc}",
            }

    @server.tool()
    def get_recording_details(recording_id: str) -> dict[str, Any]:
        """Retrieve full metadata, audio stream URL, and sonograms for a specific XC recording."""
        try:
            details = api.get_recording_details(recording_id=recording_id)
            common = details.get("common_name")
            sci = details.get("scientific_name")
            v_type = details.get("vocalization_type")
            q = details.get("quality")
            audio = details.get("audio_url")
            summary = f"XC{details.get('id')}: {common} ({sci}) - {v_type} | Q:{q} | Audio: {audio}"
            return {"recording": details, "summary": summary}
        except XenoCantoError as exc:
            return {"error": str(exc), "summary": f"Lookup failed: {exc}"}

    @server.tool()
    def get_sonogram_urls(recording_id: str) -> dict[str, Any]:
        """Retrieve spectrogram URLs for multimodal visual sound inspection."""
        try:
            sono_data = api.get_sonogram_urls(recording_id=recording_id)
            sonos = sono_data.get("sonograms", {})
            full_img = sonos.get("full") or sonos.get("med") or sonos.get("small") or "No sonogram"
            summary = (
                f"Sonogram for XC{recording_id} "
                f"({sono_data.get('species')} - {sono_data.get('vocalization_type')}): {full_img}"
            )
            return {"sonograms": sono_data, "summary": summary}
        except XenoCantoError as exc:
            return {"error": str(exc), "summary": f"Sonogram lookup failed: {exc}"}

    @server.tool()
    def compare_species_vocalizations(
        species_a: str, species_b: str, vocalization_type: str = "song"
    ) -> dict[str, Any]:
        """Compare representative high-quality audio recordings and sonograms for two species."""
        try:
            comp = api.compare_species_vocalizations(
                species_a=species_a, species_b=species_b, vocalization_type=vocalization_type
            )
            summary = (
                f"Comparison for {species_a} vs {species_b} ({vocalization_type}): "
                f"{len(comp['species_a']['recordings'])} recordings for {species_a}, "
                f"{len(comp['species_b']['recordings'])} recordings for {species_b}"
            )
            return {"comparison": comp, "summary": summary}
        except XenoCantoError as exc:
            return {"error": str(exc), "summary": f"Comparison failed: {exc}"}

    @server.tool()
    def get_species_vocalization_profile(species_name: str) -> dict[str, Any]:
        """Aggregate a species' acoustic repertoire across song, call, and alarm vocalizations."""
        try:
            profile = api.get_species_vocalization_profile(species_name=species_name)
            types_str = ", ".join(profile.get("primary_vocalizations", [])) or "None reported"
            summary = (
                f"Vocalization profile for {species_name}: "
                f"{profile.get('total_recordings_sampled')} recordings sampled across {types_str}"
            )
            return {"profile": profile, "summary": summary}
        except XenoCantoError as exc:
            return {"error": str(exc), "summary": f"Profile generation failed: {exc}"}

    return server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="xeno-canto-mcp",
        description="Model Context Protocol (MCP) server for Xeno-canto wildlife audio",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind for SSE transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for SSE transport (default: 8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="sse", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
