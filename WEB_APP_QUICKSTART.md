# Lead Intelligence Portal - Web App Quick Start

## 🎉 Implementation Complete - Phase 1!

You now have a fully functional authentication system and professional dashboard layout ready to use!

## ✅ What's Built

**Database Layer**:
- ✅ User management tables (users, roles, permissions)
- ✅ Role-based access control (admin, manager, sales_rep, viewer)
- ✅ State-based territory restrictions
- ✅ Daily lead access quotas
- ✅ Comprehensive audit logging
- ✅ Row Level Security (RLS) policies

**Web Application**:
- ✅ Next.js 14 with App Router
- ✅ TypeScript with strict typing
- ✅ Tailwind CSS with custom theme
- ✅ Authentication (login, signup, email verification)
- ✅ Protected routes via middleware
- ✅ Professional dashboard layout
- ✅ Sidebar navigation with active states
- ✅ Top navbar with search, notifications, user menu
- ✅ Dashboard page with stats, charts, tables
- ✅ Dark mode CSS (toggle logic pending)
- ✅ Responsive design (mobile, tablet, desktop)

## 🚀 Quick Start (5 Minutes)

### 1. Run Database Migration

```bash
# Go to Supabase Dashboard → SQL Editor
# Run: migrations/add_user_management_tables.sql
# You should see: "✅ User Management Migration Complete!"
```

### 2. Install Dependencies

```bash
cd web-app
npm install
```

### 3. Configure Environment

```bash
cp .env.example .env.local

# Edit .env.local with your Supabase credentials:
# - NEXT_PUBLIC_SUPABASE_URL
# - NEXT_PUBLIC_SUPABASE_ANON_KEY
# - SUPABASE_SERVICE_ROLE_KEY
```

Find these in: **Supabase Dashboard** → **Settings** → **API**

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 5. Create Admin User & Login

1. Click **Get Started** or **Sign In**
2. Click **Sign up** (if new user)
3. Fill in the form and create account
4. In Supabase Dashboard → **SQL Editor**, run:
   ```sql
   -- Upgrade to admin
   UPDATE user_permissions
   SET role_id = (SELECT id FROM roles WHERE name = 'admin')
   WHERE user_id = (SELECT id FROM users WHERE email = 'your-email@example.com');
   ```
5. Login with your credentials
6. You'll be redirected to the dashboard! 🎉

## 📸 What You'll See

### Landing Page (`/`)
- Professional hero section
- Feature cards (Real-Time Intelligence, Territory Management, Smart Filtering)
- Call-to-action buttons

### Login Page (`/login`)
- Clean login form
- Email and password inputs
- "Forgot password?" link
- OAuth provider placeholders (Google, GitHub)
- Link to signup

### Signup Page (`/signup`)
- User registration form
- Full name, email, password, confirm password
- Terms acceptance checkbox
- Email verification flow
- Success confirmation screen

### Dashboard (`/dashboard`)
- **Stats Cards**: Total Leads, New This Week, Daily Limit Used, Avg Lead Score
- **Sidebar**: Navigation with Dashboard, Leads, Analytics, Settings, Admin sections
- **Navbar**: Search bar, daily quota indicator, theme toggle, notifications, user menu
- **Lead Trends Chart**: Placeholder for Recharts integration
- **Recent Activity**: Feed of recent lead events
- **Top Leads Table**: Sortable table with company, state, score, status, last event

## 🎨 Customization

### Change Branding

**1. Logo and Company Name**:
```tsx
// components/layout/sidebar.tsx (line 35-45)
<div className="w-10 h-10 ...">
  <span>L</span>  {/* Change this */}
</div>
<span className="text-xl font-bold">
  Lead Intel  {/* Change this */}
</span>
```

**2. Landing Page Content**:
```tsx
// app/page.tsx (line 10-15)
<h1>Lead Intelligence Portal</h1>  {/* Change this */}
<p>Your tagline here...</p>  {/* Change this */}
```

**3. Brand Colors** (already set to professional blue/indigo):
```ts
// tailwind.config.ts
primary: '#3b82f6',    // Electric Blue
secondary: '#6366f1',  // Indigo
```

### Add Your Logo

1. Add logo file to `web-app/public/logo.svg`
2. Update sidebar:
```tsx
// components/layout/sidebar.tsx
import Image from 'next/image'

<Image src="/logo.svg" alt="Logo" width={40} height={40} />
```

## 📁 Project Structure

