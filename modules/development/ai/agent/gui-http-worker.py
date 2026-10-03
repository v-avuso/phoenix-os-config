"""Fixed desktop HTTPS adapter; OpenShell replaces opaque auth on egress.

One JSON request on stdin, newline JSON headers/chunks on stdout. Redirects
are deliberately disabled: neither upstream nor caller can widen credential
scope. No host credential file, gateway socket or bearer export is involved.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

LIMIT = 16 * 1024 * 1024
HEADER_LIMIT = 64 * 1024
METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}
# The pinned desktop backend API uses these two namespaces. Authentication,
# arbitrary web browsing and presigned third-party URLs stay outside this lane.
PREFIXES = ("/backend-api/", "/api/codex/")
SAFE_HEADERS = {"accept", "content-type", "openai-beta", "originator",
                "x-openai-client-version", "x-openai-client-user-agent",
                "x-openai-originator", "user-agent",
                "x-codex-turn-metadata", "x-client-request-id"}
ACCOUNTS_URL = "https://chatgpt.com/backend-api/wham/accounts/check"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def validate(request):
    url = request["url"]
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "chatgpt.com"
            or parsed.fragment or not parsed.path.startswith(PREFIXES)
            or any(c in url for c in "\r\n\\")
            or any(part in {".", ".."} for part in urllib.parse.unquote(parsed.path).split("/"))):
        raise ValueError("Destination outside the desktop backend")
    method = request.get("method", "GET")
    if method not in METHODS:
        raise ValueError("Unsupported desktop HTTP method")
    supplied = request.get("headers", {})
    if not isinstance(supplied, dict) or len(json.dumps(supplied)) > HEADER_LIMIT:
        raise ValueError("Invalid desktop HTTP headers")
    headers = {}
    for key, value in supplied.items():
        if not isinstance(key, str) or not isinstance(value, str) or any(c in key + value for c in "\r\n"):
            raise ValueError("Invalid desktop HTTP header")
        if key.lower() in SAFE_HEADERS:
            headers[key.lower()] = value
    # Ignore caller authorization, cookies and routing selectors. The gateway
    # owns the opaque credential; account identity comes from trusted launch.
    headers["authorization"] = "Bearer " + os.environ["CODEX_AUTH_ACCESS_TOKEN"]
    headers["chatgpt-account-id"] = os.environ["PHOENIX_CODEX_ACCOUNT_ID"]
    body = base64.b64decode(request.get("body", ""), validate=True)
    if len(body) > LIMIT:
        raise ValueError("Desktop HTTP request is too large")
    return urllib.request.Request(url, data=body or None, headers=headers, method=method)


def emit(value):
    print(json.dumps(value, separators=(",", ":")), flush=True)


def apply_routing(opener, request):
    if request.full_url == ACCOUNTS_URL:
        return
    # Residency is authority from the actual account discovery response,
    # never a caller header. This bootstrap request itself needs no override.
    check = validate({"url": ACCOUNTS_URL})
    with opener.open(check, timeout=60) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("Oversized routing response")
    entries = json.loads(data)["accounts"]
    if not isinstance(entries, list):
        raise ValueError("Routing discovery metadata missing")
    account = os.environ["PHOENIX_CODEX_ACCOUNT_ID"]
    selected = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == account]
    if len(selected) != 1:
        raise ValueError("Routing discovery account ambiguous")
    entry = selected[0]
    if entry.get("workspace_backend_origin") not in {"NO_CONSTRAINT", "https://chatgpt.com"}:
        raise ValueError("Routing discovery outside fixed endpoint")
    override = entry.get("account_routing_override")
    if override not in {"NO_CONSTRAINT", "us", "us_cr"}:
        raise ValueError("Routing discovery override invalid")
    if override != "NO_CONSTRAINT":
        request.add_header("X-OpenAI-Account-Routing-Override", override)


def main():
    try:
        line = sys.stdin.buffer.readline(LIMIT * 2 + HEADER_LIMIT + 1)
        if len(line) > LIMIT * 2 + HEADER_LIMIT or not line.endswith(b"\n"):
            raise ValueError("Invalid desktop HTTP frame")
        request = validate(json.loads(line))
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.ProxyHandler({}))
        apply_routing(opener, request)
        try:
            response = opener.open(request, timeout=60)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            # Cookies and redirects never leave this adapter. Body bytes are
            # streamed immediately, including SSE; no response buffering.
            headers = {key.lower(): value for key, value in response.headers.items()
                       if key.lower() in {"content-type", "cache-control", "retry-after"}}
            emit({"status": response.status, "headers": headers})
            total = 0
            while chunk := response.read1(65536):
                total += len(chunk)
                if total > LIMIT:
                    raise ValueError("Desktop HTTP response is too large")
                emit({"chunk": base64.b64encode(chunk).decode("ascii")})
            emit({"done": True})
    except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
        # Reflect neither upstream error text nor request headers: credentials
        # and task content must never reach stderr/journal on adapter failure.
        print("Desktop backend request failed within the sandbox", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
