# Function to load or initialize state
import json
import os

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as file:
            return json.load(file)
    else:
        # Initialize the state if the file doesn't exist
        return {
            "isLeft": False,
            "main_url": "",
            "resume_page_url": "",
            "resume_product": "",
            "failed_urls": [],
            "visited_urls": []
        }

# Function to save the current state to JSON
def save_state(state):
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=4)
