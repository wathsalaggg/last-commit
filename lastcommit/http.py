"""Tiny stdlib HTTP helpers, so the project has no dependencies."""

import json
import urllib.error
import urllib.request


class HTTPError(RuntimeError):
    pass


def request(url, *, method="GET", headers=None, body=None, timeout=60):
    """Return (status, headers, raw bytes). Raises HTTPError on 4xx/5xx."""
    data = None
    headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise HTTPError(f"{method} {url.split('?')[0]} -> {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise HTTPError(f"{method} {url.split('?')[0]} failed: {e.reason}") from None


def get_json(url, **kw):
    status, headers, raw = request(url, **kw)
    return json.loads(raw), headers


def post_json(url, body, **kw):
    status, headers, raw = request(url, method="POST", body=body, **kw)
    return json.loads(raw)
