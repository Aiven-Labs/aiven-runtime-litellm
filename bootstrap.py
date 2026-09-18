"""Validate starter settings and launch the version-pinned LiteLLM proxy."""
import base64
import binascii
import json
import os
from pathlib import Path
import ssl
import sys
from urllib.parse import urlencode, urlsplit, urlunsplit


def required(env, name, minimum=1):
    value = env.get(name, "")
    if len(value) < minimum:
        raise ValueError(f"{name} must contain at least {minimum} characters")
    return value


def connection(raw, schemes, local, ca, postgres=False):
    parts = urlsplit(raw)
    if parts.scheme not in schemes or not parts.hostname or not parts.port:
        raise ValueError("Connection URI requires a supported scheme, hostname and explicit port")
    if not postgres and parts.path not in ("", "/", "/0"):
        raise ValueError("Use Valkey database 0")
    if postgres and (not parts.username or not parts.password or parts.path in ("", "/")):
        raise ValueError("PostgreSQL URI requires credentials and a database")
    # Discard URI query options so injected options cannot weaken certificate checks.
    if postgres:
        query = {"sslmode": "disable"} if local else {
            "sslmode": "require", "sslaccept": "strict", "sslcert": str(ca)
        }
        scheme = "postgresql"
    else:
        if not local and not parts.password:
            raise ValueError("Valkey URI requires a password")
        scheme = "redis" if local else "rediss"
        query = {} if local else {
            "ssl_cert_reqs": "required", "ssl_check_hostname": "true",
            "ssl_ca_certs": str(ca)
        }
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), ""))


def prepare(env, directory):
    local = env.get("LOCAL_DEVELOPMENT", "false").lower() == "true"
    master = required(env, "LITELLM_MASTER_KEY", 35)
    if not master.startswith("sk-"):
        raise ValueError("LITELLM_MASTER_KEY must start with sk-")
    salt = required(env, "LITELLM_SALT_KEY", 32)
    if salt == master:
        raise ValueError("Generate separate master and salt keys")
    required(env, "UI_USERNAME")
    required(env, "UI_PASSWORD", 16)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    ca = directory / "aiven-ca.pem"
    if not local:
        try:
            pem = base64.b64decode(required(env, "AIVEN_CA_CERT_BASE64"), validate=True).decode("ascii")
            ssl.create_default_context(cadata=pem)
        except (ValueError, UnicodeError, binascii.Error, ssl.SSLError) as exc:
            raise ValueError("AIVEN_CA_CERT_BASE64 must encode a valid PEM CA certificate") from exc
        ca.write_text(pem)
        ca.chmod(0o600)
    env["DATABASE_URL"] = connection(required(env, "DATABASE_URL"), ("postgres", "postgresql"), local, ca, True)
    env["REDIS_URL"] = connection(required(env, "VALKEY_URL"), ("redis", "rediss", "valkey", "valkeys"), local, ca)
    env["STORE_MODEL_IN_DB"] = "True"
    env["LITELLM_TELEMETRY"] = "False"
    config = {
        "model_list": [],
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"},
        "router_settings": {"redis_url": "os.environ/REDIS_URL"},
        "litellm_settings": {"cache": False, "set_verbose": False},
    }
    path = directory / "config.yaml"
    # JSON is valid YAML; credentials stay in the environment, not this file.
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def main():
    os.umask(0o077)
    try:
        config = prepare(os.environ, Path("/tmp/litellm-starter"))
    except ValueError as exc:
        print(f"Starter configuration error: {exc}", file=sys.stderr)
        return 1
    print("Starting LiteLLM on port 8080; database migrations must succeed.", flush=True)
    os.execvp("litellm", ["litellm", "--config", str(config), "--host", "0.0.0.0",
                         "--port", "8080", "--num_workers", "1",
                         "--enforce_prisma_migration_check", "--use_v2_migration_resolver"])


if __name__ == "__main__":
    sys.exit(main())
