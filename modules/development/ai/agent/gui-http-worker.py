"""Fixed desktop HTTPS adapter; OpenShell replaces opaque auth on egress.

One JSON request on stdin, newline JSON headers/chunks on stdout. Redirects
are deliberately disabled: neither upstream nor caller can widen credential
scope. No host credential file, gateway socket or bearer export is involved.
"""
import base64
import errno
import http.client
import json
import os
import functools
import re
import subprocess
import sys
import socket
import ssl
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


@functools.lru_cache(maxsize=1)
def cli_user_agent():
    # The authenticated /me endpoint rejects urllib's generic user agent. Use
    # the actual contained CLI version, never a claimed older compatible one.
    version = subprocess.run(["/bin/codex", "--version"], check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
    match = re.fullmatch(rb"codex-cli ([A-Za-z0-9.+-]+)\s*", version.stdout)
    if not match:
        raise ValueError("Contained CLI version unavailable")
    return "codex_cli_rs/" + match[1].decode("ascii")


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
    if "user-agent" not in headers:
        headers["user-agent"] = cli_user_agent()
    headers.setdefault("originator", "codex_cli_rs")
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


# Fixed vocabulary is shared with the relay's strict parser. Never include an
# exception message, response body, URL, account identity or caller headers.
def failure_category(error):
    if isinstance(error, urllib.error.HTTPError):
        if error.code == 401:
            return "http-unauthorized"
        if error.code == 403:
            return "http-forbidden"
        return "http-rejected"
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(reason, ssl.SSLError):
        return "tls"
    if isinstance(error, urllib.error.URLError):
        return "transport"
    if isinstance(error, subprocess.SubprocessError):
        return "cli-identity"
    if isinstance(error, OSError):
        return "local-io"
    return "invalid-data"


def failure_detail(error):
    # Stderr-only diagnostics: inspect types/errno, never exception text or paths.
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, http.client.RemoteDisconnected):
        return "remote-disconnected"
    if isinstance(reason, OSError):
        return {
            errno.ECONNRESET: "connection-reset",
            errno.EPIPE: "broken-pipe",
            errno.ENETUNREACH: "network-unreachable",
            errno.EHOSTUNREACH: "host-unreachable",
            errno.ECONNREFUSED: "connection-refused",
            errno.ETIMEDOUT: "timed-out",
            errno.EACCES: "permission-denied",
            errno.EPERM: "permission-denied",
            errno.ENOENT: "file-missing",
        }.get(reason.errno, "other")
    return "other"


def main():
    stage = "request-validation"
    started = False
    try:
        line = sys.stdin.buffer.readline(LIMIT * 2 + HEADER_LIMIT + 1)
        if len(line) > LIMIT * 2 + HEADER_LIMIT or not line.endswith(b"\n"):
            raise ValueError("Invalid desktop HTTP frame")
        request = validate(json.loads(line))
        opener = urllib.request.build_opener(NoRedirect(), urllib.request.ProxyHandler({}))
        stage = "routing-discovery"
        apply_routing(opener, request)
        stage = "backend-request"
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
            started = True
            stage = "response-stream"
            total = 0
            while chunk := response.read1(65536):
                total += len(chunk)
                if total > LIMIT:
                    raise ValueError("Desktop HTTP response is too large")
                emit({"chunk": base64.b64encode(chunk).decode("ascii")})
            emit({"done": True})
    except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError, subprocess.SubprocessError) as error:
        # Reflect neither upstream error text nor request headers: credentials
        # and task content must never reach stderr/journal on adapter failure.
        category = failure_category(error)
        print(f"Sandbox desktop HTTP failed: stage={stage} category={category} detail={failure_detail(error)}; "
              "retained login preserved; inspect gateway policy/credential diagnostics before signing in",
              file=sys.stderr)
        if not started:
            emit({"error": {"stage": stage, "category": category}})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
