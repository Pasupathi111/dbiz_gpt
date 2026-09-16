# Remove Mocks & Fix HITL Gap (Finance Copilot Module) - Implementation Plan

## Overview
This file maps the 14 Acceptance Criteria in spec.md to 10 ordered atomic implementation tasks. Priority ordering: P0 foundations/security first, then P1 AI/UI wiring, then P2 verification.

**Dependency Graph:**
Task 1 (migrations) → Task 2 (service layer wire-up) → Task 3 (HITL/security) → Task 4/5/6 (parallel: copilot + dashboard UI + LLM commentary) → Task 7 (exports) → Task 8-10 (tests/verification)

---

## Task 1: Alembic Migrations for 17 Finance Tables
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Create new alembic revision (following existing pattern in migrations/versions/) that creates all 17 finance_* tables defined in `backend/open_webui/models/finance.py`.
  - Verify upgrade creates every table; verify downgrade drops them.
  - Use same migration style conventions as existing revisions (e.g. `7e5b5dc7342b_init.py` style).
  - Foreign keys where applicable: `finance_journal_line.journal_id → finance_journal.id`, `finance_reconciliation_item.run_id → finance_reconciliation_run.id`, `finance_bond_source_record.bond_record_id → finance_bond_record.id`, `finance_approval.* entity_id FK patterns (entity_type + entity_id polymorphic, no hard FK needed since multiple entities)`.
  - Add indexes on `period_id`, `status`, `created_at` for large-table performance.
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `rule` TR-1.1: Apply `alembic upgrade head` on fresh SQLite; run `SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'finance_%'` → row count == 17; command-line diffed list matches spec AC-1 list exactly. Evidence: bash output.
  - `rule` TR-1.2: Downgrade step `alembic downgrade -1` → 17 tables no longer present. Subsequent upgrade recreates them idempotently. Evidence: re-run SELECT returns 0 then 17.
  - `rubric` TR-1.3: Migration code quality & conventions match existing revisions. Scale 1-5, 1=no indexes/raw SQL comment only 3=works 5=all FKs, indexes, naming matches existing conventions. Threshold >= 4. Evidence: diff against existing revision pattern.

---

