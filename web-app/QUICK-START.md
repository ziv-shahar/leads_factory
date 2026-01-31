# Quick Start Guide - Fix Empty Dashboard

## 🚀 Quick Fix (3 Steps)

### Option A: Automated Script (Recommended)

```bash
cd /home/user/leads_factory/web-app
./apply-fix.sh
```

The script will guide you through:
1. Applying the RLS fix in Supabase
2. Verifying database access
3. Starting the development server

### Option B: Manual Steps

#### Step 1: Apply RLS Fix in Supabase (2 minutes)

1. Open [Supabase Dashboard](https://supabase.com)
2. Go to **SQL Editor** → **New Query**
3. Copy content from `supabase-rls-fix.sql`
4. Click **Run**

#### Step 2: Start the Server

```bash
cd /home/user/leads_factory/web-app
npm run dev
```

#### Step 3: Open Dashboard

Go to: http://localhost:3000/leads

## ✅ Expected Results

You should see:
- ✅ Grid of lead cards
- ✅ State filter dropdown
- ✅ Search, status, and score filters
- ✅ Lead count and pagination
- ✅ Clicking a lead shows detail page
- ✅ Event timeline on detail page

## ❌ Troubleshooting

### Still see empty table?

1. **Check API response:**
   - Open http://localhost:3000/api/location-leads
   - Should return JSON with leads array
   - If error message, check browser console

2. **Verify RLS fix was applied:**
   ```bash
   npx tsx scripts/verify-supabase-access.ts
   ```

3. **Check data exists:**
   - Go to Supabase → Table Editor
   - Verify `location_leads` has rows

4. **Restart the server:**
   ```bash
   # Kill current server (Ctrl+C)
   npm run dev
   ```

## 📚 Documentation

- **FIX-EMPTY-DASHBOARD.md** - Detailed troubleshooting guide
- **supabase-rls-fix.sql** - SQL script to fix RLS policies
- **scripts/verify-supabase-access.ts** - Verification script

## 🔍 What Was Fixed?

**Problem:** RLS policies had circular reference causing infinite recursion

**Solution:** Simplified policies to allow all authenticated users (temporary fix for testing)

**Next Steps:** Implement proper state-based access control (see FIX-EMPTY-DASHBOARD.md)

## 🆘 Need Help?

If you're still having issues:

1. Check browser console (F12) for errors
2. Check Network tab for API responses
3. Review FIX-EMPTY-DASHBOARD.md for detailed troubleshooting
4. Verify environment variables in `.env.local`

## 🎯 Quick Commands

```bash
# Start dev server
npm run dev

# Verify database access
npx tsx scripts/verify-supabase-access.ts

# Apply RLS fix (after editing SQL in Supabase)
./apply-fix.sh

# Check logs
# Open browser console (F12) → Console tab
```
