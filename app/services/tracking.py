"""Parcel tracking: all SQL for the tracking page lives here.

Every status shown comes from the real `status_logs.status` values in the
database. Nothing is invented.
"""
import re

from .. import db

# Real status_logs.status values found in the data, in workflow order.
WORKFLOW = [
    "booked", "at_origin_hub", "in_transit",
    "at_destination_hub", "out_for_delivery",
]
FINAL_STATES = ["delivered", "delivery_failed", "returned"]
STATUS_RANK = {s: i for i, s in enumerate(WORKFLOW + FINAL_STATES)}

STATUS_LABELS = {
    "booked": "Booked",
    "at_origin_hub": "At origin hub",
    "in_transit": "In transit",
    "at_destination_hub": "At destination hub",
    "out_for_delivery": "Out for delivery",
    "delivered": "Delivered",
    "delivery_failed": "Delivery failed",
    "returned": "Returned",
}

TRACKING_RE = re.compile(r"^\d{9}$")  # existing numbers are 9 digits


def is_valid_format(tn):
    return bool(TRACKING_RE.match(tn))


def label(status):
    return STATUS_LABELS.get(status, status.replace("_", " ").capitalize())


def mask_phone(phone):
    if not phone or len(phone) < 7:
        return None
    return phone[:4] + "•••" + phone[-3:]


def sample_tracking_numbers(n=3):
    rows = db.query_all(
        "SELECT tracking_number FROM parcels ORDER BY parcel_id LIMIT %s", (n,))
    return [r["tracking_number"] for r in rows]


def get_tracking(tn):
    parcel = db.query_one(
        """
        SELECT p.parcel_id, p.tracking_number, p.booking_date, p.category,
               p.weight_kg, p.declared_value, p.current_status, p.is_cod,
               p.receiver_name, p.receiver_phone,
               c.full_name  AS sender_name,
               oh.hub_name  AS origin_hub, oh.city AS origin_city,
               dh.hub_name  AS dest_hub,   dh.city AS dest_city,
               ra.address_line AS recv_line, ra.area AS recv_area,
               rc.city_name AS recv_city
        FROM parcels p
        JOIN customers c  ON c.customer_id = p.sender_id
        JOIN hubs oh      ON oh.hub_id = p.origin_hub_id
        JOIN hubs dh      ON dh.hub_id = p.destination_hub_id
        JOIN addresses ra ON ra.address_id = p.receiver_address_id
        JOIN cities rc    ON rc.city_id = ra.city_id
        WHERE p.tracking_number = %s
        """, (tn,))
    if parcel is None:
        return None

    pid = parcel["parcel_id"]
    logs = db.query_all(
        """
        SELECT s.log_id, s.status, s.logged_at, s.hub_id, h.hub_name, h.city,
               s.rider_id, r.full_name AS rider_name
        FROM status_logs s
        JOIN hubs h ON h.hub_id = s.hub_id
        LEFT JOIN riders r ON r.rider_id = s.rider_id
        WHERE s.parcel_id = %s
        """, (pid,))
    # Order by log_id, NOT logged_at: in the source data log_id always follows the
    # workflow, but logged_at is out of workflow order for ~62% of parcels.
    logs.sort(key=lambda e: e["log_id"])
    for e in logs:
        e["label"] = label(e["status"])
        # The 'booked' log row carries an unrelated hub in the source data
        # (matches parcels.origin_hub_id only ~5% of the time), so show the
        # parcel's own origin hub for that event instead.
        if e["status"] == "booked":
            e["hub_name"], e["city"] = parcel["origin_hub"], parcel["origin_city"]

    delivery = db.query_one(
        """
        SELECT d.delivery_id, d.assignment_time, d.pickup_time,
               d.out_for_delivery_time, d.delivery_time, d.final_status,
               d.total_attempts, r.full_name AS rider_name, r.vehicle_type
        FROM deliveries d JOIN riders r ON r.rider_id = d.rider_id
        WHERE d.parcel_id = %s
        """, (pid,))

    attempts = []
    if delivery:
        attempts = db.query_all(
            """
            SELECT a.attempt_number, a.attempt_datetime, a.was_successful,
                   f.description AS failure_reason, a.rider_notes
            FROM delivery_attempts a
            LEFT JOIN failure_reasons f ON f.reason_id = a.failure_reason_id
            WHERE a.delivery_id = %s ORDER BY a.attempt_number
            """, (delivery["delivery_id"],))

    payment = db.query_one(
        """SELECT payment_method, net_amount, cod_amount, cod_collected,
                  payment_status FROM payments WHERE parcel_id = %s""", (pid,))
    ret = db.query_one(
        """SELECT return_reason, return_status, return_date
           FROM returns WHERE parcel_id = %s""", (pid,))

    reached = {e["status"] for e in logs}
    final = next((s for s in FINAL_STATES if s in reached), None)
    stages = [{"key": s, "label": label(s), "done": s in reached} for s in WORKFLOW]
    stages.append({
        "key": final or "pending",
        "label": label(final) if final else "Final outcome",
        "done": final is not None,
        "outcome": final,
    })
    latest = logs[-1] if logs else None

    parcel["receiver_phone_masked"] = mask_phone(parcel["receiver_phone"])
    return {"parcel": parcel, "events": logs, "stages": stages, "latest": latest,
            "delivery": delivery, "attempts": attempts, "payment": payment,
            "ret": ret}
