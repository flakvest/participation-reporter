# MARS Platoon Participation Reporter — Specification

## 1. Purpose

A web application hosted on a Debian 12 VPS that ingests Army MARS RRI response strips (1PLTPARTRPT and 2PLTPARTRPT), logs them per callsign, and provides per-platoon dashboards for leadership to track who has reported.

## 2. RRI Format

Both strips have identical field structure:

```
1PLTPARTRPT/Call Sign(X)/Month(JAN,FEB,...)/All MARS Equipment and Software
Operational(YES,NO)/Possess Required MARS Skills(YES,NO)/Total HF Operational
Hours(#)/J0G Hours in the HF Total(#)/GST or Message Center Hours in the HF
Total(#)/Other HF hours including AFMARS or other regions and SHARES in the HF
Total(#)/Sum of Total HF Operational Hours plus other MARS Hours such as Admin
and Training and Equip maintenance(#)/Notes and Training Needs(X)//
```

Same for 2PLTPARTRPT.

### Parsing Rules

- Strips are delimited by `//`
- Format: `SET_IDENTIFIER/VALUE1/VALUE2/...//`
- Field count must match the expected count (11 data fields)
- Set identifier must be exactly `1PLTPARTRPT` or `2PLTPARTRPT`
- YES/NO fields validated against allowed values
- Hour fields (`#` mask) validated as numeric
- Duplicate detection: same callsign + same month + same platoon = flag as duplicate

## 3. Submission Methods

### A. File Upload
User uploads a `.txt` file (or `.csv`) containing one or more response strips. The file is parsed and all valid strips are ingested in batch.

### B. Paste Form
User pastes raw strip text into a textarea. Handles single or multiple strips (consolidation messages).

### C. API Endpoint (future)
An authenticated POST endpoint so automated systems can push strips directly.

## 4. User Model

| Concept | Detail |
|---|---|
| Registration | Self-register with callsign and password |
| Identity | One account = one callsign |
| Platoon | Assigned on registration: 1st PLT or 2nd PLT |
| Roles | **Operator** — submits own reports, sees own history |
| | **Platoon Leader** — sees all reports for their platoon, sees who has/hasn't reported |
| | **Admin** — full access, can manage users |
| 2FA | Optional TOTP (Google Authenticator, Authy). Enrolled via Settings page. |

### 2FA Login Flow

1. User enters callsign + password → POST /login
2. If password is valid AND user has 2FA enabled:
   - Issue short-lived "pre-auth" JWT (5 min, scope="totp_required")
   - Redirect to GET /login/2fa
3. User enters TOTP code → POST /login/2fa (includes pre-auth token)
4. If code is valid: issue real JWT, redirect to /dashboard
5. If code is invalid: show error, stay on /login/2fa

## 5. Data Model

### Users table
- id, callsign (unique), password_hash, platoon, role, created_at
- **totp_secret** (nullable text) — the TOTP seed
- **totp_enabled** (boolean, default false) — whether 2FA is active

### Reports table
- id, platoon, callsign, month, equipment_ok (bool), skills_ok (bool),
  total_hf_hours (int), j0g_hours (int), gst_hours (int), other_hf_hours (int),
  total_mars_hours (int), notes (text), source (file_upload|paste|api),
  duplicate_flag (bool), created_at, submitted_by (user_id)

### Unique constraint
- (platoon, callsign, month) — one report per callsign per platoon per month

## 6. Features

### Dashboard Views
- **Per-platoon summary**: how many operators have reported this month vs outstanding
- **Monthly rollup**: what % of platoon submitted each month
- **Individual operator history**: all submissions for a given callsign over time
- **Export to CSV**: filtered by platoon, month, date range

### Report Management
- View submitted reports (filterable by platoon, month, callsign)
- Flag/unflag duplicates
- Delete reports (admin only)

### 2FA Settings
- Enable: generate TOTP secret, display QR code, require confirmation code
- Disable: require current TOTP code to disable
- Status indicator on Settings page

## 7. Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy + Alembic |
| Frontend | Jinja2 templates + htmx |
| Auth | bcrypt + JWT cookies |
| 2FA | pyotp (TOTP) |

## 8. RRI Parser Module

A standalone parser function that accepts raw text, splits on `//`, validates each strip against the field definitions, and returns parsed reports or errors.
