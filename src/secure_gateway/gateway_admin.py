"""Read-only local dashboard using the gateway's existing header authentication."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit


def handle_admin(handler):
    url = urlsplit(handler.path)
    if url.path != "/admin" and not url.path.startswith("/admin/"):
        return False
    port = handler.server.server_port
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origin = handler.headers.get("Origin")
    if handler.headers.get("Host") not in hosts or (
        origin is not None and origin not in {"http://" + host for host in hosts}
    ):
        handler.send_body(403, b'{"error":"Local origin required"}')
        return True
    handler.response_headers = {
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
        "style-src 'self'; connect-src 'self'; img-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }
    assets = {"/admin": ("index.html", "text/html; charset=utf-8"),
              "/admin/": ("index.html", "text/html; charset=utf-8"),
              "/admin/app.js": ("app.js", "text/javascript; charset=utf-8"),
              "/admin/style.css": ("style.css", "text/css; charset=utf-8"),
              "/admin/favicon.svg": ("favicon.svg", "image/svg+xml")}
    if url.path in assets:
        name, content_type = assets[url.path]
        handler.send_body(200, (Path(__file__).parent / "admin" / name).read_bytes(), content_type)
        return True
    if not handler.authorized():
        handler.send_body(401, b'{"error":"Unauthorized"}')
        return True
    if url.path == "/admin/api/sessions":
        if url.query:
            handler.send_body(400, b'{"error":"Session diagnostics take no filters"}')
        else:
            handler.send_body(200, json.dumps(handler.server.session_diagnostics()).encode())
        return True
    export = url.path == "/admin/api/logs/export"
    if url.path != "/admin/api/logs" and not export:
        handler.send_body(404, b'{"error":"Unknown admin endpoint"}')
        return True
    if handler.server.audit is None:
        handler.send_body(503, b'{"error":"Audit storage is not configured"}')
        return True
    try:
        if len(url.query) > 2048:
            raise ValueError("Query too large")
        # Python 3.10 rejects an empty query when strict_parsing is enabled.
        params = parse_qs(url.query, keep_blank_values=True, strict_parsing=True) if url.query else {}
        allowed = {"agent", "provider", "subscription", "account_ref", "credential_ref", "result",
                   "since", "until"}
        if not export:
            allowed.update({"limit", "offset"})
        if set(params) - allowed or any(len(v) != 1 for v in params.values()):
            raise ValueError("Invalid filters")
        filters = {key: values[0] for key, values in params.items()}
        if export:
            if not filters.get("since") or not filters.get("until"):
                raise ValueError("Export requires a date range")
            since = datetime.fromisoformat(filters["since"].replace("Z", "+00:00"))
            until = datetime.fromisoformat(filters["until"].replace("Z", "+00:00"))
            if since.tzinfo is None or until.tzinfo is None:
                raise ValueError("Export dates require a timezone")
            span = until.astimezone(timezone.utc) - since.astimezone(timezone.utc)
            if not timedelta(0) <= span <= timedelta(days=31):
                raise ValueError("Export date range exceeds 31 days")
            result = handler.server.audit.export_metadata(filters)
            handler.response_headers["Content-Disposition"] = 'attachment; filename="secure-gateway-audit.json"'
            handler.send_body(200, json.dumps(result, allow_nan=False).encode())
            return True
        limit = int(filters.pop("limit", "50"))
        offset = int(filters.pop("offset", "0"))
        if not 1 <= limit <= 200 or not 0 <= offset <= 2**63 - 1:
            raise ValueError("Invalid pagination")
        result = handler.server.audit.query(filters, limit, offset)
        result["audit_write_errors"] = handler.server.audit_write_errors
        result["routes"] = [
            {"provider": name, "mode": "api_key" if name in handler.server.api_upstreams
             else "subscription"} for name in handler.server.upstreams
        ]
        handler.send_body(200, json.dumps(result).encode())
    except (ValueError, OverflowError):
        handler.send_body(400, b'{"error":"Invalid log filters"}')
    except sqlite3.Error:
        handler.send_body(503, b'{"error":"Audit storage unavailable"}')
    return True
