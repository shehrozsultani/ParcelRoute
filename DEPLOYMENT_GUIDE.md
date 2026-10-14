# DEPLOYMENT_GUIDE

This guide prepares your **existing ParcelRoute** app for a real public URL.

I inspected your full project and made only safe deployment fixes.

## 1) What I checked and fixed

### Blockers found
1. `app/db.py` had a broken MySQL password line, so production DB connection could fail.
2. SSL was always forced to `app/certs/ca.pem`, but that file/folder does not exist in this repo.
3. There was no complete beginner deployment guide.

### Safe code changes already done
- Fixed MySQL connection config in `/home/runner/work/ParcelRoute/ParcelRoute/app/db.py`.
- Added flexible SSL config for Aiven in:
  - `/home/runner/work/ParcelRoute/ParcelRoute/app/config.py`
  - `/home/runner/work/ParcelRoute/ParcelRoute/app/db.py`
  - `/home/runner/work/ParcelRoute/ParcelRoute/.env.example`
  - `/home/runner/work/ParcelRoute/ParcelRoute/README.md`

No database schema/data was changed.

---

## 2) Hosting choice (free + public URL + no local commands required)

## Chosen option: **Render Web Service (Free plan)**

Why this matches your requirement:
- Connect GitHub repo from dashboard (no terminal needed on your PC).
- Gives public URL like `https://your-service.onrender.com`.
- Works with Flask + Gunicorn.

### Current restrictions verified from available web sources
I verified current limits using available internet sources in this environment:
- Free services can sleep after inactivity (cold start delay on next request).
- Monthly free usage/build limits apply.
- Free tier is fine for student/demo/public project, but not for high-traffic production.

> Note: Direct fetch of official Render pages was blocked in this sandbox, so I used accessible search results.

---

## 3) What you need before deploying

You need accounts for:
1. **GitHub** (repo already exists)
2. **Render** (for hosting)
3. **Aiven** (your MySQL is already there)

Manual account-only tasks are marked clearly below.

---

## 4) Environment variables to set in Render

Set these in **Render Dashboard → Service → Environment**:

| Variable | Example | Required | Notes |
|---|---|---|---|
| `SECRET_KEY` | long random string | Yes | Flask secret |
| `DB_HOST` | `mysql-xxxx.aivencloud.com` | Yes | From Aiven service |
| `DB_PORT` | `12345` | Yes | From Aiven service |
| `DB_USER` | `avnadmin` | Yes | From Aiven service |
| `DB_PASSWORD` | your password | Yes | Keep secret |
| `DB_NAME` | `delivery_logistics` | Yes | Your database name |
| `DB_SSL_MODE` | `required` | Yes (Aiven) | Must be `required` for Aiven |
| `DB_SSL_CA_PEM` | PEM certificate text | Yes (Aiven) | Paste CA cert content directly |

Do **not** set `DB_SSL_CA_PATH` unless you also manage that file path on host.

---

## 5) Aiven MySQL SSL setup (important)

### Manual (requires your Aiven dashboard access)
1. Open **Aiven Console**.
2. Open your MySQL service.
3. Go to connection/security/SSL section.
4. Find the **CA certificate** (PEM format).
5. Copy full PEM text including:
   - `-----BEGIN CERTIFICATE-----`
   - `-----END CERTIFICATE-----`
6. In Render env vars, paste that full text into `DB_SSL_CA_PEM`.

This project now supports `DB_SSL_CA_PEM`, so you do not need local certificate files.

---

## 6) Render deployment steps (dashboard only)

### Manual (requires your Render account access)
1. Log in to Render.
2. Click **New +** → **Web Service**.
3. Connect your GitHub account (if not connected yet).
4. Select repo: `shehrozsultani/ParcelRoute`.
5. Configure service:
   - **Name:** `parcelroute` (or any name)
   - **Runtime:** Python
   - **Branch:** your deployment branch
   - **Build Command:**
     ```powershell
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```powershell
     gunicorn run:app
     ```
6. Choose Free plan.
7. Add all env vars from section 4.
8. Click **Create Web Service**.
9. Wait for first deploy to finish.

---

## 7) Verification checklist (must pass before claiming success)

After Render says "Live":

1. Open your public URL.
2. Home page must load.
3. Open tracking page and test a real number:
   - `100000000`
4. Confirm page shows real route/events/payment blocks.
5. In Render logs, confirm no DB SSL errors.

### How to confirm real Aiven DB is used
- If DB connection is wrong, app will show friendly 503 page from app error handler.
- If DB is correct, tracking details render normally from MySQL data.

**Do not claim deployment success until these checks pass on the live URL.**

---

## 8) Windows PowerShell commands (exact)

You asked for exact PowerShell commands. Use these only if needed.

## Optional: run tests locally before/after deploy
```powershell
cd C:\path\to\ParcelRoute
python -m pip install -r requirements.txt
python -m unittest tests.test_tracking
```

## Optional: quick local run
```powershell
cd C:\path\to\ParcelRoute
python run.py
```
Then open `http://127.0.0.1:5000`

## Optional: generate a strong SECRET_KEY
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> You can deploy from Render dashboard without running commands on your PC.

---

## 9) Troubleshooting

## Error: "Service temporarily unavailable"
Cause: DB connection failed.
Fix:
- Recheck `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Ensure `DB_SSL_MODE=required`
- Re-paste full CA cert into `DB_SSL_CA_PEM`

## Error in logs about SSL/CA
Cause: bad cert text format.
Fix:
- Ensure BEGIN/END certificate lines exist
- Remove extra spaces before lines

## Deploy succeeds but app not reachable
Cause: cold start or failing boot.
Fix:
- Wait 30–60 seconds and retry
- Check Render deploy logs for startup errors
- Confirm start command is exactly `gunicorn run:app`

## Module import errors
Cause: missing packages.
Fix:
- Build command must be exactly `pip install -r requirements.txt`

---

## 10) Test results from this preparation task

I ran the existing project tests:

```powershell
python -m unittest tests.test_tracking
```

Result: **12 tests passed (OK)**.

---

## 11) What still requires your manual action

Because these need your account access, I cannot do them from here:
1. Create/Configure Render Web Service in your account.
2. Read Aiven connection details and CA certificate from your Aiven account.
3. Set Render environment variables.
4. Confirm final live URL behavior in your browser.

Once you complete those, your goal (public working URL using real Aiven DB) should be achievable with this setup.
