from templates import SIMPLE_CSS, THEME_SCRIPT


AUTH_HOME_PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auth · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body class="auth-page">
<header class="top"><a class="brand" href="/">Relay</a><nav class="topnav">
<a class="plain" href="/">Webhooks</a><a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><a class="plain" href="/settings">Settings</a>
<button class="theme" id="theme-toggle" type="button">Light / dark</button><form method="post" action="/logout"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button">Sign out</button></form>
</nav></header><main><h1>Auth</h1><p class="muted">Create apps and manage credentials for your own users.</p>
{% if notice %}<div class="notice">{{ notice }}</div>{% endif %}{% if error == 'name' %}<div class="notice">Enter an app name.</div>{% endif %}
{% if one_time_api_key %}<section class="form-card user-key-card"><div class="key-eyebrow">APP SERVER CREDENTIAL</div><h2>Copy this app API key now</h2><p class="muted">Your server uses this key to call the auth API. It is not a user's product key. This key is shown once and only its hash is saved.</p><code class="secret-key">{{ one_time_api_key }}</code></section>{% endif %}
<form class="form-card" method="post" action="/auth/apps/create"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><h2>Create an app</h2><div class="auth-create"><input class="text-input" name="name" maxlength="80" placeholder="App name" required><button class="button primary" type="submit">Create app</button></div></form>
<div class="section-title">Your apps</div>{% if auth_apps %}<section class="cards">{% for item in auth_apps %}<a class="hookbox" href="/auth/apps/{{ item.id }}"><div><div class="hook-name">{{ item.name }}</div><div class="hook-path">App ID {{ item.id }} · {{ item.user_count }} users</div></div><div class="arrow">→</div></a>{% endfor %}</section>{% else %}<section class="form-card empty">No auth apps yet. Create one to get an API key.</section>{% endif %}
</main>''' + THEME_SCRIPT + r'''</body></html>'''


AUTH_APP_PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ auth_app.name }} · Auth · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body class="auth-page">
<header class="top"><a class="brand" href="/">Relay</a><nav class="topnav">
<a class="plain" href="/">Webhooks</a><a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><a class="plain" href="/settings">Settings</a>
<button class="theme" id="theme-toggle" type="button">Light / dark</button><form method="post" action="/logout"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button">Sign out</button></form>
</nav></header><main><p><a class="plain" href="/auth">← All apps</a></p><h1>{{ auth_app.name }}</h1><p class="muted">App ID {{ auth_app.id }} · API endpoint <code>{{ auth_app.api_url }}</code></p>
{% if notice == 'user-deleted' %}<div class="notice">User deleted.</div>{% elif notice == 'expiry-saved' %}<div class="notice">User expiration updated.</div>{% elif notice == 'status-saved' %}<div class="notice">User status updated.</div>{% elif notice == 'renamed' %}<div class="notice">App name updated.</div>{% elif notice == 'password-saved' %}<div class="notice">User password reset.</div>{% elif notice == 'password-unavailable' %}<div class="notice">This user does not use password authentication.</div>{% elif notice %}<div class="notice">{{ notice }}</div>{% endif %}
{% if error == 'expiry' %}<div class="notice">Enter a valid expiration date and time in UTC.</div>{% elif error == 'user-fields' %}<div class="notice">Enter a username and choose an authentication method.</div>{% elif error == 'password' %}<div class="notice">Passwords must be at least 8 characters.</div>{% elif error == 'duplicate-user' %}<div class="notice">That username is already used in this app.</div>{% elif error == 'key-rotate' %}<div class="notice">This user does not have a product key to rotate.</div>{% elif error == 'invalid-name' %}<div class="notice">Enter an app name.</div>{% endif %}
{% if one_time_api_key %}<section class="form-card user-key-card"><div class="key-eyebrow">APP SERVER CREDENTIAL</div><h2>Copy the new app API key now</h2><p class="muted">This is your server's app API key, not an end-user product key. The previous key has been revoked; this one is shown once.</p><code class="secret-key">{{ one_time_api_key }}</code></section>{% endif %}
{% if one_time_product_key %}<section class="form-card user-key-card"><div class="key-eyebrow">INDIVIDUAL USER CREDENTIAL</div><h2>Product key for {{ one_time_product_key_username }}</h2><p class="muted">This key belongs to this user only. It is shown once; copy it and share it with them securely.</p><code class="secret-key">{{ one_time_product_key }}</code></section>{% endif %}
<section class="form-card"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 7v5c0 5 3.4 8 8 10 4.6-2 8-5 8-10V7z"/><path d="m9 12 2 2 4-4"/></svg>App settings</h2><p class="muted auth-card-intro">The app API key identifies this app to your server. Each user has their own separate product key.</p><form method="post" action="/auth/apps/{{ auth_app.id }}/rename" class="auth-create"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><input class="text-input" name="name" maxlength="80" value="{{ auth_app.name }}" required><button class="button" type="submit">Rename</button></form>
<form method="post" action="/auth/apps/{{ auth_app.id }}/rotate-key" class="auth-action" onsubmit="return confirm('Revoke the current app API key and create a replacement?')"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button" type="submit">Rotate API key</button></form>
<form method="post" action="/auth/apps/{{ auth_app.id }}/delete" class="auth-action" onsubmit="return confirm('Delete this app and all its users?')"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="delete" type="submit">Delete app and users</button></form></section>
<section class="form-card create-user-card"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="4"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M19 8v6m3-3h-6"/></svg>Create a user</h2><p class="muted auth-card-intro">Each key-enabled user receives a unique product key. It is displayed after creation and cannot be viewed again.</p>
<form method="post" action="/auth/apps/{{ auth_app.id }}/users/create"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><div class="auth-user-create">
<label>Username<input class="text-input" name="username" maxlength="80" required></label>
<label>Auth method<select class="text-input" name="auth_mode"><option value="password">Username + password</option><option value="product_key">Product key</option><option value="both">Username + password + key</option></select></label>
<label>Password (8+ characters for password modes)<input class="text-input" type="password" name="password" autocomplete="new-password"></label>
<label>Expires (UTC, optional)<input class="text-input" type="datetime-local" name="expires_at"></label>
</div><button class="button primary auth-action" type="submit">Create user</button></form></section>
<div class="section-title">Users · {{ users|length }}</div>{% if users %}<div class="auth-user-list">{% for user in users %}
<section class="form-card auth-user-card"><div class="auth-user-head"><div><strong>{{ user.username }}</strong><div class="hint">{{ user.auth_mode|replace('_',' ') }} · {{ user.status }} · created {{ user.created|int|datetime }}{% if user.last_login %} · last login {{ user.last_login|int|datetime }}{% endif %}</div>{% if user.auth_mode in ['product_key','both'] %}<div class="user-key-label">Unique product key assigned to this user · use “Replace key” to issue a new one.</div>{% endif %}
{% if user.expires_at %}<div class="hint">Expires {{ user.expires_at|int|datetime }} UTC</div>{% else %}<div class="hint">No expiration</div>{% endif %}</div>
<div class="auth-actions"><form method="post" action="/auth/apps/{{ auth_app.id }}/users/{{ user.id }}/toggle"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button" type="submit">{% if user.status == 'active' %}Disable{% else %}Enable{% endif %}</button></form>
{% if user.auth_mode in ['product_key','both'] %}<form method="post" action="/auth/apps/{{ auth_app.id }}/users/{{ user.id }}/rotate-key" onsubmit="return confirm('Revoke this user's current product key?')"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button" type="submit">Replace key</button></form>{% endif %}
<form method="post" action="/auth/apps/{{ auth_app.id }}/users/{{ user.id }}/delete" onsubmit="return confirm('Delete this user?')"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="delete" type="submit">Delete</button></form></div></div>
<form method="post" action="/auth/apps/{{ auth_app.id }}/users/{{ user.id }}/expiry" class="auth-expiry"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><label>Expiration (UTC; blank means never)<input class="text-input" type="datetime-local" name="expires_at" value="{{ user.expires_local }}"></label><button class="button" type="submit">Save expiry</button></form>
{% if user.auth_mode in ['password','both'] %}<form method="post" action="/auth/apps/{{ auth_app.id }}/users/{{ user.id }}/password" class="auth-expiry"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><label>Set a new password<input class="text-input" type="password" name="password" minlength="8" required autocomplete="new-password"></label><button class="button" type="submit">Reset password</button></form>{% endif %}</section>
{% endfor %}</div>{% else %}<section class="form-card empty">No users in this app yet.</section>{% endif %}</main>''' + THEME_SCRIPT + r'''</body></html>'''


