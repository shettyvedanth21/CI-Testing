## Ops Memory Map

This file is a compact operational memory note for the active Shivex support cycle.
It exists to reduce drift between:

- local code
- manual production patches
- future image/package-based deploys

Use this together with `server-patch-checklist.md`.

### Maintenance rule

This file should be updated proactively after meaningful work, especially when:

- a production patch is applied
- a local fix materially changes behavior
- a new overwrite risk appears
- a new validation result changes operational confidence

Do not wait for a separate user reminder if the context has materially changed.

### Canonical project path

The active Shivex repo path is:

- `/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main`

All real code, git history, and tracked memory notes for this project should be
anchored to that repo path unless the user explicitly redirects work elsewhere.

### Current branch state

- local working branch: `dev-testing`
- recent local commits ahead of `origin/Dev-Testing`:
  - `cfc424b2` Fix historical loss parity for waste and reports
  - `4eb18bbd` Fix local-day boundaries for waste and reporting windows
  - `fddf051d` Show idle running in waste analysis details
  - `3db62195` Align copilot today metrics with live state
- latest remote-tracked earlier commit noted:
  - `be82f5b7` Harden date range limits and coarse counter loss accounting

### Core deployment truth

- Current production runtime was manually patched several times.
- That production runtime is safe **right now**.
- A future image-based deploy from older upstream code can overwrite those patches.
- Safe long-term path is:
  1. local fix
  2. local validation
  3. commit
  4. push
  5. merge to `main`
  6. build package/image from updated code
  7. deploy that image

### Major recent fix areas

#### 1. Copilot consistency

- Curated Copilot "today" questions were aligned to live-state truth.
- Removed inconsistent source-of-truth mixing for live today totals.
- Key commit:
  - `3db62195`

#### 2. Waste-analysis idle row UI

- Waste-analysis detail view was missing `Idle Running`.
- Backend already returned idle values; UI was omitting them.
- Key commit:
  - `fddf051d`

#### 3. Shared accounting / coarse counter hardening

- Shared logic was hardened so flat/coarse counters do not suppress real
  idle/off-hours loss when live telemetry still indicates consumption.
- Key commit:
  - `be82f5b7`

#### 4. Historical local-day timezone fix

- Waste-analysis and reporting now use the real local day window instead of a
  shifted UTC-style interpretation for same-day ranges.
- Key commit:
  - `4eb18bbd`

#### 5. Historical waste/report parity fix

- Historical loss replay was improved so accounting-sensitive paths use finer
  telemetry replay and do not collapse idle because of coarse replay behavior.
- Key commit:
  - `cfc424b2`

#### 6. Waste-analysis PDF availability state clarification

- Waste-analysis result/PDF states were clarified so users can distinguish:
  - result ready
  - stored PDF unavailable
  - fresh PDF still downloadable
- Key commit:
  - `d5ad1e37`

#### 7. Analytics history / IST timestamp behavior

- Analytics history selection and IST-facing timestamp behavior were corrected
  earlier in the branch history.
- Key commit:
  - `895a2e02`

#### 8. Runtime / deployment hardening in earlier branch history

- Redis/runtime hardening and monitoring support were added earlier.
- Server-build / deployment fallback support was also added earlier.
- These are not the main recent manual prod patch items, but they are relevant
  deployment background.
- Key commits:
  - `c443c545`
  - `a06f5251`

#### 9. Machine detail parameter configuration stale-refresh fix (local only so far)

- Editing an existing health parameter config could save successfully in the
  backend while the machine detail UI stayed stale until hard refresh.
- Root cause: post-save reconciliation only refreshed partial page state while
  the machine detail page renders from multiple overlapping data sources.
- Local fix now uses a stronger authoritative refresh path after create/update/
  delete of health configs:
  - `fetchData(false)`
  - `fetchHydration()`
  - `refreshShellSummary()`
  - `loadCurrentState()` when on parameters tab
  - `loadPerformanceTrends()` when trend section is primed
- Files changed locally:
  - `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
  - `ui-web/tests/e2e/dashboard-health-shift-calendar-depth.spec.js`
- Local validation completed:
  - `npm run typecheck`
  - `npm run test:unit` -> 273 passed
  - targeted Playwright regression for immediate post-save reconciliation -> passed
  - `npm run build` -> passed
- Production patch for this issue has **not** been applied yet.

#### 10. Machine detail parameter configuration save-state UX hardening (local only so far)

- After the stale-refresh fix, save could still feel silent for a few seconds
  while backend persistence + reconciliation completed.
- Local UX hardening now adds:
  - visible save progress copy
  - disabled duplicate actions while saving/deleting
  - save button text changes to `Saving...`
- Files changed locally:
  - `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
  - `ui-web/tests/unit/parameterConfigSaveUx.test.ts`
- Additional local validation completed:
  - `npm run typecheck`
  - `npm run test:unit` -> 275 passed
  - `npm run build` -> passed
