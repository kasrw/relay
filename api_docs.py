"""API reference and runnable client examples for the panel."""

from html import escape
import re


def example(code, language="python"):
    return '<pre><code class="language-' + language + '">' + escape(code.strip()) + '</code></pre>'


AUTH_PYTHON = r'''
import requests

# Edit these values. Run this on your trusted server.
BASE_URL = "http://127.0.0.1:30333"
APP_ID = 1
APP_API_KEY = "rly_app_REPLACE_ME"
AUTH_MODE = "password"  # "password", "product_key", or "both"
USERNAME = "alice"
PASSWORD = "replace-with-user-password"
PRODUCT_KEY = "RLY-REPLACE-WITH-THIS-USERS-KEY"

def authenticate():
    if AUTH_MODE == "password":
        credentials = {"username": USERNAME, "password": PASSWORD}
    elif AUTH_MODE == "product_key":
        credentials = {"product_key": PRODUCT_KEY}
    elif AUTH_MODE == "both":
        credentials = {
            "username": USERNAME,
            "password": PASSWORD,
            "product_key": PRODUCT_KEY,
        }
    else:
        raise ValueError("Choose password, product_key, or both.")

    try:
        response = requests.post(
            f"{BASE_URL.rstrip('/')}/api/auth/{APP_ID}/login",
            headers={"Authorization": f"Bearer {APP_API_KEY}"},
            json=credentials,
            timeout=15,
        )
    except requests.RequestException as error:
        print("Could not reach the server:", error)
        return False

    try:
        result = response.json()
    except ValueError:
        print("Server returned a non-JSON response. HTTP", response.status_code)
        return False
    if not isinstance(result, dict):
        print("Unexpected response format.")
        return False

    if response.status_code == 200 and result.get("authenticated") is True:
        user = result["user"]
        print("Authenticated:", user["username"])
        print("Expires:", user["expires_at"] or "Never")
        return True
    if response.status_code == 429:
        print("Too many attempts. Wait at least 60 seconds before retrying.")
    else:
        print("Authentication failed:", result.get("error", "Unknown error"))
    return False

if __name__ == "__main__":
    if authenticate():
        print("Continue your authorized application workflow here.")
'''

WEBHOOK_PYTHON = r'''
import requests

WEBHOOK_URL = "http://127.0.0.1:30333/wbhk/your-path"
USER_ID = "0023"  # Always send a string to preserve leading zeroes.
USERNAME = "alice"  # Optional.
MESSAGE = "Hello from Python!"

try:
    response = requests.post(
        WEBHOOK_URL,
        json={"id": USER_ID, "message": MESSAGE, "username": USERNAME},
        timeout=15,
    )
    try:
        result = response.json()
    except ValueError:
        result = {"error": "Server returned a non-JSON response"}
    if response.status_code == 201:
        print("Sent. Message ID:", result["id"])
    else:
        print("Send failed:", response.status_code, result)
except requests.RequestException as error:
    print("Could not send:", error)
'''

FILES_PYTHON = r'''
from contextlib import ExitStack
from pathlib import Path
import mimetypes
import requests

WEBHOOK_URL = "http://127.0.0.1:30333/wbhk/your-path"
USER_ID = "0023"
MESSAGE = "Files attached"
USERNAME = "alice"
FILES = ["report.zip", "photo.png"]  # TXT, RAR, 7Z, video, etc. also work.

try:
    with ExitStack() as stack:
        uploads = []
        for filename in FILES:
            path = Path(filename)
            handle = stack.enter_context(path.open("rb"))
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            uploads.append(("files", (path.name, handle, mime)))
        response = requests.post(
            WEBHOOK_URL,
            data={"id": USER_ID, "message": MESSAGE, "username": USERNAME},
            files=uploads,
            timeout=(15, 180),
        )
        try:
            result = response.json()
        except ValueError:
            result = {"error": "Server returned a non-JSON response"}
        print("Sent" if response.status_code == 201 else "Send failed",
              response.status_code, result)
except (OSError, requests.RequestException) as error:
    print("Upload failed:", error)
'''