## Task 2: Wire finance_service.py for Real CRUD (Remove All SAMPLE_* Returns)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - For each of the 44 functions in `finance_service.py`:
    1. Replace return of `SAMPLE_*` constant with actual ORM Table class call using `AsyncSession` (add `db: AsyncSession = Depends(get_async_session)` or pass db explicitly via function param since it's a service).
    2. All functions accept optional `db: AsyncSession` parameter consistent with existing ORM call patterns used in other routers.
    3. Dashboard aggregates from BondRecord JOIN BondScheduleLine JOIN Journal if period_id filter passed.
    4. Export CSV writers read from ORM query not sample arrays.
    5. Audit trail writes actually INSERT to FinanceAuditLog table (not just appended to list constant).
    6. Extraction / Reconciliation / Movement / Schedule functions return true query results; if logic is complex for a specific engine (e.g. reconciliation diff algorithm) we will implement a basic correct algorithm (not stub) — line-by-line diff for source_bond_records vs book_bond_records per reporting_period_id.
    7. At end of refactor: `grep -c "return SAMPLE_" services/finance_service.py` MUST equal 0.
    8. Keep `SAMPLE_*` module constants as optional `seed_demo_data(period_id, db)` helper ONLY triggered manually by admin via seed endpoint (to be implemented if OQ-1 answered); don't delete constants yet, just never return them directly from hot getters.
  - Router endpoints require no request/response schema change since they already forward to service — they only pass db session parameter now.
- **Acceptance Criteria Addressed**: AC-2, AC-3, AC-9, AC-14, partial AC-13 (exports)
- **Test Requirements**:
  - `rule` TR-2.1 (Period round-trip): Create period → list count += 1 → get-by-id matches created → update name → get matches updated name → delete → list count decrements. All 4 ops against DB. Evidence: httpx JSON request/responses.
  - `rule` TR-2.2 (Document/Journal/Commentary/Exception round-trip 4-entity matrix): Same 4 CRUD ops × 4 entity types = 16 assertions. All 16 == True. Evidence: table of results.
  - `rule` TR-2.3 (Dashboard not sample): Insert 15 real BondRecord rows; GET dashboard → total_bonds == 15 AND sum != known sample 1.25B constant. Evidence: dashboard JSON response sum calculated vs sample sum inequality assert.
  - `rule` TR-2.4 (Zero SAMPLE_ return paths): grep `return SAMPLE_` services/finance_service.py output line count == 0. Evidence: shell command output.
  - `rule` TR-2.5 (Audit trail write): POST create_doc triggers log_audit_trail → get_audit_trail contains 1 new row matching action. Evidence: DB count before/after delta == 1.
  - `rubric` TR-2.6: Reconciliation algorithm quality. Scale 1-5. 1=stub returned 3=basic exact-match diff 5=handles partial match fuzzy/case-insensitive and groups match/partial/mismatch statuses. Threshold >= 3 for this round. Evidence: sample test cases with 2 matches, 2 mismatches, 2 partials produce correct count.

---

## Task 3: HITL Security — RBAC on 3 Approve Endpoints + Service Defense in Depth + FinanceApproval Records
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1 (needs FinanceApproval table migrations from Task 1), partially Task 2 (but security gates are applied orthogonally on approve)
- **Description**:
  - **Router layer (finance.py):** Add permission check pattern on all 3 approve routes, exactly matching existing `routers/calendar.py:45`, `routers/chats.py:232` style:
    ```
    if user.role != 'admin' and not await has_permission(user.id, 'finance.approve', await Config.get('user.permissions'), db=db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    ```
  - **Service layer defense-in-depth (finance_service.py approve_*):** Each approve function accepts `user_id` + `db`, runs the EXACT SAME permission check inline. If fails raises PermissionError (router catches with HTTPException wrapper if needed).
  - **FinanceApproval inserts:** On SUCCESS ONLY, before returning approve response, call `FinanceApproval.insert()`: entity_type ∈ {'journal','review','commentary'}, entity_id, approved_by=user.id, approved_at=datetime.utcnow(), note optional.
  - **Router import additions:** `from open_webui.utils.access_control import has_permission; from open_webui.models.config import Config; from open_webui.constants import ERROR_MESSAGES`.
  - **get_pending_reviews** filter: Add WHERE `approved IS FALSE` (or status == pending) so already-approved items don't re-appear in queue.
- **Acceptance Criteria Addressed**: AC-4, AC-5, AC-6, AC-7, AC-8
- **Test Requirements**:
  - `rule` TR-3.1 (Unprivileged 403 × 3 endpoints): Build 3 httpx requests as user-role NO explicit perm → status codes == 403. Evidence: 3 httpbin-style status-code response snippets.
  - `rule` TR-3.2 (Admin 200 × 3 endpoints): 3 requests admin → status 200. Evidence: 3 200s.
  - `rule` TR-3.3 (Explicit perm user 200): Grant user id X finance.approve via permissions; 3 approve → 200 each. Evidence: 3 200s.
  - `rule` TR-3.4 (Service layer direct bypass test): Python direct `finance_service.approve_review(user_id=unpriv_id, ..., db=session)` → raises PermissionError. FinanceApproval count unchanged. Evidence: pytest raises assertion OR try/except block.
  - `rule` TR-3.5 (FinanceApproval record of truth): 10 mixed approve ops → DB count == 10; columns entity_type approved_by approved_at NOT NULL each row. Evidence: SELECT query output.

---

## Task 4: Finance Copilot Chat Real API Integration
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 2 (so copilot tools functions return real data not sample)
- **Description**:
  - In `src/lib/components/finance/FinanceCopilotChat.svelte`:
    1. DELETE entire `generateMockResponse(query)` function and all its 7 if/elif keyword branches and JSON.stringified literal return values.
    2. Replace with same pattern as main chat uses — import the `$chatApi` / `generateChatCompletion` or equivalent wrapper already imported in chat pages.
    3. Request body shape: `{ model: selectedModelId, messages: [{role:'user', content: query}], tools: [{type:'function', function: finance_copilot tools list defined in backend/tools/finance_copilot.py}], stream: true }` for interactive UX.
    4. Show model selector dropdown at top of copilot (reuse existing ModelSelector component from main chat).
    5. If response includes `tool_calls` block, render them as collapsible "Tool Result" sections exactly as main chat does for function tool calls.
    6. Catch HTTP errors → render AlertBanner "Copilot error: {status}".
- **Acceptance Criteria Addressed**: AC-11
- **Test Requirements**:
  - `rule` TR-4.1 (No mock function): grep `generateMockResponse` src/lib/components/finance/FinanceCopilotChat.svelte lines count == 0. Evidence: grep output.
  - `rule` TR-4.2 (Real XHR fired): Browser type query "pending review count" → browser_network_requests contains at least 1 POST whose URL path starts with `/api/chat/completions` (or `/api/v1/chat/` whatever main chat uses) AND request JSON body contains messages array. Evidence: network request list JSON.
  - `rubric` TR-4.3: Copilot UX parity with main chat (streaming tokens, tool calls renderable, history accumulates). Scale 1-5: 1=one-shot static 3=works but no stream 5=identical to main chat UX. Threshold >= 4. Evidence: screenshot of mid-stream copilot UI with 3 messages + 1 tool call rendered.

---

## Task 5: Finance Dashboard No Fake Fallback
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 2 (dashboard endpoint returns real or null)
- **Description**:
  - In `src/routes/(app)/finance/+page.svelte`:
    1. DELETE the entire inline `const defaultDashboard = { ... 82 bonds SGD 45.2M ... }` object.
    2. Add reactive state `error: string | null = null` and `empty = $derived(!error && !loading && dashboard && dashboard.bond_line_items?.length === 0)`.
    3. onMount catch() block: set `error = $t('Failed to load dashboard. Please try again or contact administrator if this persists.')`; `dashboard = null`.
    4. Template top-level `{#if loading}` render ProgressRadial / spinner (reuse existing `<Loading />` component if present elsewhere in app).
    5. `{:else if error}` render `<AlertBanner variant="error">{error}</AlertBanner>`. Use AlertBanner component pattern as found elsewhere in repo.
    6. `{:else if empty}` render EmptyState (reuse or create) — "No bonds for this period. Upload documents and run extraction first."
    7. Otherwise render dashboard data as before.
- **Acceptance Criteria Addressed**: AC-10
- **Test Requirements**:
  - `rule` TR-5.1 (defaultDashboard deleted): grep `defaultDashboard` src/routes/\(app\)/finance/+page.svelte == 0 lines. Evidence: grep output.
  - `rule` TR-5.2 (Shows error when backend off): Stop backend; visit /finance; wait 2s; browser_snapshot contains AlertBanner with text "Failed to load" OR localized. Evidence: snapshot ref + text.
  - `rule` TR-5.3 (Shows spinner briefly): Initial loading state before API completes. Evidence: browser snapshot taken <500ms into load shows `role="progressbar"` OR spinner class element exists.

---

## Task 6: Real LLM Call for Commentary/Rationale
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 1, Task 2
- **Description**:
  - Rewrite `finance_service.generate_commentary(period_id, user_id, model_id?, db)` in `finance_service.py`.
  - Query DB for actual period + bond totals + reconciliation pass/fail counts + journal pending count; form a prompt e.g.: `"Act as a fixed-income portfolio analyst. Summarize the bond portfolio for reporting period {name} ({date_range}): total bonds={n}, MV={currency}{sum}, reconciliation: mismatches={m_count}, pending journals={j_count}. Provide 4 short bullet: Portfolio Overview, Reconciliation Highlights, Risk Observations, Recommended Next Actions."`
  - Reuse existing Open WebUI LLM generation path (utils.models / utils.chat / tasks.generate or whatever router/chats.py calls for completions — inspect one working non-stream path to wire same calls).
  - Store resulting text to `Commentary.insert()` so future reads return persisted NOT regenerate. Add endpoint `POST /commentary/{id}/regenerate` to force-refresh.
  - Same for any other AI-named functions (e.g. `generate_movement_rationale` if exists) — pattern reuse.
- **Acceptance Criteria Addressed**: AC-12
- **Test Requirements**:
  - `rule` TR-6.1 (Non-determinism test): Call generate_commentary twice with different period_id inputs (period-A: 1 bond, period-B: 200 bonds + mismatches). Assert content strings are NOT equal AND length(content-B) > length(content-A). Evidence: two strings, diff output, inequality.
  - `rubric` TR-6.2 (Prompt & pipeline quality): Scale 1-5, 1=hardcoded returns 3=calls wrapper but generic 5=uses real model, period data accurate in prompt, stores to Commentary. Threshold >= 4. Evidence: log captures LLM call prompt, returned stored text excerpt, SELECT count(*) FROM finance_commentary increments by 1.

---

## Task 7: Exports Read Real DB
- **Status**: `pending`
- **Priority**: medium-low (coupled with Task 2 but verify separately)
- **Depends On**: Task 2
- **Description**:
  - Verify export endpoints (bonds CSV, journals CSV) query real tables. If Task 2 already rewrote them, do final pass + add header field names matching existing sample CSV schema to preserve API/frontend compat exactly (same column names = existing frontend "download CSV" buttons continue working).
  - Ensure Content-Disposition filename header preserved.
- **Acceptance Criteria Addressed**: AC-13
- **Test Requirements**:
  - `rule` TR-7.1 (32 bonds = 32 CSV rows): INSERT 32 BondRecords, call GET bonds.csv, response.body split by \n len - 1 header == 32. Evidence: int equality + sample rows.

---

## Task 8: Unit Test Harness (Python Pytest Tests) — HITL + Persistence Negative
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Task 1, 2, 3 complete
- **Description**:
  - Create test suite under `backend/tests/` or `tests/` (check existing test dirs, match pattern) with new file `test_finance_p0.py`.
  - Tests:
    - `test_period_crud_round_trip`
    - `test_document_crud`
    - `test_journal_crud`
    - `test_commentary_crud`
    - `test_exception_crud`
    - `test_approve_user_forbidden_router` (HTTP 403)
    - `test_approve_admin_success` (HTTP 200)
    - `test_approve_perm_user_success` (HTTP 200)
    - `test_approve_user_service_direct_permission_error`
    - `test_approval_record_of_truth`
    - `test_dashboard_returns_db_not_sample`
    - `test_export_bonds_csv_row_count_matches_db`
    - `test_log_audit_trail_persists`
  - Use in-memory SQLite async engine via FastAPI TestClient + dependency override for get_async_session pattern used in other test files.
- **Acceptance Criteria Addressed**: AC-2 through AC-9 + AC-13 + AC-14 (re-verifies all via test)
- **Test Requirements**:
  - `rule` TR-8.1: 13 tests pass when run via pytest. Evidence: pytest summary line `13 passed`.

---

## Task 9: Frontend Manual Test Matrix — Visual Snapshot Verification
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Tasks 4, 5 complete (UI code changes)
- **Description**:
  - Start backend + frontend dev server.
  - Login admin + normal user (two users).
  - Visit 14 finance sub-routes: dashboard/documents/bonds/reconciliation/exceptions/movements/schedule/journals/audit-schedule/commentary/review/settings/ai-assistant/audit-trail.
  - Verify each page loads (not blank; not default data fallback; spinner shows then content).
  - For copilot page specifically: send 3 queries, verify network calls.
  - Verify approve button for unprivileged user is either hidden or click returns 403 toast banner.
- **Acceptance Criteria Addressed**: AC-10, AC-11, partial AC-4/5 visible behavior
- **Test Requirements**:
  - `rule` TR-9.1: 14 routes render non-blank with no console errors except informational. Evidence: 14 screenshots or 14 snapshot refs.
  - `rule` TR-9.2: Approve endpoint 403 for user shows UI toast. Evidence: browser snapshot toast ref.

---

## Task 10: Final Cleanup & Regression Pass
- **Status**: `pending`
- **Priority**: low
- **Depends On**: All tasks 1-9
- **Description**:
  - Final verification pass re-running individual failing/flake tests.
  - Remove any dead commented-out code in finance_service.py / FinanceCopilotChat.svelte.
  - Final `grep -n SAMPLE_ backend/open_webui/services/finance_service.py` — zero lines of "return SAMPLE_".
  - Lint passes (ruff or flake or project standard).
  - Type check (pyright / mypy) if project standard.
- **Acceptance Criteria Addressed**: Cross-cutting clean code guarantee
- **Test Requirements**:
  - `rule` TR-10.1: Grep return SAMPLE_ zero lines. Evidence: shell output.
  - `rubric` TR-10.2: No lint/type errors on modified Python files. Scale 1-5, 1=many 3=warnings only 5=zero warnings zero errors. Threshold >= 3. Evidence: ruff/pyright output.
