# Repository Memory

- Repository name: `Shivex-Main`
- Generation date: `2026-04-18`
- Branch: `main` (confirmed from `git branch --show-current`)
- Related appendices:
  - API appendix: [memory-appendix-api.md](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/memory.md/memory-appendix-api.md)
  - DB appendix: [memory-appendix-db.md](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/memory.md/memory-appendix-db.md)
- Scan summary:
  - Confirmed from code/config: root `README.md`, `docker-compose.yml`, `.env.production.example`, root `requirements*.txt`, all major service config/startup files, shared multi-tenant/auth code, major API entrypoints, key worker implementations, `ui-web` route/auth/api layers, `shivex-mobile` auth/store/routes, monitoring configs, MySQL init scripts, and top-level/service test layout.
  - Confirmed from docs where code matched or code was not the source of truth: service `README.md` files, `docs/auth_cutover_runbook.md`, `docs/aws_production_deployment.md`, `docs/preprod_validation.md`.
  - Not exhaustively scanned line-by-line: every schema/model/repository, every React component, every test body, legacy `Project-docs/` narrative docs, generated assets.
- Status legend used throughout:
  - `Confirmed from code`
  - `Inferred from usage`
  - `Not found in repository`
  - `Needs runtime verification`

## 2026-04-24 MQTT Validation Note

- Current device-MQTT implementation is present in code and validated locally after runtime cleanup:
  - EMQX TCP listener on `1883` is configured in [ops/emqx/local.base.hocon](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/ops/emqx/local.base.hocon).
  - Device auth is MySQL-backed against `device_mqtt_credentials`.
  - Device ACL is MySQL-backed against `device_mqtt_acl`.
  - `device-service` issues hashed passwords plus per-device ACL rows in [services/device-service/app/services/device_mqtt.py](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/services/device-service/app/services/device_mqtt.py).
  - Local device simulation on `1883` with fresh credential rotation succeeded end-to-end after cleanup.
- Important root cause discovered during re-validation:
  - Local EMQX persists runtime config overrides in `/opt/emqx/data/configs/cluster.hocon`.
  - A stale override had replaced the intended git-controlled MySQL auth config with a bad hardcoded server/query, which caused `emqx_authn_mysql` timeouts and rejected fresh MQTT logins even though `base.hocon` in git was correct.
  - This drift survived normal `docker compose down` / `up` because the EMQX data volume persisted.
- Local recovery that restored MQTT auth/ACL validation:
  - remove the stale EMQX data volume
  - recreate EMQX so it boots from the repo-controlled `ops/emqx/local.base.hocon`
  - once cleared, the local device simulator successfully:
    - bootstrapped/rotated a fresh MQTT credential
    - connected to EMQX on `1883`
    - published telemetry
    - telemetry was processed by downstream workers
- Operational rule:
  - Treat `ops/emqx/*.hocon` as the source of truth.
  - Do not make persistent auth/authz edits from the EMQX dashboard for local validation.
  - If MQTT runtime behavior does not match git config, inspect/reset EMQX runtime state before changing application code.

## 2026-04-25 Analytics Queue Self-Heal Note

- Production demo investigation found analytics workers repeatedly logging:
  - `NOGROUP No such key 'analytics_jobs_stream' or consumer group 'analytics_workers' in XREADGROUP with GROUP option`
- Confirmed local code root cause:
  - `services/analytics-service/src/workers/job_queue.py` created the Redis consumer group once and cached `_group_ready=True`.
  - If the Redis stream/consumer group disappeared later, `get_job()` kept calling `XREADGROUP` against a missing group and never reset/recreated it.
- Permanent local fix:
  - `RedisJobQueue.get_job()` now detects `NOGROUP`, resets group readiness, recreates the consumer group once, logs `redis_consumer_group_missing_recreating`, and retries the read.
- Validation completed from local codebase:
  - `python3 -m compileall services/analytics-service/src services/analytics-service/tests/unit/test_job_queue.py`
  - `docker compose build analytics-service analytics-worker analytics-worker-2`
  - in-container recovery execution check result: `analytics queue recovery check: PASS`
- Operational rule:
  - push this local analytics queue fix first, then pull/recreate analytics containers on server.
  - Do not rely on worker restarts alone if `NOGROUP` is observed again.

## 2026-04-26 Local Runtime Drift Note

- Local stack incident root cause:
  - several application containers were recreated with production-style values from `.env` instead of local values from `.env.local`
  - affected services then pointed `DATABASE_URL` / `MYSQL_HOST` at production RDS (`shivex-mysql-prod...`) instead of local Docker MySQL (`mysql`)
  - `device-service` and `rule-engine-service` failed migration guard startup, and `ui-web` surfaced repeated `500` proxy failures across Machines, Calendar, Reports, fleet APIs, and alerts
- Confirmed failure pattern from logs:
  - `Can't connect to MySQL server on 'shivex-mysql-prod.cmt486yymn9w.us-east-1.rds.amazonaws.com' (timed out)`
  - `Failed to proxy http://device-service:8000/... ECONNREFUSED`
  - `Failed to proxy http://rule-engine-service:8002/... ECONNREFUSED`
- Local recovery that restored the stack:
  - explicitly recreate the affected services with `--env-file .env.local -f docker-compose.yml -f docker-compose.local.yml`
  - after recreation, verify running container envs point back to `mysql:3306`
  - confirm core local health endpoints recover:
    - `device-service`
    - `rule-engine-service`
    - `data-service`
    - `reporting-service`
- Operational rule:
  - treat widespread local `500` errors after Docker restarts as possible env drift before assuming application-code regressions
  - validate the runtime env inside containers, not only the contents of `.env.local`

## 2026-04-29 Copilot Curated-Only UI Note

- Current product/UI assumption for local and rollout validation:
  - the web Copilot experience is curated-only from the user's perspective
  - free-form user typing is disabled in the UI flow being validated
  - users can only trigger starter curated questions and predefined follow-up questions
- Code-path clarification:
  - backend still contains AI-provider fallback paths for non-curated requests in `services/copilot-service/src/ai/copilot_engine.py` and `services/copilot-service/src/intent/router.py`
  - but the current shipped UI validation assumption is that users do not reach that free-form path because the UI only exposes predefined curated prompts/follow-ups
- Validation rule going forward:
  - when evaluating current Copilot product behavior, treat it as curated-only unless the UI is explicitly changed to re-enable free-text questioning
  - do not repeatedly classify current Copilot rollout status based on hypothetical free-form prompts if the UI path under test does not allow them

## 2026-04-30 Validation and CI Maturity Note

- Current validation model is intentionally split into three layers:
  - `Level 1`: targeted deterministic CI regressions for every normal code push/PR
  - `Level 2`: broader non-destructive validation for stronger pre-release confidence
  - `Level 3`: live deployed-environment smoke validation after server deploy
- The repo now has a local CI mirror and GitHub Actions workflow for the Level 1 layer:
  - local mirror command: [scripts/run-ci-validation.sh](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/scripts/run-ci-validation.sh)
  - CI workflow: [.github/workflows/validation.yml](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/.github/workflows/validation.yml)
  - CI coverage contract: [docs/ci-validation.md](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/docs/ci-validation.md)
- Current Level 1 CI covers the high-signal targeted regression slices added during the gap-closure work:
  - entitlements
  - platform maintenance
  - simulator startup
  - deploy recovery
  - machine activity-history resilience
  - machine dashboard latency guard
  - machine detail bootstrap contract
  - analytics long-running truthfulness
  - financial consistency
  - notification/settings
  - scheduled reports
- Important boundary:
  - Level 1 CI does **not** replace live environment checks for production integrations such as RDS, S3, MQTT/EMQX, real async jobs, or full deployed-browser behavior.
  - Those still belong to broader validation and/or post-deploy smoke.
- Operational guidance:
  - normal development flow should prefer feature branches instead of working directly on `main`
  - default pre-push check is the local CI mirror command
  - broader validation should still be used before higher-risk releases or deploys

## 2026-05-03 Backend Debugger Mode Rollout Note

- The permanent backend debugger-mode rollout is complete across all core services:
  - `Confirmed from code`: shared debug bootstrap at `services/shared/debug_bootstrap.py` (env-gated, no-op by default, 17 unit tests passing).
  - `Confirmed from code`: `init_debug()` wired into all 10 API entrypoints and all 4 worker entrypoints.
  - `Confirmed from code`: `debugpy>=1.8.0` added to all 11 service requirements files (10 API + 1 analytics-worker).
  - `Confirmed from config`: `docker-compose.debug.yml` overlay exposes ports 5671-5686 for 16 containers.
  - `Confirmed from config`: `.vscode/launch.json` provides 16 attach configs + 4 compound configs.
  - `Confirmed from validation`: base compose files (`docker-compose.yml`, `docker-compose.local.yml`) have zero `DEBUGPY` references — debugger mode is fully opt-in.
  - `Confirmed from validation`: normal startup behavior is unchanged when `DEBUGPY_ENABLE` is unset.
- Source of truth: [`debugger.md`](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/implementation-docs/debugger.md).
- Operational rule:
  - never set `DEBUGPY_ENABLE=true` in committed `.env` or compose files other than `docker-compose.debug.yml`.
  - never add `--workers N` to uvicorn without also solving per-worker debug port allocation.

## 2026-05-03 UI E2E Closure Note

- The deterministic browser E2E lane is now fully closed and locally verified:
  - `Confirmed from code and local validation`: [`UI_E2E_CHECKLIST.md`](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/implementation-docs/UI_E2E_CHECKLIST.md) stands at `88 completed / 0 partial / 0 missing`.
  - `Confirmed from local validation`: Playwright default run is `53 passed / 9 skipped / 0 failed`.
  - `Confirmed from local validation`: Playwright headed run is `53 passed / 9 skipped / 0 failed`.
  - `Confirmed from local validation`: Playwright UI startup works on `127.0.0.1:9323`.
- Important testing boundary:
  - `Confirmed from code and runtime`: the default Playwright lane is a deterministic browser suite using mocked/test-harnessed backend contracts for stability.
  - `Confirmed from runtime`: local logs may still show upstream proxy `ECONNREFUSED` noise for ports like `8000`, `8002`, `8081`, `8090` when those services are not running, but this does not invalidate the passing deterministic browser suite.
- Practical command set:
  - `./node_modules/.bin/playwright test --reporter=line`
  - `./node_modules/.bin/playwright test --headed --reporter=line`
  - `./node_modules/.bin/playwright test --ui --ui-host 127.0.0.1 --ui-port 9323`
  - `PW_SLOW_MO=1200 ./node_modules/.bin/playwright test --headed --reporter=line`
- Demo/debug guidance:
  - use `--headed` with `PW_SLOW_MO` for a slow visual walkthrough
  - use `--ui` for trace/log inspection and running one spec at a time
  - use `PWDEBUG=1` only for step-debugging, not for smooth demo playback

## 2026-05-06 Machine Detail Telemetry Architecture Note

- The machine-detail runtime/read-path is now intentionally split into two lanes:
  - fast projection lane for machine-now truth
  - deeper history lane for paginated/raw telemetry history
- `Confirmed from code`: first useful shell and first useful detail render no longer depend on synchronous raw Influx history for active devices.
- Permanent ownership after the May 2026 hardening:
  - shell / overview status truth: `Device` + `DeviceLiveState`
  - detailed KPI first render: `DeviceLatestTelemetrySnapshot`
  - telemetry tab first render: bounded recent telemetry buffer in device-service
  - deeper telemetry history: explicit data-service history endpoint
  - degraded history: explicit timeout/unavailable contract instead of fake `success + empty`
- `Confirmed from code`: `current-state` is now projection/snapshot-backed rather than doing a hidden raw `limit=1` telemetry read.
- Operational rule:
  - if the page shows fresh shell state but empty KPIs/telemetry for an active device, treat that as a read-lane regression first, not as a simulator/onboarding problem.
  - do not “fix” active-device contradictions by deleting/re-onboarding devices.

## 2026-05-06 Device-Service Migration Chain Note

- A production deploy failure exposed a device-service Alembic chain mismatch after the recent telemetry-buffer work landed.
- Root cause:
  - [20260506_0002_add_recent_telemetry_samples.py](/Users/vedanthshetty/Desktop/GIT-Testing/Shivex-Main/services/device-service/alembic/versions/20260506_0002_add_recent_telemetry_samples.py) used a human-readable revision name in `down_revision` instead of the actual prior Alembic revision ID.
- Permanent correction already pushed to `main` and deployed:
  - commit `24a79f04` `Fix device-service telemetry migration chain`
  - `down_revision` now points to `20260506_0001`
- Operational rule:
  - when adding new Alembic revisions, always chain by the actual `revision` identifier string, not by the filename/docstring alias.
  - if deploy rebuilds fail at migration guard after a green CI, inspect revision linkage before assuming application/runtime regressions.

## 2026-05-06 Broad CI Coverage Truthfulness Note

- Broad CI runner topology was simplified, but suite coverage was not reduced.
- `Confirmed from code`: previously separate queued suites like `Premium Feature Gating` and `Database Integrity And Concurrency` were folded into the already-running shard that covers rules/platform/runtime validation.
- A second permanent fix was required in the aggregate summary:
  - old behavior could omit suites that never produced artifacts, causing the table to look fully green even when some suites never ran.
  - current behavior loads the expected broad-suite manifest and fails aggregate validation if any suite is missing, duplicated, unexpected, or failed.
- Operational rule:
  - treat “green summary table with missing suite execution” as a CI contract bug, not acceptable signal.
  - broad CI summary must represent complete expected suite coverage, not only available artifacts.

## 2026-05-06 Analytics Temporal-Autoencoder Hardening Note

- Production/server validation exposed a long-running anomaly-job stall around `61.33%` in the Analytics UI.
- Root cause:
  - anomaly jobs could complete isolation-forest and sequence-preparation stages, enter temporal autoencoder training, and then sit in that substage without a bounded time budget or visible elapsed-stage progress.
  - the UI therefore showed a frozen in-progress state even though the backend worker was still alive.
- Permanent local fix landed on `Dev-Testing` and was later merged/deployed:
  - commit `9505572c` `Harden analytics temporal autoencoder progress`
  - merged into `main` before server rollout
- `Confirmed from code`: the fix adds:
  - bounded temporal autoencoder training time budget
  - minimum-epoch floor before capping
  - elapsed-stage heartbeat progress updates during long model-execution substeps
  - truthful degradation metadata when the temporal model is time-capped instead of letting the whole anomaly job appear frozen
- User-facing effect:
  - long anomaly jobs should no longer appear dead at the same static percentage while the worker is still active
  - if the temporal model is capped for responsiveness, the job can still proceed with truthful result metadata instead of hanging indefinitely
- Operational rule:
  - analytics progress plateaus around low-60% for anomaly jobs usually point to the temporal-autoencoder branch, not the queue itself
  - treat a static progress value with fresh worker heartbeat as a model-execution UX/timeout issue, not a generic polling failure

## 2026-05-09 Reset Recovery, GHCR Deploy, and Runtime Bring-Up Note

- A destructive simulator/test reset exposed a real product/runtime boundary:
  - wiping table data while preserving schema/migrations can leave allocator/bootstrap state empty even when services still start healthy
  - this is not the same as dropping and recreating the whole schema
