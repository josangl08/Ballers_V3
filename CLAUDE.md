# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
## Summary of the project
**Ballers App** is a comprehensive sports session management application for soccer training centers. This project serves a dual purpose:
1. **Academic**: Final master's project for advanced Python studies  
2. **Commercial**: Production management tool for a soccer training center in Bangkok

**Environment Strategy**: 
- **Development**: Spain timezone, local SQLite database
- **Production Master**: Spain timezone, Supabase PostgreSQL (for academic delivery)
- **Production Commercial**: Thailand timezone, Supabase PostgreSQL (for Bangkok client)

## Development Principles
Be critical and analytical. Research and objectively evaluate all proposals rather than accepting them at face value. Question assumptions and suggest better alternatives when appropriate.

## Language Conventions
- **Frontend/UI**: English
- **Code Comments**: Spanish
- **Documentation**: Mixed (English for technical, Spanish for business context)

## Essential Commands

### Application Startup
```bash
# Install dependencies
pip install -r requirements.txt

# Run Dash application (primary)
python main_dash.py

# Enable debug mode
export DEBUG=True && python main_dash.py
```

### Testing & Quality Assurance
```bash
# Run test suite (should always pass: 13/13 tests)
python -m pytest tests/test_dash_app.py -v

# Verify app initialization
python -c "from main_dash import initialize_dash_app; app = initialize_dash_app()"

# Code quality checks
python -m flake8 --max-line-length=88
python -m black --check .
python -m isort --check-only .
```

### Database Management
```bash
# Database auto-initializes on first run
# Development: SQLite (data/ballers_app.db)
# Production: PostgreSQL via Supabase

# Manual database recreation
python data/seed_database.py

# Populate with test sessions
python data/seed_calendar.py

# Data maintenance scripts
python data/clear_sessions.py --backup    # Clear sessions with backup
python data/clean_duplicates.py          # Remove duplicate sessions
python data/cleanup_database.py          # Clean duplicate database fields
python data/clear_calendar.py            # Clear Google Calendar events
```

## Architecture Overview

### Core Structure
This is a **sports session management application** with Google Calendar integration, built using a clean MVC architecture pattern. Originally developed with **Streamlit**, now **migrated to Dash** for enhanced functionality, better performance, and greater customization capabilities.

**Key Components:**
- **Models**: SQLAlchemy-based data models with inheritance hierarchy (User → Admin/Coach/Player)
- **Controllers**: Business logic layer handling auth, database, calendar sync, and validation
- **Pages**: UI components for different application sections (Dash primary, Streamlit legacy)
- **Callbacks**: Dash callback functions organized by functionality (auth, navigation, sidebar, etc.)
- **Common**: Shared utilities and authentication logic (Dash + legacy versions)

### Data Model Hierarchy
```
User (base class)
├── Admin - Full system access
├── Coach - Session management, player oversight
└── Player - Session participation, limited access
    ├── Amateur Players - Standard session management
    └── Professional Players - Enhanced with Thai League statistics
```

### Professional Players Extension (Phase 12 - Current)
- **Database Extensions**: `is_professional`, `wyscout_id` fields in Player model
- **Professional Stats Model**: Complete statistics tracking (goals, assists, defensive actions, etc.)
- **Thai League Integration**: Automated data extraction from GitHub repository
- **Conditional UI**: Tab system (Info/Stats) for professional players only

### Environment Management
- **Development**: Local SQLite database, Spanish timezone, test Google Calendar
- **Production**: Supabase PostgreSQL, Thailand timezone, production Google Calendar
- Environment detection is automatic via `config.py`

### Authentication & Session Management
- Session-based authentication with automatic URL restoration
- Role-based access control (admin/coach/player)
- Context managers for database session handling
- Login state persists across page refreshes

### Google Integration
- **Calendar Sync**: Bidirectional sync with Google Calendar events
- **Sheets Integration**: Data export to Google Sheets for accounting
- **Service Account**: Uses google_service_account.json for API access
- **Auto-sync**: Background synchronization for admin/coach roles

### Key Controllers
- `AuthController`: Authentication and session management using context managers
- `calendar_sync_core`: Core Google Calendar bidirectional synchronization
- `sync_coordinator`: Manages automatic background synchronization
- `SessionController`: CRUD operations for training sessions
- `ValidationController`: Input validation and data integrity
- `ThaiLeagueController`: Professional stats extraction and player matching (Phase 12)

