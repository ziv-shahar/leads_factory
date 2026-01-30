# Database Migrations

This directory contains SQL migration scripts for the Lead Intelligence Platform.

## Available Migrations

### 1. Location Leads Table
**File**: `../add_location_leads_table.sql`
**Status**: ✅ Should already be applied
**Purpose**: Per-state lead tracking

### 2. User Management Tables (NEW)
**File**: `add_user_management_tables.sql`
**Status**: ⏳ Ready to apply
**Purpose**: Authentication, permissions, and usage tracking

## Running the User Management Migration

### Step 1: Access Supabase SQL Editor

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Navigate to **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Run the Migration

1. Open `add_user_management_tables.sql` in a text editor
2. Copy the entire contents
3. Paste into Supabase SQL Editor
4. Click **Run** (or press `Ctrl+Enter`)

### Step 3: Verify Success

You should see output like:

```
✅ User Management Migration Complete!

📊 Tables Created:
   • users - Application user profiles
   • roles - Role definitions (4 default roles seeded)
   • user_permissions - Per-user settings and territory assignments
   • lead_access_log - Audit trail of lead access
   • user_sessions - Session management (optional)

👀 Views Created:
   • daily_lead_usage - Daily usage statistics for quota tracking

🔐 RLS Policies:
   • Users can view/edit own profile
   • Admins can manage all users and permissions
   • Location leads filtered by user state permissions

🎯 Default Roles:
   • admin - Full access (unlimited leads)
   • manager - Team management (200 leads/day)
   • sales_rep - Standard access (50 leads/day)
   • viewer - Read-only (10 leads/day)
```

### Step 4: Verify Tables Exist

