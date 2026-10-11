#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/relay-panel"
ENV_FILE="/etc/relay-panel.env"
SERVICE="relay-panel"
NGINX_SITE="/etc/nginx/sites-available/relay-panel"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this installer as root: sudo bash install.sh" >&2
  exit 1
fi
if [[ ! -f /etc/os-release ]] || ! . /etc/os-release || [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This installer supports Ubuntu Server." >&2
  exit 1
fi

read -r -p "Panel port [30333]: " PORT
PORT="${PORT:-30333}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((PORT < 1 || PORT > 65535)); then
  echo "Port must be between 1 and 65535." >&2
  exit 1
fi

read -r -p "Secret panel path [relay]: " PANEL_PATH
PANEL_PATH="${PANEL_PATH:-relay}"
if ! [[ "$PANEL_PATH" =~ ^[A-Za-z0-9_-]{1,64}$ ]] || [[ "${PANEL_PATH,,}" =~ ^(wbhk|webhook|api|p|static)$ ]]; then
  echo "Use 1-64 letters, numbers, hyphens or underscores; reserved paths are not allowed." >&2
  exit 1
fi

DETECTED_PUBLIC_IPV4="$(python3 -c 'import urllib.request; print(urllib.request.urlopen("https://api4.ipify.org", timeout=5).read().decode().strip())' 2>/dev/null || true)"
read -r -p "Enable automatic HTTPS certificate? [Y/n]: " SSL_CHOICE
case "${SSL_CHOICE,,}" in
  ""|y|yes) ENABLE_SSL=yes ;;
  n|no) ENABLE_SSL=no ;;
  *) echo "Enter yes or no." >&2; exit 1 ;;
esac
read -r -p "Public IPv4 address or domain name [${DETECTED_PUBLIC_IPV4:-enter manually}]: " PUBLIC_HOST
PUBLIC_HOST="${PUBLIC_HOST:-$DETECTED_PUBLIC_IPV4}"
if [[ -z "$PUBLIC_HOST" ]] || ! python3 - "$PUBLIC_HOST" <<'PY'
import ipaddress, re, sys
value = sys.argv[1]
try:
    address = ipaddress.ip_address(value)
    valid = address.version == 4 and address.is_global
