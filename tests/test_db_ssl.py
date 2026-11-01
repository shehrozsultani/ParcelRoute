import os
import stat
import unittest

from app import db


class SSLConfigTests(unittest.TestCase):
    def tearDown(self):
        try:
            os.remove("/tmp/nodetonest-db-ca.pem")
        except FileNotFoundError:
            pass

    def test_disabled_ssl_returns_none(self):
        cfg = {"DB_SSL_MODE": "disabled"}
        self.assertIsNone(db._ssl_options(cfg))

    def test_required_ssl_without_ca_raises(self):
        cfg = {"DB_SSL_MODE": "required"}
        with self.assertRaisesRegex(ValueError, "no CA was provided"):
            db._ssl_options(cfg)

    def test_pem_supports_escaped_newlines_and_writes_secure_file(self):
        pem = "-----BEGIN CERTIFICATE-----\\nabc\\n-----END CERTIFICATE-----"
        cfg = {"DB_SSL_MODE": "required", "DB_SSL_CA_PEM": pem}
        opts = db._ssl_options(cfg)
        self.assertEqual(opts, {"ca": "/tmp/nodetonest-db-ca.pem"})
        with open("/tmp/nodetonest-db-ca.pem", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n")
        if os.name == "posix":
            mode = stat.S_IMODE(os.stat("/tmp/nodetonest-db-ca.pem").st_mode)
            self.assertEqual(mode, 0o600)

    def test_invalid_pem_raises_clear_error(self):
        cfg = {"DB_SSL_MODE": "required", "DB_SSL_CA_PEM": "not-a-certificate"}
        with self.assertRaisesRegex(ValueError, "complete PEM certificate"):
            db._ssl_options(cfg)

    def test_invalid_base64_raises_clear_error(self):
        cfg = {"DB_SSL_MODE": "required", "DB_SSL_CA_BASE64": "$$$"}
        with self.assertRaisesRegex(ValueError, "not valid base64"):
            db._ssl_options(cfg)