- Permanent allocator/bootstrap hardening is now part of the codebase:
  - `Confirmed from code`: auth startup now idempotently ensures tenant allocator state for `tenant_id_sequences`
  - `Confirmed from code`: device-service startup now idempotently ensures allocator state for `device_id_sequences` and `hardware_unit_sequences`
  - `Confirmed from code`: auth allocator startup is schema-aware and no-ops safely when minimal/pre-migration SQLite test schemas do not yet contain `organizations` / `tenant_id_sequences`
- Reporting tariff contract is now complete:
  - `Confirmed from code`: reporting-service supports tariff history retrieval and historical version activation rather than relying on UI tolerance for a missing route
  - operationally, tariff save + history is now a backend-owned contract, not a partial UI flow
- Waste-analysis date behavior required two permanent UI fixes:
  - `Confirmed from code`: shared date-range math now uses local calendar day semantics instead of UTC day boundaries for presets/defaults
  - `Confirmed from code`: `DateRangeSelector` now guards against reapplying the same initial range on parent re-render, preventing preset snap-back to `Last 7 days`
- Post-reset runtime lesson:
  - after large stack restarts/resets, `docker compose up -d` may leave some app services in `Created` while others are already healthy
  - this can surface as feature-specific breakage even when “most of the stack” looks fine
  - services specifically observed in this failure mode during May 2026 validation included `copilot-service`, `rule-engine-service`, `waste-analysis-service`, `analytics-service`, `data-service`, and `data-export-service`
- Operational rule for post-reset or post-deploy verification:
  - do not declare the stack healthy from a partial spot-check
  - always verify with `docker compose ps --all` plus direct health checks for every core app service
  - treat `Created` as not-up, even if surrounding services are healthy
- Analytics dependency lesson:
  - `Confirmed from runtime`: analytics jobs stuck around `20.75%` in readiness can indicate `data-export-service` is not running, because exact-range parquet export is a prerequisite for analytics progression
  - do not misclassify that symptom as only a frontend progress bug
- GHCR production deploy path is now the standard and was validated against the May 2026 fix set:
  - update `.env` image tag (`APP_IMAGE_TAG=sha-...`)
  - `docker compose --env-file .env pull`
  - `docker compose --env-file .env up -d`
  - verify with `docker compose ps --all` and core health endpoints
  - rerun GHCR login only if `pull` fails with registry auth/package permission errors
- GHCR fallback plan remains important and should not be forgotten:
  - `Confirmed from docs/config`: if GHCR publishing is unavailable, packages are missing, or Actions minutes are exhausted, use the server-build override path instead of changing application code
  - canonical fallback command:
    - `docker compose --env-file .env -f docker-compose.yml -f docker-compose.server-build.yml up -d --build`
  - operational rule:
    - GHCR is the preferred normal deploy path
    - `docker-compose.server-build.yml` is the emergency backup lane

## 2026-05-16 Phase 1 Performance Audit Note

- Scope:
  - local repo audit only; no production mutation; findings validated from `services/shared/auth_middleware.py`, `ui-web/next.config.ts`, `ui-web/server.mjs`, `ui-web/proxy.ts`, `services/device-service/app/api/v1/devices.py`, service startup scripts, `SCALING_READINESS.md`, and `SCALING_ROLLOUT_PLAN.md`.
- `Confirmed from code`: shared bearer-auth on backend services is a repeated per-request latency tax, not just JWT decode.
  - In bearer-authenticated requests, shared middleware performs:
    - JWT decode
    - Redis revocation lookup
    - auth DB read for user + tenant freshness
    - extra auth DB read for tenant feature entitlements
    - plant-scoped roles add another DB read for `user_plant_access`
  - Internal service requests can bypass this path via `X-Internal-Service` headers with tenant headers.
  - Relevant code: `services/shared/auth_middleware.py:110-115`, `125-203`, `262-312`, `323-380`.
- `Confirmed from code`: explicit response compression is not configured in Shivex application code today.
  - No `GZipMiddleware` / `CompressionMiddleware` was found in the inspected FastAPI services or `ui-web`.
  - `ui-web` runs through the custom `node server.mjs` entrypoint rather than an explicitly configured compression layer.
  - This confirms code-level absence of explicit compression enablement, but runtime header verification is still required before claiming end-to-end compression is absent in deployed environments.
- `Confirmed from code`: the strongest explicit `no-store` posture is concentrated in document/app-shell responses and device-service read paths.
  - HTML/document responses are forced `no-store` in `ui-web/next.config.ts`, `ui-web/server.mjs`, and `ui-web/proxy.ts`.
  - Device dashboard/live/snapshot endpoints intentionally send `Cache-Control: no-store`, including fleet SSE, dashboard summary, fleet snapshot, dashboard bootstrap, detail snapshot, today loss breakdown, and monthly energy calendar.
  - UI fetch helpers also repeatedly request `cache: "no-store"` for those endpoints and for several config/history reads such as maintenance logs, shifts, uptime, and health-config reads.
- `Confirmed from code`: some device-service reads are materially more snapshot/config-like than live-stream-like, but they are still currently uncached by both server header and UI fetch choice.
  - Candidate later-phase review set: maintenance logs, shift lists, uptime, health-config reads, and performance trends.
  - Do not change these blindly; the current UI performs immediate post-write refreshes and expects truthful read-after-write behavior.
- `Confirmed from code`: the “single-process API runtime posture” concern is a deployment/runtime finding, not a hidden code toggle.
  - The inspected API entrypoints start plain `uvicorn` with host/port only and no `--workers` setting in `device-service`, `auth-service`, `energy-service`, `analytics-service`, and `reporting-service`.
  - This means vertical/horizontal API concurrency posture is currently set by container topology rather than multi-worker process configuration in the repo startup scripts.
- Operational guidance for later phases:
  - keep live/snapshot truth endpoints fully uncached until a route-by-route freshness policy is explicitly defined and runtime-validated
  - treat auth middleware reduction, compression verification, and route cache classification as separate follow-on tracks
  - keep infra recommendations aligned with production reality: RDS + S3 plus Dockerized services

## 2026-05-16 Phase 2 Shared Auth Middleware Optimization Note

- Scope:
  - local repo only; validated against `services/shared/auth_middleware.py` and focused auth middleware tests.
- `Confirmed from code and targeted validation`: the safest Phase 2 win was to remove the extra tenant-entitlements DB read on the normal bearer-authenticated same-tenant path without weakening revocation or version freshness checks.
  - shared middleware still performs per-request:
    - JWT decode
    - Redis revocation lookup
    - auth DB read for current user/tenant/version state
    - plant-access DB read for plant-scoped roles only
  - but it no longer performs a second tenant-entitlements DB lookup for the common case where the authenticated user's tenant scope matches the request tenant scope.
- Permanent implementation shape:
  - `_load_current_auth_state()` now fetches tenant entitlement inputs (`premium_feature_grants_json`, `role_feature_matrix_json`, `tenant_entitlements_version`) together with the existing user freshness row and builds inline tenant feature state there.
  - middleware reuses that inline tenant feature state only when the resolved request tenant matches the authenticated tenant from the validated auth-state row.
  - super-admin target-tenant flows still fall back to the explicit tenant-feature lookup because those requests can intentionally target a tenant different from the authenticated row's tenant scope.
- Safety boundary:
  - Redis revocation remains authoritative on every bearer-authenticated request.
  - `permissions_version` and `tenant_entitlements_version` are still validated against the database on every bearer-authenticated request.
  - no in-process auth-state cache was added in this phase, specifically to avoid introducing a short stale window that would weaken revocation/version freshness guarantees without a stronger invalidation design.
  - plant-scoped user access remains DB-derived and per-request correct.
- Observability:
  - middleware now logs phase timings for JWT decode, revocation check, auth-state load, and tenant-feature-state resolution.
  - normal timing logs are debug-level; slow paths log a warning when total auth middleware time exceeds `AUTH_MIDDLEWARE_SLOW_MS` (default `250` ms).
- Validation completed:
  - focused pytest slice for auth middleware/version/revocation behavior passed after the change set.
- do not mix the two paths casually during the same rollout without being explicit about which path is active
- Preferred future test-environment rule:
  - for hard validation on disposable EC2, prefer a server-local env file derived from `.env.local` (for Docker MySQL + MinIO) instead of reusing production RDS/S3 credentials
  - change only the server-facing public URL/IP values in that env file; keep internal Docker-network service URLs stable

## 2026-05-10 Capacity Engineering: Outbox Relay Improvements

- Three outbox-relay improvements landed locally:
  - Device power-config TTL cache (300s default) in `OutboxRelayService._fetch_device_power_config` — eliminates per-row HTTP GET feedback loop to device-service during DEVICE_SERVICE outbox delivery
  - Explicit `outbox_retry_backoff_base_seconds=5` setting — decoupled from `outbox_poll_interval_sec` which was incorrectly reused as backoff base (forced to 1s via `max(1, int(0.5))`)
  - Targeted circuit-breaker `half_open_max_calls=3` for outbox relay breakers — was default 1, now allows 3 concurrent probes during half-open recovery
- `Confirmed from code`: cache key is `(tenant_id, device_id)` tuple — no cross-tenant leakage possible
- `Confirmed from code`: failed HTTP fetches return `None` without caching — no stale poison
- Operational rule:
  - after deploying, monitor `outbox pending/failed` counts to confirm the feedback loop is broken
  - the 300s TTL means device config changes (energy_flow_mode, polarity_mode) take up to 5 minutes to propagate through the outbox path; reconciliation catches drift faster

## 2026-05-10 Capacity Engineering: Layer 2 Redis Tenant Lock

- `RedisTenantLock` implemented in `tenant_lock.py` as a second `TenantLockProvider` using Redis `SET NX PX` + Lua compare-and-delete release
- `Confirmed from code`: lock key format `shivex:tenant_lock:projection:{tenant_id}` — tenant-isolated by construction, no cross-tenant leakage possible
- `Confirmed from code`: lock value is `{hostname}:{pid}:{uuid4[:8]}:{uuid4[:8]}` per acquire — only the holder can release (Lua script compares before DEL)
- `Confirmed from code`: TTL default 30s set via `PX` — auto-expires on worker crash; `tenant_lock_redis_ttl_seconds` setting controls this
- `Confirmed from code`: acquisition timeout default 15s with exponential backoff polling (50ms base, 500ms max, 2× backoff) — raises `TenantLockTimeoutError` on timeout
- `Confirmed from code`: `TenantLockTimeoutError` caught in `_handle_projection_batch` and treated as `downstream_overload` defer-class transient, routed to `_handle_projection_retryable_failure` — not a permanent generic failure
- `Confirmed from code`: `create_tenant_lock` factory returns `InProcessTenantLock` by default, `RedisTenantLock` when `tenant_lock_provider=redis`
- `Confirmed from code`: `InProcessTenantLock` is unchanged and remains the default-safe behavior
- New settings: `tenant_lock_provider=in_process`, `tenant_lock_redis_ttl_seconds=30`, `tenant_lock_redis_acquire_timeout_seconds=15.0`
- New Prometheus metric: `projection_tenant_lock_redis_acquire_duration_seconds` (Histogram, labels: `outcome=acquired|timeout`)
- `Confirmed from code`: batch DeviceLiveState writes no longer rely on blind `"locked"` semantics alone; the batch path now uses a version-guarded compare-and-swap update and increments `device_live_update_batch_version_conflict_total` if an unexpected concurrent writer is detected
- Operational rule:
  - Redis tenant lock remains the primary projection serializer
  - version-guarded batch writes are the defense-in-depth layer against rare lock expiry / concurrency drift
  - any non-zero `device_live_update_batch_version_conflict_total` after rollout should be treated as a real concurrency warning, not ignored
- docker-compose.yml wired with `TENANT_LOCK_PROVIDER=in_process` on both worker containers — safe default, Redis mode not yet enabled
- `with_for_update()` removed from device-service `live_projection.py` batch projection SELECT — server-validated in V6 with Redis lock enabled
- V6 combined validation: projection backlog 0, outbox failed 0, zero lock timeouts, http_req_failed 4.62%
- V6 k6 check failures (`GET history` 59%, `POST run` 55%) traced to k6 harness bug: waste-analysis URLs used `/api/waste/analysis/...` but service mounts at `/api/v1/waste/analysis/...` — fix applied to `workloads.js`
- Operational rule:
  - default `in_process` mode means zero behavior change from prior — Redis lock is feature-flagged off
  - to enable Redis mode on server: set `TENANT_LOCK_PROVIDER=redis` on both worker containers, redeploy
  - after enabling, monitor `projection_tenant_lock_acquire_total{contention=contended}` — should drop significantly
  - after enabling, monitor `projection_tenant_lock_redis_acquire_duration_seconds` — should observe <1s for most acquisitions

## Memory Maintenance

- Refresh [memory-appendix-api.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md) fully when routes, DTOs, auth middleware behavior, internal HTTP calls, frontend rewrites, or realtime interfaces change.
- Refresh [memory-appendix-db.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md) fully when models, migrations, raw SQL bootstrap files, repository query patterns, or tenant-scoping rules change.
- Update [memory.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory.md) incrementally for service ownership, flows, runtime entrypoints, environment/config, and change-impact guidance if the appendices still match code.
- Rebuild all three together after branding changes, auth/session refactors, tenant-isolation refactors, queue/worker redesigns, or any service split/merge.

## Appendix Guide

- Use [memory-appendix-api.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md) for exact endpoint maps, DTOs, internal service-to-service calls, polling/SSE/WebSocket surfaces, and API risk areas.
- Use [memory-appendix-db.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md) for schema truth, migration history, repository/query patterns, tenant-scoping at the data layer, and DB risk areas.
- This file stays focused on architecture, business flows, module ownership, runtime/config, and change impact.

## Fast Paths For Common Changes

