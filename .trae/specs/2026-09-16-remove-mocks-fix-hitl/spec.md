# Remove Mocks & Fix HITL Gap (Finance Copilot Module) - Product Requirements Document

## Overview
- **Summary**: Convert the AI Bond Copilot Finance module from 100% static/mock service stubs to real DB-persisted CRUD operations; close the CRITICAL Human-in-the-Loop (HITL) security gap where any authenticated user could approve anything; remove hardcoded frontend mock fallbacks; and wire real LLM calls in place of TS/JSON mocks.
- **Purpose**: The previous audit found the finance module in a scaffolded-only state (44 functions returning SAMPLE_* constants, 0 DB migrations, router endpoints with zero RBAC gating on approve operations, frontend falling back to hardcoded dashboard objects, copilot chat as pure TS mock). This spec covers converting that scaffolding into a working dynamic system.
- **Target Users**: Finance operations teams, reviewers, auditors, admins using the AI Bond Copilot module within this Open WebUI fork.

## Goals
- **G1**: Every one of the 44 finance_service functions operates against real DB persistence via SQLAlchemy models; no SAMPLE_* constants remain in hot code paths.
- **G2**: Alembic migration scripts exist for all 17 finance ORM models; migration applies cleanly against an empty SQLite test DB.
- **G3 (CRITICAL)**: All three approve endpoints enforce role/permission gating so only admin OR users with explicit `finance.approve` permission (or equivalent) can approve journal / review / commentary items.
- **G4**: FinanceApproval ORM table (currently defined but unused) becomes the authoritative record of every approval, with timestamp, user id, and entity FK.
- **G5**: Finance Copilot Chat UI emits real chat completions requests, not hardcoded if/elif keyword-matched JSON mock; user's existing configured Open WebUI models are used.
- **G6**: Finance dashboard page shows true loading/error states; never silently substitutes a fake 82-bond defaultDashboard object when API fails.
- **G7**: finance_service.generate_commentary/rationale calls real LLM inference, not hardcoded paragraphs.
- **G8**: Persistence round-trip tests pass for every write-op (create X → list/query returns X with same PK).
- **G9**: Negative HITL tests pass (user with role=user and no explicit finance.approve perm gets HTTP 403 from all 3 approve endpoints).

## Non-Goals
- **NG1**: Care-giving / patient-triage / "Bond Ultimatum care workflow" domain — this is explicitly out of scope in this fix iteration as it requires a new greenfield domain, product definition, and is not a "fix the gaps" action on existing code. A separate spec will be required when product decides on scope.
- **NG2**: Any changes to non-finance Open WebUI routes, models, or services outside what is minimally required to satisfy has_permission() patterns.
- **NG3**: UI/UX redesign of finance pages; this scope only removes mock fallbacks and ensures true state (loading/error/empty) renders.
- **NG4**: New PDF/CSV export formats beyond what endpoints already support (format-preserving but use live DB data).

## Background & Context
- Previous audit (2026-09-16 session) produced 29× 🔴/⚪ validation row results with 0% true working logic for the finance module. Key evidence:
  - Module docstring in `finance_service.py:1-8` states "Provides stub implementations that return realistic sample data".
  - Runtime test `create_period() → new_id; list_periods() → still 3 items unchanged` proves writes are NO-OP.
  - Runtime test `MockUser("just-registered-user-42", role="user").approve_review()` returned `status=approved reviewed_by=just-registered-user-42` proving HITL bypass.
  - `FinanceCopilotChat.svelte:29-152` uses pure TS `generateMockResponse(query)` with JSON.stringify constants.
  - `finance/+page.svelte:14-60` `defaultDashboard` fallback (82 bonds, SGD 45.2M, Sep 2026) catches API errors and renders fake numbers.
  - 17 ORM classes in `models/finance.py` exist but zero alembic migration scripts reference any `finance_*` table.

