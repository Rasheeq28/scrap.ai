# Supabase Integration - Implementation Complete ✅

## Overview
Your real estate scraper is now fully integrated with Supabase. The system includes:
- Supabase table schema with RLS policies
- Change detection and duplicate removal logic
- Admin panel transfer button
- Batch upsert with conflict resolution

---

## 1️⃣ SUPABASE SETUP (Required - Do This First)

### Step 1: Create Table & RLS Policies

1. Open your **Supabase Console** → **SQL Editor**
2. Copy all SQL commands from: [SUPABASE_SETUP.sql](SUPABASE_SETUP.sql)
3. Paste into the SQL Editor and click **Run**

**What this does:**
- Creates `Real_estate` table with 14 columns
- Adds 6 indexes for fast lookups
- Enables Row Level Security (RLS)
- Creates 4 RLS policies (SELECT, INSERT, UPDATE, DELETE)
- Adds auto-update trigger for `updated_at` timestamp

### Step 2: Verify Setup

Check these in Supabase Console:

```sql
-- View table structure
SELECT * FROM information_schema.columns WHERE table_name='Real_estate';

-- Verify RLS is enabled
SELECT relname, relrowsecurity FROM pg_class WHERE relname='Real_estate';

-- Check RLS policies
SELECT * FROM pg_policies WHERE tablename='Real_estate';
```

---

## 2️⃣ ENVIRONMENT CONFIGURATION

### Update Your `.env` File

```bash
# Copy from .env.example and configure
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_USER_ID=550e8400-e29b-41d4-a716-446655440000
```

**How to get these values:**

1. **SUPABASE_URL**: 
   - Supabase Console → Settings → API → Project URL
   - Format: `https://[PROJECT_ID].supabase.co`

2. **SUPABASE_KEY**: 
   - Supabase Console → Settings → API → anon key (public key)
   - Safe for client-side use (RLS enforces security)

3. **SUPABASE_USER_ID**: 
   - If using Supabase Auth: Extract from `auth.uid()` after login
   - If manual: Use any valid UUID (e.g., `550e8400-e29b-41d4-a716-446655440000`)
   - Can be single-user or multi-user depending on your setup

---

## 3️⃣ SCHEMA REFERENCE

### Real_estate Table

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `id` | UUID | `gen_random_uuid()` | Primary key, auto-generated |
| `slug` | TEXT | - | Unique property ID from bproperty API |
| `web_url` | TEXT | - | Full URL to property (bproperty.com) |
| `title` | TEXT | - | Property name |
| `type` | TEXT | - | Type: Apartment, House, Land, etc. |
| `location` | TEXT | - | Geographic area (indexed) |
| `address` | TEXT | - | Full street address |
| `bedroom` | INTEGER | - | Bedroom count |
| `bathroom` | INTEGER | - | Bathroom count |
| `price` | INTEGER | - | Listing price (numeric only) |
| `user_id` | UUID | - | FK to auth.users (RLS enforced) |
| `created_at` | TIMESTAMP | `NOW()` | First discovered (immutable) |
| `updated_at` | TIMESTAMP | `NOW()` | Last modified (auto-updated) |
| `source` | TEXT | `'scraper'` | Data source identifier |
| `status` | TEXT | `'COMPLETED'` | Status flag (PENDING/COMPLETED) |

### Indexes
- `idx_real_estate_slug` — Fast duplicate detection by slug
- `idx_real_estate_web_url` — Fast duplicate detection by URL
- `idx_real_estate_user_id` — Fast RLS filtering
- `idx_real_estate_location` — Fast location-based queries
- `idx_real_estate_created_at` — Fast chronological queries
- `idx_real_estate_updated_at` — Fast sync queries

---

## 4️⃣ NEW PYTHON MODULES

### `scraper/supabase_client.py`
**Purpose**: Connection & data transfer to Supabase

**Key Methods:**
- `connect()` — Test connection to Supabase
- `get_existing_properties()` — Fetch all properties for current user
- `upsert_properties(properties, batch_size=500)` — Batch insert/update
- `get_row_count()` — Count rows in Supabase
- `get_last_sync_time()` — Get timestamp of last update
- `get_summary()` — Connection status & statistics

**Example Usage:**
```python
from scraper.supabase_client import SupabaseClient

client = SupabaseClient()
if client.connect():
    success, errors, messages = client.upsert_properties([
        {
            'slug': 'prop-123',
            'web_url': 'https://...',
            'title': 'Apartment',
            'price': 50000,
            # ... other fields
        }
    ])
    print(f"Transferred {success} properties")
```

