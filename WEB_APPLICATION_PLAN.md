# Lead Intelligence Web Application - Comprehensive Plan

## Executive Summary

This document outlines the complete plan for building a professional, enterprise-grade web application to present lead intelligence data with user authentication, role-based permissions, and a billion-dollar company UI/UX experience.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Database Schema Extensions](#2-database-schema-extensions)
3. [Authentication & Authorization Architecture](#3-authentication--authorization-architecture)
4. [Technology Stack](#4-technology-stack)
5. [UI/UX Design Philosophy](#5-uiux-design-philosophy)
6. [Application Structure](#6-application-structure)
7. [Page-by-Page Specifications](#7-page-by-page-specifications)
8. [API Design](#8-api-design)
9. [Security Considerations](#9-security-considerations)
10. [Implementation Phases](#10-implementation-phases)
11. [Deployment Strategy](#11-deployment-strategy)

---

## 1. System Overview

### Current Data Model (Existing in Supabase)

**Entities Table**: Companies, agencies, contractors with metadata
- `id`, `canonical_name`, `normalized_name`, `domain`, `entity_type`
- `entity_metadata` (JSONB): website, LinkedIn, location, industry, etc.
- `created_at`, `last_enriched_at`

**Events Table**: Activities linked to entities
- `id`, `entity_id`, `source`, `event_type`, `event_time`
- `strict` (JSONB): Structured event data
- `dynamic_signals` (JSONB): Additional insights
- `extraction_confidence`, `raw_ref`

**LeadCurrent Table**: Current lead state
- `id`, `entity_id`, `score`, `confidence_score`, `status`
- `reasons` (JSONB): Evidence and reasoning breakdown
- `last_updated_at`

**LocationLeads Table**: Per-state lead tracking
- `id`, `entity_id`, `state`, `city`
- `score`, `confidence_score`, `status`, `event_count`
- `reasons` (JSONB), `last_event_date`
- Unique constraint: `(entity_id, state)`

**LeadStateHistory Table**: Audit trail of lead changes

### Web Application Goal

Create a sophisticated, production-ready web portal where:
- **Sales teams** can browse qualified leads by state/region
- **Managers** can control user access, daily limits, and territory assignments
- **Executives** can view analytics and lead quality metrics
- **Users** experience a seamless, premium interface with real-time insights

---

## 2. Database Schema Extensions

### New Tables for User Management

#### 2.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,

    -- Authentication (if not using Supabase Auth)
    password_hash VARCHAR(255),  -- Only if custom auth

    -- Account status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Metadata
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

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_auth_user_id ON users(auth_user_id);
```

#### 2.2 Roles Table

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- "admin", "manager", "sales_rep", "viewer"
    display_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Permissions blueprint
    permissions JSONB NOT NULL DEFAULT '{}',
    -- Example:
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

-- Seed default roles
INSERT INTO roles (name, display_name, description, permissions) VALUES
('admin', 'Administrator', 'Full system access',
 '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": true, "can_manage_users": true, "can_view_analytics": true, "max_daily_leads": -1}'::jsonb),

('manager', 'Manager', 'Manage team and assigned territories',
 '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": true, "max_daily_leads": 200}'::jsonb),

('sales_rep', 'Sales Representative', 'View and export assigned leads',
 '{"can_view_leads": true, "can_export_leads": true, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": false, "max_daily_leads": 50}'::jsonb),

('viewer', 'Viewer', 'Read-only access',
 '{"can_view_leads": true, "can_export_leads": false, "can_view_all_states": false, "can_manage_users": false, "can_view_analytics": false, "max_daily_leads": 10}'::jsonb);
```

#### 2.3 User Permissions Table (Individual Overrides)

```sql
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,

    -- Territory restrictions (state filtering)
    allowed_states TEXT[],  -- ["FL", "CA", "TX"] or NULL for all

    -- Daily limits (override role defaults)
    max_daily_leads INTEGER,  -- NULL = use role default, -1 = unlimited

    -- Custom permissions (overrides)
    custom_permissions JSONB DEFAULT '{}',
    -- Example: {"can_export_leads": false}  -- Override role setting

    -- Date restrictions
    access_starts_at TIMESTAMP,
    access_expires_at TIMESTAMP,

    -- Metadata
    assigned_by UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id)  -- One permission record per user
);

CREATE INDEX idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX idx_user_permissions_role_id ON user_permissions(role_id);
```

#### 2.4 Lead Access Log (Track Daily Usage)

```sql
CREATE TABLE lead_access_log (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_lead_id INTEGER REFERENCES location_leads(id) ON DELETE SET NULL,
    entity_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,

    -- Access details
    access_type VARCHAR(50) NOT NULL,  -- "view", "export", "detail_view"
    state VARCHAR(2),

    -- Tracking
    accessed_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_lead_access_user_date ON lead_access_log(user_id, accessed_at);
CREATE INDEX idx_lead_access_date ON lead_access_log(accessed_at);

-- View for daily usage tracking
CREATE VIEW daily_lead_usage AS
SELECT
    user_id,
    DATE(accessed_at) as access_date,
    COUNT(*) as leads_accessed,
    COUNT(DISTINCT entity_id) as unique_entities
FROM lead_access_log
WHERE access_type IN ('view', 'export')
GROUP BY user_id, DATE(accessed_at);
```

#### 2.5 User Sessions Table (Optional - for custom auth)

```sql
CREATE TABLE user_sessions (
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

CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
```

---

## 3. Authentication & Authorization Architecture

### Recommended Approach: **Supabase Auth** (Integrated)

**Why Supabase Auth:**
- Built-in email/password authentication
- Magic link support
- OAuth providers (Google, GitHub, etc.)
- JWT-based sessions
- Row Level Security (RLS) integration
- Email verification out of the box
- Password reset flows
- No additional infrastructure needed

### Authentication Flow

```
1. User Registration:
   └─> Supabase Auth creates auth.users record
       └─> Trigger creates users table record
           └─> Assign default role (sales_rep)
               └─> Create user_permissions record

2. User Login:
   └─> Supabase Auth validates credentials
       └─> Returns JWT token with user_id
           └─> Frontend stores token (httpOnly cookie)
               └─> All API requests include JWT
                   └─> Middleware validates JWT & checks permissions

3. Permission Check (per request):
   └─> Extract user_id from JWT
       └─> Query user_permissions + role
           └─> Build effective permissions (role + overrides)
               └─> Check state restrictions
                   └─> Check daily limit
                       └─> Allow/Deny request
```

### Permission Resolution Logic

```javascript
function getEffectivePermissions(userId) {
  // 1. Get user's role and permissions
  const userPermission = await db.user_permissions
    .select('*, roles(*)')
    .eq('user_id', userId)
    .single();

  // 2. Merge role permissions with custom overrides
  const effectivePermissions = {
    ...userPermission.roles.permissions,
    ...userPermission.custom_permissions
  };

  // 3. Add territory restrictions
  effectivePermissions.allowed_states = userPermission.allowed_states;

  // 4. Resolve daily limit
  effectivePermissions.max_daily_leads =
    userPermission.max_daily_leads ??
    userPermission.roles.permissions.max_daily_leads;

  return effectivePermissions;
}
```

### Daily Limit Enforcement

```javascript
async function checkDailyLimit(userId, permissions) {
  const today = new Date().toISOString().split('T')[0];

  // Count today's lead accesses
  const usage = await db.daily_lead_usage
    .select('leads_accessed')
    .eq('user_id', userId)
    .eq('access_date', today)
    .single();

  const accessed = usage?.leads_accessed || 0;
  const limit = permissions.max_daily_leads;

  if (limit === -1) return true;  // Unlimited
  return accessed < limit;
}
```

### Row Level Security (RLS) Policies

```sql
-- Enable RLS on location_leads
ALTER TABLE location_leads ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see leads in their allowed states
CREATE POLICY "Users see allowed states only" ON location_leads
FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM user_permissions up
    WHERE up.user_id = auth.uid()
    AND (
      up.allowed_states IS NULL  -- NULL = all states
      OR location_leads.state = ANY(up.allowed_states)
    )
  )
);

-- Policy: Admins see everything
CREATE POLICY "Admins see all leads" ON location_leads
FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM user_permissions up
    JOIN roles r ON up.role_id = r.id
    WHERE up.user_id = auth.uid()
    AND r.name = 'admin'
  )
);
```

---

## 4. Technology Stack

### Frontend

**Framework**: **Next.js 14+** (App Router)
- **Why**: Server-side rendering, optimal performance, SEO, API routes built-in
- TypeScript for type safety
- React Server Components for optimal loading

**Styling**: **Tailwind CSS** + **shadcn/ui** components
- **Why**: Professional, consistent design system
- Customizable, accessible components
- Dark mode support out of the box
- Framer Motion for animations

**State Management**: **Zustand** or **TanStack Query**
- Lightweight, modern state management
- Automatic cache invalidation
- Optimistic updates

**UI Component Library**: **shadcn/ui** + **Radix UI**
- Professional, accessible components
- Customizable with Tailwind
- No runtime overhead

**Charts & Visualizations**: **Recharts** or **Chart.js**
- Clean, professional charts
- Responsive and interactive

**Icons**: **Lucide React**
- Consistent, modern icon set
- Tree-shakeable

### Backend

**API Layer**: **Next.js API Routes** (TypeScript)
- Serverless functions
- Integrated with frontend
- Type-safe end-to-end

**Database Client**: **Supabase JavaScript Client**
- Direct connection to Supabase
- Real-time subscriptions
- RLS enforcement

**Authentication**: **Supabase Auth**
- JWT-based sessions
- Built-in providers
- Email verification

**API Validation**: **Zod**
- Runtime type checking
- TypeScript integration

### DevOps & Deployment

**Hosting**: **Vercel** (Next.js) + **Supabase** (Backend)
- **Why**: Zero-config deployment, edge network, automatic HTTPS
- Preview deployments for PRs
- Built-in analytics

**Monitoring**: **Sentry** + **Vercel Analytics**
- Error tracking
- Performance monitoring

**Email Service**: **Resend** or **SendGrid**
- Transactional emails (password reset, welcome, etc.)

---

## 5. UI/UX Design Philosophy

### Design Principles (Billion-Dollar Company Look)

#### Visual Identity

**Color Palette**:
```
Primary (Brand):    #0066FF (Electric Blue) - Trust, Intelligence
Secondary:          #6366F1 (Indigo) - Premium, Professional
Accent:             #10B981 (Emerald) - Success, Growth
Warning:            #F59E0B (Amber)
Danger:             #EF4444 (Red)
Neutral:            Slate scale (50-950)

Backgrounds:
  Light mode:  #FFFFFF, #F8FAFC (slate-50)
  Dark mode:   #0F172A (slate-900), #1E293B (slate-800)
```

**Typography**:
```
Headings:  Inter (Clean, modern, professional)
Body:      Inter (Consistent, readable)
Monospace: JetBrains Mono (for data/codes)

Scale:
  Display:  4xl-6xl (60-72px)
  Heading:  xl-3xl (20-36px)
  Body:     sm-lg (14-18px)
  Caption:  xs-sm (12-14px)
```

**Spacing System**: Tailwind's 4px base scale
- Consistent rhythm
- Breathing room around content

**Border Radius**:
```
Small:   4px (buttons, inputs)
Medium:  8px (cards)
Large:   12px (modals, containers)
```

#### Layout Principles

1. **Generous White Space**: Don't cram - let content breathe
2. **Consistent Grid**: 12-column responsive grid
3. **Clear Hierarchy**: F-pattern for dashboards, Z-pattern for landing
4. **Progressive Disclosure**: Show essential first, details on demand
5. **Glass Morphism** (subtle): Frosted glass effects for overlays
6. **Subtle Shadows**: Layered depth without being heavy

#### Interaction Design

**Micro-interactions**:
- Smooth transitions (200-300ms ease-in-out)
- Hover states for all interactive elements
- Loading skeletons (not spinners) for data fetching
- Toast notifications for actions
- Optimistic UI updates

**Animations**:
```javascript
// Entrance animations
fadeIn: { opacity: [0, 1], duration: 300 }
slideUp: { y: [20, 0], opacity: [0, 1], duration: 400 }

// Button hover
scale: { scale: [1, 1.02], duration: 150 }

// Page transitions
pageSlide: { x: [-20, 0], opacity: [0, 1], duration: 400 }
```

**Accessibility**:
- WCAG 2.1 AA compliant
- Keyboard navigation throughout
- Screen reader optimized
- Focus indicators
- Proper ARIA labels

#### Premium UI Elements

1. **Glassmorphism Cards**: Subtle blur with transparency
2. **Gradient Accents**: Subtle gradients on CTAs and highlights
3. **Animated Backgrounds**: Subtle moving gradients or particles
4. **Smooth Scrolling**: Butter-smooth page transitions
5. **Data Visualization**: Interactive charts with smooth animations
6. **Smart Loading States**: Skeleton loaders matching content shape
7. **Empty States**: Beautifully illustrated, actionable empty states

---

## 6. Application Structure

### File Structure (Next.js App Router)

```
leads-intelligence-portal/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── signup/
│   │   │   └── page.tsx
│   │   ├── forgot-password/
│   │   │   └── page.tsx
│   │   └── layout.tsx (minimal layout)
│   │
│   ├── (dashboard)/
│   │   ├── dashboard/
│   │   │   └── page.tsx (main dashboard)
│   │   ├── leads/
│   │   │   ├── page.tsx (leads list)
│   │   │   └── [id]/
│   │   │       └── page.tsx (lead detail)
│   │   ├── analytics/
│   │   │   └── page.tsx
│   │   ├── settings/
│   │   │   └── page.tsx
│   │   ├── admin/
│   │   │   ├── users/
│   │   │   │   └── page.tsx
│   │   │   └── permissions/
│   │   │       └── page.tsx
│   │   └── layout.tsx (dashboard shell)
│   │
│   ├── api/
│   │   ├── auth/
│   │   │   ├── login/route.ts
│   │   │   ├── signup/route.ts
│   │   │   └── logout/route.ts
│   │   ├── leads/
│   │   │   ├── route.ts (list)
│   │   │   └── [id]/route.ts
│   │   ├── location-leads/
│   │   │   ├── route.ts
│   │   │   └── export/route.ts
│   │   ├── analytics/
│   │   │   └── route.ts
│   │   └── users/
│   │       └── route.ts
│   │
│   ├── layout.tsx (root layout)
│   └── page.tsx (landing/home)
│
├── components/
│   ├── ui/ (shadcn components)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── navbar.tsx
│   │   ├── sidebar.tsx
│   │   └── footer.tsx
│   ├── dashboard/
│   │   ├── stats-card.tsx
│   │   ├── recent-leads.tsx
│   │   └── lead-chart.tsx
│   ├── leads/
│   │   ├── lead-table.tsx
│   │   ├── lead-card.tsx
│   │   ├── lead-filters.tsx
│   │   └── event-timeline.tsx
│   └── auth/
│       ├── login-form.tsx
│       └── signup-form.tsx
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts (client-side)
│   │   ├── server.ts (server-side)
│   │   └── middleware.ts
│   ├── auth/
│   │   ├── permissions.ts
│   │   └── session.ts
│   ├── api/
│   │   └── client.ts (API helpers)
│   └── utils/
│       ├── cn.ts (className merger)
│       └── format.ts
│
├── types/
│   ├── database.ts (Supabase generated types)
│   ├── api.ts
│   └── auth.ts
│
├── hooks/
│   ├── use-user.ts
│   ├── use-permissions.ts
│   ├── use-leads.ts
│   └── use-daily-limit.ts
│
└── middleware.ts (auth & route protection)
```

---

## 7. Page-by-Page Specifications

### 7.1 Landing Page (/)

**Purpose**: First impression, explain value proposition, drive signups

**Layout**:
```
Hero Section:
  - Full-width gradient background (animated)
  - Bold headline: "Intelligence-Driven Lead Discovery"
  - Subheading: "Uncover high-intent opportunities with AI-powered insights"
  - CTA: "Start Free Trial" + "Watch Demo"
  - Hero image/animation: Dashboard preview

Features Section:
  - 3-column grid
  - "Real-Time Intelligence", "Territory Management", "Smart Filtering"
  - Icons + short descriptions

Social Proof:
  - "Trusted by 500+ teams"
  - Logos (if available)

Footer:
  - Links: About, Privacy, Terms
  - Contact info
```

**Tech**:
- Server-rendered for SEO
- Framer Motion for scroll animations
- Responsive breakpoints: sm, md, lg, xl

---

### 7.2 Login Page (/login)

**Layout**:
```
┌─────────────────────────────────────┐
│   Left: Branding/Illustration (40%) │
│   - Company logo                     │
│   - Tagline                          │
│   - Subtle animated gradient bg      │
│                                      │
│   Right: Login Form (60%)            │
│   - Email input                      │
│   - Password input                   │
│   - "Remember me" checkbox           │
│   - "Forgot password?" link          │
│   - Login button (primary)           │
│   - "Don't have account? Sign up"    │
└─────────────────────────────────────┘
```

**Features**:
- Form validation (Zod)
- Error handling (toast notifications)
- Loading states
- OAuth options (Google, GitHub)
- Redirects to dashboard on success

**Security**:
- CSRF protection
- Rate limiting (5 attempts/minute)
- Password strength indicator

---

### 7.3 Signup Page (/signup)

**Layout**: Similar to login, with additional fields

**Fields**:
- Full name
- Email
- Password (with strength meter)
- Confirm password
- Company (optional)
- Terms acceptance checkbox

**Flow**:
```
1. User fills form
2. Supabase Auth creates account
3. Email verification sent
4. Trigger creates users record
5. Assign default role (sales_rep)
6. Redirect to onboarding/dashboard
```

---

### 7.4 Dashboard (/dashboard)

**Layout**: Main control center after login

```
┌─────────────────────────────────────────────┐
│ Navbar (Logo, Search, Notifications, Avatar)│
├──────┬──────────────────────────────────────┤
│      │                                       │
│ Side │   Main Content Area                  │
│ bar  │   ┌──────────────────────────────┐   │
│      │   │  Stats Row (4 cards)         │   │
│ Nav  │   │  - Total Leads               │   │
│ Links│   │  - New This Week             │   │
│      │   │  - Daily Limit Used          │   │
│ - Dash   │  - Avg Score                 │   │
│ - Leads  └──────────────────────────────┘   │
│ - Analy  ┌──────────────────────────────┐   │
│ - Settings  Chart: Lead Trends (line)   │   │
│ - Admin  └──────────────────────────────┘   │
│      │   ┌──────────────────────────────┐   │
│      │   │  Recent Leads Table (5)      │   │
│      │   │  Quick actions: View, Export │   │
│      │   └──────────────────────────────┘   │
└──────┴──────────────────────────────────────┘
```

**Stats Cards**:
- Animated numbers (count-up effect)
- Icon + metric + trend indicator
- Click to filter relevant data

**Lead Trends Chart**:
- Line chart showing leads over time
- Filterable by date range (7d, 30d, 90d)
- Interactive tooltips

**Recent Leads Table**:
- Top 5 high-score leads
- Columns: Company, State, Score, Status, Last Event
- Click row → Lead detail page

---

### 7.5 Leads List Page (/leads)

**Purpose**: Browse all accessible leads with filters and sorting

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Header: "Leads"                              │
│ Actions: Export CSV, New Lead (admin only)  │
├─────────────────────────────────────────────┤
│ Filters Bar:                                 │
│ [State ▼] [Status ▼] [Score Range] [Search] │
├─────────────────────────────────────────────┤
│ Results: 247 leads (within your quota)       │
├─────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────┐│
│ │ Lead Cards Grid (responsive)             ││
│ │ ┌────────┐ ┌────────┐ ┌────────┐        ││
│ │ │Company │ │Company │ │Company │        ││
│ │ │Icon    │ │Icon    │ │Icon    │        ││
│ │ │Name    │ │Name    │ │Name    │        ││
│ │ │FL • 85 │ │CA • 78 │ │TX • 72 │        ││
│ │ │3 events│ │5 events│ │2 events│        ││
│ │ └────────┘ └────────┘ └────────┘        ││
│ └──────────────────────────────────────────┘│
│ Pagination: 1 2 3 ... 10 →                  │
└─────────────────────────────────────────────┘
```

**Filters**:
- **State**: Multi-select (only shows allowed states)
- **Status**: NEW, ACTIVE, STALE
- **Score Range**: Slider (0-100+)
- **Search**: Company name, domain

**Lead Card** (hover effects):
- Company logo/icon (first letter fallback)
- Canonical name
- State badge + Score badge (color-coded)
- Event count
- Quick actions: View, Export (respects permissions)

**Sorting**:
- Score (high to low)
- Recent activity
- Alphabetical

**Pagination**:
- 24 leads per page
- "Load more" or numbered pagination

**Daily Limit Indicator**:
```
Top banner: "You've viewed 23/50 leads today"
Progress bar showing usage
```

---

### 7.6 Lead Detail Page (/leads/[id])

**Purpose**: Deep dive into a single entity with all events and insights

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Breadcrumb: Dashboard > Leads > [Company]   │
├─────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────┐│
│ │ Header Card                              ││
│ │ [Logo] Company Name                      ││
│ │        domain.com • [Entity Type Badge]  ││
│ │        San Francisco, CA                 ││
│ │                                          ││
│ │ Score: 85 (High)  |  Confidence: 92%    ││
│ │ Status: ACTIVE    |  Last Updated: 2h ago││
│ │                                          ││
│ │ [Visit Website] [LinkedIn] [Export Lead] ││
│ └──────────────────────────────────────────┘│
│                                              │
│ ┌────────────┬────────────────────────────┐│
│ │ Left Sidebar (30%)                      ││
│ │                                          ││
│ │ Company Details                          ││
│ │ • Industry: Cloud Computing              ││
│ │ • Employees: 500                         ││
│ │ • HQ: San Francisco, CA                  ││
│ │                                          ││
│ │ Lead Reasoning                           ││
│ │ • Funding Round: +20                     ││
│ │ • Hiring Surge: +15                      ││
│ │ • Partnership: +10                       ││
│ │ (click to see event details)             ││
│ │                                          ││
│ │ Location Activity                        ││
│ │ Map showing states:                      ││
│ │ • FL: 85 score, 3 events                 ││
│ │ • CA: 72 score, 2 events                 ││
│ │ (click state → filter events)            ││
│ └──────────────────────────────────────────┘│
│                                              │
│ │ Right Content (70%)                      ││
│ │                                          ││
│ │ Tabs: [Events] [Notes] [Activity]       ││
│ │                                          ││
│ │ Event Timeline (sorted newest first)     ││
│ │ ┌────────────────────────────────────┐  ││
│ │ │ 🎉 Funding Round                   │  ││
│ │ │ Jan 15, 2026 • FL • Confidence: 95%│  ││
│ │ │ Summary: Raised $50M Series B...   │  ││
│ │ │ Key Facts:                         │  ││
│ │ │ • Led by Venture Capital Partners  │  ││
│ │ │ • Expansion plans mentioned        │  ││
│ │ │ [View Full Event ▼]                │  ││
│ │ └────────────────────────────────────┘  ││
│ │                                          ││
│ │ ┌────────────────────────────────────┐  ││
│ │ │ 👥 Hiring Surge                    │  ││
│ │ │ Jan 10, 2026 • CA • Confidence: 90%│  ││
│ │ │ ...                                │  ││
│ │ └────────────────────────────────────┘  ││
│ └──────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Key Features**:

1. **Header Card**: Company overview with quick actions
2. **Left Sidebar**:
   - Company metadata (from entity_metadata JSONB)
   - Lead reasoning breakdown (clickable)
   - Location activity map (US states heatmap)
3. **Event Timeline**:
   - Chronological list of all events
   - Expandable cards showing full event details
   - Filter by event type, location, date range
   - Each event shows:
     - Event type icon + name
     - Date, state, confidence score
     - Summary from `strict` JSONB
     - Key facts / dynamic signals
     - Source reference
4. **Notes Tab**: (Future) Allow users to add private notes
5. **Activity Tab**: Audit log showing who viewed this lead

**Interactions**:
- Click reasoning item → scroll to relevant event
- Click state on map → filter events by state
- Export button → logs access, downloads data (respects permissions)

---

### 7.7 Analytics Page (/analytics)

**Purpose**: Executive dashboard with metrics and trends

**Access Control**: Only visible to roles with `can_view_analytics: true`

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Header: "Analytics & Insights"              │
│ Date Range Selector: [Last 30 Days ▼]      │
├─────────────────────────────────────────────┤
│ KPI Row (4 cards)                           │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
│ │ Total  │ │Conversion││Pipeline│ │Avg    ││
│ │ Leads  │ │  Rate   │ │ Value │ │Score  ││
│ │  1,247 │ │   12%   │ │ $2.5M │ │  67   ││
│ └────────┘ └────────┘ └────────┘ └────────┘│
├─────────────────────────────────────────────┤
│ ┌──────────────────────┬──────────────────┐│
│ │ Lead Trends Chart    │ Leads by State   ││
│ │ (Line chart)         │ (Bar chart)      ││
│ │                      │                  ││
│ └──────────────────────┴──────────────────┘│
├─────────────────────────────────────────────┤
│ ┌──────────────────────┬──────────────────┐│
│ │ Event Type Breakdown │ Top Entities     ││
│ │ (Pie chart)          │ (Table)          ││
│ │                      │                  ││
│ └──────────────────────┴──────────────────┘│
├─────────────────────────────────────────────┤
│ User Activity (admin only)                  │
│ Team leaderboard, usage stats               │
└─────────────────────────────────────────────┘
```

**Charts**:
1. **Lead Trends**: New leads over time (daily/weekly/monthly)
2. **Leads by State**: Horizontal bar chart, top 10 states
3. **Event Type Breakdown**: Pie chart showing distribution
4. **Top Entities**: Table of highest-scoring leads
5. **User Activity** (Admin): Team usage, top performers

**Filters**:
- Date range
- State (for managers with territory restrictions)
- Status

---

### 7.8 Settings Page (/settings)

**Purpose**: User profile and preferences

**Tabs**:
1. **Profile**: Edit name, email, avatar, phone
2. **Security**: Change password, 2FA settings
3. **Notifications**: Email preferences
4. **API Access**: (Future) Generate API keys

---

### 7.9 Admin Pages (/admin/*)

**Access Control**: Only `admin` role

#### User Management (/admin/users)

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Header: "User Management"                   │
│ Actions: [+ Add User]                       │
├─────────────────────────────────────────────┤
│ Search: [🔍 Search users...]                │
├─────────────────────────────────────────────┤
│ Users Table                                  │
│ ┌─────────────────────────────────────────┐│
│ │ Name     │ Email      │ Role │ Status   ││
│ │──────────────────────────────────────────││
│ │ John Doe │ john@...   │ Rep  │ Active   ││
│ │ Jane Smith│ jane@...  │ Mgr  │ Active   ││
│ │ [Edit] [Deactivate] [View Activity]      ││
│ └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Actions**:
- Add user: Opens modal with signup form
- Edit: Modify role, permissions, territories, daily limits
- Deactivate: Soft delete (is_active = false)
- View activity: Show access logs

#### Permission Management (/admin/permissions)

**Features**:
- Edit role definitions
- Assign territories to users
- Set daily limits per user
- Audit log of permission changes

---

## 8. API Design

### REST API Endpoints

All endpoints use JWT authentication via Supabase Auth.

#### Authentication

```
POST /api/auth/signup
Body: { email, password, full_name }
Response: { user, session }

POST /api/auth/login
Body: { email, password }
Response: { user, session }

POST /api/auth/logout
Headers: Authorization: Bearer <token>
Response: { success: true }

POST /api/auth/forgot-password
Body: { email }
Response: { message: "Reset email sent" }
```

#### Leads

```
GET /api/location-leads
Query params:
  - state: string[]
  - status: string[]
  - score_min: number
  - score_max: number
  - limit: number
  - offset: number
Headers: Authorization: Bearer <token>
Response: {
  leads: LocationLead[],
  total: number,
  user_limit: { used: number, max: number }
}

GET /api/location-leads/:id
Headers: Authorization: Bearer <token>
Response: {
  lead: LocationLead,
  entity: Entity,
  events: Event[]
}

POST /api/location-leads/:id/export
Headers: Authorization: Bearer <token>
Response: CSV file download
Side effect: Logs access in lead_access_log
```

#### Entities

```
GET /api/entities/:id
Headers: Authorization: Bearer <token>
Response: {
  entity: Entity,
  location_leads: LocationLead[],
  events: Event[]
}
```

#### Analytics

```
GET /api/analytics/overview
Query params:
  - start_date: ISO date
  - end_date: ISO date
  - state: string[] (filtered by user permissions)
Headers: Authorization: Bearer <token>
Response: {
  total_leads: number,
  new_leads_this_period: number,
  avg_score: number,
  leads_by_state: { state: string, count: number }[],
  leads_trend: { date: string, count: number }[]
}
```

#### User Management (Admin only)

```
GET /api/users
Headers: Authorization: Bearer <admin-token>
Response: User[]

POST /api/users
Body: { email, full_name, role_id }
Headers: Authorization: Bearer <admin-token>
Response: { user: User }

PATCH /api/users/:id
Body: { role_id?, allowed_states?, max_daily_leads? }
Headers: Authorization: Bearer <admin-token>
Response: { user: User }

GET /api/users/:id/activity
Headers: Authorization: Bearer <admin-token>
Response: { access_log: LeadAccessLog[] }
```

### API Middleware Chain

```javascript
// middleware.ts
export async function middleware(req: NextRequest) {
  // 1. Extract JWT from cookie/header
  const token = req.cookies.get('sb-access-token');

  // 2. Validate with Supabase
  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error) return redirectToLogin();

  // 3. Attach user to request context
  req.context.user = user;

  // 4. Load permissions
  const permissions = await getEffectivePermissions(user.id);
  req.context.permissions = permissions;

  // 5. Check route access
  if (req.nextUrl.pathname.startsWith('/admin') && permissions.role !== 'admin') {
    return Response.json({ error: 'Forbidden' }, { status: 403 });
  }

  return NextResponse.next();
}
```

---

## 9. Security Considerations

### Authentication Security

1. **Password Requirements**:
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Not in common password list

2. **Session Management**:
   - JWT tokens with 1-hour expiration
   - Refresh tokens with 7-day expiration
   - HttpOnly cookies (not accessible via JavaScript)
   - Secure flag (HTTPS only)

3. **Rate Limiting**:
   - Login: 5 attempts per minute per IP
   - API: 100 requests per minute per user
   - Export: 10 per hour per user

4. **CSRF Protection**:
   - SameSite=Lax cookies
   - CSRF tokens for state-changing requests

### Authorization Security

1. **Row Level Security (RLS)**:
   - Enforced at database level
   - Users only query their allowed states
   - Admins bypass restrictions

2. **API-Level Checks**:
   - Every endpoint validates permissions
   - Daily limits checked before data access
   - Audit logging for all data access

3. **SQL Injection Prevention**:
   - Parameterized queries (Supabase client handles this)
   - Input validation with Zod

### Data Security

1. **Encryption**:
   - HTTPS everywhere (TLS 1.3)
   - Database encryption at rest (Supabase default)
   - Sensitive fields encrypted (if needed)

2. **Secrets Management**:
   - Environment variables (Vercel/Supabase)
   - Never commit secrets to git
   - Rotate API keys quarterly

3. **Audit Logging**:
   - Log all lead access (who, when, what)
   - Log permission changes
   - Retention: 1 year

### Compliance Considerations

- **GDPR**: User data export, deletion requests
- **CCPA**: California residents data rights
- **SOC 2**: (Future) Compliance certification

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Database**:
- ✅ Existing tables already in place
- [ ] Create users, roles, user_permissions, lead_access_log tables
- [ ] Set up RLS policies
- [ ] Create database views for analytics

**Authentication**:
- [ ] Configure Supabase Auth
- [ ] Build login/signup pages
- [ ] Implement middleware for route protection
- [ ] Email verification flow

**Design System**:
- [ ] Set up Tailwind + shadcn/ui
- [ ] Create base components (Button, Card, Input, etc.)
- [ ] Define color palette and typography
- [ ] Build layout components (Navbar, Sidebar, Footer)

**Deliverable**: Working login system, basic layout

---

### Phase 2: Core Dashboard (Week 3-4)

**Dashboard Page**:
- [ ] Stats cards with real data
- [ ] Lead trends chart
- [ ] Recent leads table
- [ ] Responsive layout

**Leads List Page**:
- [ ] Fetch location_leads with filters
- [ ] Implement state/status/score filters
- [ ] Lead card components
- [ ] Pagination
- [ ] Daily limit indicator

**Permissions System**:
- [ ] getEffectivePermissions() function
- [ ] Daily limit checking
- [ ] State filtering in queries

**Deliverable**: Functional dashboard and leads list with permissions

---

### Phase 3: Lead Details & Export (Week 5)

**Lead Detail Page**:
- [ ] Entity header card
- [ ] Company details sidebar
- [ ] Event timeline
- [ ] Location activity map
- [ ] Lead reasoning breakdown

**Export Functionality**:
- [ ] CSV export endpoint
- [ ] Access logging
- [ ] Permission checks
- [ ] Download handling

**Deliverable**: Complete lead viewing and export flow

---

### Phase 4: Analytics & Admin (Week 6-7)

**Analytics Page**:
- [ ] KPI cards
- [ ] Charts (leads trend, by state, event types)
- [ ] Date range filtering
- [ ] Export analytics data

**Admin Pages**:
- [ ] User management table
- [ ] Add/edit user modals
- [ ] Permission assignment
- [ ] User activity logs

**Deliverable**: Analytics and admin capabilities

---

### Phase 5: Polish & Performance (Week 8)

**UI/UX Enhancements**:
- [ ] Animations and micro-interactions
- [ ] Loading skeletons
- [ ] Error states and empty states
- [ ] Toast notifications
- [ ] Dark mode toggle

**Performance**:
- [ ] Optimize queries (indexes, views)
- [ ] Implement caching (TanStack Query)
- [ ] Image optimization
- [ ] Code splitting

**Testing**:
- [ ] Unit tests for utils
- [ ] Integration tests for API routes
- [ ] E2E tests for critical flows (login, lead export)

**Deliverable**: Production-ready application

---

### Phase 6: Launch Preparation (Week 9)

**Documentation**:
- [ ] User guide (how to use the portal)
- [ ] Admin guide (managing users and permissions)
- [ ] API documentation (if exposing)

**Deployment**:
- [ ] Vercel deployment setup
- [ ] Environment variables configuration
- [ ] Domain setup and SSL
- [ ] Monitoring (Sentry, analytics)

**Onboarding**:
- [ ] First-time user tour (tooltips)
- [ ] Sample data for demos
- [ ] Email templates (welcome, password reset)

**Deliverable**: Deployed, documented application

---

## 11. Deployment Strategy

### Hosting Architecture

```
┌─────────────────────────────────────────┐
│         Vercel (Frontend + API)         │
│  ┌────────────────────────────────┐     │
│  │  Next.js App (SSR + API Routes) │     │
│  └────────────────────────────────┘     │
│           ↓ Serverless Functions         │
└──────────────┬──────────────────────────┘
               │ HTTPS/JWT
               ↓
┌─────────────────────────────────────────┐
│         Supabase (Backend)              │
│  ┌────────────┐  ┌─────────────┐       │
│  │ PostgreSQL │  │ Auth Service│       │
│  │  Database  │  │  (JWT)      │       │
│  └────────────┘  └─────────────┘       │
│                                          │
│  ┌────────────┐  ┌─────────────┐       │
│  │   Storage  │  │   Realtime  │       │
│  │   (Files)  │  │  (Optional) │       │
│  └────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

### Deployment Steps

1. **Supabase Setup**:
   - Create new Supabase project
   - Run all SQL migrations (entities, events, location_leads, users, etc.)
   - Configure Auth settings (email templates, providers)
   - Set up RLS policies
   - Generate API keys

2. **Vercel Setup**:
   - Connect GitHub repository
   - Configure environment variables:
     ```
     NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
     SUPABASE_SERVICE_ROLE_KEY=xxx (server-side only)
     ```
   - Enable automatic deployments from `main` branch
   - Set up preview deployments for PRs

3. **Domain Configuration**:
   - Point custom domain to Vercel
   - Enable automatic HTTPS
   - Configure DNS records

4. **Monitoring Setup**:
   - Sentry for error tracking
   - Vercel Analytics for performance
   - Supabase dashboard for database monitoring

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run lint
      - run: npm run test
      - run: npm run build

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

---

## Summary & Next Steps

### What This Plan Delivers

A **professional, enterprise-grade web application** featuring:

✅ **Secure Authentication**: Supabase Auth with email/password, OAuth, email verification
✅ **Granular Permissions**: Role-based access with state restrictions and daily limits
✅ **Beautiful UI**: Modern, responsive design with smooth animations
✅ **Comprehensive Dashboard**: Stats, charts, recent activity
✅ **Advanced Lead Management**: Filtering, sorting, detailed views, export
✅ **Analytics & Insights**: Executive-level metrics and trends
✅ **Admin Portal**: User and permission management
✅ **Production-Ready**: Deployed on Vercel with monitoring and CI/CD

### Implementation Timeline

- **Phase 1-2** (4 weeks): Foundation + Core Dashboard
- **Phase 3-4** (3 weeks): Details + Admin
- **Phase 5-6** (2 weeks): Polish + Launch
- **Total**: ~9 weeks to production

### Recommended First Steps

1. **Review & Approve Plan**: Ensure alignment with vision
2. **Database Migration**: Run SQL scripts to create new tables
3. **Set Up Projects**: Create Supabase project, initialize Next.js app
4. **Design System**: Build out component library with Tailwind + shadcn
5. **Authentication Flow**: Implement login/signup with Supabase Auth
6. **Dashboard Prototype**: Build first version with real data

---

## Questions & Decisions Needed

Before starting implementation:

1. **Branding**: Do you have a company name, logo, color scheme?
2. **OAuth Providers**: Which providers to support (Google, GitHub, Microsoft)?
3. **Default Roles**: Confirm role names and default permissions
4. **Email Provider**: Resend, SendGrid, or Supabase built-in?
5. **Domain**: What domain will this be hosted on?
6. **Admin User**: Who should be the first admin? (We'll seed this)
7. **Budget**: Vercel Pro ($20/mo) recommended for analytics; Supabase free tier sufficient initially

---

**Ready to build a world-class lead intelligence portal! 🚀**
