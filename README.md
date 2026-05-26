# Customer Care — Multi-Channel Payment Processing Platform

A Django 6.0 application for processing payments via SMS, calls, and chatbot across Tanzanian mobile money (MOMO) and banking channels.

## Apps

| App | Purpose |
|-----|---------|
| `calls` | IVR/Call handling with menu tree routing |
| `sms_app` | Keyword-based SMS auto-reply system |
| `chatbot` | AI chatbot with knowledge base and embeddable widget |
| `payments` | SMS payment intake → review → authorization → history pipeline |

## Payments App — SMS Parser Engine

The SMS parser extracts structured payment data from unstructured SMS text. It handles two formats:

1. **Standard Command Format** — confidence **95%**
2. **Bank Notification Format** — confidence **80%** (Mkombozi, NBC, NMB, CRDB, Mwanga Hakika, Azania)

If neither matches, a **fallback** extracts whatever it can (confidence **10%**).

---

## Standard Format (Confidence ≥ 95%)

This is the universal format for sending/transferring money. It's simple, human-writable, and parses with 95% confidence.

### Master Template

```
SEND <AMOUNT> <CURRENCY> FROM <SOURCE_TYPE> <SOURCE_ACCT> TO <DEST_TYPE> <DEST_ACCT> [REF=<REFERENCE>]

TRANSFER AMOUNT=<AMOUNT> <CURRENCY> FROM <SOURCE_TYPE> <SOURCE_ACCT> TO <DEST_TYPE> <DEST_ACCT>
```

### Field Rules

| Field | Options | Details |
|-------|---------|---------|
| **Command** | `SEND` or `TRANSFER` | Case-insensitive (`send`, `Send`, `TRANSFER` all work) |
| **Amount** | Any number | Plain: `200000`, with commas: `1,500,000`, with decimals: `50000.00` |
| **Currency** | `TZS`, `USD`, `EUR`, `GBP`, `KES`, `UGX`, `RWF`, `BIF` | Optional — defaults to `TZS` if omitted |
| **Source Type** | `BANK`, `MOMO`, or `INTL` | Uppercase recommended, not case-sensitive |
| **Source Acct** | Any string (no spaces) | Account number, phone number, IBAN |
| **Dest Type** | `BANK`, `MOMO`, or `INTL` | Same as source |
| **Dest Acct** | Any string (no spaces) | Account number, phone number, IBAN |
| **Reference** | `REF=` or `REF:` followed by text | Optional. Underscores become spaces |

### Valid Examples (all score 95%)

| # | Transaction | Example |
|---|-------------|---------|
| 1 | **BANK → MOMO** with REF= | `SEND 200000 TZS FROM BANK 00922820111301 TO MOMO 0755123456 REF=Deposit_for_Kalton` |
| 2 | **MOMO → BANK** with REF= | `SEND 50000 TZS FROM MOMO 0712345678 TO BANK 032175003282 REF=Ulete_na_kalton` |
| 3 | **BANK → BANK** (TRANSFER) | `TRANSFER AMOUNT=4990000 TZS FROM BANK 52810027160 TO BANK 00922820111301` |
| 4 | **INTL → BANK** (USD) | `SEND 100 USD FROM INTL GB12MIDL402234 TO BANK 01J7****200 REF=Western_Union_123` |
| 5 | **MOMO → MOMO** | `SEND 30000 TZS FROM MOMO 0688123456 TO MOMO 0788987654 REF=chakula` |
| 6 | **Comma amount** | `SEND 1,500,000 TZS FROM BANK 00922820111301 TO MOMO 0712345678 REF=Rent_payment` |
| 7 | **REF: colon** | `SEND 45000 TZS FROM MOMO 0688123456 TO BANK 032175003282 REF:School_fees` |
| 8 | **Lowercase** | `send 100000 tzs from bank 00922820111301 to momo 0755123456 ref=airtime` |
| 9 | **No REF** | `SEND 25000 TZS FROM BANK 00922820111301 TO MOMO 0755123456` |
| 10 | **EUR currency** | `SEND 500 EUR FROM INTL DE89370400440532013000 TO BANK 00922820111301 REF=Invoice_2024` |
| 11 | **Extra whitespace** | `SEND  200000  TZS  FROM  BANK  00922820111301  TO  MOMO  0755123456  REF=Deposit` |

