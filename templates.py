"""HTML templates and the shared styles for the Relay panel."""


# Shared panel styles
SIMPLE_CSS = r'''
:root{color-scheme:dark;--bg:#080808;--card:#111;--line:#292929;--text:#f5f5f5;--muted:#a0a0a0;--button:#f2f2f2;--buttonText:#111}body.light{color-scheme:light;--bg:#f5f5f5;--card:#fff;--line:#dedede;--text:#141414;--muted:#666;--button:#161616;--buttonText:#fff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit;text-decoration:none}button,input{font:inherit}.top{height:68px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 max(22px,calc((100vw - 920px)/2))}.brand{font-weight:750;letter-spacing:-.03em}.topnav{display:flex;align-items:center;gap:10px}.topnav form{margin:0}.plain{color:var(--muted);padding:7px 10px}.button,.theme,.delete{border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--text);padding:8px 12px;cursor:pointer}.button:hover,.theme:hover{background:var(--button);color:var(--buttonText)}.delete{color:var(--text)}.delete:hover{background:#333}main{max-width:920px;margin:38px auto;padding:0 22px}h1{font-size:26px;letter-spacing:-.04em;margin:0 0 6px}.muted{color:var(--muted);margin:0}.section-title{margin:30px 0 12px;font-size:14px;color:var(--muted);font-weight:600}.form-card,.hookbox,.message,.side{background:var(--card);border:1px solid var(--line);border-radius:12px}.form-card{padding:18px;margin-top:20px}.fields{display:grid;grid-template-columns:1fr 1fr auto;gap:10px}.text-input{width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text)}.button.primary{background:var(--button);color:var(--buttonText);font-weight:700}.hint{font-size:12px;color:var(--muted);margin:10px 0 0}.notice{padding:11px 13px;margin:15px 0;border:1px solid var(--line);border-radius:8px;color:var(--text)}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:13px}.hookbox{padding:20px;min-height:140px;display:grid;grid-template-columns:1fr auto;align-items:center;transition:border-color .15s,transform .15s}.hookbox:hover{border-color:var(--text);transform:translateY(-2px)}.hook-name{font-size:18px;font-weight:700;overflow-wrap:anywhere}.hook-path{font-size:13px;color:var(--muted);margin-top:5px;overflow-wrap:anywhere}.hook-count{font-size:12px;color:var(--muted);margin-top:12px}.hook-title-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.unread-badge{display:inline-flex;align-items:center;gap:5px;border:1px solid #71302d;border-radius:999px;background:#351614;color:#ffcbc6;padding:3px 8px;font-size:11px;font-weight:700;white-space:nowrap}body.light .unread-badge{border-color:#dc7770;background:#fff0ef;color:#a31313}.user-list{display:grid;gap:8px;padding:11px}.user-row{display:flex;align-items:center;gap:11px;padding:13px;border:1px solid var(--line);border-radius:10px;background:var(--bg);transition:transform .16s ease,border-color .16s ease,background .16s ease}.user-row:hover{border-color:var(--text);background:var(--card);transform:translateY(-1px)}.user-avatar{width:36px;height:36px;flex:none;border:1px solid var(--line);border-radius:10px;display:grid;place-items:center;font-size:13px;font-weight:750;background:var(--card)}.user-details{min-width:0;flex:1}.user-name{font-size:14px;font-weight:700;overflow-wrap:anywhere}.user-message-count{font-size:12px;color:var(--muted);margin-top:2px}.user-arrow{width:17px;height:17px;flex:none;color:var(--muted);transition:transform .16s ease}.user-row:hover .user-arrow{transform:translateX(3px)}.user-back{display:inline-flex;margin-bottom:9px}.active-user{color:hsl(var(--user-hue) 76% 66%)}body.light .active-user{color:hsl(var(--user-hue) 72% 34%)}.arrow{font-size:24px;color:var(--muted);padding-left:12px}.row{display:flex;align-items:end;justify-content:space-between;gap:18px}.columns{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:14px;align-items:start}.feed-head{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;color:var(--muted);font-size:13px}.message-list{display:grid;gap:9px;padding:11px}.message{padding:14px;display:grid;grid-template-columns:30px minmax(0,1fr) auto;gap:10px}.avatar{width:29px;height:29px;border:1px solid var(--line);border-radius:8px;display:grid;place-items:center;color:var(--muted);font-size:12px}.msg-top{display:flex;gap:9px;align-items:center}.msg-top b{font-size:13px}.time,.msg-action{font-size:11px;color:var(--muted)}.content{white-space:pre-wrap;overflow-wrap:anywhere;margin-top:5px}.files{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.file{border:1px solid var(--line);border-radius:8px;overflow:hidden}.file img,.file video{display:block;max-width:min(100%,300px);max-height:200px}.file a{display:flex;gap:8px;padding:8px;color:var(--text);font-size:12px}.pager{display:flex;align-items:center;justify-content:center;gap:8px;padding:12px;color:var(--muted);font-size:13px}.disabled{opacity:.4;pointer-events:none}.empty{text-align:center;padding:35px;color:var(--muted)}.side{padding:16px}.side h2{font-size:14px;margin:0 0 9px}.side p{font-size:12px;color:var(--muted)}.side input{font-size:11px;margin:5px 0 8px}.side .button,.side .delete{width:100%}.side-section{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}.login{max-width:380px;margin:12vh auto}.csrf{display:none!important}@media(max-width:700px){main{margin:26px auto}.fields{grid-template-columns:1fr}.columns{grid-template-columns:1fr}.row{align-items:start;flex-direction:column}.message{grid-template-columns:28px minmax(0,1fr)}.msg-action{grid-column:2}.top{padding:0 16px}}
'''

