"""
Supabase Sync Module
Handles change detection, duplicate identification, and deduplication logic.
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class SupabaseSync:
    """
    Manages synchronization logic between local SQLite and Supabase:
    - Identifies new properties (in local but not in Supabase)
    - Detects duplicates (matching by slug or web_url)
    - Removes duplicates before transfer
    """

    def __init__(self, supabase_client):
        """
        Initialize sync manager.

        Args:
            supabase_client: SupabaseClient instance (must be connected)
        """
        self.supabase_client = supabase_client
        self.existing_properties = {}

    def refresh_existing_properties(self) -> Dict[str, Tuple[str, str]]:
        """
        Fetch current properties from Supabase.

        Returns:
            Dict mapping slug -> (web_url, id)
        """
        self.existing_properties = self.supabase_client.get_existing_properties()
        return self.existing_properties

    def identify_new_properties(
        self, local_properties: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Compare local properties with Supabase and identify new ones.

        Args:
            local_properties: List of property dicts from SQLite (COMPLETED status)

        Returns:
            Tuple of (new_properties, duplicate_properties, stats_dict)
            where stats_dict contains: {'new_count': int, 'duplicate_count': int, 'total_count': int}
        """
        if not self.existing_properties:
            self.refresh_existing_properties()

        new_properties = []
        duplicate_properties = []

        # Create set of existing (slug, web_url) pairs for comparison
        existing_identifiers = set()
        for slug, (web_url, _) in self.existing_properties.items():
            existing_identifiers.add((slug, web_url))

        # Check each local property
        for prop in local_properties:
            slug = prop.get("slug", "")
            web_url = prop.get("web_url", "")

            if (slug, web_url) in existing_identifiers:
                duplicate_properties.append(prop)
            else:
                new_properties.append(prop)

        stats = {
            "new_count": len(new_properties),
            "duplicate_count": len(duplicate_properties),
            "total_count": len(local_properties),
        }

        logger.info(
            f"📊 Comparison Results: {stats['new_count']} new, "
            f"{stats['duplicate_count']} duplicates out of {stats['total_count']} total"
        )

        return new_properties, duplicate_properties, stats

    def identify_duplicates_in_batch(
        self, properties: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Identify duplicates within a batch of properties (matching by slug or web_url).

        Args:
            properties: List of property dicts to check for duplicates

        Returns:
            Tuple of (unique_properties, duplicate_properties, stats_dict)
        """
        unique_properties = []
        duplicate_properties = []

        # Track seen identifiers
        seen_slugs = set()
        seen_urls = set()
        slug_to_prop = {}  # Track first occurrence of each slug

        # First pass: identify duplicates
        for prop in properties:
            slug = prop.get("slug", "")
            web_url = prop.get("web_url", "")

            is_duplicate = False

            # Check if this slug already seen
            if slug and slug in seen_slugs:
                is_duplicate = True
            # Check if this URL already seen
            elif web_url and web_url in seen_urls:
                is_duplicate = True

            if is_duplicate:
                duplicate_properties.append(prop)
            else:
                unique_properties.append(prop)
                if slug:
                    seen_slugs.add(slug)
                    slug_to_prop[slug] = prop
                if web_url:
                    seen_urls.add(web_url)

        stats = {
            "unique_count": len(unique_properties),
            "duplicate_count": len(duplicate_properties),
            "total_count": len(properties),
        }

        logger.info(
            f"🔍 Batch Deduplication: {stats['unique_count']} unique, "
            f"{stats['duplicate_count']} duplicates out of {stats['total_count']} total"
        )

        return unique_properties, duplicate_properties, stats

    def remove_duplicates(self, properties: List[Dict]) -> List[Dict]:
        """
        Remove duplicates from a batch, keeping first occurrence of each slug.

        Args:
            properties: List of property dicts

        Returns:
            List with duplicates removed
        """
        unique_properties, _, _ = self.identify_duplicates_in_batch(properties)
        return unique_properties

    def prepare_for_transfer(
        self, local_properties: List[Dict]
    ) -> Tuple[List[Dict], Dict]:
        """
        Complete preparation pipeline:
        1. Remove duplicates within local batch
        2. Compare against Supabase
        3. Return only new properties

        Args:
            local_properties: List of COMPLETED properties from SQLite

        Returns:
            Tuple of (properties_to_transfer, summary_dict)
            summary_dict = {
                'total_local': int,
                'after_dedup': int,
                'new_only': int,
                'duplicates_batch': int,
                'duplicates_supabase': int,
                'ready_to_transfer': int,
                'properties_ready': List[Dict]
            }
        """
        logger.info(f"🚀 Starting transfer preparation pipeline...")

        summary = {
            "total_local": len(local_properties),
            "after_dedup": 0,
            "new_only": 0,
            "duplicates_batch": 0,
            "duplicates_supabase": 0,
            "ready_to_transfer": 0,
            "properties_ready": [],
        }

        # Step 1: Remove duplicates within batch
        deduplicated, dup_batch, dup_stats = self.identify_duplicates_in_batch(
            local_properties
        )
        summary["after_dedup"] = dup_stats["unique_count"]
        summary["duplicates_batch"] = dup_stats["duplicate_count"]

        logger.info(
            f"✓ Step 1 (Batch Dedup): {summary['duplicates_batch']} removed, "
            f"{summary['after_dedup']} remaining"
        )

        # Step 2: Compare against Supabase
        new_only, dup_supabase, comparison_stats = self.identify_new_properties(
            deduplicated
        )
        summary["new_only"] = comparison_stats["new_count"]
        summary["duplicates_supabase"] = comparison_stats["duplicate_count"]
        summary["ready_to_transfer"] = len(new_only)
        summary["properties_ready"] = new_only

        logger.info(
            f"✓ Step 2 (Supabase Compare): {summary['duplicates_supabase']} already exist, "
            f"{summary['new_only']} are new"
        )

        logger.info(
            f"✅ Transfer Preparation Complete: {summary['ready_to_transfer']} properties "
            f"ready to transfer to Supabase"
        )

        return new_only, summary

    def get_sync_report(
        self, local_properties: List[Dict], new_properties: List[Dict],
        duplicates_in_batch: List[Dict], duplicates_in_supabase: List[Dict]
    ) -> str:
        """
        Generate a human-readable sync report.

        Args:
            local_properties: All local properties
            new_properties: Properties to transfer
            duplicates_in_batch: Duplicates found within batch
            duplicates_in_supabase: Duplicates already in Supabase

        Returns:
            Formatted report string
        """
        report = f"""
╔════════════════════════════════════════════════════════════════╗
║                    SUPABASE SYNC REPORT                        ║
╚════════════════════════════════════════════════════════════════╝

📊 SUMMARY:
  • Total Local Properties:         {len(local_properties):>6}
  • Duplicates (within batch):      {len(duplicates_in_batch):>6}
  • Duplicates (already in Supabase):{len(duplicates_in_supabase):>6}
  • New Properties (ready):         {len(new_properties):>6}

📈 BREAKDOWN:
  • Batch Uniqueness:    {(len(local_properties) - len(duplicates_in_batch)) / max(len(local_properties), 1) * 100:.1f}%
  • New Properties Rate: {len(new_properties) / max(len(local_properties), 1) * 100:.1f}%

🎯 ACTION:
  Ready to upsert {len(new_properties)} new properties to Supabase.

════════════════════════════════════════════════════════════════
"""
        return report