- Production patch for this save-state UX improvement has **not** been applied yet.

#### 11. Machine detail parameter configuration save-path performance refinement (local only so far)

- Production testing showed the functional fix worked, but save latency was too
  high in production (`~30-45s`) because the modal was awaiting a very broad
  post-save reconciliation path.
- Root cause:
  - `reconcileAfterHealthConfigChange()` awaited:
    - `fetchData(false)`
    - `fetchHydration()`
    - `refreshShellSummary()`
    - `loadCurrentState()`
    - `loadPerformanceTrends()`
- Local refinement now keeps the correctness fix but narrows the awaited save
  path to only:
  - `fetchData(false)`
- The heavier refreshes now run in the background after the modal can close:
  - `fetchHydration()`
  - `refreshShellSummary()`
  - `loadCurrentState()`
  - `loadPerformanceTrends()`
- Files changed locally:
  - `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
  - `ui-web/tests/unit/parameterConfigSaveUx.test.ts`
- Additional local validation completed:
  - `npm run typecheck`
  - `npm run test:unit` -> 276 passed
  - `npm run build` -> passed
- This performance refinement has **not** yet been patched to production.

#### 12. Device-service API / scheduler separation for parameter-config save latency (local phase complete)

- Production diagnosis proved the remaining save delay was not mainly frontend:
  - controlled prod save on `VD00000001` took ~57s from click to backend
    `Health config updated` log
  - later failures showed `ui-web` proxy `ECONNRESET` / `socket hang up`
- Root cause hypothesis was confirmed enough to act on locally:
  - `device-service` served API traffic with `uvicorn --workers 1`
  - heavy background schedulers were running in the same runtime path
  - request latency and instability on health-config save were consistent with
    request-path contention
- Local permanent-fix implementation now separates:
  - API-serving `device-service`
  - scheduler-only `device-service-scheduler`
- Local files changed:
  - `services/device-service/app/config.py`
  - `services/device-service/app/__init__.py`
  - `services/device-service/app/scheduler_runner.py`
  - `services/device-service/start.sh`
  - `docker-compose.yml`
  - `docker-compose.local.yml`
  - `docker-compose.server-build.yml`
  - `services/device-service/tests/test_scheduler_runner.py`
- New runtime contract:
  - API runtime:
    - `DEVICE_SERVICE_RUNTIME=api`
    - `DEVICE_SERVICE_ENABLE_FLEET_STREAM=true`
    - `DEVICE_SERVICE_RUN_STARTUP_MAINTENANCE=false`
    - `DEVICE_SERVICE_RUN_EMBEDDED_SCHEDULERS=false`
  - Scheduler runtime:
    - `DEVICE_SERVICE_RUNTIME=scheduler`
    - `DEVICE_SERVICE_ENABLE_FLEET_STREAM=false`
    - `DEVICE_SERVICE_RUN_STARTUP_MAINTENANCE=true`
    - `DEVICE_SERVICE_RUN_EMBEDDED_SCHEDULERS=true`
- Local validation completed:
  - `python3 -m compileall services/device-service/app`
  - `docker compose ... config`
  - local compose rebuild/start of:
    - `device-service`
    - `device-service-scheduler`
  - verified runtime split in logs:
    - API container starts cleanly without scheduler cycles
    - scheduler container owns reconciliation / trends / snapshot / cleanup work
  - fixed scheduler healthcheck so it no longer inherits the image's HTTP
    `/health` probe incorrectly
  - focused backend suite passed:
    - `test_health_config_uniqueness.py`
    - `test_health_config_delete_idempotent.py`
    - `test_phase3_machine_api_validation.py`
    - `test_startup_reconcile.py`
    - `test_dashboard_bootstrap_summary.py`
    - `test_scheduler_runner.py`
    - total: `32 passed`
- Production rollout for this architecture change has **not** been applied yet.

### Production data changes already applied

Device names in production RDS were updated to:

- `AD00000001` -> `First Floor AC Chiller Dual Fan Unit`
- `AD00000003` -> `First Floor AC Chiller Single Fan`
- `AD00000004` -> `Second Floor AC Chiller Single Fan`
- `AD00000002` -> `Second Floor AC Chiller Dual Fan Unit`

### Historical waste-analysis status

After the local-day fix and parity fix:

- off-hours duration became aligned with expected shift remainder
- historical idle no longer collapsed to near-zero
- one or more devices can still show:
  - `LARGE_TIMESTAMP_GAP_SKIPPED`

### Meaning of LARGE_TIMESTAMP_GAP_SKIPPED

- The platform did not receive usable continuous telemetry for >15 minutes
  for that device during the selected range.
- That interval is skipped instead of guessed.
- This is conservative and truthful.
- It does **not** by itself prove MQTT was down.

Possible causes include:

- device stopped publishing
- network interruption
- MQTT path issue
- ingestion lag/failure
- timestamp irregularity
- controller restart

### Short-term operating mode before normal GitHub deploys resume

- local development
- local CI / targeted validation
- careful manual prod patch only when needed
- avoid stale upstream image deploys

### 2026-05-20 health-config save latency / HTTP 500 root cause

- Production symptom:
  - `VD00000001` health-config save/delete could wait ~30-60 seconds and then
    fail with HTTP 500 / proxy socket hang-up.
- Confirmed root cause:
  - health-config create/update/delete/bulk endpoints synchronously called
    `PerformanceTrendService.repair_recent_health_window(...)`.
  - That method walks recent trend buckets and fetches telemetry samples before
    the API response returns.
  - On production this caused long waits and gateway/proxy reset risk.
- Permanent direction:
  - user-facing health-config writes persist config and recompute live projection
    only.
  - historical/recent trend repair belongs to background scheduler/materializers,
    not the Save button request path.
- Production patch applied:
  - `services/device-service/app/api/v1/devices.py`
  - removed inline `repair_recent_health_window(...)` calls from health-config
    create/update/delete/bulk endpoints.
- Production backup:
  - `.codex-backups/health-config-fast-save-final-20260519-193617`

### Important reassurance

The wrong `FactoryOPS-Cittagent-Obeya-main` folder mistake affected only the
placement of memory notes. It did **not** change the real Shivex repo history,
and it did **not** alter production runtime patches.

### Purpose of this file

This is not a changelog.
It is a short operational memory map to preserve context and reduce mistakes.

### 2026-05-20 waste-analysis total-vs-loss accounting invariant

- Production symptom under investigation:
  - dashboard today-loss and waste-analysis job output could differ for the
    same day/device.
  - one waste job showed a device summary where `offhours_energy_kwh` was
    greater than `total_energy_kwh`, which is mathematically invalid.
- Confirmed local root cause:
  - `waste_engine.compute_device_waste(...)` computed device `total_energy_kwh`
    through the older direct interval total path.
  - idle/off-hours/overconsumption buckets came from
    `services.shared.energy_accounting.aggregate_window(...)`.
  - When those paths used different telemetry bases, bucket energy could exceed
    the reported total.
- Local permanent fix:
  - `services/waste-analysis-service/src/services/waste_engine.py` now uses
    the shared `aggregate_window(...)` total as the device total energy for the
    same result that produces idle/off-hours/overconsumption buckets.
  - The older `_calc_total_energy(...)` path remains only as a diagnostic
    method/quality probe.
  - Added regression coverage in
    `services/waste-analysis-service/tests/test_waste_engine_policy.py` to
    enforce `offhours_energy_kwh <= total_energy_kwh`.
- Local validation completed:
  - full waste-analysis tests: `79 passed, 1 skipped`
  - related device live/loss tests with local JWT secret: `43 passed`
  - compile check: `services/waste-analysis-service/src` and
    `services/shared` compiled successfully
- Production patch status:
  - applied on live server after approval.
  - patched only
    `services/waste-analysis-service/src/services/waste_engine.py`.
  - server backup:
    `.codex-backups/waste-accounting-invariant-20260519-204855/waste_engine.py`.
  - restarted only `waste-analysis-service` and `waste-analysis-worker`.
  - post-restart status: both containers healthy; startup logs clean.

### 2026-05-20 waste-analysis telemetry gap warning clarity

- User concern:
  - `LARGE_TIMESTAMP_GAP_SKIPPED` is technically correct but not explainable
    to clients.
  - Client-facing report should explain that the machine may have been on, but
    the platform did not receive continuous usable telemetry.
- Local permanent fix:
  - `services/waste-analysis-service/src/services/telemetry_normalizer.py`
    now records skipped large-gap metadata:
    - gap count
    - total excluded duration
    - largest gap duration
  - `services/waste-analysis-service/src/services/waste_engine.py` now emits
    a human-readable warning:
    - telemetry coverage gap detected
    - missing periods were excluded instead of estimated
    - includes count and excluded duration
- Validation:
  - focused warning/accounting tests: `16 passed`
  - full waste-analysis tests: `81 passed, 1 skipped`
  - compile check for waste-analysis source: passed
- Production status:
  - applied on live server after approval on 2026-05-20.
  - patched:
    - `services/waste-analysis-service/src/services/telemetry_normalizer.py`
    - `services/waste-analysis-service/src/services/waste_engine.py`
  - restart-only was not enough because production waste containers are
    image-based, not bind-mounted.
  - rebuilt only `waste-analysis-service` and `waste-analysis-worker` using
    `docker-compose.server-build.yml`; no GitHub Actions, no GHCR pull, no tag
    change, no full stack restart.
  - backup:
    `.codex-backups/waste-gap-warning-20260520-115203/`.
  - post-patch verification:
    - running production container contains the new gap warning code
    - `curl http://localhost:8087/health` returned `{"status":"healthy"}`
    - both waste containers healthy
    - fresh logs had no startup tracebacks/errors
    - in-container warning smoke produced the readable telemetry gap message

