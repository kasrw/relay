"""Apply the same presentation assets to every panel page."""

import re
import os

PANEL_PATH = os.environ.get("PANEL_PATH", "relay").strip("/")
PANEL_BASE = "/" + PANEL_PATH

HEADER = '''<header class="top panel-header"><div class="header-left"><a class="brand" href="/">Relay</a><nav class="topnav" aria-label="Main navigation"><a class="plain" href="/">Webhooks</a><a class="plain" href="/auth">Auth</a><a class="plain" href="/shares">Shares</a><a class="plain" href="/api-docs">API Docs</a></nav></div><a class="plain settings-link" href="/settings"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4 7v5c0 5 3 8 8 10 5-2 8-5 8-10V7z"/><circle cx="12" cy="11" r="3"/></svg>Settings</a></header>'''


def enhance_page(source, replace_header=True):
    if replace_header:
        source = re.sub(r'<header class="top">.*?</header>', lambda _: HEADER, source, count=1, flags=re.S)
    public_roots = ("/wbhk/", "/webhook/", "/api/auth/", "/p/")

    def prefix_attribute(match):
        attribute, quote, value = match.groups()
        if value.startswith("//") or value.startswith(public_roots):
            return match.group(0)
        if value == PANEL_BASE or value.startswith(PANEL_BASE + "/"):
            return match.group(0)
        return f'{attribute}={quote}{PANEL_BASE}{value}{quote}'

    source = re.sub(r'\b(href|action|src|formaction)=("|\')(/[^"\']*)\2', prefix_attribute, source)
    return source.replace(
        "</head>",
        f'<meta name="panel-base" content="{PANEL_BASE}">'
        f'<link rel="stylesheet" href="{PANEL_BASE}/static/panel.css">'
        f'<script src="{PANEL_BASE}/static/panel.js" defer></script></head>',
        1,
    )
