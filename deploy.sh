#!/usr/bin/env bash
# ============================================================================
#  Deploy Script — Customer Care Automation Platform
#  Kalton Investment Money Transfer Services
#
#  Usage:
#    1. SSH into your server and clone the repo:
#       git clone https://github.com/0715173877/customer_care.git /opt/customer_care
#    2. cd /opt/customer_care
#    3. chmod +x deploy.sh  &&  sudo ./deploy.sh
#

#  What it does:
#    - Installs system dependencies (Python 3, PostgreSQL, nginx)
#    - Creates a dedicated Linux user (customer_care)
#    - Creates PostgreSQL database and user
#    - Sets up a Python virtual environment
#    - Installs Python requirements
#    - Runs migrations, collects static files
#    - Creates a superuser (interactive prompt)
#    - Configures gunicorn systemd service
#    - Configures nginx reverse proxy
#    - Enables firewall (ufw)
# ============================================================================

set -euo pipefail

# ── Colour helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Configuration — ADJUST THESE for your server ──────────────────────────
PROJECT_DIR="/opt/customer_care"
PROJECT_USER="customer_care"
PROJECT_REPO="https://github.com/0715173877/customer_care.git"

DJANGO_SETTINGS_MODULE="customer_care.settings"
DOMAIN="kaltoninvestment.co.tz"           # Change to your domain or server IP
GUNICORN_WORKERS=4
GUNICORN_PORT=8000

# PostgreSQL
DB_NAME="customer_care_db"
DB_USER="customer_care_user"
DB_PASSWORD="care_pass_2026"              # ⚠️ CHANGE in production!

# Django superuser (you will be prompted to set the password)
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"

# ── Sanity checks
[[ $EUID -ne 0 ]] && err "This script must be run as root (use sudo)."
[[ ! -d "$PROJECT_DIR" ]] && err "Project directory $PROJECT_DIR not found. Copy your files there first."

cd "$PROJECT_DIR"

# ── 1. System packages
info "Updating system packages..."
apt-get update -y && apt-get upgrade -y 2>&1

info "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-client \
    libpq-dev \
    nginx \
    git \
    curl \
    ufw 2>&1

ok "System dependencies installed."

# ── 2. Create project user
if id "$PROJECT_USER" &>/dev/null; then
    warn "User '$PROJECT_USER' already exists — skipping."
else
    useradd --system --user-group --no-create-home --shell /usr/sbin/nologin "$PROJECT_USER"
    info "Created system user: $PROJECT_USER"
fi

# ── 3. PostgreSQL setup
info "Starting PostgreSQL..."
systemctl enable postgresql 2>&1
systemctl start postgresql 2>&1

if sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" 2>/dev/null | grep -q 1; then
    warn "PostgreSQL user '$DB_USER' already exists — skipping."
else
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>&1
    ok "PostgreSQL user created: $DB_USER"
fi

if sudo -u postgres psql -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" 2>/dev/null | grep -q 1; then
    warn "Database '$DB_NAME' already exists — skipping."
else
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>&1
    ok "Database created: $DB_NAME (owner: $DB_USER)"
fi

# Allow the project user to create test databases (needed for Django tests)
sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;" 2>&1

# ── 4. Python virtual environment
info "Setting up Python virtual environment..."
if [[ ! -d venv ]]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip 2>&1

if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt 2>&1
else
    pip install Django djangorestframework psycopg2-binary python-decouple twilio google-generativeai gunicorn whitenoise 2>&1
fi
ok "Python dependencies installed."

# ── 5. Environment file (.env)
if [[ ! -f .env ]]; then
    info "Creating .env file..."
    NEW_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    cat > .env <<EOF
# Django
SECRET_KEY=$NEW_SECRET_KEY
DEBUG=False

# PostgreSQL Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432

# Google Gemini AI (optional — set your API key to enable AI responses)
GEMINI_API_KEY=

# Twilio (optional — set for SMS & voice integration)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# CSRF cookies — set to True once HTTPS is configured
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
EOF

    chown "$PROJECT_USER":"$PROJECT_USER" .env
    chmod 600 .env
    ok "Created .env with secure SECRET_KEY (DEBUG=False)"
