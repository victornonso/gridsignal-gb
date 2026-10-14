"""Create the personal repository using Git's credential manager; never persist credentials."""

import json
import subprocess
import urllib.error
import urllib.request


def main():
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = fields.get("password")
    if not token:
        raise SystemExit("GitHub authentication unavailable: sign in through Git Credential Manager.")

    def api(path, data=None):
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "GridSignal-setup",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    user = api("/user")["login"]
    try:
        repo = api(f"/repos/{user}/gridsignal-gb")
        print("Repository already exists:", repo["html_url"])
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise SystemExit(f"GitHub repository lookup failed (HTTP {error.code}).") from None
        try:
            repo = api(
                "/user/repos",
                {
                    "name": "gridsignal-gb",
                    "description": "Great Britain electricity intelligence: official APIs, PostgreSQL analytics, FastAPI and Next.js",
                    "private": True,
                    "auto_init": False,
                },
            )
        except urllib.error.HTTPError as error:
            raise SystemExit(
                f"GitHub repository creation requires authentication with repo creation permission (HTTP {error.code})."
            ) from None
        print("Created private repository:", repo["html_url"])
    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    if "origin" not in remotes:
        subprocess.run(["git", "remote", "add", "origin", repo["clone_url"]], check=True)


if __name__ == "__main__":
    main()
