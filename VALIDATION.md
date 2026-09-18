# Validation

## Aiven Runtime — 18 September 2026

Successfully deployed the unmodified template from commit `2ed8b7faf6489c52ff5f1ffc9153a929e74a2404` in AWS Ireland (`aws-eu-west-1`).

| Component | Tested configuration | Listed base price/hour |
| --- | --- | --- |
| Runtime | `startup-100-2048`, one replica, 2 GiB RAM | $0.06849 |
| PostgreSQL | `startup-4`, PostgreSQL 16.15 | $0.151 |
| Valkey | `startup-1`, Valkey 9.1.2 | $0.041 |

Total listed base price: **$0.26049/hour**, approximately **$6.25/day** while running, before any additional usage charges or account-specific discounts. Prices were checked for this project and region on the test date.

### Passed

- Aiven built the pinned LiteLLM v1.101.0 image and deployed the pushed commit successfully.
- Both service credential integrations supplied working connection strings.
- PostgreSQL startup migrations completed with the template's strict TLS settings; `/health/readiness` returned HTTP 200 with `db: connected`.
- Valkey answered PING over certificate- and hostname-verified TLS. The dedicated service contained six shared-state keys, with active subscribe, set and get client connections from the gateway workload.
- Native Admin UI rendered and rejected an incorrect password; the configured admin credentials opened the dashboard.
- Missing and invalid API keys returned HTTP 401.
- Created a database-backed mock model and a virtual key restricted to that model. The virtual key returned the expected mock chat completion; access to a different model returned HTTP 403.
- Powered the Runtime application off and on. Logs confirmed the old process shut down and a new runtime instance started. The same model and virtual key worked afterward without being recreated; PostgreSQL remained connected and the browser session retained access to the saved key.
- No implementation changes were necessary during this deployment test.

The model `runtime-smoke-mock` and key alias `runtime-smoke-test` exist only in the live test installation, not in the template. The test key was created with a one-day expiry and a $1 budget. The model returns a fixed mock response and makes no external provider call; any tiny spend estimate displayed by LiteLLM is not a provider charge.

## Local checks

- Seven bootstrap unit tests passed, covering strict TLS query settings, encoded credentials, invalid URIs, missing secrets, invalid CA input, local mode and empty-model configuration.
- Official image manifest resolved to the digest pinned in the Dockerfile, with Linux amd64 and arm64 variants.
- `git diff --cached --check` passed.

## Limits and remaining checks

- Real model-provider authentication and inference were not tested: no provider API key was supplied.
- Local Docker Compose startup was not tested because no container engine was available in the authoring environment. Its Valkey image is version 8; the managed service test used 9.1.2.
- Runtime reported that Dockerfile HEALTHCHECK is ignored for OCI images. HTTP and authenticated API checks were run independently.
- The public readiness endpoint reports database status but does not prove Valkey connectivity; Valkey was checked separately.
- This was a small, single-replica functional test, not a load test, HA exercise or production sizing benchmark.
- The Console Compose scanner workflow was not exercised; deployment used Aiven MCP with explicit service integrations and the root Dockerfile.
