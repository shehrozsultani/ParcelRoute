# Database analysis (from delivery_logistics_full_corrected.sql)

Source: one SQL file, 15 tables, 163,218 rows, 15 FOREIGN KEYs enforced, no views/triggers/saved queries. Schema matches your ER diagram exactly.

## Row counts
cities 30 · failure_reasons 10 · customers 3,000 · hubs 20 · addresses 4,028 · riders 80 · routes 152 · parcels 12,000 · deliveries 12,000 · delivery_attempts 16,653 · parcel_items 15,514 · payments 12,000 · pre_dispatch_checks 12,000 · returns 3,731 · status_logs 72,000

## Real vocabularies
- status_logs.status: booked, at_origin_hub, in_transit, at_destination_hub, out_for_delivery, then delivered (7,325) / delivery_failed (676) / returned (3,999)
- parcels.current_status: complete 6,650 · canceled 2,588 · refund 1,411 · closed 1,351 (NOT delivery states)
- deliveries.final_status: delivered / returned / failed
- payments: cod, credit_card, debit_card, easypaisa, easypay, jazzcash; status collected / pending / settled / refunded
- pre_dispatch_checks.dispatch_decision: READY (risk 1-3) / VERIFY (risk 4-6)
- hubs: 2 origin (Karachi, Lahore), 6 transit, 12 destination. routes: 152, all active.

## Cardinality (verified)
parcel → delivery 1:1, → payment 1:1, → pre_dispatch_check 1:1, → status_logs exactly 6 each, → return 0..1 (3,731), → items 1..3.

## Data-quality findings
1. **status_logs.logged_at is out of workflow order for 7,386 of 12,000 parcels.** log_id always follows the workflow, so the app orders by log_id and shows timestamps as recorded.
2. **deliveries.route_id matches the parcel's origin/destination hubs only 75 of 12,000 times.** The tracking page does not show the route.
3. **Rider's assigned hub = parcel destination hub only 614 of 12,000.**
4. 'booked' log hub equals parcels.origin_hub_id only 603 of 12,000; the app shows the parcel's own origin hub for that event.
5. Receiver address city equals destination hub city only 432 of 12,000; sender address city equals origin hub city 377 of 12,000. Receiver addresses belong to other customers (only 3 belong to the sender), so `receiver_name` rarely matches the address owner.
6. parcels.declared_value equals payments.order_value (12,000/12,000) but never equals the sum of parcel_items.
7. Payment methods 'easypay' and 'easypaisa' both exist (probably the same thing).
8. All parcels are historical (2016-03 to 2018-08) and terminal: no parcel is currently in transit or pending.
9. 3,999 'returned' deliveries but only 3,731 return rows; 457 delivered parcels also have a return row.
10. The meaning of parcels.current_status (complete/closed/refund/canceled) is UNKNOWN — requires your confirmation.

## Decisions needed before building Booking
A. parcels.current_status has no value for an active parcel. Allow a new value (e.g. 'booked')? No schema change needed (plain VARCHAR(20)), but it is a new vocabulary value.
B. A new booking has no rider or route yet, but deliveries.pickup_time and out_for_delivery_time are NOT NULL. Options: (1) bookings create no deliveries row until dispatch, and rider/dispatch features are read-only; (2) optional migration making those two columns NULLable. Back up first.
C. Receiver address: addresses.customer_id is NOT NULL, so a new receiver address must be owned by a customer. Proposal: store it under the sender.
