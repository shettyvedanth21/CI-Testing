## Server Patch Checklist

This checklist is for the first fully upstream image/package-based deploy after
the manual production patch cycle.

The goal is to avoid losing manual server fixes when GitHub Actions, package
builds, and image deploys resume.

### Maintenance rule

This file should be updated after every meaningful manual production patch so the
next post-patch verification and the first post-June-1 image-based deploy stay
safe and traceable.

### Ownership rule for future packaged deploy

When GitHub Actions/package-based deploys resume after June 1:

1. verify what manual prod patches exist
2. verify the same fixes exist in local source
3. verify the same fixes exist in merged upstream source
4. verify the built image/tag contains those fixes
5. only then allow overwrite of the current server runtime

The server patch checklist is the first reference point for that verification.

### Canonical project path

The active Shivex repo path is:

- `/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main`

Do not maintain this checklist in lookalike folders or renamed side folders.

### Golden rule

Before a future deploy overwrites production with a package/image, verify that
the same fixes are already present in local source, in the merged branch, and in
the built image.

---

## Production patch areas that must not regress

### 1. Copilot consistency

Expected behavior:

- curated "today" questions stay aligned with live-state truth
- no regression to mixed live-state vs stale log-source behavior

Local commit reference:
- `3db62195`

Checks after deploy:
- "What is today's total idle loss?"
- "Summarize today's factory performance"
- "Which machine caused the highest loss today?"

---

### 2. Waste-analysis idle row UI

Expected behavior:

- waste-analysis details show:
  - `Idle Running`
  - `Off-Hours Running`
  - `Overconsumption`

Local commit reference:
- `fddf051d`

Checks after deploy:
- open waste-analysis details UI and confirm all 3 rows appear

---

### 3. Shared accounting / coarse counter hardening

Expected behavior:

- live idle/off-hours accounting does not regress to undercounting when counters
  are flat/coarse but telemetry still indicates consumption

Local commit reference:
- `be82f5b7`

Checks after deploy:
- verify live loss figures remain materially believable on affected devices

---

### 4. Historical local-day timezone fix

Expected behavior:

- same-day historical ranges use the correct local day boundary

Local commit reference:
- `4eb18bbd`

Checks after deploy:
- verify same-day custom range behaves correctly for local time

---

### 5. Historical waste/report parity fix

Expected behavior:

- historical waste-analysis does not collapse idle
- off-hours duration stays aligned with shift remainder

Local commit reference:
- `cfc424b2`

Checks after deploy:
- same-day waste analysis remains believable
- historical report totals do not regress to the old broken values

---

### 6. Waste-analysis PDF availability state clarity

Expected behavior:

- waste-analysis status should not regress to confusing PDF/result state wording
- users should still be able to distinguish:
  - result ready
  - stored PDF unavailable
  - fresh PDF fallback available

Local/branch commit reference:
- `d5ad1e37`

Checks after deploy:
- review a waste-analysis job card/result state and confirm the wording still
  makes sense

---

### 7. Analytics history / IST timestamp behavior

Expected behavior:

- analytics history selection should not regress
- IST-facing timestamps should remain sensible for users

Local/branch commit reference:
- `895a2e02`

Checks after deploy:
- analytics history selection still behaves correctly
- timestamps still look correct in local/IST context

---

### 8. Machine detail parameter configuration immediate refresh

Expected behavior:

- after create/update/delete of a parameter health config, the machine detail UI
  reflects the new values immediately
- no manual browser refresh should be required
- repeated edits to the same config should still reflect immediately

Local validation reference:
- local frontend change in `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
- targeted Playwright regression added in:
  - `ui-web/tests/e2e/dashboard-health-shift-calendar-depth.spec.js`

Checks after deploy:
- update an existing parameter config and confirm new values render immediately
- edit the same config again and confirm no hard refresh is needed
- delete a config and confirm the page updates immediately

### 9. Machine detail parameter configuration save-state UX

Expected behavior:

- when user clicks Save, the modal should show visible progress immediately
- duplicate clicks should be blocked while save is in flight
- close/cancel/delete controls should not allow conflicting actions mid-save
- save button should reflect in-flight state with `Saving...`

Local validation reference:
- local frontend change in `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
- unit UX contract in:
  - `ui-web/tests/unit/parameterConfigSaveUx.test.ts`

