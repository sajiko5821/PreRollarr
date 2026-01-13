import yaml
import os
from datetime import datetime

def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_plex_mapped_files(root_path, plex_path, patterns):
    """
    Finds files using root_path, but returns them formatted with plex_path.
    """
    final_paths = []
    
    # Ensure paths end with a slash for clean replacement
    root_path = os.path.join(root_path, '')
    plex_path = os.path.join(plex_path, '')

    for pattern in patterns:
        clean_pattern = pattern.strip('/')
        full_local_path = os.path.join(root_path, clean_pattern)

        if os.path.exists(full_local_path):
            # If it's a directory, list all files inside
            if os.path.isdir(full_local_path):
                for item in os.listdir(full_local_path):
                    local_file_path = os.path.join(full_local_path, item)
                    
                    if os.path.isfile(local_file_path):
                        # --- THE MAGIC HAPPENS HERE ---
                        # Swap root_path for plex_path
                        plex_ready_path = local_file_path.replace(root_path, plex_path)
                        final_paths.append(plex_ready_path)
            
            # If it's a direct file path
            elif os.path.isfile(full_local_path):
                plex_ready_path = full_local_path.replace(root_path, plex_path)
                final_paths.append(plex_ready_path)
        else:
            print(f"Warning: Path not found: {full_local_path}")
            
    return final_paths

def main():
    config = load_config()
    today = datetime.now().date()
    current_year = today.year
    
    root_path = config['paths']['root_path']
    plex_path = config['paths']['plex_path']
    
    matched_patterns = None
    event_name = "Default"

    # 1. Determine which event is active
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

    print(f"--- Active Event: {event_name} ---")

    # 2. Get the files with the Plex-mapped paths
    plex_files = get_plex_mapped_files(root_path, plex_path, matched_patterns)
    
    if not plex_files:
        print("No files found.")
    else:
        # This will now print paths starting with /tests/PreRoll/
        for p in plex_files:
            print(p)

if __name__ == "__main__":
    main()