### 2026-05-20 local stack 500s after restart

- Symptom after local restart:
  - waste-analysis history, reports history/schedules/tariff, and copilot
    curated questions returned HTTP 500.
  - `reporting-service` and `waste-analysis-service` were restart-looping.
- Confirmed root causes:
  - Local Docker was started with plain `docker compose`, so Compose used
    `.env` production-style values instead of `.env.local`.
  - Containers were pointed at production RDS host instead of local MySQL.
  - A separate latent SQLAlchemy/aiomysql compatibility issue surfaced:
    `pool_pre_ping=True` called `AsyncAdapt_aiomysql_connection.ping()` without
    aiomysql's required `reconnect` argument.
- Local fix applied:
  - Added a narrow aiomysql pool pre-ping compatibility shim in:
    - `services/waste-analysis-service/src/database.py`
    - `services/reporting-service/src/database.py`
    - `services/copilot-service/src/database.py`
  - Restarted local app containers with:
    `docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml ...`
- Validation:
  - affected containers healthy locally.
  - runtime env inside affected containers shows local MySQL:
    `mysql+aiomysql://...@mysql:3306/ai_factoryops`.
  - unauthenticated proxy smoke returned `401 MISSING_TOKEN`, not `500`.
  - authenticated smoke returned `200` for report history/schedules and expected
    `403 FEATURE_DISABLED` for disabled local demo features, not `500`.