Checks after deploy:
- click Save on an edited parameter config and confirm the button changes to `Saving...`
- confirm a progress message is visible while the request is in flight
- confirm repeated clicks are blocked

### 10. Device-service API / scheduler runtime split

Expected behavior:

- `device-service` API container should serve requests without also owning the
  embedded scheduler loops
- `device-service-scheduler` should own:
  - performance trends / idle aggregation
  - dashboard snapshot materialization
  - live projection reconciliation
  - retention / cleanup jobs
- health-config save path should no longer contend with those background loops

Local validation reference:
- `services/device-service/app/config.py`
- `services/device-service/app/__init__.py`
- `services/device-service/app/scheduler_runner.py`
- `services/device-service/start.sh`
- `docker-compose.yml`
- `docker-compose.server-build.yml`
- `services/device-service/tests/test_scheduler_runner.py`

Checks after deploy:
- API container logs should not show scheduler startup/cycle messages
- scheduler container logs should show reconciliation / trends / snapshot cycles
- both containers should become healthy
- health-config save path should be re-measured in prod after rollout
- dashboard / live telemetry / snapshot flows should still behave normally

---

## Production data changes to verify

These are DB metadata changes and should still appear after deploy:

- `AD00000001` -> `First Floor AC Chiller Dual Fan Unit`
- `AD00000003` -> `First Floor AC Chiller Single Fan`
- `AD00000004` -> `Second Floor AC Chiller Single Fan`
- `AD00000002` -> `Second Floor AC Chiller Dual Fan Unit`

Checks after deploy:
- Machines page
- Machine detail pages

---

## Before first post-June-1 deploy

### Source checks

- [ ] local branch contains all recent fixes
- [ ] branch pushed upstream
- [ ] PR merged to `main`
- [ ] `main` includes:
  - [ ] copilot consistency fix
  - [ ] waste idle-row UI fix
  - [ ] shared accounting/coarse-counter hardening
  - [ ] historical local-day fix
  - [ ] historical parity fix
  - [ ] waste PDF availability state clarity
  - [ ] analytics history / IST behavior fix
  - [ ] device-service API / scheduler separation

### Build checks

- [ ] package/image built from updated `main`
- [ ] no stale image tag accidentally reused
- [ ] built image corresponds to the merged code

### Server deploy checks

- [ ] deploy the new package/image
- [ ] restart only required services
- [ ] verify health
- [ ] verify runtime behavior, not just source presence

---

## Post-deploy smoke checks

### Copilot

- [ ] today's idle loss
- [ ] factory summary
- [ ] highest loss machine today

### Waste analysis

- [ ] idle row still visible
- [ ] same-day historical output remains believable
- [ ] off-hours duration still aligns with shift
- [ ] idle does not collapse again
- [ ] per-device loss buckets never exceed that device's total energy
- [ ] total waste cost is derived from the same shared accounting basis as
  idle/off-hours/overconsumption buckets

### Reporting

- [ ] same-day energy/report range aligns to local day

### Devices

- [ ] renamed device names still appear correctly

### Machine detail parameter configuration UX

- [ ] save existing parameter configuration closes normally
- [ ] editing the same parameter again reflects immediately without hard refresh
- [ ] delete configuration completes normally
- [ ] duplicate clicks are still blocked during save/delete
- [ ] save latency is acceptable and does not linger on `Saving...` for tens of seconds

### Health-config API fast-save contract

- [x] `device-service` API container is rebuilt after removing blocking trend
  repair from health-config writes
- [x] running production container no longer calls
  `repair_recent_health_window(...)` from:
  - create health-config
  - update health-config
  - delete health-config
  - bulk create health-config
- [x] `PerformanceTrendService` remains available for the read-only
  `/performance-trends` endpoint
- [ ] after user/browser test, confirm save/delete completes in a few seconds
  and no `/health-config/...` HTTP 500 appears

---

## Warning interpretation reminder

If a report still shows:

- `LARGE_TIMESTAMP_GAP_SKIPPED`