AUTH_DOCS_PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Auth API docs · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body class="auth-page">
<header class="top"><a class="brand" href="/">Relay</a><nav class="topnav">
<a class="plain" href="/">Webhooks</a><a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><a class="plain" href="/settings">Settings</a>
<button class="theme" id="theme-toggle" type="button">Light / dark</button><form method="post" action="/logout"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button">Sign out</button></form>
</nav></header><main><h1>Auth API</h1><p class="muted">Use this server-to-server endpoint to check credentials for an app.</p>
<section class="form-card"><h2>Endpoint</h2><p><code>POST /api/auth/APP_ID/login</code></p><p>Send the app API key in <code>Authorization: Bearer APP_API_KEY</code> and a JSON body containing the credentials.</p><p>The API key identifies an app and can only check credentials. It cannot create apps or manage users. Keep it on your server; do not bundle it in a public client.</p></section>
<section class="form-card"><h2>Username and password</h2><pre><code>curl -X POST 'https://YOUR_HOST/api/auth/1/login' \
  -H 'Authorization: Bearer YOUR_APP_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"user-password"}'</code></pre></section>
<section class="form-card"><h2>Product key</h2><pre><code>curl -X POST 'https://YOUR_HOST/api/auth/1/login' \
  -H 'Authorization: Bearer YOUR_APP_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"product_key":"RLY-YOUR-KEY"}'</code></pre></section>