# Theme toggle
THEME_SCRIPT = r'''<script>(function(){const b=document.body;const saved=localStorage.getItem('relay-theme');if(saved==='light')b.classList.add('light');document.getElementById('theme-toggle')?.addEventListener('click',()=>{b.classList.toggle('light');localStorage.setItem('relay-theme',b.classList.contains('light')?'light':'dark')})})()</script>'''

# Shared panel styles
SIMPLE_CSS += r'''
.login-wrap{min-height:100vh;display:grid;place-items:center;padding:20px}.login-card{width:min(390px,100%);padding:25px;border:1px solid var(--line);border-radius:12px;background:var(--card)}.login-card h1{margin-bottom:8px}.login-card .text-input{margin:17px 0 11px}.login-card .button{width:100%}.error{min-height:22px;color:#d33}
.button,.theme,.delete{transition:background .18s ease,color .18s ease,border-color .18s ease,transform .18s ease,box-shadow .18s ease}.button:hover,.theme:hover,.delete:hover{transform:translateY(-1px);box-shadow:0 5px 16px #0003}.hookbox{animation:rise .35s both}.hookbox:nth-child(2){animation-delay:.04s}.hookbox:nth-child(3){animation-delay:.08s}.hookbox:nth-child(4){animation-delay:.12s}.message{animation:rise .24s both}.file{transition:border-color .16s ease,transform .16s ease}.file:hover{border-color:var(--text);transform:translateY(-2px)}.file-line{display:flex;align-items:center;gap:8px;padding:9px 10px;font-size:12px;overflow-wrap:anywhere}.file-icon{width:18px;height:18px;flex:none;color:var(--muted)}.download{border-top:1px solid var(--line);font-weight:600}.username{color:hsl(var(--user-hue) 76% 66%)}body.light .username{color:hsl(var(--user-hue) 72% 34%)}.delete{border-color:#a92525;background:#341414;color:#ffdada;display:inline-flex;align-items:center;gap:6px}.delete:hover{background:#651b1b;border-color:#ee5555;color:white}body.light .delete{background:#fff0f0;color:#a31313;border-color:#d95353}body.light .delete:hover{background:#c92020;color:#fff}.delete svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.icon{width:17px;height:17px;vertical-align:-3px;margin-right:5px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.button.primary{display:inline-flex;align-items:center;gap:7px}.hookbox:hover .arrow{transform:translateX(4px)}.arrow{transition:transform .18s ease}.text-input:focus{outline:2px solid #888;outline-offset:1px}@keyframes rise{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}}
'''