that does **not** automatically mean the patch failed.
It means telemetry continuity was broken for >15 minutes for that device and the
system chose to exclude that missing interval instead of guessing.

---

## Pending production patch: waste-analysis accounting invariant

Status: local fix complete and production hot-patched on 2026-05-20 IST.

Files to patch when approved:
- `services/waste-analysis-service/src/services/waste_engine.py`

Validation already completed locally:
- [x] `services/waste-analysis-service/tests`: `79 passed, 1 skipped`
- [x] related device live/loss tests:
  `services/device-service/tests/test_live_projection_service.py`
  and `services/device-service/tests/test_device_loss_stats.py`: `43 passed`
- [x] compile check for `services/waste-analysis-service/src` and
  `services/shared`

Production rollout plan when approved:
- [x] backup current server file under `.codex-backups/`
  - backup: `.codex-backups/waste-accounting-invariant-20260519-204855/waste_engine.py`
- [x] patch only `services/waste-analysis-service/src/services/waste_engine.py`
- [x] restart only waste-analysis API/worker containers if required by current
  compose layout
- [x] verify service health
- [ ] run a fresh today waste-analysis job for the OVA devices
- [ ] confirm per-device invariant:
  `idle + off-hours + overconsumption <= total_energy`
- [ ] compare dashboard today-loss against a newly generated waste job taken at
  roughly the same time, allowing only small timing/rounding drift

---

## Pending production patch: waste-analysis telemetry gap warning clarity

Status: production patched on 2026-05-20 after approval.

Files patched:
- `services/waste-analysis-service/src/services/telemetry_normalizer.py`
- `services/waste-analysis-service/src/services/waste_engine.py`

Local behavior after patch:
- Large telemetry gaps are still excluded from calculations.
- Warning text becomes client-readable and explains:
  - machine may have been on
  - platform did not receive continuous usable telemetry
  - report counts only measured intervals for accuracy
  - missing periods were excluded instead of estimated
  - number of gaps detected
  - total excluded duration
  - largest gap duration

Validation already completed locally:
- [x] focused warning/accounting tests: `16 passed`
- [x] full waste-analysis tests: `81 passed, 1 skipped`
- [x] compile check for `services/waste-analysis-service/src`

Production rollout completed:
- [x] backup both server files under `.codex-backups/`
  - backup: `.codex-backups/waste-gap-warning-20260520-115203/`
- [x] patch only the two waste-analysis warning files listed above
- [x] compile check passed on server
- [x] discovered restart-only does not load patched source because production
  waste containers are image-based
- [x] rebuilt only `waste-analysis-service` and `waste-analysis-worker` using
  `docker-compose.server-build.yml`
- [x] no GitHub Actions, no GHCR pull, no tag change, no full stack restart
- [x] verified running container includes the new warning code
- [x] verified `/health` returned `{"status":"healthy"}`
- [x] verified both waste containers healthy
- [x] verified fresh logs had no startup tracebacks/errors
- [x] verified in-container warning smoke includes gap count and excluded
  duration

Production note:
- The server-local rebuild resolved newer Python dependencies and exposed the
  known aiomysql `pool_pre_ping` compatibility issue in waste-analysis.
- To recover production, patched only:
  - `services/waste-analysis-service/src/database.py`
- Did not patch reporting/copilot database files in production during this
  warning rollout.

---

## Pending production patch: SQLAlchemy / aiomysql pool pre-ping compatibility

Status: partially applied to production only for waste-analysis on 2026-05-20.

Why this exists:
- Local services returned HTTP 500 / restart-looped after stale DB pool checks.
- Root error:
  `AsyncAdapt_aiomysql_connection.ping() missing 1 required positional argument: 'reconnect'`.
- The fix preserves `pool_pre_ping=True`; it only adds the missing default
  `reconnect=False` wrapper for aiomysql's adapter method.

Files to patch when approved:
- `services/reporting-service/src/database.py`
- `services/copilot-service/src/database.py`

Already patched in production due waste-analysis rebuild recovery:
- `services/waste-analysis-service/src/database.py`

Local validation already completed:
- [x] compile check for all three patched database modules
- [x] affected local containers healthy
- [x] affected local containers verified against `.env.local` / local MySQL
- [x] proxy smoke checks return `401`/`403`/`200`, not `500`
- [x] no new `ping()`/Traceback errors in affected service logs after restart

