# Machine Health Intelligence Plan

Temporary planning note for the Shivex machine fault score and anomaly activity work.

This is a design memory file only. It is not implementation code, not a production patch, and can be deleted after the feature is fully specified or moved into permanent docs.

## Product Direction

Build an explainable, lightweight, production-safe machine health layer that can replace the heavy ML analytics flow for day-to-day operations.

Primary positioning:

- Explainable Failure Risk Engine
- Machine Degradation Score
- Anomaly Activity

Do not position the first version as exact failure-date prediction. Position it as a condition-based risk indicator using telemetry evidence.

## Core Principle

Dashboard pages must never calculate health intelligence live from raw telemetry.

Use this flow:

```text
Raw telemetry -> feature windows -> score snapshots -> dashboard reads snapshots
```

The dashboard should read precomputed latest rows and stay fast even with 100 organizations and 1500+ devices.

## Scale Target

Initial enterprise target:

- 100 organizations
- approximately 15 devices per organization
- approximately 1500 devices total
- many concurrent dashboard users

The design must support this without blocking machine pages, reports, waste analysis, calendar, or telemetry ingestion.

## Standard Telemetry Contract

Preferred device telemetry fields:

- timestamp
- device_id
- current_avg
- current_l1
- current_l2
- current_l3
- power
- power_factor
- voltage_avg
- voltage_l1
- voltage_l2
- voltage_l3
- voltage_line
- frequency
- energy_kwh
- machine_status or running_state if available

The system can work with partial fields, but confidence must decrease when important signals are missing.

## Shared Foundation

Both Phase 1 and Phase 2 should use the same foundation.

Foundation responsibilities:

- classify running windows
- aggregate telemetry into compact windows
- learn per-machine baselines
- measure baseline quality
- track telemetry coverage and gaps
- detect startup/shutdown/load-change windows
- learn per-machine phase profile
- provide explainable features for downstream scoring

Avoid duplicate calculation paths between degradation and anomaly features.

## Running Window Classifier

Before scoring, classify each window:

- OFF
- STARTUP
- STEADY_RUNNING
- LOAD_CHANGE
- SHUTDOWN
- UNKNOWN

Degradation scoring should primarily use STEADY_RUNNING windows.

Startup spikes must not be treated as degradation or anomaly by default.

Startup exclusion rule:

```text
If machine transitions from non-running to running,
ignore the first 2-5 minutes for degradation/anomaly scoring,
but still store telemetry normally.
```

## Feature Window Table Concept

Create compact summaries from raw telemetry.

Candidate table:

```text
machine_feature_windows
```

Suggested fields:

- device_id
- tenant_id
- window_start
- window_end
- window_minutes
- current_avg_mean
- current_avg_std
- current_avg_p50
- current_avg_p95
- current_l1_mean
- current_l2_mean
- current_l3_mean
- power_mean
- power_p95
- power_factor_mean
- voltage_avg_mean
- voltage_imbalance
- phase_imbalance
- frequency_mean
- energy_kwh
- telemetry_coverage
- running_state
- excluded_reason

Aggregation cadence:

- 5-minute windows for future anomaly activity
- hourly rollups for degradation scoring

## Baseline Design

Baselines must be per-machine, not global.

Baseline fields:

- current baseline
- power baseline
- power factor baseline
- voltage baseline
- phase imbalance baseline
- current variability baseline
- operating mode/running-state baseline
- learned_from_start_ts
- learned_from_end_ts
- baseline_version
- status: active / candidate / retired
- quality_score

Baseline quality inputs:

- reading coverage
- steady-running coverage
- time spread
- variance stability
- telemetry gap quality
- signal completeness

If baseline quality is weak, UI should show:

```text
Learning baseline
```

or:

```text
Low confidence: insufficient stable telemetry
```

Do not force confident scores from weak baselines.

## Phase 1: Machine Degradation Score

Question answered:

```text
Is this machine slowly getting worse?
```

Update cadence:

- compute every 1 hour
- dashboard reads latest stored snapshot
- show "Updated X minutes ago"

Initial UI:

- score 1 to 10
- health band
- confidence %
- top 3 reasons
- last calculated time
- 7-day or 9-day score trend
- baseline status
- phase status

Suggested score bands:

- 1.0-2.9: Healthy
- 3.0-4.9: Watch
- 5.0-6.9: Warning
- 7.0-10.0: Critical

Recommended first formula:

```text
degradation_raw =
  current_variability_score * 0.25
+ power_factor_drop_score * 0.25
+ abnormal_power_draw_score * 0.20
+ phase_imbalance_drift_score * 0.15
+ trend_worsening_score * 0.15
```

Confidence formula concept:

```text
confidence =
  baseline_quality
  * telemetry_coverage
  * steady_running_coverage
  * signal_completeness
```

Top reason examples:

- Power factor dropped 14% below learned baseline over 5 days.
- Current variability is 2.4x normal across recent steady-running windows.
- Power draw is 18% above learned baseline during comparable running periods.
- Phase imbalance is worse than this machine's learned phase profile.
- Score trend worsened +1.8 over the last 7 days.

Phase imbalance rule:

- Do not compare every machine to a perfect three-phase ideal only.
- Learn each machine's normal phase profile.
- Flag when phase imbalance worsens versus its own baseline, especially when PF drops or variability rises.

Performance target:

- score calculation happens in background
- dashboard latest-score read should be fast, ideally under a few hundred milliseconds
- no raw telemetry scan during dashboard page load

Suggested Phase 1 tables:

```text
machine_health_baselines
machine_health_latest
machine_health_history
machine_feature_windows
```

Phase 1 exclusions:

- no automatic alerts initially
- no hard maintenance reset workflow initially
- no anomaly timeline initially
- no claim of exact failure date

## Phase 2: Anomaly Activity

Question answered:

```text
Did anything unusual happen recently?
```

This should be built after Phase 1 is stable.

Recommended cadence:

- start with 5-minute micro-batch windows
- later add severe-only faster path if needed
- do not write one event per raw telemetry reading in the first version

Widget shows:

- today count
- this week count
- this month count
- mild / strong / severe breakdown
- last anomaly
- top signal
- trend vs previous week
- baseline quality

Detection methods:

- z-score
- modified z-score using median absolute deviation
- persistence checks
- cross-field confirmation
- startup/shutdown exclusion
- supply-event tagging

Severity concept:

- mild: small but confirmed deviation
- strong: clear deviation or repeated deviation
- severe: extreme deviation or sustained dangerous pattern

Important rule:

```text
Do not count startup spikes as machine anomalies.
```

Suggested anomaly tables:

```text
machine_anomaly_events
machine_anomaly_daily_counts
```

Weekly and monthly counts can initially be derived from daily counts.

Potential event fields:

- device_id
- tenant_id
- occurred_at
- ended_at
- duration_seconds
- signal_field
- signal_value
- baseline_value
- z_score
- severity
- confidence
- anomaly_type
- supply_related
- startup_adjacent
- mode_change
- recurring
- time_window

Anomaly UI examples:

- "12 events this week"
- "1 severe, 3 strong, 8 mild"
- "Last: 2h ago - 28.4 A on Current Avg"
- "Worsening this week"

## Maintenance Reset Direction

Do not hard-reset the score to 1 just because maintenance was marked complete.

Preferred future state machine:

```text
active -> maintenance_pending -> candidate_baseline -> active
```

After maintenance:

- create maintenance event
- start candidate baseline
- require 24-72 hours stable telemetry before promoting
- if unstable, keep old baseline and show maintenance recovery warning

This can be Phase 3 after the two widgets are stable.

## API Shape

Phase 1 candidate endpoints:

```text
GET /api/v1/devices/{device_id}/health-intelligence
GET /api/v1/devices/{device_id}/health-score-history
GET /api/v1/devices/{device_id}/health-baseline
```

Phase 2 candidate endpoints:

```text
GET /api/v1/devices/{device_id}/anomaly-widget
GET /api/v1/devices/{device_id}/anomaly-history
GET /api/v1/devices/{device_id}/anomaly-breakdown
GET /api/v1/devices/anomaly-widget/fleet
```

The exact service ownership must be verified before implementation.

## UI Direction

Machine dashboard should eventually show:

- Degradation Score widget
- Anomaly Activity widget

Clicking each widget opens an expanded panel with:

- breakdown
- reasons
- trend
- confidence
- history/timeline

Keep UI language honest:

- "Risk score"
- "Confidence"
- "Top contributing signals"
- "Baseline quality"
- "Updated X minutes ago"

Avoid unsafe language:

- "Guaranteed failure prediction"
- "100% accurate"
- "Exact failure date"

## Operational Safety

If score worker is delayed or fails:

- machine dashboard must still load
- show "Score unavailable" or "Last computed X ago"
- never calculate raw score synchronously during page load

If telemetry coverage is poor:

- reduce confidence
- explain missing coverage
- do not produce misleading high-certainty result

## Implementation Order

Recommended order when development begins:

1. Phase 1 analysis prompt for OpenCode/GLM.
2. Codex validates analysis.
3. Implement feature-window/baseline design locally.
4. Add degradation score calculation.
5. Add latest score API.
6. Add dashboard widget.
7. Add tests and local validation.
8. Only after stable Phase 1, design Phase 2 anomaly activity.

## Non-Goals For First Implementation

- No production patch without explicit approval.
- No replacement/removal of current ML analytics at first.
- No live raw-telemetry dashboard scoring.
- No broad DB migration without careful review.
- No alerts until false-positive behavior is understood.

## Open Questions Before Implementation

- Which service should own machine health intelligence: device-service, analytics-service, or a new lightweight service?
- Which existing telemetry summary APIs/tables can be reused?
- Do we already store maintenance events in a reusable model?
- What is the exact local and production migration process?
- What signal fields are guaranteed for real devices versus simulator-only?
- What baseline learning duration should be configurable per organization?
- What UI label should be shown while baseline is learning?

## Founder-Level Product Decision

This feature should be treated as a production-grade replacement path for the current heavy ML failure-prediction experience, but with safer wording.

The product should not claim:

```text
This predicts the exact date of failure.
```

The product can confidently claim:

```text
This estimates machine degradation risk using explainable telemetry evidence.
```

Reason:

- even ML-based failure prediction is probabilistic, not 100% accurate
- this approach is explainable and auditable
- every score can show the exact signals that contributed
- the system is lighter on CPU/RAM than model inference
- dashboards remain fast because scoring is precomputed
- customers can understand current, PF, power, phase, and trend reasons

Good customer-facing language:

- "Degradation Score"
- "Failure Risk"
- "Maintenance Risk"
- "Confidence"
- "Top Reasons"
- "Baseline Quality"
- "Updated X minutes ago"
- "Learning baseline"
- "Insufficient telemetry coverage"

Avoid:

- "Guaranteed failure prediction"
- "100% accurate"
- "Exact failure date"
- "Machine will fail on..."

## Why This Is Better Than Heavy ML For The Current Platform

Current ML analytics risk profile:

- heavy runtime cost
- memory pressure under concurrent users
- slower local and production execution
- harder to explain to customers
- difficult to debug when results look wrong
- limited practical range
- not suitable for instant machine dashboard cards

Machine Health Intelligence risk profile:

- uses compact summary rows
- runs in background
- dashboard reads latest snapshots
- explainable signal-by-signal output
- easier to validate and test
- easier to tune by machine type
- safer for 1000+ devices

This does not mean ML is useless.

