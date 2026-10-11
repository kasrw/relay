"""Bulk accounts, live inbox snapshots and app-wide storage maintenance."""

import io
import json
import logging
import secrets
import shutil
import threading
import time

from flask import jsonify, redirect, render_template_string, request, url_for
from werkzeug.security import generate_password_hash


def install_features(app, ctx):
    db = ctx['db']
    setting = ctx['setting_value']
    data_dir, uploads = ctx['DATA_DIR'], ctx['UPLOAD_DIR']
    started = False
    start_lock = threading.Lock()

    def put(con, key, value):
        con.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    def initialize():
        with db() as con:
            con.execute('CREATE TABLE IF NOT EXISTS automatic_backups (webhook_id INTEGER NOT NULL,sender_id TEXT NOT NULL,last_message_id INTEGER NOT NULL,completed REAL NOT NULL,PRIMARY KEY(webhook_id,sender_id))')

    def summary():
        disk = shutil.disk_usage(data_dir)
        with db() as con:
            attachment = con.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM attachments').fetchone()
            share_files = con.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM shares WHERE disk_name IS NOT NULL').fetchone()
            messages = con.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
        data_bytes = 0
        for path in data_dir.rglob('*'):
            try:
                if path.is_file():
                    data_bytes += path.stat().st_size
            except FileNotFoundError:
                pass  # An upload or retention cleanup may change files during the scan.
        return dict(free_gb=round(disk.free / 1024**3, 2), total_gb=round(disk.total / 1024**3, 2),
                    used_percent=round((disk.total-disk.free)*100/disk.total), data_mb=round(data_bytes/1024**2, 2),
                    attachment_mb=round((attachment[1]+share_files[1])/1024**2, 2), files=attachment[0]+share_files[0], messages=messages,
                    auto_enabled=setting('auto_backup_enabled', '1') == '1',
                    backup_status=setting('auto_backup_status', 'Waiting for the first storage check.'),
                    backup_time=setting('auto_backup_completed', ''), retention_days=setting('retention_days', '0'))

    def purge(days):
        cutoff = time.time() - days*86400
        with db() as con:
            files = con.execute('SELECT disk_name FROM attachments WHERE message_id IN (SELECT id FROM messages WHERE created<?)', (cutoff,)).fetchall()
            count = con.execute('DELETE FROM messages WHERE created<?', (cutoff,)).rowcount
        for row in files:
            (uploads / row['disk_name']).unlink(missing_ok=True)
        return count

    def check_storage():
        initialize()
        now = time.time()
        # A SQLite lease coordinates the monitor across Gunicorn workers.
        with db() as con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute("SELECT value FROM settings WHERE key='storage_monitor_lease'").fetchone()
            if row and float(row[0]) > now:
                return
            put(con, 'storage_monitor_lease', now+3600)
        try:
            free = shutil.disk_usage(data_dir).free
            if free < 10*1024**3 and setting('auto_backup_enabled', '1') == '1':
                token, chat = setting('telegram_bot_token'), setting('telegram_chat_id')
                if not token or not chat:
                    with db() as con:
                        put(con, 'auto_backup_status', 'Low storage: configure a Telegram bot and chat ID in Settings.')
                    return
                with db() as con:
                    # Latest users means latest first appearance, scoped to each webhook.
                    users = con.execute('SELECT webhook_id,sender_id,MAX(id) AS last_id FROM messages GROUP BY webhook_id,sender_id ORDER BY MIN(created) DESC,MIN(id) DESC LIMIT 20').fetchall()
                bot = ctx['telegram_bot'](token)
                processed = 0
                for user in users:
                    with db() as con:
                        previous = con.execute('SELECT last_message_id FROM automatic_backups WHERE webhook_id=? AND sender_id=?', (user['webhook_id'], user['sender_id'])).fetchone()
                        if previous and previous[0] >= user['last_id']:
                            continue
                        put(con, 'storage_monitor_lease', time.time()+3600)
                        hook = con.execute('SELECT name FROM webhooks WHERE id=?', (user['webhook_id'],)).fetchone()
                        history = con.execute('SELECT id,source,content,created FROM messages WHERE webhook_id=? AND sender_id=? AND id<=? ORDER BY id', (user['webhook_id'], user['sender_id'], user['last_id'])).fetchall()
                        files = con.execute('SELECT a.* FROM attachments a JOIN messages m ON m.id=a.message_id WHERE m.webhook_id=? AND m.sender_id=? AND m.id<=? ORDER BY a.id', (user['webhook_id'], user['sender_id'], user['last_id'])).fetchall()
                    if not hook:
                        continue
                    ctx['telegram_send_text'](token, bot, chat, f"Relay automatic low-storage backup\nWebhook: {hook['name']}\nUser ID: {user['sender_id']}\nMessages: {len(history)}\nFree disk: {free/1024**3:.2f} GiB")
                    manifest = json.dumps(dict(webhook=dict(id=user['webhook_id'],name=hook['name']),sender_id=user['sender_id'],messages=[dict(r) for r in history],attachments=[dict(r) for r in files]), ensure_ascii=False, indent=2).encode('utf-8')
                    # The history manifest is downloadable and can be used to reconstruct messages.
                    manifest_name = f"relay-{user['webhook_id']}-{user['sender_id']}-messages.json"
                    chunk_size = ctx['TELEGRAM_CHUNK_BYTES']
                    parts = max(1, (len(manifest)+chunk_size-1)//chunk_size)
                    if parts > 1:
                        ctx['telegram_send_text'](token,bot,chat,f'History {manifest_name} has {parts} parts. Concatenate the parts in numeric order to restore the JSON file.')
                    for index in range(parts):
                        filename = manifest_name if parts == 1 else f'{manifest_name}.part{index+1:04d}-of-{parts:04d}'
                        ctx['telegram_call'](token, bot.send_document, chat, io.BytesIO(manifest[index*chunk_size:(index+1)*chunk_size]), visible_file_name=filename)
                    for item in files:
                        with db() as con:
                            put(con, 'storage_monitor_lease', time.time()+3600)
                        path = uploads / item['disk_name']
                        if not path.is_file():
                            raise OSError(f"Missing attachment: {item['name']}")
                        ctx['telegram_send_file'](token, bot, chat, path, item['name'], item['size'])
                    with db() as con:
                        con.execute('INSERT INTO automatic_backups VALUES(?,?,?,?) ON CONFLICT(webhook_id,sender_id) DO UPDATE SET last_message_id=excluded.last_message_id,completed=excluded.completed', (user['webhook_id'], user['sender_id'], user['last_id'], time.time()))
                    processed += 1
                with db() as con:
                    put(con, 'auto_backup_status', f'Low-storage backup finished: {processed} updated users sent; unchanged users skipped. Local data retained.')
                    put(con, 'auto_backup_completed', time.time())
            elif free >= 10*1024**3:
                with db() as con:
                    put(con, 'auto_backup_status', 'Storage is above the 10 GiB backup threshold.')
            # Retention is opt-in and does not run while low on disk, preserving backup candidates.
            retention = int(setting('retention_days', '0'))
            if retention and free >= 10*1024**3:
                purge(retention)
        except Exception:
            logging.getLogger('relay.storage').exception('Automatic storage maintenance failed')
            # Keep Telegram credentials and external error text out of the UI.
            with db() as con:
                put(con, 'auto_backup_status', 'Backup failed. It will retry; partial files may already be in Telegram. Check server logs.')
        finally:
            with db() as con:
                put(con, 'storage_monitor_lease', time.time()+300)

    def start_monitor():
        nonlocal started
        with start_lock:
            if started:
                return
            started = True
            def loop():
                while True:
                    try:
                        check_storage()
                    except Exception:
                        logging.getLogger('relay.storage').exception('Storage monitor error')
                    time.sleep(60)
            threading.Thread(target=loop, name='relay-storage', daemon=True).start()

    @app.get('/panel/live')
    def live_snapshot():
        if not ctx['is_logged_in']():
            return jsonify(error='Sign in required'), 401
        with db() as con:
            hooks = con.execute('SELECT w.id,COUNT(DISTINCT m.sender_id) AS users,COALESCE(MAX(m.id),0) AS latest,SUM(CASE WHEN m.id>w.last_seen_message_id THEN 1 ELSE 0 END) AS unread FROM webhooks w LEFT JOIN messages m ON m.webhook_id=w.id GROUP BY w.id').fetchall()
        response = jsonify(webhooks=[dict(h) for h in hooks])
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/settings/storage')
    def storage_options():
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        try:
            days = int(request.form.get('retention_days', '0'))
            if not 0 <= days <= 36500:
                raise ValueError()
        except ValueError:
            return redirect(url_for('settings_page', storage_notice='Choose a retention duration from 0 to 36500 days.'))
        with db() as con:
            put(con, 'auto_backup_enabled', '1' if request.form.get('auto_backup') else '0')
            put(con, 'retention_days', days)
        return redirect(url_for('settings_page', storage_notice='Storage preferences saved.'))

    @app.post('/settings/storage/cleanup')
    def storage_cleanup():
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        try:
            days = int(request.form.get('days', '30'))
            if not 1 <= days <= 36500:
                raise ValueError()
        except ValueError:
            return redirect(url_for('settings_page', storage_notice='Choose a cleanup age of at least 1 day.'))
        count = purge(days)
        return redirect(url_for('settings_page', storage_notice=f'Deleted {count} old messages and their attachments across all webhooks.'))

    @app.post('/auth/apps/<int:app_id>/users/bulk')
    def bulk_users(app_id):
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        try:
            ids = list({int(value) for value in request.form.getlist('user_ids')})
            days = int(request.form.get('days', '30'))
            if not ids or len(ids) > 1000 or not 1 <= days <= 36500:
                raise ValueError()
        except ValueError:
            return redirect(url_for('auth_app_page', app_id=app_id, notice='Select users and enter a valid duration.'))
        action = request.form.get('action')
        count = 0
        with db() as con:
            for user_id in ids:
                user = con.execute('SELECT * FROM auth_users WHERE id=? AND app_id=?', (user_id,app_id)).fetchone()
                if not user:
                    continue
                if action in ('enable','disable'):
                    con.execute('UPDATE auth_users SET status=? WHERE id=?', ('active' if action=='enable' else 'disabled',user_id))
                elif action == 'delete':
                    con.execute('DELETE FROM auth_users WHERE id=?', (user_id,))
                elif action == 'extend':
                    if user['duration_days'] and user['activated_at'] is None:
                        con.execute('UPDATE auth_users SET duration_days=duration_days+? WHERE id=?', (days,user_id))
                    else:
                        expiry = max(time.time(), user['expires_at'] or time.time()) + days*86400
                        activated = user['activated_at'] or time.time()
                        duration = max(1,int((expiry-activated+86399)//86400))
                        con.execute('UPDATE auth_users SET expires_at=?,duration_days=?,activated_at=? WHERE id=?', (expiry,duration,activated,user_id))
                else:
                    return redirect(url_for('auth_app_page', app_id=app_id, notice='Choose a valid bulk action.'))
                count += 1
        return redirect(url_for('auth_app_page', app_id=app_id, notice=f'Bulk {action}: {count} users updated.'))

    @app.post('/auth/apps/<int:app_id>/users/batch-create')
    def batch_create(app_id):
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        try:
            count = int(request.form.get('count', '1'))
            days = int(request.form.get('duration_days', '30'))
            if not 1 <= count <= 100 or not 0 <= days <= 36500:
                raise ValueError()
        except ValueError:
            return redirect(url_for('auth_app_page',app_id=app_id,notice='Batch size must be 1–100 and duration 0–36500 days.'))
        mode = request.form.get('auth_mode', 'product_key')
        if mode not in ('password','product_key','both'):
            return redirect(url_for('auth_app_page',app_id=app_id))
        credentials = []
        with db() as con:
            if not con.execute('SELECT 1 FROM auth_apps WHERE id=?',(app_id,)).fetchone():
                return redirect(url_for('auth_home'))
            for _ in range(count):
                username = 'user-' + secrets.token_hex(6)
                password = secrets.token_urlsafe(18) if mode != 'product_key' else ''
                key = ctx['new_product_key']() if mode != 'password' else ''
                con.execute('INSERT INTO auth_users(app_id,username,auth_mode,password_hash,product_key_hash,created,duration_days) VALUES(?,?,?,?,?,?,?)',
                            (app_id,username,mode,generate_password_hash(password) if password else None,ctx['auth_secret_hash'](key) if key else None,time.time(),days or None))
                credentials.append(dict(username=username,password=password,product_key=key))
        # Immediate POST response only; secrets are never saved in session or plaintext DB columns.
        page = ctx['auth_app_context'](app_id, notice=f'Created {count} users. Copy the credentials now; they are shown once.')
        from html import escape
        block = '<section class="form-card"><h2>New user credentials · copy now</h2><pre><code>' + escape(json.dumps(credentials,indent=2)) + '</code></pre></section>'
        return page.replace('<div class="section-title">Users', block+'<div class="section-title">Users', 1)

    return summary, start_monitor
