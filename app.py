import streamlit as st
import pandas as pd
import time
import sys
import os

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.storage import init_db, get_pending, update_property, get_all_data, reset_db, get_state
from scraper.api_fetcher import discover_properties
from scraper.property_scraper import scrape_property_details
from scraper.progress_tracker import update_progress, get_last_progress, clear_progress
from utils.logger import setup_logger

logger = setup_logger("admin_panel")

# Initialize DB
init_db()

st.set_page_config(page_title="Q Scrapers Admin v1.0", layout="wide", page_icon="🏙️")

st.title("🏙️ Q Scrapers - Real Estate v1.0")
st.markdown("---")

# Session State Initialization
if 'scraping_active' not in st.session_state:
    st.session_state.scraping_active = False

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    if st.button("🔍 Discover New Properties", help="Fetch property IDs and slugs from API", use_container_width=True):
        with st.spinner("Discovering from API..."):
            if discover_properties():
                st.success("Discovery complete!")
            else:
                st.error("Discovery failed. Check logs.")
    
    st.divider()
    
    # Scraping toggle logic
    col_a, col_b = st.columns(2)
    if st.button("🚀 Start/Resume", disabled=st.session_state.scraping_active, use_container_width=True):
        st.session_state.scraping_active = True
        st.rerun()
        
    if st.button("⏸️ Pause", disabled=not st.session_state.scraping_active, use_container_width=True):
        st.session_state.scraping_active = False
        st.rerun()

    st.divider()
    
    if st.button("📥 Export to CSV", use_container_width=True):
        df = get_all_data()
        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                label="Confirm Download",
                data=csv,
                file_name=f"bproperty_data_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No data found to export.")

    st.divider()
    
    st.warning("Danger Zone")
    if st.button("🗑️ Reset All Data", help="Wipe database and progress", type="secondary", use_container_width=True):
        reset_db()
        clear_progress()
        st.success("System reset successfully!")
        st.rerun()

# Layout: Stats & Metrics
col1, col2, col3 = st.columns(3)
with col1:
    total_items = get_state("api_state", "totalItems") or "0"
    st.metric("Total Listings (API)", total_items)
with col2:
    pending_list = get_pending()
    st.metric("Pending Scrape", len(pending_list))
with col3:
    completed_df = get_all_data()
    st.metric("Successfully Scraped", len(completed_df))

# Progress Area
if st.session_state.scraping_active:
    st.header("⏳ Scraping in Progress...")
    
    pending = get_pending()
    if not pending:
        st.info("No pending properties found. Please run Discovery first.")
        st.session_state.scraping_active = False
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total = len(pending)
        count = 0
        
        for item in pending:
            # Check pause state
            if not st.session_state.scraping_active:
                st.warning("Scraping paused.")
                break
                
            prop_id = item['id']
            slug = item['slug']
            
            status_text.text(f"Scraping [{count+1}/{total}]: {slug}")
            
            details = scrape_property_details(slug)
            if details:
                update_property(prop_id, details)
                count += 1
                update_progress(count, total, prop_id)
            
            progress_bar.progress((count) / total)
            
        if count == total:
            st.success(f"Successfully scraped {count} properties!")
            st.session_state.scraping_active = False
            st.rerun()

# Data Preview
st.divider()
st.header("📊 Scraped Data Overview")
df = get_all_data()
if not df.empty:
    # Reorder columns for better view
    cols = ['title', 'price', 'type', 'location', 'bedroom', 'bathroom', 'address', 'web_url']
    st.dataframe(df[cols], use_container_width=True)
else:
    st.info("No data available yet. Start scraping to see results.")
