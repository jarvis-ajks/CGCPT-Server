import json
import math
from pathlib import Path

import stacking_analyzer as sa


def main():
    base = Path(__file__).resolve().parent / "test_cifs"
    for p in sorted(base.glob("*.cif")):
        cif = p.read_text(encoding="utf-8", errors="ignore")
        d = sa.parse_cif_text(cif)
        if not d:
            print(p.name, "parse_failed")
            continue
        layers = sa.extract_layer_features(d) or []
        nz = d.get("atom_sites") or []
        bad = 0
        for l in layers:
            r = l.get("x_to_o_ratio")
            if isinstance(r, float) and not math.isfinite(r):
                bad += 1
        print(p.name, "atoms", len(nz), "layers", len(layers), "bad_ratio", bad)
        if len(layers) <= 12:
            print("  z:", [l.get("z") for l in layers])


if __name__ == "__main__":
    main()
