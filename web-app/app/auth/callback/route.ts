/**
 * Auth Callback Route Handler
 *
 * This route is called after:
 * - Email verification
 * - OAuth provider redirects (Google, GitHub, etc.)
 * - Password reset
 */

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') || '/dashboard'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (!error) {
      // Successful authentication - redirect to dashboard or specified route
      return NextResponse.redirect(new URL(next, request.url))
    }
  }

  // Something went wrong - redirect to error page or login
  return NextResponse.redirect(
    new URL('/login?error=Unable to authenticate', request.url)
  )
}