- Operational rule reinforced:
  - for local work, never use plain `docker compose up`; always include
    `--env-file .env.local -f docker-compose.yml -f docker-compose.local.yml`.

### 2026-05-20 production waste-analysis aiomysql compatibility recovery

- During the server-local waste image rebuild for the warning patch, pip
  resolved newer `aiomysql`/SQLAlchemy-compatible packages inside the rebuilt
  waste image.
- Production symptom after rebuild:
  - `waste-analysis-service` restarted repeatedly with:
    `AsyncAdapt_aiomysql_connection.ping() missing 1 required positional argument: 'reconnect'`
  - `waste-analysis-worker` heartbeat logged the same compatibility error.
- Recovery patch applied only to waste-analysis:
  - `services/waste-analysis-service/src/database.py`
  - This is the same narrow local compatibility shim, limited to the service
    that was rebuilt and affected.
- Not patched in production in this step:
  - `services/reporting-service/src/database.py`
  - `services/copilot-service/src/database.py`
- Verification:
  - compile check passed for waste database and warning files.
  - rebuilt only `waste-analysis-service` and `waste-analysis-worker`.
  - both containers healthy.
  - `/health` returned `{"status":"healthy"}`.
  - fresh logs showed no `ping()` tracebacks after recovery.

### 2026-05-20 local machine overview chart history ranges

- User issue:
  - machine dashboard overview charts only showed the recent live buffer.
  - after roughly an hour, older readings disappeared from the visible trend.
- Local-only fix:
  - kept the live WebSocket/recent buffer capped for safety.
  - added overview chart range controls: `Live`, `6h`, `24h`, `7d`.
  - non-live ranges fetch historical telemetry from the existing data-service
    telemetry history endpoint with safe aggregation windows.
  - no backend service files changed for this chart fix.
- Files changed locally:
  - `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
  - `ui-web/tests/unit/machineOverviewCharts.test.ts`
- Validation:
  - UI unit suite: `279 passed`
  - React hooks lint: passed
  - TypeScript typecheck: passed
  - `git diff --check`: passed
  - local page route smoke: `curl -I http://localhost:3000/machines/AD00000001`
    returned `HTTP/1.1 200 OK`
- Note:
  - full `npm --prefix ui-web run lint` still fails on unrelated pre-existing
    lint errors in other files; this chart patch did not introduce those.
  - local compose originally kept `ui-web` on the GHCR image, so `--build` did
    not rebuild local UI changes.
  - added a local-only `ui-web` build override in `docker-compose.local.yml`.
  - rebuilt only `ui-web` with `--no-deps`; page route smoke returned `200`.
