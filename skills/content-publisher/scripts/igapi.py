"""Minimal client for Instagram's official content-publishing API.

This is the only module in the project that talks to the network, and it only
talks to Meta's Graph API hosts (ALLOWED_HOSTS). It never uses a password;
it uses an access token the creator generated in their own Meta app.
The token is never printed, logged or written to disk by this module; error
messages are scrubbed of it.

The HTTP layer is injectable (Client(transport=...)) so tests run offline.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

ALLOWED_HOSTS = ("graph.instagram.com", "graph.facebook.com")


class ApiError(Exception):
    """An error returned by the Graph API, or a refused / failed request."""

    def __init__(self, message, code=None, subcode=None, status=None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.status = status


def urllib_transport(method, url, data, timeout):
    """Default transport: returns (http_status, body_text)."""
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"} if body else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


class Client:
    def __init__(self, token, host="graph.instagram.com", version="v27.0", transport=None,
                 timeout=30, sleep=time.sleep):
        if host not in ALLOWED_HOSTS:
            raise ApiError("refusing to call %r: only %s are allowed" % (host, ", ".join(ALLOWED_HOSTS)))
        if not token:
            raise ApiError("no access token")
        self._token = token
        self.base = "https://%s/%s" % (host, version.strip("/"))
        self.transport = transport or urllib_transport
        self.timeout = timeout
        self.sleep = sleep
        self.calls = []  # (method, path) for the run log; never includes the token

    # -- plumbing ---------------------------------------------------------
    def _scrub(self, text):
        return text.replace(self._token, "<token>") if text else text

    def _request(self, method, path, params=None):
        params = dict(params or {})
        params["access_token"] = self._token
        self.calls.append((method, path))
        if method == "GET":
            url = "%s/%s?%s" % (self.base, path.lstrip("/"), urllib.parse.urlencode(params))
            data = None
        else:
            url = "%s/%s" % (self.base, path.lstrip("/"))
            data = params
        host = urllib.parse.urlsplit(url).hostname
        if host not in ALLOWED_HOSTS:  # belt and braces: path tricks cannot change the host
            raise ApiError("refusing to call %r" % host)
        try:
            status, text = self.transport(method, url, data, self.timeout)
        except OSError as e:
            raise ApiError(self._scrub("network error: %s" % e))
        try:
            payload = json.loads(text) if text else {}
        except ValueError:
            raise ApiError(self._scrub("non-JSON response (HTTP %s): %s" % (status, text[:200])), status=status)
        if isinstance(payload, dict) and "error" in payload:
            err = payload["error"] or {}
            msg = err.get("error_user_msg") or err.get("message") or "unknown API error"
            raise ApiError(self._scrub(msg), err.get("code"), err.get("error_subcode"), status)
        if status and status >= 400:
            raise ApiError(self._scrub("HTTP %s: %s" % (status, text[:200])), status=status)
        return payload

    # -- endpoints --------------------------------------------------------
    def me(self):
        """The professional account behind the token: {'user_id'|'id', 'username'}."""
        return self._request("GET", "me", {"fields": "user_id,username"})

    def publishing_limit(self, ig_id):
        return self._request("GET", "%s/content_publishing_limit" % ig_id, {"fields": "quota_usage,config"})

    def create_container(self, ig_id, params):
        return self._request("POST", "%s/media" % ig_id, params)["id"]

    def container_status(self, container_id):
        return self._request("GET", container_id, {"fields": "status_code,status"})

    def publish(self, ig_id, container_id):
        return self._request("POST", "%s/media_publish" % ig_id, {"creation_id": container_id})

    def permalink(self, media_id):
        return self._request("GET", media_id, {"fields": "permalink"}).get("permalink")

    def wait_until_ready(self, container_id, interval=60, attempts=5):
        """Poll status_code as Meta recommends (about once a minute, at most ~5 minutes)."""
        last = None
        for i in range(attempts + 1):
            st = self.container_status(container_id)
            last = st.get("status_code")
            if last in ("FINISHED", "PUBLISHED"):
                return last
            if last in ("ERROR", "EXPIRED"):
                raise ApiError("media container %s is %s (%s)" % (container_id, last, st.get("status", "no detail")))
            if i < attempts:
                self.sleep(interval)
        raise ApiError("media container %s still %s after %d checks; nothing was published. "
                       "Run publish again later (same approval code) once it has finished processing."
                       % (container_id, last, attempts + 1))
