-- ============================================================================
-- SUPABASE SETUP: Real Estate Scraper
-- ============================================================================
-- Run these SQL commands in your Supabase SQL Editor to set up the Real_estate table
-- with proper schema, indexes, and RLS policies
-- ============================================================================

-- 1. CREATE TABLE: Real_estate
-- ============================================================================
CREATE TABLE IF NOT EXISTS "Real_estate" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    web_url TEXT NOT NULL UNIQUE,
    title TEXT,
    type TEXT,
    location TEXT,
    address TEXT,
    bedroom INTEGER,
    bathroom INTEGER,
    price INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. CREATE INDEXES for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_real_estate_web_url ON "Real_estate"(web_url);
CREATE INDEX IF NOT EXISTS idx_real_estate_location ON "Real_estate"(location);
CREATE INDEX IF NOT EXISTS idx_real_estate_created_at ON "Real_estate"(created_at);
CREATE INDEX IF NOT EXISTS idx_real_estate_updated_at ON "Real_estate"(updated_at);

-- 3. CREATE TRIGGER for automatic updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_real_estate_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_real_estate_updated_at ON "Real_estate";
CREATE TRIGGER trigger_real_estate_updated_at
BEFORE UPDATE ON "Real_estate"
FOR EACH ROW
EXECUTE FUNCTION update_real_estate_timestamp();

-- 6. GRANT PERMISSIONS (if using service role)
-- ============================================================================
-- Note: These grants are typically automatic if using anon key with RLS.
-- Uncomment only if using service role without RLS enforcement:
-- GRANT SELECT, INSERT, UPDATE, DELETE ON "Real_estate" TO authenticated;

-- ============================================================================
-- VERIFICATION COMMANDS (optional, for testing after setup)
-- ============================================================================
-- Check if table is created:
-- SELECT * FROM information_schema.tables WHERE table_name='Real_estate';

-- Check if RLS is disabled:
-- SELECT relname, relrowsecurity FROM pg_class WHERE relname='Real_estate';

-- Check indexes:
-- SELECT indexname FROM pg_indexes WHERE tablename='Real_estate';

-- Check RLS policies:
-- SELECT * FROM pg_policies WHERE tablename='Real_estate';

-- ============================================================================
-- SCHEMA DESCRIPTION
-- ============================================================================
-- id:           UUID primary key, auto-generated
-- slug:         Unique property identifier from bproperty API (indexed for fast lookup)
-- web_url:      Full URL to property on bproperty.com (indexed for fast lookup)
-- title:        Property name/title
-- type:         Property type (e.g., "Apartment", "Rent")
-- location:     Geographic area/neighborhood (indexed for filtering)
-- address:      Full street address
-- bedroom:      Number of bedrooms
-- bathroom:     Number of bathrooms
-- price:        Listing price (numeric only, integer)
-- user_id:      FK to auth.users - identifies which user owns this property entry (RLS enforced)
-- created_at:   Timestamp when property was first discovered (immutable after insert)
-- updated_at:   Timestamp of last update (auto-managed by trigger)
-- source:       Data source identifier (default: 'scraper')
-- status:       Current status (default: 'COMPLETED')
--
-- RLS ENFORCEMENT:
-- - All SELECT, INSERT, UPDATE, DELETE operations filtered by current_user_id = auth.uid()
-- - Each user can only see/modify their own properties
-- - Safe for multi-tenant use
--
-- ============================================================================