- Production status:
  - applied on live server after approval on 2026-05-20.
  - backed up production page to:
    `.codex-backups/ui-overview-history-20260520-161834/page.tsx`
  - patched only:
    `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
  - rebuilt/recreated only `ui-web` with `docker-compose.server-build.yml`.
  - no backend services were restarted.
  - local and server machine page hashes matched after patch:
    `2345ab9a3a00f0b021ebcc115d310cbd198c6e783f3881fbbbb1d581f9d18af2`
  - post-patch smoke:
    `/machines/AD00000001`, `/reports`, `/waste-analysis`, and `/copilot`
    all returned HTTP 200.

### 2026-05-20 local canonical financial total consistency fix

- User issue:
  - Calendar/Home Dashboard, Energy Consumption Report, and Waste Analysis
    showed different `kWh` and cost for the same Obeya Smart Workspaces devices
    and date window.
- Read-only production diagnosis found:
  - Calendar/Home use energy-service canonical aggregate rows.
  - Energy Report fetched canonical rows successfully, but rejected them when
    quality/conflict heuristics were present and fell back to report-local
    telemetry math.
  - Waste Analysis also fetched canonical rows, but only applied them when
    loss-bucket/classification overlay checks passed.
- Local permanent contract now:
  - canonical energy-service totals are the financial source of truth when
    valid `totals.energy_kwh` exists.
  - quality flags remain diagnostics/warnings; they do not switch money totals
    to independent local math.
  - waste loss bucket/classification overlay can still be rejected separately,
    but total energy and total energy cost stay canonical.
- Files changed locally:
  - `services/reporting-service/src/tasks/report_task.py`
  - `services/reporting-service/tests/test_report_task_tariff_warning.py`
  - `services/waste-analysis-service/src/tasks/waste_task.py`
  - `services/waste-analysis-service/tests/test_waste_historical_loss_parity.py`
- Validation:
  - focused reporting financial tests: `14 passed`
  - focused waste financial/loss tests: `7 passed`
  - full waste-analysis tests: `82 passed, 1 skipped`
  - compile check passed for touched reporting/waste task modules.
  - full reporting test directory reached `119 passed`; remaining failures were
    local environment prerequisites unrelated to this patch:
    unresolved `redis:6379` for rate-limit/queue API tests and missing
    `ad00000001_apr20.csv` for two truth-proof CSV tests.
- Production status:
  - patched after explicit user approval on 2026-05-20.
  - patched runtime financial consistency files:
    - `services/reporting-service/src/tasks/report_task.py`
    - `services/waste-analysis-service/src/tasks/waste_task.py`
  - rebuilding reporting exposed the known aiomysql `pool_pre_ping`
    compatibility issue; applied the already-local reporting database shim to:
    - `services/reporting-service/src/database.py`
  - did not touch copilot database shim in production.
  - production backups:
    - `.codex-backups/canonical-financial-20260520-211743/`
    - `.codex-backups/reporting-aiomysql-20260520-212925/`
  - post-patch verification:
    - reporting/waste services and workers healthy.
    - `/reports` and `/waste-analysis` returned HTTP 200.
    - device-service, energy-service, copilot-service, and ui-web retained
      prior uptimes.

### 2026-05-20 local PF warning false-positive fix

- User issue:
  - Waste PDF/UI showed `Power factor estimated at 0.85` even when production
    telemetry rows had usable `power_factor` for the selected device/range.
- Root cause:
  - `services/shared/energy_accounting.py` used `IntervalSample.power_estimated`
    as the source for PF-assumption warnings.
  - During counter fallback, any active-power integration
    (`energy_delta_method == "power_integration"`) was being marked as
    `power_estimated=True`.
  - Active-power integration is estimated energy, but it does not mean PF was
    missing or that `0.85` was assumed.
- Local fix:
  - `power_estimated` is now set only when the interval energy method is
    `derived_vi_assumed_pf`.
  - This keeps PF warnings tied to the real condition: voltage/current-derived
    energy where PF was missing/invalid and default PF had to be used.
- Files changed locally:
  - `services/shared/energy_accounting.py`
  - `services/waste-analysis-service/tests/test_waste_engine_policy.py`
- Validation:
  - controlled reproduction with `power`, `current`, `voltage`, and
    `power_factor=0.92` now returns:
    `pf_estimated=False`, `offhours_pf_estimated=False`.
  - focused waste policy tests: `13 passed`
  - full waste-analysis tests: `83 passed, 1 skipped`
  - reporting overtime smoke with valid `power_factor` returned no PF warning.
  - compile checks passed for touched shared/reporting/waste modules.
  - `git diff --check`: passed.
- Production status:
  - patched after explicit user approval on 2026-05-21.
  - patched only:
    - `services/shared/energy_accounting.py`
  - production backup:
    - `.codex-backups/pf-warning-20260521-061743/energy_accounting.py`
  - local/server SHA-256 matched after copy:
    `5751f030ff151f9da8a81fff15f107c0806703af2373d42e22aaca31dbc476cf`
  - compile check passed on server.
  - restarted only:
    - `reporting-service`
    - `reporting-worker`
    - `waste-analysis-service`
    - `waste-analysis-worker`
  - post-patch verification:
    - all four targeted containers healthy.
    - `http://localhost:8085/health`: healthy.
    - `http://localhost:8087/health`: healthy.
    - `https://shivex.ai/reports`: HTTP 200.
    - `https://shivex.ai/waste-analysis`: HTTP 200.
    - device-service, energy-service, copilot-service, and ui-web retained
      prior uptimes.

