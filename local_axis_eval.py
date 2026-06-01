import sys
from pathlib import Path

import stacking_analyzer as sa


def group(values, tol):
    vals = sorted(v % 1.0 for v in values)
    if not vals:
        return []
    clusters = []
    curr = [vals[0]]
    for v in vals[1:]:
        if v - curr[-1] <= tol:
            curr.append(v)
        else:
            clusters.append(curr)
            curr = [v]
    clusters.append(curr)
    if len(clusters) > 1 and (clusters[0][0] + 1.0 - clusters[-1][-1]) <= tol:
        clusters[0] = [v - 1.0 for v in clusters[-1]] + clusters[0]
        clusters.pop()
    centers = [(sum(c) / len(c)) % 1.0 for c in clusters]
    return centers


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "test_XO3_M7_XO3_T_XO2_T_XO3_3.cif"
    p = Path(__file__).resolve().parent / "test_cifs" / name
    d = sa.parse_cif_file(p)
    lat = d.get("lattice") or {}
    sites = d.get("atom_sites") or []
    for axis, L in (("x", lat.get("a", 0)), ("y", lat.get("b", 0)), ("z", lat.get("c", 0))):
        tol = 0.02
        if L and L > 0:
            tol = min(0.05, max(0.002, 0.5 / float(L)))
        centers = group([s[axis] for s in sites], tol)
        print(axis, "len", L, "tol", round(tol, 5), "layers", len(centers))


if __name__ == "__main__":
    main()