Production rollout plan when approved:
- [x] backup and patch waste-analysis database only as part of the 2026-05-20
  waste warning production recovery
- [ ] separately decide whether reporting/copilot should receive the same shim
  before any future server-local rebuild of those images
- [ ] if approved later, backup only reporting/copilot database files
- [ ] patch only reporting/copilot database files
- [ ] restart only affected containers:
  `reporting-service`, `copilot-service`
- [ ] verify report history and copilot curated questions do not return HTTP 500

---

## Production patch completed: machine overview chart historical ranges

Status: completed on production on 2026-05-20.

Purpose:
- Machine dashboard overview charts were recent-buffer-only.
- Users could not review previous time windows after the live buffer rolled over.

Local files changed:
- `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
- `ui-web/tests/unit/machineOverviewCharts.test.ts`
- `docker-compose.local.yml` local-only build override for `ui-web`

Behavior:
- `Live` keeps using the capped live telemetry buffer.
- `6h`, `24h`, and `7d` fetch historical telemetry from the existing
  data-service telemetry history API.
- Historical ranges use aggregation instead of increasing WebSocket memory:
  - `6h`: `1m` mean
  - `24h`: `5m` mean
  - `7d`: `15m` mean

Local validation:
- [x] UI unit suite: `279 passed`
- [x] React hooks lint passed
- [x] TypeScript typecheck passed
- [x] `git diff --check` passed
- [x] local route smoke returned `HTTP/1.1 200 OK`
- [x] local `ui-web` image rebuilt from source with `--no-deps`

Production rollout plan when approved:
- [x] backup the production UI file
  - `.codex-backups/ui-overview-history-20260520-161834/page.tsx`
- [x] patch only `ui-web/app/(protected)/machines/[deviceId]/page.tsx`
- [ ] if production needs tests committed alongside source, add
  `ui-web/tests/unit/machineOverviewCharts.test.ts`; otherwise source-only patch
  is enough for runtime
- [x] rebuild/restart only the UI container/service
- [x] verify machine page loads
- [x] verify running container contains `Telemetry Trends`
- [x] verify reports, waste analysis, and copilot pages still load
- [x] verify no backend services were restarted

Post-patch verification:
- `ui-web` recreated only.
- `device-service`, `waste-analysis-service`, `reporting-service`, and
  `copilot-service` retained prior uptimes.
- Smoke routes returned HTTP 200:
  - `/machines/AD00000001`
  - `/reports`
  - `/waste-analysis`
  - `/copilot`
- Local/server machine page SHA-256 matched:
  `2345ab9a3a00f0b021ebcc115d310cbd198c6e783f3881fbbbb1d581f9d18af2`

---

## Production patch completed: canonical financial total consistency

Status: completed on production on 2026-05-20.

Purpose:
- Make Calendar/Home Dashboard, Energy Consumption Report, and Waste Analysis
  use the same canonical financial totals for `kWh` and energy cost.
- Prevent reporting/waste modules from silently falling back to separate local
  telemetry math when canonical totals are available but quality flags exist.

Root cause confirmed by read-only production diagnosis:
- Calendar/Home Dashboard use energy-service canonical aggregate rows.
- Energy Report fetched canonical range data successfully, then rejected it via
  defensive quality/conflict gates and used `normalized_telemetry`.
- Waste Analysis fetched canonical range data successfully, then tied total
  energy/cost replacement to loss-bucket overlay acceptance.

Local files changed:
- `services/reporting-service/src/tasks/report_task.py`
- `services/reporting-service/tests/test_report_task_tariff_warning.py`
- `services/waste-analysis-service/src/tasks/waste_task.py`
- `services/waste-analysis-service/tests/test_waste_historical_loss_parity.py`

Behavior after local fix:
- Reporting financial totals use canonical `totals.energy_kwh` when present.
- Reporting keeps placeholder-zero protection so a bogus zero canonical total
  does not wipe a positive local result.
- Waste Analysis always applies canonical total energy/cost when valid
  canonical financial totals exist.
- Waste Analysis can still reject canonical idle/off-hours/overconsumption
  bucket overlays when classification conflicts, without changing the financial
  source of truth.

Local validation:
- [x] focused reporting tests: `14 passed`
- [x] focused waste tests: `7 passed`
- [x] full waste-analysis tests: `82 passed, 1 skipped`
- [x] compile check passed for touched task modules
- [x] full reporting directory had `119 passed`; remaining failures were local
  prerequisites unrelated to this change:
  - `redis:6379` unavailable for queue/rate-limit tests
  - missing `ad00000001_apr20.csv` for two truth-proof CSV tests

Production rollout plan when approved:
- [x] backup the two production task files:
  - `services/reporting-service/src/tasks/report_task.py`
  - `services/waste-analysis-service/src/tasks/waste_task.py`
- [x] patch only those two runtime files.
- [x] compile check only those two files on the server.
- [x] rebuild/restart only affected services:
  - `reporting-service`
  - `reporting-worker`
  - `waste-analysis-service`
  - `waste-analysis-worker`
- [x] verify `/reports` and `/waste-analysis` pages return HTTP 200.
- [ ] generate/inspect one short-window report and waste analysis for the same
  known devices/date window and confirm total `kWh`/energy cost align with the
  energy-service canonical total.
- [x] no UI, auth, device, calendar, copilot, or data-service patch required.

Production notes:
- Runtime backups:
  - `.codex-backups/canonical-financial-20260520-211743/report_task.py`
  - `.codex-backups/canonical-financial-20260520-211743/waste_task.py`
- Local/server SHA-256 matched after copy:
  - reporting task: `0575524a297935ace14a50bfdd20bae2edaea565867ccf739fda23b9085bd586`
  - waste task: `b9d139ab7d896f7ed8824e009308ed903cf02f2646266cb520510ff76f0d7a87`
- Rebuilding reporting exposed the known aiomysql `pool_pre_ping` compatibility
  issue that was previously documented as pending.
- Recovery applied only to reporting database compatibility shim:
  - backup: `.codex-backups/reporting-aiomysql-20260520-212925/database.py`
  - patched: `services/reporting-service/src/database.py`
  - copilot was not touched.
- Post-patch verification:
  - `reporting-service`: healthy
  - `reporting-worker`: healthy
  - `waste-analysis-service`: healthy
  - `waste-analysis-worker`: healthy
  - `curl http://localhost:8085/health`: `{"status":"healthy"}`
  - `curl http://localhost:8087/health`: `{"status":"healthy"}`
  - `https://shivex.ai/reports`: HTTP 200
  - `https://shivex.ai/waste-analysis`: HTTP 200
