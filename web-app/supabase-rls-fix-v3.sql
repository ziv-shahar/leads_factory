-- ============================================================================
-- RLS FIX V3 - Complete Reset and Reconfiguration
-- ============================================================================
-- This script completely resets all RLS policies and creates fresh ones.
-- It handles conflicts from previous migration attempts.
--
-- Purpose: Allow both web app (authenticated users) and Python pipeline
-- (service role) to work correctly.
-- ============================================================================

-- ============================================================================
-- STEP 1: ENTITIES TABLE - Complete Reset
-- ============================================================================
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Enable all for authenticated users" ON entities;
DROP POLICY IF EXISTS "Enable all for service role" ON entities;
DROP POLICY IF EXISTS "Users can view entities" ON entities;
DROP POLICY IF EXISTS "Allow all authenticated access" ON entities;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON entities;
DROP POLICY IF EXISTS "authenticated_users_access_entities" ON entities;
DROP POLICY IF EXISTS "authenticated_users_read_entities" ON entities;
DROP POLICY IF EXISTS "service_role_all_access_entities" ON entities;

-- Create fresh policies
CREATE POLICY "entities_auth_read"
ON entities FOR SELECT TO authenticated
USING (true);

CREATE POLICY "entities_service_all"
ON entities FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- STEP 2: EVENTS TABLE - Complete Reset
-- ============================================================================
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Enable all for authenticated users" ON events;
DROP POLICY IF EXISTS "Enable all for service role" ON events;
DROP POLICY IF EXISTS "Users can view events" ON events;
DROP POLICY IF EXISTS "Allow all authenticated access" ON events;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON events;
DROP POLICY IF EXISTS "authenticated_users_access_events" ON events;
DROP POLICY IF EXISTS "authenticated_users_read_events" ON events;
DROP POLICY IF EXISTS "service_role_all_access_events" ON events;

-- Create fresh policies
CREATE POLICY "events_auth_read"
ON events FOR SELECT TO authenticated
USING (true);

CREATE POLICY "events_service_all"
ON events FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- STEP 3: LOCATION_LEADS TABLE - Complete Reset
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;
DROP POLICY IF EXISTS "Enable all for service role" ON location_leads;
DROP POLICY IF EXISTS "Admins see all location leads" ON location_leads;
DROP POLICY IF EXISTS "Users see allowed state leads" ON location_leads;
DROP POLICY IF EXISTS "Users can view location leads" ON location_leads;
DROP POLICY IF EXISTS "Allow all authenticated access" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_access_all_leads" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_read_leads" ON location_leads;
DROP POLICY IF EXISTS "service_role_all_access_leads" ON location_leads;

-- Create fresh policies
CREATE POLICY "location_leads_auth_read"
ON location_leads FOR SELECT TO authenticated
USING (true);

CREATE POLICY "location_leads_service_all"
ON location_leads FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- STEP 4: RAW_EVENTS TABLE - Complete Reset
-- ============================================================================
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Enable all for authenticated users" ON raw_events;
DROP POLICY IF EXISTS "Enable all for service role" ON raw_events;
DROP POLICY IF EXISTS "authenticated_users_read_raw_events" ON raw_events;
DROP POLICY IF EXISTS "service_role_all_access_raw_events" ON raw_events;

-- Create fresh policies
CREATE POLICY "raw_events_auth_read"
ON raw_events FOR SELECT TO authenticated
USING (true);

CREATE POLICY "raw_events_service_all"
ON raw_events FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- STEP 5: LEADS_CURRENT TABLE (if exists) - Complete Reset
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'leads_current') THEN
    EXECUTE 'ALTER TABLE leads_current ENABLE ROW LEVEL SECURITY';

    -- Drop all variations
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for authenticated users" ON leads_current';
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for service role" ON leads_current';
    EXECUTE 'DROP POLICY IF EXISTS "authenticated_users_read_leads_current" ON leads_current';
    EXECUTE 'DROP POLICY IF EXISTS "service_role_all_access_leads_current" ON leads_current';

    -- Create fresh policies
    EXECUTE 'CREATE POLICY "leads_current_auth_read" ON leads_current
             FOR SELECT TO authenticated USING (true)';

    EXECUTE 'CREATE POLICY "leads_current_service_all" ON leads_current
             FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- STEP 6: LEAD_STATE_HISTORY TABLE (if exists) - Complete Reset
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_state_history') THEN
    EXECUTE 'ALTER TABLE lead_state_history ENABLE ROW LEVEL SECURITY';

    -- Drop all variations
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for authenticated users" ON lead_state_history';
    EXECUTE 'DROP POLICY IF EXISTS "Enable all for service role" ON lead_state_history';
    EXECUTE 'DROP POLICY IF EXISTS "authenticated_users_read_history" ON lead_state_history';
    EXECUTE 'DROP POLICY IF EXISTS "service_role_all_access_history" ON lead_state_history';

    -- Create fresh policies
    EXECUTE 'CREATE POLICY "lead_state_history_auth_read" ON lead_state_history
             FOR SELECT TO authenticated USING (true)';

    EXECUTE 'CREATE POLICY "lead_state_history_service_all" ON lead_state_history
             FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- STEP 7: USERS TABLE - Complete Reset (Web app only)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Admins can view all users" ON users;
