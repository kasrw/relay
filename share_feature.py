"""Pastebin-like public text and file shares managed from the Relay panel."""

import re
import secrets
import time
from pathlib import Path

from flask import redirect, render_template_string, request, send_file, url_for
from werkzeug.utils import secure_filename

from panel_ui import enhance_page
from templates import SIMPLE_CSS, THEME_SCRIPT


SHARES_PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shares · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body><header class="top"><a class="brand" href="/">Relay</a><nav class="topnav"><a href="/">Webhooks</a></nav></header>
<main class="shares-main"><div class="shares-heading"><div><div class="section-title">QUICK PUBLISHING</div><h1>Text & file shares</h1><p class="muted">Publish a note or file, then share its private URL with anyone who needs it.</p></div><span class="workspace-app-id"><span class="share-gradient-text">{{ shares|length }} SHARES</span></span></div>
{% if error == 'invalid' %}<div class="notice" role="alert">Choose a title, a custom path using letters, numbers, hyphens or underscores, and some text or a file.</div>{% elif error == 'duplicate' %}<div class="notice" role="alert">That custom path is already in use. Try another one.</div>{% elif error == 'large' %}<div class="notice" role="alert">This share exceeds the current {{ limit_mb }} MB limit.</div>{% elif error == 'failed' %}<div class="notice" role="alert">Could not create the share. Please try again.</div>{% elif error == 'busy' %}<div class="notice" role="alert">The file is currently being downloaded. Try deleting this share again in a moment.</div>{% endif %}
<section class="form-card share-create"><div class="share-create-heading"><span class="share-hero-icon" aria-hidden="true">↗</span><div><h2>Create a share</h2><p class="muted">Add text, a file, or both. Choose a short path that is easy to pass along.</p></div></div><form method="post" enctype="multipart/form-data" action="/shares/create"><input type="hidden" name="csrf" value="{{ csrf }}"><div class="share-form-grid"><label><span class="share-label-text">Title</span><input class="text-input" name="title" maxlength="100" placeholder="e.g. Setup instructions" required></label><label><span class="share-label-text">Custom link path</span><div class="share-slug-input"><span>/p/</span><input class="text-input" name="slug" maxlength="63" pattern="[A-Za-z0-9][A-Za-z0-9_-]{2,62}" placeholder="setup-guide" required></div></label></div><label class="share-label"><span class="share-label-text">Text <small>optional with a file</small></span><textarea class="text-input share-text" name="content" placeholder="Paste plain text here…"></textarea></label><label class="share-file-picker"><input type="file" name="file"><span class="share-file-icon" aria-hidden="true">＋</span><span><strong>Choose a file</strong><small>Any file type · up to {{ limit_mb }} MB per share</small></span><span class="share-file-name" aria-live="polite">No file selected</span></label><div class="share-create-footer"><span class="share-link-preview"><span>LINK PREVIEW</span><code id="share-link-preview">/p/your-link</code></span><button class="button primary" type="submit">Create share <span aria-hidden="true">→</span></button></div></form></section>
<div class="share-list-head"><div><div class="section-title">LIBRARY</div><h2>Your shares</h2></div><span>{{ shares|length }} links</span></div>
{% if shares %}<section class="share-list">{% for item in shares %}<article class="form-card share-item"><div class="share-item-icon {% if item.disk_name %}file-share{% else %}text-share{% endif %}" aria-hidden="true">{% if item.disk_name %}↧{% else %}¶{% endif %}</div><div class="share-item-main"><div class="share-item-title"><h3>{{ item.title }}</h3><span class="share-type-pill {% if item.disk_name %}file-pill{% else %}text-pill{% endif %}">{{ 'FILE' if item.disk_name else 'TEXT' }}</span></div><a href="/p/{{ item.slug }}" target="_blank" rel="noopener">/p/{{ item.slug }}</a><div class="share-item-meta">{% if item.disk_name %}{{ item.filename }} · {{ (item.size/1048576)|round(1) }} MB{% else %}Text share · {{ item.content|length }} characters{% endif %} · {{ item.created|int|datetime }}</div></div><div class="share-item-actions"><button class="button" type="button" data-copy="{{ request.host_url.rstrip('/') }}/p/{{ item.slug }}">Copy link</button><a class="button" href="/p/{{ item.slug }}" target="_blank" rel="noopener">Open</a><form method="post" action="/shares/{{ item.id }}/delete" onsubmit="return confirm('Delete this share and its public link?')"><input type="hidden" name="csrf" value="{{ csrf }}"><button class="delete" type="submit">Delete</button></form></div></article>{% endfor %}</section>{% else %}<section class="form-card empty share-empty"><span aria-hidden="true">¶</span><h2>No shares yet</h2><p>Create a text paste or upload a file to get your first shareable link.</p></section>{% endif %}</main><script>const slugField=document.querySelector('[name="slug"]');const preview=document.querySelector('#share-link-preview');const fileField=document.querySelector('[name="file"]');const fileName=document.querySelector('.share-file-name');slugField?.addEventListener('input',()=>preview.textContent='/p/'+(slugField.value.trim().toLowerCase()||'your-link'));fileField?.addEventListener('change',()=>fileName.textContent=fileField.files[0]?.name||'No file selected');</script>''' + THEME_SCRIPT + r'''</body></html>'''


PUBLIC_SHARE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{{ item.title }} · Relay share</title><style>''' + SIMPLE_CSS + r'''</style></head><body class="public-share-page"><header class="top"><a class="brand" href="/">Relay</a><span class="share-public-label">PUBLIC SHARE</span></header><main class="public-share-main"><a class="workspace-back" href="/">← Relay</a><section class="form-card public-share-card"><div class="key-eyebrow">{{ 'FILE' if item.disk_name else 'TEXT' }} · SHARED WITH A LINK</div><h1>{{ item.title }}</h1><p class="muted">Created {{ item.created|int|datetime }}</p>{% if item.disk_name %}<div class="public-file-card"><div><strong>{{ item.filename }}</strong><span>{{ (item.size/1048576)|round(1) }} MB · {{ item.mime }}</span></div><a class="button primary" href="/p/{{ item.slug }}/download">Download file</a></div>{% endif %}{% if item.content %}<pre class="public-share-content"><code>{{ item.content }}</code></pre>{% endif %}</section><p class="share-public-footer">Anyone with this link can view this share.</p></main></body></html>'''


