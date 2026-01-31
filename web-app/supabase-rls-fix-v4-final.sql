-- ============================================================================
-- RLS FIX V4 - FINAL - Complete Policy Reset
-- ============================================================================
-- This script completely removes ALL RLS policies and recreates them fresh.
-- It handles all previous versions (v1, v2, v3) and partial runs.
-- ============================================================================

-- ============================================================================
-- ENTITIES TABLE
-- ============================================================================
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Drop every possible policy name (from all versions)
DO $$
BEGIN
    -- Drop v1/v2 policy names
    DROP POLICY IF EXISTS "Enable all for authenticated users" ON entities;
    DROP POLICY IF EXISTS "Enable all for service role" ON entities;
    DROP POLICY IF EXISTS "Users can view entities" ON entities;
    DROP POLICY IF EXISTS "Allow all authenticated access" ON entities;
    DROP POLICY IF EXISTS "authenticated_users_full_access" ON entities;
    DROP POLICY IF EXISTS "authenticated_users_access_entities" ON entities;
    DROP POLICY IF EXISTS "authenticated_users_read_entities" ON entities;
    DROP POLICY IF EXISTS "service_role_all_access_entities" ON entities;
    -- Drop v3 policy names
    DROP POLICY IF EXISTS "entities_auth_read" ON entities;
    DROP POLICY IF EXISTS "entities_service_all" ON entities;
END $$;

-- Create final policies
CREATE POLICY "entities_select_auth" ON entities FOR SELECT TO authenticated USING (true);
CREATE POLICY "entities_all_service" ON entities FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- EVENTS TABLE
-- ============================================================================
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "Enable all for authenticated users" ON events;
    DROP POLICY IF EXISTS "Enable all for service role" ON events;
    DROP POLICY IF EXISTS "Users can view events" ON events;
    DROP POLICY IF EXISTS "Allow all authenticated access" ON events;
    DROP POLICY IF EXISTS "authenticated_users_full_access" ON events;
    DROP POLICY IF EXISTS "authenticated_users_access_events" ON events;
    DROP POLICY IF EXISTS "authenticated_users_read_events" ON events;
    DROP POLICY IF EXISTS "service_role_all_access_events" ON events;
    DROP POLICY IF EXISTS "events_auth_read" ON events;
    DROP POLICY IF EXISTS "events_service_all" ON events;
END $$;

CREATE POLICY "events_select_auth" ON events FOR SELECT TO authenticated USING (true);
CREATE POLICY "events_all_service" ON events FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- LOCATION_LEADS TABLE
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
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
    DROP POLICY IF EXISTS "location_leads_auth_read" ON location_leads;
    DROP POLICY IF EXISTS "location_leads_service_all" ON location_leads;
END $$;

CREATE POLICY "location_leads_select_auth" ON location_leads FOR SELECT TO authenticated USING (true);
CREATE POLICY "location_leads_all_service" ON location_leads FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- RAW_EVENTS TABLE
-- ============================================================================
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "Enable all for authenticated users" ON raw_events;
    DROP POLICY IF EXISTS "Enable all for service role" ON raw_events;
    DROP POLICY IF EXISTS "authenticated_users_read_raw_events" ON raw_events;
    DROP POLICY IF EXISTS "service_role_all_access_raw_events" ON raw_events;
    DROP POLICY IF EXISTS "raw_events_auth_read" ON raw_events;
    DROP POLICY IF EXISTS "raw_events_service_all" ON raw_events;
END $$;

CREATE POLICY "raw_events_select_auth" ON raw_events FOR SELECT TO authenticated USING (true);
CREATE POLICY "raw_events_all_service" ON raw_events FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- LEADS_CURRENT TABLE (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'leads_current') THEN
    EXECUTE 'ALTER TABLE leads_current ENABLE ROW LEVEL SECURITY';

    DROP POLICY IF EXISTS "Enable all for authenticated users" ON leads_current;
    DROP POLICY IF EXISTS "Enable all for service role" ON leads_current;
    DROP POLICY IF EXISTS "authenticated_users_read_leads_current" ON leads_current;
    DROP POLICY IF EXISTS "service_role_all_access_leads_current" ON leads_current;
    DROP POLICY IF EXISTS "leads_current_auth_read" ON leads_current;
    DROP POLICY IF EXISTS "leads_current_service_all" ON leads_current;

    EXECUTE 'CREATE POLICY "leads_current_select_auth" ON leads_current FOR SELECT TO authenticated USING (true)';
    EXECUTE 'CREATE POLICY "leads_current_all_service" ON leads_current FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- LEAD_STATE_HISTORY TABLE (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_state_history') THEN
    EXECUTE 'ALTER TABLE lead_state_history ENABLE ROW LEVEL SECURITY';

    DROP POLICY IF EXISTS "Enable all for authenticated users" ON lead_state_history;
    DROP POLICY IF EXISTS "Enable all for service role" ON lead_state_history;
    DROP POLICY IF EXISTS "authenticated_users_read_history" ON lead_state_history;
    DROP POLICY IF EXISTS "service_role_all_access_history" ON lead_state_history;
    DROP POLICY IF EXISTS "lead_state_history_auth_read" ON lead_state_history;
    DROP POLICY IF EXISTS "lead_state_history_service_all" ON lead_state_history;

    EXECUTE 'CREATE POLICY "lead_state_history_select_auth" ON lead_state_history FOR SELECT TO authenticated USING (true)';
    EXECUTE 'CREATE POLICY "lead_state_history_all_service" ON lead_state_history FOR ALL TO service_role USING (true) WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- USERS TABLE (Web app only - users see only their own data)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "Users can view own profile" ON users;
    DROP POLICY IF EXISTS "Users can update own profile" ON users;
    DROP POLICY IF EXISTS "Admins can view all users" ON users;
    DROP POLICY IF EXISTS "Admins can manage users" ON users;
    DROP POLICY IF EXISTS "users_manage_own_profile" ON users;
    DROP POLICY IF EXISTS "users_view_own_profile" ON users;
    DROP POLICY IF EXISTS "users_update_own_profile" ON users;
    DROP POLICY IF EXISTS "users_own_select" ON users;
    DROP POLICY IF EXISTS "users_own_update" ON users;
