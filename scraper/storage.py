import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "scraper_v1.db")

@contextmanager
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # Primary storage for properties
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id TEXT PRIMARY KEY,
                web_url TEXT,
                title TEXT,
                type TEXT,
                location TEXT,
                address TEXT,
                bedroom INTEGER,
                bathroom INTEGER,
                price REAL,
                slug TEXT UNIQUE,
                status TEXT DEFAULT 'PENDING',
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scraped_at TIMESTAMP
            )
        """)
        
        # Metadata / API state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Progress Tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        conn.commit()

def save_discovery(prop_id, slug):
    web_url = f"https://www.bproperty.com/property/{slug}"
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO properties (id, slug, web_url, status)
            VALUES (?, ?, ?, 'PENDING')
        """, (prop_id, slug, web_url))
        conn.commit()
        return cursor.rowcount > 0

def update_property(prop_id, details):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE properties 
            SET title = ?, type = ?, location = ?, address = ?, 
                bedroom = ?, bathroom = ?, price = ?, 
                status = 'COMPLETED', scraped_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            details.get('title'),
            details.get('type'),
            details.get('location'),
            details.get('address'),
            details.get('bedroom'),
            details.get('bathroom'),
            details.get('price'),
            prop_id
        ))
        conn.commit()

def get_pending():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, slug, web_url FROM properties WHERE status = 'PENDING'")
        return [dict(row) for row in cursor.fetchall()]

def set_state(table, key, value):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(f"INSERT OR REPLACE INTO {table} (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

def get_state(table, key):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT value FROM {table} WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

def get_all_data():
    import pandas as pd
    with get_db_conn() as conn:
        return pd.read_sql_query("SELECT * FROM properties WHERE status = 'COMPLETED'", conn)

def reset_db():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM properties")
        cursor.execute("DELETE FROM api_state")
        cursor.execute("DELETE FROM progress")
        conn.commit()

def get_completed_for_export():
    """
    Get all COMPLETED properties in format ready for Supabase transfer.
    Ensures all fields are properly formatted. Missing values are set to None/null.
    
    Returns:
        List of dictionaries with Supabase schema fields
    """
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT web_url, title, type, location, address, 
                   bedroom, bathroom, price
            FROM properties 
            WHERE status = 'COMPLETED'
            ORDER BY discovered_at DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            try:
                # Convert row to dict with explicit field mapping
                # Use None for any missing or invalid values instead of failing
                prop_dict = {
                    'web_url': row[0] if row[0] else None,  # web_url - keep as is, can be None
                    'title': row[1] if row[1] else None,  # title TEXT
                    'type': row[2] if row[2] else None,  # type TEXT
                    'location': row[3] if row[3] else None,  # location TEXT
                    'address': row[4] if row[4] else None,  # address TEXT
                    'bedroom': int(row[5]) if row[5] else None,  # bedroom INT (None if missing)
                    'bathroom': int(row[6]) if row[6] else None,  # bathroom INT (None if missing)
                    'price': int(row[7]) if row[7] and row[7] > 0 else None,  # price INT (None if invalid)
                }
                
                results.append(prop_dict)
                
            except (TypeError, ValueError) as e:
                logger.warning(f"Error processing row {row}: {e} - Using None for problematic values")
                # Still add the property with None for problematic fields
                prop_dict = {
                    'web_url': row[0] if len(row) > 0 and row[0] else None,
                    'title': row[1] if len(row) > 1 and row[1] else None,
                    'type': row[2] if len(row) > 2 and row[2] else None,
                    'location': row[3] if len(row) > 3 and row[3] else None,
                    'address': row[4] if len(row) > 4 and row[4] else None,
                    'bedroom': None,  # Set to None if conversion fails
                    'bathroom': None,  # Set to None if conversion fails
                    'price': None,  # Set to None if conversion fails
                }
                results.append(prop_dict)
        
        return results

def get_pending_count():
    """Get count of pending properties."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM properties WHERE status = 'PENDING'")
        return cursor.fetchone()[0]

def get_completed_count():
    """Get count of completed properties."""
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM properties WHERE status = 'COMPLETED'")
        return cursor.fetchone()[0]