- Unrelated services were not restarted:
  - `device-service`, `energy-service`, `copilot-service`, and `ui-web`
    retained prior uptimes.

---

## Production patch completed: PF warning false-positive fix

Status: completed on production on 2026-05-21.

Purpose:
- Stop showing `Power factor estimated at 0.85` when usable `power_factor`
  exists in the telemetry rows used by waste/report category calculations.
- Keep the warning only for real PF fallback cases where energy is derived from
  voltage/current and PF is missing/invalid.

Root cause:
- `services/shared/energy_accounting.py` marked every non-counter energy delta
  as `power_estimated=True`.
- That included active-power integration (`power_integration`), which does not
  assume PF.
- Waste/report warning paths interpreted that flag as “PF was assumed”.

Local files changed:
- `services/shared/energy_accounting.py`
- `services/waste-analysis-service/tests/test_waste_engine_policy.py`

Local validation:
- [x] controlled reproduction with valid `power_factor=0.92` no longer emits
  PF-estimated flags/warnings.
- [x] focused waste policy tests: `13 passed`
- [x] full waste-analysis tests: `83 passed, 1 skipped`
- [x] reporting overtime smoke with valid `power_factor` produced no PF warning.
- [x] compile checks passed for touched shared/reporting/waste modules.
- [x] `git diff --check`: passed.

Production rollout:
- [x] backup `services/shared/energy_accounting.py` on server.
- [x] patch only `services/shared/energy_accounting.py`.
- [x] compile-check the patched file on server.
- [x] rebuild/restart only services that import the shared module for these
  calculations:
  - `reporting-service`
  - `reporting-worker`
  - `waste-analysis-service`
  - `waste-analysis-worker`