## Functional Requirements
- **FR-1 (DB)**: Each of the 17 ORM finance tables has a corresponding DB table post-migration; all CRUDs write/query via SQLAlchemy `AsyncSession` (`get_async_session` DI pattern, same as rest of Open WebUI routers).
- **FR-2 (Service)**: All 44 public callables in finance_service.py (dashboard, periods CRUD, documents CRUD, extraction, reconciliation, movements, schedule/journals, audit schedule, commentary, review, approvals, audit trail, exceptions, export) return DB-backed data.
- **FR-3 (RBAC Approve)**: `POST /api/v1/finance/journals/{id}/approve`, `POST /api/v1/finance/review/approve`, `POST /api/v1/finance/commentary/{id}/approve` all enforce `role == 'admin' OR has_permission(user_id, 'finance.approve', permissions_config, db)`. Fail returns HTTP 403 ERROR_MESSAGES.ACCESS_PROHIBITED.
- **FR-4 (HITL — Defense in Depth)**: Equivalent permission check is ALSO performed inside `finance_service.approve_journal()`, `finance_service.approve_review()`, `finance_service.approve_commentary()`, passing user_id and db session. Service layer raises PermissionError if check fails; router translates to HTTP 403. (This ensures any future non-HTTP callers of service still get gating.)
- **FR-5 (FinanceApproval Record of Truth)**: On every successful approval, `FinanceApproval.insert()` creates a row with columns: id, entity_type (journal/review/commentary), entity_id (uuid FK), approved_by (user.id), approved_at (utcnow), note (optional).
- **FR-6 (Copilot Real AI)**: `FinanceCopilotChat.svelte` removes `generateMockResponse` and uses same chat flow as main Open WebUI chat (`$chatApi.generateChatCompletion` or direct fetch to `/api/chat/completions`) with `model`, `messages`, optionally `tools: finance_copilot tools array` enabling function-calling against finance data.
- **FR-7 (Dashboard No Fallback)**: `finance/+page.svelte` — delete `defaultDashboard` constant. In catch() block: set `error = $t('Failed to load dashboard'); dashboard = null`. Render spinner while loading; render AlertBanner on error; render EmptyState when dashboard.bond_line_items empty and no error.
- **FR-8 (LLM Commentary)**: `finance_service.generate_commentary(period_id)` and similar LLM-annotated functions accept model parameter and call an existing Open WebUI LLM utility (e.g. same path used by `/api/chat/completions` / tasks wrapper) rather than returning SAMPLE_COMMENTARY.
- **FR-9 (Export)**: CSV export generators query real tables and write true rows.

## Non-Functional Requirements
- **NFR-1 (Performance)**: Dashboard GET loads in < 2 seconds with 1000 test BondRecord rows on SQLite local; no linear scans across all periods without user_id/period_id filter.
- **NFR-2 (Security)**: Zero RBAC bypass on approve endpoints per negative test matrix (role=user / role=admin / user + explicit finance.approve perm / user without perm → 4 combinations each on 3 endpoints = 12 request-cases asserted).
- **NFR-3 (Backward Compat)**: All router shapes (path, request form schema fields, response top-level keys) remain identical to current router shapes so existing frontend API calls do not break. Values now return real data instead of sample.
- **NFR-4 (Migration Safety)**: Alembic upgrade/downgrade both run idempotently. No destructive schema-only drops on downgrade.
- **NFR-5 (Traceability)**: log_audit_trail entries actually persisted to FinanceAuditLog table (not returned from memory).

## Constraints
- **Technical**: Must stay on existing FastAPI + SQLAlchemy 2.0 async + Alembic stack. RBAC pattern MUST mirror existing `open_webui.utils.access_control.has_permission` + `Config.get('user.permissions')` pattern used in routers/calendar.py:45, routers/skills.py:129, routers/chats.py:232, etc.
- **Technical**: All new permission keys added must be namespaced `finance.*` (e.g. `finance.approve`).
- **Business**: Cannot modify existing non-finance user permission defaults out of the box; finance.approve must be opt-in per user/group (admin bypass allowed for admin role already, same as calendar/skills patterns).
- **Dependencies**: Reuse existing storage provider for document file content upload path; no new S3 libraries.
- **Dependencies**: LLM call path must reuse Open WebUI's existing model/key pipeline rather than introducing raw httpx calls with raw API keys directly in finance_service.

## Assumptions
- **A-1**: The existing `Finance*Table.insert/get_by_id/list/query/update/delete` methods in `models/finance.py` are syntactically correct (they follow same pattern as other models files) — we simply haven't invoked them yet. If any have runtime errors they will be fixed in flight.
- **A-2**: `has_permission()` from `open_webui.utils.access_control` correctly handles unknown permission keys by returning False (so users without explicit `finance.approve` default-deny until admin grants). Will verify at runtime during tests.
- **A-3**: Document file uploads (content storage) can proceed through same `/api/v1/files/upload` flow already defined in routers/files.py; FinanceDocument.file_id FKs to File.id.
- **A-4**: Same LLM wrapper used by `/api/chats` for chat completions can be reused by commentary generation; if finance_service needs a non-stream synchronous wrapper we'll use task queue or a synchronous generate call within same config context.

