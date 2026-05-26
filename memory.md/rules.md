# Runtime Rules

## Environment Separation

- `.env.local` is for local development only.
- `.env` is for production deployment values.
- Local development must continue using local Docker-backed infrastructure such as local MySQL and local MinIO.
- Production must use production-backed infrastructure such as AWS RDS and, once migrated, AWS S3.

## Local Docker Command Rule

- Always run local Docker Compose with `.env.local`, not the default `.env`.
- If local pages suddenly start returning widespread `500` errors across Machines, Calendar, Reports, alerts, or fleet APIs after a recreate/restart, verify the running containers did not accidentally come up with `.env` production values.
- The first runtime checks should be:
  - inspect live container env for `DATABASE_URL` / `MYSQL_HOST`
  - confirm they point to local `mysql`, not production RDS
  - recreate the affected services explicitly with `.env.local`
- Use these commands for local runs:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml down
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

- If only selected local services drifted to `.env`, prefer targeted recreation first:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d --force-recreate --no-deps device-service rule-engine-service data-service analytics-service analytics-worker analytics-worker-2 data-export-service energy-service reporting-service reporting-worker waste-analysis-service copilot-service rule-engine-worker data-telemetry-worker data-telemetry-worker-2 ui-web
```

## EMQX Runtime Config Rule

- For MQTT validation, `ops/emqx/local.base.hocon` and `ops/emqx/production.base.hocon` are the intended source of truth.
- EMQX also persists runtime changes in `/opt/emqx/data/configs/cluster.hocon`.
- Dashboard/API/CLI edits inside EMQX can silently override the git-controlled `base.hocon` config and survive normal `docker compose down` / `up`.
- If MQTT auth/ACL behavior does not match the repo config, check for stale EMQX runtime overrides before changing application code.
- For local recovery after auth/authz drift, reset the EMQX data volume and recreate the broker so it boots from the repo-managed config.
- With the current default compose project name, the local EMQX state volumes are `shivex-main_emqx_data` and `shivex-main_emqx_log`.
- Local EMQX reset flow:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml rm -sf emqx
docker volume rm shivex-main_emqx_data shivex-main_emqx_log
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d emqx
```

## Production Docker Rule

- Production server runs Docker Compose with the default `.env`.
- Production deploy flow is:

```bash
git pull
docker compose down
docker compose up -d --build
```

## Production Validation Rule

- Do not run destructive reset validation against the production server.
- `full-reset` / volume-destructive validation is only for local or disposable preprod environments.
- Production post-deploy validation must be non-destructive and should use scoped smoke checks only.
- Production smoke may create limited smoke artifacts, but those must be:
  - scoped to dedicated smoke-safe entities where possible
  - deliberately cleaned up afterward if they are not meant to persist
- Never use production smoke in a way that wipes shared/customer data or removes live infrastructure volumes.

## Secret Handling Rule

- Never commit production AWS access keys or secret keys into repo-tracked files.
- Repo `.env` may contain blank placeholders for production-only secrets, but the real values must be added only on the production server.
- At minimum, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` must be server-only values.

## RDS Rule

- `docker-compose.yml` is now DB env-driven for production database wiring.
- Production database values must come from `.env`.
- Local database values must come from `.env.local`.
- Do not test local using the default `.env`, because that can accidentally point local containers to production RDS.

## Current Status Notes

- RDS network path has been validated from the EC2 app server to the AWS RDS instance.
- RDS database `ai_factoryops` exists.
- App DB user `energy` exists.
- Read-only DB user `copilot_reader` exists.
- Full production cutover is only considered complete after the server pulls the updated code, starts successfully, and application services are verified against RDS at runtime.
- S3 migration is a separate step and should be completed and validated after RDS cutover.
