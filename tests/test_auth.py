import unittest

from app import create_app, db
from app.services import auth_service


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "APP_ENV": "production",
            "SECRET_KEY": "x" * 48,
        })
        self.client = self.app.test_client()
        self._orig_authenticate = auth_service.authenticate_user

    def tearDown(self):
        auth_service.authenticate_user = self._orig_authenticate

    def _csrf(self):
        self.client.get("/login")
        with self.client.session_transaction() as sess:
            return sess["csrf_token"]

    def test_successful_login_sets_session(self):
        auth_service.authenticate_user = lambda u, p: {
            "user_id": 1,
            "username": "alice",
            "role": "admin",
        } if (u, p) == ("alice", "StrongPassword123!") else None

        r = self.client.post("/login", data={
            "csrf_token": self._csrf(),
            "username": "alice",
            "password": "StrongPassword123!",
        })
        self.assertEqual(r.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["username"], "alice")
            self.assertEqual(sess["role"], "admin")

    def test_invalid_credentials_return_generic_message(self):
        auth_service.authenticate_user = lambda _u, _p: None
        r = self.client.post("/login", data={
            "csrf_token": self._csrf(),
            "username": "nouser",
            "password": "wrongpass",
        })
        self.assertEqual(r.status_code, 401)
        self.assertIn(b"Invalid username or password", r.data)

    def test_password_hash_verification(self):
        pwd = "VeryStrongPassword123!"
        hashed = auth_service.hash_password(pwd)
        self.assertNotEqual(hashed, pwd)
        self.assertTrue(auth_service.verify_password(pwd, hashed))
        self.assertFalse(auth_service.verify_password("WrongPassword123!", hashed))

    def test_unauthenticated_access_to_protected_route_redirects_to_login(self):
        r = self.client.get("/ops")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_role_authorization(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["username"] = "ops-user"
            sess["role"] = "ops"
            sess["csrf_token"] = "token"
        self.assertEqual(self.client.get("/ops").status_code, 200)
        self.assertEqual(self.client.get("/admin").status_code, 403)

        with self.client.session_transaction() as sess:
            sess["role"] = "admin"
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_logout_invalidates_session(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "alice"
            sess["role"] = "admin"
            sess["csrf_token"] = "logout-token"
        r = self.client.post("/logout", data={"csrf_token": "logout-token"})
        self.assertEqual(r.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)
            self.assertNotIn("username", sess)
            self.assertNotIn("role", sess)

    def test_csrf_rejects_missing_or_invalid_tokens(self):
        r1 = self.client.post("/login", data={"username": "x", "password": "y"})
        self.assertEqual(r1.status_code, 400)

        self.client.get("/login")
        r2 = self.client.post("/login", data={
            "csrf_token": "invalid-token",
            "username": "x",
            "password": "y",
        })
        self.assertEqual(r2.status_code, 400)

    def test_tracking_and_healthz_remain_public(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/track").status_code, 200)

    def test_weak_secret_rejected_in_production(self):
        with self.assertRaises(RuntimeError):
            create_app({
                "TESTING": False,
                "APP_ENV": "production",
                "SECRET_KEY": "dev-only-change-me",
            })

    def test_database_failure_handled_safely_on_login(self):
        def boom(_u, _p):
            raise db.DatabaseError("connection refused")

        auth_service.authenticate_user = boom
        r = self.client.post("/login", data={
            "csrf_token": self._csrf(),
            "username": "alice",
            "password": "StrongPassword123!",
        })
        self.assertEqual(r.status_code, 503)
        self.assertIn(b"temporarily unavailable", r.data)
        self.assertNotIn(b"connection refused", r.data)


if __name__ == "__main__":
    unittest.main()
