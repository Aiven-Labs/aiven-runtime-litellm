# LiteLLM starter for Aiven Runtime

A standalone **LiteLLM AI Gateway and Admin UI** with **Aiven for PostgreSQL** and **Aiven for Valkey**. Bring your own model-provider credentials and expose them through an OpenAI-compatible API with virtual keys, budgets and usage tracking.

The application image is pinned to LiteLLM **v1.101.0**, including its registry digest. No model provider is configured and no model calls are made automatically.

## Architecture

```text
Browser / API client --HTTPS--> Aiven Runtime :8080
                                      |
                               LiteLLM proxy + UI
                                /            \
                         verified TLS    verified TLS
                              /                \
                    Aiven PostgreSQL       Aiven Valkey
```

PostgreSQL holds application configuration, users, virtual keys, spend records and encrypted provider credentials. Valkey supplies shared gateway/routing state. LLM response caching is disabled by default. Valkey is a dependency of this starter even though LiteLLM can run without it in smaller configurations.

The bootstrap validates required settings, enforces TLS on managed service connections, and starts LiteLLM with migration failure checks enabled. LiteLLM handles authentication itself. `/ui` is the admin console; API requests require a key. Liveness and other upstream public endpoints are not protected by a separate password page.

## Local demo

Requires Docker Compose v2 and a container engine.

1. Copy `.env.example` to `.env`.
2. Generate independent values for `POSTGRES_PASSWORD` and `UI_PASSWORD` with `openssl rand -hex 24`.
3. Generate two separate values with `openssl rand -hex 32`, prefix each with `sk-`, and set `LITELLM_MASTER_KEY` and `LITELLM_SALT_KEY`.
4. Run `docker compose up --build -d`. Initial database migrations may take several minutes.
5. Open <http://localhost:8080/ui> and log in with `UI_USERNAME` and `UI_PASSWORD`.

Only port 8080 is published, on loopback. Local PostgreSQL and Valkey use the private Compose network without TLS; local Valkey has no password. `LOCAL_DEVELOPMENT=true` is exclusively for this local setup. Never enable it on Runtime.

`docker compose down` keeps PostgreSQL data. `docker compose down -v` permanently deletes local application data. Valkey state is disposable in the local demo.

## Deploy on Aiven Runtime

1. Commit and push this repository to GitHub so Runtime can build it.
2. In Aiven Console, deploy a Runtime application from the repository and select **compose.aiven.yaml**. The scanner recognizes PostgreSQL and Valkey dependencies and can create credential integrations. Review both mappings: PostgreSQL connection string to `DATABASE_URL`, Valkey connection string to `VALKEY_URL`.
3. Use a dedicated, initially empty PostgreSQL database owned by the supplied account. Start with PostgreSQL 16; the scanner ignores image version tags, so explicitly review the version in Console.
4. Choose one Runtime replica and configure the variables below before startup. Publish only HTTP **8080**. The inherited image also advertises 4000, but the starter listens on 8080.
5. Wait for migrations, open the generated HTTPS URL with `/ui`, and sign in. The gateway starts with an empty model list.

For MCP/API deployment, build the root Dockerfile and create the two `application_service_credential` integrations explicitly; the API does not process Compose manifests.

### Suggested demo sizes

| Service | Starting point | Notes |
| --- | --- | --- |
| Runtime | 1 replica, 2 GiB RAM | Allow memory and time for initial migrations; increase if startup or workload needs it |
| PostgreSQL | `startup-4` or equivalent 4 GiB plan | Dedicated application database; conservative starting point |
| Valkey | Smallest available plan with at least 1 GiB RAM | Shared state, with response caching disabled |

These are estimates, not benchmarked minimums or production recommendations. Plans are selected in Console/API, not enforced by this Compose file. Check available internal/free plans and displayed pricing before creating services. See [VALIDATION.md](VALIDATION.md) for test status.

### Runtime variables

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Integration-provided PostgreSQL connection URI, including credentials, database and port |
| `VALKEY_URL` | Integration-provided Valkey connection URI, including credentials and port; database 0 |
| `AIVEN_CA_CERT_BASE64` | Project CA PEM encoded as a single line using `openssl base64 -A -in ca.pem` |
| `LITELLM_MASTER_KEY` | Unique admin API secret: `sk-` followed by at least 32 random characters |
| `LITELLM_SALT_KEY` | Separate stable random secret used to encrypt provider credentials; generate independently |
| `UI_USERNAME` | Bootstrap admin username, for example `admin` |
| `UI_PASSWORD` | Unique admin UI password, at least 16 characters |

Keep credentials and keys in Runtime secrets and outside Git. Both managed services must use the CA supplied here; normally this is the Aiven project CA. The wrapper converts Valkey URIs to `rediss` and requires certificate and hostname checks. PostgreSQL uses Prisma's `sslmode=require`, `sslaccept=strict` and CA certificate options. Incoming URI query parameters are deliberately discarded so they cannot disable TLS verification.

Preserve `LITELLM_SALT_KEY` across restarts, upgrades and restores; changing it can make saved provider credentials unreadable. Back up it separately alongside PostgreSQL backups. Keep the master key private; applications should receive restricted virtual keys instead.

The demo uses LiteLLM's environment-based admin login. For shared use, follow the upstream guide to create individual admin accounts and then set `disable_env_credential_login: true` in the `general_settings` generated by `bootstrap.py`. Verify individual login before disabling the bootstrap account. SSO and other enterprise features may require a LiteLLM license.

## Add a model and try the API

1. Sign in to `/ui`, open **Models**, and add a provider, model ID and provider API key. Choose a model alias such as `my-model`. This is saved in PostgreSQL; no provider secrets need to be committed to the repo.
2. Create a virtual key restricted to that alias with an appropriate budget and rate limit.
3. Export `LITELLM_BASE_URL` to your HTTPS application origin and `LITELLM_API_KEY` to the virtual key in your shell. Run:

```sh
curl "$LITELLM_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"my-model","messages":[{"role":"user","content":"Reply with a short hello."}]}'
```

Provider usage is billed by your chosen provider. Restart the Runtime application and check that the model configuration and virtual key remain available. The template contains no bundled model, inference engine or sample provider credentials.

## Validation and operations

Run `python3 -m unittest discover -s tests -v` with Python 3.10+. Container and live deployment checks are recorded separately in [VALIDATION.md](VALIDATION.md).

The Docker health check calls `/health/liveliness`; this only proves the proxy is running. Check database readiness, authenticated model/key operations and a real provider request separately. Runtime may ignore Dockerfile health checks.

This is a single-replica demo. Database migrations run at startup using LiteLLM's v2 migration resolver and fail startup on migration errors. Before scaling out, move migrations into a controlled deployment step and configure connection limits, rate limits, retention, monitoring and failure handling. Back up before upgrades and do not downgrade a migrated database. The image inherits the upstream runtime user and dependencies; review hardening for your production environment.

## References

- [LiteLLM deployment](https://docs.litellm.ai/docs/proxy/deploy)
- [LiteLLM Admin UI and account setup](https://docs.litellm.ai/docs/proxy/ui)
- [LiteLLM configuration](https://docs.litellm.ai/docs/proxy/config_settings)
- [Pinned LiteLLM release](https://github.com/BerriAI/litellm/releases/tag/v1.101.0)
- [Aiven Runtime Compose manifests](https://aiven.io/docs/products/runtime/manifest-files/compose-files)
