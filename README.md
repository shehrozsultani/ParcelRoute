# ParcelRoute — Logistics & Last-Mile Parcel Routing web app

Flask + MySQL web application built around the existing `delivery_logistics` database.
The database schema and data are used as-is; this app only **reads** from it so far.

## Status
| Feature | State |
|---|---|
| Homepage | Done |
| Parcel tracking (real data) | Done, 12 automated tests |
| Booking | Waiting on 3 decisions (see `docs/DATABASE_ANALYSIS.md`) |
| Dashboard / hubs / riders | Planned |

## Run it
1. Create the database and load YOUR dump (the dump begins with `DROP TABLE IF EXISTS`, so use a fresh database):
   ```
   mysql -u root -p -e "CREATE DATABASE delivery_logistics CHARACTER SET utf8mb4"
   mysql -u root -p delivery_logistics < database/delivery_logistics_full_corrected.sql
   ```
2. `python -m venv .venv` then activate it, then `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `DB_PASSWORD`.
   - Local MySQL: keep `DB_SSL_MODE=disabled`.
   - Aiven/hosted MySQL: set `DB_SSL_MODE=required` and add one of `DB_SSL_CA_PATH`, `DB_SSL_CA_PEM`, or `DB_SSL_CA_BASE64`.
4. `python run.py` and open http://127.0.0.1:5000. Try tracking `100000000`.

## Test
`python -m unittest tests.test_tracking` — loads your SQL dump into an in-memory SQLite copy, so no MySQL is needed.
Limitation: this checks app logic and your real data, not MySQL-specific behaviour. Please also click through the app against real MySQL.

## Architecture
Browser → Flask routes (`app/routes.py`) → service layer with SQL (`app/services/tracking.py`) → `app/db.py` (parameterized queries via PyMySQL) → MySQL.

## Security
Parameterized SQL only, tracking numbers validated (`^\d{9}$`) before any query, credentials in `.env` (git-ignored), receiver phone masked, database errors shown as a friendly 503.

## Known data-quality issues in the source data
See `docs/DATABASE_ANALYSIS.md`. The tracking page works around them and does not hide them.