### Professional Stats System (Phase 12) - Key Files
- `models/professional_stats_model.py`: Statistical data model (50+ metrics)
- `models/thai_league_seasons_model.py`: Season import tracking
- `controllers/thai_league_controller.py`: Data extraction, fuzzy matching, GitHub sync
- `callbacks/professional_tabs_callbacks.py`: Conditional tabs UI logic
- `data/migrate_players_table.py`: Database migration for professional fields

### Configuration System
- Environment-aware configuration via `config.py`
- Automatic timezone handling (Europe/Madrid dev, Asia/Bangkok prod)
- Google API credentials management for both environments
- Database URL configuration based on environment

### UI Architecture (Dash)
- **Sidebar Navigation**: Collapsible role-based menu system with Bootstrap components
- **Dynamic Loading**: Modules loaded dynamically based on user selection via callbacks
- **Component-based**: Dash Bootstrap Components for consistent UI/UX
- **Callback System**: Organized callback registration for better maintainability
- **Custom Styling**: CSS customization with Bootstrap + custom styles
- **Responsive Design**: Bootstrap grid system with responsive breakpoints

## Important Implementation Notes

### Database Sessions
Always use context managers for database operations:
```python
with AuthController() as auth:
    # Database operations here
    pass
```

### Environment Variables
Required for development:
- `CALENDAR_ID`: Google Calendar ID for sync
- `ACCOUNTING_SHEET_ID`: Google Sheets ID for data export
- `GOOGLE_SA_PATH`: Path to service account JSON file
- `DEBUG`: Enable verbose logging (optional)

### Google Calendar Integration
- Events are synchronized bidirectionally
- Session status affects calendar event colors
- Hash-based change detection prevents unnecessary API calls
- Timezone conversion handled automatically

### Validation Patterns
Use `ValidationController` for all input validation rather than inline validation to maintain consistency across the application.

### Error Handling
- Database initialization failures show helpful diagnostic messages
- Google API errors are logged but don't crash the application
- User-facing error messages are localized in Spanish

## 🚀 PROJECT MIGRATION STATUS & ROADMAP

### Migration Context
The project successfully migrated from **Streamlit to Dash** for enhanced functionality and better performance. The migration is now **98% complete** with all major features implemented, tested, and functional.

### Current Status: Phase 11 - Final Integration & Production Prep 🚀 **IN PROGRESS** (July 2025)
**Latest Achievement**: Complete migration finalized with role-based access control fixes
- ✅ Webhook integration system fully implemented and active
- ✅ Complete backend migration from Streamlit to Dash  
- ✅ Role-based access control completely functional
- ✅ JavaScript errors resolved and user restrictions working
- ✅ All UI phases completed (9/9 phases)
- ✅ Backend components 100% migrated and tested

### Development Methodology
- **Incremental Development**: Small, functional changes with frequent commits
- **Commit Strategy**: Each working feature gets its own commit
- **No AI Attribution**: Commits should appear as if created by the human developer
- **Quality Focus**: Code must pass tests and work correctly before committing

### Migration Phases Overview

#### ✅ **Completed Phases (10/11)**:
1. **Infrastructure Cleanup** - Project structure and imports (Dec 2024)
2. **Sidebar Menu Migration** - Complete navigation system (July 2025)
3. **Player Cards Optimization** - Responsive player displays (July 2025)
4. **Calendar Features** - Visual improvements and data management (July 2025)
5. **Player Profile Details** - Complete profile system (July 2025)
6. **Administration Panel** - Full admin functionality (July 2025)
7. **Advanced Calendar Features** - Auto-completion and visual enhancements (July 2025)
8. **Financials Migration** - Google Sheets integration (July 2025)
9. **Settings Migration** - Complete user and system settings functionality (July 2025)
10. **Webhook Integration** - Real-time Google Calendar sync system (July 2025)

#### 🔄 **Current Phase (11/11)**:
**Phase 11: Final Integration & Production Prep** 🚀 **IN PROGRESS** (July 2025)
**Objetivo**: Final polish, optimization, and production deployment preparation
- 🎯 **Performance Optimization**: Code cleanup and speed improvements
- 🎯 **End-to-End Testing**: Complete system validation
- 🎯 **Production Configuration**: Environment-specific setups
- 🎯 **Documentation**: User and technical documentation finalization
- 🎯 **Deployment Preparation**: Ready for Bangkok client production

