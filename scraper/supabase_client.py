"""
Supabase Client Module
Handles connection to Supabase, upsert operations, and batch data transfer.
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from supabase import create_client, Client
from utils.secrets import get_secret

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Manages Supabase connection and operations for real estate properties.
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client.

        Args:
            url: Supabase project URL (defaults to SUPABASE_URL from secrets)
            key: Supabase API key (defaults to SUPABASE_KEY from secrets)
        """
        self.url = url or get_secret("SUPABASE_URL")
        self.key = key or get_secret("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in secrets or environment variables"
            )

        self.client: Optional[Client] = None
        self.connected = False

    def connect(self) -> bool:
        """
        Establish connection to Supabase.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = create_client(self.url, self.key)
            # Test connection by fetching schema info
            response = self.client.table("Real_estate").select("id").limit(1).execute()
            self.connected = True
            logger.info("✓ Connected to Supabase successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to Supabase: {str(e)}")
            self.connected = False
            return False

    def get_existing_properties(self) -> Dict[str, str]:
        """
        Fetch all existing properties from Supabase.

        Returns:
            Dict mapping web_url -> id for fast duplicate detection
        """
        if not self.connected:
            raise RuntimeError("Not connected to Supabase. Call connect() first.")

        try:
            response = self.client.table("Real_estate").select("web_url,id").execute()
            properties = {}
            for row in response.data:
                properties[row["web_url"]] = row["id"]
            logger.info(f"📊 Fetched {len(properties)} existing properties from Supabase")
            return properties
        except Exception as e:
            logger.error(f"✗ Failed to fetch existing properties: {str(e)}")
            return {}

    def upsert_properties(
        self, properties: List[Dict], batch_size: int = 500
    ) -> Tuple[int, int, List[str]]:
        """
        Upsert properties to Supabase using batch processing.
        Conflict resolution: on web_url, update all fields including updated_at.
        Handles null values gracefully.

        Args:
            properties: List of property dictionaries to upsert
            batch_size: Number of records per batch (default: 500)

        Returns:
            Tuple of (success_count, error_count, error_messages)
        """
        if not self.connected:
            raise RuntimeError("Not connected to Supabase. Call connect() first.")

        if not properties:
            logger.warning("No properties to upsert")
            return 0, 0, []

        success_count = 0
        error_count = 0
        error_messages = []

        # Add timestamps to each property
        for idx, prop in enumerate(properties):
            try:
                prop["updated_at"] = datetime.utcnow().isoformat()
                # Don't override created_at if it exists, let Supabase handle it
                if "created_at" not in prop:
                    prop["created_at"] = datetime.utcnow().isoformat()
            except Exception as e:
                logger.warning(f"Error adding metadata to property {idx}: {e}")
                # Continue anyway, let it fail in batch if needed
                continue

        # Process in batches
        total_batches = (len(properties) + batch_size - 1) // batch_size
        logger.info(f"📦 Processing {len(properties)} properties in {total_batches} batch(es)...")

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(properties))
            batch = properties[start_idx:end_idx]

            try:
                # Validate batch before sending
                valid_batch = []
                for prop in batch:
                    if isinstance(prop, dict) and 'web_url' in prop:
                        valid_batch.append(prop)
                    else:
                        logger.warning(f"Skipping invalid property in batch: {prop}")
                
                if not valid_batch:
                    logger.warning(f"Batch {batch_idx + 1} has no valid properties")
                    error_count += len(batch)
                    error_messages.append(f"Batch {batch_idx + 1}: All properties invalid")
                    continue
                
                response = self.client.table("Real_estate").upsert(
                    valid_batch, on_conflict="web_url"
                ).execute()

                batch_success = len(valid_batch)
                success_count += batch_success
                logger.info(
                    f"✓ Batch {batch_idx + 1}/{total_batches}: "
                    f"Upserted {batch_success} properties"
                )
            except Exception as e:
                batch_error_count = len(batch)
                error_count += batch_error_count
                # Handle both Exception objects and dict error responses
                if isinstance(e, dict):
                    error_msg = f"Batch {batch_idx + 1}: {e.get('message', str(e))}"
                else:
                    error_msg = f"Batch {batch_idx + 1}: {str(e)}"
                error_messages.append(error_msg)
                logger.error(f"✗ {error_msg}")

        logger.info(
            f"📊 Upsert Summary: {success_count} succeeded, {error_count} failed"
        )
        return success_count, error_count, error_messages

    def get_row_count(self) -> int:
        """
        Get total row count for current user in Supabase.

        Returns:
            Number of rows in Real_estate table for current user
        """
        if not self.connected:
            raise RuntimeError("Not connected to Supabase. Call connect() first.")

        try:
            response = self.client.table("Real_estate").select(
                "id", count="exact"
            ).execute()
            count = response.count or 0
            return count
        except Exception as e:
            logger.error(f"✗ Failed to get row count: {str(e)}")
            return 0

    def get_last_sync_time(self) -> Optional[str]:
        """
        Get timestamp of most recently updated property.

        Returns:
            ISO format timestamp or None if no records
        """
        if not self.connected:
            raise RuntimeError("Not connected to Supabase. Call connect() first.")

        try:
            response = self.client.table("Real_estate").select(
                "updated_at"
            ).order("updated_at", desc=True).limit(1).execute()

            if response.data:
                return response.data[0]["updated_at"]
            return None
        except Exception as e:
            logger.error(f"✗ Failed to get last sync time: {str(e)}")
            return None

    def delete_property(self, slug: str) -> bool:
        """
        Delete a property by slug (for cleanup/maintenance).

        Args:
            slug: Property slug to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            raise RuntimeError("Not connected to Supabase. Call connect() first.")

        try:
            response = self.client.table("Real_estate").delete().eq("slug", slug).execute()
            logger.info(f"✓ Deleted property: {slug}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to delete property {slug}: {str(e)}")
            return False

    def get_summary(self) -> Dict:
        """
        Get connection summary and statistics.

        Returns:
            Dictionary with connection status and stats
        """
        summary = {
            "connected": self.connected,
            "url": self.url,
            "row_count": self.get_row_count() if self.connected else 0,
            "last_sync": self.get_last_sync_time() if self.connected else None,
        }
        return summary