# Keep usernames and their message counts on separate lines in the list.
SIMPLE_CSS += r'''
.user-details{display:grid}
'''

SIMPLE_CSS += r'''
.side-pager{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.side-pager .button{text-align:center;padding:7px 5px;font-size:12px}.side-page-status{grid-column:1/-1;text-align:center;color:var(--muted);font-size:12px;padding-top:2px}.side-search{display:flex;align-items:center;gap:7px}.side-search .text-input{flex:1;min-width:0;width:auto;margin:0;font-size:13px}.side-search .button{width:auto;flex:none;padding:8px}.side-search .icon{margin:0}
'''

SIMPLE_CSS += r'''
.side{display:grid;align-content:start;gap:12px;padding:0;border:0;border-radius:0;background:transparent}.side-box{padding:16px;background:var(--card);border:1px solid var(--line);border-radius:12px;transition:border-color .16s ease}.side-box:hover{border-color:#555}.side-box>h2{margin:0 0 10px}.side-box>p{margin:0 0 10px}.side-box .side-section{margin-top:14px;padding-top:14px}
'''

SIMPLE_CSS += r'''
.hookbox{background:linear-gradient(140deg,hsl(var(--hook-hue) 40% 16%),var(--card) 78%);border-color:hsl(var(--hook-hue) 35% 28%)}.hookbox:hover{border-color:hsl(var(--hook-hue) 70% 60%)}body.light .hookbox{background:linear-gradient(140deg,hsl(var(--hook-hue) 55% 94%),var(--card) 78%);border-color:hsl(var(--hook-hue) 38% 82%)}.hook-count{display:flex;align-items:center;gap:6px}.user-count-icon{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
'''

# Webhook message center
MESSAGE_CENTER = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ hook.name }} · Relay</title>
<style>''' + SIMPLE_CSS + r'''</style>
</head>
<body>
<header class="top">
  <a class="brand" href="/">Relay <span class="muted">/ {{ hook.name }}</span></a>
  <nav class="topnav">
    <a class="plain" href="/">← Webhooks</a>
    <a class="plain" href="/settings">Settings</a>
    <button class="theme" id="theme-toggle" type="button">Light / dark</button>
    <form method="post" action="/logout">
      <input class="csrf" type="hidden" name="csrf" value="{{ csrf }}">
      <button class="button">Sign out</button>
    </form>
  </nav>
