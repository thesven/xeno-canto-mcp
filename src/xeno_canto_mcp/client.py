from __future__ import annotations

import math
import tempfile
from pathlib import Path
from typing import Any

import httpx


class XenoCantoError(RuntimeError):
    """Base exception for Xeno-canto API client errors."""


class XenoCantoClient:
    """Client for querying the Xeno-canto API v2."""

    def __init__(
        self,
        base_url: str = "https://xeno-canto.org/api/2",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def search_recordings(
        self,
        query: str = "",
        species: str | None = None,
        country: str | None = None,
        vocalization_type: str | None = None,
        quality_rating: str | None = None,
        taxonomic_group: str | None = None,
        life_stage: str | None = None,
        sex: str | None = None,
        sound_method: str | None = None,
        recordist: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search bioacoustic recordings with taxonomic, geographical, and acoustic filters."""
        query_parts = []
        if query:
            query_parts.append(query.strip())
        if species:
            query_parts.append(f'"{species.strip()}"')
        if country:
            query_parts.append(f'cnt:"{country.strip()}"')
        if vocalization_type:
            query_parts.append(f'type:"{vocalization_type.strip()}"')
        if quality_rating:
            query_parts.append(f"q:{quality_rating.strip().upper()}")
        if taxonomic_group:
            query_parts.append(f"grp:{taxonomic_group.strip().lower()}")
        if life_stage:
            query_parts.append(f'stage:"{life_stage.strip().lower()}"')
        if sex:
            query_parts.append(f'sex:"{sex.strip().lower()}"')
        if sound_method:
            query_parts.append(f'method:"{sound_method.strip().lower()}"')
        if recordist:
            query_parts.append(f'rec:"{recordist.strip()}"')

        full_query = " ".join(query_parts).strip() or "q:A"
        data = self._request("/recordings", {"query": full_query})

        raw_recordings = data.get("recordings", []) if isinstance(data, dict) else []
        normalized = [self._normalize_recording(r) for r in raw_recordings[: min(limit, 100)]]

        return {
            "recordings": normalized,
            "total_recordings": int(data.get("numRecordings", len(normalized))),
            "total_species": int(data.get("numSpecies", 0)),
            "query_used": full_query,
        }

    def search_recordings_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: int = 50,
        species: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Search recordings located within a geographical bounding box around a coordinate."""
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
        min_lat = round(lat - lat_delta, 4)
        max_lat = round(lat + lat_delta, 4)
        min_lon = round(lon - lon_delta, 4)
        max_lon = round(lon + lon_delta, 4)

        box_tag = f"box:{min_lat},{min_lon},{max_lat},{max_lon}"
        query = f"{box_tag}"
        if species:
            query = f'"{species.strip()}" {box_tag}'

        return self.search_recordings(query=query, limit=limit)

    def get_recording_details(self, recording_id: str) -> dict[str, Any]:
        """Fetch detailed metadata for a single recording by its XC identifier."""
        data = self.search_recordings(query=f"nr:{recording_id}", limit=1)
        recordings = data.get("recordings", [])
        if not recordings:
            raise XenoCantoError(f"Recording XC{recording_id} not found.")
        return recordings[0]

    def get_sonogram_urls(self, recording_id: str) -> dict[str, Any]:
        """Retrieve full, medium, and small spectrogram image URLs for multimodal sound analysis."""
        details = self.get_recording_details(recording_id)
        sonograms = details.get("sonograms", {})
        return {
            "recording_id": recording_id,
            "species": details.get("scientific_name"),
            "common_name": details.get("common_name"),
            "vocalization_type": details.get("vocalization_type"),
            "sonograms": sonograms,
            "audio_url": details.get("audio_url"),
        }

    def compare_species_vocalizations(
        self, species_a: str, species_b: str, vocalization_type: str = "song"
    ) -> dict[str, Any]:
        """Retrieve high-quality comparison recordings for two species with sonograms."""
        res_a = self.search_recordings(
            species=species_a, vocalization_type=vocalization_type, quality_rating="A", limit=3
        )
        res_b = self.search_recordings(
            species=species_b, vocalization_type=vocalization_type, quality_rating="A", limit=3
        )
        return {
            "species_a": {
                "name": species_a,
                "recordings": res_a.get("recordings", []),
            },
            "species_b": {
                "name": species_b,
                "recordings": res_b.get("recordings", []),
            },
            "vocalization_type": vocalization_type,
        }

    def get_species_vocalization_profile(self, species_name: str) -> dict[str, Any]:
        """Aggregate a species' acoustic repertoire across song, call, and alarm vocalizations."""
        res = self.search_recordings(species=species_name, limit=50)
        recordings = res.get("recordings", [])

        vocal_counts: dict[str, int] = {}
        featured: list[dict[str, Any]] = []
        seen_types = set()

        for r in recordings:
            v_type = (r.get("vocalization_type") or "sound").lower()
            vocal_counts[v_type] = vocal_counts.get(v_type, 0) + 1
            if v_type not in seen_types and len(featured) < 5:
                seen_types.add(v_type)
                featured.append(r)

        return {
            "species": species_name,
            "total_recordings_sampled": len(recordings),
            "vocalization_types": vocal_counts,
            "featured_recordings": featured,
            "primary_vocalizations": list(vocal_counts.keys())[:5],
        }

    def download_audio_clip(
        self,
        recording_id: str,
        target_dir: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Download high-fidelity wildlife audio file locally for playback and analysis."""
        details = self.get_recording_details(recording_id)
        audio_url = details.get("audio_url")
        if not audio_url:
            raise XenoCantoError(f"No audio download URL available for XC{recording_id}.")

        out_dir = Path(target_dir) if target_dir else Path(tempfile.gettempdir())
        out_dir.mkdir(parents=True, exist_ok=True)
        file_name = filename or f"XC{recording_id}.mp3"
        out_path = out_dir / file_name

        with httpx.Client(
            timeout=self.timeout, transport=self.transport, follow_redirects=True
        ) as client:
            try:
                resp = client.get(audio_url)
                resp.raise_for_status()
                out_path.write_bytes(resp.content)
            except (httpx.HTTPError, OSError) as exc:
                raise XenoCantoError(
                    f"Failed to download audio for XC{recording_id}: {exc}"
                ) from exc

        return {
            "recording_id": str(recording_id),
            "file_path": str(out_path.resolve()),
            "file_size_bytes": out_path.stat().st_size,
            "mime_type": "audio/mpeg",
            "species": details.get("scientific_name"),
            "common_name": details.get("common_name"),
            "vocalization_type": details.get("vocalization_type"),
            "quality": details.get("quality"),
            "audio_url": audio_url,
        }

    def get_recordist_profile(self, recordist_name: str, limit: int = 25) -> dict[str, Any]:
        """Retrieve recordist portfolio, contribution statistics, and sampled recordings."""
        res = self.search_recordings(recordist=recordist_name, limit=limit)
        recordings = res.get("recordings", [])
        species_counts: dict[str, int] = {}
        countries: set[str] = set()

        for r in recordings:
            sp = r.get("scientific_name")
            if sp:
                species_counts[sp] = species_counts.get(sp, 0) + 1
            cnt = r.get("country")
            if cnt:
                countries.add(cnt)

        top_species = sorted(species_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "recordist": recordist_name,
            "total_recordings": res.get("total_recordings", len(recordings)),
            "total_species_recorded": res.get("total_species", len(species_counts)),
            "countries_visited": sorted(countries),
            "top_recorded_species": [{"species": s[0], "count": s[1]} for s in top_species],
            "sample_recordings": recordings,
        }

    def _request(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise XenoCantoError(f"Xeno-canto API request failed for {path}: {exc}") from exc

            try:
                return response.json()
            except Exception as exc:
                raise XenoCantoError(f"Invalid JSON returned from Xeno-canto for {path}") from exc

    @staticmethod
    def _normalize_recording(rec: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize raw recording into agent-friendly JSON."""
        gen = rec.get("gen", "").strip()
        sp = rec.get("sp", "").strip()
        scientific = f"{gen} {sp}".strip() if gen or sp else "Unknown"

        audio_file = rec.get("file", "")
        if audio_file.startswith("//"):
            audio_file = f"https:{audio_file}"

        web_url = rec.get("url", "")
        if web_url.startswith("//"):
            web_url = f"https:{web_url}"

        sono = rec.get("sono", {})
        sonograms = {}
        if isinstance(sono, dict):
            for size, url in sono.items():
                if isinstance(url, str):
                    sonograms[size] = f"https:{url}" if url.startswith("//") else url

        lat_val = None
        lon_val = None
        try:
            if rec.get("lat"):
                lat_val = float(rec["lat"])
            if rec.get("lng"):
                lon_val = float(rec["lng"])
        except (ValueError, TypeError):
            pass

        return {
            "id": str(rec.get("id")),
            "scientific_name": scientific,
            "common_name": rec.get("en"),
            "group": rec.get("group", "birds"),
            "vocalization_type": rec.get("type"),
            "quality": rec.get("q"),
            "length": rec.get("length"),
            "recordist": rec.get("rec"),
            "country": rec.get("cnt"),
            "locality": rec.get("loc"),
            "latitude": lat_val,
            "longitude": lon_val,
            "date": rec.get("date"),
            "time": rec.get("time"),
            "audio_url": audio_file,
            "web_url": web_url,
            "sonograms": sonograms,
            "license": rec.get("lic"),
            "remarks": rec.get("rmk"),
        }
