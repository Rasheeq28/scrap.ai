from scraper.storage import set_state, get_state, get_pending
import json

def update_progress(current_index, total_items, completed_id):
    """Saves current scraping state to the database."""
    state = {
        "current_index": current_index,
        "total_to_scrape": total_items,
        "last_completed_id": completed_id
    }
    set_state("progress", "last_session", json.dumps(state))

def get_last_progress():
    """Retrieves last saved session state."""
    raw = get_state("progress", "last_session")
    if raw:
        return json.loads(raw)
    return None

def clear_progress():
    """Resets session progress."""
    set_state("progress", "last_session", "")
