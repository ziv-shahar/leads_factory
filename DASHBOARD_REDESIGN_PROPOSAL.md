# Dashboard & Leads Page Redesign Proposal
**Professional Lead Intelligence Platform**

---

## 🎯 Design Goals

1. **Lead-Type Specific Views** - Different card designs for different lead types
2. **Opportunity-Centric** - For government contracts, show deadline, status, size prominently
3. **Clean & Professional** - Remove score/confidence clutter, focus on actionable data
4. **Modern Enterprise UI** - Premium look with better visual hierarchy
5. **Actionable Information** - Show what matters for each lead type

---

## 📊 Dashboard Page Redesign

### **New Layout Structure**

```
┌────────────────────────────────────────────────────────────┐
│ Dashboard                                                   │
│ Track your lead intelligence and opportunities             │
└────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Active       │ Expiring     │ New This     │ Total        │
│ Opportunities│ Soon         │ Week         │ Leads        │
│              │              │              │              │
│ 23           │ 8            │ 84           │ 1,247        │
│ ────────────→│ ⚠ Alert     │ +12.5%       │ All Types    │
└──────────────┴──────────────┴──────────────┴──────────────┘

┌─────────────────────────────────┬──────────────────────────┐
│ Opportunity Timeline            │ Lead Type Breakdown      │
│                                 │                          │
│ [Chart: Opportunities by        │ [Pie/Donut Chart]        │
│  deadline week]                 │  - Gov Contracts: 45%    │
│                                 │  - Permits: 25%          │
│                                 │  - Demolitions: 15%      │
│                                 │  - Other: 15%            │
└─────────────────────────────────┴──────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Opportunities Closing Soon (Next 30 Days)                  │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ VETERANS AFFAIRS              📅 Mar 15, 2026 (8 days) │ │
│ │ Office Space - Atlanta, GA    📐 15,000-20,000 sq ft   │ │
│ │ Status: ACTIVE  │  $2.5M/yr estimated                  │ │
│ └────────────────────────────────────────────────────────┘ │
│ ... (5 more)                                               │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Recent Activity (All Lead Types)                           │
│ • ACME Corp - Expansion in Miami, FL          2h ago       │
│ • Building Demolition Permit - Tampa, FL      4h ago       │
│ • Defense Dept - New Contract - DC            1d ago       │
└────────────────────────────────────────────────────────────┘
```

### **New Stat Cards**

1. **Active Opportunities** (government contracts with `temporal_status=in_progress`)
   - Count of active opportunities
   - Arrow indicator "View All →"

2. **Expiring Soon** (response_deadline within 14 days)
   - Count with ⚠ warning icon
   - Red/orange accent color
   - Click to filter

3. **New This Week** (created_at within 7 days)
   - Count + percentage change
   - Green accent

4. **Total Leads** (all types)
   - Total count
   - "All Types" subtitle

---

## 🎴 Lead Cards - By Type

### **1. Government Opportunity Card**

**For**: `event_type=government_contract` OR `entity_type=government_agency`

```
┌───────────────────────────────────────────────────────────┐
│ 🏛 VETERANS AFFAIRS                    STATUS: ACTIVE ✓   │
│                                                           │
│ Office Space Lease - Atlanta, GA                         │
│ RFP-2026-VA-ATL-001                                      │
│                                                           │
│ ┌──────────────┬──────────────┬──────────────┐          │
│ │ 📅 DEADLINE  │ 📐 SIZE      │ 💰 BUDGET    │          │
│ │ Mar 15, 2026 │ 15-20K sq ft │ ~$2.5M/yr    │          │
│ │ (8 days)     │              │              │          │
│ └──────────────┴──────────────┴──────────────┘          │
│                                                           │
│ 📍 Delineated Area: Atlanta Metro, GA                    │
│ 🔒 Security Level: Level 2  │  🚗 Parking: 50 spaces   │
│ 📋 Lease Term: 10 years (5 firm)                         │
│                                                           │
│ [View Details →]                      Updated: 2h ago    │
└───────────────────────────────────────────────────────────┘
```

**Key Fields Displayed**:
- **Header**: Agency name + status badge (`opportunity_status`)
- **Title**: `title` from opportunity
- **Solicitation**: `solicitation_number`
- **3 Metric Cards**:
  - Deadline: `response_deadline` (with countdown in days)
  - Size: `aboa_sf_min`-`aboa_sf_max` sq ft
  - Budget: `award_amount` (if available) or "TBD"
- **Secondary Info**:
  - Location: `delineated_area` or `city, state`
  - Security: `facility_security_level`
  - Parking: `parking_spaces`
  - Lease terms: `lease_term_years`, `firm_term_years`
- **Footer**: View details link + last updated time