### `scraper/supabase_sync.py`
**Purpose**: Change detection & duplicate removal

**Key Methods:**
- `refresh_existing_properties()` — Load current Supabase data
- `identify_new_properties(local_properties)` — Compare local vs. Supabase
- `identify_duplicates_in_batch(properties)` — Find duplicates in local batch
- `remove_duplicates(properties)` — Dedupe before transfer
- `prepare_for_transfer(properties)` — Complete pipeline (dedup + compare)
- `get_sync_report(...)` — Generate human-readable report

**Example Usage:**
```python
from scraper.supabase_sync import SupabaseSync
from scraper.supabase_client import SupabaseClient

client = SupabaseClient()
client.connect()

sync = SupabaseSync(client)
sync.refresh_existing_properties()

new_props, summary = sync.prepare_for_transfer(local_properties)
print(f"Found {len(new_props)} new properties ready to transfer")
print(summary['duplicates_supabase'])  # Already in Supabase
```

---

## 5️⃣ MODIFIED MODULES

### `scraper/storage.py`
**New Methods Added:**
- `get_completed_for_export()` — Returns COMPLETED properties in Supabase format
- `get_pending_count()` — Count pending properties
- `get_completed_count()` — Count completed properties

**Example:**
```python
from scraper.storage import get_completed_for_export

properties = get_completed_for_export()  # List[Dict]
# Ready to pass to Supabase client
```

### `app.py`
**New Section Added:** "📤 Supabase Transfer"

**Features:**
- ✓ Connection status indicator
- 📊 Preview statistics (new vs. duplicate properties)
- 🚀 "Transfer to Supabase" button
- 📝 Sample data preview of properties to transfer
- 🔄 Sync status information (last update, row counts)
- ⚠️ Error handling with detailed messages

**Admin Panel Flow:**
1. Click "Transfer to Supabase" button
2. System automatically:
   - Fetches all COMPLETED properties from SQLite
   - Detects duplicates within batch
   - Compares against Supabase
   - Shows preview of new properties
3. Confirm transfer
4. Upsert executed in batches of 500
5. Success/error feedback displayed

---

## 6️⃣ HOW IT WORKS

### Data Flow for Transfer

```
┌─────────────────────────────────────────────────────────────┐
│ Admin Panel: Click "Transfer to Supabase"                   │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Load COMPLETED properties from SQLite                     │
│    storage.get_completed_for_export() → List[Dict]          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Remove duplicates within batch                            │
│    sync.identify_duplicates_in_batch() → unique only        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Fetch existing properties from Supabase                   │
│    client.get_existing_properties() → Dict[slug -> url]     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Identify new properties (not already in Supabase)        │
│    Compare slug+web_url → separate new from duplicates      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Show preview to user                                      │
│    Display count & sample of new properties                 │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
              User Confirms Transfer
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Batch upsert to Supabase                                 │
│    Process in chunks of 500 with progress tracking          │
│    Conflict resolution: ON slug → UPDATE                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Show success/error feedback                              │
│    Display rows transferred, any errors                     │
└─────────────────────────────────────────────────────────────┘
```

### Duplicate Detection Logic

**Matching Strategy**: `(slug, web_url)` tuple comparison

**Phase 1 - Batch Deduplication:**
- Compare all properties in local batch
- Remove duplicates (keep first occurrence)
- Identify: `unique_props`, `duplicates_in_batch`

**Phase 2 - Supabase Comparison:**
- Fetch all existing properties from Supabase (for current user)
- Create set of `(slug, web_url)` pairs
- Compare unique batch against existing
- Identify: `new_props`, `duplicates_in_supabase`

**Result**: Only truly new properties transferred

---

## 7️⃣ TESTING CHECKLIST

### ✅ Connectivity Test
```python
from scraper.supabase_client import SupabaseClient

client = SupabaseClient()
assert client.connect(), "Connection failed"
print(client.get_summary())
```

### ✅ Change Detection Test
1. Add 5 COMPLETED properties to SQLite
2. Manually insert 2 of them into Supabase (via console)
3. Run transfer
4. Verify: Shows 3 new, 2 duplicates

```python
from scraper.storage import get_completed_for_export
from scraper.supabase_sync import SupabaseSync

local = get_completed_for_export()
new_props, summary = sync.prepare_for_transfer(local)
assert summary['new_count'] == 3, "Should show 3 new properties"
assert summary['duplicate_count'] == 2, "Should show 2 duplicates"
```