- Change auth/session behavior:
  - start in `services/auth-service/app/api/v1/auth.py`, `services/auth-service/app/services/auth_service.py`, `services/auth-service/app/services/token_service.py`, `services/shared/auth_middleware.py`, `ui-web/lib/authApi.ts`, `ui-web/lib/authBootstrap.ts`, `ui-web/lib/browserSession.ts`, `shivex-mobile/src/api/authApi.ts`
  - API map: [memory-appendix-api.md#auth-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#auth-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change analytics behavior:
  - start in `services/analytics-service/src/api/routes/analytics.py`, `src/infrastructure/mysql_repository.py`, `src/workers/job_queue.py`, `src/workers/job_worker.py`, `src/services/scaling_policy.py`, `ui-web/app/(protected)/analytics/*`
  - API map: [memory-appendix-api.md#analytics-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#analytics-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change reports:
  - start in `services/reporting-service/src/handlers/`, `src/services/report_engine.py`, `src/repositories/report_repository.py`, `src/repositories/scheduled_repository.py`, `ui-web/app/(protected)/reports/*`
  - API map: [memory-appendix-api.md#reporting-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#reporting-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change telemetry ingest or public telemetry APIs:
  - start in `services/data-service/src/handlers/mqtt_handler.py`, `src/services/telemetry_service.py`, `src/workers/telemetry_pipeline.py`, `src/repositories/influxdb_repository.py`, `src/repositories/outbox_repository.py`
  - API map: [memory-appendix-api.md#data-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#data-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change notifications or alert delivery:
  - start in `services/rule-engine-service/app/services/evaluator.py`, `app/services/notification_outbox.py`, `app/workers/notification_worker.py`, `app/repositories/notification_delivery.py`, `app/repositories/notification_outbox.py`, and reporting-service `src/models/settings.py` / `src/repositories/settings_repository.py` for shared notification channels
  - API map: [memory-appendix-api.md#rule-engine-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#rule-engine-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change dashboard status/runtime/load behavior:
  - start in `services/device-service/app/services/live_projection.py`, `app/services/idle_running.py`, `app/api/v1/devices.py`, `services/energy-service/app/api/routes.py`, and frontend dashboard pages under `ui-web/app/(protected)/devices/*`, `machines/*`, and related client hooks
  - API map: [memory-appendix-api.md#device-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#device-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Change branding:
  - start in root `README.md`, `services/auth-service/app/config.py`, `ui-web` metadata/layout files, and `shivex-mobile` app config plus auth-facing email/template strings
  - current state is mixed `FactoryOPS / Cittagent / Shivex`; do not assume one canonical name without checking code paths and user-facing copy

- Change tenant isolation:
  - start in `services/shared/auth_middleware.py`, `services/shared/tenant_context.py`, `services/shared/tenant_guards.py`, `services/shared/scoped_repository.py`, then inspect service-specific repository filters and internal header builders
  - API map: [memory-appendix-api.md#6-api-contracts-and-shared-types](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - DB map: [memory-appendix-db.md#5-tenant-isolation-in-data-model](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

## 1. Platform Overview

- Product identity:
  - `Confirmed from code`: the repository contains a multi-service industrial monitoring / energy operations platform with device telemetry, dashboards, alerts/rules, analytics, reporting, waste analysis, and AI copilot capabilities (`README.md`, `docker-compose.yml`, service folders under `services/`).
  - `Confirmed from code`: current branding is mixed.
    - `FactoryOPS / Cittagent` appears in root repo naming and `README.md`.
    - `Shivex` appears in auth defaults and web/mobile branding defaults, for example `services/auth-service/app/config.py:38-48` and web/mobile naming in `ui-web` / `shivex-mobile`.
  - `Inferred from usage`: this is B2B SaaS for industrial/factory operators and administrators. Evidence: tenant/org/plant hierarchy, invitation flows, org feature entitlements, plant-scoped users, dashboards by machine/fleet/energy/reporting domain.

- Business purpose:
  - `Confirmed from code`: ingest power/telemetry data from devices, normalize and persist it, project live state to dashboards, evaluate rules/alerts, compute energy and waste insights, generate reports, and optionally answer tenant-scoped questions through AI copilot.

- Primary actors:
  - `Confirmed from code`: `super_admin`, `org_admin`, `plant_manager`, `operator`, `viewer` are the implemented role set (`app.models.auth.UserRole` usage in auth routes and `services/shared/feature_entitlements.py:23-49`).
  - `Confirmed from code`: org/tenant admins can create users and plants; plant managers are constrained to lower-privilege users (`services/auth-service/app/api/v1/orgs.py:79-224`).

- Major product capabilities:
  - `Confirmed from code`: auth, login, refresh, invite acceptance, password reset (`services/auth-service/app/api/v1/auth.py`, `services/auth-service/app/services/auth_service.py`).
  - `Confirmed from code`: super-admin platform maintenance announcements with relational tenant targeting and tenant-aware current-read API (`services/auth-service/app/api/v1/admin.py`, `services/auth-service/app/api/v1/platform_maintenance.py`, `services/auth-service/app/repositories/platform_maintenance_repository.py`).
  - `Confirmed from code`: super-admin platform maintenance scheduling workflow in the web admin area, including saved notice list, announcement editor, audience selection, and preview banner (`ui-web/app/(protected)/admin/platform-maintenance/page.tsx`, `ui-web/lib/platformMaintenance.ts`, `ui-web/components/admin/PlatformMaintenancePreview.tsx`).
  - `Confirmed from code`: platform maintenance now has durable auth-service email delivery tracking plus a background delivery worker, and tenant-scoped in-app maintenance banners in the authenticated web shell (`services/auth-service/app/services/platform_maintenance_delivery.py`, `services/auth-service/app/models/auth.py`, `ui-web/components/layout/PlatformMaintenanceBanner.tsx`).
  - `Confirmed from code`: platform maintenance status is now time-derived consistently across admin responses, tenant banner reads, and delivery email wording; suspended organisations are blocked from new targeting and do not receive current-banner visibility (`services/auth-service/app/services/platform_maintenance_status.py`, `services/auth-service/app/api/v1/admin.py`, `services/auth-service/app/repositories/platform_maintenance_repository.py`).
  - `Confirmed from code`: device inventory, live dashboard state, health config, machine runtime/load classification, fleet streams (`services/device-service/app/...`, `services/device-service/README.md`).
  - `Confirmed from code`: MQTT telemetry ingest, validation, Influx persistence, Redis-stream pipeline, WebSocket/broadcast, downstream projection, energy/rules fan-out (`services/data-service/src/...`).
  - `Confirmed from code`: energy projections and summaries (`services/energy-service/app/api/routes.py`).
  - `Confirmed from code`: alert/rule evaluation and notification outbox delivery (`services/rule-engine-service/app/services/evaluator.py`, `notification_outbox.py`, `workers/notification_worker.py`).
  - `Confirmed from code`: analytics jobs and ML job queueing (`services/analytics-service/src/...`).
  - `Confirmed from code`: report generation and downloadable artifacts via MinIO/object storage (`services/reporting-service/src/...`).
  - `Confirmed from code`: waste-analysis jobs with PDF/object storage outputs (`services/waste-analysis-service/src/...`).
  - `Confirmed from code`: AI copilot with tenant-scoped SQL guard and curated prompts (`services/copilot-service/src/...`).

- Multi-tenant model:
  - `Confirmed from code`: tenant isolation is a first-class concern. Shared middleware derives tenant context from JWT claims and request headers (`services/shared/auth_middleware.py`, `services/shared/tenant_context.py`).
  - `Confirmed from code`: tenant-scoped repositories automatically filter on `tenant_id` when models include that column (`services/shared/scoped_repository.py`).
  - `Confirmed from code`: cross-tenant access is blocked and audited through tenant guards (`services/shared/tenant_guards.py:87-141`).
  - `Confirmed from code`: super admins can operate without a tenant claim and select a target tenant via `X-Target-Tenant-Id` / query parameter (`services/shared/auth_middleware.py:179-214`, `services/shared/tenant_context.py`).
  - Detailed API-side auth/tenant contract: [memory-appendix-api.md#6-api-contracts-and-shared-types](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - Detailed data-side tenant map: [memory-appendix-db.md#5-tenant-isolation-in-data-model](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

## 2. High-Level Architecture

- Architecture style:
  - `Confirmed from code`: hybrid service-oriented architecture, not a single monolith. Services are independently containerized in `docker-compose.yml` and have separate codebases under `services/`.
  - Detailed HTTP/API surface: [memory-appendix-api.md#1-api-surface-overview](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - Detailed persistence/service datastore map: [memory-appendix-db.md#1-database-overview](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Service boundaries:
  - `Confirmed from code`:
    - `auth-service`: identity, orgs/plants/users, tokens, invitations, entitlements.
    - `device-service`: device CRUD, live/fleet state, health configs, machine runtime/load state, dashboard materialization.
    - `data-service`: telemetry ingest API/MQTT bridge, Redis stage pipeline, Influx persistence, DLQ/outbox.
    - `energy-service`: energy projections and summaries.
    - `rule-engine-service`: rule evaluation, alert creation, notification delivery.
    - `analytics-service`: queued analytics/ML jobs and result formatting.
    - `reporting-service`: report jobs, datasets, report files, tariff-driven reporting.
    - `waste-analysis-service`: waste-analysis jobs and artifacts.
    - `data-export-service`: telemetry export to Parquet/CSV datasets in object storage.
    - `copilot-service`: AI-assisted tenant-scoped querying and curated Q&A.
    - shared cross-cutting package: `services/shared`.

- Request flow overview:
  - `Confirmed from code`: browser/mobile -> `ui-web` Next.js rewrite proxy or direct mobile API -> backend services.
  - `Confirmed from code`: most service-to-service calls carry internal service and tenant headers built from shared helpers (`services/shared/tenant_context.py`).
  - `Confirmed from code`: backend auth enforcement is middleware-first; feature gating is route-level in some services.

- Real-time / live-update architecture:
  - `Confirmed from code`: telemetry lands in `data-service`, persists to Influx, then projection/broadcast stages update dashboard consumers.
  - `Confirmed from code`: device live state is persisted in MySQL table/model layer via live projection logic and distributed to fleet subscribers through Redis fan-out (`services/device-service/app/services/live_projection.py`, `services/device-service/app/config.py:91-96`).
  - `Confirmed from code`: energy-service publishes Redis energy update events (`services/energy-service/app/main.py` startup + broadcaster).
  - `Needs runtime verification`: exact browser subscription transport for every dashboard page. Web app clearly consumes protected APIs and has live pages, but not every component path was traced end-to-end.

- Async / background architecture:
  - `Confirmed from code`: Redis streams are used for durable telemetry and analytics/reporting queueing.
  - `Confirmed from code`: background workers exist for:
    - telemetry pipeline (`data-service`)
    - rule-engine notification outbox worker
    - analytics job workers
    - reporting job workers
    - data export worker
    - refresh token cleanup loop in auth-service
    - APScheduler tasks in reporting-service
    - weekly retrainer in analytics-service

- Internal communication patterns:
  - `Confirmed from code`: synchronous HTTP service calls with tenant-scoped internal headers.
  - `Confirmed from code`: Redis streams / consumer groups for durable background pipelines.
  - `Confirmed from code`: Redis pub/sub channels for live fan-out in device/energy domains.
  - `Confirmed from code`: MQTT input through EMQX to `data-service`.

- Deployment model:
  - `Confirmed from code`: local/dev/preprod orchestration via Docker Compose (`docker-compose.yml`).
  - `Confirmed from docs`: production deployment guidance exists in `docs/aws_production_deployment.md`.
  - `Not found in repository`: Terraform / Helm / Kubernetes manifests.
  - `Needs runtime verification`: actual production hosting/runtime topology.

## 3. Technology Stack

### Frontend

- `Confirmed from code`: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Radix UI, Recharts, `@tanstack/react-query`, `framer-motion`, `lucide-react` (`ui-web/package.json`).
- `Confirmed from code`: Expo / React Native mobile app with Expo Router, Zustand, SecureStore (`shivex-mobile/package.json`).

### Backend

- `Confirmed from code`: Python FastAPI across services.
- `Confirmed from code`: Uvicorn process startup for API services.
- `Confirmed from code`: SQLAlchemy async + Alembic migrations.
- `Confirmed from code`: Pydantic / `pydantic-settings`.
- `Confirmed from code`: Pandas / NumPy in reporting and waste/analytics codepaths.

### Databases

- `Confirmed from code`: MySQL for relational tenant/auth/device/job/outbox data.
- `Confirmed from code`: InfluxDB for telemetry time-series (`data-service`, reporting, waste).

### Queues / Messaging

- `Confirmed from code`: Redis Streams for telemetry, analytics jobs, report jobs, rule notification outbox.
- `Confirmed from code`: Redis pub/sub for live fleet / energy broadcasts.
- `Confirmed from code`: MQTT via EMQX for telemetry ingress.

### Caching

- `Confirmed from code`: Redis for auth token revocation state, issued token tracking, queueing, and live channels.
- `Confirmed from code`: in-process tariff caches and stale fallbacks in device/waste/energy code.

### Auth

- `Confirmed from code`: JWT access tokens signed with shared secret (`services/auth-service/app/services/token_service.py`).
- `Confirmed from code`: refresh tokens stored hashed in MySQL.
- `Confirmed from code`: HttpOnly cookie refresh for web; explicit refresh token storage for mobile.
- `Confirmed from code`: browser refresh/logout flows are cookie-first, with origin checks on cookie-bound requests in auth-service.

### Storage

- `Confirmed from code`: MinIO / S3-compatible object storage for datasets and generated reports.
- `Confirmed from code`: buckets include `energy-platform-datasets` and `factoryops-waste-reports` (`docker-compose.yml`, `createbuckets` service).

### Observability

- `Confirmed from code`: Prometheus, Grafana, Alertmanager in `monitoring/`.
- `Confirmed from code`: health/ready/metrics endpoints across services.
- `Confirmed from code`: structured logging patterns in several services.

### Testing

- `Confirmed from code`: `pytest`-based backend tests.
- `Confirmed from code`: Playwright for web e2e (`ui-web/package.json`).
- `Confirmed from code`: Vitest / Testing Library unit tests in `ui-web`.

### DevOps / Containers / Infra

- `Confirmed from code`: Dockerfiles per service, Docker Compose, initialization SQL scripts.
- `Confirmed from code`: Mailpit for local email capture.
- `Not found in repository`: Kubernetes, ECS task definitions, Terraform state, CD pipeline definitions.
- `Confirmed from code`: auth-service currently pins `bcrypt==4.0.1` for compatibility with `passlib==1.7.4`; this is a deliberate runtime hygiene pin.

## 4. Project Structure

### Directory tree (up to 4 levels)

```text
.
├── README.md
├── docker-compose.yml
├── docs/
│   ├── auth_cutover_runbook.md
│   ├── aws_production_deployment.md
│   ├── preprod_validation.md
│   └── validation/
├── init-scripts/
│   └── mysql/
│       ├── 01_init.sql
│       ├── 02_data_service_dlq.sql
│       └── 03_copilot_reader.sql
├── monitoring/
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   ├── grafana/
│   │   └── dashboards/
│   └── prometheus/
│       ├── prometheus.yml
│       └── rules/
├── services/
│   ├── analytics-service/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── config/
│   │   │   ├── services/
│   │   │   ├── workers/
│   │   │   └── ...
│   │   └── tests/
│   ├── auth-service/
│   │   ├── app/
│   │   │   ├── api/v1/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   └── ...
│   │   └── tests/
│   ├── copilot-service/
│   │   ├── src/
│   │   │   ├── ai/
│   │   │   ├── api/
│   │   │   ├── db/
│   │   │   ├── integrations/
│   │   │   └── ...
│   │   └── tests/
│   ├── data-export-service/
│   │   ├── main.py
│   │   ├── worker.py
│   │   ├── exporter.py
│   │   ├── data_source.py
│   │   └── ...
│   ├── data-service/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── config/
│   │   │   ├── services/
│   │   │   ├── workers/
│   │   │   └── ...
│   │   └── tests/
│   ├── device-service/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   └── ...
│   │   └── tests/
│   ├── energy-service/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   └── ...
│   │   └── tests/
│   ├── reporting-service/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── workers/
│   │   │   └── ...
│   │   └── tests/
│   ├── rule-engine-service/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── services/
│   │   │   ├── workers/
│   │   │   └── ...
│   │   └── tests/
│   ├── shared/
│   └── waste-analysis-service/
│       ├── src/
│       │   ├── handlers/
│       │   ├── services/
│       │   ├── tasks/
│       │   └── ...
│       └── tests/
├── tests/
│   ├── e2e/
│   ├── integration/
│   └── regression/
├── tools/
│   └── device-simulator/
├── ui-web/
│   ├── app/
│   │   ├── (protected)/
│   │   ├── login/
│   │   ├── forgot-password/
│   │   └── ...
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── tests/
└── shivex-mobile/
    ├── app/
    ├── src/
    │   ├── api/
    │   ├── store/
    │   └── ...
    └── components/
```

### Top-level folders

- `services/`: all backend services plus shared backend package.
- `ui-web/`: Next.js web frontend.
- `shivex-mobile/`: Expo mobile frontend.
- `tests/`: cross-service higher-level tests.
- `monitoring/`: Prometheus, Grafana, Alertmanager config.
- `init-scripts/`: DB/bootstrap SQL.
- `docs/`: deployment/auth validation docs.
- `tools/device-simulator/`: telemetry simulator tooling.

## 5. Module Map

### Auth and Tenant Administration

- Folder: `services/auth-service/app`
- Responsibility:
  - `Confirmed from code`: login, refresh, logout, `/me`, invite acceptance, password reset, super-admin bootstrap, tenant/org/plant/user administration, explicit invite/reactivate/deactivate lifecycle handling, auth token cleanup, feature entitlements.
- Key files:
  - `services/auth-service/app/main.py`
  - `services/auth-service/app/api/v1/auth.py`
  - `services/auth-service/app/api/v1/admin.py`
  - `services/auth-service/app/api/v1/orgs.py`
  - `services/auth-service/app/services/auth_service.py`
  - `services/auth-service/app/services/action_token_service.py`
  - `services/auth-service/app/services/token_cleanup_service.py`
  - `services/auth-service/app/services/token_service.py`
  - `services/auth-service/app/config.py`
- Dependencies:
  - MySQL, Redis, SMTP/Mailpit, shared tenant/auth helpers.
- Critical contracts:
  - access token claims include `sub`, `email`, `tenant_id`, `role`, `plant_ids`, `permissions_version`, `tenant_entitlements_version`, `jti` (`token_service.py:64-88`).
  - refresh cookie name/path/domain behavior in `auth.py` + `config.py`.
  - user lifecycle now distinguishes `invited`, `invite_expired`, `active`, and `deactivated` through API/UI fields layered on top of `is_active`, `invited_at`, `activated_at`, and `deactivated_at`.
  - `last_login_at` is intended to move only on successful interactive login, not on invite acceptance, password reset, or refresh.
  - auth cleanup loop now purges stale `refresh_tokens` and stale `auth_action_tokens`.
  - organization lifecycle now uses `organizations.is_active` as an `Active` / `Suspended` state, and plant lifecycle uses `plants.is_active` as an `Active` / `Inactive` state.
  - plant deletion is intentionally not exposed as a destructive workflow; instead there is a device-count guard path to prevent orphaned devices.
  - exact endpoint map: [memory-appendix-api.md#auth-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#auth-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Shared Tenant/Auth Infrastructure

- Folder: `services/shared`
- Responsibility:
  - `Confirmed from code`: middleware, tenant context derivation, feature entitlement resolution, tenant-scoped repositories, telemetry normalization.
- Key files:
  - `services/shared/auth_middleware.py`
  - `services/shared/tenant_context.py`
  - `services/shared/tenant_guards.py`
  - `services/shared/scoped_repository.py`
  - `services/shared/feature_entitlements.py`
  - `services/shared/telemetry_normalization.py`
  - `services/shared/energy_accounting.py`
- Critical contracts:
  - internal header names `X-Internal-Service`, `X-Tenant-Id`, `X-Target-Tenant-Id` (`tenant_context.py:11-13`).
  - role baseline features and grantable premium features (`feature_entitlements.py:12-49`).
  - shared auth contract: [memory-appendix-api.md#shared-auth--tenant-contract](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - tenant-isolation data map: [memory-appendix-db.md#5-tenant-isolation-in-data-model](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Device Domain

- Folder: `services/device-service/app`
- Responsibility:
  - `Confirmed from code`: devices, heartbeat/property sync, dashboard summaries, health configs, live state, runtime/load/idle classification, fleet streaming.
- Key files:
  - `app/api/v1/router.py`
  - `app/services/live_projection.py`
  - `app/services/idle_running.py`
  - `app/services/health_config.py`
  - `app/config.py`
- Dependencies:
  - auth-service (middleware auth), data-service, energy-service, reporting-service, Redis, MySQL.
- Critical contracts:
  - machine states and canonical parameter aliases in `health_config.py`.
  - optimistic `version` updates for device live state in `live_projection.py:87-148`.
  - exact endpoint map: [memory-appendix-api.md#device-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#device-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Telemetry Ingest and Pipeline

- Folder: `services/data-service/src`
- Responsibility:
  - `Confirmed from code`: MQTT ingest, validation, Redis stream staging, Influx persistence, projection/broadcast/energy/rules fan-out, DLQ, outbox relay, WebSocket/data APIs.
- Key files:
  - `src/main.py`
  - `src/worker_main.py`
  - `src/services/telemetry_service.py`
  - `src/workers/telemetry_pipeline.py`
  - `src/services/outbox_relay.py`
  - `src/config/settings.py`
- Dependencies:
  - EMQX, Redis, InfluxDB, MySQL, device-service, energy-service, rule-engine-service.
- Critical contracts:
  - stage stream names/defaults in `settings.py`.
  - API prefix `/api/v1/data` in `settings.py`.
  - exact endpoint map: [memory-appendix-api.md#data-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#data-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Energy Domain

- Folder: `services/energy-service/app`
- Responsibility:
  - `Confirmed from code`: live energy updates, summary and calendar views, device lifecycle/range calculations, downstream energy broadcast.
- Key files:
  - `app/main.py`
  - `app/api/routes.py`
  - `app/config.py`
- Dependencies:
  - MySQL, Redis, device-service, reporting-service.
- Exact references:
  - API map: [memory-appendix-api.md#energy-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)

### Rules and Notifications

- Folder: `services/rule-engine-service/app`
- Responsibility:
  - `Confirmed from code`: rule evaluation against telemetry/live state, alert creation, notification outbox and delivery worker.
- Key files:
  - `app/services/evaluator.py`
  - `app/services/notification_outbox.py`
  - `app/workers/notification_worker.py`
  - `app/config.py`
- Dependencies:
  - MySQL, Redis, SMTP, optional Twilio.
- Critical contracts:
  - notification settings come from the shared physical `notification_channels` table owned by reporting-service and read by rule-engine through a mirror model.
  - exact endpoint map: [memory-appendix-api.md#rule-engine-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#rule-engine-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Analytics / ML Jobs

- Folder: `services/analytics-service/src`
- Responsibility:
  - `Confirmed from code`: analytics job queueing, worker execution, backlog fairness/caps, result formatting, optional weekly retraining.
- Key files:
  - `src/main.py`
  - `src/worker_main.py`
  - `src/workers/job_queue.py`
  - `src/services/scaling_policy.py`
  - `src/services/result_formatter.py`
  - `src/config/settings.py`
- Dependencies:
  - MySQL, Redis, data-export-service, data-service, device-service, object storage.
- Critical contracts:
  - tenant scoping partly lives in job `parameters->tenant_id` and request context rather than a dedicated DB column.
  - exact endpoint map: [memory-appendix-api.md#analytics-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#analytics-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Reporting

- Folder: `services/reporting-service/src`
- Responsibility:
  - `Confirmed from code`: queued report generation, metrics, MinIO storage, report history/download/result APIs, tariff-linked reporting settings.
- Key files:
  - `src/main.py`
  - `src/worker_main.py`
  - `src/services/report_engine.py`
  - `src/workers/report_worker.py`
  - `src/config.py`
- Dependencies:
  - MySQL, Redis, InfluxDB, MinIO, device-service, energy-service.
- Critical contracts:
  - report jobs, schedules, tariff rows, and notification channels are tightly linked.
  - exact endpoint map: [memory-appendix-api.md#reporting-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#reporting-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Waste Analysis

- Folder: `services/waste-analysis-service/src`
- Responsibility:
  - `Confirmed from code`: waste-analysis job creation/history/status/result/download, quality gates, per-device waste summaries, object output.
- Key files:
  - `src/main.py`
  - `src/handlers/waste_analysis.py`
  - `src/tasks/waste_task.py`
  - `src/config.py`
- Dependencies:
  - MySQL, InfluxDB, MinIO, device-service, reporting-service, energy-service.
- Exact references:
  - API map: [memory-appendix-api.md#waste-analysis-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - schema map: [memory-appendix-db.md#waste-analysis-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Data Export

- Folder: `services/data-export-service`
- Responsibility:
  - `Confirmed from code`: continuous and forced telemetry export to object storage with checkpointing (`main.py`, `config.py`).
- Key files:
  - `main.py`
  - `worker.py`
  - `exporter.py`
  - `data_source.py`
  - `checkpoint.py`
  - `s3_writer.py`
- Dependencies:
  - InfluxDB, MySQL checkpoint store, S3/MinIO, data-service.
- Critical contracts:
  - forced export endpoint `/api/v1/exports/run` validates date ranges and tenant-scoped devices (`main.py`).
  - API map: [memory-appendix-api.md#data-export-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)

### Copilot

- Folder: `services/copilot-service/src`
- Responsibility:
  - `Confirmed from code`: curated AI copilot, tenant-scoped SQL execution guard, tariff-aware answers.
- Key files:
  - `src/main.py`
  - `src/api/chat.py`
  - `src/db/query_engine.py`
  - `src/config.py`
- Dependencies:
  - readonly MySQL, AI provider APIs, data/reporting/energy services.
- Critical contracts:
  - SQL tenant filter injection based on schema manifest and `tenant_id` columns (`query_engine.py:29-112`).
  - exact endpoint map: [memory-appendix-api.md#copilot-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)

### Web Frontend

- Folder: `ui-web`
- Responsibility:
  - `Confirmed from code`: user-facing product UI, route protection, session handling, tenant selection, API proxying.
- Key files:
  - `ui-web/app/layout.tsx`
  - `ui-web/app/(protected)/layout.tsx`
  - `ui-web/lib/authContext.tsx`
  - `ui-web/lib/authApi.ts`
  - `ui-web/lib/authBootstrap.ts`
  - `ui-web/lib/apiFetch.ts`
  - `ui-web/lib/browserSession.ts`
  - `ui-web/lib/tenantStore.ts`
  - `ui-web/components/AuthGuard.tsx`
  - `ui-web/components/SuperAdminOrgGate.tsx`
  - `ui-web/next.config.ts`

### Mobile Frontend

- Folder: `shivex-mobile`
- Responsibility:
  - `Confirmed from code`: mobile access to auth, machines, alerts, reports, rules, waste, copilot.
- Key files:
  - `shivex-mobile/src/api/authApi.ts`
  - `shivex-mobile/src/store/useUserStore.ts`
  - Expo route folders under `shivex-mobile/app`.

## 6. Runtime Entry Points

### Service startup commands

- `Confirmed from code`:
  - `auth-service`: `uvicorn app.main:app --host 0.0.0.0 --port 8090` via `services/auth-service/start.sh`
  - `device-service`: `uvicorn app:app --host 0.0.0.0 --port 8000` via `services/device-service/start.sh`
  - `data-service`: `uvicorn src.main:app --host 0.0.0.0 --port 8081` via Dockerfile
  - `energy-service`: `uvicorn app.main:app --host 0.0.0.0 --port 8010` via `services/energy-service/start.sh`
  - `rule-engine-service` API: `uvicorn app:app --host 0.0.0.0 --port 8002`
  - `analytics-service` API: `uvicorn src.main:app --host 0.0.0.0 --port 8003`
  - `reporting-service` API: `uvicorn src.main:app --host 0.0.0.0 --port 8085`
  - `waste-analysis-service`: `uvicorn src.main:app --host 0.0.0.0 --port 8087`
  - `data-export-service`: FastAPI app in `main.py` on port `8080`
  - `copilot-service`: `uvicorn main:app --host 0.0.0.0 --port 8007`

### Worker startup commands

- `Confirmed from code`:
  - `data-service` worker: `python -m src.worker_main`
  - `rule-engine-service` worker: `python -m app.worker_main`
  - `analytics-service` worker: `python -m src.worker_main`
  - `reporting-service` worker: `python -m src.worker_main`
  - `data-export-service`: worker lifecycle starts inside API app lifespan (`main.py`)

### Docker Compose services, ports, and internal names

- `Confirmed from code` (`docker-compose.yml`):
  - `ui-web`: `3000`
  - `device-service`: `8000`
  - `data-service`: `8081`
  - `rule-engine-service`: `8002`
  - `analytics-service`: `8003`
  - `copilot-service`: `8007`
  - `data-export-service`: `8080`
  - `reporting-service`: `8085`
  - `waste-analysis-service`: `8087`
  - `energy-service`: `8010`
  - `auth-service`: `8090`
  - `mysql`: `3306`
  - `redis`: `6379`
  - `influxdb`: `8086`
  - `emqx`: `1883` plus management/UI ports
  - `minio`: `9000`, console `9001`
  - `mailpit`: SMTP `1025`, UI `8025`
  - `prometheus`: `9090`
  - `alertmanager`: `9093`
  - `grafana`: `3001`

### Healthchecks

- `Confirmed from code`: most services expose `/health`.
- `Confirmed from code`: many services expose `/ready`.
- `Confirmed from code`: several services expose `/metrics`.
- `Confirmed from code`: auth middleware skips auth for `/health`, `/ready`, `/metrics`, docs, OpenAPI, login and refresh (`services/shared/auth_middleware.py:42-55`).

### Main background workers

- `Confirmed from code`:
  - telemetry stage workers and maintenance loops (`data-service`)
  - rule notification worker
  - analytics job worker(s)
  - reporting worker
  - export worker
  - auth token cleanup service (refresh tokens plus stale action tokens)
  - analytics weekly retrainer

## 7. Core Data Flows

- Endpoint-level detail for these flows lives in [memory-appendix-api.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md); table/model detail lives in [memory-appendix-db.md](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md).

### Login / auth / session

- Trigger:
  - web/mobile login form posts credentials to auth-service.
- Services touched:
  - `auth-service`, Redis, MySQL, then frontend session helpers.
- Persistence points:
  - MySQL `users`, `refresh_tokens`.
  - Redis issued token index / revoked token keys.
- Async boundaries:
  - none required for basic login; auth-service startup also runs cleanup loop.
- Output/result:
  - `Confirmed from code`: access token returned in response body; refresh token returned in cookie for browser and in body for mobile usage path.
  - `Confirmed from code`: successful interactive login updates `users.last_login_at`; failed login, invite acceptance, password reset, and refresh do not.
- Critical rules:
  - pending invite blocks login with `PASSWORD_SETUP_REQUIRED` (`auth_service.py:203-221`).
  - disabled account blocks login (`auth_service.py:223-228`).
  - org suspension blocks login (`auth_service.py:186-197`).
  - browser auth is cookie-first for refresh/logout; the web app keeps access token in memory only and does not persist refresh tokens in browser JS storage.
  - web cold-start bootstrap is refresh-first when there is no valid in-memory access token; `authContext` now initializes through `ui-web/lib/authBootstrap.ts` so reloads attempt `/refresh` before `/me`, avoiding guaranteed startup `/me` 401s after browser refreshes.
  - access tokens carry `permissions_version` and `tenant_entitlements_version`; mismatch invalidates token (`token_service.py:64-88`, `auth_service.py:307-339`, `services/shared/auth_middleware.py:123-170`).
  - web refresh token cookie is HttpOnly, path-scoped to `/backend/auth/api/v1/auth` (`auth-service/app/config.py:40-44`, `auth.py` cookie setter).
  - terminal refresh-token failures (`INVALID_REFRESH_TOKEN`, `REFRESH_TOKEN_REVOKED`, `REFRESH_TOKEN_EXPIRED`) now clear the browser refresh cookie in `auth-service/app/api/v1/auth.py`; non-terminal refresh failures do not eagerly destroy session state.
  - web frontend keeps access token only in memory (`ui-web/lib/browserSession.ts`).
  - mobile stores access and refresh tokens in SecureStore (`shivex-mobile/src/api/authApi.ts`).
  - exact endpoint map: [memory-appendix-api.md#auth-and-session-endpoints](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact schema map: [memory-appendix-db.md#auth-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Invite user flow

- Trigger:
  - org/super admin or plant manager creates a user without password.
- Services touched:
  - `auth-service`, SMTP/Mailpit.
- Persistence points:
  - new `users` row, optional plant access rows, action token rows.
- Async boundaries:
  - email delivery call; not queued through separate worker in current auth service code.
- Output/result:
  - invitation email with frontend `/accept-invite?token=...` link.
- Critical rules:
  - plant managers can only create `operator` or `viewer` (`orgs.py:125-133`).
  - org admins cannot create `org_admin` or `super_admin` (`orgs.py:135-151`).
  - plant-scoped roles must have plant IDs; plant managers must assign exactly one plant (`orgs.py:176-204`).
  - invite acceptance hashes password, activates user, revokes prior tokens (`auth_service.py:86-111`).
  - expired never-activated invites do not permanently poison an email address; the same logical user row is reused for reinvite/resend instead of creating a duplicate account.
  - previously activated but later deactivated users must use `reactivate`, not reinvite.

### Organization suspension lifecycle

- Trigger:
  - super admin suspends or reactivates an organization/tenant.
- Services touched:
  - `auth-service`, then any tenant-authenticated service on subsequent requests.
- Persistence points:
  - `organizations.is_active`.
- Async boundaries:
  - none required; enforcement happens on subsequent login/refresh/write requests.
- Output/result:
  - suspended org cannot log in, refresh, invite users, or create new plants/users.
- Critical rules:
  - super-admin visibility into suspended orgs remains intact.
  - suspended orgs fail closed on login/refresh with `ORG_SUSPENDED`.
  - old tenant tokens become unusable for protected writes because auth freshness checks re-read tenant state.

### Plant inactive lifecycle

- Trigger:
  - tenant/org admin deactivates or reactivates a plant.
- Services touched:
  - `auth-service` for plant admin actions and user assignment checks; `device-service` for onboarding checks; web admin/org pages.
- Persistence points:
  - `plants.is_active`.
- Async boundaries:
  - none required.
- Output/result:
  - inactive plant remains readable for history/admin visibility, but cannot be used for new user-plant assignments or new device onboarding.
- Critical rules:
  - inactive plants are filtered out of active assignment/onboarding dropdowns in the web app.
  - inactive plants cause create/update flows to fail with `PLANT_INACTIVE`.
  - plant delete itself is still intentionally unavailable; delete behavior is represented by a guard check only.

### Telemetry ingest

- Trigger:
  - MQTT message on configured topic (default `devices/+/telemetry`; tenant-prefixed use is documented in README and simulator tooling).
- Services touched:
  - EMQX -> `data-service` API role -> Redis Streams -> InfluxDB -> device-service / energy-service / rule-engine-service.
- Persistence points:
  - Redis stage streams, InfluxDB telemetry bucket, MySQL outbox / DLQ rows.
- Async boundaries:
  - raw message publish to ingest stream.
  - worker stages: ingest -> projection -> broadcast -> energy -> rules.
- Output/result:
  - persisted time-series, updated device live state, downstream energy projection, rule evaluation, live broadcasts.
- Critical rules:
  - invalid messages are dead-lettered (`telemetry_service.py`, `README.md`).
  - backpressure thresholds can reject new ingest (`data-service/src/config/settings.py`).
  - projection batching groups by tenant before sync to device-service.
  - projection failures can defer/retry or continue downstream with projection error context depending on failure type.
  - exact API map: [memory-appendix-api.md#data-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md), [memory-appendix-api.md#5-realtime--polling-interfaces](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact DB map: [memory-appendix-db.md#data-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#device-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Dashboard live state

- Trigger:
  - downstream projection from telemetry pipeline and/or energy live update endpoints.
- Services touched:
  - `data-service` -> `device-service`, optionally `energy-service`, frontend protected pages.
- Persistence points:
  - `device_live_state` and related dashboard materialized data in MySQL.
  - Redis fleet/energy channels.
- Async boundaries:
  - telemetry projection stage and Redis broadcast.
- Output/result:
  - machine/fleet dashboard shows current runtime, load, health, and cost/energy state.
- Critical rules:
  - `device_live_state` is updated with optimistic locking on `version` (`live_projection.py:87-148`).
  - shift windows support overnight spans (`live_projection.py:223-242`).
  - runtime status and load state are separate concepts (`device-service/README.md`).
  - exact API map: [memory-appendix-api.md#device-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md), [memory-appendix-api.md#5-realtime--polling-interfaces](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact DB map: [memory-appendix-db.md#device_live_state](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#device_state_intervals](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Analytics job lifecycle

- Trigger:
  - analytics API job submission from UI/mobile.
- Services touched:
  - `analytics-service` API -> Redis stream or in-memory queue -> analytics worker -> MySQL/object storage/related downstreams.
- Persistence points:
  - job rows/state in MySQL, queue stream in Redis, optionally dataset access from object storage.
- Async boundaries:
  - durable queue claim/ack/retry via Redis stream.
- Output/result:
  - analytics job result persisted and returned through analytics APIs.
- Critical rules:
  - global queue backlog reject threshold -> `503` (`scaling_policy.py`, settings).
  - tenant queued/active caps -> `429`.
  - stale queued/running jobs are failed on service restart (`analytics-service/src/main.py`).
  - API role avoids importing heavyweight ML libs (`analytics-service/src/main.py`).
  - exact API map: [memory-appendix-api.md#analytics-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact DB map: [memory-appendix-db.md#analytics_jobs](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#ml_model_artifacts](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Report generation

- Trigger:
  - report request from web/mobile.
- Services touched:
  - `reporting-service` API -> Redis report queue -> reporting worker -> InfluxDB / device/energy data -> MinIO.
- Persistence points:
  - MySQL report job rows, Redis queue stream, object storage output.
- Async boundaries:
  - report queue and worker claim/timeout/retry cycle.
- Output/result:
  - report history/status/result/download URLs and stored artifact.
- Critical rules:
  - retries up to `REPORT_JOB_MAX_RETRIES` then dead-letter (`report_worker.py`, `src/config.py`).
  - report engine normalizes telemetry through shared normalization (`report_engine.py:8-10`, `58-91`).
  - `Needs runtime verification`: full precedence logic between direct energy counter vs normalized power integration because README describes a multi-step fallback order, while the scanned code path clearly computes from normalized business power.
  - exact API map: [memory-appendix-api.md#reporting-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact DB map: [memory-appendix-db.md#energy_reports](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#scheduled_reports](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Notification / alert delivery

- Trigger:
  - rule evaluates to triggered condition.
- Services touched:
  - `rule-engine-service`, SMTP, optional Twilio.
- Persistence points:
  - alert rows, notification outbox rows, delivery audit ledger, Redis stream.
- Async boundaries:
  - notification outbox queue and worker.
- Output/result:
  - queued, delivered, skipped, retried, or dead-lettered notifications.
- Critical rules:
  - alert storm protection skips evaluation if >50 alerts/device in 60s (`evaluator.py`).
  - if no recipients, outbox is marked skipped with `NO_ACTIVE_RECIPIENTS`.
  - exponential backoff and max retry logic in notification worker.
  - exact API map: [memory-appendix-api.md#rule-engine-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - exact DB map: [memory-appendix-db.md#notification_delivery_logs](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#notification_outbox](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Tenant switching

- Trigger:
  - super admin selects tenant in web UI or sends target tenant header.
- Services touched:
  - frontend auth context/store, auth-service `/me`, all tenant-scoped backend services through shared middleware.
- Persistence points:
  - selected tenant in web `sessionStorage` (`factoryops_selected_tenant`).
- Async boundaries:
  - none required.
- Output/result:
  - super admin can browse tenant-scoped pages as chosen org.
- Critical rules:
  - super admins may omit tenant claim and resolve tenant from `X-Target-Tenant-Id` or query param (`auth_middleware.py:179-214`).
  - non-super-admins must stay within token tenant scope.
  - web gate `SuperAdminOrgGate` blocks tenant-scoped pages until a tenant is selected.

### Export flow

- Trigger:
  - continuous export loop or manual `/api/v1/exports/run`.
- Services touched:
  - `data-export-service`, InfluxDB, MySQL checkpoint store, S3/MinIO.
- Persistence points:
  - export checkpoints table, object storage datasets.
- Async boundaries:
  - worker lifecycle inside service lifespan.
- Output/result:
  - Parquet/CSV datasets under object storage.
- Critical rules:
  - forced export validates paired `start_time` / `end_time` and maximum export window (`data-export-service/main.py`).
  - tenant/device scoping enforced before force export.

### Waste-analysis flow

- Trigger:
  - `/analysis/run` request.
- Services touched:
  - `waste-analysis-service`, device-service, InfluxDB, reporting-service, energy-service, MinIO.
- Persistence points:
  - MySQL waste job rows/history, MinIO report output.
- Async boundaries:
  - FastAPI background task with timeout wrapper.
- Output/result:
  - job history/status/result/download artifact URL.
- Critical rules:
  - active duplicate requests are deduped at job creation.
  - concurrency is bounded by configured value and CPU-based safety cap (`waste_task.py:40-44`).
  - quality gate can fail the job if `WASTE_STRICT_QUALITY_GATE` is enabled.
  - public warnings suppress internal/noise warnings before returning results (`waste_task.py:20-37`, `73-81`).

### Copilot flow

- Trigger:
  - `/api/v1/copilot/chat`.
- Services touched:
  - `copilot-service`, readonly MySQL, AI provider, tariff service client.
- Persistence points:
  - none obvious for conversation persistence in scanned code.
- Async boundaries:
  - AI provider call and SQL execution timeout boundary.
- Output/result:
  - natural-language answer, reasoning, error code if unavailable.
- Critical rules:
  - tenant required from request context (`chat.py:35-37`).
  - SQL is validated by `SQLGuard` and tenant filters are injected on tenant-scoped tables (`query_engine.py:29-112`).
  - query timeout and max rows enforced (`query_engine.py:113-137`, `src/config.py`).

## 8. Authentication and Authorization

- Detailed auth endpoint and DTO catalog: [memory-appendix-api.md#auth-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
- Detailed auth schema and tenant-isolation map: [memory-appendix-db.md#auth-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md), [memory-appendix-db.md#5-tenant-isolation-in-data-model](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

- Auth model:
  - `Confirmed from code`: JWT access token + DB-backed refresh token model.
  - `Confirmed from code`: tenant and plant lifecycle enforcement are layered on top of the auth/tenant model rather than using a separate lifecycle service.

- Token/session model:
  - `Confirmed from code`: access tokens are signed JWTs with revocation via Redis `token:revoked:{jti}` (`token_service.py:24-46`, `154-165`).
  - `Confirmed from code`: issued token JTIs are tracked per user in Redis for bulk revocation (`token_service.py:33-61`, `167-190`).
  - `Confirmed from code`: refresh tokens are opaque random strings; only SHA-256 hashes are stored in DB (`token_service.py:191-246`).

- Refresh flow:
  - `Confirmed from code`: refresh endpoint accepts body token or cookie token; web path expects cookie and enforces origin validation.
  - `Confirmed from code`: refresh rotation revokes old refresh token and issues a new one (`auth_service.py:276-305`).
  - `Confirmed from code`: refresh endpoint clears the browser refresh cookie on terminal 401 states (`INVALID_REFRESH_TOKEN`, `REFRESH_TOKEN_REVOKED`, `REFRESH_TOKEN_EXPIRED`) so dead-cookie startup loops terminate cleanly.
  - `Confirmed from code`: endpoint changes must preserve both cookie-based web refresh and body-token/mobile refresh.

- Cookie handling:
  - `Confirmed from code`: refresh cookie is HttpOnly, path-scoped, same-site configurable, secure only in production (`auth-service/app/config.py:40-62`).

- Browser storage behavior:
  - `Confirmed from code`: web keeps access token in memory only and stores `/me` plus selected tenant in `sessionStorage`.
  - `Confirmed from code`: web no longer stores refresh token in `sessionStorage` or `localStorage`.
  - `Confirmed from code`: web startup session restore is driven by `ui-web/lib/authBootstrap.ts`; if there is no valid in-memory access token, the bootstrap path attempts cookie refresh before fetching `/me`.
  - `Confirmed from code`: mobile stores access token, refresh token, and cached profile in Expo SecureStore.

- User lifecycle / audit semantics:
  - `Confirmed from code`: tenant user APIs expose `lifecycle_state` values `invited`, `invite_expired`, `active`, and `deactivated`, plus action flags `can_resend_invite`, `can_reactivate`, and `can_deactivate`.
  - `Confirmed from code`: `last_login_at` updates only on successful interactive login; invite acceptance and password reset do not fabricate login history.

- Roles found:
  - `Confirmed from code`: `super_admin`, `org_admin`, `plant_manager`, `operator`, `viewer`.

- Auth middleware:
  - `Confirmed from code`: `services/shared/auth_middleware.py` runs on services, validates Bearer tokens, refreshes tenant/entitlement freshness from DB, resolves tenant context, and attaches request state.
  - `Confirmed from code`: internal services can bypass Bearer auth using `X-Internal-Service` plus tenant headers (`auth_middleware.py:58-75`, `300-307`).

- Tenant isolation enforcement points:
  - `Confirmed from code`:
    - middleware tenant resolution
    - tenant guards (`assert_same_tenant`, `assert_plants_belong_to_tenant`)
    - tenant-scoped repositories
    - copilot SQL tenant injection
    - frontend super-admin gate
    - active-org and active-plant write guards in auth/device flows

- Super-admin / tenant switching:
  - `Confirmed from code`: super admins are treated as org-admin for entitlement display but can switch target tenant via header/query/UI selector.

## 9. Frontend Architecture

- Routing structure:
  - `Confirmed from code`: App Router in `ui-web/app`.
  - public routes: `/login`, `/forgot-password`, `/reset-password`, `/accept-invite`.
  - protected domains include `/admin`, `/analytics`, `/calendar`, `/copilot`, `/devices`, `/machines`, `/org/*`, `/tenant/*`, `/reports`, `/rules`, `/settings`, `/waste-analysis`, `/profile`.

- Protected vs public:
  - `Confirmed from code`: root layout wraps `AuthProvider`; protected layout uses `AuthGuard`.
  - `Confirmed from code`: `SuperAdminOrgGate` enforces tenant selection for super admins on tenant-scoped views.

- API calling pattern:
  - `Confirmed from code`: Next.js rewrites proxy `/backend/*` and `/api/reports/*`, `/api/waste/*` to internal service URLs (`ui-web/next.config.ts`).
  - `Confirmed from code`: `apiFetch` injects access token and tenant headers.

- Auth/session handling:
  - `Confirmed from code`: `authApi` handles login, refresh, `/me`, org selection flows.
  - `Confirmed from code`: no persistent access-token local storage on web.

- Reusable UI systems:
  - `Confirmed from code`: shared components under `ui-web/components`, Radix-based component patterns, React Query data layer.
  - `Needs runtime verification`: exact design-system completeness because only architecture files, not every component, were inspected.

- Live update / polling / stream patterns:
  - `Inferred from usage`: device/machine dashboard pages likely consume device/energy live APIs and/or WebSocket/polling helpers.
  - `Confirmed from code`: backend supports live-update and fleet streams; frontend route domains exist for dashboards.
  - Detailed interfaces: [memory-appendix-api.md#5-realtime--polling-interfaces](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)

- Major page domains:
  - `Confirmed from code`: auth, admin/tenants/orgs, devices/machines, analytics, reports, rules, settings, waste-analysis, copilot, calendar, profile.

## 10. Background Jobs and Workers

### Data-service telemetry pipeline

- Responsibility:
  - persist telemetry, project device state, fan out broadcast/energy/rules.
- Queue source:
  - Redis Streams.
- Retry behavior:
  - max attempts and DLQ settings in `data-service/src/config/settings.py`.
- Trigger type:
  - MQTT ingress and stage publish chain.
- Key files:
  - `src/workers/telemetry_pipeline.py`
  - `src/services/telemetry_service.py`
  - `src/services/outbox_relay.py`

### Data-service outbox relay / reconciliation

- Responsibility:
  - durable relay of downstream energy deliveries and drift repair.
- Queue source:
  - MySQL outbox rows + reconciliation scans.
- Retry behavior:
  - `outbox_max_retries`, circuit breaker thresholds, dead-letter retention.
- Trigger type:
  - polling loops on worker maintenance instance.

### Rule-engine notification worker

- Responsibility:
  - deliver queued notifications.
- Queue source:
  - Redis stream `rule-engine:notification-outbox` by default (`app/config.py`).
- Retry behavior:
  - exponential backoff, terminal dead-letter after `NOTIFICATION_OUTBOX_MAX_RETRIES`.
- Trigger type:
  - rule trigger outbox enqueue.

### Analytics job worker

- Responsibility:
  - claim and execute analytics jobs, heartbeat, stale recovery.
- Queue source:
  - Redis stream or in-memory queue.
- Retry behavior:
  - `queue_max_attempts`, dead-letter stream.
- Trigger type:
  - analytics API job submission.

### Analytics weekly retrainer

- Responsibility:
  - scheduled retraining (`Inferred from usage` based on `WeeklyRetrainer` startup path).
- Queue source:
  - internal scheduler, not an external queue.
- Retry behavior:
  - `Needs runtime verification`.

### Reporting worker

- Responsibility:
  - claim and generate reports.
- Queue source:
  - Redis stream `reporting:jobs`.
- Retry behavior:
  - retries until `REPORT_JOB_MAX_RETRIES`, then dead-letter.
- Trigger type:
  - report creation API.

### Data export worker

- Responsibility:
  - export telemetry windows to object storage, maintain checkpoints.
- Queue source:
  - internal continuous worker loop, plus forced export triggers.
- Retry behavior:
  - `Needs runtime verification` for exact backoff implementation unless inspecting `worker.py`.

### Auth refresh token cleanup service

- Responsibility:
  - background cleanup of expired/revoked refresh tokens plus stale invite/password-reset action tokens.
- Trigger type:
  - startup in auth-service lifespan.

### Org / plant lifecycle guard paths

- Responsibility:
  - enforce org suspension and plant inactivity for write paths, plus safe pre-delete checks for plants.
- Trigger type:
  - synchronous API calls from super-admin/admin/org UI and downstream auth/device checks.

## 11. Environment Variables and Configuration

### Shared / cross-service

- `JWT_SECRET_KEY`
  - purpose: sign and validate access tokens.
  - used by: auth-service, shared auth middleware.
  - required: effectively required.
  - sensitive: yes.
- `REDIS_URL`
  - purpose: token revocation, queueing, pub/sub, streams.
  - used by: auth-service, device-service, rule-engine-service, analytics-service, reporting-service, data-service, energy-service.
  - sensitive: no.
- `DATABASE_URL`
  - purpose: primary MySQL DSN for many services.
  - used by: auth-service, device-service, energy-service, rule-engine-service, reporting-service, waste-analysis-service.
  - sensitive: yes.
- `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`
  - purpose: telemetry time-series connection.
  - used by: data-service, reporting-service, waste-analysis-service, data-export-service.
  - sensitive: token yes.
- `MINIO_ENDPOINT`, `MINIO_EXTERNAL_URL`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
  - purpose: object storage.
  - used by: reporting-service, waste-analysis-service.
  - sensitive: access/secret yes.

### Auth-service (`services/auth-service/app/config.py`)

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `SERVICE_HOST`
- `SERVICE_PORT`
- `LOG_LEVEL`
- `ENVIRONMENT`
- `SQLALCHEMY_ECHO`
- `EMAIL_ENABLED`
- `EMAIL_SMTP_HOST` / aliases `SMTP_SERVER`, `AUTH_SMTP_SERVER`
- `EMAIL_SMTP_PORT` / aliases `SMTP_PORT`, `AUTH_SMTP_PORT`
- `EMAIL_SMTP_USERNAME` / aliases `SMTP_USERNAME`, `AUTH_SMTP_USERNAME`, `EMAIL_SENDER`
- `EMAIL_SMTP_PASSWORD` / aliases `EMAIL_PASSWORD`, `AUTH_EMAIL_PASSWORD`
- `EMAIL_FROM_ADDRESS` / aliases `EMAIL_FROM_ADDRESS`, `EMAIL_SENDER`, `EMAIL_SMTP_USERNAME`
- `PLATFORM_NAME`
- `FRONTEND_BASE_URL`
- `AUTH_ALLOWED_ORIGINS`
- `REFRESH_COOKIE_NAME`
- `REFRESH_COOKIE_DOMAIN`
- `REFRESH_COOKIE_PATH`
- `REFRESH_COOKIE_SAMESITE`
- `BOOTSTRAP_SUPER_ADMIN_EMAIL`
- `BOOTSTRAP_SUPER_ADMIN_PASSWORD`
- `BOOTSTRAP_SUPER_ADMIN_FULL_NAME`
- `INVITE_TOKEN_EXPIRE_MINUTES`
- `PASSWORD_RESET_EXPIRE_MINUTES`
- `ACTION_TOKEN_RETENTION_HOURS`
- `LOGIN_RATE_LIMIT`
- `PASSWORD_FORGOT_RATE_LIMIT`
- `INVITATION_ACCEPT_RATE_LIMIT`

### Device-service (`services/device-service/app/config.py`)

- `DATABASE_URL`
- `AUTH_SERVICE_URL` / `AUTH_SERVICE_BASE_URL`
- `DATA_SERVICE_BASE_URL`
- `RULE_ENGINE_SERVICE_BASE_URL`
- `REPORTING_SERVICE_BASE_URL`
- `ENERGY_SERVICE_BASE_URL`
- `ENERGY_SERVICE_TIMEOUT_SECONDS`
- `PROJECTION_BATCH_CHUNK_SIZE`
- performance/dashboard/snapshot settings:
  - `PERFORMANCE_TRENDS_*`
  - `DASHBOARD_*`
  - `STATE_INTERVAL_*`
  - `SNAPSHOT_STORAGE_BACKEND`
  - `SNAPSHOT_MINIO_BUCKET`
  - `SNAPSHOT_MINIO_ENDPOINT`
  - `SNAPSHOT_MINIO_ACCESS_KEY`
  - `SNAPSHOT_MINIO_SECRET_KEY`
  - `SNAPSHOT_MINIO_SECURE`
  - `MIGRATE_SNAPSHOTS_TO_MINIO`
- `REDIS_URL`
- `FLEET_STREAM_REDIS_CHANNEL_TEMPLATE`
- `BOOTSTRAP_DEMO_DEVICES`

### Data-service (`services/data-service/src/config/settings.py`)

- MQTT:
  - `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_TOPIC`, `MQTT_QOS`, `MQTT_RECONNECT_INTERVAL`, `MQTT_MAX_RECONNECT_ATTEMPTS`, `MQTT_KEEPALIVE`, `MQTT_CLEAN_SESSION`
- Redis / worker:
  - `REDIS_URL`, `APP_ROLE`, `TELEMETRY_WORKER_CONSUMER_NAME`, `TELEMETRY_WORKER_MAINTENANCE_ENABLED`, `TELEMETRY_WORKER_OUTBOX_RELAY_ENABLED`
  - all `telemetry_*stream*`, `telemetry_*threshold*`, `telemetry_*workers`, `telemetry_*batch_size`, heartbeat, reclaim, retry settings
- Influx:
  - `INFLUXDB_URL`, `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`, `INFLUXDB_TIMEOUT`
- Downstream:
  - `DEVICE_SERVICE_URL`, `ENERGY_SERVICE_URL`, `RULE_ENGINE_URL`
- MySQL helper vars:
  - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
- Outbox / reconciliation / DLQ:
  - `OUTBOX_*`, `RECONCILIATION_*`, `CIRCUIT_BREAKER_*`, `DLQ_*`
- Telemetry validation:
  - `TELEMETRY_MAX_VOLTAGE`, `TELEMETRY_MIN_VOLTAGE`, `TELEMETRY_MAX_CURRENT`, `TELEMETRY_MAX_POWER`, etc.
- WebSocket:
  - `WS_HEARTBEAT_INTERVAL`, `WS_MAX_CONNECTIONS`

### Energy-service (`services/energy-service/app/config.py`)

- `DATABASE_URL`
- `REDIS_URL`
- `ENERGY_STREAM_REDIS_CHANNEL`
- `REPORTING_SERVICE_BASE_URL`
- `DEVICE_SERVICE_BASE_URL`
- `PLATFORM_TIMEZONE`
- `TARIFF_CACHE_TTL_SECONDS`
- `MAX_FALLBACK_GAP_SECONDS`
- `LIVE_UPDATE_MAX_REORDER_SECONDS`
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`
- `CIRCUIT_BREAKER_OPEN_TIMEOUT_SEC`
- `CIRCUIT_BREAKER_SUCCESS_THRESHOLD`
- `ENERGY_BATCH_CHUNK_SIZE`

### Rule-engine-service (`services/rule-engine-service/app/config.py`)

- `DATABASE_URL`
- `EMAIL_SMTP_HOST`
- `EMAIL_SMTP_PORT`
- `EMAIL_SMTP_USERNAME`
- `EMAIL_SMTP_PASSWORD`
- `EMAIL_FROM_ADDRESS`
- `SMS_ENABLED`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_SMS_FROM_NUMBER`
- `WHATSAPP_ENABLED`
- `TWILIO_WHATSAPP_FROM_NUMBER`
- `DEVICE_SERVICE_URL`
- `REDIS_URL`
- `APP_ROLE`
- `QUEUE_BACKEND`
- queue settings for notification outbox streams/groups/consumer/retries/backoff/timeouts
- `NOTIFICATION_COOLDOWN_MINUTES`
- `MAX_RULES_PER_DEVICE`
- `PLATFORM_TIMEZONE`

### Analytics-service (`services/analytics-service/src/config/settings.py`)

- MySQL:
  - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
- Object storage:
  - `S3_BUCKET_NAME`, `S3_REGION`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
- Queue/scaling:
  - `MAX_CONCURRENT_JOBS`, `GLOBAL_ACTIVE_JOB_LIMIT`, `QUEUE_MAX_LENGTH`, `QUEUE_BACKLOG_REJECT_THRESHOLD`, `TENANT_MAX_QUEUED_JOBS`, `TENANT_MAX_ACTIVE_JOBS`
  - `QUEUE_BACKEND`, `REDIS_URL`, stream/group/consumer names, heartbeat TTL
- ML feature flags:
  - `ML_ANALYTICS_V2_ENABLED`, `ML_FORMATTED_RESULTS_ENABLED`, `ML_WEEKLY_RETRAINER_ENABLED`, `ML_FLEET_STRICT_ENABLED`, `ML_DATA_READINESS_GATE_ENABLED`, `ML_REQUIRE_EXACT_DATASET_RANGE`, `ML_MAX_DATASET_ROWS`
- Downstream:
  - `DATA_EXPORT_SERVICE_URL`, `DATA_SERVICE_URL`, `DEVICE_SERVICE_URL`

### Reporting-service (`services/reporting-service/src/config.py`)

- `DATABASE_URL`
- `INFLUXDB_URL`
- `INFLUXDB_TOKEN`
- `INFLUXDB_ORG`
- `INFLUXDB_BUCKET`
- measurement/field names such as `INFLUX_POWER_FIELD`, `INFLUX_VOLTAGE_FIELD`, `INFLUX_CURRENT_FIELD`
- `DEVICE_SERVICE_URL`
- `ENERGY_SERVICE_URL`
- MinIO vars listed above
- `PLATFORM_TIMEZONE`
- `DEMAND_WINDOW_MINUTES`
- `REPORT_JOB_TIMEOUT_SECONDS`
- `APP_ROLE`
- queue vars: `QUEUE_BACKEND`, `REDIS_URL`, `REPORT_QUEUE_*`, `REPORT_WORKER_CONCURRENCY`, retry and metrics cache settings

### Waste-analysis-service (`services/waste-analysis-service/src/config.py`)

- `DATABASE_URL`
- `INFLUXDB_URL`
- `INFLUXDB_TOKEN`
- `INFLUXDB_ORG`
- `INFLUXDB_BUCKET`
- `DEVICE_SERVICE_URL`
- `REPORTING_SERVICE_URL`
- `ENERGY_SERVICE_URL`
- MinIO vars listed above
- `MINIO_BUCKET`
- `PLATFORM_TIMEZONE`
- `TARIFF_CACHE_TTL_SECONDS`
- `WASTE_STRICT_QUALITY_GATE`
- `WASTE_JOB_TIMEOUT_SECONDS`
- `WASTE_DEVICE_CONCURRENCY`
- `WASTE_DB_BATCH_SIZE`
- `WASTE_PDF_MAX_DEVICES`

### Data-export-service (`services/data-export-service/config.py`)

- `influxdb_url`
- `influxdb_token`
- `influxdb_org`
- `influxdb_bucket`
- `data_service_url`
- `export_interval_seconds`
- `export_batch_size`
- `export_format`
- `s3_bucket`
- `s3_prefix`
- `s3_region`
- `s3_endpoint_url`
- `aws_access_key_id`
- `aws_secret_access_key`
- checkpoint DB vars:
  - `checkpoint_db_host`, `checkpoint_db_port`, `checkpoint_db_name`, `checkpoint_db_user`, `checkpoint_db_password`, `checkpoint_table`
- `lookback_hours`
- `max_export_window_hours`
- `max_force_export_window_hours`
- `device_ids`

### Copilot-service (`services/copilot-service/src/config.py`)

- `AI_PROVIDER`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `MYSQL_URL`
- `MYSQL_READONLY_URL`
- `DATA_SERVICE_URL`
- `REPORTING_SERVICE_URL`
- `ENERGY_SERVICE_URL`
- `FACTORY_TIMEZONE`
- `MAX_QUERY_ROWS`
- `QUERY_TIMEOUT_SEC`
- `MAX_HISTORY_TURNS`
- `STAGE1_MAX_TOKENS`
- `STAGE2_MAX_TOKENS`

### Frontend proxy/runtime configuration

- `Confirmed from code`: `ui-web/next.config.ts` expects backend service base URLs for rewrites. Exact env var names should be confirmed in that file before changing deployment configuration.
- `Needs runtime verification`: production hostnames and CDN/proxy layout.

## 12. External Integrations

- EMQX / MQTT
  - purpose: device telemetry ingress.
  - protocol: MQTT.
  - files: `data-service` settings and README, simulator tooling, `docker-compose.yml`.
  - auth: username/password optional in settings.

- MySQL
  - purpose: relational source of truth for auth, tenant, device, job, outbox, checkpoints.
  - protocol: SQLAlchemy/MySQL drivers.

- InfluxDB
  - purpose: telemetry time-series storage and reporting source.
  - protocol: Influx HTTP client.
  - files: data-service, reporting-service, waste-analysis-service, data-export-service configs.
  - auth: token.

- Redis
  - purpose: auth revocation, queues, pub/sub, stream heartbeats.
  - protocol: Redis client.

- MinIO / S3-compatible storage
  - purpose: report files, datasets, waste outputs, dashboard snapshot migration path.
  - protocol: S3 API / MinIO client.
  - auth: access key + secret.

- SMTP / Mailpit
  - purpose: invitation and password reset emails, alert emails.
  - protocol: SMTP.
  - files: auth-service mailer config, rule-engine notification adapters, `docker-compose.yml`.

- Twilio SMS / WhatsApp
  - purpose: notification delivery from rule-engine.
  - protocol: Twilio API/SDK path inferred from config and adapter naming.
  - auth: account SID + auth token.

- Groq
  - purpose: default AI provider for copilot.
  - protocol: API SDK/client.
  - files: `services/copilot-service/src/config.py`.

- Gemini
  - purpose: optional AI provider.
  - protocol: API.

- OpenAI
  - purpose: optional AI provider for copilot.
  - protocol: API.

- Prometheus / Grafana / Alertmanager
  - purpose: metrics scraping, dashboards, alert routing.
  - protocol: HTTP scraping/configured dashboards.

## 13. Business Logic Rules

- Feature entitlements:
  - `Confirmed from code`: baseline role features:
    - `org_admin`: `machines`, `calendar`, `rules`, `settings`
    - `plant_manager`: `machines`, `rules`, `settings`
    - `operator`: `machines`, `rules`
    - `viewer`: `machines`
  - `Confirmed from live validation`: rule notification channels are tenant-gated as:
    - `email`: always available
    - `sms`: requires `notification_sms`
    - `whatsapp`: requires `notification_whatsapp`
  - `Confirmed from code + live validation`: for SMS/WhatsApp rule recipients, the UI assumes India-first entry and the backend also normalizes a plain 10-digit mobile number to `+91...` so delivery-safe E.164 formatting does not depend only on the browser.
    (`services/shared/feature_entitlements.py:23-28`)
  - `Confirmed from code`: org grantable premium features are `analytics`, `reports`, `waste_analysis`, `copilot` (`feature_entitlements.py:30-35`).
  - `Confirmed from code`: plant managers can delegate only `analytics`, `reports`, `waste_analysis` (`feature_entitlements.py:37-41`).

- Telemetry normalization:
  - `Confirmed from code`: shared normalization version is `signed-power-v1` (`services/shared/telemetry_normalization.py:13`).
  - `Confirmed from code`: default energy flow mode is `consumption_only`; default fallback power factor is `0.85` (`telemetry_normalization.py:14-17`).

- Device health / runtime:
  - `Confirmed from code`: valid machine states include `RUNNING`, `OFF`, `IDLE`, `UNLOAD`, `POWER CUT`.
  - `Confirmed from code`: scoreable states are `RUNNING`, `IDLE`, `UNLOAD`.
  - `Confirmed from code`: standby states are `OFF`, `POWER CUT`.
  - `Confirmed from code`: duplicate health configs for the same canonical parameter are blocked.

- Alert/rule behavior:
  - `Confirmed from code`: max 100 rules per device by config default.
  - `Confirmed from code`: alert storm suppression after >50 alerts/device in 60 seconds.
  - `Confirmed from code`: notification cooldown defaults to 15 minutes.
  - `Confirmed from code`: time-window rules support overnight windows using platform timezone.

- Analytics fairness/caps:
  - `Confirmed from code`:
    - global active job limit `48`
    - queue backlog reject threshold `500`
    - tenant max queued `25`
    - tenant max active `8`
    - queue max attempts `3`
    (`analytics-service/src/config/settings.py`)

- Reporting:
  - `Confirmed from code`: reporting normalizes telemetry before computing energy/peak/load-factor values (`report_engine.py:58-91`, `188-227`).
  - `Confirmed from code`: load-factor band thresholds:
    - `<30`: `poor`
    - `30-70`: `moderate`
    - `>70`: `good`
    (`report_engine.py:165-172`)

- Waste-analysis:
  - `Confirmed from code`: public-facing warnings intentionally suppress internal markers and some no-op warnings (`waste_task.py:20-37`, `73-81`).
  - `Confirmed from code`: result includes off-hours, overconsumption, unoccupied-running, idle breakdowns.
  - `Confirmed from code`: per-device concurrency is capped to `min(configured, max(4, cpu*4))` (`waste_task.py:40-44`).
  - `Confirmed from code`: config default `WASTE_STRICT_QUALITY_GATE=False` (`waste-analysis-service/src/config.py:38`).
  - `Confirmed from docs`: waste README appears to describe stricter quality-gate behavior as default.
  - Repository discrepancy:
    - `Confirmed from code`: config default is false.
    - `Confirmed from docs`: README indicates strict mode behavior.
    - Treat this as a real configuration/documentation mismatch.

- Copilot:
  - `Confirmed from code`: SQL queries are tenant-filtered if referenced tables carry `tenant_id` in the schema manifest.
  - `Confirmed from code`: blocked/invalid SQL returns structured `QUERY_BLOCKED`, `QUERY_TIMEOUT`, or `QUERY_FAILED`.

- Tenant constraints:
  - `Confirmed from code`: non-super-admins cannot operate without tenant scope.
  - `Confirmed from code`: cross-tenant access may return 404 for obscurity and logs an audit record in `tenant_security_audit_log`.

## 14. Error Handling and Observability

- Error handling style:
  - `Confirmed from code`: FastAPI exception handlers return structured JSON payloads with `code`, `message`, and sometimes `details`.
  - `Confirmed from code`: services often convert internal errors to stable domain codes like `INVALID_TOKEN`, `EXPORT_TRIGGER_FAILED`, `AI_UNAVAILABLE`.

- Custom exception patterns:
  - `Confirmed from code`: auth and tenant helpers raise `HTTPException` with structured details.
  - `Confirmed from code`: frontend throws client-side `TenantNotSelectedError` for super-admin flows.

- Logging style:
  - `Confirmed from code`: Python `logging` used throughout; several services favor structured `extra={...}` payloads.
  - `Confirmed from code`: data-export-service sets up structured logging via `logging_config.py`.

- Health endpoints:
  - `Confirmed from code`: `/health`, `/ready`, `/metrics` are common across services.

- Metrics/monitoring:
- `Confirmed from code`: Prometheus stack is configured in `monitoring/prometheus/prometheus.yml`.
- `Confirmed from code`: device SLO rules exist in `monitoring/prometheus/rules/device-slo-alerts.yml`.
- `Confirmed from code`: Redis monitoring now includes a dedicated `redis-exporter` scrape target plus `RedisDown`, `RedisMemoryHigh`, and `RedisMemoryCritical` alerts in `monitoring/prometheus/rules/redis-alerts.yml`, which is important because Shivex runs Redis with `maxmemory` and `noeviction` so memory pressure must be surfaced before writes start failing.
  - `Confirmed from code`: Grafana dashboard JSON exists for device SLOs.

- Retry/dead-letter concepts:
  - `Confirmed from code`: data-service DLQ with durable MySQL backend by default.
  - `Confirmed from code`: analytics dead-letter stream.
  - `Confirmed from code`: reporting dead-letter stream.
  - `Confirmed from code`: rule notification outbox dead-letter stream.

## 15. Testing Structure

- Layout:
  - `Confirmed from code`: per-service `tests/` directories under backend services.
  - `Confirmed from code`: top-level `tests/e2e`, `tests/integration`, `tests/regression`.
  - `Confirmed from code`: `ui-web/tests/unit` and `ui-web/tests/e2e`.

- Naming conventions:
  - `Confirmed from code`: backend uses `test_*.py`.
  - `Confirmed from code`: top-level regression/e2e tests use numbered files like `test_19_energy_dashboard_regression.py`.

- Test types:
  - `Confirmed from code`: unit and integration coverage for auth, tenant scoping, energy/reporting/waste flows.
  - `Confirmed from code`: Playwright/browser tests in web app.
  - `Confirmed from code`: top-level `tests/e2e` is Python/pytest-based business/API/system validation, not Playwright.
  - `Confirmed from code`: `ui-web/tests/e2e` is the browser E2E suite driven by Playwright.
  - `Not found in repository`: obvious dedicated mobile test suite.

- Common test commands:
  - `Confirmed from code`: web package scripts include `test:unit` and `test:e2e`.
  - `Confirmed from local validation`: Playwright browser suite runs from `ui-web` and currently passes at `53 passed / 9 skipped`.
  - `Inferred from usage`: backend services use `pytest`.

## 16. Change Impact Map

### Auth / tenant / entitlements

- Files usually touched together:
  - auth routes, `auth_service.py`, `action_token_service.py`, `token_cleanup_service.py`, `token_service.py`, shared middleware, frontend auth context/api, mobile auth API.
- Regression risks:
  - web refresh cookie path/origin behavior
  - web cold-start bootstrap order (`refresh -> /me`) versus protected fetch recovery (`401 -> refresh -> retry once`)
  - token freshness invalidation
  - super-admin tenant switching
  - invite/reset flow links
  - incorrect `last_login_at` audit behavior
  - reinvite/reactivate lifecycle drift
  - cleanup logic deleting valid action tokens
  - org suspension not being enforced consistently across login, invite, and create-resource paths
  - inactive plants still appearing in assignment/onboarding flows
- Tests to run:
  - auth-service tests, top-level tenant scope/auth regression tests, web auth unit/e2e tests.
  - `ui-web/tests/unit/authBootstrap.test.ts`
  - `services/auth-service/tests/test_login_audit.py`
  - `services/auth-service/tests/test_token_cleanup_service.py`
  - `services/auth-service/tests/test_org_plant_lifecycle.py`
  - `services/auth-service/tests/test_auth_cookie_security.py`
  - `services/device-service/tests/test_plant_lifecycle_guards.py`
- Common pitfalls:
  - forgetting `permissions_version` or `tenant_entitlements_version`
  - breaking cookie-based refresh while mobile still uses body token
  - bypassing tenant guards in service-to-service paths
  - assuming invite acceptance counts as login for audit purposes when it should not
  - allowing plant deletion or reassignment flows to orphan devices
- Exact API/DB references:
  - [memory-appendix-api.md#auth-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-db.md#auth-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)
  - [memory-appendix-db.md#5-tenant-isolation-in-data-model](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Telemetry / live dashboard

- Files usually touched together:
  - data-service pipeline + device live projection + energy-service live update + frontend dashboard clients.
- Regression risks:
  - backlog thresholds
  - DLQ classification
  - duplicate/reordered telemetry behavior
  - optimistic lock conflicts in live state
- Tests to run:
  - data-service tests, energy/device regression tests, energy dashboard top-level regression.
- Common pitfalls:
  - changing telemetry field names without updating shared normalization
  - missing tenant headers on downstream calls
- Exact API/DB references:
  - [memory-appendix-api.md#data-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-api.md#device-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-db.md#data-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)
  - [memory-appendix-db.md#device-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Rules / alerts / notifications

- Files usually touched together:
  - evaluator, notification outbox, worker, frontend rules pages.
- Regression risks:
  - alert storms
  - cooldown logic
  - no-recipient behavior
  - dead-letter growth
- Tests to run:
  - rule-engine tests, notification-related integration tests.
- Exact API/DB references:
  - [memory-appendix-api.md#rule-engine-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-db.md#rule-engine-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Analytics

- Files usually touched together:
  - analytics API, queue worker, scaling policy, result formatter, frontend analytics pages.
- Regression risks:
  - queue fairness and tenant throttling
  - stale-job restart handling
  - ML import leakage into API role
- Tests to run:
  - analytics service tests, any end-to-end analytics regression coverage.
- Exact API/DB references:
  - [memory-appendix-api.md#analytics-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-db.md#analytics-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Reporting / exports / waste

- Files usually touched together:
  - reporting engine, report worker, data export, waste-analysis task/handlers, MinIO configs, frontend reports/waste pages.
- Regression risks:
  - telemetry normalization consistency
  - report artifact storage URLs
  - quality gate behavior
  - cross-service tenant-scoped HTTP calls
- Tests to run:
  - reporting, waste-analysis, export-related tests and top-level report/waste regressions.
- Common pitfalls:
  - README/config mismatches
  - assuming energy counter precedence not actually implemented in scanned code path
- Exact API/DB references:
  - [memory-appendix-api.md#reporting-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-api.md#waste-analysis-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-api.md#data-export-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)
  - [memory-appendix-db.md#reporting-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)
  - [memory-appendix-db.md#waste-analysis-service-schemas](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-db.md)

### Copilot

- Files usually touched together:
  - chat API, model client, SQL guard, schema loader, web/mobile copilot pages.
- Regression risks:
  - unsafe SQL allowance
  - missing tenant filter injection
  - provider fallback handling
- Tests to run:
  - copilot service tests plus tenant-scope/security regressions.
- Exact API/DB references:
  - [memory-appendix-api.md#copilot-service](/Users/vedanthshetty/Desktop/GIT-Testing/FactoryOPS-Cittagent-Obeya-main/memory-appendix-api.md)

## 2026-05-09 Disposable Mixed-Load Validation Truth Note

- Disposable-server HTTP load validation is now considered structurally valid after permanent harness corrections:
  - k6 runner env precedence fixed so inline env overrides beat `tests/load/k6/.env`
  - direct-mode service addressing added for backend-only validation
  - tenant-scoped org-admin credentials plus premium entitlements required for realistic domain coverage
- Important truth about early failures:
  - the initial `~68-70%` k6 failure rate was **not** a backend-scale verdict
  - root causes were:
    - load-test tenants created with empty `premium_feature_grants`
    - super-admin `/auth/me` context returning `tenant_id=null` / no effective tenant entitlements for discovery-driven scenarios
  - after granting `analytics`, `reports`, and `waste_analysis` to load-test tenants and switching k6 auth to tenant-scoped org-admin users, the mixed-load harness exercised real domain flows successfully
- Final validated disposable mixed-load result on the corrected harness:
  - baseline: `50` telemetry simulators across 3 tenants
  - HTTP pressure: k6 `mixed` scenario, direct mode, `4` VUs, `10m`
  - threshold outcome:
    - `http_req_failed = 1.22%` (`PASS`)
    - `p95 = 5674ms` (`FAIL`)
    - `p99 = 8313ms` (`FAIL`)
  - endpoint outcome:
    - core auth/discovery/rules CRUD paths passed cleanly
    - only a small minority of report-history / async-run checks failed
  - system outcome:
    - projection backlog rose from roughly `88` to roughly `4961`
    - projection workers saturated at `100` inflight each
    - outbox failure inventory remained a major background symptom even though retries were actively draining
- Operational conclusion:
  - current architecture on the tested single-node disposable topology is **functionally stable** at `50` telemetry simulators plus light mixed HTTP pressure
  - it is **not latency-SLA clean**
  - the first real scaling bottleneck remains the `data-service` projection stage, with outbox/downstream retry pressure as the next follow-on concern
  - do not claim `1000+` device readiness from this evidence
  - next work should prioritize projection/outbox optimization and a more production-like capacity topology rather than broader blind load escalation

## 17. Known Issues / Tech Debt

- Waste strict-quality gate documentation mismatch
  - file reference: `services/waste-analysis-service/src/config.py`, service README.
  - impact: operators may assume stricter default enforcement than the running config actually provides.

- Branding inconsistency across product names
  - file reference: root `README.md`, `services/auth-service/app/config.py`, `shivex-mobile/`, likely web metadata files.
  - impact: naming drift may cause confusion in prompts, emails, tenant-facing UI, and deployment configuration.

- Reporting energy precedence not fully self-evident from scanned implementation
  - file reference: `services/reporting-service/src/services/report_engine.py`, reporting README.
  - impact: future changes to energy calculations need careful verification against tests and expected contract.

- Default bootstrap super-admin credentials are hard-coded in config
  - file reference: `services/auth-service/app/config.py:45-47`
  - impact: acceptable for bootstrap/dev flow only; high operational sensitivity if not overridden outside local/dev.

## 18. Glossary

- tenant
  - `Confirmed from code`: organization-level isolation boundary, often synonymous with org in request routing and data ownership.

- org / organization
  - `Confirmed from code`: tenant record managed by auth-service; carries activation status and premium feature entitlements.

- plant
  - `Confirmed from code`: sub-scope within a tenant used for plant-manager/operator/viewer access control.

- telemetry
  - `Confirmed from code`: device sensor/time-series payload including energy and electrical metrics persisted to InfluxDB.

- FLA
  - `Inferred from usage`: full-load amps / full-load current. Appears in waste-analysis result fields such as `full_load_current_a`.

- load state
  - `Confirmed from code`: machine load classification persisted in device live state; distinct from runtime status.

- runtime status
  - `Confirmed from code`: running/stopped-style state separate from load classification in device-service.

- overconsumption
  - `Confirmed from code`: waste-analysis category comparing measured behavior against overconsumption thresholds/config.

- idle
  - `Confirmed from code`: machine state / waste category representing low-load but active behavior; used by rules and waste/reporting logic.

- fleet
  - `Confirmed from code`: multi-device dashboard/live stream view in device-service.

- outbox
  - `Confirmed from code`: durable table/stream-backed dispatch record used for energy delivery and notifications.

- DLQ
  - `Confirmed from code`: dead-letter queue/stream/table for failed telemetry, notification, analytics, or reporting items.

- curated questions
  - `Confirmed from code`: predefined copilot starter prompts returned by `/api/v1/copilot/curated-questions`.

- premium feature grants
  - `Confirmed from code`: organization-level enabled premium modules: `analytics`, `reports`, `waste_analysis`, `copilot`.

- role feature matrix
  - `Confirmed from code`: delegated feature enablement matrix applied to tenant roles beneath the org-level premium grants.
2026-05-10: Remaining POST run failures were traced to analytics-service queue-cap admission under duplicate submissions, not rules/copilot/projection. Local permanent fix added analytics duplicate-job reuse before admission-policy enforcement, plus analytics_jobs dedup lookup index and unit coverage.
2026-05-10: Disposable test-server validation confirmed the analytics dedup fix needed a second iteration. Exact datetime matching produced zero reuse events because k6 request timestamps varied at millisecond precision; dedup key was reduced to tenant_id + device_id + analysis_type + model_name + pending/running status. Final revalidation passed with http_req_failed=0.00%, checks_succeeded=100%, POST run at 100%, and 22 analytics_job_reused_duplicate events. Rules/reporting/projection paths remained clean; remaining latency tails stayed infrastructure-bound on the small EC2.
2026-05-11: Scaling-validation conclusion after the disposable test-server hardening cycle:
  - the core backend concurrency path is now materially stronger and should be treated as a permanent-fix direction rather than patchwork
  - validated improvements cover Redis tenant locking, projection write hardening, outbox retry/cache improvements, analytics dedup, and the corrected mixed-load harness
  - practical guidance from the validated work:
    - `100`-device-class rollout confidence is strong
    - `100-500` active devices should be treated mainly as infrastructure sizing / worker-topology work, not as the original backend-lock bottleneck problem
    - `500+` and especially `1000-1500` active devices still require production-like topology sizing and verification; do not overclaim that the small disposable EC2 directly proved those upper ranges
  - this guidance is an engineering inference from the validated backend-fix results, not a literal claim that `500` or `1000+` was fully simulated end-to-end on the disposable node
2026-05-11: Production rollout then proceeded through the normal GHCR image path:
  - PR merged to `main`
  - GHCR publish workflow produced first-party images tagged with `sha-05d6b28`
  - Shivex server deploy used `APP_IMAGE_TAG=sha-05d6b28` in `.env`, followed by:
    - `docker compose --env-file .env pull`
    - `docker compose --env-file .env up -d`
  - server verification after deploy showed first-party services and workers healthy on `sha-05d6b28`, including `data-service`, `device-service`, `auth-service`, `analytics-service`, `analytics-worker`, `analytics-worker-2`, `reporting-service`, `rule-engine-service`, `waste-analysis-service`, `copilot-service`, and `ui-web`
  - rollback model is image-tag based, not source-build based: change `APP_IMAGE_TAG` back to an older known-good `sha-*`, rerun `pull`, then `up -d`
2026-05-11: Final pre-merge local validation before production deploy included:
  - `ui-web` typecheck
  - `ui-web` production build
  - `ui-web` unit test suite
  - `shivex-mobile` TypeScript validation
  - targeted Playwright rerun for machine telemetry recovery behavior
  - one stale frontend unit test and one brittle telemetry E2E selector were corrected locally before the final green PR/merge so CI time was not wasted on already-known local issues
2026-05-11: Current Docker-topology scaling interpretation after direct compose inspection:
  - current all-in-one Docker setup already has a stronger worker baseline than it may appear at a glance:
    - telemetry/data path: `2` dedicated worker containers (`data-telemetry-worker`, `data-telemetry-worker-2`) plus internal stage parallelism (`8` persistence, `4` projection, `4` broadcast, `6` energy, `8` rules)
    - analytics path: `2` worker containers with `MAX_CONCURRENT_JOBS=3`
    - reporting path: `1` worker container with `REPORT_WORKER_CONCURRENCY=2`
    - waste-analysis path: `1` worker container with `WASTE_WORKER_CONCURRENCY=2`
    - rules/notification path: `1` worker container with `NOTIFICATION_WORKER_CONCURRENCY=4`
  - current compose also keeps Redis on the same Docker host with default `REDIS_MAXMEMORY=512mb`
  - operational recommendation for the present `8 GB` single-node Docker setup:
    - leave worker counts as-is for now
    - do **not** raise worker counts first on the current box just to prepare for `100-500`
    - for smoother upper-range `100-500` operation, prioritize infrastructure sizing first (server RAM/CPU/disk and Redis headroom) before increasing worker replicas
 - practical guidance:
   - current backend code path can remain as-is right now
   - next scaling move should be infrastructure-first
   - revisit worker-count increases only after the host/Redis capacity is strengthened
2026-05-16: Added root-level `SCALING_READINESS.md` as the Shivex-specific 1000+ readiness checklist:
  - grounded in current compose topology, service code, and prior scaling notes
  - keeps the current interpretation conservative: do not claim proven `1000+` readiness from existing evidence alone
  - records the current scaling order as infrastructure-first, with `data-service` projection as the first likely bottleneck and outbox/downstream pressure as the next follow-on concern
2026-05-16: Added root-level `SCALING_ROLLOUT_PLAN.md` as the operator-facing staged rollout guide for `100 -> 500 -> 1000+` devices:
  - translates the readiness conclusions into concrete stage-by-stage infra guidance
  - keeps the same core interpretation: scale telemetry/data path and Redis first, then downstream dependencies, then reporting/analytics worker capacity as measured
  - avoids throughput promises and uses current code-backed thresholds as watchpoints rather than guarantees
2026-05-16: Phase-1 privacy/data-handling baseline docs were added at the repo root:
  - `PRIVACY_POLICY.md`
  - `DATA_HANDLING.md`
 - purpose:
    - create a concrete product/privacy baseline before broader rollout
    - document current user/org/plant/device/telemetry/report/export/copilot data categories from actual code paths
    - capture storage/access/retention guidance in one operator-readable place
  - operational note:
    - these docs are implementation-grounded baseline references, not final legal sign-off artifacts
    - treat them as the starting point for privacy/security hardening phases, not the end of the review
2026-05-16: Phase-3 runtime compression validation and safe enablement were completed locally against the Dockerized stack:
  - verified by runtime headers:
    - `ui-web` HTML responses on `:3000` already return `Content-Encoding: gzip`
    - non-streaming API JSON responses on `auth-service :8090`, `device-service :8000`, `energy-service :8010`, `reporting-service :8085`, and `analytics-service :8003` now return `Content-Encoding: gzip`
    - device fleet SSE on `device-service /api/v1/devices/dashboard/fleet-stream` remains intentionally uncompressed with `content-type: text/event-stream` and no `content-encoding`
  - permanent-fix decision:
    - keep `ui-web` unchanged because compression is already active at runtime there
    - add explicit API-layer compression only in backend services, using a shared middleware that compresses compressible non-streaming responses and bypasses SSE / already-encoded responses
    - avoid Starlette `GZipMiddleware` directly because its default behavior can compress streaming responses, which is not acceptable for live SSE behavior here
  - implementation note:
    - shared helper added at `services/shared/http_compression.py`
    - wired into `auth-service`, `device-service`, `energy-service`, `reporting-service`, and `analytics-service`
    - reporting-service needed an extra correction because it creates two `FastAPI` app objects and compression had to be attached to the second, real runtime app
2026-05-17: Phase-4 route-by-route cache classification was completed locally for `device-service` plus `ui-web` device/hardware fetch clients, and the validated conclusion was intentionally conservative:
  - `must stay fully live / no-store`:
    - dashboard summary, fleet snapshot, fleet SSE stream, device detail snapshot, dashboard bootstrap summary, dashboard bootstrap, today loss breakdown, and monthly energy calendar
    - reason: these are projection/live-dashboard or live-loss views whose value is tied to current telemetry truth and freshness warnings
  - `snapshot-backed but freshness-sensitive`:
    - per-device current state, loss stats, idle stats, and performance trends
    - reason: these are not SSE, but they derive from recent telemetry / projection state and would be easy to make misleading with even short client-side cache reuse
  - `safe for short private caching` in data-shape terms but **not safe to change yet in the current UX contract**:
    - maintenance log list + summary
    - shifts
    - uptime
    - health-config list / validation helpers
    - dashboard widget config
    - hardware inventory, hardware mappings, and hardware installation history/current views
    - idle / waste config reads
    - reason: these are configuration/history/admin reads, but the current UI explicitly reloads them immediately after local create/update/delete flows, so adding browser-visible short caching now would weaken read-after-write truthfulness
  - `unsafe to change without wider design review`:
    - any route used by polling/refresh loops or CRUD reconciliation without explicit cache-busting or invalidation semantics
    - especially machine detail maintenance/config flows and org hardware admin flows
  - implementation outcome:
    - no selective cache-header or fetch-cache changes were made in Phase 4
    - the current code needs a wider invalidation strategy or explicit cache-busting conventions before these config/history routes can safely move away from the present conservative posture
2026-05-17: Phase-5 production runtime posture hardening was completed locally as an env-driven concurrency control change, without changing local/dev defaults:
  - validated runtime finding:
    - `device-service`, `auth-service`, `energy-service`, `analytics-service`, `reporting-service`, and `waste-analysis-service` API entrypoints were all starting with single-process `uvicorn`
    - `analytics-service`, `reporting-service`, and `waste-analysis-service` already preserve API-vs-worker role separation through `APP_ROLE`, and that split must stay intact
  - permanent-fix decision:
    - add `UVICORN_WORKERS` support in each API start script, defaulting to `1`
    - wire production-facing env knobs through `docker-compose.yml` only, while leaving `docker-compose.local.yml` unchanged so local/dev behavior stays simple and unchanged by default
    - treat the actual worker count as an operator sizing decision rather than a code default
  - safety guard:
    - multi-worker API startup is explicitly blocked when `DEBUGPY_ENABLE=true`, because the current debug bootstrap binds a single fixed port and is not safe to fan out across multiple workers
  - operator-facing env knobs:
    - `DEVICE_SERVICE_UVICORN_WORKERS`
    - `AUTH_SERVICE_UVICORN_WORKERS`
    - `ENERGY_SERVICE_UVICORN_WORKERS`
    - `ANALYTICS_API_UVICORN_WORKERS`
    - `REPORTING_SERVICE_UVICORN_WORKERS`
    - `WASTE_ANALYSIS_SERVICE_UVICORN_WORKERS`
  - local validation:
    - shell syntax checks passed for all updated start scripts
    - `docker compose config` remained valid with `.env.local`
    - targeted service rebuild/recreate succeeded locally
    - all six API containers came back healthy with the unchanged default of one worker per service
2026-05-17: Added `memory.md/performance-hardening-status.md` as the plain-English project summary of the completed performance hardening track:
  - explains what is already done
  - separates remaining ops/infra work from real remaining code work
  - records worker sizing guidance / deployment verification as the next recommended step rather than more immediate app rewrites
2026-05-17: Redis sizing decision for the current all-in-one 8 GB production server shape:
  - verified running Redis config was `maxmemory=512mb` and `maxmemory-policy=noeviction`
  - verified current Redis usage is low right now, so the immediate risk is future headroom rather than present exhaustion
  - keep `noeviction` because silent eviction would be more dangerous than honest write rejection for telemetry/auth/queue correctness
  - raise the shared production Redis ceiling from `512mb` to `1gb` as the safer immediate default on this 8 GB host, instead of jumping straight to `2gb`
  - if Redis later grows materially toward `1gb`, the next move should be more host headroom or a less-crowded Redis placement, not a policy switch away from `noeviction`
2026-05-17: Environment-file rule to preserve going forward:
  - `.env` is the real production/server runtime env file in this repo/deploy flow
  - `.env.local` is local-only
  - `docker-compose.local.yml` is local-only
  - do not treat `.env.production.example` as the live production source of truth when making real rollout config decisions