---

## How Parser Extracts Fields

The regex captures these groups in order:

1. **Command** — `SEND` or `TRANSFER`
2. **Amount** — digits, optional commas and decimals
3. **Currency** — 3-letter code (optional, defaults to TZS)
4. **From type** — `BANK`, `MOMO`, or `INTL`
5. **From account** — everything until next space
6. **To type** — `BANK`, `MOMO`, or `INTL`
7. **To account** — everything until next space (or end)
8. **Reference** — after `REF=` or `REF:` (optional)

### Parser Output Example

**Input:**
```
SEND 200000 TZS FROM BANK 00922820111301 TO MOMO 0755123456 REF=Deposit_for_Kalton
```

**Output:**
```json
{
  "amount": 200000,
  "currency": "TZS",
  "from_account": "00922820111301",
  "from_account_type": "BANK",
  "to_account": "0755123456",
  "to_account_type": "MOMO",
  "reference": "Deposit_for_Kalton",
  "memo": "Deposit for Kalton",
  "parse_confidence": 0.95,
  "parse_notes": "Parsed as standard command format"
}
```

All 18 SMS templates from `sample sms.txt` pass — **100% score**.

---

## Quick Start (Development)

```bash
# 1. Clone the project
git clone https://github.com/0715173877/customer_care.git
cd customer_care

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database (PostgreSQL)
#    Create a database and user, then copy `.env.example` to `.env` and edit:
#    cp .env.example .env
#    Set: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# 5. Run migrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser

# 7. Start dev server
python manage.py runserver 0.0.0.0:8000
```

- **Payments Intake**: http://127.0.0.1:8000/payments/intake/
- **Payments Review**: http://127.0.0.1:8000/payments/review/
- **Payments Authorize**: http://127.0.0.1:8000/payments/authorize/
- **Payments History**: http://127.0.0.1:8000/payments/history/
- **Admin Panel**: http://127.0.0.1:8000/admin/

---

## Production Deployment (Ubuntu Server)


The `deploy.sh` script fully automates deployment on a fresh Ubuntu 22.04+ server.

### Prerequisites

- Ubuntu 22.04+ server with **root/sudo** access
- Domain name pointing to your server's IP (or use IP directly)

### Step-by-Step

```bash
# 1. SSH into your server
ssh root@your-server

# 2. Clone the repository
git clone https://github.com/0715173877/customer_care.git /opt/customer_care
cd /opt/customer_care

# 3. Make the script executable and run it
chmod +x deploy.sh
sudo ./deploy.sh
```

### What the Script Does

| Step | Action |
|------|--------|
| 1 | Installs Python 3, PostgreSQL, Nginx, UFW firewall |
| 2 | Creates `customer_care` system user |
| 3 | Creates PostgreSQL database `customer_care_db` and user |
| 4 | Sets up Python virtual environment & installs requirements |
| 5 | Generates `.env` with secure `SECRET_KEY` and `DEBUG=False` |
| 6 | Runs `collectstatic` and `migrate` |
| 7 | Prompts for superuser creation |
| 8 | Configures **Gunicorn** systemd service |
| 9 | Configures **Nginx** reverse proxy |
| 10 | Enables **UFW** firewall (SSH, HTTP, HTTPS) |


### After Deployment

```bash
# 1. Configure AI and Twilio (edit .env with your keys)
sudo nano /opt/customer_care/.env

# 2. Set up HTTPS with Let's Encrypt
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo certbot --nginx -d your-domain.com

# 3. Log into the admin panel
#    http://your-domain.com/admin/

# Useful commands
sudo journalctl -u gunicorn -f     # Watch gunicorn logs
sudo tail -f /var/log/nginx/access.log
sudo systemctl restart gunicorn    # Restart after code changes
sudo systemctl restart nginx       # Restart after nginx config changes
```

### Architecture

```
Internet → Nginx (port 80/443)
                │
                ▼
         Gunicorn (port 8000)
                │
                ▼
           Django App
                │
                ▼
          PostgreSQL (port 5432)
```

