-- ============================================================================
-- User Management & Permissions Migration
-- ============================================================================
-- Run this script in Supabase SQL Editor to add user management tables
-- This enables authentication, role-based access control, and usage tracking
-- ============================================================================

-- ============================================================================
-- Table: Users
-- ============================================================================
-- Note: This table links to Supabase Auth (auth.users)
-- You can also use this without Supabase Auth by uncommenting password_hash

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Basic info
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,

    -- Authentication (uncomment if using custom auth instead of Supabase Auth)
    -- password_hash VARCHAR(255),

    -- Account status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Profile
    avatar_url TEXT,
    phone VARCHAR(50),
    title VARCHAR(100),  -- "Sales Rep", "Manager", "Executive"
    department VARCHAR(100),

    -- Tracking
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Link to Supabase Auth (recommended approach)
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_auth_user_id ON users(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Comments
COMMENT ON TABLE users IS 'Application users with profiles and metadata';
COMMENT ON COLUMN users.auth_user_id IS 'Reference to Supabase Auth user (recommended)';
COMMENT ON COLUMN users.is_active IS 'Soft delete flag - inactive users cannot login';
COMMENT ON COLUMN users.is_verified IS 'Email verification status';

-- ============================================================================
-- Table: Roles
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Permissions blueprint (JSONB for flexibility)
    permissions JSONB NOT NULL DEFAULT '{}',
    -- Example structure:
    -- {
    --   "can_view_leads": true,
    --   "can_export_leads": true,
    --   "can_view_all_states": false,
    --   "can_manage_users": false,
    --   "can_view_analytics": true,
    --   "max_daily_leads": 50
    -- }

    created_at TIMESTAMP DEFAULT NOW()
);

-- Comments
COMMENT ON TABLE roles IS 'Role definitions with permission blueprints';
COMMENT ON COLUMN roles.permissions IS 'JSONB object defining role capabilities and limits';

-- ============================================================================
-- Seed Default Roles
-- ============================================================================

