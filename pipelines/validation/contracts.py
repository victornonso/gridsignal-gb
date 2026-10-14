"""Minimum source envelope/field checks, recorded independently of row validation."""


def contract_drift(source, body):
    if source == "demand":
        result = body.get("result", {})
        if "resources" in result:
            return []
        records = result.get("records")
        expected = {"SETTLEMENT_DATE", "SETTLEMENT_PERIOD", "ND", "TSD"}
    else:
        records = body.get("data")
        expected = {
            "carbon": {"from", "to", "intensity"},
            "regional": {"from", "to", "regions"},
            "mix": {"from", "to", "generationmix"},
            "elexon": {"startTime", "fuelType", "generation"},
            "factors": set(),
        }[source]
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list):
        return [{"missing": "record collection"}]
    failures = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            failures.append({"record": index, "missing": ["object record"]})
        elif expected - set(record):
            failures.append({"record": index, "missing": sorted(expected - set(record))})
    return failures
