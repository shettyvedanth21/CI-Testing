# Shivex Performance Hardening Status

This document is the simple project-level summary of the completed performance hardening work as of May 17, 2026.

It is meant to answer three questions clearly:

1. What performance work is already done?
2. What is still left?
3. Which remaining items are code work vs ops/infra work?

## What Is Already Done

### 1. Shared auth middleware hot path was improved

- The backend auth middleware was doing repeated tenant-feature database work on normal authenticated requests.
- That duplicate work was removed on the same-tenant path.
- Security was not weakened:
  - token revocation still checks Redis per request
  - `permissions_version` still checks the database per request
  - `tenant_entitlements_version` still checks the database per request
  - plant-scoped access is still derived correctly

Practical meaning:
- authenticated backend requests are lighter than before
- correctness and tenant safety remain intact

### 2. Safe backend response compression was added

- Non-streaming API responses now support gzip compression through a shared backend helper.
- This was enabled only for API services where it was safe.
- Live streaming endpoints such as SSE were intentionally excluded.
- `ui-web` was left alone because runtime checks already showed HTML gzip behavior there.

Practical meaning:
- larger backend responses can travel more efficiently
- live status and streaming behavior were not turned into stale/static behavior

### 3. Unsafe caching changes were intentionally avoided

- A route-by-route review confirmed that many device/history/config/admin reads still depend on immediate read-after-write truth.
- Because of that, broad short-TTL caching was deliberately not added.

Practical meaning:
- the platform avoided a false optimization that could have shown stale data after edits

### 4. Production API worker posture is now configurable

- API services were previously single-process by default.
- Worker count is now configurable by environment for production-facing use.
- Local/dev defaults were intentionally left simple at one worker.
- Debug multi-worker startup is explicitly blocked when it would be unsafe.

Practical meaning:
- production can scale API concurrency more safely
- local development did not become more complicated

## What Is Not Finished

The remaining work is mostly not urgent code work.

### A. Worker sizing guidance

This is the most useful next step.

It means deciding:
- which API should stay at `1` worker
- which API can move above `1`
- what CPU / RAM / DB pool / request backlog signals should trigger scaling

Type of work:
- documentation
- operations guidance
- deployment/runtime planning

### B. Redis / projection / outbox scaling hardening

This remains the biggest long-term traffic risk.

The main known sensitivity is still:
- `data-service` projection stage
- then downstream outbox pressure
- then shared Redis headroom

Type of work:
- mainly infra/ops
- monitoring
- load/rollout planning

### C. Cache invalidation design

This is optional later work if faster config/history/admin reads become a priority.

It would require:
- explicit invalidation rules
- mutation-aware refresh behavior
- safe cache-busting semantics

Type of work:
- real code/UX design work

This is not required immediately.

### D. Production deployment verification

Before rollout, it is still worth validating:
- compression behavior through real ingress
- worker counts against DB pool headroom
- service memory/CPU headroom

Type of work:
- deployment validation
- not mainly code work

## What Is Code Work vs Non-Code Work

### Mostly completed code work

- auth middleware hot-path cleanup
- backend compression
- cache-safety classification
- worker-count configurability

### Mostly non-code work still remaining

- worker sizing guidance
- Redis/projection infra hardening
- production deployment verification

### Optional later code/design work

- cache invalidation / mutation-aware revalidation

## Recommended Next Step

If the goal is to close this performance track cleanly, the best next step is:

1. operator-facing worker sizing guidance
2. then production verification
3. then later, only if needed, cache invalidation design

## Plain-English Final Summary

Shivex performance work is in a better place now than before:

- common authenticated backend requests are lighter
- backend responses are more efficient
- dangerous stale-cache shortcuts were avoided
- production API concurrency is now configurable

What remains is mostly about using those improvements correctly in production, not rewriting the application again right now.
