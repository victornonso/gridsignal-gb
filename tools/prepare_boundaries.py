"""Transform and simplify NESO's licensed 2024 DNO boundaries for web presentation."""

import hashlib
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
MAPPING = {
    "_A": 10,
    "_B": 9,
    "_C": 13,
    "_D": 6,
    "_E": 8,
    "_F": 4,
    "_G": 3,
    "_P": 1,
    "_J": 14,
    "_K": 7,
    "_L": 11,
    "_M": 5,
    "_N": 2,
    "_H": 12,
}


def main():
    source = ROOT / "docs/contracts/dno-boundaries.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    projection = Transformer.from_crs(27700, 4326, always_xy=True).transform
    for feature in data["features"]:
        properties = feature["properties"]
        properties["region_id"] = MAPPING[properties["Name"]]
        properties["name"] = str(properties["region_id"])
        geom = shape(feature["geometry"]).simplify(150, preserve_topology=True)
        feature["geometry"] = mapping(transform(projection, geom))
    data.pop("crs", None)
    target = ROOT / "apps/dashboard/public/dno-regions.geojson"
    target.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    doc = {
        "source": "NESO GB DNO Licence Areas 20240503",
        "licence": "NESO Open Data Licence",
        "url": "https://www.neso.energy/data-portal/gis-boundaries-gb-dno-license-areas",
        "resource_id": "1c6a7dc0-1b6c-443a-bc67-5f7125649434",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_crs": "EPSG:27700",
        "output_crs": "EPSG:4326",
        "simplification_metres": 150,
        "mapping": MAPPING,
        "limitations": "Published approximate DNO licence boundaries, not exact service eligibility polygons.",
    }
    (ROOT / "docs/boundary-provenance.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("Prepared 14 licensed regions:", target.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
