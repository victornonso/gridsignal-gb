"""Skip redundant watchdog collections; refresh conservatively if status is unavailable."""

import json
import os
from urllib.request import urlopen

SOURCES = {"carbon", "regional", "mix", "elexon", "demand", "factors"}
NEEDS_COLLECTION = {"overdue", "failed", "no_data"}


def needs_refresh(rows):
    by_source = {row.get("id"): row for row in rows}
    return not SOURCES.issubset(by_source) or any(
        by_source[source].get("collection_status") in NEEDS_COLLECTION
        or not by_source[source].get("last_success_at")
        for source in SOURCES & by_source.keys()
    )


def main():
    required = os.environ.get("FORCE_REFRESH", "false").lower() == "true"
    reason = "scheduled collection or explicit refresh"
    if not required:
        try:
            with urlopen("https://gridsignal-api.onrender.com/api/v1/operations/sources", timeout=95) as response:
                required = needs_refresh(json.load(response)["rows"])
            reason = "source collection needs recovery" if required else "all sources are within their collection window"
        except Exception as exc:
            required = True
            reason = f"status unavailable ({type(exc).__name__}); attempt bounded recovery"
    print(json.dumps({"refresh_required": required, "reason": reason}))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"required={str(required).lower()}\n")


if __name__ == "__main__":
    main()
