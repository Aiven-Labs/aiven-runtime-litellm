import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from bootstrap import connection, prepare


class ConfigurationTests(unittest.TestCase):
    def env(self):
        return dict(LOCAL_DEVELOPMENT="true", LITELLM_MASTER_KEY="sk-" + "a" * 32,
                    LITELLM_SALT_KEY="b" * 32, UI_USERNAME="admin", UI_PASSWORD="c" * 20,
                    DATABASE_URL="postgresql://user:p%40ss@postgres:5432/demo",
                    VALKEY_URL="redis://valkey:6379/0")

    def test_postgres_enforces_tls_and_preserves_encoded_credentials(self):
        uri = connection("postgres://u:p%40ss@db.example:1234/demo?sslmode=disable&sslaccept=accept_invalid_certs",
                         ("postgres",), False, Path("/tmp/ca.pem"), True)
        parts = urlsplit(uri)
        self.assertEqual(parts.netloc, "u:p%40ss@db.example:1234")
        self.assertEqual(parse_qs(parts.query), dict(sslmode=["require"], sslaccept=["strict"], sslcert=["/tmp/ca.pem"]))

    def test_valkey_enforces_certificate_and_hostname_checks(self):
        uri = connection("valkey://u:p@cache:1234/0?ssl_cert_reqs=none", ("valkey",), False, Path("/tmp/ca.pem"))
        self.assertEqual(urlsplit(uri).scheme, "rediss")
        query = parse_qs(urlsplit(uri).query)
        self.assertEqual(query["ssl_cert_reqs"], ["required"])
        self.assertEqual(query["ssl_check_hostname"], ["true"])

    def test_local_configuration_has_no_models_or_response_cache(self):
        env = self.env()
        with tempfile.TemporaryDirectory() as tmp:
            cfg = json.loads(prepare(env, Path(tmp)).read_text())
        self.assertEqual(cfg["model_list"], [])
        self.assertFalse(cfg["litellm_settings"]["cache"])
        self.assertNotIn(env["UI_PASSWORD"], json.dumps(cfg))
        self.assertEqual(env["STORE_MODEL_IN_DB"], "True")
        self.assertEqual(parse_qs(urlsplit(env["DATABASE_URL"]).query)["sslmode"], ["disable"])

    def test_missing_or_short_secrets_fail_closed(self):
        for name in ("LITELLM_MASTER_KEY", "LITELLM_SALT_KEY", "UI_PASSWORD", "UI_USERNAME"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                env = self.env()
                env[name] = ""
                with self.assertRaises(ValueError):
                    prepare(env, Path(tmp))

    def test_runtime_requires_valid_ca(self):
        for value in ("", "not-base64", "aGVsbG8="):
            env = self.env()
            env.update(LOCAL_DEVELOPMENT="false", AIVEN_CA_CERT_BASE64=value)
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                prepare(env, Path(tmp))

    def test_bad_database_uri_rejected(self):
        for uri in ("https://db:1234/demo", "postgresql://db:5432/demo", "postgresql://u:p@db/demo"):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                connection(uri, ("postgresql",), False, Path("/tmp/ca.pem"), True)

    def test_runtime_valkey_requires_password_and_database_zero(self):
        for uri in ("redis://cache:1234/0", "rediss://u:p@cache:1234/1"):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                connection(uri, ("redis", "rediss"), False, Path("/tmp/ca.pem"))


if __name__ == "__main__":
    unittest.main()
