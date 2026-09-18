# Validation

## Local checks — 18 September 2026

- Bootstrap unit tests cover enforced TLS settings, preservation of encoded credentials, invalid connection URIs, missing secrets, invalid CA input, local mode and empty-model startup configuration.
- Official `ghcr.io/berriai/litellm:v1.101.0` manifest resolved to the digest pinned in the Dockerfile, with Linux amd64 and arm64 variants.

## Pending

- Container build and local Compose startup (no container engine available in the authoring environment).
- Aiven Runtime build, PostgreSQL migrations and Valkey connectivity.
- Native UI login, rejection of invalid credentials, and unauthenticated API rejection.
- Model configuration and virtual-key persistence after restart.
- A real model request using a privately supplied provider key.
- Resource usage and actual plan selection/pricing.

Suggested sizes in the README are estimates until live testing is recorded here. No Aiven services have been created for this starter yet.