#### ✅ **Recently Completed Major Achievements**:
**Backend Migration Completed** (July 2025):
- ✅ Complete elimination of Streamlit dependencies
- ✅ All controllers migrated to pure Dash architecture
- ✅ Legacy code cleaned and removed

**Role-Based Access Control Fixes** (July 2025):
- ✅ JavaScript store reference errors resolved
- ✅ Coach user restrictions fully implemented
- ✅ Session filtering by user role working correctly
- ✅ Create/Edit forms with appropriate role limitations
- ✅ All user types (admin/coach/player) tested and functional

### Current Project Status
- **UI Migration**: 100% complete (10/10 phases)
- **Backend Migration**: 100% complete (all controllers migrated)
- **Webhook Integration**: 100% complete (real-time sync active)
- **Role-Based Access Control**: 100% complete (all restrictions working)
- **Overall Project**: **98% complete** (Phase 11 in progress)

## ✅ PHASE 10: AUTOSYNC → WEBHOOKS MIGRATION - **COMPLETED** (July 2025)

### **Migration Overview**
Successfully transformed the polling system (every 5 minutes) to Google Calendar webhooks for real-time synchronization with minimal latency.

### **✅ COMPLETED ACHIEVEMENTS**:
- ✅ **Webhook Server Implementation**: Flask-based webhook server running on port 8001
- ✅ **Real-time Google Calendar Integration**: Push notifications from Google Calendar working
- ✅ **UI Updates in Real-time**: Automatic UI refresh based on webhook events
- ✅ **Development Environment Setup**: Local webhook testing with manual fallback
- ✅ **Legacy System Removal**: SimpleAutoSync polling system completely eliminated
- ✅ **Notification System Integration**: Webhook events integrated with existing notification controller

### **Implementation Results**
The webhook system has been successfully implemented with the following architecture:

#### **Current Architecture**:
```
Google Calendar ──webhook──▶ Flask Server ──▶ calendar_sync_core ──▶ Database
     (events)       (port 8001)    (real-time)       (sessions)
                         │
                         ▼
                 NotificationController ──▶ Dash UI
                   (event tracking)      (real-time updates)
```

#### **Key Technical Achievements**:
- **Webhook Server**: Flask-based server running on localhost:8001
- **Real-time Processing**: Events processed immediately upon Google Calendar changes  
- **Development Setup**: HTTP webhook endpoint for local development with manual testing
- **Fallback System**: Manual sync remains available as backup
- **UI Integration**: Real-time updates reflected in Dash interface

#### **Development Status**:
- **Local Environment**: Webhook server active and functional
- **Google Calendar**: HTTPS requirement noted for production (development uses HTTP)
- **Testing**: Manual webhook testing available via curl commands
- **Performance**: Near-zero latency for local event processing

## 🛠️ ROLE-BASED ACCESS CONTROL FIXES - **COMPLETED** (July 2025)

### **Critical Issues Resolved**
This phase addressed critical JavaScript errors and implemented complete role-based restrictions for coach users.

#### **✅ JavaScript Store Reference Errors Fixed**:
- **Problem**: `user-type-store` references in administration callbacks causing JavaScript errors
- **Solution**: Updated all references to use `admin-user-type-store` in administration pages
- **Files Modified**: `callbacks/administration_callbacks.py` - Fixed State references in create/edit session callbacks
- **Result**: No more JavaScript console errors, all callbacks working correctly

#### **✅ Database Import Issues Resolved**:
- **Problem**: Incorrect import of `db_session` instead of `get_db_session()` function
- **Solution**: Fixed import statements and context manager usage
- **Files Modified**: `controllers/session_controller.py` - Corrected `get_coach_by_user_id()` function
- **Result**: Database operations working correctly without import errors

#### **✅ Coach Role Restrictions Implemented**:
- **Create Session Form**: Coach pre-selected and dropdown disabled for coach users
- **Edit Session Form**: Coach users can only see and edit their own sessions
- **Session Filtering**: Calendar and table views filtered by coach ID for coach users
- **Table Functionality**: Extended `create_sessions_table_dash()` to support `coach_id` parameter

#### **✅ Session Filtering by Role**:
- **Calendar View**: Already working correctly, shows only coach's sessions
- **Table View**: Fixed to apply coach filtering using updated table function
- **Form Access**: Create/edit forms now respect role-based restrictions
- **Admin Access**: Admin users maintain full access to all functionality

