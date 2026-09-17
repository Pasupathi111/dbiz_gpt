# AI Bond Copilot — Architecture Document

## 1. Existing OpenWebUI Architecture

### Frontend
- **Framework**: SvelteKit (Svelte 5) + TypeScript
- **Styling**: Tailwind CSS v4, dark mode via `class`
- **Components**: `src/lib/components/` — layout, chat, admin, workspace, common
- **Routes**: `src/routes/(app)/` — chat, workspace, notes, automations, calendar, playground, admin
- **State**: Svelte stores in `src/lib/stores/`
- **APIs**: `src/lib/apis/` — typed fetch wrappers
- **i18n**: i18next
- **Navigation**: Sidebar with pinned menu items system (`isMenuItemVisible`, `getMenuItemMeta`)

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLAlchemy (async) + Alembic migrations, SQLite/PostgreSQL
- **Auth**: JWT tokens, bcrypt/argon2, OAuth
- **Models Pattern**: SQLAlchemy `Base` table + Pydantic schema + `Table` class with static CRUD methods
- **Routers**: `backend/open_webui/routers/` — one file per domain
- **File Storage**: `backend/open_webui/models/files.py` — metadata in DB, files on disk
- **AI Integration**: OpenAI, Anthropic, Google via SDKs; tool/function calling system
- **Background Jobs**: APScheduler
- **WebSocket**: socket.io for real-time updates

## 2. Bond Copilot Extension Strategy

### What to Reuse
- Authentication & user management
- File upload infrastructure (`/api/v1/files`)
- Chat system for conversational AI
- Tool/function calling framework
- Sidebar navigation system
- Common UI components (Spinner, Tooltip, Modal, etc.)
- Database infrastructure (SQLAlchemy, Alembic)
- WebSocket for real-time status

### What to Extend
- Sidebar: add "Finance Copilot" navigation item
- Roles: add finance_user, finance_manager, auditor permissions
- File processing: add Excel/PDF bond extraction pipeline
- Tools: register bond-specific AI tools

### What to Create New
- Finance Copilot frontend module: `src/lib/components/finance/`
- Finance routes: `src/routes/(app)/finance/`
- Backend finance module: `backend/open_webui/models/finance/` + `routers/finance/`
- Bond data models, reconciliation engine, movement detection
- AI service abstraction for financial operations

## 3. Database Entities

| Entity | Purpose |
|--------|---------|
| ReportingPeriod | Monthly period context |
| FinanceDocument | Uploaded UBS/LGI/schedule files |
| DocumentVersion | Version tracking per document |
| ExtractionJob | Processing pipeline tracking |
| BondRecord | Normalized canonical bond data |
| BondSourceRecord | Raw source-specific values |
| ReconciliationRun | Reconciliation execution record |
| ReconciliationItem | Per-bond reconciliation result |
| BondMovement | Movement classification per bond |
| BondSchedule | Generated monthly schedule |
| BondScheduleLine | Individual schedule line items |
| Journal | Draft accounting journal |
| JournalLine | Journal debit/credit lines |
| AuditScheduleEntry | Audit-ready schedule rows |
| Commentary | AI-generated month-end commentary |
| FinanceApproval | Approval workflow records |
| FinanceException | Data exceptions and resolutions |
| FinanceAuditLog | Immutable audit trail |
| SourceReference | Traceability to source doc/cell |

## 4. API Design

All APIs under `/api/v1/finance/`:

- `POST /documents/upload` — Upload bond documents
- `GET /documents` — List documents for period
- `POST /documents/{id}/process` — Trigger extraction
- `GET /periods` — List reporting periods
- `POST /periods` — Create reporting period
- `GET /bonds` — Query bond records
- `POST /reconciliation/run` — Execute reconciliation
- `GET /reconciliation` — Get reconciliation results
- `GET /reconciliation/exceptions` — Get exceptions
- `POST /movements/analyze` — Detect movements
- `GET /movements` — Get movement analysis
- `POST /schedule/generate` — Generate bond schedule
- `GET /schedule` — Get current schedule
- `POST /journals/generate` — Generate draft journals
- `GET /journals` — List journals
- `POST /journals/{id}/approve` — Approve journal
- `POST /audit-schedule/generate` — Generate audit schedule
- `GET /audit-schedule` — Get audit schedule
- `POST /commentary/generate` — Generate commentary
- `GET /commentary` — Get commentary
- `POST /review/submit` — Submit for review
- `POST /review/approve` — Approve output
- `POST /review/reject` — Reject output
- `GET /audit-trail` — Query audit trail
- `GET /dashboard` — Dashboard KPI data

## 5. UI Screens

All under `/finance/` route:

1. Dashboard — KPI cards, processing timeline, status overview
2. Workspace — Period selection, step progress
3. Documents — Upload, preview, status
4. Extraction Review — Side-by-side original vs extracted
5. Bonds — Data explorer with filtering
6. Reconciliation — Variance dashboard, exception drill-down
7. Movements — Movement analysis with AI explanations
8. Schedule — Generated bond schedule with export
9. Journals — Draft journals with approval
10. Audit Schedule — Audit-ready schedule
11. Commentary — AI month-end commentary
12. Review — Approval workflow
13. Audit Trail — Immutable log viewer
14. Settings — Finance module configuration

## 6. Design Reference

UI follows enterprise SaaS pattern (Casework OS style):
- Left sidebar with workspace sections + numbered nav items
- Main content with breadcrumb header
- KPI stat cards with sparklines
- Professional data tables with status badges
- Right panel for contextual AI assistant
- Processing timeline indicators
- Clean typography, consistent spacing
- Purple/indigo accent palette for finance branding