- [x] health-check reporting and waste services.
- [x] smoke-check `/reports` and `/waste-analysis`.
- [ ] generate or inspect one short known waste/report result with valid
  `power_factor` and confirm no false PF-estimated warning.

Production notes:
- Backup:
  - `.codex-backups/pf-warning-20260521-061743/energy_accounting.py`
- Local/server SHA-256 matched after copy:
  - `5751f030ff151f9da8a81fff15f107c0806703af2373d42e22aaca31dbc476cf`
- Server compile check:
  - `python3 -m py_compile services/shared/energy_accounting.py`
- Post-patch verification:
  - `reporting-service`: healthy
  - `reporting-worker`: healthy
  - `waste-analysis-service`: healthy
  - `waste-analysis-worker`: healthy
  - `curl http://localhost:8085/health`: `{"status":"healthy"}`
  - `curl http://localhost:8087/health`: `{"status":"healthy"}`
  - `https://shivex.ai/reports`: HTTP 200
  - `https://shivex.ai/waste-analysis`: HTTP 200
- Unrelated services were not restarted:
  - `device-service`, `energy-service`, `copilot-service`, and `ui-web`
    retained prior uptimes.

---

## Pending production patch: Energy Report PDF layout cleanup

Status: production patched and runtime-corrected on 2026-05-21.

Purpose:
- Make Energy Consumption Report PDF visually cleaner and closer to the Waste
  Analysis PDF layout.
- Reduce header height, KPI/card padding, chart height, and table spacing so
  long values/timestamps are less likely to overlap.

Local files changed:
- `services/reporting-service/src/pdf/builder.py`

Safety:
- Presentation-only PDF template/CSS change.
- No energy calculation, tariff, canonical totals, telemetry query, DB schema,
  API, UI route, or waste analysis logic changed.

Local validation:
- [x] compile check passed for reporting PDF builder.
- [x] Jinja HTML render smoke confirmed compact header is active.
- [x] focused PDF template tests: `10 passed`
- [x] focused reporting task tests: `14 passed`

Production rollout plan when approved:
- [x] backup `services/reporting-service/src/pdf/builder.py`.
- [x] patch only `services/reporting-service/src/pdf/builder.py`.
- [x] compile-check patched file on server.
- [x] rebuild/restart runtime using server-build override:
  - `reporting-service`
  - `reporting-worker`
- [x] health-check reporting service/worker.
- [x] smoke-check `/reports`.
- [x] inside-container template verification confirmed patched reporting PDF
  template is active.
- [ ] generate one Energy Consumption Report PDF and visually verify header,
  KPI cards, charts, and tables do not overlap.

---

## Pending production patch: Energy Report PDF cost columns

Status: production patched and runtime-corrected on 2026-05-21.

Purpose:
- Add `Cost` to Energy Consumption Report PDF `Device Breakdown`.
- Remove `Method` from that table because it confuses end users.
- Add `Cost` to `Daily Energy Breakdown`.

Local files changed:
- `services/reporting-service/src/tasks/report_task.py`
- `services/reporting-service/src/pdf/builder.py`

Safety:
- Reporting payload + PDF template only.
- No energy formula, tariff source, canonical overlay policy, telemetry query,
  DB schema, dashboard, or waste-analysis behavior changed.

Local validation:
- [x] compile check passed for `report_task.py`.
- [x] compile check passed for reporting PDF builder.
- [x] focused reporting task tests: `14 passed`
- [x] focused PDF template tests: `11 passed`
- [x] `git diff --check` passed

Production rollout plan when approved:
- [x] backup:
  - `services/reporting-service/src/tasks/report_task.py`
  - `services/reporting-service/src/pdf/builder.py`
- [x] patch only those two files.
- [x] compile-check patched files on server.
- [x] rebuild/restart runtime using server-build override:
  - `reporting-service`
  - `reporting-worker`
- [x] health-check reporting service/worker.
- [x] smoke-check `/reports`.
- [x] inside-container template verification:
  - `Device Breakdown` shows `Cost`
  - `Method` is removed
  - `Daily Energy Breakdown` shows `Cost`

