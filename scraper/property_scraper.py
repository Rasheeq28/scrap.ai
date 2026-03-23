import httpx
from scraper.parser import PropertyParser
from utils.helpers import random_delay
from utils.logger import setup_logger

logger = setup_logger("property_scraper")
BASE_WEB_URL = "https://www.bproperty.com/property/"

def scrape_property_details(slug, max_retries=2):
    url = f"{BASE_WEB_URL}{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for attempt in range(max_retries + 1):
        try:
            random_delay(1, 3) 
            with httpx.Client(headers=headers, follow_redirects=True) as client:
                response = client.get(url, timeout=20)
                
                if response.status_code == 429:
                    logger.warning(f"Rate limited (429) on {slug}. Retrying after longer delay...")
                    random_delay(5, 10)
                    continue
                    
                response.raise_for_status()
                parser = PropertyParser(response.text)
                data = parser.parse_all()
                data['web_url'] = url
                return data
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for {slug}: {e}")
            if attempt == max_retries:
                return None
    return None