### 2026-05-21 local Energy Report PDF layout cleanup

- User issue:
  - Energy Consumption Report PDF looked visually heavier and more prone to
    overlap than the cleaner Waste Analysis PDF.
- Local fix:
  - presentation-only changes in `services/reporting-service/src/pdf/builder.py`.
  - compacted Energy Report header to a waste-style title block with generated,
    period/scope, and tariff lines.
  - reduced oversized hero/KPI/card/table/chart spacing.
  - added safer wrapping for long values.
- Safety:
  - no calculation, tariff, telemetry, canonical total, database, or API logic
    changed.
- Validation:
  - compile check passed for reporting PDF builder.
  - rendered Jinja HTML smoke confirmed the compact header path is active.
  - focused PDF template tests: `10 passed`.
  - focused reporting task tests: `14 passed`.
- Production status:
  - not patched to production yet.

### 2026-05-21 local Energy Report PDF cost-column cleanup

- User request:
  - add `Cost` to the Energy Consumption Report PDF `Device Breakdown`.
  - remove `Method` from `Device Breakdown` to avoid user confusion.
  - add `Cost` to the `Daily Energy Breakdown`.
- Local fix:
  - `services/reporting-service/src/tasks/report_task.py`
    - computes per-device `total_cost` from validated per-day cost rows.
    - extends flattened `daily_series` with canonical day-level `cost`.
  - `services/reporting-service/src/pdf/builder.py`
    - replaces `Method` column with `Cost` in `Device Breakdown`.
    - adds `Cost` column to `Daily Energy Breakdown`.
    - updates section subtitle/intro copy to remove method wording.
- Safety:
  - reporting payload/template only.
  - no energy formulas, tariff source, canonical overlays, telemetry queries,
    DB schema, or waste-analysis logic changed.
- Validation:
  - compile checks passed for `report_task.py` and reporting PDF builder.
  - focused reporting task tests: `14 passed`.
  - focused reporting PDF template tests: `11 passed`.
  - `git diff --check` passed.
- Production status:
  - not patched to production yet.

### 2026-05-21 local Waste Report PDF simplification + table totals

- User request:
  - remove `Method` and `PF Estimated` columns from Waste Report PDF `Total Consumption by Device`.
  - add bottom totals to:
    - `Idle Running Analysis`
    - `Off-Hours Running Analysis`
    - `Overconsumption Analysis`
    - `Total Consumption by Device`
- Local fix:
  - `services/waste-analysis-service/src/pdf/builder.py`
    - removes the two confusing columns from the total-consumption table.
    - computes PDF footer totals from existing payload/device summary values.
    - adds `tfoot` total rows to the four waste PDF tables.
  - `services/waste-analysis-service/tests/test_pdf_presentation.py`
    - asserts removed columns stay hidden.
    - asserts footer totals render.
- Safety:
  - waste PDF presentation only.
  - no telemetry normalization, waste engine, tariff source, category formulas,
    canonical totals, DB schema, API behavior, or reporting-service logic changed.
- Validation:
  - compile checks passed.
  - waste PDF presentation tests: `7 passed`.
  - reporting task tests still passed: `14 passed`.
  - reporting PDF template tests still passed: `11 passed`.
  - `git diff --check` passed.
- Production status:
  - not patched to production yet.

### 2026-05-21 production report PDF runtime-build correction

- Issue observed:
  - host source files on production were patched, but freshly generated PDFs
    still used the old Energy/Waste PDF layout.
- Root cause:
  - production compose uses GHCR images without mounting the server source into
    `/app`.
  - plain `docker compose up -d --build ...` reused the image path, so the
    running containers still had old `/app/src/pdf/builder.py` code.
- Correct production path while GHCR/GitHub Actions are exhausted:
  - use `docker-compose.server-build.yml` with the base compose file:
    `docker compose -f docker-compose.yml -f docker-compose.server-build.yml up -d --build reporting-service reporting-worker waste-analysis-service waste-analysis-worker`
  - this builds the service images locally from the patched server source.
- Verification after correction:
  - inside `reporting-service`, Energy PDF template:
    - `Method present False`
    - `Daily cost present True`
    - `Device total cost present True`
  - inside `waste-analysis-service`, Waste PDF template:
    - `PF Estimated present False`
    - `calculation_method present False`
    - `tfoot present True`
  - services healthy:
    - `device-service`
    - `energy-service`
    - `reporting-service`
    - `reporting-worker`
    - `waste-analysis-service`
    - `waste-analysis-worker`
  - public pages returned HTTP 200:
    - `/reports`
    - `/waste-analysis`

### 2026-05-21 local Phase 1 complete: Machine Degradation Score foundation

- Scope completed:
  - backend-only Phase 1 for machine degradation scoring in `device-service`.
  - no analytics-service substitution yet.
  - no anomaly widget, rule-engine coupling, maintenance reset flow, or UI work yet.
