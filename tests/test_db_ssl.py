import os
import unittest

from app import create_app
from app import db


class DbSslTests(unittest.TestCase):
    def test_ssl_disabled_returns_none(self):
        self.assertIsNone(db._ssl_options({"DB_SSL_MODE": "disabled"}))

    def test_ssl_required_with_pem_env_writes_tmp_ca(self):
        pem = "-----BEGIN CERTIFICATE-----\\nABC\\n-----END CERTIFICATE-----"
        opts = db._ssl_options({"DB_SSL_MODE": "required", "DB_SSL_CA_PEM": pem})
        self.assertEqual(opts, {"ca": "/tmp/nodetonest-db-ca.pem"})
        with open("/tmp/nodetonest-db-ca.pem", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("-----BEGIN CERTIFICATE-----", text)
        self.assertIn("-----END CERTIFICATE-----", text)
        self.assertIn("\nABC\n", text)

    def test_ssl_required_without_ca_raises(self):
        with self.assertRaises(ValueError):
            db._ssl_options({"DB_SSL_MODE": "required"})

    def test_ssl_invalid_pem_raises(self):
        with self.assertRaises(ValueError):
            db._ssl_options({"DB_SSL_MODE": "required", "DB_SSL_CA_PEM": "not-a-pem"})

    def test_ssl_unsupported_mode_raises(self):
        with self.assertRaises(ValueError):
            db._ssl_options({"DB_SSL_MODE": "required-ish"})

    def test_healthz_route_exists(self):
        app = create_app({"TESTING": True})
        client = app.test_client()
        r = client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