---

## Pending production patch: Waste Report PDF simplification + table totals

Status: production patched and runtime-corrected on 2026-05-21.

Purpose:
- Remove `Method` and `PF Estimated` from Waste Report PDF `Total Consumption by Device`.
- Add bottom totals for:
  - `Idle Running Analysis`
  - `Off-Hours Running Analysis`
  - `Overconsumption Analysis`
  - `Total Consumption by Device`

Local files changed:
- `services/waste-analysis-service/src/pdf/builder.py`
- `services/waste-analysis-service/tests/test_pdf_presentation.py`

Safety:
- Waste PDF template/presentation only.
- No waste engine formulas, telemetry handling, tariff source, canonical totals,
  DB schema, dashboard logic, or reporting-service behavior changed.

Local validation:
- [x] compile checks passed
- [x] waste PDF presentation tests: `7 passed`
- [x] reporting task tests still passed: `14 passed`
- [x] reporting PDF template tests still passed: `11 passed`
- [x] `git diff --check` passed

Production rollout plan when approved:
- [x] backup:
  - `services/waste-analysis-service/src/pdf/builder.py`
- [x] patch only that file.
- [x] compile-check patched file on server.
- [x] rebuild/restart runtime using server-build override:
  - `waste-analysis-service`
  - `waste-analysis-worker`
- [x] health-check waste service/worker.
- [x] smoke-check `/waste-analysis`.
- [x] inside-container template verification:
  - `Method` removed
  - `PF Estimated` removed
  - all four table footer totals visible

Important production note:
- Production services run from container image files under `/app`, not from the
  host repo source tree.
- While GHCR/GitHub Actions are exhausted, use:
  `docker compose -f docker-compose.yml -f docker-compose.server-build.yml up -d --build ...`
  after host-file patches so the running containers receive the patched code.

---

## Pending production patch: Machine Degradation Score Phase 1 foundation

Status: local complete on 2026-05-21. Not patched to production.

Purpose:
- Add backend foundation for a precomputed machine degradation score in `device-service`.
- Keep analytics-service untouched.
- Expose a read-only endpoint backed by precomputed DB rows.

Local files changed:
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

Safety:
- New degradation tables + device-service-only backend logic.
- No reporting, waste-analysis, copilot, auth, energy-service, or analytics-service code changed.
- No live dashboard calculation path; API reads only from `machine_health_latest`.

Local validation:
- [x] compile check passed for `services/device-service/app`
- [x] migration tests passed
- [x] scorer tests passed
- [x] feature aggregation tests passed
- [x] baseline learner tests passed
- [x] degradation API tests passed
- [x] degradation scheduler tests passed
- [x] total focused Phase 1 validation: `109 passed`
- [x] `git diff --check` passed

Production rollout plan when approved:
- [ ] backup:
  - `services/device-service/app/models/device.py`
  - `services/device-service/app/config.py`
  - `services/device-service/app/scheduler_runner.py`
  - `services/device-service/app/schemas/device.py`
  - `services/device-service/app/api/v1/devices.py`
  - `services/device-service/app/services/degradation/`
  - `services/device-service/alembic/versions/20260521_0001_machine_degradation_score.py`
- [ ] patch only the listed device-service files.
- [ ] run device-service migration on server.
- [ ] compile-check patched `device-service` source on server.
- [ ] rebuild/restart runtime using server-build override:
  - `device-service`
  - `device-service-scheduler`
- [ ] health-check service + scheduler.
- [ ] smoke-check:
  - `GET /api/v1/devices/{device_id}/degradation-score`
  - existing device dashboard/bootstrap routes still return expected responses
- [ ] verify scheduler logs show degradation cycles without crashing.

Notes:
- Phase 1 is backend-only. UI widget, anomaly activity, rule-engine coupling, and maintenance reset remain future work.

---

## Pending production patch: Machine Health Intelligence Phase 2

Status: local complete on 2026-05-21. Not patched to production.

Purpose:
- Anomaly detection with baseline learning
- Performance trend tracking with health-window aggregation
- Signal completeness and `insufficient_signals` first-class status
- Migrations 0001-0005; upgrade->downgrade->upgrade verified on live MySQL

