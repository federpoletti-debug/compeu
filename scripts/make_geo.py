"""Generate the dotted map of Europe used by the 3D map (site/static/geo/europe-dots.json).

Input: Natural Earth 1:50m countries as TopoJSON (world-atlas@2.0.2, public domain):
    https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json
Usage:
    uv run python scripts/make_geo.py path/to/countries-50m.json

Projection: Lambert azimuthal equal-area centred on 52N 10E, the EU's reference
projection for statistics (EPSG:3035), in its spherical form, in kilometres with
the origin at the centre. site/static/js/map3d.js uses the same formula for sites.

Each land dot gets a group: 3 Switzerland, 2 EU27, 1 rest of Europe, 0 outside.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

R = 6371.0072  # km, authalic radius
LAT0, LON0 = math.radians(52), math.radians(10)
SPACING = 26  # km between dots
X_RANGE = (-2700, 3300)
Y_RANGE = (-2000, 3100)

EU27 = {
    "040",
    "056",
    "100",
    "191",
    "196",
    "203",
    "208",
    "233",
    "246",
    "250",
    "276",
    "300",
    "348",
    "372",
    "380",
    "428",
    "440",
    "442",
    "470",
    "528",
    "616",
    "620",
    "642",
    "703",
    "705",
    "724",
    "752",
}
SWITZERLAND = {"756"}
OTHER_EUROPE = {
    "352",
    "578",
    "438",
    "826",
    "804",
    "112",
    "498",
    "688",
    "070",
    "499",
    "807",
    "008",
    "020",
    "492",
    "674",
    "336",
    "643",
    "792",
    "268",
    "051",
    "031",
}


def laea(lon: float, lat: float) -> tuple[float, float]:
    lam, phi = math.radians(lon), math.radians(lat)
    d = lam - LON0
    denom = 1 + math.sin(LAT0) * math.sin(phi) + math.cos(LAT0) * math.cos(phi) * math.cos(d)
    k = math.sqrt(2 / denom)
    x = R * k * math.cos(phi) * math.sin(d)
    y = R * k * (math.cos(LAT0) * math.sin(phi) - math.sin(LAT0) * math.cos(phi) * math.cos(d))
    return x, y


def decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def ring(arcs: list, indices: list[int]) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in indices:
        a = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
        pts.extend(a if not pts else a[1:])
    return pts


def polygons(geom: dict, arcs: list) -> list[list[list[tuple[float, float]]]]:
    if geom["type"] == "Polygon":
        return [[ring(arcs, r) for r in geom["arcs"]]]
    if geom["type"] == "MultiPolygon":
        return [[ring(arcs, r) for r in poly] for poly in geom["arcs"]]
    return []


def group_of(cid: str) -> int:
    if cid in SWITZERLAND:
        return 3
    if cid in EU27:
        return 2
    if cid in OTHER_EUROPE:
        return 1
    return 0


def main(src: str) -> None:
    topo = json.loads(Path(src).read_text(encoding="utf-8"))
    arcs = decode_arcs(topo)
    xs = list(range(X_RANGE[0], X_RANGE[1] + 1, SPACING))
    ys = list(range(Y_RANGE[0], Y_RANGE[1] + 1, SPACING))
    grid: dict[tuple[int, int], int] = {}
    for geom in topo["objects"]["countries"]["geometries"]:
        cid = str(geom.get("id", ""))
        g = group_of(cid)
        for poly in polygons(geom, arcs):
            rings = []
            for r in poly:
                if not any(-45 < lon < 70 and lat > 25 for lon, lat in r):
                    continue
                # Clamp far-away vertices (e.g. eastern Russia) to the edge of the view.
                rings.append([laea(min(max(lon, -60), 75), max(lat, 20)) for lon, lat in r])
            if not rings:
                continue
            ymin = min(p[1] for rr in rings for p in rr)
            ymax = max(p[1] for rr in rings for p in rr)
            for yi, y in enumerate(ys):
                if y < ymin or y > ymax:
                    continue
                # Scanline fill, even-odd rule across outer ring and holes.
                cuts = []
                for rr in rings:
                    for (x1, y1), (x2, y2) in zip(rr, rr[1:] + rr[:1], strict=True):
                        if (y1 <= y < y2) or (y2 <= y < y1):
                            cuts.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                cuts.sort()
                for a, b in zip(cuts[0::2], cuts[1::2], strict=False):
                    for xi, x in enumerate(xs):
                        if a <= x <= b:
                            grid[(xi, yi)] = max(grid.get((xi, yi), -1), g)
    points = []
    for (xi, yi), g in sorted(grid.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        points += [xs[xi], ys[yi], g]
    out = Path(__file__).resolve().parents[1] / "site" / "static" / "geo" / "europe-dots.json"
    out.write_text(
        json.dumps(
            {
                "projection": "LAEA 52N 10E (EPSG:3035, spherical), km",
                "spacing_km": SPACING,
                "source": "Natural Earth 1:50m via world-atlas@2.0.2 (public domain)",
                "groups": {
                    "3": "Switzerland",
                    "2": "EU27",
                    "1": "rest of Europe",
                    "0": "outside Europe",
                },
                "points": points,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"{len(points) // 3} dots -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