Long-term, ML can be kept as an optional advanced analytics path. But day-to-day production machine health should use this explainable engine first.

## Strong Architectural Rule

There must be exactly one shared health feature foundation.

Do not build:

```text
degradation feature aggregation path
anomaly feature aggregation path
dashboard-specific aggregation path
report-specific aggregation path
```

Build:

```text
machine_feature_windows
```

Then let degradation score and anomaly activity both consume it.

This avoids the same mistake that caused earlier energy/cost consistency problems: multiple modules computing the same concept in different ways.

## Service Ownership Options

Before implementation, inspect the repo and choose ownership carefully.

### Option A: Add To analytics-service

Pros:

- conceptually related to analytics
- may already have worker infrastructure
- avoids introducing another service

Cons:

- current analytics may already be heavy
- risk of coupling this lightweight feature to slow analytics flows
- if analytics service is down, machine dashboard health widget might be affected

Recommended only if analytics-service is lightweight enough after inspection.

### Option B: Add To device-service

Pros:

- machine dashboard already depends heavily on device-service
- device metadata and machine dashboard context likely lives here
- simpler API routing for per-machine card

Cons:

- device-service is already critical
- adding scoring workers to it may increase blast radius
- telemetry aggregation may not belong here

Recommended only if the scoring is read-side only and worker logic is separated cleanly.

### Option C: New lightweight machine-health-service

Pros:

- clean ownership
- isolated workers
- clear API boundary
- easier to scale independently
- avoids slowing existing services

Cons:

- new service, compose entries, routing, health checks
- more operational surface area
- more deployment work

Best long-term architecture, but may be too large for Phase 1 MVP.

### Initial Recommendation

For Phase 1 local implementation, prefer the least risky path after repo inspection:

```text
If device-service already owns dashboard bootstrap and can expose one read-only endpoint:
  keep API in device-service
  keep scoring logic in a separate module/package
  run worker separately if possible

If analytics-service already has clean worker scheduling and is not coupled to heavy ML:
  place scoring worker there
  expose lightweight API through device-service or analytics-service
```

Do not decide without inspecting actual code.

## Data Flow Detail

Target flow:

```text
MQTT telemetry
  -> data-service writes raw telemetry to Influx
  -> background feature aggregation reads recent telemetry
  -> machine_feature_windows upserted to MySQL
  -> degradation scorer reads feature windows
  -> machine_health_latest and machine_health_history updated
  -> UI reads latest score only
```

Important:

- UI must not query raw Influx for health score
- UI must not compute baseline live
- UI must not trigger scoring job during page load
- score endpoint must be safe even if worker is behind

## Feature Window Granularity

Use two layers:

### 5-Minute Feature Windows

Purpose:

- anomaly activity
- startup/shutdown/load-change detection
- future severe-event fast path

Fields:

- mean
- std
- min
- max
- p50
- p95
- first value
- last value
- sample count
- telemetry coverage

### Hourly Feature Windows

Purpose:

- degradation scoring
- long trend
- baseline learning
- lower DB volume

Can be derived from 5-minute windows or computed directly from telemetry.

Recommended:

- Phase 1 can compute hourly windows directly if simpler
- Phase 2 should introduce 5-minute windows if anomaly activity begins

## Window Coverage Rules

Each feature window must include telemetry coverage.

Example:

```text
expected_samples = window_seconds / expected_sample_interval_seconds
coverage = actual_samples / expected_samples
```

If sample interval is variable or unknown:

```text
coverage = covered_duration_seconds / window_seconds
```

Coverage bands:

- `>= 0.90`: high
- `0.70 - 0.89`: medium
- `0.40 - 0.69`: low
- `< 0.40`: insufficient

Do not score a window confidently when coverage is low.

## Running State Detection Detail

The classifier should use current, power, and maybe device status if available.

Suggested state rules:

### OFF

```text
current_avg near 0
power near 0
or device status says stopped/off
```

### STARTUP