Local validation:
- [x] all Phase 2 test suites passed
- [x] migrations verified on live MySQL

Production rollout plan when approved:
- [ ] run migrations 0002-0005 on server
- [ ] rebuild device-service and device-service-scheduler images
- [ ] health-check services
- [ ] smoke-check anomaly/performance-trend/degradation-history endpoints

---

## Pending production patch: Energy-service gap-closure fixes

Status: local complete on 2026-05-22. Not patched to production.

Purpose:
- Lock-exhaustion returns HTTP 503 with retryable flag instead of silently dropping
- Shared HTTP clients properly closed on lifespan shutdown

Files changed:
- `services/energy-service/app/services/energy_engine.py`
- `services/energy-service/app/services/device_meta.py`
- `services/energy-service/app/services/tariff_cache.py`
- `services/energy-service/app/api/routes.py`
- `services/energy-service/app/main.py`

Local validation:
- [x] 33 energy-service tests pass
- [x] compile check clean

Production rollout plan when approved:
- [ ] backup energy-service files listed above
- [ ] patch only listed files
- [ ] rebuild/restart energy-service
- [ ] health-check
- [ ] verify `/live-update/batch` still works; single `/live-update` returns 503 on lock contention

---

## Pending production patch: Device-service scale fixes

Status: local complete on 2026-05-22. Not patched to production.

Purpose:
- Scheduler session churn reduction (per-tenant sessions with savepoints instead of per-device)
- Dashboard telemetry HTTP call halving (fetch once for month, derive both today and month)
- Async-safe object-storage delete (asyncio.to_thread for MinIO/S3 remove_object)
- Separate DB pool for scheduler (SchedulerSessionLocal with pool_size=15, max_overflow=25)

Files changed:
- `services/device-service/app/scheduler_runner.py`
- `services/device-service/app/services/dashboard.py`
- `services/device-service/app/database.py`
- `services/device-service/app/config.py`
- `services/device-service/app/__init__.py`
- `services/device-service/tests/test_degradation_scheduler.py`

Local validation:
- [x] compile check clean
- [x] 214 tests passed across dashboard/scorer/anomaly/baseline/feature-window suites
- [x] pre-existing scheduler mock failure confirmed not caused by these changes

Production rollout plan when approved:
- [ ] backup device-service files listed above
- [ ] patch only listed files
- [ ] rebuild/restart device-service and device-service-scheduler
- [ ] health-check both containers
- [ ] verify scheduler logs show per-tenant session pattern
- [ ] verify dashboard snapshots still materialize correctly
- [ ] verify snapshot retention cleanup no longer blocks event loop

---

## Pending production patch: Data-service pool sizing and safety fixes

Status: local complete on 2026-05-22. Not patched to production.

Purpose:
- DB pool sizing configurable via env vars
- DLQ insert uses pool_timeout
- Outbox retry-count increment uses atomic SQL
- Enrichment service defensive fallback for malformed MQTT status

Files changed:
- `services/data-service/src/config/settings.py`
- `services/data-service/src/repositories/dlq_repository.py`
- `services/data-service/src/repositories/outbox_repository.py`
- `services/data-service/src/services/enrichment_service.py`

Local validation:
- [x] compile check clean

Production rollout plan when approved:
- [ ] backup data-service files listed above
- [ ] patch only listed files
- [ ] rebuild/restart data-service
- [ ] health-check
- [ ] verify outbox retry processing still works

---

## Pending production patch: Docker compose hardening

Status: local complete on 2026-05-22. Not patched to production.

Purpose:
- Redis auth with `REDIS_URL` pattern `redis://:${REDIS_PASSWORD:-}@redis:6379/0`
- Log rotation on all 30 services
- Memory limits on 23 services
- `expose:` instead of `ports:` for internal services
- FRONTEND_BASE_URL no longer defaults to localhost

Files changed:
- `docker-compose.yml`

Production rollout plan when approved:
- [ ] backup production docker-compose.yml
- [ ] patch compose file
- [ ] verify `docker compose config` validates
- [ ] rolling restart affected services
- [ ] verify Redis connectivity with and without password