def install_share_feature(app, ctx):
    db, data_dir, uploads = ctx['db'], ctx['DATA_DIR'], ctx['UPLOAD_DIR']

    @app.get('/shares')
    def shares_page():
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        with db() as con:
            shares = con.execute('SELECT * FROM shares ORDER BY created DESC,id DESC').fetchall()
        return render_template_string(enhance_page(SHARES_PAGE), shares=shares, csrf=ctx['session'].get('csrf',''), limit_mb=ctx['message_limit_mb'](), error=request.args.get('error',''))

    @app.post('/shares/create')
    def create_share():
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        title = (request.form.get('title') or '').strip()[:100]
        slug = (request.form.get('slug') or '').strip().lower()
        content = request.form.get('content') or ''
        incoming = request.files.get('file')
        if not title or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,62}',slug) or (not content.strip() and (incoming is None or not incoming.filename)):
            return redirect(url_for('shares_page',error='invalid'))
        limit = ctx['message_limit_bytes']()
        if len(content.encode('utf-8')) > limit:
            return redirect(url_for('shares_page',error='large'))
        disk_name = filename = mime = None
        size = 0
        if incoming is not None and incoming.filename:
            filename = secure_filename(incoming.filename) or 'download'
            mime = incoming.mimetype or 'application/octet-stream'
            disk_name = secrets.token_hex(24)
            path = uploads / disk_name
            try:
                with path.open('wb') as target:
                    while True:
                        chunk = incoming.stream.read(1024*1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size + len(content.encode('utf-8')) > limit:
                            raise OverflowError()
                        target.write(chunk)
            except OverflowError:
                path.unlink(missing_ok=True)
                return redirect(url_for('shares_page',error='large'))
            except OSError:
                path.unlink(missing_ok=True)
                return redirect(url_for('shares_page',error='failed'))
            except Exception:
                path.unlink(missing_ok=True)
                raise
        try:
            with db() as con:
                con.execute('INSERT INTO shares(slug,title,content,disk_name,filename,mime,size,created) VALUES(?,?,?,?,?,?,?,?)',
                            (slug,title,content,disk_name,filename,mime,size,time.time()))
        except Exception as exc:
            if disk_name:
                (uploads/disk_name).unlink(missing_ok=True)
            import sqlite3
            if isinstance(exc,sqlite3.IntegrityError):
                return redirect(url_for('shares_page',error='duplicate'))
            raise
        return redirect(url_for('shares_page'))

    @app.post('/shares/<int:share_id>/delete')
    def delete_share(share_id):
        if not ctx['is_logged_in']():
            return redirect(url_for('login_page'))
        with db() as con:
            row=con.execute('SELECT disk_name FROM shares WHERE id=?',(share_id,)).fetchone()
        if row and row['disk_name']:
            try:
                (uploads/row['disk_name']).unlink(missing_ok=True)
            except OSError:
                return redirect(url_for('shares_page',error='busy'))
        with db() as con:
            con.execute('DELETE FROM shares WHERE id=?',(share_id,))
        return redirect(url_for('shares_page'))

    @app.get('/p/<slug>')
    def public_share(slug):
        with db() as con:
            row=con.execute('SELECT * FROM shares WHERE slug=? COLLATE NOCASE',(slug,)).fetchone()
        if not row:
            return render_template_string(enhance_page(PUBLIC_SHARE,replace_header=False), item={'title':'Share not found','created':time.time(),'disk_name':None,'content':'This link is unavailable.','slug':''}),404
        response=app.make_response(render_template_string(enhance_page(PUBLIC_SHARE,replace_header=False),item=row))
        response.headers['X-Robots-Tag']='noindex, nofollow'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    @app.get('/p/<slug>/download')
    def download_share(slug):
        with db() as con:
            row=con.execute('SELECT filename,disk_name,size FROM shares WHERE slug=? COLLATE NOCASE',(slug,)).fetchone()
        if not row or not row['disk_name']:
            return 'File not found',404
        path=uploads/row['disk_name']
        if not path.is_file():
            return 'File not found',404
        response=send_file(path,as_attachment=True,download_name=row['filename'],mimetype='application/octet-stream',conditional=True)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="sandbox; default-src 'none'"
        response.headers['Cache-Control']='no-store'
        response.headers['Referrer-Policy']='no-referrer'
        return response