<section class="form-card"><h2>Both username/password and product key</h2><pre><code>{"username":"alice","password":"user-password","product_key":"RLY-YOUR-KEY"}</code></pre><p>For accounts created with the “both” method, all three fields must match the same user.</p></section>
<section class="form-card"><h2>Responses</h2><p>Success returns HTTP 200 with <code>authenticated: true</code> and the username and expiration timestamp.</p><pre><code>{"authenticated":true,"user":{"username":"alice","expires_at":null}}</code></pre><p>Invalid, disabled, or expired credentials return HTTP 401. Requests are limited to 30 attempts per app and client IP per minute. This endpoint verifies credentials only; it does not issue a session or access token. Use HTTPS whenever credentials cross a network.</p></section>
<section class="form-card"><h2>Python example</h2><pre><code>import requests

response = requests.post(
    "https://YOUR_HOST/api/auth/1/login",
    headers={"Authorization": "Bearer YOUR_APP_API_KEY"},
    json={"username": "alice", "password": "user-password"},
    timeout=10,
)
result = response.json()
if response.ok and result.get("authenticated"):
    print("Access granted")</code></pre></section>
</main>''' + THEME_SCRIPT + r'''</body></html>'''


from panel_ui import enhance_page
from api_docs import expand_docs
from auth_workspace import app_workspace, home_workspace

AUTH_HOME_PAGE = enhance_page(home_workspace(AUTH_HOME_PAGE))
AUTH_APP_PAGE = enhance_page(app_workspace(AUTH_APP_PAGE))
AUTH_DOCS_PAGE = enhance_page(expand_docs(AUTH_DOCS_PAGE))

__all__ = ["AUTH_APP_PAGE", "AUTH_DOCS_PAGE", "AUTH_HOME_PAGE"]
