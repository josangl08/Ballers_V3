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

## 🚀 PROJECT STATUS REFERENCE

### Current State Summary
The project has **completed the Streamlit to Dash migration (100%)** and is now in advanced functionality development phase. For detailed chronological information about phases and milestones, see **PROYECTO_STATUS.md**.

### Development Methodology
- **Incremental Development**: Small, functional changes with frequent commits
- **Commit Strategy**: Each working feature gets its own commit
- **No AI Attribution**: Commits should appear as if created by the human developer
- **Quality Focus**: Code must pass tests and work correctly before committing

### Key Architectural Achievements
- **Zero Streamlit Dependencies**: Complete migration to Dash architecture
- **Real-time Webhook Integration**: Google Calendar SSE system (sub-100ms latency)
- **Role-based Access Control**: Complete restrictions for admin/coach/player
- **Professional Stats System**: 95% complete with ML baseline
- **Machine Learning Analytics**: 85% complete with CRISP-DM methodology

### Current Architecture Status

#### **Real-time Webhook System**:
```
Google Calendar ──webhook──▶ Flask Server ──▶ calendar_sync_core ──▶ Database
     (events)       (port 8001)    (real-time)       (sessions)
                         │
                         ▼
                 NotificationController ──▶ Dash UI
                   (event tracking)      (real-time updates)
```

#### **Technical Achievements**:
- **Webhook Server**: Flask-based server running on localhost:8001
- **Real-time Processing**: Events processed immediately upon Google Calendar changes
- **Development Setup**: HTTP webhook endpoint for local development
- **Fallback System**: Manual sync remains available as backup
- **UI Integration**: Real-time updates reflected in Dash interface

### Development Guidelines

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

### Success Metrics
- Tests passing: 13/13 ✅
- App initializes without errors ✅
- Interface components work as expected ✅
- Visual consistency maintained ✅
- User experience preserved ✅
- Professional stats system functional ✅

## 🏗️ TECHNICAL ARCHITECTURE DETAILS

### CSS Architecture (Current Implementation)
**Centralized Variables System**: Successfully migrated to CSS variables for maintainability

#### **Technical Implementation:**
- **Primary Colors**: `--color-primary: #24DE84` with alpha variations (10%, 30%, 40%, 50%, 80%)
- **Spacing Variables**: Consistent padding, margins, and sizing across components
- **Typography System**: Standardized font weights, sizes, and line heights
- **Effect Variables**: Transitions, shadows, and hover effects
- **Bootstrap Integration**: Seamless integration with existing Bootstrap utilities

#### **Key Files:**
- `/assets/style.css` - Central CSS variables system
- Pages and callbacks - Migrated from inline styles to CSS classes

### Professional Stats System Architecture
**Hybrid Platform**: Local training center + Professional analytics integration

#### **Database Schema:**
- **Player Model Extensions**: `is_professional`, `wyscout_id` fields
- **Professional Stats Model**: 50+ statistical metrics (goals, assists, defensive actions, etc.)
- **Thai League Controller**: Automated data extraction with fuzzy matching

#### **UI Architecture:**
- **Conditional Tabs System**: Info/Stats tabs for professional players only
- **Maximum Code Reuse**: Info tab reuses original amateur layout
- **Dynamic Visibility Control**: Stats tab shows only professional content

### Machine Learning System
**CRISP-DM Methodology**: Academic-grade ML implementation

#### **Components:**
- **Dataset**: 2,359 records × 127 columns (5 Thai League seasons)
- **Feature Engineering**: 41 non-circular features validated
- **Models**: Linear, Ridge, Ensemble baseline (MAE 0.774, R² 0.950)
- **Validation**: 5-fold cross-validation with statistical significance tests

### Development Environment Status
- **Database**: SQLite with professional extensions
- **Controllers**: ThaiLeagueController with 5 seasons of data (2020-2025)
- **UI**: Conditional tabs system fully functional
- **CSS Architecture**: Optimized with centralized variables system
- **Testing**: All 13 tests passing, app initializes without errors

---

**For project chronology and detailed phase information, see PROYECTO_STATUS.md**