DROP POLICY IF EXISTS "Admins can manage users" ON users;
DROP POLICY IF EXISTS "users_manage_own_profile" ON users;
DROP POLICY IF EXISTS "users_view_own_profile" ON users;
DROP POLICY IF EXISTS "users_update_own_profile" ON users;

-- Create fresh policies (users only see their own data)
CREATE POLICY "users_own_select"
ON users FOR SELECT TO authenticated
USING (auth_user_id = auth.uid());

CREATE POLICY "users_own_update"
ON users FOR UPDATE TO authenticated
USING (auth_user_id = auth.uid())
WITH CHECK (auth_user_id = auth.uid());

-- ============================================================================
-- STEP 8: USER_PERMISSIONS TABLE - Complete Reset
-- ============================================================================
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "Users can view own permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can view all permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can manage permissions" ON user_permissions;
DROP POLICY IF EXISTS "users_view_own_permissions" ON user_permissions;
DROP POLICY IF EXISTS "users_view_own_permissions_simple" ON user_permissions;

-- Create fresh policy
CREATE POLICY "user_permissions_own_select"
ON user_permissions FOR SELECT TO authenticated
USING (
  user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1)
);

-- ============================================================================
-- STEP 9: ROLES TABLE - Complete Reset
-- ============================================================================
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Drop ALL possible policy variations
DROP POLICY IF EXISTS "All users can view roles" ON roles;
DROP POLICY IF EXISTS "Authenticated users can view roles" ON roles;
DROP POLICY IF EXISTS "Admins can modify roles" ON roles;
DROP POLICY IF EXISTS "authenticated_users_view_roles" ON roles;

-- Create fresh policy
CREATE POLICY "roles_auth_read"
ON roles FOR SELECT TO authenticated
USING (true);

-- ============================================================================
-- STEP 10: LEAD_ACCESS_LOG TABLE (if exists) - Complete Reset
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_access_log') THEN
    EXECUTE 'ALTER TABLE lead_access_log ENABLE ROW LEVEL SECURITY';

    -- Drop all variations
    EXECUTE 'DROP POLICY IF EXISTS "Users can view own access log" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "Admins can view all access logs" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "Authenticated can insert access logs" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "users_view_own_access_log" ON lead_access_log';
    EXECUTE 'DROP POLICY IF EXISTS "authenticated_insert_access_logs" ON lead_access_log';

    -- Create fresh policies
    EXECUTE 'CREATE POLICY "lead_access_log_own_select" ON lead_access_log
             FOR SELECT TO authenticated
             USING (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1))';

    EXECUTE 'CREATE POLICY "lead_access_log_auth_insert" ON lead_access_log
             FOR INSERT TO authenticated WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Test queries (uncomment to run):
-- SELECT COUNT(*) FROM entities;
-- SELECT COUNT(*) FROM events;
-- SELECT COUNT(*) FROM location_leads;
-- SELECT COUNT(*) FROM raw_events;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅✅✅ RLS POLICIES RESET AND CONFIGURED SUCCESSFULLY ✅✅✅';
    RAISE NOTICE '';
    RAISE NOTICE '📊 DATA TABLES (Pipeline can write, Web can read):';
    RAISE NOTICE '   ✓ entities';
    RAISE NOTICE '   ✓ events';
    RAISE NOTICE '   ✓ location_leads';
    RAISE NOTICE '   ✓ raw_events';
    RAISE NOTICE '   ✓ leads_current (if exists)';
    RAISE NOTICE '   ✓ lead_state_history (if exists)';
    RAISE NOTICE '';
    RAISE NOTICE '👤 USER TABLES (Web app only):';
    RAISE NOTICE '   ✓ users';
    RAISE NOTICE '   ✓ user_permissions';
    RAISE NOTICE '   ✓ roles';
    RAISE NOTICE '   ✓ lead_access_log (if exists)';
    RAISE NOTICE '';
    RAISE NOTICE '🐍 PYTHON PIPELINE: Ready to run!';
    RAISE NOTICE '   → python main.py run';
    RAISE NOTICE '';
    RAISE NOTICE '🌐 WEB APP: Ready to display data!';
    RAISE NOTICE '   → http://localhost:3000/leads';
    RAISE NOTICE '';
END $$;
