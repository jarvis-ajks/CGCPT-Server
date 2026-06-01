import sys
from collections import Counter
from pathlib import Path

import stacking_analyzer as sa


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "test_XO3_M7_XO3_T_XO2_T_XO3_3.cif"
    p = Path(__file__).resolve().parent / "test_cifs" / name
    d = sa.parse_cif_file(p)
    zs = [s["z"] % 1.0 for s in d.get("atom_sites") or []]
    xs = [s["x"] % 1.0 for s in d.get("atom_sites") or []]
    ys = [s["y"] % 1.0 for s in d.get("atom_sites") or []]
    print("file", p.name)
    print("atoms", len(zs))
    print("unique_x_round3", len(set(round(x, 3) for x in xs)))
    print("unique_y_round3", len(set(round(y, 3) for y in ys)))
    print("unique_z_round4", len(set(round(z, 4) for z in zs)))
    print("unique_z_round3", len(set(round(z, 3) for z in zs)))
    print("unique_z_round2", len(set(round(z, 2) for z in zs)))
    c = Counter(round(z, 3) for z in zs)
    print("top_bins", c.most_common(25))


if __name__ == "__main__":
    main()
