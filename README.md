# relay
A small, self-hosted Python inbox for managing multiple webhook channels, managing app licensing and file sharing


## Install on Ubuntu Server

Point the domain's DNS A record at the server's public IPv4 address first (when using a domain). Copy this directory to Ubuntu Server, then run:

```bash
sudo bash install.sh
```

The installer asks whether to enable automatic HTTPS, then asks for the public host, panel port (default `30333`), secret path (default `relay`), and panel password. It detects the server's public IPv4 and uses it as the default host; enter a domain instead if you have one. The app listens only on localhost behind Nginx. With HTTPS enabled, the panel opens at `https://HOST/relay/` and Certbot renews the certificate automatically. If you skip HTTPS, Nginx serves it at `http://HOST/relay/` and Certbot is not installed. The webhook API and public shares stay at `/wbhk/PATH` and `/p/SHARE_PATH` on the same host.

For a domain, create its DNS A record before running the installer. This installer configures IPv4; remove any AAAA record for the domain. It checks that the domain resolves to this server's detected public IPv4; it cannot change records at your registrar because it has no DNS provider credentials. The installer opens the applicable Nginx ports in UFW when UFW is already enabled; the backend port stays bound to localhost.

If you raise the message cap above 100 MB, also raise the reverse proxy’s request body limit to match.

## Share text and files

Open **Shares** in the panel to publish a text paste, a file, or both at `/p/YOUR_PATH`. Share links are public to anyone who has the URL. The custom path must be unique and contain 3–63 letters, numbers, hyphens, or underscores. Each share uses the panel's current combined message size limit. Shares have no automatic expiry; delete a share in the panel to revoke its link.

Uploaded files are always downloaded as attachments. Text is HTML-escaped and displayed as plain text. The public share page is marked `noindex`; use HTTPS and share the link only with people who should see its contents.

The share form accepts either text, a file, or both, with the same combined size cap used for webhook messages.

## Webhook formats

JSON:

```bash
curl -X POST 'https://SERVER_IP/wbhk/PATH' \
  -H 'Content-Type: application/json' \
  -d '{"id":"0023","message":"Build finished","username":"build-bot"}'
```

Every message requires an `id` and non-empty `message`. IDs are strings so leading zeroes are preserved. `username` and repeated `files` fields are optional. Different IDs remain separate users even when they share a username.

```bash
curl -X POST 'https://SERVER_IP/wbhk/PATH' \
  -F 'id=0023' -F 'message=Logs attached' -F 'username=build-bot' \
  -F 'files=@build.zip' -F 'files=@preview.png'
```

The panel shows incoming messages and previews common images and videos. Files can be downloaded by signed-in panel users. Messages and uploads are kept under `/opt/relay-panel/data` by default.

## Send messages with Python

Use the included `send_to_webhook.py` script to post text and files. Edit `WEBHOOK_URL`, `USER_ID`, `MESSAGE`, and optionally `USERNAME` and `FILES` at the top of the file, then run it with Python. It uses only Python's standard library:

```bash
python send_to_webhook.py
```

Add one or more file paths to `FILES`, for example `FILES = ["app.log", "screenshots.zip"]`. The script checks the combined text and file size before sending. If you change the panel’s message cap, set `MAX_MESSAGE_MB` to the same value.

## Telegram notifications and backups

Create a Telegram bot, open a chat with it, and press **Start**. In Relay Settings, enter the bot token and the destination chat ID, then save and use **Test bot and send a test message** to verify both values. The token stays hidden in the settings page and is stored in the Relay database.

Relay uses `pyTelegramBotAPI` (`telebot`) for bot calls. It sends an alert when a sender ID first appears in a webhook. On that user's message page, **Send user backup to Telegram** sends the user's full text history and attachments. Files larger than 45 MiB are split into numbered parts; the bot posts a note explaining how to concatenate them in order. Each part is uploaded separately to stay below Telegram's hosted Bot API per-document cap, without changing Telegram's other chat or rate limits.

To upgrade an existing Ubuntu install and configure the secret path and HTTPS proxy, copy the new project files to the server and rerun the installer. Keep `/opt/relay-panel/data` to preserve messages, users, and shares. The installer rewrites its systemd and Nginx configuration, checks DNS, obtains or reuses the certificate, and restarts the service.

```bash
sudo /opt/relay-panel/venv/bin/pip install -r /opt/relay-panel/requirements.txt
sudo systemctl restart relay-panel
```

## Auth apps and API

Open **Auth** in the panel to create an app. Each app gets its own server API key, shown once at creation (or key rotation). Each user configured for product-key auth receives a different product key; it is shown once with that user's name and can be individually replaced. Create users with username and password, product key, or both; optionally set an expiration time, disable accounts, reset passwords, or delete users. App and user deletion require confirmation. Passwords and API/product keys are stored as hashes.

The **API Docs** tab includes curl and Python examples. Credential checks use `POST /api/auth/APP_ID/login` with `Authorization: Bearer APP_API_KEY` and a JSON body. Password accounts send `username` and `password`; product-key accounts send `product_key`; accounts configured for both must send all three. A successful response confirms the credentials and returns the username and expiration time. This endpoint checks credentials only; it does not issue a session or access token. Keep app API keys on a trusted server and use HTTPS.

## Service commands

Auth users have a single license duration: 7, 30, 90, or 365 days, or lifetime. Timed licenses begin on first successful authentication and calculate their end date automatically. Changing an activated license sets its duration from today; an unactivated license still starts on first login. Individual edits also accept a custom number of days (0 means lifetime). Existing end dates are preserved until you change the license. Use the app's search and status/method filters to find accounts, select users for bulk enable/disable/extend/delete, or generate up to 100 unique accounts at once. Generated passwords and product keys are shown once.

Webhook badges and user counts refresh every five seconds while the panel is visible. New messages show an update banner so you can refresh the feed when ready.

Settings includes global disk space, panel data usage, and optional message retention. Retention is disabled by default; enabling it removes old messages and their attachments across all webhooks. Auth accounts are retained. You can also explicitly clean up messages older than a chosen age.

The server checks storage every five minutes. When the data volume has less than 10 GiB free, automatic backups (enabled by default) send the 20 newest webhook users, ordered by first appearance, to the configured Telegram bot chat. Each backup contains a JSON history manifest and all its attachments; large files and manifests are split into parts. Unchanged completed backups are skipped, updated users are resent, and failures retry on a later check. An incomplete user backup can be partly duplicated on retry. Local data is retained; sending a backup does not reclaim disk space. Automatic retention pauses below the threshold. This is a user-history export, not a full database or auth-account backup. Keep the server running and configure Telegram to enable delivery.

```bash
sudo systemctl status relay-panel
sudo systemctl restart relay-panel
sudo journalctl -u relay-panel -f
```

Webhook senders are limited to 3 accepted messages per sender IP across all webhooks every 30 seconds. Change the panel password and message size limit from the panel’s Settings page. For service-level secrets in `/etc/relay-panel.env`, restart the service after editing. Back up `/opt/relay-panel/data` to preserve messages and attachments.