def docs_content():
    return r'''<main class="docs-main"><div class="section-title">QUICK REFERENCE</div><h1>API docs, made simple</h1><p class="muted">Copy an example, change the sample values, and try it from Python or curl.</p>
<nav class="docs-links" aria-label="Documentation sections"><a href="#getting-started">Start here</a><a href="#authentication">User login</a><a href="#auth-python">Python example</a><a href="#webhooks">Send a message</a><a href="#file-uploads">Send files</a><a href="#shares">Share links</a><a href="#api-errors">Common errors</a></nav>
<section class="form-card" id="getting-started"><h2>1. Start here</h2><ol><li>Create an app and user in <a href="/auth">Auth</a> to check user logins.</li><li>Create a webhook in <a href="/">Webhooks</a> to receive messages.</li><li>Create a public text or file link in <a href="/shares">Shares</a>.</li><li>Install requests to run the Python examples below.</li></ol>''' + example('python -m pip install requests', 'shell') + r'''<p class="hint">The default local address is <code>http://127.0.0.1:30333</code>. Replace it with your server address. Use HTTPS for real credentials and keep app keys private.</p></section>
<section class="form-card" id="authentication"><h2>2. Authentication reference</h2><p><code>POST /api/auth/APP_ID/login</code></p><p>Header: <code>Authorization: Bearer YOUR_APP_API_KEY</code>. Send credentials as a JSON object. The app API key identifies the app; every key-enabled user has a separate product key.</p><div class="docs-table-wrap"><table class="docs-table"><thead><tr><th>Account mode</th><th>Required JSON fields</th><th>Example</th></tr></thead><tbody><tr><td>Password</td><td>username, password</td><td><code>{"username":"alice","password":"user-password"}</code></td></tr><tr><td>Product key</td><td>product_key</td><td><code>{"product_key":"RLY-USER-KEY"}</code></td></tr><tr><td>Both</td><td>username, password, product_key</td><td>All three must belong to the same user.</td></tr></tbody></table></div><p>The selected credentials must match the account mode configured in the panel. Disabled or expired users are rejected. A blank expiry means the account never expires; dates entered in the panel are UTC.</p><h3>curl: password login</h3>''' + example(r'''
curl -X POST 'http://127.0.0.1:30333/api/auth/1/login' \
  -H 'Authorization: Bearer rly_app_YOUR_APP_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"user-password"}'
''', 'shell') + r'''<h3>curl: product key login</h3>''' + example(r'''
curl -X POST 'http://127.0.0.1:30333/api/auth/1/login' \
  -H 'Authorization: Bearer rly_app_YOUR_APP_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"product_key":"RLY-USER-KEY"}'
''', 'shell') + r'''<h3>curl: both credentials</h3>''' + example(r'''
curl -X POST 'http://127.0.0.1:30333/api/auth/1/login' \
  -H 'Authorization: Bearer rly_app_YOUR_APP_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"user-password","product_key":"RLY-USER-KEY"}'
''', 'shell') + r'''<h3>Success · HTTP 200</h3>''' + example('''{"authenticated":true,"user":{"username":"alice","expires_at":"2027-01-01T00:00:00+00:00"}}''', 'json') + r'''<p><code>expires_at</code> is an ISO date with UTC offset, or <code>null</code> for no expiry. The endpoint checks credentials on each call and does not issue a session token. Rotating an app API key immediately revokes the previous app key. Replacing a user's product key revokes that user's previous key. App and user management is performed in the signed-in panel.</p></section>
<section class="form-card" id="auth-python"><h2>3. Complete Python authentication client</h2><p>Set <code>AUTH_MODE</code> to the user's configured mode. This example handles connection errors, invalid responses, rejected credentials, and rate limits.</p>''' + example(AUTH_PYTHON) + r'''</section>
<section class="form-card" id="webhooks"><h2>4. Send a webhook message</h2><p><code>POST /wbhk/YOUR_PATH</code>. No app API key is required; keep the webhook URL private.</p><div class="docs-table-wrap"><table class="docs-table"><thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead><tbody><tr><td>id</td><td>Yes</td><td>Sender ID, 1–80 letters, numbers, hyphens, or underscores. Send as text, e.g. "0023".</td></tr><tr><td>message</td><td>Yes</td><td>Non-empty message text, including when uploading files.</td></tr><tr><td>username</td><td>No</td><td>Display name. Sender IDs distinguish users sharing a name.</td></tr><tr><td>files</td><td>No</td><td>Repeated file fields in a multipart form request.</td></tr></tbody></table></div><h3>Python · JSON message</h3>''' + example(WEBHOOK_PYTHON) + r'''<h3>curl · JSON message</h3>''' + example(r'''
curl -X POST 'http://127.0.0.1:30333/wbhk/your-path' \
  -H 'Content-Type: application/json' \
  -d '{"id":"0023","message":"Hello!","username":"alice"}'
''', 'shell') + r'''<h3>Success · HTTP 201</h3>''' + example('{"ok":true,"id":42}', 'json') + r'''<p>The response <code>id</code> is the stored message ID, not the sender ID. Webhooks accept at most 3 messages per sender IP across all webhooks in 30 seconds.</p></section>
<section class="form-card" id="file-uploads"><h2>5. Upload one or more files</h2><p>Send a multipart form with repeated <code>files</code> fields. Python sets the multipart Content-Type and boundary automatically. Do not set a JSON Content-Type for this request. Files are saved as attachments; ZIP, RAR, and 7Z files are not extracted.</p><h3>Python · text and multiple attachments</h3>''' + example(FILES_PYTHON) + r'''<h3>curl · text and files</h3>''' + example(r'''
curl -X POST 'http://127.0.0.1:30333/wbhk/your-path' \
  -F 'id=0023' -F 'message=Files attached' -F 'username=alice' \
  -F 'files=@report.zip' -F 'files=@photo.png'
''', 'shell') + r'''<p>The combined message limit defaults to 100 MB and can be changed in Settings from 1 to 1024 MB. Set any reverse proxy's upload limit accordingly. A timeout does not prove a message failed to save; check the panel before resending to avoid duplicates.</p></section>
<section class="form-card" id="api-errors"><h2>6. Errors and troubleshooting</h2><div class="docs-table-wrap"><table class="docs-table"><thead><tr><th>HTTP</th><th>Meaning</th><th>What to do</th></tr></thead><tbody><tr><td>400</td><td>Invalid input</td><td>Check JSON shape or required webhook fields.</td></tr><tr><td>401</td><td>Auth rejected</td><td>Check app key, account mode, user credentials, enabled status, and expiry.</td></tr><tr><td>404</td><td>Unknown app or webhook</td><td>Check App ID or webhook path.</td></tr><tr><td>405</td><td>Wrong HTTP method</td><td>Use POST; opening the API in a browser uses GET.</td></tr><tr><td>413</td><td>Request too large</td><td>Auth JSON body limit is 16 KiB. For uploads, check panel and proxy limits.</td></tr><tr><td>429</td><td>Too many requests</td><td>Pause before retrying. Auth: 30 attempts with a valid app key per app and client IP in 60 seconds. Webhooks: 3 accepted messages per sender IP in 30 seconds.</td></tr><tr><td>503</td><td>Server configuration missing</td><td>Check the server's SECRET_KEY environment setting.</td></tr></tbody></table></div><h3>Rejected user · HTTP 401</h3>''' + example('{"authenticated":false,"error":"Invalid, disabled, or expired credentials"}', 'json') + r'''<p>Other API errors typically include an <code>error</code> string. A reverse proxy or server configuration error can return HTML instead of JSON; the Python examples handle that. Connection refused usually means the server is stopped, the port is wrong, or a firewall blocked the connection. Start the server and copy the current URL from the panel. Rate limits use the client IP seen by Flask; clients behind the same proxy may share a limit.</p><p class="hint">The curl line continuation examples use shell syntax for Ubuntu. On Windows, use the Python examples or adapt the command to your shell.</p></section></main>'''


