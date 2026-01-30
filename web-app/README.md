# Lead Intelligence Portal - Web Application

Enterprise-grade web application for managing and visualizing lead intelligence data with role-based access control, territory management, and usage tracking.

## Features

- **Authentication**: Secure login/signup with Supabase Auth
- **Role-Based Access**: Admin, Manager, Sales Rep, and Viewer roles
- **Territory Management**: State-based access restrictions
- **Daily Quotas**: Per-user lead access limits
- **Analytics Dashboard**: Executive-level insights and metrics
- **Lead Management**: Browse, filter, and export leads
- **Audit Logging**: Full compliance with access tracking
- **Premium UI/UX**: Professional design with dark mode

## Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand + TanStack Query
- **Charts**: Recharts
- **Icons**: Lucide React
- **Animations**: Framer Motion

### Backend
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **API**: Next.js API Routes
- **Validation**: Zod

### DevOps
- **Hosting**: Vercel
- **Monitoring**: Sentry + Vercel Analytics
- **CI/CD**: GitHub Actions

## Prerequisites

Before you begin, ensure you have:

- **Node.js** 18.0.0 or higher
- **npm** 9.0.0 or higher
- **Supabase Project** with database migrations completed
- **Git** for version control

## Getting Started

### 1. Database Setup

First, ensure you've run all database migrations:

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Navigate to **SQL Editor**
3. Run the migration scripts from `../migrations/`:
   - `add_location_leads_table.sql` (if not already done)
   - `add_user_management_tables.sql` (NEW - required!)

See `../migrations/README.md` for detailed instructions.

### 2. Clone and Install

```bash
# Navigate to web-app directory
cd web-app

# Install dependencies
npm install
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env.local

# Edit .env.local with your values
nano .env.local
```

Required values:
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon key
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key (server-side only)

Find these in: **Supabase Dashboard** → **Settings** → **API**

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 5. Create First Admin User

1. Sign up via the app (will create sales_rep by default)
2. In Supabase Dashboard → **SQL Editor**, run:

```sql
-- Upgrade user to admin
UPDATE user_permissions
SET role_id = (SELECT id FROM roles WHERE name = 'admin')
WHERE user_id = (SELECT id FROM users WHERE email = 'your-email@example.com');
```

## Project Structure

```
web-app/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Auth pages (login, signup)
│   ├── (dashboard)/       # Main application (dashboard, leads, analytics)
│   ├── api/               # API routes
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
│
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── layout/           # Navbar, Sidebar, Footer
│   ├── dashboard/        # Dashboard-specific components
│   ├── leads/            # Lead management components
│   └── auth/             # Authentication forms
│
├── lib/                   # Utility libraries
│   ├── supabase/         # Supabase client setup
│   ├── auth/             # Auth helpers
│   ├── api/              # API client
│   └── utils/            # General utilities
│
├── types/                 # TypeScript type definitions
│   ├── database.ts       # Supabase generated types
│   ├── api.ts            # API types
│   └── auth.ts           # Auth types
│
├── hooks/                 # Custom React hooks
│   ├── use-user.ts       # User session hook
│   ├── use-permissions.ts # Permissions hook
│   ├── use-leads.ts      # Leads data hook
│   └── use-daily-limit.ts # Quota tracking hook
│
└── public/                # Static assets
    ├── logo.svg
    └── favicon.ico
```

## Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Type checking
npm run type-check

# Format code with Prettier
npm run format
```

## Development Workflow

### Adding New Components

We use **shadcn/ui** for UI components. To add a component:

```bash
# Example: Add a button component
npx shadcn-ui@latest add button

# Example: Add a dialog component
npx shadcn-ui@latest add dialog
```

Components are added to `components/ui/` and can be customized.

### Working with Supabase Types

Generate TypeScript types from your Supabase schema:

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Generate types
supabase gen types typescript --project-id YOUR_PROJECT_ID > types/database.ts
```

Update `YOUR_PROJECT_ID` with your actual Supabase project ID.

### Creating API Routes

API routes go in `app/api/`:

```typescript
// app/api/leads/route.ts
import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const supabase = createClient()

  const { data, error } = await supabase
    .from('location_leads')
    .select('*')
    .limit(10)

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }

  return NextResponse.json({ leads: data })
}
```

## Authentication Flow

1. User signs up via `/signup` page
2. Supabase Auth creates user in `auth.users`
3. Database trigger creates record in `users` table
4. Database trigger assigns default `sales_rep` role
5. User can login and access permitted leads

## Deployment

### Deploy to Vercel (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Initial web app setup"
   git push origin main
   ```

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Set root directory to `web-app`
   - Add environment variables (same as `.env.local`)
   - Deploy!

3. **Configure Domain**:
   - In Vercel Dashboard, go to **Domains**
   - Add your custom domain
   - Update DNS records as instructed

### Environment Variables for Production

In Vercel Dashboard → **Settings** → **Environment Variables**, add:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (production key!)
- `NEXT_PUBLIC_APP_URL` (your production domain)

## Security Checklist

- [ ] All environment variables set correctly
- [ ] `.env.local` in `.gitignore` (never commit!)
- [ ] RLS policies enabled on all tables
- [ ] Service role key only used server-side
- [ ] HTTPS enabled (automatic with Vercel)
- [ ] Rate limiting configured
- [ ] Admin user created and tested
- [ ] User permissions working correctly

## Troubleshooting

### "Supabase client not found"

Make sure you've created `.env.local` with correct Supabase credentials.

### "Cannot connect to database"

Check that your Supabase URL and keys are correct. Test them in Supabase Dashboard.

### "Permission denied" errors

1. Verify RLS policies are enabled
2. Check user's role and permissions in database
3. Ensure user is authenticated (check session)

### "Daily limit exceeded"

User has reached their daily quota. Check `daily_lead_usage` view:

```sql
SELECT * FROM daily_lead_usage
WHERE user_id = 'user-id-here'
AND access_date = CURRENT_DATE;
```

### Type errors after database changes

Regenerate types:

```bash
supabase gen types typescript --project-id YOUR_PROJECT_ID > types/database.ts
```

## Performance Optimization

- **Image Optimization**: Use Next.js `<Image>` component
- **Code Splitting**: Automatic with Next.js App Router
- **Server Components**: Use by default for better performance
- **Caching**: TanStack Query handles automatic caching
- **Database**: Ensure proper indexes (done in migrations)

## Contributing

1. Create a feature branch
2. Make changes
3. Test thoroughly
4. Run linter: `npm run lint`
5. Format code: `npm run format`
6. Commit and push
7. Create pull request

## Support

For issues or questions:
- Check `../WEB_APPLICATION_PLAN.md` for architecture details
- Review `../migrations/README.md` for database setup
- Check Supabase logs for backend errors
- Check browser console for frontend errors

## License

MIT License - see LICENSE file for details

---

**Ready to build amazing lead intelligence experiences! 🚀**