</header>
<main>
  <div class="row">
    <div>
      <div class="section-title" style="margin:0 0 5px">Message center</div>
      {% if active_user is not none %}
      <a class="plain user-back" href="{{ url_for('webhook_messages', webhook_id=hook.id) }}">← All usernames</a>
      <h1 class="active-user" style="--user-hue:{{ active_user_hue }}">{{ active_user }}</h1>
      <p class="muted">ID {{ active_user_id }} · {{ total }} messages</p>
      {% else %}
      <h1>{{ hook.name }}</h1>
      <p class="muted">{{ users|length }} users · {{ total }} messages</p>
      {% endif %}
    </div>
  </div>
  <div class="columns" style="margin-top:18px">
    <section class="form-card" style="margin:0;padding:0">
      {% if active_user is none %}
      <div class="feed-head"><span>Users</span><span>{{ users|length }} user IDs</span></div>
      {% if users %}
      <div class="user-list">
        {% for user in users %}
        <a class="user-row" href="{{ url_for('webhook_messages', webhook_id=hook.id, user_id=user.sender_id, q=search_query) }}">
          <span class="user-avatar" style="--user-hue:{{ user.user_hue }};color:hsl(var(--user-hue) 76% 66%)">{{ user.source[:1]|upper }}</span>
          <span class="user-details">
            <span class="user-name" style="--user-hue:{{ user.user_hue }};color:hsl(var(--user-hue) 76% 66%)">{{ user.source }}</span>
            <span class="user-message-count">ID {{ user.sender_id }}</span>
            <span class="user-message-count">{{ user.message_count }} messages</span>
          </span>
          <svg class="user-arrow" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>
        </a>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty">No users or messages yet.</div>
      {% endif %}
      {% else %}
      <div class="feed-head">
        <span>Messages from <b class="active-user" style="--user-hue:{{ active_user_hue }}">{{ active_user }}</b> <span class="muted">(ID {{ active_user_id }})</span></span>
        <span>{{ page }} / {{ pages }}</span>
      </div>
      {% if messages %}
      <div class="message-list">
        {% for message in messages %}
        <article class="message">
          <div class="avatar">{{ (message.source or 'W')[:1]|upper }}</div>
          <div>
            <div class="msg-top">
              <b class="username" style="--user-hue:{{ message.user_hue }}">{{ message.source }}</b>
              <span class="time">ID {{ message.sender_id }}</span>
              <span class="time">{{ message.created|int|datetime }}</span>
            </div>
            {% if message.content %}<div class="content">{{ message.content }}</div>{% endif %}
            {% if message.files %}
            <div class="files">
              {% for file in message.files %}
              <div class="file">
                <span class="file-line">
                  <svg class="file-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                    {% if file.mime.startswith('image/') %}<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m21 15-5-5L5 20"/>
                    {% elif file.mime.startswith('video/') %}<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9 5 3-5 3z"/>
                    {% elif file.name.lower().endswith(('.zip','.rar','.7z')) %}<path d="M5 4h14v16H5zM9 4v4h6V4M9 12h6M9 16h6"/>
                    {% elif file.mime.startswith('text/') or file.name.lower().endswith(('.txt','.log','.md','.csv')) %}<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7"/>
                    {% else %}<path d="m8 12 5-5a3 3 0 0 1 4 4l-7 7a4 4 0 0 1-6-6l7-7"/>{% endif %}
                  </svg>
                  <span>{{ file.name }} · {{ (file.size/1048576)|round(1) }} MB</span>
                </span>
                {% if file.mime in ['image/jpeg','image/png','image/gif','image/webp','image/avif'] %}
                <a href="/files/{{ file.id }}" target="_blank" rel="noopener"><img src="/files/{{ file.id }}" alt="{{ file.name }}"></a>
                {% elif file.mime in ['video/mp4','video/webm','video/ogg'] %}
                <video src="/files/{{ file.id }}" controls preload="metadata"></video>
                {% endif %}
                <a class="download" href="/files/{{ file.id }}" download="{{ file.name }}">Download file</a>
              </div>
              {% endfor %}
            </div>
            {% endif %}
          </div>
          <div class="msg-action">
            <form method="post" action="/webhooks/{{ hook.id }}/messages/{{ message.id }}/delete" onsubmit="return confirm('Delete this message and its attachments?')">
              <input class="csrf" type="hidden" name="csrf" value="{{ csrf }}">
              <input type="hidden" name="return_user_id" value="{{ active_user_id }}">
              <input type="hidden" name="return_query" value="{{ search_query }}">
              <input type="hidden" name="return_page" value="{{ page }}">
              <button class="delete"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg>Delete</button>
            </form>
          </div>
        </article>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty">No messages from this user ID yet.</div>
      {% endif %}
      {% endif %}
    </section>
    <aside class="side">
      {% if active_user is not none %}
      <section class="side-box side-pager-wrap">
        <h2>Pages</h2>
        <nav class="side-pager" aria-label="Message pages">
          <a class="button {% if page == 1 %}disabled{% endif %}" href="{{ url_for('webhook_messages', webhook_id=hook.id, user_id=active_user_id, q=search_query, page=1) }}">First</a>
          <a class="button {% if page == 1 %}disabled{% endif %}" href="{{ url_for('webhook_messages', webhook_id=hook.id, user_id=active_user_id, q=search_query, page=page-1) }}">← Prev</a>
          <a class="button {% if page == pages %}disabled{% endif %}" href="{{ url_for('webhook_messages', webhook_id=hook.id, user_id=active_user_id, q=search_query, page=page+1) }}">Next →</a>
          <a class="button {% if page == pages %}disabled{% endif %}" href="{{ url_for('webhook_messages', webhook_id=hook.id, user_id=active_user_id, q=search_query, page=pages) }}">Last</a>
          <span class="side-page-status">Page {{ page }} of {{ pages }}</span>
        </nav>
      </section>
      {% endif %}
      <section class="side-box">
        <h2>Search</h2>
        <form class="side-search" method="get" action="{{ url_for('webhook_messages', webhook_id=hook.id) }}" role="search">
          {% if active_user is not none %}<input type="hidden" name="user_id" value="{{ active_user_id }}">{% endif %}
          <input class="text-input" type="search" name="q" value="{{ search_query }}" placeholder="{% if active_user is none %}Search user IDs and usernames{% else %}Search messages and files{% endif %}" aria-label="{% if active_user is none %}Search user IDs and usernames{% else %}Search messages and files{% endif %}">
          <button class="button" type="submit" aria-label="Search">
            <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>
          </button>
        </form>
      </section>
      <section class="side-box">
        <h2>Webhook management</h2>
        <p>Webhook URL · send a POST request to this private address.</p>
        <input class="text-input" id="hook-url" readonly value="{{ hook.url }}">
        <button class="button" type="button" onclick="navigator.clipboard.writeText(document.getElementById('hook-url').value)">Copy URL</button>
        <div class="side-section">
        <form method="post" action="/webhooks/{{ hook.id }}/delete" onsubmit="return confirm('Delete this webhook and all its messages and files?')">
          <input class="csrf" type="hidden" name="csrf" value="{{ csrf }}">
          <button class="delete"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7"/></svg>Delete webhook</button>
        </form>
        </div>
        <p class="hint">Maximum {{ limit_mb }} MB per message.</p>
      </section>
    </aside>
  </div>
