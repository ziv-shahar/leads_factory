#!/bin/bash

# ============================================================================
# Quick Fix Script for Empty Dashboard Issue
# ============================================================================
# This script helps you apply the RLS fix and verify everything works
#
# Usage: ./apply-fix.sh
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  Lead Intelligence Dashboard - RLS Fix Application                ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local file not found"
    echo "   A template has been created for you at .env.local"
    echo "   Please verify the Supabase credentials are correct"
    exit 1
fi

echo "✅ Found .env.local file"
echo ""

# Check if Node modules are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
    echo ""
fi

# Show instructions for Supabase fix
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Apply RLS Fix in Supabase"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The SQL fix script is located at: supabase-rls-fix.sql"
echo ""
echo "To apply the fix:"
echo "1. Open https://supabase.com and go to your project"
echo "2. Click on 'SQL Editor' in the left sidebar"
echo "3. Click 'New Query'"
echo "4. Copy and paste the entire content of supabase-rls-fix.sql"
echo "5. Click 'Run' to execute the script"
echo ""
echo "Press ENTER when you have completed this step..."
read -r

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Verify Database Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if tsx is installed
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx not found. Please install Node.js"
    exit 1
fi

echo "Running verification script..."
echo ""

# Install tsx if needed
if ! npm list tsx &> /dev/null; then
    echo "Installing tsx..."
    npm install -D tsx
fi

# Run verification script
if npx tsx scripts/verify-supabase-access.ts; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "STEP 3: Start Development Server"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "The database access is working correctly!"
    echo ""
    echo "To start the development server, run:"
    echo "  npm run dev"
    echo ""
    echo "Then open http://localhost:3000/leads in your browser"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Fix Applied Successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Your dashboard should now display data correctly."
    echo ""
    echo "If you still have issues, check FIX-EMPTY-DASHBOARD.md for"
    echo "troubleshooting steps."
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ Verification Failed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "The verification tests failed. This could mean:"
    echo ""
    echo "1. The RLS fix wasn't applied correctly in Supabase"
    echo "   → Go back and make sure you ran the entire SQL script"
    echo ""
    echo "2. Your environment variables are incorrect"
    echo "   → Check .env.local for correct SUPABASE_URL and SUPABASE_ANON_KEY"
    echo ""
    echo "3. There's no data in your Supabase tables"
    echo "   → Check the Supabase Table Editor to verify data exists"
    echo ""
    echo "For detailed troubleshooting, see: FIX-EMPTY-DASHBOARD.md"
    echo ""
    exit 1
fi