### **Technical Implementation Details**
- **Helper Function**: `get_coach_by_user_id()` properly maps user_id to coach_id
- **Store Management**: Global `user-type-store` available across all layouts
- **Role Detection**: Dynamic role detection from session data in callbacks
- **Form Restrictions**: Automatic form field pre-population and disabling based on user role

### **Testing Verification**
- ✅ **Admin Role**: Full access to all sessions and functionality
- ✅ **Coach Role**: Restricted to own sessions, pre-populated forms, no JavaScript errors
- ✅ **Player Role**: Continues to work normally with profile restrictions
- ✅ **Database Functions**: All context managers and imports working correctly
- ✅ **UI Functionality**: All forms, tables, and navigation working without errors

#### ✅ Phase 1: Infrastructure Cleanup (COMPLETED)
**Status**: Successfully completed
**Achievements**:
- Project structure cleaned and organized
- Import errors resolved (cloud_utils, app_dash → main_dash)
- Obsolete tests updated to work with new Dash structure (13 tests passing)
- Basic application functionality verified
- Code style improved (removed unused imports, fixed formatting)

**Key Files Cleaned**:
- `/controllers/session_controller.py` - Fixed imports and cloud_utils references
- `/controllers/sync_coordinator.py` - Fixed imports and cloud_utils references
- `/tests/test_dash_app.py` - Completely rewritten for new structure
- `/pages/administration_dash.py` - Added missing imports
- `/pages/ballers_dash.py` - Added missing imports and callbacks
- `/pages/settings_dash.py` - Massive cleanup of unused imports
- `/common/` files - Cleaned unused imports across all files

**Current State**:
- Application initializes without errors
- All tests pass (13/13)
- Import structure optimized
- Ready for incremental development

#### 🎯 Phase 2: Core Interface Reconstruction (NEXT)
**Status**: Ready to begin
**Objectives**:
- Rebuild login interface with proper styling
- Reconstruct main menu/sidebar navigation
- Rebuild ballers_dash with complete functionality
- Ensure visual consistency with original design

**Priority Features**:
1. **Login System** - Complete authentication interface
2. **Main Menu** - Sidebar navigation with role-based access
3. **Ballers Dashboard** - Player management and profiles
4. **Settings Panel** - User management and system configuration

#### 🔄 Phase 3: Advanced Features (FUTURE)
**Status**: Planned
**Objectives**:
- Google Calendar integration interface
- Advanced user management features
- Reporting and analytics dashboards
- Performance optimization

### Current Development Guidelines

#### Commit Strategy
```bash
# Each working feature should be committed immediately
git add -A && git commit -m "Specific feature description

- List of changes made
- Any important notes
- Next steps if applicable"
```

#### Testing Requirements
- Run tests before each commit: `python -m pytest tests/test_dash_app.py`
- Verify app initialization: `python -c "from main_dash import initialize_dash_app; app = initialize_dash_app()"`
- Check for basic functionality

#### Code Quality Standards
- Follow existing code patterns and structure
- Maintain Spanish comments as per project requirements
- Use context managers for database operations
- Implement proper error handling

### Key Lessons Learned
1. **Backup Strategy**: Always commit working states before major changes
2. **Incremental Approach**: Small, testable changes are safer than large refactors
3. **Test Coverage**: Maintain working tests to catch regressions early
4. **Import Management**: Keep imports clean and organized to prevent cascading errors

### Next Session Instructions
When starting a new session, focus on:
1. **Verify Current State**: Run tests and check app initialization
2. **Identify Next Feature**: Choose the next logical UI component to rebuild
3. **Implement Incrementally**: Make small, testable changes
4. **Commit Frequently**: Each working feature gets its own commit
5. **Document Progress**: Update this file with completed work

### Files to Monitor
- `main_dash.py` - Main application entry point
- `tests/test_dash_app.py` - Test suite for verification
- `pages/` - UI components that need rebuilding
- `callbacks/` - Dash callback functions
- `controllers/` - Business logic (should be stable)

### Success Metrics
- Tests passing: 13/13 ✅
- App initializes without errors ✅
- Interface components work as expected ✅
- Visual consistency maintained ✅
- User experience preserved ✅
- Professional stats system functional ✅

## 🚀 CURRENT PROJECT STATUS (Phase 12 - July 2025)