</main>
''' + THEME_SCRIPT + r'''</body>
</html>'''

# Webhook list
PANEL_HOME = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Webhooks · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body><header class="top"><a class="brand" href="/">Relay</a><nav class="topnav"><a class="plain" href="/settings"><svg class="icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.6.9l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.6-.9l-1.7.7-1.4-2.4 1.4-1.1a8 8 0 0 1 0-1.9l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.6-.9l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.6.9l1.7-.7 1.4 2.4-1.4 1.1a8 8 0 0 1 0 1.9z"/></svg>Settings</a><button class="theme" id="theme-toggle" type="button">Light / dark</button><form method="post" action="/logout"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button">Sign out</button></form></nav></header><main><h1>Webhooks</h1><p class="muted">Create an endpoint, then open it to see its messages.</p>
{% if request.args.get('created') %}<div class="notice">Webhook created: /wbhk/{{ request.args.get('created') }}</div>{% elif request.args.get('error') == 'duplicate' %}<div class="notice">That path is already in use. Choose another one.</div>{% elif request.args.get('error') == 'invalid' %}<div class="notice">Enter a name and a path using letters, numbers, hyphens, or underscores.</div>{% endif %}
<form class="form-card" method="post" action="/webhooks/create"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><div class="section-title" style="margin:0 0 12px;color:var(--text)"><svg class="icon" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Create a webhook</div><div class="fields"><input class="text-input" name="name" maxlength="80" placeholder="Name" required><input class="text-input" name="slug" maxlength="63" pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}" placeholder="Path, e.g. alerts-prod" required><button class="button primary"><svg class="icon" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>Create webhook</button></div><p class="hint">{{ webhooks|length }} webhooks · path format /wbhk/your-path</p></form>
{% if webhooks %}<div class="section-title">Your webhooks</div><section class="cards">{% for hook in webhooks %}<a class="hookbox" style="--hook-hue:{{ (hook.id * 67) % 360 }}" href="/webhooks/{{ hook.id }}"><div><div class="hook-title-row"><div class="hook-name">{{ hook.name }}</div>{% if hook.unread_count %}<span class="unread-badge" aria-label="{{ hook.unread_count }} unread messages">{{ hook.unread_count }} new</span>{% endif %}</div><div class="hook-path">/wbhk/{{ hook.slug }}</div><div class="hook-count"><svg class="user-count-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>{{ hook.user_count }} users</div></div><div class="arrow"><svg class="icon" viewBox="0 0 24 24"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></div></a>{% endfor %}</section>{% endif %}</main>''' + THEME_SCRIPT + r'''</body></html>'''