else
    warn ".env already exists — ensure DEBUG=False in production."
    # Ensure .env is owned by the project user
    chown "$PROJECT_USER":"$PROJECT_USER" .env
    chmod 600 .env
fi

# ── 6. Static files (using whitenoise)
info "Collecting static files..."
mkdir -p staticfiles
python manage.py collectstatic --noinput --clear 2>&1
ok "Static files collected."

# ── 7. Database migrations
info "Running database migrations..."
python manage.py migrate --noinput 2>&1
ok "Migrations complete."

# ── 8. Create superuser (interactive)
info "Creating Django superuser (you will be prompted for password)..."
python manage.py createsuperuser --username="$ADMIN_USERNAME" --email="$ADMIN_EMAIL" 2>&1 || true

# ── 9. Gunicorn systemd service
info "Configuring Gunicorn systemd service..."

cat > /etc/systemd/system/gunicorn.service <<UNIT
[Unit]
Description=gunicorn daemon — Customer Care Automation
After=network.target postgresql.service

[Service]
User=$PROJECT_USER
Group=$PROJECT_USER
WorkingDirectory=$PROJECT_DIR
Environment="DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \
    --workers $GUNICORN_WORKERS \
    --bind 127.0.0.1:$GUNICORN_PORT \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    customer_care.wsgi:application

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

mkdir -p /var/log/gunicorn
chown -R "$PROJECT_USER":"$PROJECT_USER" /var/log/gunicorn
chown -R "$PROJECT_USER":"$PROJECT_USER" "$PROJECT_DIR"

systemctl daemon-reload
systemctl enable gunicorn 2>&1
systemctl start gunicorn 2>&1
ok "Gunicorn service started."

# ── 10. Nginx reverse proxy
info "Configuring nginx..."

cat > /etc/nginx/sites-available/customer_care <<NGINX
server {
    listen 80;
    server_name $DOMAIN;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:$GUNICORN_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/customer_care /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t 2>&1 && systemctl restart nginx 2>&1
ok "Nginx configured and running."

# ── 11. Firewall
info "Configuring UFW firewall..."
ufw --force reset 2>&1
ufw default deny incoming 2>&1
ufw default allow outgoing 2>&1
ufw allow ssh 2>&1
ufw allow http 2>&1
ufw allow https 2>&1
ufw --force enable 2>&1
ok "Firewall enabled (SSH, HTTP, HTTPS)."

# ── 12. Health check
sleep 2
if systemctl is-active --quiet gunicorn && systemctl is-active --quiet nginx; then
    ok "Both gunicorn and nginx are running."
else
    warn "Check service status: systemctl status gunicorn nginx"
fi

# ── Done
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "  Web:      ${CYAN}http://$DOMAIN${NC}"
echo -e "  Admin:    ${CYAN}http://$DOMAIN/admin/${NC}"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo -e "    1. Edit  .env  to set your GEMINI_API_KEY and Twilio credentials"
echo -e "    2. Log into the admin panel to configure:"
echo -e "       - Call menu options (IVR)"
echo -e "       - SMS keyword auto-replies"
echo -e "       - Chatbot knowledge base entries"
echo -e "       - Payment transfer management"
echo -e "    3. For HTTPS, run:"
echo -e "       ${CYAN}sudo snap install core; sudo snap refresh core${NC}"
echo -e "       ${CYAN}sudo snap install --classic certbot${NC}"
echo -e "       ${CYAN}sudo certbot --nginx -d $DOMAIN${NC}"
echo ""
echo -e "  ${YELLOW}Useful commands:${NC}"
echo -e "     sudo journalctl -u gunicorn -f     # live gunicorn logs"
echo -e "     sudo tail -f /var/log/nginx/access.log"
echo -e "     sudo systemctl restart gunicorn    # after code changes"
echo -e "     sudo systemctl restart nginx       # after nginx config changes"
echo ""
echo -e "${GREEN}============================================================${NC}"