Run this query to verify all tables were created:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'roles', 'user_permissions', 'lead_access_log', 'user_sessions')
ORDER BY table_name;
```

You should see all 5 tables listed.

## Creating Your First Admin User

After running the migration, you need to create your first admin user.

### Option A: Via Supabase Dashboard (Recommended)

1. **Create Auth User**:
   - Go to **Authentication** → **Users** in Supabase Dashboard
   - Click **Add User**
   - Enter email and password
   - Set email as confirmed
   - Click **Create User**
   - Copy the user's UUID

2. **Verify User Record Created**:
   ```sql
   SELECT u.id, u.email, u.full_name, r.name as role
   FROM users u
   JOIN user_permissions up ON u.id = up.user_id
   JOIN roles r ON up.role_id = r.id
   WHERE u.email = 'your-email@example.com';
   ```

3. **Upgrade to Admin**:
   ```sql
   -- Get admin role ID
   SELECT id FROM roles WHERE name = 'admin';  -- Note this ID (usually 1)

   -- Update user's role to admin
   UPDATE user_permissions
   SET role_id = 1  -- Use the admin role ID from above
   WHERE user_id = (
       SELECT id FROM users WHERE email = 'your-email@example.com'
   );
   ```

4. **Verify Admin Access**:
   ```sql
   SELECT
       u.email,
       u.full_name,
       r.name as role,
       r.permissions
   FROM users u
   JOIN user_permissions up ON u.id = up.user_id
   JOIN roles r ON up.role_id = r.id
   WHERE u.email = 'your-email@example.com';
   ```

### Option B: Manual SQL Script

If you prefer to do everything in one step:

```sql
-- Create auth user (you'll need to do this via Dashboard or API)
-- Then run this to upgrade them to admin:

DO $$
DECLARE
    v_admin_email VARCHAR := 'admin@yourcompany.com';  -- CHANGE THIS
    v_user_id UUID;
    v_admin_role_id INTEGER;
BEGIN
    -- Get admin role ID
    SELECT id INTO v_admin_role_id FROM roles WHERE name = 'admin';

    -- Get user ID by email
    SELECT id INTO v_user_id FROM users WHERE email = v_admin_email;

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found. Create user in Supabase Auth first.', v_admin_email;
    END IF;

    -- Update to admin role
    UPDATE user_permissions
    SET role_id = v_admin_role_id
    WHERE user_id = v_user_id;

    RAISE NOTICE 'User % is now an admin!', v_admin_email;
END $$;
```

## Testing the Setup

### 1. Test Roles

```sql
-- View all roles and their permissions
SELECT name, display_name, permissions
FROM roles
ORDER BY id;
```

### 2. Test User Permissions Function

```sql
-- Get effective permissions for a user
SELECT get_user_permissions(auth.uid());
```

### 3. Test Daily Limit Function

```sql
-- Check if user has remaining quota (run as authenticated user)
SELECT check_daily_limit((SELECT id FROM users WHERE auth_user_id = auth.uid()));
```

### 4. Test RLS Policies

```sql
-- As admin: Should see all location leads
SELECT COUNT(*) FROM location_leads;

-- As sales_rep with state restrictions: Should see filtered leads
SELECT COUNT(*) FROM location_leads;
```

## What the Migration Creates

### Tables

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `users` | User profiles | Links to Supabase Auth, soft deletes |
| `roles` | Role definitions | JSONB permissions, 4 default roles |
| `user_permissions` | Per-user settings | State restrictions, daily limits |
| `lead_access_log` | Audit trail | Tracks all lead access |
| `user_sessions` | Session management | Optional, for custom auth |

### Views

| View | Purpose |
|------|---------|
| `daily_lead_usage` | Daily usage statistics per user |

### Functions

| Function | Purpose |
|----------|---------|
| `get_user_permissions(uuid)` | Get merged permissions for user |
| `check_daily_limit(uuid)` | Check if user has quota remaining |
| `handle_new_auth_user()` | Auto-create user on signup |
| `update_updated_at_column()` | Auto-update timestamps |

### RLS Policies

All tables have Row Level Security enabled with appropriate policies:
- Users can view/edit own data
- Admins can manage all data
- State-based filtering for location leads

## Rollback (if needed)

To rollback this migration:

```sql
-- Drop triggers first
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_user_permissions_updated_at ON user_permissions;

-- Drop functions
DROP FUNCTION IF EXISTS handle_new_auth_user();
DROP FUNCTION IF EXISTS check_daily_limit(UUID);
DROP FUNCTION IF EXISTS get_user_permissions(UUID);
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop views
DROP VIEW IF EXISTS daily_lead_usage;

-- Drop RLS policies on location_leads
DROP POLICY IF EXISTS "Admins see all location leads" ON location_leads;
DROP POLICY IF EXISTS "Users see allowed state leads" ON location_leads;

-- Drop tables (order matters due to foreign keys)
DROP TABLE IF EXISTS lead_access_log;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS user_permissions;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;
```

## Next Steps

After successfully running this migration:

1. ✅ Create your first admin user (see above)
2. 📱 Set up the Next.js frontend project
3. 🔐 Configure Supabase Auth in the app
4. 🎨 Build the authentication UI
5. 📊 Build the dashboard

See `../WEB_APPLICATION_PLAN.md` for the complete implementation roadmap.

## Troubleshooting

### Error: "relation auth.users does not exist"

This means Supabase Auth is not enabled. Go to **Authentication** in your Supabase Dashboard to enable it.

### Error: "permission denied for schema auth"

The migration needs to be run with appropriate permissions. Make sure you're using the SQL Editor in Supabase Dashboard (which has the right permissions), not a client connection.

### Trigger Not Working

If the `handle_new_auth_user()` trigger doesn't fire when creating users:

1. Check that the trigger exists:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
   ```

2. If missing, recreate it:
   ```sql
   CREATE TRIGGER on_auth_user_created
       AFTER INSERT ON auth.users
       FOR EACH ROW
       EXECUTE FUNCTION handle_new_auth_user();
   ```

### Users Not Seeing Location Leads

Check their permissions:

```sql
SELECT
    u.email,
    r.name as role,
    up.allowed_states,
    up.max_daily_leads
FROM users u
JOIN user_permissions up ON u.id = up.user_id
JOIN roles r ON up.role_id = r.id
WHERE u.email = 'user@example.com';
```

If `allowed_states` is not NULL, they can only see leads in those states.
