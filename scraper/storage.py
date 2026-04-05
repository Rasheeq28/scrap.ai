import sqlite3
import os
from contextlib import contextmanager

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
    
    Returns:
        List of dictionaries with Supabase schema fields
    """
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, slug, web_url, title, type, location, address, 
                   bedroom, bathroom, price, discovered_at, scraped_at, status
            FROM properties 
            WHERE status = 'COMPLETED'
            ORDER BY discovered_at DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'slug': row[1],
                'web_url': row[2],
                'title': row[3],
                'type': row[4],
                'location': row[5],
                'address': row[6],
                'bedroom': row[7],
                'bathroom': row[8],
                'price': int(row[9]) if row[9] else None,
                'source': 'scraper',
                'status': row[12] or 'COMPLETED'
            })
        
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
