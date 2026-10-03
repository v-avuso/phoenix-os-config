"""Build a Codex auth file from OpenShell's opaque handles, never real tokens."""
import base64
import json
import os
from pathlib import Path
import sys
import time
import uuid

home = Path(os.environ["HOME"]) / ".codex"
home.mkdir(mode=0o700, parents=True, exist_ok=True)
encode = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
now = int(time.time())
identity = ".".join([
    encode({"alg": "none", "typ": "JWT"}),
    encode({"iss": "https://auth.openai.com", "aud": "codex", "sub": "phoenix-sandbox",
            "email": "sandbox@phoenix.invalid", "iat": now, "exp": now + 3600,
            "https://api.openai.com/auth": {
                "chatgpt_account_id": str(uuid.UUID(os.environ["PHOENIX_CODEX_ACCOUNT_ID"]))}}),
    "placeholder",
])
# Matches upstream's v0.1.2 examples/codex-app-server authentication pattern.
auth = {
    "auth_mode": "chatgptAuthTokens", "OPENAI_API_KEY": None,
    "tokens": {"id_token": identity,
               "access_token": os.environ["CODEX_AUTH_ACCESS_TOKEN"],
               "refresh_token": "", "account_id": str(uuid.UUID(os.environ["PHOENIX_CODEX_ACCOUNT_ID"]))},
    "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
target = home / "auth.json"
# Sandbox state can be hostile on reconnect; never follow an auth-file symlink.
directory = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
try:
    fd = os.open("auth.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
finally:
    os.close(directory)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w") as stream:
    json.dump(auth, stream)
if sys.argv[1:]:
    os.execv(sys.argv[1], sys.argv[1:])
