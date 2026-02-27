import yaml
import os
import requests
import time
import threading
from datetime import datetime
from urllib.parse import quote
from flask import Flask, jsonify, request as flask_request, render_template

app = Flask(__name__)

# Determine config path once at startup
CONFIG_PATH = '/app/config.yaml' if os.path.exists('/app/config.yaml') else 'fallback_config.yaml'


def load_config(config_path=None):
    if config_path is None:
        config_path = CONFIG_PATH
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Write the full config back to disk."""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def get_plex_mapped_files(root_path, plex_path, patterns):
    final_paths = []
    root_path = os.path.join(root_path, '')
    plex_path = os.path.join(plex_path, '')

    for pattern in patterns:
        clean_pattern = pattern.strip('/')
        full_local_path = os.path.join(root_path, clean_pattern)

        if os.path.exists(full_local_path):
            if os.path.isdir(full_local_path):
                for item in os.listdir(full_local_path):
                    # Filter out hidden files like .DS_Store
                    if not item.startswith('.'):
                        local_file_path = os.path.join(full_local_path, item)
                        if os.path.isfile(local_file_path):
                            plex_ready_path = local_file_path.replace(root_path, plex_path)
                            final_paths.append(plex_ready_path)
            elif os.path.isfile(full_local_path):
                plex_ready_path = full_local_path.replace(root_path, plex_path)
                final_paths.append(plex_ready_path)

    return final_paths


def update_plex_preroll(server_url, token, preroll_string):
    """Sends the PUT request to Plex to update the pre-roll setting."""
    # URL-encode the string to handle spaces and special characters safely
    encoded_preroll = quote(preroll_string)

    endpoint = f"{server_url}/:/prefs"
    params = {'CinemaTrailersPrerollID': preroll_string}
    headers = {'X-Plex-Token': token}

    try:
        # Plex expects a PUT request to the /:/prefs endpoint
        response = requests.put(endpoint, params=params, headers=headers)

        if response.status_code == 200:
            print("Successfully updated Plex Pre-Roll settings.")
        else:
            print(f"Failed to update. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")


def update_prerolls():
    """Main function to update pre-rolls."""
    config = load_config()
    today = datetime.now().date()
    current_year = today.year

    # Config Variables - allow override via environment variables
    plex_url = os.getenv('PLEX_URL', config['plex']['url'])
    plex_token = os.getenv('PLEX_TOKEN', config['plex']['token'])
    root_path = config['paths']['root_path']
    plex_path = os.getenv('PLEX_PATH', config['paths']['plex_path'])

    matched_patterns = None
    event_name = "Default"

    # 1. Date Logic
    for event in config.get('events', []):
        start_str = event['start_date'].replace('YYYY', str(current_year))
        end_str = event['end_date'].replace('YYYY', str(current_year))
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

        if start_date <= today <= end_date:
            matched_patterns = event['patterns']
            event_name = event['name']
            break

    if not matched_patterns:
        matched_patterns = config['always'][0]['patterns']

    # 2. Path Processing
    plex_files = get_plex_mapped_files(root_path, plex_path, matched_patterns)

    # If no files found for the matched event, fall back to default patterns
    if not plex_files and matched_patterns != config['always'][0]['patterns']:
        print(f"[{datetime.now()}] [{event_name}] No files found. Falling back to default patterns.")
        matched_patterns = config['always'][0]['patterns']
        event_name = "Default"
        plex_files = get_plex_mapped_files(root_path, plex_path, matched_patterns)

    if not plex_files:
        print(f"[{datetime.now()}] [{event_name}] No files found. Skipping update.")
        return

    # 3. Join with Semicolon
    preroll_string = ";".join(plex_files)
    print(f"[{datetime.now()}] [{event_name}] Setting Pre-rolls to: {preroll_string}")

    # 4. API Request
    update_plex_preroll(plex_url, plex_token, preroll_string)


def main():
    """Main loop - runs the update at specified intervals."""
    updates_per_day = int(os.getenv('UPDATES_PER_DAY', '4'))
    interval_seconds = (24 * 3600) // updates_per_day

    print(f"PreRollarr started. Will update {updates_per_day} times per day (every {interval_seconds} seconds)")
    print(f"First update at: {datetime.now()}")

    # Run indefinitely
    while True:
        try:
            update_prerolls()
        except Exception as e:
            print(f"[{datetime.now()}] Error during update: {e}")

        # Wait for the next update
        time.sleep(interval_seconds)


# ——— Flask Web UI ———

def _get_active_index():
    """Return the index of the currently active event, or -1 if none."""
    config = load_config()
    today = datetime.now().date()
    current_year = today.year
    for i, event in enumerate(config.get('events', [])):
        start_str = event['start_date'].replace('YYYY', str(current_year))
        end_str = event['end_date'].replace('YYYY', str(current_year))
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            if start_date <= today <= end_date:
                return i
        except ValueError:
            continue
    return -1


@app.route('/')
def web_index():
    return render_template('index.html')


@app.route('/api/config')
def api_config():
    """Return events, always-patterns, and the currently active event index."""
    config = load_config()
    events = config.get('events', [])
    always_patterns = config.get('always', [{}])[0].get('patterns', ['/'])
    active_index = _get_active_index()
    return jsonify({
        'events': events,
        'always': always_patterns,
        'active_index': active_index,
    })


@app.route('/api/events', methods=['POST'])
def api_add_event():
    """Append a new event."""
    data = flask_request.get_json()
    if not data or not data.get('name') or not data.get('start_date') or not data.get('end_date') or not data.get('patterns'):
        return jsonify({'error': 'Alle Felder sind erforderlich.'}), 400

    config = load_config()
    config.setdefault('events', []).append({
        'name': data['name'],
        'start_date': data['start_date'],
        'end_date': data['end_date'],
        'patterns': data['patterns'],
    })
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True}), 201


@app.route('/api/events/<int:index>', methods=['PUT'])
def api_update_event(index):
    """Update an existing event by index."""
    data = flask_request.get_json()
    config = load_config()
    events = config.get('events', [])
    if index < 0 or index >= len(events):
        return jsonify({'error': 'Event nicht gefunden.'}), 404

    events[index] = {
        'name': data.get('name', events[index]['name']),
        'start_date': data.get('start_date', events[index]['start_date']),
        'end_date': data.get('end_date', events[index]['end_date']),
        'patterns': data.get('patterns', events[index]['patterns']),
    }
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True})


@app.route('/api/events/<int:index>', methods=['DELETE'])
def api_delete_event(index):
    """Delete an event by index."""
    config = load_config()
    events = config.get('events', [])
    if index < 0 or index >= len(events):
        return jsonify({'error': 'Event nicht gefunden.'}), 404
    events.pop(index)
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True})


@app.route('/api/events/<int:index>/move', methods=['POST'])
def api_move_event(index):
    """Move an event up or down in the list (first-match-wins order matters)."""
    data = flask_request.get_json()
    direction = data.get('direction', 0)  # -1 = up, +1 = down
    config = load_config()
    events = config.get('events', [])
    new_index = index + direction
    if index < 0 or index >= len(events) or new_index < 0 or new_index >= len(events):
        return jsonify({'error': 'Verschieben nicht möglich.'}), 400
    events[index], events[new_index] = events[new_index], events[index]
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True})


@app.route('/api/events/reorder', methods=['POST'])
def api_reorder_event():
    """Move an event from one index to another (drag & drop)."""
    data = flask_request.get_json()
    from_idx = data.get('from')
    to_idx = data.get('to')
    config = load_config()
    events = config.get('events', [])
    if (from_idx is None or to_idx is None or
            from_idx < 0 or from_idx >= len(events) or
            to_idx < 0 or to_idx >= len(events)):
        return jsonify({'error': 'Invalid indices.'}), 400
    event = events.pop(from_idx)
    events.insert(to_idx, event)
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True})


@app.route('/api/always', methods=['PUT'])
def api_update_always():
    """Update the default (always) patterns."""
    data = flask_request.get_json()
    patterns = data.get('patterns', ['/'])
    config = load_config()
    config.setdefault('always', [{'name': 'Default', 'patterns': ['/']}])
    config['always'][0]['patterns'] = patterns
    save_config(config)
    update_prerolls()
    return jsonify({'ok': True})


def start_web():
    """Start the Flask web server."""
    port = int(os.getenv('WEB_PORT', '7919'))
    print(f"PreRollarr Web UI available at http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Start the polling loop in a background thread
    poll_thread = threading.Thread(target=main, daemon=True)
    poll_thread.start()

    # Run the web server in the main thread
    start_web()
