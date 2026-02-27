<p align="center">
  <img src="prerollarr_logo.png" width="200" />
</p>

<h1 align="center">PreRollarr</h1>

[![Docker Image Version](https://img.shields.io/github/v/tag/sajiko5821/prerollarr?label=version&logo=docker&color=2496ED)](https://github.com/sajiko5821/prerollarr/pkgs/container/prerollarr)
[![Build Status](https://img.shields.io/github/actions/workflow/status/sajiko5821/prerollarr/docker-publish.yml?branch=main&label=build&logo=github)](https://github.com/sajiko5821/prerollarr/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automates the management of pre-roll videos in Plex. The application monitors seasonal events and updates your Plex pre-roll settings accordingly.

## Features

- 🎬 Automatic pre-roll management for Plex
- 📅 Event-based pre-roll rotation (holidays, seasons, etc.)
- 🐳 Docker support with docker-compose
- ⏱️ Configurable update frequency
- 📂 Select multiple pre-rolls per event from defined a folder

## Quick Start with Docker

### Prerequisites

- Docker & Docker Compose
- Plex Server running
- Your Plex authentication token

### 1. Get your Plex Token

[How to find your X-Plex-Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

### 2. Edit `docker-compose.yml`

Update the environment variables with your Plex details:

```yaml
environment:
  - PLEX_URL=http://YOUR_PLEX_IP:YOUR_PORT         # e.g., http://192.168.1.100:32400
  - PLEX_TOKEN=YOUR_PLEX_TOKEN                     # Your X-Plex-Token
  - PLEX_PATH=/path/in/plex                        # Where Plex sees the pre-rolls
  - UPDATES_PER_DAY=4                              # How often to update (1, 2, 4, 6, 8, 12, 24)
```

### 3. Update volume mounts

Edit the pre-roll path in `docker-compose.yml`:

```yaml
volumes:
  - ./appdata/config.yaml:/app/config.yaml:ro     # Path to your config.yaml (Persistant) - You may copy the config.yaml.example 
  - /your/local/preroll/path:/local-preroll:ro    # Path to your pre-roll videos
```

### 4. Start the container and check logs

```bash
docker-compose up -d

docker-compose logs -f prerollarr
```

## Configuration

### config.yaml

Edit `config.yaml` to define your pre-roll events:

```yaml
plex:
  url: http://YOUR_PLEX_IP:PORT           # Optional, gets overridden by PLEX_URL in docker-compose.yml
  token: YOUR_PLEX_TOKEN                  # Optional, gets overridden by PLEX_TOKEN in docker-compose.yml

paths:
  root_path: /local-preroll               # Inside container
  plex_path: /path/in/plex                # How Plex sees it

always:
  - name: "Default"
    patterns:
      - "/"                               # Default pre-rolls

events:
  - name: "Christmas"
    start_date: YYYY-12-24
    end_date: YYYY-12-25
    patterns:
      - "/christmas"
```

## Local Development

### Requirements

- Python 3.11+
- PyYAML
- requests

### Installation

```bash
pip3 install -r requirements.txt
```

### Run

```bash
python3 main.py
```

## Troubleshooting

### No logs appearing

Make sure `PYTHONUNBUFFERED=1` is set in docker-compose.yml

### Pre-rolls not updating

1. Check logs: `docker-compose logs prerollarr`
2. Verify Plex URL and token are correct
3. Verify PLEX_PATH matches your Plex library structure
4. Ensure pre-roll video files exist in the mounted volume

### Permission denied errors

Ensure the pre-roll directory is readable by Docker

## License

MIT
