# UI Design: Admin and User Menus

## Overview
Design two role-based menu groups for the current project:
- Admin menu: user management, data synchronization, system status
- User menu: chart viewing with data filtering

Primary goals:
- Clear separation of responsibilities by role
- Fast access to monitoring and sync controls for admins
- Flexible analysis experience for users with strong filtering

## Information Architecture
### Global layout
- Top bar: logo/project name, environment badge, notifications, user profile
- Left navigation: role-aware menu groups
- Main content: page header, filters/actions, primary content, secondary panels

### Navigation structure
- Admin menu
  - User Management
  - Data Synchronization
  - System Status
- User menu
  - Chart Explorer

Role behavior:
- Users only see User menu items.
- Admins see both groups with an Admin/User divider.
- Optional role switcher in top bar for accounts with both roles.

## Screen Designs

### Admin > User Management
Purpose: manage accounts, roles, and access status.

Layout:
- Page header: "User Management" with quick stats (Total, Active, Suspended)
- Action row: Search, Filter, Add User
- Main panel: user table
- Right panel (optional): selected user details

User table columns:
- Name, Email, Role, Status, Last Login, Created Date, Actions

User detail panel:
- Profile summary, role change, status toggle, reset password, audit trail

Filters:
- Role (Admin/User)
- Status (Active/Suspended/Pending)
- Last login (range)

States:
- Empty: "No users found" with clear filter button
- Error: show message and retry


### Admin > Data Synchronization
Purpose: control and monitor sync jobs.

Layout:
- Page header: "Data Synchronization"
- Action row: Run Now, Schedule, Sync Settings
- Main panel: job list with statuses
- Secondary panel: latest run details

Job list columns:
- Job Name, Source, Target, Status, Last Run, Duration, Next Run, Actions

Job details:
- Step timeline, logs preview, rows processed, warnings

Controls:
- Run Now (primary)
- Pause/Resume
- Edit schedule

States:
- Running: live progress bar, ETA
- Failed: error summary with view logs and retry


### Admin > System Status
Purpose: monitor system health and performance.

Layout:
- Page header: "System Status"
- Summary tiles: Uptime, Sync Queue, Error Rate, Storage
- Main panel: health checks list
- Secondary panel: alerts and recent incidents

Health checks list:
- Service, Status (OK/Warn/Down), Last Check, Latency

Charts:
- Time series for errors and throughput

States:
- Degraded: highlight affected services and recommended actions


### User > Chart Explorer
Purpose: explore charts with filters.

Layout:
- Page header: "Chart Explorer"
- Left filter panel
- Main panel: chart grid or single chart view
- Secondary row: table view for underlying data

Charts:
- Line, bar, area, and pie
- Metric selector (e.g., total rows, latency, errors)
- Toggle between chart and table

Filter panel fields:
- Date range (quick picks + custom)
- Category (multi-select)
- Data source (multi-select)
- Status (success/failure)
- Keyword search
- Advanced: numeric range sliders

Chart interactions:
- Hover tooltips
- Click to drill down
- Save filter presets

States:
- Empty: "No results for current filters"
- Loading: skeleton chart


## Shared Components
- Breadcrumbs in header
- Primary/secondary buttons
- Inline status badges (OK/Warn/Fail)
- Global toast notifications
- Pagination controls

## Visual Style (Guidance)
- Clean, data-first layout with strong hierarchy
- High-contrast badges for status
- Neutral background with subtle panel borders

## Accessibility
- All actions available via keyboard
- Clear focus states and large hit targets
- Color + icon for status (not color-only)

## Responsive Behavior
- Left nav collapses to icon rail on smaller screens
- Filter panel collapses into a drawer
- Tables become card lists on mobile

## Permissions Summary
- Admin menu: only visible to Admin role
- User menu: visible to all authenticated users