```text
previous window OFF or IDLE
current rises sharply
power rises sharply
first 2-5 minutes after transition
```

### STEADY_RUNNING

```text
current above running threshold
power above running threshold
current variability below mode-change threshold
not inside startup exclusion window
not inside shutdown exclusion window
```

### LOAD_CHANGE

```text
current or power shifts to a new level
shift persists long enough to be real
new level is relatively stable
```

### SHUTDOWN

```text
current/power falls sharply from running to near zero
```

### UNKNOWN

```text
coverage too low
missing important fields
conflicting signals
```

Score treatment:

- STEADY_RUNNING: eligible for degradation scoring
- STARTUP: exclude from degradation and normal anomaly counts
- LOAD_CHANGE: exclude or lower confidence until stable
- OFF: no degradation scoring
- UNKNOWN: no confident scoring

## Startup Spike Handling Detail

This is critical because every machine may spike when started.

Do not flag normal startup spike as failure.

Recommended approach:

```text
if transition_to_running:
  mark startup_exclusion_until = first_running_ts + configured_startup_minutes
```

Default:

- startup exclusion: 3 minutes
- configurable per tenant/machine type later

If telemetry frequency is 30 seconds:

- 3 minutes = about 6 samples

If telemetry frequency is 60 seconds:

- 3 minutes = about 3 samples

The system should still store the spike in telemetry and feature windows, but mark it as startup excluded.

UI wording:

```text
Startup transient excluded from risk scoring
```

## Baseline Learning Detail

Initial baseline should use recent stable windows, not all telemetry.

Default learning:

- minimum 7 days
- recommended 14 days
- maximum lookback 30 days
- only STEADY_RUNNING windows
- exclude startup/shutdown/load-change/unknown

Minimum requirements:

- enough steady-running windows
- enough coverage
- enough signal completeness
- no extreme telemetry gaps

If device is new:

```text
Learning baseline - X days remaining
```

If device has sparse data:

```text
Learning baseline - waiting for enough stable running data
```

## Baseline Versioning

Every active baseline must be versioned.

Why:

- maintenance can change normal behavior
- repaired machines may draw less current
- cleaning filters can reduce power draw
- bearing replacement can improve PF/current variability
- old baselines need audit history

Statuses:

- active
- candidate
- retired

Future maintenance reset:

```text
active baseline remains active
candidate baseline starts after maintenance
candidate promoted only after stable telemetry
old baseline retired after promotion
```

## Baseline Quality Formula

Candidate quality formula:

```text
quality =
  coverage_score * 0.35
+ steady_running_score * 0.25
+ signal_completeness_score * 0.20
+ variance_stability_score * 0.10
+ time_spread_score * 0.10
```

Bands:

- `>= 0.85`: high
- `0.70 - 0.84`: medium
- `0.50 - 0.69`: low
- `< 0.50`: insufficient

Score confidence should never exceed baseline quality by much.

Example:

```text
baseline_quality = 0.62
max_confidence = around 62-70%
```

## Degradation Signal Details

### Current Variability Score

Purpose:

- detects unstable draw
- useful for mechanical/electrical instability

Inputs:

- current_avg_std from steady-running windows
- baseline current variability

Candidate formula:

```text
ratio = current_std_recent / baseline_current_std
```

Scoring:

- ratio <= 1.2: 0
- ratio 1.2-1.8: mild
- ratio 1.8-2.5: warning
- ratio > 2.5: critical contribution

Need safeguards:

- baseline std cannot be zero
- use floor epsilon
- require enough windows

### Power Factor Drop Score

Purpose:

- strong early warning signal
- PF drop can indicate inefficiency, load/motor issue, wiring, or poor operating condition

Inputs:

- recent PF mean during steady-running
- baseline PF mean

Candidate formula:

```text
drop_pct = (baseline_pf - recent_pf) / baseline_pf
```

Scoring:

- drop < 3%: 0
- 3-8%: mild
- 8-15%: warning
- > 15%: critical contribution

Safeguards:

- PF must be valid between 0 and 1
- ignore negative PF unless explicitly supported by meter semantics
- missing/invalid PF lowers confidence
- do not assume PF silently for this feature

### Abnormal Power Draw Score

Purpose:

- detects sustained higher power draw under comparable operation

Inputs:

- recent power mean/p95
- baseline power mean/p95
- steady-running windows only

Candidate formula:

```text
power_ratio = recent_power_mean / baseline_power_mean
```

Scoring:

- <= 1.10: 0
- 1.10-1.25: mild
- 1.25-1.50: warning
- > 1.50: critical contribution

Safeguard:

- if load/mode changed and stabilized, do not immediately call degradation
- require trend/persistence

### Phase Imbalance Drift Score

Purpose:

- detects worsening phase behavior compared to machine's own normal profile

Do not compare only to ideal equal phases.

Compute current phase imbalance:

```text
avg_phase_current = mean(l1, l2, l3)
max_deviation = max(abs(l1 - avg), abs(l2 - avg), abs(l3 - avg))
imbalance_pct = max_deviation / avg_phase_current
```

But compare to machine baseline:

```text
drift = recent_imbalance_pct - baseline_imbalance_pct
```

Scoring:

- no drift or tiny drift: 0
- moderate drift: mild/warning
- large sustained drift plus PF/current issues: high contribution

Special cases:

- if only one phase is available, skip phase score and lower confidence
- if avg current is near zero, do not calculate phase imbalance
- if one phase is naturally always higher but stable, do not punish

### Trend Worsening Score

Purpose:

- prevents one bad day from creating a critical score
- captures gradual degradation

Inputs:

- previous health scores
- recent 7-day slope
- week-over-week signal changes

Candidate:

```text
slope = score_today - score_7_days_ago
```

or:

```text
linear regression slope over last 7-14 daily/hourly scores
```

Scoring:

- flat or improving: 0
- small worsening: mild
- consistent worsening: warning
- sharp worsening with other signals: critical

## Degradation Final Score Detail

Raw contribution output should remain explainable.

Example payload:

```json
{
  "score": 7.4,
  "confidence": 0.82,
  "status": "critical",
  "updated_at": "2026-05-21T13:30:00Z",
  "baseline_quality": "high",
  "contributions": {
    "current_variability": 0.65,
    "power_factor_drop": 0.81,
    "abnormal_power_draw": 0.55,
    "phase_imbalance_drift": 0.42,
    "trend_worsening": 0.72
  },
  "top_reasons": [
    "Power factor dropped 14% below learned baseline over 5 days.",
    "Current variability is 2.4x normal across recent steady-running windows.",
    "Score trend worsened +1.8 over the last 7 days."
  ]
}
```

Scale raw 0-1 to score 1-10:

```text
score = 1 + (raw_weighted_score * 9)
```

Clamp:

```text
min 1
max 10
```

If confidence is too low:

- still compute internal score if possible
- UI should show low-confidence badge
- do not show critical language without enough confidence

## Degradation Snapshot Tables

Candidate `machine_health_latest`:

```text
tenant_id
device_id
score
status
confidence
baseline_version
baseline_quality
top_reasons_json
contributions_json
phase_status
computed_at
source_window_start
source_window_end
worker_version
```

One row per device.

Candidate `machine_health_history`:

```text
tenant_id
device_id
computed_at
score
status
confidence
baseline_version
contributions_json
```

Retention:

- keep hourly scores 90 days
- optionally daily compressed history for 2 years later

## Worker Scheduling

Feature aggregation:

```text
every 5 minutes:
  create/update recent feature windows
```

Degradation scoring:

```text
every 1 hour:
  score devices with sufficient baseline
```

Batching:

```text
batch size: 50 devices
concurrency: 2-4
retry failed batch only
```

Why:

