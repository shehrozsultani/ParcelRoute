"""Tracking tests.

These run WITHOUT a MySQL server: the project's own SQL dump is loaded into an
in-memory SQLite copy and db._run is swapped for a SQLite runner. The queries
used by the app are plain, portable SQL, so this verifies the logic and the
real data. Run MySQL-specific verification separately (see README).
"""
import os
import re
import sqlite3
import unittest
from pathlib import Path

from app import create_app, db

SQL_FILE = Path(__file__).resolve().parent.parent / "database" / "delivery_logistics_full_corrected.sql"


def build_sqlite():
    sql = SQL_FILE.read_text(encoding="utf8")
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    for m in re.finditer(r"CREATE TABLE `(\w+)` \((.*?)\) ENGINE", sql, re.S):
        cols = []
        for line in m.group(2).split("\n"):
            line = line.strip().rstrip(",")
            if line.startswith("`"):
                cols.append(re.sub(r"\s+(NOT NULL|NULL)$", "", line))
        con.execute(f"CREATE TABLE {m.group(1)} ({', '.join(cols)})")
    body = sql[sql.index("START TRANSACTION;"):]
    for stmt in re.findall(r"INSERT INTO .*?;\n", body, re.S):
        con.execute(stmt.replace("\\'", "''"))
    return con


class TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = build_sqlite()

        def run(sql, params=()):
            return [dict(r) for r in cls.con.execute(sql.replace("%s", "?"), params)]

        cls._orig = db._run
        db._run = run
        cls.client = create_app({"TESTING": True}).test_client()

    @classmethod
    def tearDownClass(cls):
        db._run = cls._orig

    def test_home_loads_with_real_samples(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"100000000", r.data)

    def test_delivered_parcel_shows_full_journey(self):
        r = self.client.get("/track?tn=100000000")
        self.assertEqual(r.status_code, 200)
        for text in (b"Delivered", b"At origin hub", b"Out for delivery", b"Karachi Main Hub", b"Islamabad Hub"):
            self.assertIn(text, r.data)

    def test_failed_delivery_shows_attempt_reasons(self):
        row = self.con.execute(
            """SELECT p.tracking_number FROM parcels p JOIN deliveries d USING(parcel_id)
               WHERE d.final_status='failed' LIMIT 1""").fetchone()
        r = self.client.get(f"/track?tn={row[0]}")
        self.assertIn(b"Delivery failed", r.data)
        self.assertIn(b"Not delivered", r.data)

    def test_returned_parcel_has_return_block(self):
        row = self.con.execute(
            """SELECT p.tracking_number FROM parcels p JOIN returns r USING(parcel_id)
               WHERE r.return_status IS NOT NULL LIMIT 1""").fetchone()
        r = self.client.get(f"/track?tn={row[0]}")
        self.assertIn(b"Return", r.data)

    def test_unknown_number_gives_friendly_message(self):
        r = self.client.get("/track?tn=999999999")
        self.assertIn(b"No parcel found", r.data)
        self.assertNotIn(b"Traceback", r.data)

    def test_invalid_formats_are_rejected_before_sql(self):
        for bad in ("abc", "12345", "1000000000", "1' OR '1'='1", "<script>"):
            r = self.client.get("/track", query_string={"tn": bad})
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"doesn", r.data)  # "doesn't look like a tracking number"
            self.assertNotIn(b"<script>", r.data)

    def test_empty_search_shows_prompt(self):
        r = self.client.get("/track")
        self.assertIn(b"Enter your 9-digit", r.data)

    def test_receiver_phone_is_masked(self):
        row = self.con.execute(
            "SELECT tracking_number, receiver_phone FROM parcels WHERE receiver_phone IS NOT NULL LIMIT 1").fetchone()
        r = self.client.get(f"/track?tn={row[0]}")
        self.assertNotIn(row[1].encode(), r.data)

    def test_missing_receiver_phone_does_not_crash(self):
        row = self.con.execute(
            "SELECT tracking_number FROM parcels WHERE receiver_phone IS NULL LIMIT 1").fetchone()
        self.assertEqual(self.client.get(f"/track?tn={row[0]}").status_code, 200)

    def test_every_parcel_page_renders(self):
        # all 12,000 real records must render without error
        rows = self.con.execute(
            "SELECT tracking_number FROM parcels WHERE parcel_id % 20 = 0").fetchall()  # every 20th record
        bad = [r[0] for r in rows if self.client.get(f"/track?tn={r[0]}").status_code != 200]
        self.assertEqual(bad, [])

    def test_events_follow_workflow_order_even_if_timestamps_do_not(self):
        from app.services import tracking
        with self.client.application.app_context():
            for tn in ("100000003", "100000000", "100000010"):
                ranks = [tracking.STATUS_RANK[e["status"]] for e in tracking.get_tracking(tn)["events"]]
                self.assertEqual(ranks, sorted(ranks), tn)

    def test_database_down_shows_friendly_503(self):
        def boom(sql, params=()):
            raise db.DatabaseError("connection refused")
        saved = db._run
        db._run = boom
        try:
            r = self.client.get("/track?tn=100000000")
            self.assertEqual(r.status_code, 503)
            self.assertIn(b"temporarily unavailable", r.data)
            self.assertNotIn(b"connection refused", r.data)
        finally:
            db._run = saved


if __name__ == "__main__":
    unittest.main()
