"""Send one message to a Relay webhook. Edit the settings below, then run this file."""

import json
import mimetypes
import secrets
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ── Edit these settings ──────────────────────────────────────────────────────
WEBHOOK_URL = "http://127.0.0.1:60852/wbhk/nigga"
USER_ID = "32123221"  # Required; kept as text so leading zeroes are preserved.
USERNAME = "hore"  # Optional; leave empty to display "User <ID>".
MESSAGE = "this is a test"
FILES = []  # Example: ["report.zip", "photo.png"]
MAX_MESSAGE_MB = 100  # Match the limit in the panel's Settings.
# ────────────────────────────────────────────────────────────────────────────


def main():
    if "YOUR_PATH" in WEBHOOK_URL or not WEBHOOK_URL.startswith(("http://", "https://")):
        print("Set WEBHOOK_URL at the top of this file first.", file=sys.stderr)
        return 1
    if not USER_ID.strip() or not USER_ID.replace("-", "").replace("_", "").isalnum() or len(USER_ID) > 80:
        print("Set USER_ID to 1-80 letters, numbers, hyphens, or underscores.", file=sys.stderr)
        return 1
    if not MESSAGE.strip():
        print("MESSAGE is required.", file=sys.stderr)
        return 1

    paths = [Path(name).expanduser() for name in FILES]
    for path in paths:
        if not path.is_file():
            print(f"File not found: {path}", file=sys.stderr)
            return 1

    total_size = len(MESSAGE.encode("utf-8")) + sum(path.stat().st_size for path in paths)
    if total_size > MAX_MESSAGE_MB * 1024 * 1024:
        print(f"Message and files exceed the {MAX_MESSAGE_MB} MB limit.", file=sys.stderr)
        return 1

    boundary = "----Relay" + secrets.token_hex(16)
    body = bytearray()

    def add_field(name, value):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    add_field("id", USER_ID)
    add_field("message", MESSAGE)
    if USERNAME.strip():
        add_field("username", USERNAME)

    for path in paths:
        filename = path.name.replace('"', "_").replace("\r", "_").replace("\n", "_")
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
        body.extend(path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())
    request = Request(
        WEBHOOK_URL,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )

    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Message sent (ID {result.get('id', '?')}).")
            return 0
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("error", "Request failed")
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            detail = error.reason
        print(f"Webhook error {error.code}: {detail}", file=sys.stderr)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"Could not send message: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
