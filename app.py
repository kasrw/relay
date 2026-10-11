import os
import secrets
import sqlite3
import time
import base64
import re
import hashlib
import logging
import io
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

import telebot
from telebot import util as telebot_util

from flask import Flask, jsonify, redirect, render_template_string, request, send_file, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from auth_templates import AUTH_APP_PAGE, AUTH_DOCS_PAGE, AUTH_HOME_PAGE
from templates import LOGIN_HTML_NEW, MESSAGE_CENTER, PANEL_HOME, SETTINGS_PAGE
from panel_ui import enhance_page

ROOT = Path(__file__).resolve().parent
PANEL_PATH = os.environ.get("PANEL_PATH", "relay").strip("/")
if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", PANEL_PATH) or PANEL_PATH.lower() in {"wbhk", "webhook", "api", "p", "static"}:
    raise RuntimeError("PANEL_PATH must be 1-64 letters, numbers, '_' or '-', and cannot be a reserved public path")
PANEL_PREFIX = "/" + PANEL_PATH
DATA_DIR = Path(os.environ.get("CHAT_DATA_DIR", ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "messages.sqlite3"
DEFAULT_MESSAGE_LIMIT_MB = 100
MAX_MESSAGE_LIMIT_MB = 1024
MESSAGE_RATE_LIMIT = 3
MESSAGE_RATE_WINDOW_SECONDS = 30
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)


class PanelMountMiddleware:
    """Mount private panel routes under PANEL_PATH while keeping public APIs at root."""

    def __init__(self, application, prefix):
        self.application = application
        self.prefix = prefix.rstrip("/")

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path == self.prefix or path.startswith(self.prefix + "/"):
            environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + self.prefix
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
        return self.application(environ, start_response)


app.wsgi_app = PanelMountMiddleware(app.wsgi_app, PANEL_PREFIX)
app.secret_key = os.environ.get("SECRET_KEY", "")
app.config["MAX_CONTENT_LENGTH"] = MAX_MESSAGE_LIMIT_MB * 1024 * 1024 + 1024 * 1024
logger = logging.getLogger("relay.telegram")
TELEGRAM_CHUNK_BYTES = 45 * 1024 * 1024


class RateLimitExceeded(Exception):
    """Raised when a sender exceeds the webhook message rate limit."""


# Configuration and database helpers
def config_value(key, default=""):
    return os.environ.get(key, default)


def panel_password():
    encoded = config_value("PANEL_PASSWORD_B64")
    if encoded:
        try:
            return base64.b64decode(encoded).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
    return config_value("PANEL_PASSWORD")


def verify_panel_password(supplied):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key='panel_password_hash'").fetchone()
    if row:
        try:
            return check_password_hash(row["value"], supplied)
        except (ValueError, TypeError):
            return False
    configured = panel_password()
    return bool(configured) and secrets.compare_digest(supplied, configured)


def render_panel(template, **context):
    return render_template_string(enhance_page(template), **context)


def message_limit_mb():
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key='max_message_mb'").fetchone()
    raw = row["value"] if row else config_value("MAX_MESSAGE_MB", str(DEFAULT_MESSAGE_LIMIT_MB))
    try:
        return min(MAX_MESSAGE_LIMIT_MB, max(1, int(raw)))
    except (TypeError, ValueError):
        return DEFAULT_MESSAGE_LIMIT_MB


def message_limit_bytes():
    return message_limit_mb() * 1024 * 1024


def setting_value(key, default=""):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def telegram_bot(token):
    return telebot.TeleBot(token, threaded=False)


def telegram_call(token, callback, *args, **kwargs):
    """Normalize telebot errors and redact credentials before surfacing them."""
    try:
        return callback(*args, **kwargs)
    except Exception as exc:
        detail = getattr(exc, "description", None) or str(exc)
        if "Connection" in detail or "timed out" in detail.lower():
            detail = "Could not connect to Telegram. Check the server's internet connection."
        raise RuntimeError(str(detail).replace(token, "[hidden]")) from None


def telegram_send_text(token, bot, chat_id, text):
    for part in telebot_util.smart_split(text, chars_per_string=3900):
        telegram_call(token, bot.send_message, chat_id, part)


def telegram_send_file(token, bot, chat_id, path, filename, size):
    """Send a file directly or as numbered parts below Telegram's per-file cap."""
    part_count = max(1, (size + TELEGRAM_CHUNK_BYTES - 1) // TELEGRAM_CHUNK_BYTES)
    if part_count == 1:
        with Path(path).open("rb") as source:
            telegram_call(token, bot.send_document, chat_id, source, visible_file_name=filename)
        return 1

    telegram_send_text(
        token,
        bot,
        chat_id,
        f"Large attachment: {filename}\nOriginal size: {size} bytes\nParts: {part_count}\n"
        f"To restore it, download all files named {filename}.partNNNN-of-NNNN and concatenate them in numeric order.",
    )
    sent_parts = 0
    with Path(path).open("rb") as source:
        for part_number in range(1, part_count + 1):
            chunk = source.read(TELEGRAM_CHUNK_BYTES)
            part_name = f"{filename}.part{part_number:04d}-of-{part_count:04d}"
            payload = io.BytesIO(chunk)
            telegram_call(
                token,
                bot.send_document,
                chat_id,
                payload,
                visible_file_name=part_name,
                caption=f"Part {part_number}/{part_count} of {filename}"[:900],
            )
            sent_parts += 1
    return sent_parts


def telegram_new_user_notice(webhook_id, sender_id, username, message, file_count):
    token = setting_value("telegram_bot_token")
    chat_id = setting_value("telegram_chat_id")
    if not token or not chat_id:
        return
    with db() as con:
        hook = con.execute("SELECT name,slug FROM webhooks WHERE id=?", (webhook_id,)).fetchone()
    if not hook:
        return
    text = f"New webhook user\nWebhook: {hook['name']} (/wbhk/{hook['slug']})\nID: {sender_id}\nUsername: {username or f'User {sender_id}'}\nFirst message: {message[:2800]}"
    if file_count:
        text += f"\nAttachments: {file_count}"
    try:
        telegram_send_text(token, telegram_bot(token), chat_id, text)
    except RuntimeError as exc:
        logger.warning("Telegram new-user notification failed: %s", exc)


def webhook_base_url():
    scheme = "https" if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https" else "http"
    return f"{scheme}://{request.host}"


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("CREATE TABLE IF NOT EXISTS webhooks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, slug TEXT UNIQUE, token TEXT NOT NULL UNIQUE, created REAL NOT NULL, last_seen_message_id INTEGER NOT NULL DEFAULT 0)")
        con.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS shares (id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE COLLATE NOCASE, title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '', disk_name TEXT, filename TEXT, mime TEXT, size INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS auth_apps (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, api_key_hash TEXT NOT NULL UNIQUE, created REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS auth_users (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER NOT NULL REFERENCES auth_apps(id) ON DELETE CASCADE, username TEXT NOT NULL, auth_mode TEXT NOT NULL CHECK(auth_mode IN ('password','product_key','both')), password_hash TEXT, product_key_hash TEXT UNIQUE, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','disabled')), created REAL NOT NULL, expires_at REAL, last_login REAL)")
        con.execute("CREATE TABLE IF NOT EXISTS auth_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, app_id INTEGER NOT NULL, remote_ip TEXT NOT NULL, attempted REAL NOT NULL)")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS auth_users_app_username_idx ON auth_users(app_id, username COLLATE NOCASE)")
        con.execute("CREATE INDEX IF NOT EXISTS auth_users_app_id_idx ON auth_users(app_id,id)")
        auth_columns = {row[1] for row in con.execute("PRAGMA table_info(auth_users)")}
        for column, definition in (("duration_days", "INTEGER"), ("activated_at", "REAL")):
            if column not in auth_columns:
                con.execute(f"ALTER TABLE auth_users ADD COLUMN {column} {definition}")
        con.execute("CREATE INDEX IF NOT EXISTS auth_attempts_lookup_idx ON auth_attempts(app_id,remote_ip,attempted)")
        con.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, webhook_id INTEGER REFERENCES webhooks(id) ON DELETE CASCADE, sender_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL, sender_ip TEXT NOT NULL DEFAULT '')")
        columns = {row[1] for row in con.execute("PRAGMA table_info(messages)").fetchall()}
        if "webhook_id" not in columns:
            con.execute("ALTER TABLE messages ADD COLUMN webhook_id INTEGER REFERENCES webhooks(id) ON DELETE CASCADE")
        if "sender_id" not in columns:
            con.execute("ALTER TABLE messages ADD COLUMN sender_id TEXT NOT NULL DEFAULT ''")
            con.execute("UPDATE messages SET sender_id=source WHERE sender_id=''")
        if "sender_ip" not in columns:
            con.execute("ALTER TABLE messages ADD COLUMN sender_ip TEXT NOT NULL DEFAULT ''")
        hook_columns = {row[1] for row in con.execute("PRAGMA table_info(webhooks)").fetchall()}
        if "slug" not in hook_columns:
            con.execute("ALTER TABLE webhooks ADD COLUMN slug TEXT")
        if "last_seen_message_id" not in hook_columns:
            con.execute("ALTER TABLE webhooks ADD COLUMN last_seen_message_id INTEGER NOT NULL DEFAULT 0")
        for hook in con.execute("SELECT id FROM webhooks WHERE slug IS NULL").fetchall():
            con.execute("UPDATE webhooks SET slug=? WHERE id=?", ("legacy-" + secrets.token_hex(8), hook["id"]))
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS webhooks_slug_unique_idx ON webhooks(slug)")
        con.execute("CREATE TABLE IF NOT EXISTS attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE, name TEXT NOT NULL, disk_name TEXT NOT NULL, mime TEXT NOT NULL, size INTEGER NOT NULL)")
        migrated = con.execute("SELECT value FROM settings WHERE key='legacy_webhook_migrated'").fetchone()
        if not migrated:
            old_token = config_value("WEBHOOK_TOKEN") or config_value("LEGACY_WEBHOOK_TOKEN")
            if old_token:
                row = con.execute("SELECT id FROM webhooks WHERE token=?", (old_token,)).fetchone()
                if not row:
                    cur = con.execute("INSERT INTO webhooks(name,slug,token,created) VALUES(?,?,?,?)", ("Imported webhook", "legacy-" + secrets.token_hex(8), old_token, time.time()))
                    webhook_id = cur.lastrowid
                else:
                    webhook_id = row["id"]
                con.execute("UPDATE messages SET webhook_id=? WHERE webhook_id IS NULL", (webhook_id,))
            con.execute("INSERT INTO settings(key,value) VALUES('legacy_webhook_migrated','1')")
        con.execute("CREATE INDEX IF NOT EXISTS messages_webhook_id_idx ON messages(webhook_id,id)")
        con.execute("CREATE INDEX IF NOT EXISTS messages_webhook_sender_idx ON messages(webhook_id,sender_id,id)")
        con.execute("CREATE INDEX IF NOT EXISTS messages_sender_ip_created_idx ON messages(sender_ip,created)")


# Request security and panel authentication
@app.before_request
def ensure_ready():
    if request.script_root.rstrip("/") != PANEL_PREFIX and not request.path.startswith(("/wbhk/", "/webhook/", "/api/auth/", "/p/")):
        return "Not found", 404
    if not app.secret_key:
        return "Server is not configured. Set SECRET_KEY in the environment.", 503
    init_db()
    start_storage_monitor()
    app.config["MAX_CONTENT_LENGTH"] = message_limit_bytes() + 1024 * 1024
    if request.method in ("GET", "HEAD"):
        session.setdefault("csrf", secrets.token_urlsafe(32))
    elif request.path != "/login" and not request.path.startswith(("/webhook/", "/wbhk/", "/api/auth/")):
        supplied = request.form.get("csrf", "") or request.headers.get("X-CSRF-Token", "")
        if not supplied or not secrets.compare_digest(supplied, session.get("csrf", "")):
            return "Invalid or expired form token. Reload the page and try again.", 400


def is_logged_in():
    return session.get("logged_in") is True


@app.after_request
def prevent_panel_caching(response):
    if not request.path.startswith(("/static/", "/wbhk/", "/webhook/", "/api/auth/")):
        response.headers["Cache-Control"] = "no-store"
    return response


# Login and panel routes
@app.get("/login")
def login_page():
    return render_panel(LOGIN_HTML_NEW, error="", csrf=session.get("csrf", ""))


@app.post("/login")
def login():
    password = panel_password()
    if not password:
        with db() as con:
            changed = con.execute("SELECT 1 FROM settings WHERE key='panel_password_hash'").fetchone()
        if not changed:
            return "PANEL_PASSWORD is not configured.", 503
    supplied = request.form.get("password", "")
    if verify_panel_password(supplied):
        session.clear()
        session["logged_in"] = True
        session["csrf"] = secrets.token_urlsafe(32)
        return redirect(url_for("home"))
    session["csrf"] = secrets.token_urlsafe(32)
    return render_panel(LOGIN_HTML_NEW, error="Password did not match. Try again.", csrf=session["csrf"]), 401


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.get("/")
def home():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        hooks = con.execute("""
            SELECT w.id, w.name, w.slug, w.token, w.created,
                   COUNT(DISTINCT m.sender_id) AS user_count,
                   (SELECT COUNT(*) FROM messages unread
                    WHERE unread.webhook_id = w.id
                      AND unread.id > w.last_seen_message_id) AS unread_count
            FROM webhooks w
            LEFT JOIN messages m ON m.webhook_id = w.id
            GROUP BY w.id
            ORDER BY w.created DESC, w.id DESC
        """).fetchall()
    items = [{**dict(h), "url": webhook_base_url() + "/wbhk/" + h["slug"]} for h in hooks]
    return render_panel(PANEL_HOME, webhooks=items, csrf=session.get("csrf", ""))


def webhook_row(webhook_id):
    with db() as con:
        return con.execute("SELECT id,name,slug,token,created FROM webhooks WHERE id=?", (webhook_id,)).fetchone()


# Webhook and settings management
@app.post("/webhooks/create")
def create_webhook():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    name = (request.form.get("name") or "").strip()[:80]
    slug = (request.form.get("slug") or "").strip().lower()
    if not name or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", slug):
        return redirect(url_for("home", error="invalid"))
    token = secrets.token_urlsafe(36)
    with db() as con:
        try:
            con.execute("INSERT INTO webhooks(name,slug,token,created) VALUES(?,?,?,?)", (name, slug, token, time.time()))
        except sqlite3.IntegrityError:
            return redirect(url_for("home", error="duplicate"))
    return redirect(url_for("home", created=slug))


@app.post("/webhooks/<int:webhook_id>/rename")
def rename_webhook(webhook_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    name = (request.form.get("name") or "").strip()[:80]
    if not name:
        return redirect(url_for("home", error="empty-name"))
    with db() as con:
        con.execute("UPDATE webhooks SET name=? WHERE id=?", (name, webhook_id))
    return redirect(url_for("home"))


@app.get("/settings")
def settings_page():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return render_panel(
        SETTINGS_PAGE,
        csrf=session.get("csrf", ""),
        message_mb=message_limit_mb(),
        max_limit_mb=MAX_MESSAGE_LIMIT_MB,
        saved=request.args.get("saved", ""),
        error=request.args.get("error", ""),
        telegram_configured=bool(setting_value("telegram_bot_token") and setting_value("telegram_chat_id")),
        telegram_chat_id=setting_value("telegram_chat_id"),
        telegram_status=request.args.get("telegram", ""),
        telegram_error=request.args.get("telegram_error", ""),
        storage=storage_summary(),
        storage_notice=request.args.get("storage_notice", ""),
    )


@app.post("/settings/telegram")
def save_telegram_settings():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    submitted_token = request.form.get("bot_token", "").strip()
    chat_id = request.form.get("chat_id", "").strip()
    current_token = setting_value("telegram_bot_token")
    # A blank token keeps the saved secret. Clear both fields to disable the integration.
    if not submitted_token and not chat_id:
        with db() as con:
            con.execute("DELETE FROM settings WHERE key IN ('telegram_bot_token','telegram_chat_id')")
        return redirect(url_for("settings_page", telegram="disabled"))
    token = submitted_token or current_token
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,}", token) or not chat_id or len(chat_id) > 128:
        return redirect(url_for("settings_page", telegram="invalid"))
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES('telegram_bot_token',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (token,))
        con.execute("INSERT INTO settings(key,value) VALUES('telegram_chat_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (chat_id,))
    return redirect(url_for("settings_page", telegram="saved"))


@app.post("/settings/telegram/test")
def test_telegram_settings():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    token = setting_value("telegram_bot_token")
    chat_id = setting_value("telegram_chat_id")
    if not token or not chat_id:
        return redirect(url_for("settings_page", telegram="missing"))
    try:
        bot = telegram_bot(token)
        bot_info = telegram_call(token, bot.get_me)
        bot_name = getattr(bot_info, "username", None) or getattr(bot_info, "first_name", None) or "your bot"
        telegram_send_text(token, bot, chat_id, f"Relay test: Telegram bot {bot_name} is connected.")
    except RuntimeError as exc:
        return redirect(url_for("settings_page", telegram_error=str(exc)[:180]))
    return redirect(url_for("settings_page", telegram="tested"))


@app.post("/settings/password")
def change_password():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    current = request.form.get("current", "")
    new = request.form.get("new", "")
    confirm = request.form.get("confirm", "")
    if not verify_panel_password(current):
        return redirect(url_for("settings_page", error="current"))
    if len(new) < 12 or new != confirm:
        return redirect(url_for("settings_page", error="new"))
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES('panel_password_hash',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (generate_password_hash(new),))
    return redirect(url_for("settings_page", saved="password"))


@app.post("/settings/message-limit")
def set_message_limit():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    try:
        limit = int(request.form.get("limit", ""))
    except ValueError:
        return redirect(url_for("settings_page", error="message-limit"))
    if not 1 <= limit <= MAX_MESSAGE_LIMIT_MB:
        return redirect(url_for("settings_page", error="message-limit"))
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES('max_message_mb',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(limit),))
    return redirect(url_for("settings_page", saved="message-limit"))


# App-based authentication management
def auth_secret_hash(secret):
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def new_auth_api_key():
    return "rly_app_" + secrets.token_urlsafe(32)


def new_product_key():
    return "RLY-" + secrets.token_hex(16).upper()


def parse_expiry(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        raise ValueError("Enter an expiration date and time in UTC.") from None


def auth_app_context(app_id, one_time_api_key="", one_time_product_key="", one_time_product_key_username="", notice=""):
    with db() as con:
        auth_app = con.execute("SELECT id,name,created FROM auth_apps WHERE id=?", (app_id,)).fetchone()
        if not auth_app:
            return None
        users = con.execute(
            "SELECT id,username,auth_mode,status,created,expires_at,last_login,duration_days,activated_at FROM auth_users WHERE app_id=? ORDER BY created DESC,id DESC",
            (app_id,),
        ).fetchall()
    all_users = users
    search = request.args.get("q", "").strip().casefold()
    status_filter = request.args.get("status", "")
    mode_filter = request.args.get("mode", "")
    now = time.time()
    users = [u for u in users if (not search or search in u["username"].casefold() or search == str(u["id"]))
             and (not mode_filter or u["auth_mode"] == mode_filter)
             and (not status_filter or (status_filter == "expired" and u["expires_at"] is not None and u["expires_at"] <= now)
                  or (status_filter == "pending" and u["duration_days"] and not u["activated_at"])
                  or (status_filter == "disabled" and u["status"] == "disabled")
                  or (status_filter == "active" and u["status"] == "active" and not (u["duration_days"] and u["activated_at"] is None) and (u["expires_at"] is None or u["expires_at"] > now)))]
    user_items = []
    for user in users:
        item = dict(user)
        item["display_status"] = "disabled" if user["status"] == "disabled" else "expired" if user["expires_at"] is not None and user["expires_at"] <= now else "pending" if user["duration_days"] and user["activated_at"] is None else "active"
        item["days_left"] = max(0, int((user["expires_at"]-now+86399)//86400)) if user["expires_at"] else None
        item["expires_local"] = datetime.fromtimestamp(user["expires_at"], timezone.utc).strftime("%Y-%m-%dT%H:%M") if user["expires_at"] else ""
        user_items.append(item)
    return render_panel(
        AUTH_APP_PAGE,
        auth_app={**dict(auth_app), "api_url": request.host_url.rstrip("/") + url_for("api_authenticate", app_id=app_id).removeprefix(request.script_root)},
        users=user_items,
        csrf=session.get("csrf", ""),
        one_time_api_key=one_time_api_key,
        one_time_product_key=one_time_product_key,
        one_time_product_key_username=one_time_product_key_username,
        notice=notice or request.args.get("notice", ""),
        error=request.args.get("error", ""),
        search_query=request.args.get("q", ""),
        status_filter=status_filter,
        mode_filter=mode_filter,
        total_users=len(all_users),
        account_stats={
            "total":len(all_users),
            "pending":sum(bool(u["duration_days"] and u["activated_at"] is None and u["status"] == "active") for u in all_users),
            "expired":sum(bool(u["expires_at"] is not None and u["expires_at"] <= now) for u in all_users),
            "disabled":sum(u["status"] == "disabled" for u in all_users),
        },
    )


def auth_home_context(one_time_api_key="", notice="", error=""):
    with db() as con:
        apps = con.execute(
            "SELECT a.id,a.name,a.created,COUNT(u.id) AS user_count FROM auth_apps a "
            "LEFT JOIN auth_users u ON u.app_id=a.id GROUP BY a.id ORDER BY a.created DESC,a.id DESC"
        ).fetchall()
    return render_panel(
        AUTH_HOME_PAGE,
        auth_apps=apps,
        csrf=session.get("csrf", ""),
        one_time_api_key=one_time_api_key,
        notice=notice or request.args.get("notice", ""),
        error=error or request.args.get("error", ""),
    )


@app.get("/auth")
def auth_home():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return auth_home_context()


@app.post("/auth/apps/create")
def create_auth_app():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    name = (request.form.get("name") or "").strip()[:80]
    if not name:
        return auth_home_context(error="name")
    api_key = new_auth_api_key()
    with db() as con:
        cur = con.execute(
            "INSERT INTO auth_apps(name,api_key_hash,created) VALUES(?,?,?)",
            (name, auth_secret_hash(api_key), time.time()),
        )
        app_id = cur.lastrowid
    # Show the generated key in this POST response only; only its hash is stored.
    return auth_home_context(one_time_api_key=api_key, notice=f"Created app {name} (ID {app_id}). Copy its API key now.")


@app.get("/auth/apps/<int:app_id>")
def auth_app_page(app_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    page = auth_app_context(app_id)
    return page if page is not None else redirect(url_for("auth_home"))


@app.post("/auth/apps/<int:app_id>/rename")
def rename_auth_app(app_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    name = (request.form.get("name") or "").strip()[:80]
    if name:
        with db() as con:
            con.execute("UPDATE auth_apps SET name=? WHERE id=?", (name, app_id))
    return redirect(url_for("auth_app_page", app_id=app_id, notice="renamed" if name else "", error="" if name else "invalid-name"))


@app.post("/auth/apps/<int:app_id>/rotate-key")
def rotate_auth_app_key(app_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    api_key = new_auth_api_key()
    with db() as con:
        cur = con.execute("UPDATE auth_apps SET api_key_hash=? WHERE id=?", (auth_secret_hash(api_key), app_id))
    if not cur.rowcount:
        return redirect(url_for("auth_home"))
    return auth_app_context(app_id, one_time_api_key=api_key, notice="The previous API key was revoked. Copy the new key now.")


@app.post("/auth/apps/<int:app_id>/delete")
def delete_auth_app(app_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        con.execute("DELETE FROM auth_apps WHERE id=?", (app_id,))
    return redirect(url_for("auth_home", notice="deleted"))


@app.post("/auth/apps/<int:app_id>/users/create")
def create_auth_user(app_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    username = (request.form.get("username") or "").strip()[:80]
    mode = request.form.get("auth_mode", "")
    password = request.form.get("password", "")
    try:
        expires_at = None
        duration_days = int(request.form.get("duration_days", "0"))
        if not 0 <= duration_days <= 36500:
            raise ValueError("Invalid duration")
        if duration_days:
            expires_at = None
    except ValueError:
        return redirect(url_for("auth_app_page", app_id=app_id, error="expiry"))
    if not username or mode not in {"password", "product_key", "both"}:
        return redirect(url_for("auth_app_page", app_id=app_id, error="user-fields"))
    if mode in {"password", "both"} and len(password) < 8:
        return redirect(url_for("auth_app_page", app_id=app_id, error="password"))
    product_key = new_product_key() if mode in {"product_key", "both"} else ""
    password_hash = generate_password_hash(password) if mode in {"password", "both"} else None
    product_key_hash = auth_secret_hash(product_key) if product_key else None
    try:
        with db() as con:
            cur = con.execute("SELECT 1 FROM auth_apps WHERE id=?", (app_id,)).fetchone()
            if not cur:
                return redirect(url_for("auth_home"))
            con.execute(
                "INSERT INTO auth_users(app_id,username,auth_mode,password_hash,product_key_hash,created,expires_at,duration_days) VALUES(?,?,?,?,?,?,?,?)",
                (app_id, username, mode, password_hash, product_key_hash, time.time(), expires_at, duration_days or None),
            )
    except sqlite3.IntegrityError:
        return redirect(url_for("auth_app_page", app_id=app_id, error="duplicate-user"))
    return auth_app_context(
        app_id,
        one_time_product_key=product_key,
        one_time_product_key_username=username if product_key else "",
        notice="User created. Copy this user's product key now." if product_key else "User created.",
    )


@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/expiry")
@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/license")
def update_auth_user_expiry(app_id, user_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    try:
        days = int(request.form.get("duration_days", ""))
        if not 0 <= days <= 36500:
            raise ValueError()
    except ValueError:
        return redirect(url_for("auth_app_page", app_id=app_id, error="expiry"))
    with db() as con:
        user = con.execute("SELECT activated_at,last_login,expires_at FROM auth_users WHERE id=? AND app_id=?", (user_id, app_id)).fetchone()
        if not user:
            return redirect(url_for("auth_app_page", app_id=app_id))
        active = any(user[field] is not None for field in ("activated_at", "last_login", "expires_at"))
        activated = time.time() if active and days else None
        expires_at = activated + days*86400 if activated is not None else None
        con.execute("UPDATE auth_users SET expires_at=?,duration_days=?,activated_at=? WHERE id=? AND app_id=?", (expires_at, days or None, activated, user_id, app_id))
    return redirect(url_for("auth_app_page", app_id=app_id, notice="License duration updated."))


@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/toggle")
def toggle_auth_user(app_id, user_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        con.execute("UPDATE auth_users SET status=CASE status WHEN 'active' THEN 'disabled' ELSE 'active' END WHERE id=? AND app_id=?", (user_id, app_id))
    return redirect(url_for("auth_app_page", app_id=app_id, notice="status-saved"))


@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/rotate-key")
def rotate_auth_user_key(app_id, user_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    product_key = new_product_key()
    with db() as con:
        user = con.execute(
            "SELECT username FROM auth_users WHERE id=? AND app_id=? AND auth_mode IN ('product_key','both')",
            (user_id, app_id),
        ).fetchone()
        if not user:
            return redirect(url_for("auth_app_page", app_id=app_id, error="key-rotate"))
        cur = con.execute(
            "UPDATE auth_users SET product_key_hash=? WHERE id=? AND app_id=? AND auth_mode IN ('product_key','both')",
            (auth_secret_hash(product_key), user_id, app_id),
        )
    if not cur.rowcount:
        return redirect(url_for("auth_app_page", app_id=app_id, error="key-rotate"))
    return auth_app_context(
        app_id,
        one_time_product_key=product_key,
        one_time_product_key_username=user["username"],
        notice=f"New product key created for {user['username']}. The old key was revoked.",
    )


@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/password")
def reset_auth_user_password(app_id, user_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    password = request.form.get("password", "")
    if len(password) < 8:
        return redirect(url_for("auth_app_page", app_id=app_id, error="password"))
    with db() as con:
        cur = con.execute(
            "UPDATE auth_users SET password_hash=? WHERE id=? AND app_id=? AND auth_mode IN ('password','both')",
            (generate_password_hash(password), user_id, app_id),
        )
    return redirect(url_for("auth_app_page", app_id=app_id, notice="password-saved" if cur.rowcount else "password-unavailable"))


@app.post("/auth/apps/<int:app_id>/users/<int:user_id>/delete")
def delete_auth_user(app_id, user_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        con.execute("DELETE FROM auth_users WHERE id=? AND app_id=?", (user_id, app_id))
    return redirect(url_for("auth_app_page", app_id=app_id, notice="user-deleted"))


@app.get("/api/auth/<int:app_id>/login")
def auth_api_info(app_id):
    return jsonify(error="Send credentials using POST with an Authorization: Bearer app-key header."), 405


@app.post("/api/auth/<int:app_id>/login")
def api_authenticate(app_id):
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify(error="App API key required"), 401
    supplied_app_key = parts[1].strip()
    if request.content_length and request.content_length > 16384:
        return jsonify(error="Request body is too large"), 413
    try:
        payload = request.get_json(force=True)
    except (ValueError, TypeError):
        return jsonify(error="Send a JSON request body"), 400
    if not isinstance(payload, dict):
        return jsonify(error="Send a JSON object"), 400

    remote_ip = request.remote_addr or "unknown"
    now = time.time()
    with db() as con:
        app_row = con.execute("SELECT id,api_key_hash FROM auth_apps WHERE id=?", (app_id,)).fetchone()
        if not app_row:
            return jsonify(error="Unknown app"), 404
        if not secrets.compare_digest(auth_secret_hash(supplied_app_key), app_row["api_key_hash"]):
            return jsonify(error="Invalid app API key"), 401
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM auth_attempts WHERE attempted<?", (now - 60,))
        attempt_count = con.execute(
            "SELECT COUNT(*) FROM auth_attempts WHERE app_id=? AND remote_ip=? AND attempted>?",
            (app_id, remote_ip, now - 60),
        ).fetchone()[0]
        if attempt_count >= 30:
            return jsonify(error="Too many authentication attempts. Try again shortly."), 429
        con.execute("INSERT INTO auth_attempts(app_id,remote_ip,attempted) VALUES(?,?,?)", (app_id, remote_ip, now))

        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        product_key = str(payload.get("product_key", "")).strip()
        user = None
        if product_key:
            user = con.execute(
                "SELECT * FROM auth_users WHERE app_id=? AND product_key_hash=?",
                (app_id, auth_secret_hash(product_key)),
            ).fetchone()
            valid = bool(user and user["auth_mode"] in {"product_key", "both"})
            if valid and user["auth_mode"] == "both":
                valid = username.casefold() == user["username"].casefold() and check_password_hash(user["password_hash"], password)
        else:
            user = con.execute(
                "SELECT * FROM auth_users WHERE app_id=? AND username=? COLLATE NOCASE",
                (app_id, username),
            ).fetchone()
            valid = bool(user and user["auth_mode"] == "password" and check_password_hash(user["password_hash"], password))
        if not valid or user["status"] != "active" or (user["expires_at"] is not None and user["expires_at"] <= now):
            return jsonify(authenticated=False, error="Invalid, disabled, or expired credentials"), 401
        con.execute("UPDATE auth_users SET last_login=? WHERE id=?", (now, user["id"]))
        expires_at = user["expires_at"]
        if user["duration_days"] and user["activated_at"] is None:
            expires_at = now + user["duration_days"] * 86400
            con.execute("UPDATE auth_users SET activated_at=?,expires_at=? WHERE id=?", (now, expires_at, user["id"]))
        return jsonify(
            authenticated=True,
            user={
                "username": user["username"],
                "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat() if expires_at else None,
            },
        ), 200


@app.get("/api-docs")
def auth_api_docs():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return render_panel(AUTH_DOCS_PAGE, csrf=session.get("csrf", ""))


# Message center and attachment routes
@app.post("/webhooks/<int:webhook_id>/delete")
def delete_webhook(webhook_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        files = con.execute("SELECT a.disk_name FROM attachments a JOIN messages m ON m.id=a.message_id WHERE m.webhook_id=?", (webhook_id,)).fetchall()
        con.execute("DELETE FROM webhooks WHERE id=?", (webhook_id,))
    for item in files:
        (UPLOAD_DIR / item["disk_name"]).unlink(missing_ok=True)
    return redirect(url_for("home"))


@app.get("/webhooks/<int:webhook_id>")
def webhook_messages(webhook_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    hook = webhook_row(webhook_id)
    if not hook:
        return redirect(url_for("home"))
    with db() as con:
        latest_message_id = con.execute(
            "SELECT COALESCE(MAX(id), 0) FROM messages WHERE webhook_id=?",
            (webhook_id,),
        ).fetchone()[0]
        con.execute(
            "UPDATE webhooks SET last_seen_message_id=MAX(last_seen_message_id, ?) WHERE id=?",
            (latest_message_id, webhook_id),
        )
        active_user_id = request.args.get("user_id")
        search_query = (request.args.get("q") or "").strip()[:100]
        search_pattern = f"%{search_query}%"
        users_sql = (
            "SELECT sender_id, (SELECT m2.source FROM messages m2 WHERE m2.webhook_id=messages.webhook_id "
            "AND m2.sender_id=messages.sender_id ORDER BY m2.id DESC LIMIT 1) AS source, "
            "COUNT(*) AS message_count, MAX(id) AS latest_id FROM messages WHERE webhook_id=?"
        )
        users_params = [webhook_id]
        if search_query:
            users_sql += " AND (sender_id LIKE ? OR source LIKE ?)"
            users_params.extend([search_pattern, search_pattern])
        users_sql += " GROUP BY sender_id ORDER BY latest_id DESC"
        users = con.execute(users_sql, users_params).fetchall()
        if active_user_id is None:
            total = con.execute(
                "SELECT COUNT(*) FROM messages WHERE webhook_id=?", (webhook_id,)
            ).fetchone()[0]
            if search_query:
                total = con.execute(
                    "SELECT COUNT(*) FROM messages WHERE webhook_id=? AND (sender_id LIKE ? OR source LIKE ?)",
                    (webhook_id, search_pattern, search_pattern),
                ).fetchone()[0]
        else:
            message_filter = "webhook_id=? AND sender_id=?"
            message_params = [webhook_id, active_user_id]
            if search_query:
                message_filter += (
                    " AND (content LIKE ? OR EXISTS ("
                    "SELECT 1 FROM attachments a "
                    "WHERE a.message_id=messages.id AND a.name LIKE ?))"
                )
                message_params.extend([search_pattern, search_pattern])
            total = con.execute(
                f"SELECT COUNT(*) FROM messages WHERE {message_filter}",
                message_params,
            ).fetchone()[0]
        page_size = 20
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(max(request.args.get("page", 1, type=int), 1), pages)
        if active_user_id is None:
            rows = []
        else:
            rows_params = [*message_params, page_size, (page - 1) * page_size]
            rows = con.execute(
                "SELECT id,sender_id,source,content,created FROM messages "
                f"WHERE {message_filter} ORDER BY id DESC LIMIT ? OFFSET ?",
                rows_params,
            ).fetchall()
        items = []
        for row in rows:
            files = con.execute("SELECT id,name,mime,size FROM attachments WHERE message_id=? ORDER BY id", (row["id"],)).fetchall()
            hue = int.from_bytes(hashlib.sha256(row["sender_id"].encode("utf-8")).digest()[:2], "big") % 360
            items.append({**dict(row), "files": [dict(f) for f in files], "user_hue": hue})
    hook_data = dict(hook)
    hook_data["url"] = webhook_base_url() + "/wbhk/" + hook_data["slug"]
    user_items = []
    for user in users:
        source = user["source"] or f"User {user['sender_id']}"
        hue = int.from_bytes(hashlib.sha256(user["sender_id"].encode("utf-8")).digest()[:2], "big") % 360
        user_items.append({**dict(user), "source": source, "user_hue": hue})
    active_user = None
    active_user_hue = None
    if active_user_id is not None:
        with db() as con:
            user_row = con.execute("SELECT source FROM messages WHERE webhook_id=? AND sender_id=? ORDER BY id DESC LIMIT 1", (webhook_id, active_user_id)).fetchone()
        active_user = (user_row["source"] if user_row else "") or f"User {active_user_id}"
        active_user_hue = int.from_bytes(
            hashlib.sha256(active_user_id.encode("utf-8")).digest()[:2], "big"
        ) % 360
    return render_panel(
        MESSAGE_CENTER,
        hook=hook_data,
        messages=items,
        users=user_items,
        active_user=active_user,
        active_user_id=active_user_id,
        active_user_hue=active_user_hue,
        search_query=search_query,
        total=total,
        page=page,
        pages=pages,
        csrf=session.get("csrf", ""),
        telegram_backup=request.args.get("telegram_backup", ""),
        backup_sent=request.args.get("sent", 0, type=int),
        backup_skipped=request.args.get("skipped", 0, type=int),
    )


@app.post("/webhooks/<int:webhook_id>/users/<sender_id>/telegram-backup")
def backup_user_to_telegram(webhook_id, sender_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    token = setting_value("telegram_bot_token")
    chat_id = setting_value("telegram_chat_id")
    redirect_args = {"user_id": sender_id}
    if not token or not chat_id:
        return redirect(url_for("webhook_messages", webhook_id=webhook_id, telegram_backup="missing", **redirect_args))
    with db() as con:
        hook = con.execute("SELECT name FROM webhooks WHERE id=?", (webhook_id,)).fetchone()
        rows = con.execute(
            "SELECT id,source,content,created FROM messages WHERE webhook_id=? AND sender_id=? ORDER BY id",
            (webhook_id, sender_id),
        ).fetchall()
        history = []
        for row in rows:
            files = con.execute(
                "SELECT name,disk_name,mime,size FROM attachments WHERE message_id=? ORDER BY id",
                (row["id"],),
            ).fetchall()
            history.append((dict(row), [dict(item) for item in files]))
    if not hook or not history:
        return redirect(url_for("webhook_messages", webhook_id=webhook_id, telegram_backup="missing-user", **redirect_args))

    sent_files = 0
    skipped_files = 0
    try:
        bot = telegram_bot(token)
        telegram_send_text(token, bot, chat_id, f"Relay user backup\nWebhook: {hook['name']}\nUser ID: {sender_id}\nMessages: {len(history)}")
        for row, files in history:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["created"]))
            sender_name = row["source"] or f"User {sender_id}"
            telegram_send_text(token, bot, chat_id, f"[{stamp}] {sender_name} (ID {sender_id})\n{row['content']}")
            for item in files:
                path = UPLOAD_DIR / item["disk_name"]
                if not path.is_file():
                    skipped_files += 1
                    continue
                sent_files += telegram_send_file(
                    token,
                    bot,
                    chat_id,
                    path,
                    item["name"],
                    item["size"],
                )
    except (RuntimeError, OSError) as exc:
        logger.warning("Telegram user backup failed for ID %s: %s", sender_id, exc)
        return redirect(url_for("webhook_messages", webhook_id=webhook_id, telegram_backup="failed", **redirect_args))
    return redirect(url_for("webhook_messages", webhook_id=webhook_id, telegram_backup="done", sent=sent_files, skipped=skipped_files, **redirect_args))


@app.post("/webhooks/<int:webhook_id>/clear")
def clear_messages(webhook_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        files = con.execute("SELECT a.disk_name FROM attachments a JOIN messages m ON m.id=a.message_id WHERE m.webhook_id=?", (webhook_id,)).fetchall()
        con.execute("DELETE FROM messages WHERE webhook_id=?", (webhook_id,))
    for item in files:
        (UPLOAD_DIR / item["disk_name"]).unlink(missing_ok=True)
    return redirect(url_for("webhook_messages", webhook_id=webhook_id))


@app.post("/webhooks/<int:webhook_id>/messages/<int:message_id>/delete")
def delete_message(webhook_id, message_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with db() as con:
        files = con.execute("SELECT a.disk_name FROM attachments a JOIN messages m ON m.id=a.message_id WHERE m.id=? AND m.webhook_id=?", (message_id, webhook_id)).fetchall()
        con.execute("DELETE FROM messages WHERE id=? AND webhook_id=?", (message_id, webhook_id))
    for item in files:
        (UPLOAD_DIR / item["disk_name"]).unlink(missing_ok=True)
    return redirect(
        url_for(
            "webhook_messages",
            webhook_id=webhook_id,
            user_id=request.form.get("return_user_id") or None,
            q=request.form.get("return_query") or None,
            page=request.form.get("return_page", type=int),
        )
    )


@app.get("/api/messages")
def messages():
    if not is_logged_in():
        return jsonify(error="Login required"), 401
    after = request.args.get("after", 0, type=int)
    with db() as con:
        rows = con.execute("SELECT id,sender_id,source,content,created FROM messages WHERE id>? ORDER BY id ASC LIMIT 200", (after,)).fetchall()
        total = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        output = []
        for row in rows:
            files = con.execute("SELECT id,name,mime,size FROM attachments WHERE message_id=? ORDER BY id", (row["id"],)).fetchall()
            output.append({"id": row["id"], "sender_id": row["sender_id"], "source": row["source"], "content": row["content"], "created": row["created"], "files": [dict(f) for f in files]})
    return jsonify(messages=output, total=total)


@app.get("/files/<int:file_id>")
def download(file_id):
    if not is_logged_in():
        return jsonify(error="Login required"), 401
    with db() as con:
        item = con.execute("SELECT name,disk_name,mime FROM attachments WHERE id=?", (file_id,)).fetchone()
    if not item:
        return "File not found", 404
    path = UPLOAD_DIR / item["disk_name"]
    if not path.is_file():
        return "File not found", 404
    mime = item["mime"].lower()
    safe_inline = mime in {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif", "video/mp4", "video/webm", "video/ogg"}
    response = send_file(path, as_attachment=not safe_inline, download_name=item["name"], mimetype=mime if safe_inline else "application/octet-stream", conditional=True)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


# Public webhook ingestion
def create_message(webhook_id, sender_id, source, content, incoming_files, sender_ip=""):
    sender_id = (sender_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sender_id):
        raise ValueError("A valid user ID is required (1-80 letters, numbers, hyphens, or underscores).")
    source = (source or f"User {sender_id}").strip()[:80] or f"User {sender_id}"
    content = (content or "").strip()
    total = len(content.encode("utf-8"))
    staged = []
    limit = message_limit_bytes()
    if total > limit:
        raise ValueError(f"The combined message and attachments exceed the current {limit // (1024 * 1024)} MB limit.")
    current_path = None
    try:
        for f in incoming_files:
            name = secure_filename(f.filename or "") or "attachment"
            disk_name = secrets.token_hex(20)
            path = UPLOAD_DIR / disk_name
            current_path = path
            size = 0
            with path.open("wb") as out:
                while True:
                    chunk = f.stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    total += len(chunk)
                    if total > limit:
                        raise ValueError(f"The combined message and attachments exceed the current {limit // (1024 * 1024)} MB limit.")
                    out.write(chunk)
            staged.append((name, disk_name, f.mimetype or "application/octet-stream", size))
            current_path = None
    except Exception:
        if current_path is not None:
            current_path.unlink(missing_ok=True)
        for _, disk_name, _, _ in staged:
            (UPLOAD_DIR / disk_name).unlink(missing_ok=True)
        raise
    if not content:
        raise ValueError("A message is required.")
    is_new_user = False
    try:
        with db() as con:
            con.execute("BEGIN IMMEDIATE")
            created = time.time()
            recent_count = con.execute(
                "SELECT COUNT(*) FROM messages WHERE sender_ip=? AND created>?",
                (sender_ip, created - MESSAGE_RATE_WINDOW_SECONDS),
            ).fetchone()[0]
            if recent_count >= MESSAGE_RATE_LIMIT:
                raise RateLimitExceeded(
                    f"Message limit reached: send up to {MESSAGE_RATE_LIMIT} messages every {MESSAGE_RATE_WINDOW_SECONDS} seconds."
                )
            is_new_user = con.execute(
                "SELECT 1 FROM messages WHERE webhook_id=? AND sender_id=? LIMIT 1",
                (webhook_id, sender_id),
            ).fetchone() is None
            cur = con.execute(
                "INSERT INTO messages(webhook_id,sender_id,source,content,created,sender_ip) VALUES(?,?,?,?,?,?)",
                (webhook_id, sender_id, source, content, created, sender_ip),
            )
            mid = cur.lastrowid
            for name, disk_name, mime, size in staged:
                con.execute("INSERT INTO attachments(message_id,name,disk_name,mime,size) VALUES(?,?,?,?,?)", (mid, name, disk_name, mime, size))
    except Exception:
        for _, disk_name, _, _ in staged:
            (UPLOAD_DIR / disk_name).unlink(missing_ok=True)
        raise
    if is_new_user:
        telegram_new_user_notice(webhook_id, sender_id, source, content, len(staged))
    return mid


@app.post("/wbhk/<slug>")
def public_webhook(slug):
    with db() as con:
        hook = con.execute("SELECT id FROM webhooks WHERE slug=?", (slug,)).fetchone()
    if not hook:
        return jsonify(error="Invalid webhook"), 404
    return receive_webhook(hook)


@app.post("/webhook/<token>")
def legacy_webhook(token):
    with db() as con:
        hook = con.execute("SELECT id FROM webhooks WHERE token=?", (token,)).fetchone()
    if not hook:
        return jsonify(error="Invalid webhook"), 404
    return receive_webhook(hook)


def receive_webhook(hook):
    try:
        if request.is_json:
            payload = request.get_json(silent=True) or {}
            sender_id = str(payload.get("id", ""))
            content = str(payload.get("message", ""))
            source = str(payload.get("username", ""))
            files = []
        else:
            sender_id = request.form.get("id", "")
            content = request.form.get("message", "")
            source = request.form.get("username", "")
            files = request.files.getlist("files") or request.files.getlist("file")
        if not sender_id.strip():
            raise ValueError("The id field is required.")
        if not content.strip():
            raise ValueError("The message field is required.")
        mid = create_message(
            hook["id"], sender_id, source, content, files, request.remote_addr or "unknown"
        )
        return jsonify(ok=True, id=mid), 201
    except RateLimitExceeded as exc:
        return jsonify(error=str(exc)), 429
    except ValueError as exc:
        return jsonify(error=str(exc)), 413 if "limit" in str(exc).lower() else 400


@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return jsonify(error=f"The combined request limit is {message_limit_mb()} MB per message."), 413



# Configure the shared timestamp display used by message templates.
from panel_features import install_features
from share_feature import install_share_feature

storage_summary, start_storage_monitor = install_features(app, globals())
install_share_feature(app, globals())
if app.secret_key:
    init_db()
    start_storage_monitor()

app.jinja_env.filters["datetime"] = lambda value: time.strftime("%b %d, %Y · %H:%M", time.localtime(value))
app.jinja_env.filters["utc_datetime"] = lambda value: datetime.fromtimestamp(value, timezone.utc).strftime("%b %d, %Y · %H:%M")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(config_value("PORT", "30333")))
