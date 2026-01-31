-- ============================================================================
-- FIX: Infinite Recursion in RLS Policies
-- ============================================================================
-- This script fixes the circular reference issue in Row Level Security policies
-- that was preventing data from loading in the dashboard.
--
-- ISSUE: The location_leads RLS policy was joining user_permissions to users table:
--   user_permissions.user_id -> users.id -> users.auth_user_id = auth.uid()
-- But the users table has its own RLS policies, creating infinite recursion.
--
-- SOLUTION: Simplify policies to use auth.uid() directly or avoid the users table join.
-- This temporary fix allows all authenticated users to access all data for testing.
-- ============================================================================

-- ============================================================================
-- STEP 1: Fix location_leads table
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Drop all existing policies that might have circular references
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;
DROP POLICY IF EXISTS "Admins see all location leads" ON location_leads;
DROP POLICY IF EXISTS "Users see allowed state leads" ON location_leads;
DROP POLICY IF EXISTS "Users can view location leads" ON location_leads;
DROP POLICY IF EXISTS "Allow all authenticated access" ON location_leads;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON location_leads;

-- Create simple policy for authenticated users (no user table join)
-- This allows all authenticated users to see all location leads
CREATE POLICY "authenticated_users_access_all_leads"
ON location_leads
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 2: Fix entities table
-- ============================================================================
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON entities;
DROP POLICY IF EXISTS "Users can view entities" ON entities;
DROP POLICY IF EXISTS "Allow all authenticated access" ON entities;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON entities;

-- Create simple policy for authenticated users
CREATE POLICY "authenticated_users_access_entities"
ON entities
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 3: Fix events table
-- ============================================================================
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON events;
DROP POLICY IF EXISTS "Users can view events" ON events;
DROP POLICY IF EXISTS "Allow all authenticated access" ON events;
DROP POLICY IF EXISTS "authenticated_users_full_access" ON events;

-- Create simple policy for authenticated users
CREATE POLICY "authenticated_users_access_events"
ON events
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 4: Fix users table (remove circular dependencies)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies that cause circular references
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Admins can view all users" ON users;
DROP POLICY IF EXISTS "Admins can manage users" ON users;
DROP POLICY IF EXISTS "users_manage_own_profile" ON users;

-- Users can view and update their own profile using auth.uid() directly
-- This avoids any joins to user_permissions
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
-- STEP 5: Fix user_permissions table
-- ============================================================================
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can view all permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can manage permissions" ON user_permissions;
DROP POLICY IF EXISTS "users_view_own_permissions" ON user_permissions;

-- Allow users to view their own permissions without joining to users table
-- Get user_id directly from a subquery
CREATE POLICY "users_view_own_permissions_simple"
ON user_permissions
FOR SELECT
TO authenticated
USING (
  user_id = (
    SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1
  )
);

-- ============================================================================
-- STEP 6: Fix roles table
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
-- STEP 7: Fix lead_access_log table
-- ============================================================================
ALTER TABLE lead_access_log ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own access log" ON lead_access_log;
DROP POLICY IF EXISTS "Admins can view all access logs" ON lead_access_log;
DROP POLICY IF EXISTS "Authenticated can insert access logs" ON lead_access_log;

-- Users can view their own access log
CREATE POLICY "users_view_own_access_log"
ON lead_access_log
FOR SELECT
TO authenticated
USING (
  user_id = (
    SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1
  )
);

-- Anyone can insert access logs (for tracking)
CREATE POLICY "authenticated_insert_access_logs"
ON lead_access_log
FOR INSERT
TO authenticated
WITH CHECK (true);

-- ============================================================================
-- STEP 8: Fix user_sessions table (if exists)
-- ============================================================================
-- Check if table exists and enable RLS
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'user_sessions') THEN
    EXECUTE 'ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY';

    -- Drop existing policies
    EXECUTE 'DROP POLICY IF EXISTS "Users can view own sessions" ON user_sessions';

    -- Create simple policy
    EXECUTE 'CREATE POLICY "users_view_own_sessions" ON user_sessions
             FOR ALL TO authenticated
             USING (user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid() LIMIT 1))';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries to verify the fix worked:

-- Check that you can now query location_leads
-- SELECT COUNT(*) FROM location_leads;

-- Check that you can query with joins
-- SELECT ll.*, e.canonical_name
-- FROM location_leads ll
-- JOIN entities e ON ll.entity_id = e.id
-- LIMIT 10;

-- Check events
-- SELECT COUNT(*) FROM events;

-- Check your user record
-- SELECT * FROM users WHERE auth_user_id = auth.uid();

-- Check your permissions
-- SELECT up.*, r.name as role_name
-- FROM user_permissions up
-- JOIN roles r ON up.role_id = r.id
-- WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid());

-- ============================================================================
-- IMPORTANT NOTES
-- ============================================================================
-- ⚠️  This is a TEMPORARY fix for testing purposes!
--
-- Current behavior:
-- - All authenticated users can see ALL location_leads (no state filtering)
-- - All authenticated users can see ALL entities
-- - All authenticated users can see ALL events
-- - Users can only see their own profile and permissions
--
-- This is fine for:
-- ✅ Initial development and testing
-- ✅ Single-user applications
-- ✅ Admin-only dashboards
--
-- For production with multiple users and state-based restrictions, you should:
-- 1. Add an auth_user_id column directly to user_permissions table for faster lookups
-- 2. Update the location_leads policy to use user_permissions.auth_user_id directly
-- 3. Avoid any joins to the users table in RLS policies
--
-- Example for future state-based access control:
--
-- -- Add column to user_permissions for faster lookups
-- ALTER TABLE user_permissions ADD COLUMN IF NOT EXISTS auth_user_id UUID;
-- UPDATE user_permissions up SET auth_user_id = u.auth_user_id
--   FROM users u WHERE up.user_id = u.id;
-- CREATE INDEX idx_user_permissions_auth_user_id ON user_permissions(auth_user_id);
--
-- -- Then create policy without joining to users table:
-- CREATE POLICY "users_see_allowed_state_leads"
-- ON location_leads FOR SELECT TO authenticated
-- USING (
--   EXISTS (
--     SELECT 1 FROM user_permissions
--     WHERE auth_user_id = auth.uid()
--     AND (allowed_states IS NULL OR location_leads.state = ANY(allowed_states))
--   )
-- );
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ RLS Fix Applied Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Fixed Tables:';
    RAISE NOTICE '   • location_leads - All authenticated users can access';
    RAISE NOTICE '   • entities - All authenticated users can access';
    RAISE NOTICE '   • events - All authenticated users can access';
    RAISE NOTICE '   • users - Users can view/edit own profile';
    RAISE NOTICE '   • user_permissions - Users can view own permissions';
    RAISE NOTICE '   • roles - All authenticated users can view';
    RAISE NOTICE '   • lead_access_log - Users can view own logs';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT: This allows ALL authenticated users to see ALL data.';
    RAISE NOTICE '   This is fine for testing, but implement proper access control for production.';
    RAISE NOTICE '';
    RAISE NOTICE '🧪 Test the fix:';
    RAISE NOTICE '   SELECT COUNT(*) FROM location_leads;';
    RAISE NOTICE '';
END $$;