### Migration Complete (100%)
The **Streamlit to Dash migration** is **100% completed** with all 11 phases successfully implemented:
- Full UI migration with responsive design
- Complete backend independence from Streamlit
- Real-time webhook integration with Google Calendar
- Role-based access control with proper restrictions

### Professional Stats System (80% Complete)
**Phase 12: Professional Player Statistics** is **80% functional** with:

#### ✅ **Completed Components:**
1. **Database Schema Extended**: `is_professional`, `wyscout_id` fields added to Player model
2. **Professional Stats Model**: 50+ statistical metrics (goals, assists, defensive actions, etc.)
3. **Thai League Controller**: Automated data extraction from GitHub repository with fuzzy matching
4. **Form Integration**: Professional player checkbox with automatic Thai League search
5. **Conditional UI System**: Tab-based interface for professional players
   - **Info Tab**: Reuses original layout (maximum code reuse achieved)
   - **Stats Tab**: Professional statistics with placeholder visualizations

#### ✅ **Key Technical Achievements:**
- **Maximum Code Reuse**: Info tab uses original elements without duplication
- **Dynamic Visibility Control**: Stats tab shows only professional content
- **No DOM Conflicts**: Eliminated "Multiple objects found" errors
- **Seamless UX**: Amateur players see original interface, professionals get enhanced tabs

#### 🎯 **Next Steps (Phase 12.5 - Remaining 20%):**
- **Plotly Visualizations**: Evolution charts, radar plots, comparative analysis
- **Data Normalization**: Position and age-based statistical adjustments  
- **ML Preparation**: Feature engineering and CRISP-DM methodology foundation

## CSS Architecture Optimization & Cleanup - **COMPLETED** (Agosto 2025)

### **Migration from Inline Styles to CSS Variables**
Successfully migrated all hardcoded colors and styles to a centralized CSS variables system for better maintainability and consistency.

### ✅ **Achievements Completed:**
- **Corporate Color Standardization**: Migrated 100+ hardcoded color instances to CSS variables system
- **CSS Variables Implementation**: Created 52 centralized variables for colors, spacing, typography, and effects
- **Streamlit Legacy Cleanup**: Eliminated all Streamlit-specific CSS code (data-testid, st-emotion-cache, streamlit-* selectors)
- **Architecture Consolidation**: Unified CSS architecture using Bootstrap + custom variables approach
- **Code Optimization**: Reduced CSS file size while maintaining 100% visual functionality
- **Focus States Fix**: Resolved tab focus styling issues maintaining accessibility

### **Technical Implementation:**
- **Primary Colors**: `--color-primary: #24DE84` with alpha variations (10%, 30%, 40%, 50%, 80%)
- **Spacing Variables**: Consistent padding, margins, and sizing across components
- **Typography System**: Standardized font weights, sizes, and line heights
- **Effect Variables**: Transitions, shadows, and hover effects
- **Bootstrap Integration**: Seamless integration with existing Bootstrap utilities

### **Migration Statistics:**
- **Files Modified**: 8 files across pages, callbacks, and components
- **Inline Styles Migrated**: 102 instances converted to CSS classes/variables
- **CSS Lines Optimized**: ~150 lines of legacy code removed
- **Architecture Benefit**: Single source of truth for all visual styling

### **Files Enhanced:**
- `/assets/style.css` - Central CSS variables system and legacy cleanup
- `/callbacks/settings_callbacks.py` - 22 instances migrated
- `/pages/ballers_dash.py` - 25 instances migrated  
- `/pages/settings_dash.py` - 30 instances migrated
- `/pages/administration_dash.py` - 11 instances migrated
- `/callbacks/administration_callbacks.py` - 5 instances migrated
- `/callbacks/navigation_callbacks.py` - 4 instances migrated
- `/common/upload_component.py` - 4 instances migrated
- `/common/login_dash.py` - 1 instance migrated

#### **Latest Commit:** `58e8d35` - CSS architecture optimization with centralized variables system

### Development Environment Ready
- **Database**: SQLite with professional extensions
- **Controllers**: ThaiLeagueController with 5 seasons of data (2020-2025)
- **UI**: Conditional tabs system fully functional
- **CSS Architecture**: Optimized with centralized variables system
- **Testing**: All 13 tests passing, app initializes without errors

**Ready for**: Implementation of advanced Plotly visualizations and ML preparation features.