INSERT INTO roles (name, display_name, description, permissions) VALUES
(
    'admin',
    'Administrator',
    'Full system access including user management',
    '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": true, "can_manage_users": true, "can_view_analytics": true, "can_manage_settings": true, "max_daily_leads": -1}'::jsonb
),
(
    'manager',
    'Manager',
    'Manage team and assigned territories with analytics access',
    '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": true, "can_manage_settings": false, "max_daily_leads": 200}'::jsonb
),
(
    'sales_rep',
    'Sales Representative',
    'View and export assigned leads within daily limits',
    '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": false, "can_manage_settings": false, "max_daily_leads": 50}'::jsonb
),
(
    'viewer',
    'Viewer',
    'Read-only access with limited export capabilities',
    '{"can_view_leads": true, "can_export_leads": false, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": false, "can_manage_settings": false, "max_daily_leads": 10}'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- Table: User Permissions (Individual User Settings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,

    -- Territory restrictions (state filtering)
    allowed_states TEXT[],  -- ["FL", "CA", "TX"] or NULL for all states

    -- Daily limits (overrides role default if set)
    max_daily_leads INTEGER,  -- NULL = use role default, -1 = unlimited, N = specific limit

    -- Custom permission overrides (overrides role permissions)
    custom_permissions JSONB DEFAULT '{}',
    -- Example: {"can_export_leads": false}  -- Override role setting

    -- Date restrictions (optional)
    access_starts_at TIMESTAMP,
    access_expires_at TIMESTAMP,

    -- Metadata
    assigned_by UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- One permission record per user
    CONSTRAINT uq_user_permissions_user_id UNIQUE (user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_role_id ON user_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_allowed_states ON user_permissions USING GIN(allowed_states);

-- Comments
COMMENT ON TABLE user_permissions IS 'Per-user permission settings and territory assignments';
COMMENT ON COLUMN user_permissions.allowed_states IS 'Array of 2-letter state codes user can access, NULL = all states';
COMMENT ON COLUMN user_permissions.max_daily_leads IS 'Override role default: NULL = use role, -1 = unlimited, N = specific';
COMMENT ON COLUMN user_permissions.custom_permissions IS 'JSONB overrides for specific permissions';

-- ============================================================================
-- Table: Lead Access Log (Usage Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lead_access_log (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_lead_id INTEGER REFERENCES location_leads(id) ON DELETE SET NULL,
    entity_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,

    -- Access details
    access_type VARCHAR(50) NOT NULL,  -- "view", "export", "detail_view"
    state VARCHAR(2),

    -- Tracking metadata
    accessed_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,

    -- Optional: Export format for exports
    export_format VARCHAR(20)  -- "csv", "json", "pdf"
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_lead_access_user_date ON lead_access_log(user_id, accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_access_date ON lead_access_log(accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_access_entity ON lead_access_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_lead_access_type ON lead_access_log(access_type);

-- Comments
COMMENT ON TABLE lead_access_log IS 'Audit log of all lead access for compliance and usage tracking';
COMMENT ON COLUMN lead_access_log.access_type IS 'Type of access: view, export, detail_view';

-- ============================================================================
-- View: Daily Lead Usage (For Quota Tracking)
-- ============================================================================

CREATE OR REPLACE VIEW daily_lead_usage AS
SELECT
    user_id,
    DATE(accessed_at) as access_date,
    COUNT(*) as total_accesses,
    COUNT(DISTINCT entity_id) as unique_entities_accessed,
    COUNT(DISTINCT location_lead_id) as unique_location_leads_accessed,
    COUNT(*) FILTER (WHERE access_type = 'view') as views,
    COUNT(*) FILTER (WHERE access_type = 'export') as exports,
    COUNT(*) FILTER (WHERE access_type = 'detail_view') as detail_views
FROM lead_access_log
WHERE access_type IN ('view', 'export', 'detail_view')
GROUP BY user_id, DATE(accessed_at);

COMMENT ON VIEW daily_lead_usage IS 'Daily aggregated usage statistics per user for quota enforcement';

-- ============================================================================
-- Table: User Sessions (Optional - for custom auth)
-- ============================================================================
-- Only needed if NOT using Supabase Auth
-- Comment out this section if using Supabase Auth

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,

    -- Session metadata
    ip_address INET,
    user_agent TEXT,

    -- Expiration
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);

-- Auto-cleanup expired sessions (run daily)
-- Can be set up as a cron job or Supabase function

COMMENT ON TABLE user_sessions IS 'Session tracking (only needed for custom auth, not Supabase Auth)';

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_access_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS Policies: Users Table
-- ============================================================================

-- Users can view their own profile
CREATE POLICY "Users can view own profile" ON users
FOR SELECT
USING (auth.uid() = auth_user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON users
FOR UPDATE
USING (auth.uid() = auth_user_id);

-- Admins can view all users
CREATE POLICY "Admins can view all users" ON users
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- Admins can manage all users
CREATE POLICY "Admins can manage users" ON users
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- ============================================================================
-- RLS Policies: Roles Table
-- ============================================================================

-- All authenticated users can view roles
CREATE POLICY "Authenticated users can view roles" ON roles
FOR SELECT
TO authenticated
USING (true);

-- Only admins can modify roles
CREATE POLICY "Admins can modify roles" ON roles
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- ============================================================================
-- RLS Policies: User Permissions Table
-- ============================================================================

-- Users can view their own permissions
CREATE POLICY "Users can view own permissions" ON user_permissions
FOR SELECT
USING (
    user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
);

-- Admins can view all permissions
CREATE POLICY "Admins can view all permissions" ON user_permissions
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- Admins can manage permissions
CREATE POLICY "Admins can manage permissions" ON user_permissions
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- ============================================================================
-- RLS Policies: Lead Access Log
-- ============================================================================

-- Users can view their own access log
CREATE POLICY "Users can view own access log" ON lead_access_log
FOR SELECT
USING (
    user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
);

-- Admins can view all access logs
CREATE POLICY "Admins can view all access logs" ON lead_access_log
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
    )
);

-- System can insert access logs (for API logging)
CREATE POLICY "Authenticated can insert access logs" ON lead_access_log
FOR INSERT
TO authenticated
WITH CHECK (true);

-- ============================================================================
-- RLS Policies: Location Leads (Updated for User Permissions)
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users see allowed states only" ON location_leads;
DROP POLICY IF EXISTS "Admins see all leads" ON location_leads;
DROP POLICY IF EXISTS "Enable all for authenticated users" ON location_leads;

-- Policy 1: Admins see everything
CREATE POLICY "Admins see all location leads" ON location_leads
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN roles r ON up.role_id = r.id
        WHERE up.user_id = (SELECT id FROM users WHERE auth_user_id = auth.uid())
        AND r.name = 'admin'
        AND (r.permissions->>'can_view_all_states')::boolean = true
    )
);

-- Policy 2: Users see leads in their allowed states
CREATE POLICY "Users see allowed state leads" ON location_leads
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM user_permissions up
        JOIN users u ON up.user_id = u.id
        WHERE u.auth_user_id = auth.uid()
        AND u.is_active = true
        AND (
            up.allowed_states IS NULL  -- NULL = access all states
            OR location_leads.state = ANY(up.allowed_states)  -- State is in allowed list
        )
        AND (
            up.access_expires_at IS NULL  -- No expiration
            OR up.access_expires_at > NOW()  -- Not expired
        )
    )
);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to get effective permissions for a user
CREATE OR REPLACE FUNCTION get_user_permissions(p_auth_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_permissions JSONB;
    v_role_permissions JSONB;
    v_custom_permissions JSONB;
BEGIN
    -- Get role permissions and custom overrides
    SELECT
        COALESCE(r.permissions, '{}'::jsonb) || COALESCE(up.custom_permissions, '{}'::jsonb),
        up.allowed_states,
        COALESCE(up.max_daily_leads, (r.permissions->>'max_daily_leads')::integer)
    INTO v_role_permissions
    FROM users u
    JOIN user_permissions up ON u.id = up.user_id
    JOIN roles r ON up.role_id = r.id
    WHERE u.auth_user_id = p_auth_user_id
    AND u.is_active = true;

    RETURN COALESCE(v_role_permissions, '{}'::jsonb);
END;
$$;

COMMENT ON FUNCTION get_user_permissions IS 'Get merged permissions (role + custom overrides) for a user';

-- Function to check if user has reached daily limit
CREATE OR REPLACE FUNCTION check_daily_limit(p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_limit INTEGER;
    v_used INTEGER;
BEGIN
    -- Get user's daily limit
    SELECT COALESCE(
        up.max_daily_leads,
        (r.permissions->>'max_daily_leads')::integer
    )
    INTO v_limit
    FROM user_permissions up
    JOIN roles r ON up.role_id = r.id
    WHERE up.user_id = p_user_id;

    -- -1 means unlimited
    IF v_limit = -1 THEN
        RETURN true;
    END IF;

    -- Count today's usage
    SELECT COALESCE(total_accesses, 0)
    INTO v_used
    FROM daily_lead_usage
    WHERE user_id = p_user_id
    AND access_date = CURRENT_DATE;

    RETURN v_used < v_limit;
END;
$$;

COMMENT ON FUNCTION check_daily_limit IS 'Check if user has remaining quota for today';

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply to user_permissions table
DROP TRIGGER IF EXISTS update_user_permissions_updated_at ON user_permissions;
CREATE TRIGGER update_user_permissions_updated_at
    BEFORE UPDATE ON user_permissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Trigger: Auto-create user record when Supabase Auth user signs up
-- ============================================================================

CREATE OR REPLACE FUNCTION handle_new_auth_user()
RETURNS TRIGGER AS $$
DECLARE
    v_sales_rep_role_id INTEGER;
BEGIN
    -- Get sales_rep role ID
    SELECT id INTO v_sales_rep_role_id FROM roles WHERE name = 'sales_rep' LIMIT 1;

    -- Create user record
    INSERT INTO public.users (auth_user_id, email, full_name, is_verified)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
        NEW.email_confirmed_at IS NOT NULL
    );

    -- Create default permissions (sales_rep role, no state restrictions)
    INSERT INTO public.user_permissions (user_id, role_id, allowed_states, max_daily_leads)
    VALUES (
        (SELECT id FROM public.users WHERE auth_user_id = NEW.id),
        v_sales_rep_role_id,
        NULL,  -- NULL = all states
        NULL   -- NULL = use role default
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_auth_user();

-- ============================================================================
-- Success Message
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ User Management Migration Complete!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Tables Created:';
    RAISE NOTICE '   • users - Application user profiles';
    RAISE NOTICE '   • roles - Role definitions (4 default roles seeded)';
    RAISE NOTICE '   • user_permissions - Per-user settings and territory assignments';
    RAISE NOTICE '   • lead_access_log - Audit trail of lead access';
    RAISE NOTICE '   • user_sessions - Session management (optional)';
    RAISE NOTICE '';
    RAISE NOTICE '👀 Views Created:';
    RAISE NOTICE '   • daily_lead_usage - Daily usage statistics for quota tracking';
    RAISE NOTICE '';
    RAISE NOTICE '🔐 RLS Policies:';
    RAISE NOTICE '   • Users can view/edit own profile';
    RAISE NOTICE '   • Admins can manage all users and permissions';
    RAISE NOTICE '   • Location leads filtered by user state permissions';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Default Roles:';
    RAISE NOTICE '   • admin - Full access (unlimited leads)';
    RAISE NOTICE '   • manager - Team management (200 leads/day)';
    RAISE NOTICE '   • sales_rep - Standard access (50 leads/day)';
    RAISE NOTICE '   • viewer - Read-only (10 leads/day)';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ Auto-Triggers:';
    RAISE NOTICE '   • New Supabase Auth users automatically get sales_rep role';
    RAISE NOTICE '   • updated_at timestamps auto-maintained';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Next Steps:';
    RAISE NOTICE '   1. Create your first admin user in Supabase Auth';
    RAISE NOTICE '   2. Update their role to admin in user_permissions table';
    RAISE NOTICE '   3. Start building the Next.js frontend!';
    RAISE NOTICE '';
END $$;
