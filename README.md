# xeno-canto-mcp

[![CI](https://github.com/thesven/xeno-canto-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thesven/xeno-canto-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A multimodal **Model Context Protocol (MCP)** server for querying global wildlife vocalizations, bioacoustics recordings, and sound spectrograms from the [Xeno-canto](https://xeno-canto.org/) database.

Bridges the sensory gap in ecological AI by allowing language models and multimodal vision assistants to inspect wildlife audio streams, compare similar vocalizations, and analyze sonogram spectrogram patterns.

---

## Key Features

- **Global Bioacoustics Catalog**: Search over 800,000+ wildlife sound recordings covering birds, bats, amphibians, and vocalizing insects worldwide.
- **Multimodal Sonogram & Spectrogram Inspection**: Exposes direct URLs to generated frequency-time spectrogram images (`sono.full`, `sono.med`, `sono.small`) for visual sound analysis.
- **Species Vocalization Profiler**: Aggregate a species' acoustic repertoire across songs, calls, and alarms.
- **Vocalization Type & Taxa Filtering**: Easily query by vocal behavior (`song`, `alarm call`, `flight call`) and taxonomic groups (`birds`, `frogs`, `bats`, `grasshoppers`).
- **Quality-Filtered Audios**: Filter by recording quality grades (`A` through `E`) to guarantee high-fidelity audio evidence.
- **Acoustic Comparison Engine**: Compare two vocalizing species side-by-side with high-grade reference recordings.
- **Geographic Proximity Queries**: Find audio recorded in a specific area via bounding coordinates.

---

## Available Tools

| Tool | Description |
| :--- | :--- |
| `search_recordings` | Search wildlife audio recordings by species, country, vocalization type, quality, or taxa. |
| `search_recordings_nearby` | Search recordings within a bounding box around GPS coordinates and radius. |
| `get_recording_details` | Retrieve complete metadata, audio stream MP3 URL, and sonograms for an XC recording. |
| `get_sonogram_urls` | Retrieve spectrogram image URLs for multimodal visual sound inspection. |
| `get_species_vocalization_profile` | Aggregate a species' acoustic repertoire across song, call, and alarm vocalizations. |
| `compare_species_vocalizations` | Compare high-grade recordings and spectrograms for two similar species. |
| `download_audio_clip` | Download high-fidelity wildlife audio file locally for playback and analysis. |
| `get_recordist_profile` | Retrieve recordist portfolio, contribution statistics, and sampled recordings. |

---

## Installation & Usage

### Running with `uvx` (Recommended)

```bash
uvx --from git+https://github.com/thesven/xeno-canto-mcp.git xeno-canto-mcp
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "xeno-canto": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thesven/xeno-canto-mcp.git", "xeno-canto-mcp"]
    }
  }
}
```

---

## Development & Quality Gate

```bash
# Run code formatting check
uv run ruff format --check src tests scripts

# Run linting
uv run ruff check src tests scripts

# Run test suite with strict coverage floor (>90%)
uv run pytest --cov=xeno_canto_mcp --cov-branch --cov-report=term-missing

# Build wheel and sdist
uv build

# Run package distribution check & smoke test
uv run python scripts/check_dist.py
uv run python scripts/smoke.py
```

## License

MIT License. See [LICENSE](LICENSE) for details.