- prevents one bad device from blocking all scoring
- keeps DB and Influx load controlled
- avoids giant all-device jobs

Backpressure:

- if worker is behind, skip duplicate scheduled runs
- do not run multiple full-score jobs concurrently
- latest successful score remains visible

## Dashboard API Performance

Latest score endpoint should be read-only and fast.

It should query:

```text
machine_health_latest
```

not:

```text
raw telemetry
Influx full-range query
baseline computation
score computation
```

Endpoint behavior:

- if row exists, return latest row
- if no row but baseline learning, return learning state
- if worker stale, return stale marker
- if error, return safe unavailable payload

Example unavailable response:

```json
{
  "device_id": "AD00000001",
  "available": false,
  "state": "unavailable",
  "message": "Machine health score is not available yet.",
  "last_computed_at": null
}
```

## UI Placement For Phase 1

Machine detail dashboard:

- add a compact Degradation Score card near health/KPI area
- card shows score, band, confidence, updated time
- clicking opens expanded panel

Expanded panel:

- current score
- confidence
- top reasons
- signal contributions
- key current/PF/power/phase values vs baseline
- 7-day trend
- baseline status

Do not make first version too visually heavy.

Initial card copy:

```text
Degradation Score
7.4 / 10
Critical
Confidence 82%
Updated 18 min ago
```

Learning copy:

```text
Learning baseline
Collecting stable running data
```

Low confidence copy:

```text
Low confidence
Insufficient stable telemetry
```

## Anomaly Activity Detailed Design

Anomaly is Phase 2 and should not block Phase 1.

### Anomaly Definition

An anomaly is a confirmed unusual event compared to the machine's own learned baseline.

Not anomaly:

- normal startup
- normal shutdown
- planned load change
- supply voltage issue affecting multiple machines
- sparse telemetry gap
- one noisy reading without confirmation

### Detection Window

Initial:

```text
5-minute windows
```

Later:

```text
1-minute severe-only fast path if needed
```

Reason:

- 5-minute windows reduce false positives
- reduces DB writes
- easier to explain and test
- good enough for operational dashboards

### Z-Score Method

Standard z-score:

```text
z = (value - mean) / std
```

Modified z-score:

```text
z_modified = 0.6745 * (value - median) / MAD
```

Use modified z-score when MAD is meaningful.

Use standard z-score when MAD is too small or unavailable.

Never divide by zero.

### Candidate Severity

```text
abs(z) < 2.0: normal
2.0 <= abs(z) < 3.0: mild candidate
3.0 <= abs(z) < 4.0: strong candidate
abs(z) >= 4.0: severe candidate
```

Candidate does not always become event.

### Confirmation Rules

Initial simple confirmation:

- mild: require repeated/persistent candidate across window
- strong: require stronger persistence or multi-field support
- severe: can confirm faster if extreme and not startup/supply

Avoid counting every raw outlier as a separate event.

Merge nearby events:

```text
same device + same signal + same severity within short time window
=> same event with extended duration
```

### Cross-Field Validation

If current anomaly and PF anomaly:

- confidence increases

If current anomaly and voltage anomaly:

- tag as supply-related
- do not count as machine degradation anomaly unless persistent independently

If PF anomaly alone:

- possible early degradation
- keep but lower severity unless persistent

## Anomaly Count Tables

Candidate `machine_anomaly_events`:

```text
tenant_id
device_id
event_id
occurred_at
ended_at
duration_seconds
signal_field
signal_value
baseline_value
z_score
severity
confidence
anomaly_type
supply_related
startup_adjacent
mode_change
recurring
time_window
created_at
```

Candidate `machine_anomaly_daily_counts`:

```text
tenant_id
device_id
date
total_count
mild_count
strong_count
severe_count
supply_related_count
top_signal
avg_confidence
updated_at
```

Widget can compute weekly/monthly from daily counts.

Do not add weekly table until needed.

