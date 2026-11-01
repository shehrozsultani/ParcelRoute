# NodeToNest — Logistics & Last-Mile Parcel Routing web app

Flask + MySQL web application built around the existing `project` database.
The database schema and data are used as-is; this app only **reads** from it so far.

## Status
| Feature | State |
|---|---|
| Homepage | Done |
| Parcel tracking (real data) | Done, 12 automated tests |
| Booking | Waiting on 3 decisions (see `docs/DATABASE_ANALYSIS.md`) |
| Dashboard / hubs / riders | Planned |

## Run it
1. Use your existing MySQL database (`DB_NAME=project`).
   - Optional for a separate local test database only: load `database/delivery_logistics_full_corrected.sql` into a fresh local DB.
2. `python -m venv .venv` then activate it, then `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `DB_PASSWORD`.
   - Local MySQL: keep `DB_SSL_MODE=disabled`.
   - Aiven/hosted MySQL: set `DB_SSL_MODE=required` and add one of `DB_SSL_CA_PATH`, `DB_SSL_CA_PEM`, or `DB_SSL_CA_BASE64`.
   - Set `APP_ENV=development` for local development. Production must use `APP_ENV=production`.
   - Set a strong `SECRET_KEY` (32+ random characters). The app rejects weak/default production secrets.
4. `python run.py` and open http://127.0.0.1:5000. Try tracking `100000000`.

## Authentication and RBAC (Phase 1)
- Login route: `/login`
- Logout route: `POST /logout`
- Protected routes:
  - `/ops` (roles: `ops`, `admin`)
  - `/admin` (role: `admin`)
- Public tracking remains open (`/`, `/track`, `/healthz`).

### Provisioning the first administrator safely
1. Initialize auth schema:
   - `flask --app run.py init-auth-schema`
2. Create first admin user (password prompt is hidden; no plaintext stored):
   - `flask --app run.py create-admin --username your_admin --role admin`

Passwords are stored as hashes only (`werkzeug.security`), never plaintext.

## Test
`python -m unittest tests.test_tracking` — loads your SQL dump into an in-memory SQLite copy, so no MySQL is needed.
Limitation: this checks app logic and your real data, not MySQL-specific behaviour. Please also click through the app against real MySQL.

## Architecture
Browser → Flask routes (`app/routes.py`) → service layer with SQL (`app/services/tracking.py`) → `app/db.py` (parameterized queries via PyMySQL) → MySQL.

## Security
Parameterized SQL only, tracking numbers validated (`^\d{9}$`) before any query, credentials in `.env` (git-ignored), receiver phone masked, database errors shown as a friendly 503.

## Known data-quality issues in the source data
See `docs/DATABASE_ANALYSIS.md`. The tracking page works around them and does not hide them.
