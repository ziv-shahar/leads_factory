-- ============================================================================
-- FIX: Infinite Recursion in RLS Policies
-- ============================================================================
-- This script fixes the circular reference issue in Row Level Security policies
-- that was preventing data from loading in the dashboard.
--
-- ISSUE: The location_leads RLS policy was joining to the users table,
-- which itself has RLS policies, creating infinite recursion.
--
-- SOLUTION: Simplify policies to use auth.uid() directly without joining
-- to the users table. This temporary fix allows all authenticated users
-- to access all data for initial testing.
-- ============================================================================

-- 1. Fix location_leads table
-- ============================================================================
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Drop all existing policies that might have circular references
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;
DROP POLICY IF EXISTS "Admins see all location leads" ON location_leads;
DROP POLICY IF EXISTS "Users see allowed state leads" ON location_leads;
DROP POLICY IF EXISTS "Users can view location leads" ON location_leads;
DROP POLICY IF EXISTS "Allow all authenticated access" ON location_leads;

-- Create simple policy for authenticated users (no user table join)
CREATE POLICY "authenticated_users_full_access"
ON location_leads
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- 2. Fix entities table
-- ============================================================================
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON entities;
DROP POLICY IF EXISTS "Users can view entities" ON entities;
DROP POLICY IF EXISTS "Allow all authenticated access" ON entities;

-- Create simple policy for authenticated users
CREATE POLICY "authenticated_users_full_access"
ON entities
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- 3. Fix events table
-- ============================================================================
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Enable all for authenticated users" ON events;
DROP POLICY IF EXISTS "Users can view events" ON events;
DROP POLICY IF EXISTS "Allow all authenticated access" ON events;

-- Create simple policy for authenticated users
CREATE POLICY "authenticated_users_full_access"
ON events
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- 4. Fix user_permissions table (if it has RLS issues)
-- ============================================================================
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own permissions" ON user_permissions;
DROP POLICY IF EXISTS "Admins can manage permissions" ON user_permissions;

-- Allow users to view their own permissions
CREATE POLICY "users_view_own_permissions"
ON user_permissions
FOR SELECT
TO authenticated
USING (
  auth_user_id = auth.uid()
);

-- 5. Fix users table (simplified to avoid circular references)
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Admins can view all users" ON users;

-- Users can view and update their own profile using auth.uid() directly
CREATE POLICY "users_manage_own_profile"
ON users
FOR ALL
TO authenticated
USING (auth_user_id = auth.uid())
WITH CHECK (auth_user_id = auth.uid());

-- 6. Fix roles table
-- ============================================================================
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "All users can view roles" ON roles;

-- All authenticated users can view roles
CREATE POLICY "authenticated_users_view_roles"
ON roles
FOR SELECT
TO authenticated
USING (true);

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

-- ============================================================================
-- NOTES FOR PRODUCTION
-- ============================================================================
-- This is a TEMPORARY fix for testing. For production, you should:
--
-- 1. Implement proper state-based access control without circular references
-- 2. Use a materialized view or cache for user permissions
-- 3. Consider using Postgres functions to check permissions
-- 4. Test thoroughly with different user roles
--
-- Example of a better approach for state-based access (future implementation):
--
-- CREATE POLICY "users_see_allowed_state_leads"
-- ON location_leads
-- FOR SELECT
-- TO authenticated
-- USING (
--   EXISTS (
--     SELECT 1 FROM user_permissions
--     WHERE auth_user_id = auth.uid()
--     AND (
--       allowed_states IS NULL
--       OR location_leads.state = ANY(allowed_states)
--     )
--   )
-- );
--
-- This avoids joining to the users table by using auth_user_id directly
-- from the user_permissions table.
-- ============================================================================