- Files changed:
  - `services/device-service/alembic/versions/20260521_0001_machine_degradation_score.py`
  - `services/device-service/app/models/device.py`
  - `services/device-service/app/config.py`
  - `services/device-service/app/scheduler_runner.py`
  - `services/device-service/app/schemas/device.py`
  - `services/device-service/app/api/v1/devices.py`
  - `services/device-service/app/services/degradation/__init__.py`
  - `services/device-service/app/services/degradation/types.py`
  - `services/device-service/app/services/degradation/scorer.py`
  - `services/device-service/app/services/degradation/feature_aggregator.py`
  - `services/device-service/app/services/degradation/baseline_learner.py`
  - `services/device-service/app/services/degradation/service.py`
  - `services/device-service/tests/test_machine_degradation_migration.py`
  - `services/device-service/tests/test_degradation_scorer.py`
  - `services/device-service/tests/test_feature_window_aggregation.py`
  - `services/device-service/tests/test_baseline_learner.py`
  - `services/device-service/tests/test_degradation_score_api.py`
  - `services/device-service/tests/test_degradation_scheduler.py`
- Phase 1 deliverables now present:
  - additive DB migration for:
    - `machine_health_feature_windows`
    - `machine_health_baselines`
    - `machine_health_latest`
    - `machine_health_history`
  - SQLAlchemy models for the four tables.
  - pure scorer with five signals:
    - current variability drift
    - power factor drop
    - abnormal power draw
    - phase imbalance drift
    - trend worsening
  - pure feature-window aggregation helpers and running-state classifier.
  - pure baseline learner from steady-running windows.
  - ORM-ready service helpers for feature rows, baselines, latest snapshot, and history rows.
  - read-only API endpoint:
    - `GET /api/v1/devices/{device_id}/degradation-score`
  - scheduler/config wiring for feature aggregation, baseline learning, scoring, and cleanup.
- Important correctness notes:
  - `running_state` default fixed to `UNKNOWN` to match CHECK constraint.
  - baseline audit metadata now uses real `window_start` / `window_end`, not placeholder `now()`.
  - degradation API stale handling reads `settings.DEGRADATION_STALE_THRESHOLD_MINUTES`, not a hardcoded constant.
  - degradation API reads only from `MachineHealthLatest`; no scorer/raw telemetry/Influx calls on request path.
- Validation:
  - compile check passed for `services/device-service/app`.
  - focused Phase 1 suite passed:
    - migration tests
    - scorer tests
    - feature aggregation tests
    - baseline learner tests
    - API tests
    - scheduler tests
  - total: `109 passed`
  - `git diff --check` passed.
- Production status:
  - local only.
  - no production patch done for machine degradation score yet.

### 2026-05-21 Machine Health Intelligence Phase 2

- Scope completed:
  - anomaly detection with baseline learning
  - performance trend tracking with health-window aggregation
  - signal completeness and `insufficient_signals` first-class status
  - MHL/MHH status column widened to `String(24)`; `phase_status` removed from MHL
  - migrations 0001-0005 created, applied, upgrade->downgrade->upgrade verified on live MySQL
  - read-only API endpoints for anomaly scores, performance trends, degradation history
  - scheduler wiring for anomaly detection, baseline learning, trend tracking, cleanup
- Key design decisions:
  - `insufficient_signals` is a first-class DB status, not mapped to `learning` at persist time
  - `signal_completeness` persisted as Float on MHL, computed from contributions at scoring time
  - Dashboard reads precomputed snapshots only, never calculates live from raw telemetry
  - History endpoint is on-demand only; trend contributions opt-in
- Files changed:
  - migrations 0001-0005 under `services/device-service/alembic/versions/`
  - `services/device-service/app/models/device.py`
  - `services/device-service/app/services/degradation/` (scorer, feature_aggregator, baseline_learner, service, types)
  - `services/device-service/app/services/anomaly/`
  - `services/device-service/app/services/performance_trends.py`
  - `services/device-service/app/scheduler_runner.py`
  - `services/device-service/app/schemas/device.py`
  - `services/device-service/app/api/v1/devices.py`
  - `services/device-service/app/config.py`
  - `services/device-service/tests/` (multiple new test files)
- Production status:
  - local only.
  - no production patch done for Phase 2 yet.

### 2026-05-22 Runtime hardening batch (8 structured commits)

- 8 commits on `dev-testing`:
  - `14eb4889` -> `8aad99be` -> `29b566b3` -> `fd6e22eb` -> `c6f8c378` -> `4dbd2c76` -> `03f7fff5` -> `d0e5a7d3`
- Changes:
  - shared HTTP pool (`shared_http.py`) for device-service
  - scheduler crash-cascade prevention
  - restart policies, health checks
  - INTERNAL_HEADERS fix
  - Redis depends_on, expose vs ports
  - FRONTEND_BASE_URL hardening
  - circuit breaker removal (deferred for holistic work)
  - dead import cleanup