def expand_docs(source):
    content = docs_content().replace('A blank expiry means the account never expires; dates entered in the panel are UTC.', 'Choose a license duration in the panel. Lifetime licenses have no time limit; timed licenses calculate their end date automatically in UTC.')
    content = content.replace('The endpoint checks credentials on each call', 'Timed licenses activate on the first successful login, and that response includes the calculated expiry. Invalid credentials do not activate a license. Updating an activated license sets its new duration from today; pending licenses still start on first login. Bulk extension adds days to the existing license. The endpoint checks credentials on each call')
    content = content.replace('<section class="form-card" id="api-errors">', '<section class="form-card" id="shares"><h2>Share text and files</h2><p>Create shares on the signed-in <a href="/shares">Shares</a> page. Choose a title and unique path, then paste text, attach a file, or both. Anyone with the link can view it. Share creation and deletion happen in the panel; there is no public create API.</p><p><code>GET /p/YOUR_PATH</code> opens the share. For a file, <code>GET /p/YOUR_PATH/download</code> downloads it.</p><h3>Download a shared file with Python</h3>' + example('from pathlib import Path\nimport requests\n\nurl = "http://127.0.0.1:30333/p/toolkit/download"\nresponse = requests.get(url, stream=True, timeout=(15, 180))\nresponse.raise_for_status()\nwith Path("toolkit.zip").open("wb") as output:\n    for chunk in response.iter_content(1024 * 1024):\n        if chunk:\n            output.write(chunk)') + '<p>Delete a share in the panel to revoke the link and remove its uploaded file.</p></section><section class="form-card" id="api-errors">')
    return re.sub(r'<main>.*?</main>', lambda _: content, source, count=1, flags=re.S)
