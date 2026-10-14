"""Encrypt the scoped writer secret for this repository using existing GitHub authentication."""

import base64
import json
import subprocess
import urllib.request
from pathlib import Path

from nacl.public import PublicKey, SealedBox


def main():
    result = subprocess.run(["git", "credential", "fill"],
                            input="protocol=https\nhost=github.com\n\n",
                            capture_output=True, text=True, check=True, timeout=30)
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = fields["password"]
    base = "https://api.github.com/repos/victornonso/gridsignal-gb"

    def request(path, method="GET", data=None):
        req = urllib.request.Request(base + path, method=method,
                                     data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": "Bearer " + token,
                                              "Accept": "application/vnd.github+json",
                                              "Content-Type": "application/json", "User-Agent": "GridSignal"})
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else {}

    config = json.loads((Path(__file__).resolve().parents[1] / ".local/hosted.json").read_text())
    key = request("/actions/secrets/public-key")
    encrypted = SealedBox(PublicKey(base64.b64decode(key["key"]))).encrypt(config["database_url"].encode())
    request("/actions/secrets/HOSTED_WRITER_DATABASE_URL", "PUT", {
        "key_id": key["key_id"], "encrypted_value": base64.b64encode(encrypted).decode(),
    })
    variables = request("/actions/variables")["variables"]
    exists = any(v["name"] == "HOSTED_INGESTION_ENABLED" for v in variables)
    request("/actions/variables" + ("/HOSTED_INGESTION_ENABLED" if exists else ""),
            "PATCH" if exists else "POST", {"name": "HOSTED_INGESTION_ENABLED", "value": "true"})
    request("/actions/workflows/ingestion.yml/dispatches", "POST", {"ref": "main"})
    print("Encrypted repository writer secret stored; bounded refresh workflow dispatched.")


if __name__ == "__main__":
    main()
