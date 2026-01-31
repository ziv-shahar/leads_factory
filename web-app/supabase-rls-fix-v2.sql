-- ============================================================================
-- FIX: RLS Policies for Both Web App and Python Pipeline
-- ============================================================================
-- This script fixes RLS policies to allow:
-- 1. Authenticated users (web app) to read data
-- 2. Service role (Python pipeline) to read/write data
-- 3. Avoids circular references that caused infinite recursion
-- ============================================================================

-- ============================================================================
-- STEP 1: Fix entities table - Allow pipeline to insert
-- ============================================================================
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON entities;
DROP POLICY IF EXISTS "Users can view entities" ON entities;
DROP POLICY IF EXISTS "Allow all authenticated access" ON entities;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON entities;
DROP POLICY IF EXISTS "authenticated_users_access_entities" ON entities;

-- Allow authenticated users to read
CREATE POLICY "authenticated_users_read_entities"
ON entities
FOR SELECT
TO authenticated
USING (true);

-- Allow service role to do everything (for Python pipeline)
CREATE POLICY "service_role_all_access_entities"
ON entities
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 2: Fix events table - Allow pipeline to insert
-- ============================================================================
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON events;
DROP POLICY IF EXISTS "Users can view events" ON events;
DROP POLICY IF EXISTS "Allow all authenticated access" ON events;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON events;
DROP POLICY IF EXISTS "authenticated_users_access_events" ON events;

-- Allow authenticated users to read
CREATE POLICY "authenticated_users_read_events"
ON events
FOR SELECT
TO authenticated
USING (true);

-- Allow service role to do everything (for Python pipeline)
CREATE POLICY "service_role_all_access_events"
ON events
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 3: Fix location_leads table - Allow pipeline to insert
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Drop all existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;
DROP POLICY IF EXISTS "Admins see all location leads" ON location_leads;
DROP POLICY IF EXISTS "Users see allowed state leads" ON location_leads;
DROP POLICY IF EXISTS "Users can view location leads" ON location_leads;
DROP POLICY IF EXISTS "Allow all authenticated access" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_access_all_leads" ON location_leads;

-- Allow authenticated users to read
CREATE POLICY "authenticated_users_read_leads"
ON location_leads
FOR SELECT
TO authenticated
USING (true);

-- Allow service role to do everything (for Python pipeline)
CREATE POLICY "service_role_all_access_leads"
ON location_leads
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 4: Fix raw_events table (used by pipeline)
-- ============================================================================
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON raw_events;
DROP POLICY IF EXISTS "Enable all for service role" ON raw_events;

-- Allow authenticated users to read
CREATE POLICY "authenticated_users_read_raw_events"
ON raw_events
FOR SELECT
TO authenticated
USING (true);

-- Allow service role to do everything (for Python pipeline)
CREATE POLICY "service_role_all_access_raw_events"
ON raw_events
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 5: Fix leads_current table (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'leads_current') THEN
    EXECUTE 'ALTER TABLE leads_current ENABLE ROW LEVEL SECURITY';

    EXECUTE 'DROP POLICY IF EXISTS "Enable all for authenticated users" ON leads_current';
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for service role" ON leads_current';

    EXECUTE 'CREATE POLICY "authenticated_users_read_leads_current" ON leads_current
             FOR SELECT TO authenticated USING (true)';

    EXECUTE 'CREATE POLICY "service_role_all_access_leads_current" ON leads_current
             FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- STEP 6: Fix lead_state_history table (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_state_history') THEN
    EXECUTE 'ALTER TABLE lead_state_history ENABLE ROW LEVEL SECURITY';

    EXECUTE 'DROP POLICY IF EXISTS "Enable all for authenticated users" ON lead_state_history';
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for service role" ON lead_state_history';

    EXECUTE 'CREATE POLICY "authenticated_users_read_history" ON lead_state_history
             FOR SELECT TO authenticated USING (true)';

    EXECUTE 'CREATE POLICY "service_role_all_access_history" ON lead_state_history
             FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- STEP 7: Fix users table (web app only, no pipeline access)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Admins can view all users" ON users;
DROP POLICY IF EXISTS "Admins can manage users" ON users;
DROP POLICY IF EXISTS "users_manage_own_profile" ON users;
DROP POLICY IF EXISTS "users_view_own_profile" ON users;
DROP POLICY IF EXISTS "users_update_own_profile" ON users;

-- Users can view and update their own profile
CREATE POLICY "users_view_own_profile"
ON users
FOR SELECT
TO authenticated
USING (auth_user_id = auth.uid());

CREATE POLICY "users_update_own_profile"
ON users
FOR UPDATE
TO authenticated
USING (auth_user_id = auth.uid())
WITH CHECK (auth_user_id = auth.uid());

-- ============================================================================
-- STEP 8: Fix user_permissions table
-- ============================================================================
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can view all permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can manage permissions" ON user_permissions;
DROP POLICY IF EXISTS "users_view_own_permissions" ON user_permissions;
DROP POLICY IF EXISTS "users_view_own_permissions_simple" ON user_permissions;

-- Allow users to view their own permissions
CREATE POLICY "users_view_own_permissions"
ON user_permissions
FOR SELECT
TO authenticated
USING (
  user_id = (
    SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1
  )
);

-- ============================================================================
-- STEP 9: Fix roles table
-- ============================================================================
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "All users can view roles" ON roles;
DROP POLICY IF EXISTS "Authenticated users can view roles" ON roles;
DROP POLICY IF EXISTS "Admins can modify roles" ON roles;
DROP POLICY IF EXISTS "authenticated_users_view_roles" ON roles;

-- All authenticated users can view roles
CREATE POLICY "authenticated_users_view_roles"
ON roles
FOR SELECT
TO authenticated
USING (true);

-- ============================================================================
-- STEP 10: Fix lead_access_log table (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_access_log') THEN
    EXECUTE 'ALTER TABLE lead_access_log ENABLE ROW LEVEL SECURITY';

    EXECUTE 'DROP POLICY IF EXISTS "Users can view own access log" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can view all access logs" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "Authenticated can insert access logs" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "users_view_own_access_log" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "authenticated_insert_access_logs" ON lead_access_log';

    EXECUTE 'CREATE POLICY "users_view_own_access_log" ON lead_access_log
             FOR SELECT TO authenticated
             USING (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1))';

    EXECUTE 'CREATE POLICY "authenticated_insert_access_logs" ON lead_access_log
             FOR INSERT TO authenticated WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify:

-- Check entities (should work)
-- SELECT COUNT(*) FROM entities;

-- Check location_leads (should work)
-- SELECT COUNT(*) FROM location_leads;

-- Check events (should work)
-- SELECT COUNT(*) FROM events;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ RLS Policies Updated Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Policy Summary:';
    RAISE NOTICE '   • entities - Service role can write, authenticated can read';
    RAISE NOTICE '   • events - Service role can write, authenticated can read';
    RAISE NOTICE '   • location_leads - Service role can write, authenticated can read';
    RAISE NOTICE '   • raw_events - Service role can write, authenticated can read';
    RAISE NOTICE '   • users - Users can view/edit own profile';
    RAISE NOTICE '   • user_permissions - Users can view own permissions';
    RAISE NOTICE '   • roles - All authenticated users can view';
    RAISE NOTICE '';
    RAISE NOTICE '🐍 Python Pipeline: Can now insert data using service role key';
    RAISE NOTICE '🌐 Web App: Can read all data when authenticated';
    RAISE NOTICE '';
    RAISE NOTICE '🧪 Test your Python pipeline:';
    RAISE NOTICE '   python main.py run';
    RAISE NOTICE '';
END $$;
