import re
import random
import time

def clean_numeric(text):
    """Extracts only digits from a string and returns as int."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d]", "", str(text))
    return int(cleaned) if cleaned else None

def random_delay(min_s=1, max_s=3):
    """Sleeps for a random duration between min_s and max_s."""
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)

def format_comma_separated(items):
    """Joins a list of items into a comma-separated string."""
    if not items:
        return ""
    return ", ".join(filter(None, [str(i).strip() for i in items]))
