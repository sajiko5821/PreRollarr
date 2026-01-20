# PreRollarr

Automates the management of pre-roll videos in Plex.

## Requirements

- Python 3.x
- PyYAML
- requests

## Installation & Start

```bash
pip3 install -r requirements.txt
python3 main.py
```

## Configuration

Edit `config.yaml` with the following settings:

- `plex_server_url`: Your Plex server URL (e.g., `http://localhost:32400`)
- `plex_token`: Your X-Plex-Token -> [How to get your Plex Token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
- `root_path`: Local path to your pre-roll video files on the system
- `plex_path`: Mapped path in Plex to the pre-roll video files
- `patterns`: Directory names to match for specific pre-roll seasons or events

## Docker Usage

To create and run the Docker container, use the provided `docker-compose.yml` file.
Before starting, ensure you have a valid `config.yaml` in the same directory.

```bash
docker-compose up -d
```