**Color Coding**:
- **ACTIVE** (in_progress): Green badge
- **FORECASTED** (planned): Blue badge
- **AWARDED** (completed): Gray badge
- **Deadline < 7 days**: Red warning border
- **Deadline < 14 days**: Orange warning badge

---

### **2. Permit Card**

**For**: `event_type=permit`

```
┌───────────────────────────────────────────────────────────┐
│ 🏗 ACME CONSTRUCTION                   NEW PERMIT 🆕      │
│                                                           │
│ Commercial Building Permit - Miami, FL                   │
│                                                           │
│ ┌──────────────┬──────────────┬──────────────┐          │
│ │ 📅 ISSUED    │ 📐 TYPE      │ 💰 VALUE     │          │
│ │ Mar 7, 2026  │ New Build    │ $4.2M        │          │
│ └──────────────┴──────────────┴──────────────┘          │
│                                                           │
│ 📍 123 Main St, Miami, FL 33101                          │
│ 🏢 Scope: 25,000 sq ft office building                   │
│                                                           │
│ [View Details →]                      Updated: 1d ago    │
└───────────────────────────────────────────────────────────┘
```

**Key Fields**:
- Company name + "NEW PERMIT" badge
- Permit type/title
- **3 Metrics**: Issue date, permit type, estimated value
- Address (if available in `key_facts`)
- Project scope/description
- Footer with view link + timestamp

---

### **3. Demolition Card**

**For**: `event_type=demolition`

```
┌───────────────────────────────────────────────────────────┐
│ 🏚 BUILDING DEMOLITION                 PERMIT ISSUED      │
│                                                           │
│ Commercial Building Demolition - Tampa, FL               │
│                                                           │
│ ┌──────────────┬──────────────┬──────────────┐          │
│ │ 📅 START     │ 📐 SIZE      │ 🏢 TYPE      │          │
│ │ Apr 2026     │ 50,000 sq ft │ Office       │          │
│ └──────────────┴──────────────┴──────────────┘          │
│                                                           │
│ 📍 456 Harbor Blvd, Tampa, FL                            │
│ 🔔 Opportunity: Redevelopment potential                  │
│                                                           │
│ [View Details →]                      Updated: 3d ago    │
└───────────────────────────────────────────────────────────┘
```

**Key Fields**:
- "BUILDING DEMOLITION" + status
- Location description
- **3 Metrics**: Start date, size, building type
- Address
- Opportunity note (redevelopment, new construction)
- Footer

---

### **4. Business Event Card** (Expansion, Funding, etc.)

**For**: `event_type=expansion|funding_round|partnership|etc.`

```
┌───────────────────────────────────────────────────────────┐
│ 🚀 ACME CLOUD CORP                     EXPANSION          │
│                                                           │
│ Opening New Office in Austin, TX                         │
│                                                           │
│ ┌──────────────┬──────────────┬──────────────┐          │
│ │ 📅 DATE      │ 👥 HIRING    │ 📍 MARKET    │          │
│ │ Feb 2026     │ 150 positions│ Austin, TX   │          │
│ └──────────────┴──────────────┴──────────────┘          │
│                                                           │
│ 🌐 acme.com  │  Industry: SaaS  │  Employees: 500+      │
│                                                           │
│ 💡 Signal: Seeking 20,000 sq ft office space            │
│                                                           │
│ [View Details →]                      Updated: 5h ago    │
└───────────────────────────────────────────────────────────┘
```

**Key Fields**:
- Company name + event type badge
- Event summary
- **3 Metrics**: Date, hiring count, market/location
- Company metadata (domain, industry, size)
- Top dynamic signal
- Footer

---

## 🎨 Design System Updates

### **Typography**
- **Card Headers**: Font-bold, text-lg
- **Titles**: Font-semibold, text-base
- **Metrics**: Font-black for numbers, text-sm for labels
- **Metadata**: Text-sm, text-gray-600/400

### **Color Palette** (Enhanced)

**Status Colors**:
- 🟢 **Active/In Progress**: `bg-green-50 text-green-700 border-green-200`
- 🔵 **Planned/Forecasted**: `bg-blue-50 text-blue-700 border-blue-200`
- 🟡 **Expiring Soon**: `bg-amber-50 text-amber-700 border-amber-200`
- ⚪ **Completed/Awarded**: `bg-gray-50 text-gray-700 border-gray-200`
- 🔴 **Urgent (<7 days)**: `bg-red-50 text-red-700 border-red-200`

**Lead Type Icons**:
- 🏛 Government: `Building2` icon in blue
- 🏗 Permit: `FileText` icon in cyan
- 🏚 Demolition: `Trash2` icon in pink
- 🚀 Expansion: `TrendingUp` icon in green
- 💰 Funding: `DollarSign` icon in emerald

### **Card Layouts**