## Anomaly Widget Payload

Example:

```json
{
  "device_id": "AD00000001",
  "is_learning": false,
  "today": {
    "total": 3,
    "mild": 2,
    "strong": 1,
    "severe": 0
  },
  "week": {
    "total": 12,
    "mild": 8,
    "strong": 3,
    "severe": 1
  },
  "month": {
    "total": 41,
    "mild": 28,
    "strong": 11,
    "severe": 2
  },
  "last_anomaly": {
    "occurred_at": "2026-05-21T13:22:00Z",
    "signal_field": "current_avg",
    "signal_value": 28.4,
    "baseline_value": 12.5,
    "z_score": 3.8,
    "severity": "strong"
  },
  "trend": "worsening",
  "top_signal": "current_avg",
  "baseline_quality": "high"
}
```

## Fleet-Level Health Later

After per-machine Phase 1 and Phase 2 are stable:

- fleet degradation summary
- machines sorted by risk
- anomaly activity across org
- "needs attention" list

Do not start with fleet view.

Per-machine correctness first.

## Accuracy And Feedback

Accuracy cannot be proven without maintenance labels.

But confidence can be computed from data quality.

Long-term feedback:

- operator marks issue real / false positive / unsure
- maintenance findings linked to high scores
- threshold tuning per machine type

Do not build feedback UI in Phase 1 unless it is cheap.

Keep design ready for it.

## Testing Strategy

### Unit Tests

Test:

- running state classifier
- startup exclusion
- baseline quality formula
- scoring formula
- missing signal behavior
- invalid PF behavior
- phase imbalance calculation
- confidence clamping
- no NaN/Infinity

### Integration Tests

Test:

- feature window creation from sample telemetry
- baseline learned from stable windows
- latest score created
- dashboard endpoint returns latest score
- no raw telemetry query in UI endpoint

### Performance Tests

Synthetic:

- 1500 devices
- N windows per device
- score all devices in batches
- ensure worker time acceptable
- ensure dashboard endpoint remains fast

### Regression Tests

Ensure no breakage to:

- reports
- waste analysis
- calendar
- machine dashboard KPIs
- telemetry ingestion
- factory copilot

## Validation Metrics For Phase 1

Minimum before production:

- score computed for test devices
- low-confidence state shown for weak baseline
- learning state shown for new/insufficient devices
- startup spikes excluded from degradation
- dashboard remains fast
- worker failure does not break page
- no new 500s in reports/waste/copilot
- no existing energy/cost consistency regressions

## Production Rollout Plan Later

When implementation is ready:

1. Local implementation only.
2. Local tests.
3. Local Docker validation with `.env.local`.
4. Confirm no RDS usage from local.
5. Commit local code.
6. Production patch only after explicit approval.
7. Backup server files.
8. Apply patch.
9. Rebuild affected services with server-build override if GHCR unavailable.
10. Verify containers healthy.
11. Verify endpoints.
12. Verify UI.
13. Update memory and checklist.

Never patch production directly during discussion mode.

## OpenCode / GLM Workflow For This Feature

Use controlled phases.

Phase 1 analysis prompt should ask OpenCode to:

- inspect current service ownership
- find telemetry query patterns
- find existing machine dashboard API
- find existing maintenance log model
- find migration framework
- propose exact files to modify
- identify tests
- explicitly say what not to touch

OpenCode should not edit files during analysis.

Codex validates analysis before implementation.

Implementation should be split:

1. database/models/migration
2. feature aggregation
3. baseline/scoring engine
4. API
5. UI
6. tests

No broad one-shot implementation.

## Decision Gate Before Coding

Before writing code, answer:

- Which service owns Phase 1?
- What tables are required for Phase 1 only?
- Can we reuse existing telemetry summary code?
- What endpoint powers machine dashboard today?
- What is the minimum UI card?
- What tests prove no service break?
- What migration rollback is possible?

If these are not answered, do not implement.