# Panel settings
SETTINGS_PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Settings · Relay</title><style>''' + SIMPLE_CSS + r'''</style></head><body><header class="top"><a class="brand" href="/">Relay</a><nav class="topnav"><a class="plain" href="/">← Webhooks</a><button class="theme" id="theme-toggle" type="button">Light / dark</button><form method="post" action="/logout"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button">Sign out</button></form></nav></header><main><h1>Settings</h1><p class="muted">Panel access and upload limits.</p>{% if saved %}<div class="notice">Settings saved.</div>{% elif error %}<div class="notice">{% if error == 'current' %}Current password is incorrect.{% elif error == 'new' %}New passwords must match and be at least 12 characters.{% elif error == 'message-limit' %}Choose a message limit from 1 to {{ max_limit_mb }} MB.{% else %}The setting value is invalid. Please try again.{% endif %}</div>{% endif %}<section class="form-card"><h2><svg class="icon" viewBox="0 0 24 24"><path d="M12 3 5 6v5c0 5 3 8 7 10 4-2 7-5 7-10V6z"/><path d="M9 12h6"/></svg>Maximum per message</h2><p class="muted">{{ message_mb }} MB currently · choose from 1 to {{ max_limit_mb }} MB.</p><form method="post" action="/settings/message-limit"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><div class="fields"><input class="text-input" type="number" name="limit" min="1" max="{{ max_limit_mb }}" value="{{ message_mb }}" required><span></span><button class="button primary">Save size limit</button></div></form></section><section class="form-card"><h2>Change panel password</h2><p class="muted">Use at least 12 characters.</p><form method="post" action="/settings/password"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><div class="fields"><input class="text-input" type="password" name="current" placeholder="Current password" required><input class="text-input" type="password" name="new" placeholder="New password (12+ characters)" minlength="12" required><input class="text-input" type="password" name="confirm" placeholder="Confirm new password" minlength="12" required></div><button class="button primary" style="margin-top:10px">Change password</button></form></section></main>''' + THEME_SCRIPT + r'''</body></html>'''

# Panel sign-in
LOGIN_HTML_NEW = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Relay · Sign in</title><style>''' + SIMPLE_CSS + r'''</style></head><body><div class="login-wrap"><form class="login-card" method="post"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><h1>Relay</h1><p class="muted">Sign in to manage your webhooks.</p><input class="text-input" name="password" type="password" placeholder="Panel password" required autofocus><div class="error">{{ error }}</div><button class="button primary">Sign in</button></form></div></body></html>'''

SETTINGS_PAGE = SETTINGS_PAGE.replace(
    "</main>",
    r'''<section class="form-card"><h2>Telegram notifications and backups</h2>
