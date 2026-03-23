import httpx
from scraper.storage import save_discovery, set_state, get_state
from utils.logger import setup_logger

logger = setup_logger("api_fetcher")
BASE_API_URL = "https://api.bproperty.com/api/collections/property_views/records"

def discover_properties():
    """Fetches all property IDs and slugs from the Bproperty API."""
    try:
        page = 1
        total_pages = 1
        new_count = 0
        total_new_items = 0
        
        # Initial call to get current state
        prev_items = int(get_state("api_state", "totalItems") or 0)
        prev_pages = int(get_state("api_state", "totalPages") or 0)

        with httpx.Client() as client:
            while page <= total_pages:
                logger.info(f"Fetching API page {page}...")
                response = client.get(f"{BASE_API_URL}?page={page}", timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Tracking API changes
                total_pages = data.get("totalPages", 1)
                total_items = data.get("totalItems", 0)
                
                set_state("api_state", "totalPages", total_pages)
                set_state("api_state", "totalItems", total_items)
                
                items = data.get("items", [])
                for item in items:
                    prop_id = item.get("id")
                    slug = item.get("slug")
                    if prop_id and slug:
                        if save_discovery(prop_id, slug): # Modify storage.py to return True on new insert
                            new_count += 1
                
                page += 1
        
        total_new_items = int(total_items) - prev_items
        total_new_pages = int(total_pages) - prev_pages
        
        logger.info(f"Discovery complete. New listings in DB: {new_count}. API diff: +{total_new_items} items.")
        return {
            "new_in_db": new_count,
            "new_items_api": total_new_items,
            "new_pages_api": total_new_pages
        }
    except Exception as e:
        logger.error(f"Error during discovery: {e}")
        return None
