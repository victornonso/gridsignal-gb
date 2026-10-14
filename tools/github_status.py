"""Read this project's CI status with the existing Git credential helper."""

import argparse
import json
import subprocess
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int)
    args = parser.parse_args()
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    token = fields["password"]
    path = f"/actions/runs/{args.run}/jobs" if args.run else "/actions/runs?per_page=3"
    request = urllib.request.Request(
        "https://api.github.com/repos/victornonso/gridsignal-gb" + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "GridSignal-ci-check",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if args.run:
        print(
            json.dumps(
                [
                    {
                        "id": j["id"],
                        "name": j["name"],
                        "status": j["status"],
                        "conclusion": j["conclusion"],
                        "steps": [{"name": s["name"], "conclusion": s["conclusion"]} for s in j["steps"]],
                    }
                    for j in data["jobs"]
                ],
                indent=2,
            )
        )
    else:
        print(
            json.dumps(
                [
                    {
                        "id": r["id"],
                        "status": r["status"],
                        "conclusion": r["conclusion"],
                        "commit": r["head_sha"],
                        "url": r["html_url"],
                    }
                    for r in data["workflow_runs"]
                ],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
