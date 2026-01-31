/**
 * Supabase Access Verification Script
 *
 * This script verifies that the RLS policies are working correctly
 * and that the API can fetch data from Supabase.
 *
 * Run this script after applying the RLS fix to verify everything works.
 *
 * Usage:
 *   npx tsx scripts/verify-supabase-access.ts
 */

import { createClient } from '@supabase/supabase-js'

// Load environment variables
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('❌ Missing Supabase environment variables')
  console.error('   Make sure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set')
  process.exit(1)
}

console.log('🔍 Verifying Supabase Access...\n')
console.log(`Supabase URL: ${SUPABASE_URL}`)
console.log(`Using anon key: ${SUPABASE_ANON_KEY.substring(0, 20)}...\n`)

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

async function verifyAccess() {
  let hasErrors = false

  // Test 1: Check location_leads access
  console.log('📊 Test 1: Checking location_leads access...')
  try {
    const { data, error, count } = await supabase
      .from('location_leads')
      .select('*', { count: 'exact', head: true })

    if (error) {
      console.error('   ❌ ERROR:', error.message)
      hasErrors = true
    } else {
      console.log(`   ✅ SUCCESS: ${count} location_leads found`)
    }
  } catch (err: any) {
    console.error('   ❌ EXCEPTION:', err.message)
    hasErrors = true
  }

  // Test 2: Check entities access
  console.log('\n📊 Test 2: Checking entities access...')
  try {
    const { data, error, count } = await supabase
      .from('entities')
      .select('*', { count: 'exact', head: true })

    if (error) {
      console.error('   ❌ ERROR:', error.message)
      hasErrors = true
    } else {
      console.log(`   ✅ SUCCESS: ${count} entities found`)
    }
  } catch (err: any) {
    console.error('   ❌ EXCEPTION:', err.message)
    hasErrors = true
  }

  // Test 3: Check events access
  console.log('\n📊 Test 3: Checking events access...')
  try {
    const { data, error, count } = await supabase
      .from('events')
      .select('*', { count: 'exact', head: true })

    if (error) {
      console.error('   ❌ ERROR:', error.message)
      hasErrors = true
    } else {
      console.log(`   ✅ SUCCESS: ${count} events found`)
    }
  } catch (err: any) {
    console.error('   ❌ EXCEPTION:', err.message)
    hasErrors = true
  }

  // Test 4: Check location_leads with entity join (like the API does)
  console.log('\n📊 Test 4: Checking location_leads with entity join...')
  try {
    const { data, error } = await supabase
      .from('location_leads')
      .select(`
        *,
        entity:entities (
          id,
          canonical_name,
          normalized_name,
          domain,
          entity_type
        )
      `)
      .limit(5)

    if (error) {
      console.error('   ❌ ERROR:', error.message)
      hasErrors = true
    } else {
      console.log(`   ✅ SUCCESS: Fetched ${data?.length} leads with entity data`)
      if (data && data.length > 0) {
        console.log('\n   Sample lead:')
        const sample = data[0] as any
        console.log(`   - ID: ${sample.id}`)
        console.log(`   - State: ${sample.state}`)
        console.log(`   - Score: ${sample.score}`)
        console.log(`   - Status: ${sample.status}`)
        console.log(`   - Entity: ${sample.entity?.canonical_name}`)
      }
    }
  } catch (err: any) {
    console.error('   ❌ EXCEPTION:', err.message)
    hasErrors = true
  }

  // Test 5: Check events with filters
  console.log('\n📊 Test 5: Checking events with entity_id filter...')
  try {
    const { data: firstLead } = await supabase
      .from('location_leads')
      .select('entity_id')
      .limit(1)
      .single()

    if (firstLead) {
      const { data, error } = await supabase
        .from('events')
        .select('*')
        .eq('entity_id', firstLead.entity_id)
        .limit(5)

      if (error) {
        console.error('   ❌ ERROR:', error.message)
        hasErrors = true
      } else {
        console.log(`   ✅ SUCCESS: Fetched ${data?.length} events for entity ${firstLead.entity_id}`)
      }
    } else {
      console.log('   ⚠️  SKIPPED: No leads found to test events')
    }
  } catch (err: any) {
    console.error('   ❌ EXCEPTION:', err.message)
    hasErrors = true
  }

  // Summary
  console.log('\n' + '='.repeat(60))
  if (hasErrors) {
    console.log('❌ VERIFICATION FAILED')
    console.log('\nSome tests failed. Please:')
    console.log('1. Make sure you ran the supabase-rls-fix.sql script')
    console.log('2. Check that you have data in the tables')
    console.log('3. Verify your Supabase environment variables are correct')
    process.exit(1)
  } else {
    console.log('✅ ALL TESTS PASSED')
    console.log('\nYour Supabase access is working correctly!')
    console.log('The dashboard should now be able to fetch and display data.')
    process.exit(0)
  }
}

verifyAccess().catch((err) => {
  console.error('\n❌ Unexpected error:', err)
  process.exit(1)
})