```
web-app/
├── app/
│   ├── (auth)/              # Auth pages (login, signup)
│   ├── (dashboard)/         # Protected dashboard pages
│   ├── auth/callback/       # OAuth callback handler
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Landing page
│   └── globals.css          # Global styles
│
├── components/
│   ├── ui/                  # Reusable UI components
│   └── layout/              # Layout components (sidebar, navbar)
│
├── lib/
│   ├── supabase/           # Supabase clients (browser, server)
│   └── utils/              # Utility functions
│
└── middleware.ts           # Auth middleware (route protection)
```

## 🔐 Authentication Flow

1. **User signs up** → Supabase Auth creates account
2. **Database trigger** → Automatically creates `users` record
3. **Database trigger** → Assigns default `sales_rep` role
4. **User logs in** → Supabase Auth validates credentials
5. **Middleware** → Checks authentication on protected routes
6. **Dashboard** → User can access based on permissions

## 🛡️ Permission System

**4 Default Roles**:
- **Admin**: Full access, unlimited leads, can manage users
- **Manager**: Team management, 200 leads/day, analytics access
- **Sales Rep**: Standard access, 50 leads/day (default for new users)
- **Viewer**: Read-only, 10 leads/day, no exports

**Permission Features**:
- State-based territory restrictions (e.g., only access FL, CA, TX)
- Daily lead access quotas
- Custom permission overrides per user
- Full audit logging of all lead access

## 🧪 Testing

### Test Authentication
```bash
# Login page
http://localhost:3000/login

# Signup page
http://localhost:3000/signup

# Try logging in/out
```

### Test Protected Routes
```bash
# Without login - should redirect to /login
http://localhost:3000/dashboard

# After login - should show dashboard
http://localhost:3000/dashboard
```

### Test Permissions (SQL)
```sql
-- View user's permissions
SELECT
  u.email,
  r.name as role,
  r.permissions,
  up.allowed_states,
  up.max_daily_leads
FROM users u
JOIN user_permissions up ON u.id = up.user_id
JOIN roles r ON up.role_id = r.id
WHERE u.email = 'your@email.com';
```

## 🐛 Troubleshooting

### Cannot connect to Supabase
- Check `.env.local` has correct values
- Verify Supabase project is active (not paused)
- Check browser console for errors

### "Permission denied" errors
- Run the database migration
- Check user has role assigned:
  ```sql
  SELECT * FROM user_permissions WHERE user_id = (SELECT id FROM users WHERE email = 'your@email.com');
  ```

### TypeScript errors
```bash
npm install
# Restart IDE/TypeScript server
```

### Module not found
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📚 Next Steps

### Immediate (Can do now):
1. ✅ Customize branding (logo, colors, text)
2. ✅ Create more user accounts and test roles
3. ✅ Explore the dashboard UI
4. ✅ Test authentication flow

### Phase 2 (Next to build):
1. **Leads List Page** - Browse and filter location leads
2. **Lead Detail Page** - Full entity view with events
3. **User Context** - Load real user data
4. **Dark Mode Toggle** - Wire up theme switching
5. **Charts** - Integrate Recharts for visualizations

### Phase 3 (Future):
1. **Analytics Dashboard** - Metrics and trends
2. **Admin Panel** - User and permission management
3. **Export Functionality** - CSV/JSON exports
4. **Real-time Updates** - Supabase subscriptions
5. **Mobile App** - React Native version

## 📖 Documentation

- **Database Setup**: `migrations/README.md`
- **Full Architecture**: `WEB_APPLICATION_PLAN.md`
- **Supabase Guide**: `SUPABASE_SETUP.md`
- **Web App README**: `web-app/README.md`

## 🎯 Success Checklist

Before moving forward, verify:

- [ ] Database migration completed
- [ ] Admin user created
- [ ] `npm install` successful
- [ ] `.env.local` configured
- [ ] Dev server running
- [ ] Can signup/login/logout
- [ ] Dashboard displays correctly
- [ ] No console errors

## 💡 Pro Tips

1. **Use the Admin Role**: Always test with admin first to see all features
2. **Check RLS Policies**: If data isn't showing, check Row Level Security
3. **Monitor Supabase Logs**: Dashboard → Logs to see API calls
4. **Use TypeScript**: It'll catch errors before runtime
5. **Test Mobile**: Resize browser or use device mode (F12 → Toggle device)

## 🎉 You're All Set!

The foundation is complete. You now have:
- ✅ Professional authentication system
- ✅ Production-ready database schema
- ✅ Beautiful, responsive UI
- ✅ Role-based access control
- ✅ Solid architecture for scaling

**Time to build the features that make your business unique!** 🚀

---

Need help? Check the troubleshooting section or review the detailed docs in `WEB_APPLICATION_PLAN.md`.
