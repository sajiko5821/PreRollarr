# PreRollarr – Copilot Instructions

## Project Overview

PreRollarr is a Python service (`main.py`) that periodically updates the Plex pre-roll setting based on date-driven event rules. It runs as a long-lived Docker container combining an infinite polling loop with a Flask web UI for managing events.

## Architecture & Data Flow

```
           ┌─────────── Flask Web UI (port 8080) ───────────┐
           │  GET/POST/PUT/DELETE /api/events                │
           │  PUT /api/always                                │
           │  reads & writes config.yaml                     │
           └─────────────────────────────────────────────────┘
                              ↕ config.yaml
┌─ Polling Thread (background, daemon) ─────────────────────────────┐
│ load_config() → date match in events[] → get_plex_mapped_files()  │
│                                         → update_plex_preroll()   │
└───────────────────────────────────────────────────────────────────┘
```

1. **Config loading** (`load_config`): Prefers `/app/config.yaml` (Docker mount), falls back to `fallback_config.yaml`. Path is determined once at startup in `CONFIG_PATH`.
2. **Event matching** (`update_prerolls`): Iterates `config['events']` in order; first match wins (`break`). Falls back to `config['always'][0]['patterns']` when no event matches.
3. **Path mapping** (`get_plex_mapped_files`): Finds files on disk under `root_path`, then rewrites that prefix to `plex_path` — these are two mount points for the same directory. Hidden files (`.DS_Store` etc.) are filtered automatically.
4. **Plex API** (`update_plex_preroll`): `PUT /:/prefs?CinemaTrailersPrerollID=<semicolon-joined paths>` with `X-Plex-Token` header.
5. **Polling loop** (`main`): Runs in a daemon thread. `UPDATES_PER_DAY` env var controls frequency.
6. **Web UI** (`start_web`): Flask server runs in the main thread on `WEB_PORT` (default `8080`). Template lives in `templates/index.html`.

## Web UI

- **Endpoint**: `http://localhost:8080` — manages events and default pre-rolls via REST API
- **API routes** (all in `main.py`):
  - `GET /api/config` — full config + active event index
  - `POST /api/events` — add event
  - `PUT /api/events/<index>` — update event
  - `DELETE /api/events/<index>` — delete event
  - `POST /api/events/<index>/move` — reorder (first-match-wins order matters)
  - `PUT /api/always` — update default patterns
- **Frontend**: Single-page vanilla HTML/CSS/JS in `templates/index.html`, no build step
- Config is saved to disk on every write operation via `save_config()`

## Configuration Schema (`fallback_config.yaml`)

```yaml
plex:
  url: http://HOST:32400   # overridden by PLEX_URL env
  token: TOKEN             # overridden by PLEX_TOKEN env

paths:
  root_path: /local-preroll  # container-local path to video files
  plex_path: /path/in/plex   # overridden by PLEX_PATH env; how Plex sees same files

always:
  - name: "Default"
    patterns: ["/"]          # falls back when no event matches

events:
  - name: "Christmas"
    start_date: YYYY-12-01   # YYYY is replaced with current_year at runtime
    end_date:   YYYY-12-30
    patterns: ["/xmas"]
```

`YYYY` in dates is a literal placeholder string, replaced via `.replace('YYYY', str(current_year))` — do not change this convention.

## Environment Variables

| Variable | Default (compose) | Purpose |
|---|---|---|
| `PLEX_URL` | `http://localhost:32400` | Overrides `plex.url` in config |
| `PLEX_TOKEN` | — | Overrides `plex.token` in config |
| `PLEX_PATH` | `/tests/PreRoll` | Overrides `paths.plex_path` |
| `UPDATES_PER_DAY` | `4` | Must divide 86400 evenly |
| `WEB_PORT` | `8080` | Port for the Flask web UI |
| `PYTHONUNBUFFERED` | `1` | Required for live Docker logs |

## Docker Volume Mounts

```yaml
- ./appdata/config.yaml:/app/config.yaml   # user config (rw for web UI)
- /host/preroll/dir:/local-preroll:ro       # pre-roll video files
```

The same physical directory is mounted twice conceptually: as `/local-preroll` inside the container (`root_path`) and as whatever path Plex uses (`plex_path`). Path rewriting bridges these two views.

## Local Development

```bash
pip3 install -r requirements.txt
python3 main.py                  # uses fallback_config.yaml automatically
```

There are no tests. The only runtime dependencies are `PyYAML`, `requests`, and `Flask`.

## Key Patterns & Constraints

- All logic lives in `main.py`; keep it that way for simplicity.
- Event evaluation is **first-match-wins** and purely date-based — guard against overlapping date ranges in config.
- `patterns` are relative to `root_path`. A pattern of `"/"` scans `root_path` itself (non-recursively, one level deep).
- New events should follow the `YYYY-MM-DD` date format with the `YYYY` placeholder.
- The Plex API expects a **semicolon-separated** string; do not use commas or other delimiters.