- Local stack: 25 containers, 24/24 healthchecked healthy, all E2E flows pass
- Production status:
  - local only.

### 2026-05-22 Full-platform E2E validation

- Compose regression found and fixed during validation
- Full-platform E2E local validation complete
- Deep scale analysis complete across all services

### 2026-05-22 Batch 1a (correctness + infra safety)

- Data-service:
  - pool sizing configurable via env vars (`db_pool_size`, `db_max_overflow`, `db_pool_recycle`, `db_pool_timeout`)
  - DLQ repository: pool_timeout on insert
  - outbox repository: retry-count increment uses atomic SQL
  - enrichment service: defensive fallback for malformed MQTT status field
- Docker compose:
  - Redis auth: `REDIS_URL` uses `redis://:${REDIS_PASSWORD:-}@redis:6379/0` pattern
  - log rotation on all 30 services
  - memory limits on 23 services
  - only ui-web:3000 and EMQX have `ports:`

### 2026-05-22 Energy-service gap-closure fixes

- Gap 1: Lock-exhaustion surfaced as HTTP 503
  - `routes.py` detects `idempotent_drop` -> returns `JSONResponse(status_code=503, content={"success": False, "error": "optimistic_lock_contention", "retryable": True, "data": result})`
  - broadcast skipped for dropped results
- Gap 2: Shared HTTP client shutdown
  - `main.py` adds `_close_shared_http_clients()` calling `aclose()` on `meta_cache._client` and `tariff_cache._client` in lifespan shutdown
- Caller contract verified: single `/live-update` endpoint is dead code path in outbox relay (energy goes through `/live-update/batch`); batch path uses `persistence_mode="locked"` (SELECT FOR UPDATE), never hits optimistic lock
- Tests: `test_live_update_returns_503_on_optimistic_lock_exhaustion`, `test_live_update_returns_200_on_success` -- 33 energy-service tests pass
- Key decisions:
  - 503 for lock exhaustion is backward-compatible because no internal caller reaches single `/live-update`
  - 503 triggers outbox retry semantics (`status_code >= 500` check)
- Files changed:
  - `services/energy-service/app/services/energy_engine.py`
  - `services/energy-service/app/services/device_meta.py`
  - `services/energy-service/app/services/tariff_cache.py`
  - `services/energy-service/app/api/routes.py`
  - `services/energy-service/app/main.py`
- Production status:
  - local only.

### 2026-05-22 Device-service scale fixes (4 issues)

- Issue 1 (Scheduler session churn - Critical):
  - All scheduler functions changed from per-device `AsyncSessionLocal()` to per-tenant `SchedulerSessionLocal()` with `begin_nested()` savepoints for per-device isolation; `commit()` after each device savepoint
  - Session count per cycle drops from ~1,100 to ~101 for 1,000 devices across 100 tenants
  - Uses `SchedulerSessionLocal` (separate pool) so scheduler connections don't compete with API pool
- Issue 2 (Dashboard N+1 fanout - Critical):
  - `materialize_energy_and_loss_snapshots` now fetches telemetry once for month window and derives both today and month from cached data (N HTTP calls instead of 2N)
  - No downstream service changes needed; same `aggregate_window` formula; same output shape
- Issue 3 (Blocking MinIO delete - High):
  - `_run_dashboard_snapshot_retention_cycle` uses `asyncio.to_thread()` with `_delete_expired_snapshots_from_storage()` batch method
  - Event loop never blocks on synchronous `remove_object` calls
  - Safe for both local MinIO and production S3-compatible storage
- Issue 4 (DB pool sizing - High):
  - `database.py` adds `scheduler_engine` and `SchedulerSessionLocal` (separate pool)
  - `config.py` adds `SCHEDULER_DATABASE_POOL_SIZE=15` and `SCHEDULER_DATABASE_MAX_OVERFLOW=25` (env-configurable)
  - API pool stays at current defaults (10+20=30 max)
  - Scheduler pool (15+25=40 max) accommodates up to 15 concurrent scheduler tasks
  - `scheduler_runner.py` disposes `scheduler_engine` not `engine` on shutdown
- Files changed:
  - `services/device-service/app/scheduler_runner.py`
  - `services/device-service/app/services/dashboard.py`
  - `services/device-service/app/database.py`
  - `services/device-service/app/config.py`
  - `services/device-service/app/__init__.py`
  - `services/device-service/tests/test_degradation_scheduler.py`
- Validation:
  - compile check: clean
  - dashboard/bootstrap/tariff/loss/projection tests: 52 passed
  - scorer/feature-window/baseline/anomaly tests: 162 passed
  - pre-existing scheduler test failure (SQLAlchemy Base mock incompatibility) confirmed not caused by these changes
- Production status:
  - local only.
