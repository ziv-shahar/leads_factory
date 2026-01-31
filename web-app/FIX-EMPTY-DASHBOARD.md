# Fix for Empty Dashboard Issue

## Problem
The dashboard shows an empty table even though data exists in Supabase. The API returns error:
```
{"error":"infinite recursion detected in policy for relation \"users\""}
```

## Root Cause
The Row Level Security (RLS) policies on `location_leads` table have a circular reference. The policy joins to the `users` table to check permissions, but the `users` table has its own RLS policies that reference back, creating infinite recursion.

## Solution Steps

### Step 1: Apply the RLS Fix

1. Open your Supabase project dashboard at https://supabase.com
2. Go to the **SQL Editor** (left sidebar)
3. Click **New Query**
4. Copy and paste the entire content of `supabase-rls-fix.sql` into the editor
5. Click **Run** to execute the SQL script

This will:
- Remove all problematic RLS policies with circular references
- Create simplified policies that allow all authenticated users to access data
- Fix policies on tables: `location_leads`, `entities`, `events`, `users`, `user_permissions`, `roles`

### Step 2: Verify the Fix (Option A - Using Browser)

1. Open your browser to the dashboard: http://localhost:3000/leads
2. Refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
3. You should now see your leads data displayed
4. Try filtering by state to ensure filtering works
5. Click on a lead to view the detail page with events

### Step 2: Verify the Fix (Option B - Using Script)

If you want to verify the fix programmatically before testing in the browser:

1. Make sure you have a `.env.local` file with your Supabase credentials:
   ```bash
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
   ```

2. Install tsx if not already installed:
   ```bash
   npm install -D tsx
   ```

3. Run the verification script:
   ```bash
   npx tsx scripts/verify-supabase-access.ts
   ```

   This will test:
   - ✅ Access to location_leads table
   - ✅ Access to entities table
   - ✅ Access to events table
   - ✅ Joining location_leads with entities
   - ✅ Filtering events by entity_id

4. If all tests pass, proceed to test in the browser

### Step 3: Test the Dashboard

1. Start the development server if not already running:
   ```bash
   cd /home/user/leads_factory/web-app
   npm run dev
   ```

2. Open http://localhost:3000/leads

3. Verify the following features work:
   - [ ] Leads are displayed in grid layout
   - [ ] Total count is correct
   - [ ] State filter works
   - [ ] Status filter works
   - [ ] Score filter works
   - [ ] Search works
   - [ ] Pagination works
   - [ ] Clicking a lead opens detail page
   - [ ] Detail page shows all events
   - [ ] Score breakdown is displayed

## Expected Results

### Leads List Page
You should see:
- Grid of lead cards with company logos
- Color-coded scores (green for high, blue for medium, etc.)
- Location (city, state)
- Event counts
- Top 3 event types that contributed to the score
- Filters working correctly

### Lead Detail Page
You should see:
- Company header with logo and metadata
- Score and status badges
- Event count and last activity
- Left sidebar with score breakdown
- Right panel with expandable event timeline
- Events showing summaries, key facts, and dynamic signals

## Troubleshooting

### If you still see an empty table:

1. **Check browser console for errors**
   - Press F12 to open developer tools
   - Look at Console tab for errors
   - Look at Network tab to see API response

2. **Check API directly**
   - Open http://localhost:3000/api/location-leads in browser
   - Should return JSON with leads array
   - If error, check the error message

3. **Verify data exists in Supabase**
   - Go to Supabase dashboard → Table Editor
   - Check `location_leads` table has rows
   - Check `entities` table has rows
   - Check `events` table has rows

4. **Verify authentication**
   - Make sure you're logged in
   - Check that your user exists in the `users` table
   - Check that `auth_user_id` in `users` table matches your Supabase auth user ID

5. **Check environment variables**
   - Verify `NEXT_PUBLIC_SUPABASE_URL` is set correctly
   - Verify `NEXT_PUBLIC_SUPABASE_ANON_KEY` is set correctly
   - Restart the dev server after changing `.env.local`

### If verification script fails:

1. **"infinite recursion" error persists**
   - Make sure you ran the entire `supabase-rls-fix.sql` script
   - Check Supabase SQL Editor for any error messages
   - Try running the script again

2. **"permission denied" errors**
   - Check that RLS is enabled on all tables
   - Verify you're authenticated (logged in)
   - Check that policies were created successfully

3. **"relation does not exist" errors**
   - Verify table names are correct in your schema
   - Check that tables were created by your migration

## Next Steps (After Fix is Verified)

Once the dashboard is working with the temporary fix, you can:

1. **Implement proper state-based access control**
   - Modify RLS policies to use `user_permissions.auth_user_id` directly
   - Avoid circular references by not joining to `users` table
   - Test with different user roles and state restrictions

2. **Add additional features**
   - Export functionality
   - Lead status updates
   - Notes and comments
   - Activity logging

3. **Optimize performance**
   - Add database indexes
   - Implement caching
   - Use pagination more effectively

## Important Notes

⚠️ **This is a temporary fix for testing purposes.**

The current RLS policies allow ALL authenticated users to access ALL data. This is fine for initial development and testing, but for production you should:

1. Implement proper role-based access control
2. Enforce state-based restrictions
3. Add audit logging for data access
4. Test thoroughly with different user roles

The SQL file includes comments with examples of how to implement proper state-based access control without circular references.