END $$;

CREATE POLICY "users_select_own" ON users FOR SELECT TO authenticated USING (auth_user_id = auth.uid());
CREATE POLICY "users_update_own" ON users FOR UPDATE TO authenticated USING (auth_user_id = auth.uid()) WITH CHECK (auth_user_id = auth.uid());

-- ============================================================================
-- USER_PERMISSIONS TABLE
-- ============================================================================
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "Users can view own permissions" ON user_permissions;
    DROP POLICY IF EXISTS "Admins can view all permissions" ON user_permissions;
    DROP POLICY IF EXISTS "Admins can manage permissions" ON user_permissions;
    DROP POLICY IF EXISTS "users_view_own_permissions" ON user_permissions;
    DROP POLICY IF EXISTS "users_view_own_permissions_simple" ON user_permissions;
    DROP POLICY IF EXISTS "user_permissions_own_select" ON user_permissions;
END $$;

CREATE POLICY "user_permissions_select_own" ON user_permissions FOR SELECT TO authenticated
USING (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1));

-- ============================================================================
-- ROLES TABLE
-- ============================================================================
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "All users can view roles" ON roles;
    DROP POLICY IF EXISTS "Authenticated users can view roles" ON roles;
    DROP POLICY IF EXISTS "Admins can modify roles" ON roles;
    DROP POLICY IF EXISTS "authenticated_users_view_roles" ON roles;
    DROP POLICY IF EXISTS "roles_auth_read" ON roles;
END $$;

CREATE POLICY "roles_select_all" ON roles FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- LEAD_ACCESS_LOG TABLE (if exists)
-- ============================================================================
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'lead_access_log') THEN
    EXECUTE 'ALTER TABLE lead_access_log ENABLE ROW LEVEL SECURITY';

    DROP POLICY IF EXISTS "Users can view own access log" ON lead_access_log;
    DROP POLICY IF EXISTS "Admins can view all access logs" ON lead_access_log;
    DROP POLICY IF EXISTS "Authenticated can insert access logs" ON lead_access_log;
    DROP POLICY IF EXISTS "users_view_own_access_log" ON lead_access_log;
    DROP POLICY IF EXISTS "authenticated_insert_access_logs" ON lead_access_log;
    DROP POLICY IF EXISTS "lead_access_log_own_select" ON lead_access_log;
    DROP POLICY IF EXISTS "lead_access_log_auth_insert" ON lead_access_log;

    EXECUTE 'CREATE POLICY "lead_access_log_select_own" ON lead_access_log FOR SELECT TO authenticated
             USING (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1))';
    EXECUTE 'CREATE POLICY "lead_access_log_insert_all" ON lead_access_log FOR INSERT TO authenticated WITH CHECK (true)';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- List all policies to verify
DO $$
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'CURRENT RLS POLICIES:';
    RAISE NOTICE '========================================';
    FOR r IN
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE tablename IN ('entities', 'events', 'location_leads', 'raw_events',
                           'leads_current', 'lead_state_history', 'users',
                           'user_permissions', 'roles', 'lead_access_log')
        ORDER BY tablename, policyname
    LOOP
        RAISE NOTICE '  % : %', r.tablename, r.policyname;
    END LOOP;
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '██████████████████████████████████████████████████████████';
    RAISE NOTICE '█                                                        █';
    RAISE NOTICE '█  ✅ RLS POLICIES SUCCESSFULLY CONFIGURED (V4 FINAL)   █';
    RAISE NOTICE '█                                                        █';
    RAISE NOTICE '██████████████████████████████████████████████████████████';
    RAISE NOTICE '';
    RAISE NOTICE '📊 DATA TABLES:';
    RAISE NOTICE '   ✓ entities - Service role: ALL, Auth users: SELECT';
    RAISE NOTICE '   ✓ events - Service role: ALL, Auth users: SELECT';
    RAISE NOTICE '   ✓ location_leads - Service role: ALL, Auth users: SELECT';
    RAISE NOTICE '   ✓ raw_events - Service role: ALL, Auth users: SELECT';
    RAISE NOTICE '';
    RAISE NOTICE '👤 USER TABLES:';
    RAISE NOTICE '   ✓ users - Users see only their own data';
    RAISE NOTICE '   ✓ user_permissions - Users see only their own';
    RAISE NOTICE '   ✓ roles - All auth users can view';
    RAISE NOTICE '';
    RAISE NOTICE '🐍 NEXT STEP: Run your Python pipeline';
    RAISE NOTICE '   cd /path/to/leads_factory';
    RAISE NOTICE '   python main.py run';
    RAISE NOTICE '';
    RAISE NOTICE '🌐 WEB APP: http://localhost:3000/leads';
    RAISE NOTICE '';
END $$;