except ValueError:
    valid = bool(len(value) <= 253 and re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", value))
if not valid:
    raise SystemExit(1)
PY
then
  echo "Enter a public IPv4 address or a fully qualified domain name." >&2
  exit 1
fi
CERT_EMAIL=""
if [[ "$ENABLE_SSL" == "yes" ]]; then
  read -r -p "Certificate contact email (optional): " CERT_EMAIL
fi

read -r -s -p "Choose a strong panel password: " PANEL_PASSWORD
echo
if ((${#PANEL_PASSWORD} < 12)); then
  echo "Use a password with at least 12 characters." >&2
  exit 1
fi

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
LEGACY_WEBHOOK_TOKEN=""
if [[ -f "$ENV_FILE" ]]; then
  LEGACY_WEBHOOK_TOKEN="$(awk -F= '$1 == "LEGACY_WEBHOOK_TOKEN" { value=substr($0, index($0, "=") + 1); found=1; next } $1 == "WEBHOOK_TOKEN" && !found { old=substr($0, index($0, "=") + 1) } END { if (found) print value; else if (old != "") print old }' "$ENV_FILE")"
fi

apt-get update
APT_PACKAGES=(python3 python3-venv python3-pip nginx curl)
if [[ "$ENABLE_SSL" == "yes" ]]; then
  APT_PACKAGES+=(snapd)
fi
DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_PACKAGES[@]}"

SERVER_IPV4="$(curl -4fsS --max-time 10 https://api.ipify.org || true)"
if python3 - "$PUBLIC_HOST" "$SERVER_IPV4" <<'PY'
import ipaddress, socket, sys
host, public_ip = sys.argv[1:]
try:
    address = ipaddress.ip_address(host)
except ValueError:
    try:
        resolved = {item[4][0] for item in socket.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise SystemExit(f"Could not resolve {host}: {exc}")
    if not resolved:
        raise SystemExit(f"No IPv4 A record found for {host}.")
    if public_ip and public_ip not in resolved:
        raise SystemExit(f"{host} resolves to {', '.join(sorted(resolved))}, but this server's public IPv4 is {public_ip}. Fix the DNS A record and rerun.")
    try:
        ipv6_records = socket.getaddrinfo(host, None, family=socket.AF_INET6, type=socket.SOCK_STREAM)
    except OSError:
        ipv6_records = []
    if ipv6_records:
        raise SystemExit(f"{host} has an AAAA record, but this installer configures IPv4 only. Remove the AAAA record or point it to an IPv6-enabled setup before rerunning.")
else:
    if public_ip and str(address) != public_ip:
        raise SystemExit(f"The entered IP is {address}, but this server's public IPv4 is {public_ip}.")
PY
then
  :
else
  echo "Public address check failed. Ensure the domain A record points to this server and rerun." >&2
  exit 1
fi

install -d -m 0755 "$APP_DIR"
install -d -m 0750 "$APP_DIR/data" "$APP_DIR/data/uploads"
if [[ "$ENABLE_SSL" == "yes" ]]; then
  install -d -m 0755 /var/www/letsencrypt/.well-known/acme-challenge
  chmod 0755 /var/www/letsencrypt /var/www/letsencrypt/.well-known /var/www/letsencrypt/.well-known/acme-challenge
fi
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for source in app.py templates.py auth_templates.py panel_ui.py settings_ui.py api_docs.py panel_features.py feature_ui.py auth_workspace.py share_feature.py requirements.txt; do
  install -m 0644 "$SCRIPT_DIR/$source" "$APP_DIR/$source"
done
install -d -m 0755 "$APP_DIR/static"
install -m 0644 "$SCRIPT_DIR/static/panel.css" "$APP_DIR/static/panel.css"
install -m 0644 "$SCRIPT_DIR/static/panel.js" "$APP_DIR/static/panel.js"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

PANEL_PASSWORD_B64="$(printf '%s' "$PANEL_PASSWORD" | base64 -w 0)"
umask 077
cat > "$ENV_FILE" <<EOF
PANEL_PASSWORD_B64=$PANEL_PASSWORD_B64
LEGACY_WEBHOOK_TOKEN=$LEGACY_WEBHOOK_TOKEN
SECRET_KEY=$SECRET_KEY
PORT=$PORT
PANEL_PATH=$PANEL_PATH
CHAT_DATA_DIR=$APP_DIR/data
EOF
chmod 0600 "$ENV_FILE"
unset PANEL_PASSWORD PANEL_PASSWORD_B64 LEGACY_WEBHOOK_TOKEN SECRET_KEY

cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Relay webhook inbox panel
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:$PORT --timeout 120 app:app
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/data

[Install]
WantedBy=multi-user.target
EOF

if [[ "$ENABLE_SSL" == "yes" ]]; then
cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    server_name $PUBLIC_HOST;
    client_max_body_size 1030m;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type text/plain;
    }
    location / { return 404; }
}
EOF
ln -sfn "$NGINX_SITE" /etc/nginx/sites-enabled/relay-panel
nginx -t
systemctl enable nginx
systemctl reload-or-restart nginx

PREFLIGHT_NAME="relay-acme-preflight-$RANDOM"
printf '%s' "$PREFLIGHT_NAME" > "/var/www/letsencrypt/.well-known/acme-challenge/$PREFLIGHT_NAME"
if [[ "$(curl -fsS --max-time 5 -H "Host: $PUBLIC_HOST" "http://127.0.0.1/.well-known/acme-challenge/$PREFLIGHT_NAME" || true)" != "$PREFLIGHT_NAME" ]]; then
  rm -f "/var/www/letsencrypt/.well-known/acme-challenge/$PREFLIGHT_NAME"
  echo "Nginx is not serving the Certbot challenge from /var/www/letsencrypt. Check for another port-80 server block, then rerun." >&2
  exit 1
fi
rm -f "/var/www/letsencrypt/.well-known/acme-challenge/$PREFLIGHT_NAME"

snap install core
snap refresh core
snap install --classic certbot
ln -sf /snap/bin/certbot /usr/local/bin/certbot
CERTBOT_VERSION="$(certbot --version | awk '{print $2}')"
if ! python3 - "$CERTBOT_VERSION" <<'PY'
import sys
parts = tuple(int(piece) for piece in sys.argv[1].split(".")[:2])
if parts < (5, 4):
    raise SystemExit(1)
PY
then
  echo "Certbot 5.4 or newer is required for IP certificates with the webroot plugin." >&2
  exit 1
fi

CERT_ARGS=(certonly --webroot --webroot-path /var/www/letsencrypt --non-interactive --agree-tos)
if [[ -n "$CERT_EMAIL" ]]; then
  CERT_ARGS+=(--email "$CERT_EMAIL")
else
  CERT_ARGS+=(--register-unsafely-without-email)
fi
if python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1])' "$PUBLIC_HOST" 2>/dev/null; then
  certbot "${CERT_ARGS[@]}" --ip-address "$PUBLIC_HOST" --preferred-profile shortlived
else
  certbot "${CERT_ARGS[@]}" --domains "$PUBLIC_HOST"
fi

cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    server_name $PUBLIC_HOST;
    client_max_body_size 1030m;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type text/plain;
    }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl;
    server_name $PUBLIC_HOST;
    client_max_body_size 1030m;
    ssl_certificate /etc/letsencrypt/live/$PUBLIC_HOST/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$PUBLIC_HOST/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF
nginx -t
else
  cat > "$NGINX_SITE" <<EOF
server {
    listen 80;
    server_name $PUBLIC_HOST;
    client_max_body_size 1030m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF
  nginx -t
fi

if [[ "$ENABLE_SSL" == "yes" ]]; then
  install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/relay-panel-nginx <<'EOF'
#!/usr/bin/env sh
nginx -t && systemctl reload nginx
EOF
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/relay-panel-nginx
cat > /etc/systemd/system/relay-certbot-renew.service <<'EOF'
[Unit]
Description=Renew Relay panel TLS certificate

[Service]
Type=oneshot
ExecStart=/snap/bin/certbot renew --quiet
EOF
cat > /etc/systemd/system/relay-certbot-renew.timer <<'EOF'
[Unit]
Description=Daily renewal check for the Relay panel certificate

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF
fi

chown -R www-data:www-data "$APP_DIR/data"
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"
if [[ "$ENABLE_SSL" == "yes" ]]; then
  systemctl enable --now relay-certbot-renew.timer
else
  systemctl disable --now relay-certbot-renew.timer 2>/dev/null || true
fi
systemctl enable nginx
systemctl reload-or-restart nginx
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  if [[ "$ENABLE_SSL" == "yes" ]]; then
    ufw allow 'Nginx Full'
  else
    ufw allow 'Nginx HTTP'
  fi
fi

echo
echo "Relay panel installed and running."
if [[ "$ENABLE_SSL" == "yes" ]]; then
  echo "Panel:   https://$PUBLIC_HOST/$PANEL_PATH/"
  echo "Webhook: https://$PUBLIC_HOST/wbhk/WEBHOOK_PATH"
  echo "TLS certificate renewal: daily systemd timer."
else
  echo "Panel:   http://$PUBLIC_HOST/$PANEL_PATH/"
  echo "Webhook: http://$PUBLIC_HOST/wbhk/WEBHOOK_PATH"
  echo "HTTPS was skipped. You can enable it later by rerunning the installer."
fi
echo "Secrets: $ENV_FILE (root-only)"