## Acceptance Criteria

### AC-1: Finance tables actually exist post-alembic upgrade
- **Type**: `rule`
- **Given**: Empty SQLite test database + alembic.ini alembic configured.
- **When**: Run `alembic upgrade head`.
- **Then**: Query PRAGMA table_list returns rows for all 17 table names: finance_reporting_period, finance_document, finance_extraction_job, finance_bond_record, finance_bond_source_record, finance_reconciliation_run, finance_reconciliation_item, finance_bond_movement, finance_bond_schedule_line, finance_journal, finance_journal_line, finance_audit_schedule_entry, finance_commentary, finance_approval, finance_exception, finance_audit_log, finance_source_reference.
- **Pass Condition**: 17 distinct names returned count == 17.
- **Evidence**: SQLite CLI dump or SQLAlchemy `inspect(tables).keys()` output captured.

### AC-2: ReportingPeriod CRUD round-trip
- **Type**: `rule`
- **Given**: DB migrated (per AC-1); no periods yet.
- **When**: HTTP POST /api/v1/finance/periods create period; then HTTP GET /api/v1/finance/periods list.
- **Then**: List count increments from 0 → 1; returned list item id equals create response id; name/status match input exactly.
- **Pass Condition**: Assert `len(list_periods_before) + 1 == len(list_periods_after) AND new_id in [p.id for p in list_periods_after]`
- **Evidence**: httpx post/response + get JSON bodies captured, id equality assertion output.

### AC-3: Equivalent CRUD round-trip for Documents, Journals, Commentary, Exceptions
- **Type**: `rule`
- **Given**: AC-2 passes, same test DB.
- **When**: create + list performed for 4 entity types (document, journal, commentary, finance_exception).
- **Then**: Each individual entity: count increments by exactly 1; created entity present in list.
- **Pass Condition**: 4 passes (document pass AND journal pass AND commentary pass AND exception pass) all == True.
- **Evidence**: 4 individual assertion results concatenated.

### AC-4 (CRITICAL): HTTP 403 Forbidden for user-role without explicit finance.approve
- **Type**: `rule`
- **Given**: 3 approve endpoints + user with role=user and NO explicit `finance.approve` permission set in `Config.get('user.permissions')`.
- **When**: 3 POSTs (approve journal, approve review, approve commentary) sent with JWT/session of unprivileged user.
- **Then**: All 3 responses return `status_code == 403`. No FinanceApproval rows inserted.
- **Pass Condition**: 3/3 endpoints give HTTP 403 AND post-test `SELECT COUNT(*) FROM finance_approval == 0`.
- **Evidence**: 3 response status_code values captured (one per endpoint) plus DB count.

### AC-5: Admin role bypass works (approve succeeds)
- **Type**: `rule`
- **Given**: user.role == 'admin'.
- **When**: Same 3 approve endpoint POSTs.
- **Then**: 3 responses 200 OK; 3 FinanceApproval rows inserted (approved_by == admin_user_id).
- **Pass Condition**: 3/3 == 200 AND row count == 3.
- **Evidence**: 3 response codes + DB query.

### AC-6: Explicit finance.approve permission works for user-role
- **Type**: `rule`
- **Given**: user.role == 'user' BUT `user.id` is granted `'finance.approve': true` in permissions config (via has_permission matrix).
- **When**: 3 approve endpoint calls.
- **Then**: 3 success 200s.
- **Pass Condition**: 3/3 == 200.
- **Evidence**: 3 response codes.

### AC-7: Service layer defense in depth
- **Type**: `rule`
- **Given**: Direct Python import call (NOT HTTP) to `finance_service.approve_review(user_id=unprivileged_user_id, ..., db=session)`.
- **When**: Call function directly with unprivileged user_id to bypass router.
- **Then**: Raises PermissionError (or custom HTTPException equivalent for non-HTTP caller); no FinanceApproval row.
- **Pass Condition**: Exception thrown AND row count == 0.
- **Evidence**: Exception traceback + DB count.

### AC-8: FinanceApproval is record of truth
- **Type**: `rule`
- **Given**: 10 successful approval operations (mixed types, mixed users).
- **When**: `SELECT COUNT(*) FROM finance_approval WHERE entity_type IN ('journal','review','commentary')`.
- **Then**: Count == 10; every row approved_at <= now; approved_by FKs match calling user_id; entity_id references exist.
- **Pass Condition**: Count assertions AND referential integrity checks.
- **Evidence**: SQL query output.