All cards follow:
```
┌─────────────────────────────────┐
│ ICON + NAME            BADGE    │ ← Header (colored bg)
│                                 │
│ Title/Summary                   │ ← Main content
│                                 │
│ ┌──────┬──────┬──────┐         │ ← 3-column metrics
│ │ M1   │ M2   │ M3   │         │
│ └──────┴──────┴──────┘         │
│                                 │
│ Secondary metadata              │ ← Additional info
│                                 │
│ [Action] │  Timestamp           │ ← Footer
└─────────────────────────────────┘
```

**Spacing**: `p-6` for cards, `gap-4` between sections

**Shadows**:
- Default: `shadow-sm`
- Hover: `shadow-md` with `scale-[1.02]`
- Urgent: `shadow-lg border-2 border-red-300`

---

## 📄 Lead Detail Page Updates

### **Header Section** (Updated)

```
┌────────────────────────────────────────────────────────────┐
│ ← Back to Leads                                    Export  │
│                                                             │
│ 🏛 VETERANS AFFAIRS                                        │
│ Office Space Lease - Atlanta, GA                           │
│ RFP-2026-VA-ATL-001                                        │
│                                                             │
│ 🌐 va.gov  │  Federal Agency  │  📍 Washington, DC         │
└────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬──────────────┐
│ STATUS       │ DEADLINE     │ SIZE         │ BUDGET       │
│              │              │              │              │
│ ACTIVE ✓     │ Mar 15, 2026 │ 15-20K sq ft │ ~$2.5M/yr   │
│ In Progress  │ (8 days) ⚠  │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Removed**: Score badge, confidence score
**Added**: Lead-type specific metrics (deadline, size, budget for gov opportunities)

### **Sidebar** (Updated)

**Replace "Score Breakdown" with "Opportunity Details"** (for gov contracts):

```
┌─────────────────────────────────┐
│ Opportunity Details             │
│                                 │
│ 📋 Solicitation                │
│ RFP-2026-VA-ATL-001            │
│                                 │
│ 🏢 Sub-Agency                  │
│ Veterans Health Admin           │
│                                 │
│ 📅 Posted Date                 │
│ Feb 28, 2026                    │
│                                 │
│ 📅 Response Deadline           │
│ Mar 15, 2026 4:00 PM ET        │
│ ⚠ 8 days remaining             │
│                                 │
│ 📐 Office Size                 │
│ 15,000 - 20,000 sq ft          │
│                                 │
│ 🏗 Lease Terms                 │
│ • 10 year lease                │
│ • 5 year firm term             │
│                                 │
│ 🚗 Parking                     │
│ 50 spaces required             │
│ 10 reserved                    │
│                                 │
│ 🔒 Security Level              │
│ Level 2                        │
│                                 │
│ 💰 Tenant Improvement          │
│ $25/sq ft allowance            │
│                                 │
│ 📍 Delineated Area             │
│ Atlanta Metro, GA              │
│                                 │
│ 🔍 NAICS Code                  │
│ 531120 - Real Estate Leasing   │
└─────────────────────────────────┘
```

For **non-government leads**, show:
- Company info (domain, industry, employees)
- Recent activity summary
- Key milestones

---

## 🔍 Leads List Page Updates

### **Filters** (Updated)

```
┌────────────────────────────────────────────────────────────┐
│ 🔍 Filters                                                 │
│                                                             │
│ ┌──────────┬──────────┬──────────┬──────────┬──────────┐ │
│ │ Search   │ Type     │ State    │ Status   │ Timeline │ │
│ │ [____]   │ [Gov ▼]  │ [FL ▼]  │ [Active] │ [30 days]│ │
│ └──────────┴──────────┴──────────┴──────────┴──────────┘ │
└────────────────────────────────────────────────────────────┘
```

**New Filters**:
1. **Lead Type**: Government | Permits | Demolition | Business Events | All
2. **Timeline**: Next 7 days | Next 30 days | Next 90 days | All (for deadlines)
3. **Status**: Active | Forecasted | Closing Soon | All

**Removed**: Score range filter (not needed without score display)

### **Grid Layout**

- Keep responsive 1/2/3 column grid
- Use lead-type specific cards (from above)
- Group by type option: "Group by Lead Type" toggle

---

## 📱 Responsive Design

### **Mobile** (< 768px)
- Stack all metrics vertically
- Full-width cards
- Simplified metadata (show top 3 fields only)
- Collapsible detail sections

### **Tablet** (768-1024px)
- 2-column grid
- Keep 3-metric layout
- Show all metadata

### **Desktop** (> 1024px)
- 3-column grid
- Full detail view
- Hover previews

---

## 🎯 Data Field Mapping

### **Government Opportunities** (`entity_type=government_agency`)

| Display Name | Source Field | Notes |
|--------------|--------------|-------|
| Agency Name | `entity.canonical_name` | Header |
| Status | `event.strict.key_facts.other.opportunity_status` | Badge |
| Deadline | `event.strict.key_facts.other.response_deadline` | ISO datetime |
| Size | `event.strict.key_facts.aboa_sf_min/max` | sq ft |
| Budget | `event.strict.key_facts.amount` | Dollar amount |
| Solicitation | `event.strict.key_facts.other.solicitation_number` | ID |
| Notice Type | `event.strict.key_facts.other.notice_type` | Type label |
| Location | `event.strict.key_facts.other.delineated_area` | Primary |
| City/State | `event.strict.key_facts.city/state` | Fallback |
| Lease Terms | `event.strict.key_facts.other.lease_term_years` | Years |
| Firm Term | `event.strict.key_facts.other.firm_term_years` | Years |
| Parking | `event.strict.key_facts.other.parking_spaces` | Count |
| Security | `event.strict.key_facts.other.facility_security_level` | Level |
| TI Allowance | `event.strict.key_facts.other.tenant_improvement_allowance` | $ |
| Sub-Agency | `event.strict.key_facts.other.sub_agency` | Name |
| Awardee | `event.strict.key_facts.other.awardee_name` | If awarded |
| Expired | `event.expired_at` | Deadline passed |
| Temporal Status | `event.temporal_status` | planned/in_progress/completed |

### **Permits** (`event_type=permit`)

| Display Name | Source Field |
|--------------|--------------|
| Company | `entity.canonical_name` |
| Type | `event.summary` or type field |
| Issued Date | `event.event_time` |
| Value | `event.strict.key_facts.amount` |
| Location | `event.strict.key_facts.city/state` |
| Address | `event.strict.key_facts.address` |

### **Demolitions** (`event_type=demolition`)

| Display Name | Source Field |
|--------------|--------------|
| Building | Summary from event |
| Start Date | `event.event_time` |
| Size | From key_facts |
| Location | `event.strict.key_facts.city/state` |

### **Business Events** (expansion, funding, etc.)

| Display Name | Source Field |
|--------------|--------------|
| Company | `entity.canonical_name` |
| Event Type | `event.event_type` |
| Date | `event.event_time` |
| Location | `event.strict.key_facts.city/state` |
| Domain | `entity.domain` |
| Industry | `entity.entity_metadata.industry` |
| Employees | `entity.entity_metadata.employee_count` |
| Top Signal | `event.dynamic_signals[0]` |

---

## ✅ Implementation Checklist

### **Phase 1: Dashboard Updates**
- [ ] Update stat cards (Active Opps, Expiring Soon, New, Total)
- [ ] Add "Expiring Soon" calculation (response_deadline < 14 days)
- [ ] Create "Opportunities Closing Soon" section
- [ ] Update Recent Activity to show all lead types
- [ ] Remove score-based components

### **Phase 2: Lead Card Components**
- [ ] Create `GovernmentOpportunityCard.tsx`
- [ ] Create `PermitCard.tsx`
- [ ] Create `DemolitionCard.tsx`
- [ ] Create `BusinessEventCard.tsx`
- [ ] Add deadline countdown utility
- [ ] Add status badge mapping
- [ ] Add responsive 3-metric layout

### **Phase 3: Lead Detail Page**
- [ ] Update header to show lead-type metrics
- [ ] Create `OpportunityDetails` sidebar component
- [ ] Remove score breakdown
- [ ] Add opportunity-specific fields display
- [ ] Update event timeline styling

### **Phase 4: Filters & List**
- [ ] Add Lead Type filter
- [ ] Add Timeline filter (deadline-based)
- [ ] Update Status filter options
- [ ] Implement lead-type card routing
- [ ] Add "Group by Type" toggle

### **Phase 5: API Updates**
- [ ] Add `expiring_soon` field to stats endpoint
- [ ] Add `lead_type` calculation to leads endpoint
- [ ] Add deadline countdown helper
- [ ] Optimize queries for new filters

### **Phase 6: Polish**
- [ ] Test all responsive breakpoints
- [ ] Verify dark mode
- [ ] Add loading skeletons
- [ ] Add empty states
- [ ] Performance testing

---

## 🚀 Next Steps

**Review & Approve** this proposal, then I'll implement in phases starting with the most impactful changes first (lead cards).

**Questions to Confirm**:
1. Do you want to completely hide score/confidence, or show in a minimal way (e.g., small badge on hover)?
2. For non-government leads (permits, demolitions), should we still show them or focus only on government opportunities?
3. Any specific deadline urgency thresholds? (Currently: <7 days = urgent, <14 days = warning)
4. Do you want filtering by deadline range (e.g., "Closing this week", "Closing this month")?
5. Should "Expiring Soon" dashboard stat be 7 days or 14 days?

Let me know if you want any changes to this plan!