### ✅ Admin Panel Test
1. Open Streamlit app
2. Look for "📤 Supabase Transfer" section
3. Verify connection status
4. Click "Transfer to Supabase" button
5. Confirm properties transfer
6. Check Supabase Console → Properties viewed correctly

### ✅ RLS Test (Multi-User)
1. Create 2 test users in Supabase Auth
2. User A: Transfer 5 properties
3. User B: Transfer 3 properties
4. Query as User A: Should see only 5 rows
5. Query as User B: Should see only 3 rows

```sql
-- Login as User A, run:
SELECT COUNT(*) FROM "Real_estate";  -- Should be 5

-- Login as User B, run:
SELECT COUNT(*) FROM "Real_estate";  -- Should be 3
```

---

## 8️⃣ TROUBLESHOOTING

### Issue: "Connection failed" error

**Solution:**
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Check Supabase project is active (not paused)
3. Ensure Real_estate table exists (run SQL setup)
4. Check RLS policies are enabled

```bash
# Test from terminal in project directory
python -c "
from scraper.supabase_client import SupabaseClient
client = SupabaseClient()
print(client.connect())
"
```

### Issue: "No properties to transfer"

**Solution:**
1. Verify COMPLETED properties exist in SQLite
2. Check they're not already in Supabase
3. Verify SUPABASE_USER_ID matches owned properties

```bash
python -c "
from scraper.storage import get_completed_for_export
props = get_completed_for_export()
print(f'COMPLETED properties: {len(props)}')
for p in props[:3]:
    print(p)
"
```

### Issue: Upsert fails with "duplicate key" error

**Solution:**
- This shouldn't happen (upsert handles conflicts)
- If it occurs, the slug is already in Supabase
- Check RLS policy allows your user_id to see that property

### Issue: RLS error "new row violates row-level security policy"

**Solution:**
- Verify `user_id` field in transferred data matches `auth.uid()`
- Check `SUPABASE_USER_ID` in `.env` is correct
- Ensure RLS policies are properly configured

---

## 9️⃣ NEXT STEPS & OPTIMIZATION

### Potential Enhancements

1. **Real-Time Sync**: Add Supabase subscriptions for live updates
2. **Scheduled Sync**: Automate transfer on timer (every 1 hour, etc.)
3. **Advanced Filtering**: Transfer only properties in specific location/price range
4. **Backup**: Automatic SQLite backup before Supabase transfer
5. **Conflict Resolution**: Manual review of update conflicts
6. **Data Validation**: Pre-transfer validation of required fields

### Current Limitations

- Single-user mode (SUPABASE_USER_ID in .env)
- Manual transfer button (not automated)
- No scheduled sync
- Batch size hardcoded at 500 rows

---

## 🔟 QUICK REFERENCE

### File Structure
```
├── SUPABASE_SETUP.sql              ← Run this in Supabase Console first
├── .env.example                    ← Copy to .env and configure
├── scraper/
│   ├── supabase_client.py          ← NEW: Supabase connection & upsert
│   ├── supabase_sync.py            ← NEW: Change detection & dedup
│   ├── storage.py                  ← MODIFIED: Added export methods
│   └── ...
├── app.py                          ← MODIFIED: Added Transfer section
└── ...
```

### Key Commands

```bash
# Test connection
python -c "
from scraper.supabase_client import SupabaseClient
c = SupabaseClient()
print('Connected:', c.connect())
"

# Get completed properties count
python -c "
from scraper.storage import get_completed_for_export
print(len(get_completed_for_export()))
"

# Run transfer manually
python -c "
from scraper.storage import get_completed_for_export
from scraper.supabase_client import SupabaseClient
from scraper.supabase_sync import SupabaseSync

client = SupabaseClient()
client.connect()
sync = SupabaseSync(client)
props = get_completed_for_export()
new, summary = sync.prepare_for_transfer(props)
print(summary)
"
```

---

## Summary

✅ **Complete Implementation:**
1. Supabase table with RLS policies (SUPABASE_SETUP.sql)
2. Python modules for connection & sync (supabase_client.py, supabase_sync.py)
3. Change detection with duplicate removal
4. Admin panel button for data transfer
5. Batch upsert with conflict resolution
6. Comprehensive error handling

**Ready to use!** Follow the setup steps above.