### AC-9: dashboard query returns DB-backed bonds not SAMPLE_*
- **Type**: `rule`
- **Given**: 15 real BondRecord rows inserted (via CRUD endpoints); zero rows == 142 sample_bonds_1.25B.
- **When**: `GET /api/v1/finance/dashboard?period_id=...`.
- **Then**: `dashboard.total_bonds == 15` AND `sum(b.market_value for b in dashboard.bond_line_items)` equals sum persisted (not SAMPLE's SGD 45.2M / 1.25B constants).
- **Pass Condition**: Count assertion + sum inequality against known sample sum.
- **Evidence**: Response JSON, sum computed, inequality comparison boolean True.

### AC-10: Frontend shows loading/error/empty NOT fake fallback
- **Type**: `rule`
- **Given**: Browser visits `/finance` while backend stopped (guaranteed API failure).
- **When**: Wait 3s for loading + catch() block.
- **Then**: DOM contains `role="alert"` with text "Failed to load dashboard" OR localized equiv; DOM does NOT contain 82 bond count anywhere (check defaultDashboard removed).
- **Pass Condition**: Alert present AND defaultDashboard string const absent from compiled JS bundle.
- **Evidence**: browser_snapshot DOM refs + grep for defaultDashboard in `src/routes/(app)/finance/+page.svelte` == count 0.

### AC-11: FinanceCopilotChat.svelte uses real chat API (not generateMockResponse)
- **Type**: `rule`
- **Given**: User types "what's pending review?" into finance copilot chatbox.
- **When**: Network tab inspection of browser XHR/fetch requests (1 POST URL `/api/chat/completions` OR `/api/v1/...chat...` matching same pattern main chat uses).
- **Then**: A real HTTP POST occurs with JSON body containing `{model, messages[{role:user, content:"what..."}]}`. Response content NOT produced by if/elif in TS.
- **Pass Condition**: At least 1 real network POST captured for copilot query; `generateMockResponse` identifier absent from svelte file (grep count == 0).
- **Evidence**: browser_network_requests list + grep output.

### AC-12: Commentary generation calls real LLM
- **Type**: `rubric`
- **Dimension**: LLM call realism & non-determinism for different inputs
- **Scale**: 1-5
  - 1 = Still returns constant/hardcoded string
  - 3 = Calls a wrapper fn but doesn't vary output per period_id inputs
  - 5 = Calls existing Open WebUI LLM generate pipeline with actual prompt/period context; responses vary with different period id; JSON trace confirms tokens generated
- **Pass Threshold**: >= 4
- **Evidence**: LLM call stack trace captured (logging + two differing input period-ids → two different content responses).

### AC-13: Export CSV row count matches DB
- **Type**: `rule`
- **Given**: 32 test BondRecord rows.
- **When**: `GET /api/v1/finance/export/bonds.csv` then rows count (minus header line).
- **Then**: Rows count == 32.
- **Pass Condition**: Integer equality.
- **Evidence**: CSV bytes downloaded split('\n') count - 1 == 32.

### AC-14: Zero SAMPLE_ constants active in hot return paths
- **Type**: `rule`
- **Given**: Source `services/finance_service.py`.
- **When**: AST parse or manual walk of every function body.
- **Then**: Zero return statements returning direct references to `SAMPLE_*` constants (i.e., return SAMPLE_PERIODS, return SAMPLE_DASHBOARD, return SAMPLE_COMMENTARY patterns). Init-time or empty-list seed defaults for test fixtures allowed (e.g. if no periods exist seed demo data ONCE with INSERT for first admin only? but never constant-only returns).
- **Pass Condition**: Grep for `return SAMPLE_` count == 0.
- **Evidence**: grep `return SAMPLE_` finance_service.py output lines 0.

## Open Questions
- [ ] **OQ-1**: For empty-on-first-install behavior — should the finance module auto-seed 1 demo period + sample test bonds for the FIRST admin user ONLY (with UI badge "Demo data — click here to delete"), OR always show true empty-state screen and let admin click "Seed demo" button? (Recommendation: latter, to keep determinism.)
- [ ] **OQ-2**: Should commentary LLM call be streaming (SSE to dashboard) or sync generate + return in commentary response JSON? (Recommendation: sync stored persisted commentary rows with refresh LLM button.)
- [ ] **OQ-3**: For document upload storage path — reuse existing files table + storage provider (assumption A-3), or create separate FinanceDocument storage table? (Recommendation: reuse + FK file_id.)
