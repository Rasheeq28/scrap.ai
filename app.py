import streamlit as st
import pandas as pd
import time
import sys
import os

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.storage import init_db, get_pending, update_property, get_all_data, reset_db, get_state, get_completed_for_export, get_completed_count
from scraper.api_fetcher import discover_properties
from scraper.property_scraper import scrape_property_details
from scraper.progress_tracker import update_progress, get_last_progress, clear_progress
from utils.logger import setup_logger

# Optional Supabase imports (graceful fallback if not installed)
try:
    from scraper.supabase_client import SupabaseClient
    from scraper.supabase_sync import SupabaseSync
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

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

st.divider()

# ============================================================================
# SUPABASE TRANSFER SECTION (Optional - only if available)
# ============================================================================
if SUPABASE_AVAILABLE:
    st.header("📤 Supabase Transfer")

    col_sup1, col_sup2 = st.columns([2, 1])

    with col_sup1:
        try:
            # Initialize Supabase connection
            supabase_client = SupabaseClient()
            
            # Connection Status
            if supabase_client.connect():
                sync = SupabaseSync(supabase_client)
                sync.refresh_existing_properties()
                
                # Get stats
                completed_properties = get_completed_for_export()
                
                if not completed_properties:
                    st.info("📭 No completed properties to transfer yet. Start scraping to see data here.")
                else:
                    try:
                        new_props, prep_stats = sync.prepare_for_transfer(completed_properties)
                        
                        # Display status
                        st.success("✓ Connected to Supabase")
                        
                        # Display counts in expandable section
                        with st.expander("📊 Transfer Preview & Statistics", expanded=False):
                            col_stat1, col_stat2, col_stat3 = st.columns(3)
                            with col_stat1:
                                st.metric("Ready to Transfer", prep_stats['ready_to_transfer'])
                            with col_stat2:
                                st.metric("Already in DB", prep_stats['duplicates_supabase'])
                            with col_stat3:
                                st.metric("Total Completed", prep_stats['total_local'])
                            
                            st.divider()
                            
                            # Show sync report (use counts from prep_stats)
                            st.write(sync.get_sync_report(
                                completed_properties, new_props, 
                                [],  # duplicates_in_batch (reconstructed from prep_stats)
                                []  # duplicates_in_supabase (reconstructed from prep_stats)
                            ))
                            
                            # Show sample data
                            if new_props:
                                st.write("**Sample of properties to transfer (first 5):**")
                                sample_df = pd.DataFrame(new_props[:5])
                                st.dataframe(sample_df, use_container_width=True)
                        
                        # Transfer button
                        if len(new_props) > 0:
                            if st.button("🚀 Transfer to Supabase", use_container_width=True, type="primary"):
                                with st.spinner("Transferring data to Supabase..."):
                                    try:
                                        success_count, error_count, errors = supabase_client.upsert_properties(new_props)
                                        
                                        if success_count > 0:
                                            st.success(f"✓ Successfully transferred {success_count} properties to Supabase!")
                                            st.info(f"📊 These properties are now available in the Real_estate table")
                                        
                                        if error_count > 0:
                                            st.error(f"✗ {error_count} properties failed to transfer")
                                            with st.expander("Error Details"):
                                                for error in errors:
                                                    st.error(error)
                                    except Exception as e:
                                        st.error(f"✗ Transfer failed: {str(e)}")
                        else:
                            st.info("✓ All completed properties are already in Supabase. No new data to transfer.")
                        
                        # View sync status
                        with st.expander("🔄 Sync Status & Information"):
                            summary = supabase_client.get_summary()
                            st.write(f"**URL**: {summary['url']}")
                            st.write(f"**User ID**: {summary['user_id']}")
                            st.write(f"**Total Rows in Supabase**: {summary['row_count']}")
                            if summary['last_sync']:
                                st.write(f"**Last Update**: {summary['last_sync']}")
                    
                    except ValueError as ve:
                        st.error(f"❌ Data validation error: {str(ve)}")
                        with st.expander("Error Details"):
                            st.write(f"This usually means there's an issue with the data format from SQLite.")
                            st.write(f"Error: {str(ve)}")
                    except Exception as e:
                        st.error(f"❌ Sync preparation error: {str(e)}")
                        with st.expander("Error Details"):
                            st.write(f"Error: {str(e)}")
                            st.write("Try checking the logs on Streamlit Cloud for more details.")
            else:
                st.error("✗ Failed to connect to Supabase. Check your credentials in secrets")
                st.info("Required secrets: SUPABASE_URL, SUPABASE_KEY, SUPABASE_USER_ID")
        
        except ValueError as ve:
            st.error(f"❌ Configuration error: {str(ve)}")
            st.error("Make sure SUPABASE_URL and SUPABASE_KEY are set in your secrets/env")
        except Exception as e:
            st.error(f"❌ Unexpected error in Supabase Transfer: {str(e)}")
            with st.expander("Error Details"):
                st.write(f"Error: {str(e)}")

    st.divider()
else:
    st.info("💡 **Supabase Transfer Feature**: Install `supabase-py` to enable database sync. Run: `pip install supabase`")

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
