import yaml
import os
import requests
import time
from datetime import datetime
from urllib.parse import quote


def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


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


if __name__ == "__main__":
    main()