<p class="muted">{% if telegram_configured %}Bot configured for chat {{ telegram_chat_id }}. The saved token is hidden.{% else %}Add a Telegram bot token and destination chat ID to enable new-user alerts and manual backups.{% endif %}</p>
{% if telegram_status == 'saved' %}<div class="notice">Telegram settings saved.</div>{% elif telegram_status == 'disabled' %}<div class="notice">Telegram integration disabled.</div>{% elif telegram_status == 'tested' %}<div class="notice">Test message sent successfully.</div>{% elif telegram_status == 'missing' %}<div class="notice">Save a bot token and chat ID first.</div>{% elif telegram_status == 'invalid' %}<div class="notice">Both a valid bot token and a chat ID are required.</div>{% elif telegram_error %}<div class="notice">Telegram test failed: {{ telegram_error }}</div>{% endif %}
<form method="post" action="/settings/telegram"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><div style="display:grid;gap:10px"><input class="text-input" type="password" name="bot_token" autocomplete="new-password" placeholder="{% if telegram_configured %}Bot token (leave blank to keep current){% else %}Telegram bot token{% endif %}"><input class="text-input" name="chat_id" value="{{ telegram_chat_id }}" placeholder="Chat ID" autocomplete="off"><button class="button primary" type="submit">Save Telegram settings</button></div></form>
<p class="hint">To disable Telegram, clear both fields and save. Keep the bot token private; it is stored in the Relay database.</p>
<form method="post" action="/settings/telegram/test" style="margin-top:12px"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button" type="submit" {% if not telegram_configured %}disabled{% endif %}>Test bot and send a test message</button></form>
</section></main>''',
)

MESSAGE_CENTER = MESSAGE_CENTER.replace(
    '      <section class="side-box">\n        <h2>Search</h2>',
    r'''      {% if active_user is not none %}
      {% if telegram_backup == 'done' %}<div class="notice">User backup sent. {{ backup_sent }} file parts uploaded{% if backup_skipped %}; {{ backup_skipped }} missing files skipped.{% endif %}</div>{% elif telegram_backup == 'failed' %}<div class="notice">Telegram backup failed. Check the Telegram settings and server connection; some earlier items may already have been sent.</div>{% elif telegram_backup == 'missing' %}<div class="notice">Configure Telegram in Settings before sending a backup.</div>{% elif telegram_backup == 'missing-user' %}<div class="notice">This user or webhook no longer exists.</div>{% endif %}
      {% endif %}
      <section class="side-box">
        <h2>Search</h2>''',
)

MESSAGE_CENTER = MESSAGE_CENTER.replace(
    '      </section>\n      <section class="side-box">\n        <h2>Webhook management</h2>',
    r'''      </section>
      {% if active_user is not none %}<section class="side-box telegram-backup-box"><h2><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m21 3-7.4 18-3.8-7.8L2 9.4 21 3Z"/><path d="m9.8 13.2 5.4-5.4"/></svg>Telegram backup</h2><p>Send this user's full message history and eligible attachments to the configured chat.</p><form method="post" action="/webhooks/{{ hook.id }}/users/{{ active_user_id }}/telegram-backup" onsubmit="return confirm('Send this user’s message history and attachments to Telegram?')"><input class="csrf" type="hidden" name="csrf" value="{{ csrf }}"><button class="button" type="submit">Send user backup to Telegram</button></form></section>{% endif %}
      <section class="side-box">
        <h2>Webhook management</h2>''',
)

SIMPLE_CSS += r'''
.auth-create{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px}.auth-user-create{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.auth-user-create label,.auth-expiry label{display:grid;gap:5px;font-size:12px;color:var(--muted)}.auth-action{margin-top:10px}.auth-user-list{display:grid;gap:12px}.auth-user-card{margin:0}.auth-user-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.auth-actions{display:flex;gap:8px;flex-wrap:wrap}.auth-expiry{display:flex;gap:9px;align-items:end;margin-top:12px;flex-wrap:wrap}.auth-expiry .text-input{min-width:220px}.secret-key{display:block;overflow-wrap:anywhere;padding:12px;background:var(--bg);border:1px solid var(--line);border-radius:8px}pre{overflow:auto;padding:14px;background:var(--bg);border:1px solid var(--line);border-radius:8px;white-space:pre-wrap}code{overflow-wrap:anywhere}@media(max-width:700px){.auth-create{grid-template-columns:1fr}.topnav{gap:4px}.topnav .plain{padding:6px 5px;font-size:12px}}
'''

# Keep the primary sections beside the Relay brand across existing pages.
PANEL_HOME = PANEL_HOME.replace(
    '<a class="plain" href="/settings"><svg class="icon"',
    '<a class="plain" href="/">Webhooks</a><a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><a class="plain" href="/settings"><svg class="icon"',
)
MESSAGE_CENTER = MESSAGE_CENTER.replace(
    '<a class="plain" href="/settings">Settings</a>',
    '<a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><a class="plain" href="/settings">Settings</a>',
)
MESSAGE_CENTER = MESSAGE_CENTER.replace(
    '</style>',
    '.telegram-backup-box{border-color:#454545;background:linear-gradient(145deg,#171717,var(--card) 72%)}.telegram-backup-box:hover{border-color:#777}.telegram-backup-box .button{background:#f0f0f0;color:#151515;font-weight:700}.telegram-backup-box .button:hover{background:#d8d8d8}</style>',
    1,
)
SETTINGS_PAGE = SETTINGS_PAGE.replace(
    '<button class="theme" id="theme-toggle"',
    '<a class="plain" href="/auth">Auth</a><a class="plain" href="/api-docs">API Docs</a><button class="theme" id="theme-toggle"',
)

SIMPLE_CSS += r'''
body.auth-page{background-image:radial-gradient(ellipse at 12% 0%,#252525 0,transparent 38%),radial-gradient(ellipse at 95% 35%,#191919 0,transparent 30%);background-attachment:fixed}body.light.auth-page{background-image:radial-gradient(ellipse at 12% 0%,#e8e8e8 0,transparent 40%),radial-gradient(ellipse at 95% 35%,#eee 0,transparent 32%)}.auth-page .top{backdrop-filter:blur(14px);background:color-mix(in srgb,var(--bg) 84%,transparent);position:sticky;top:0;z-index:5}.auth-page main{max-width:1020px;margin-top:44px;margin-bottom:64px}.auth-page h1{font-size:clamp(28px,4vw,36px);letter-spacing:-.05em}.auth-page .form-card,.auth-page .hookbox{box-shadow:0 12px 32px #0002}.auth-page .form-card{transition:border-color .2s ease,transform .2s ease,box-shadow .2s ease}.auth-page .form-card:hover{border-color:#555;box-shadow:0 16px 38px #0003}.auth-page .form-card h2{display:flex;align-items:center;gap:4px;font-size:17px;letter-spacing:-.02em;margin:0 0 9px}.auth-page .auth-card-intro{margin:0 0 15px}.auth-page .section-title{font-size:13px;letter-spacing:.08em;text-transform:uppercase}.auth-page .secret-key{font:600 13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;background:color-mix(in srgb,var(--bg) 80%,#222);border-color:#444}.user-key-card{border-color:#686868;background:linear-gradient(135deg,color-mix(in srgb,var(--card) 86%,#444),var(--card) 65%)}.key-eyebrow{font-size:10px;font-weight:800;letter-spacing:.12em;color:var(--muted);margin-bottom:5px}.auth-user-card{position:relative;overflow:hidden}.auth-user-card:before{content:"";position:absolute;inset:0 auto 0 0;width:3px;background:linear-gradient(180deg,#fafafa,#777);opacity:.65}.user-key-label{font-size:11px;color:var(--muted);margin-top:5px}.auth-actions .button,.auth-actions .delete{min-height:38px}.auth-page .text-input{transition:border-color .16s ease,box-shadow .16s ease}.auth-page .text-input:focus{border-color:#aaa;box-shadow:0 0 0 3px #8882;outline:0}.auth-page .plain{border-radius:8px;transition:background .16s ease,color .16s ease}.auth-page .plain:hover{background:var(--card);color:var(--text)}.telegram-backup-box{order:2}.telegram-backup-box h2{display:flex;align-items:center}.telegram-backup-box .button{background:#f0f0f0;color:#151515;font-weight:700}.telegram-backup-box .button:hover{background:#d8d8d8}@media(max-width:700px){.auth-page .top{height:auto;min-height:68px;gap:8px;align-items:flex-start;flex-direction:column;padding:12px 16px}.auth-page .topnav{width:100%;flex-wrap:wrap;justify-content:flex-start}.auth-page main{margin-top:28px}.auth-page .auth-expiry{align-items:stretch;flex-direction:column}.auth-page .auth-expiry .text-input{min-width:0}}
'''

from panel_ui import enhance_page
from settings_ui import redesign_settings

LOGIN_HTML_NEW = enhance_page(LOGIN_HTML_NEW)
MESSAGE_CENTER = enhance_page(MESSAGE_CENTER)
PANEL_HOME = enhance_page(PANEL_HOME)
SETTINGS_PAGE = enhance_page(redesign_settings(SETTINGS_PAGE))

__all__ = ["LOGIN_HTML_NEW", "MESSAGE_CENTER", "PANEL_HOME", "SETTINGS_PAGE"]
