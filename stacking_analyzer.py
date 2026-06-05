import os
import json
import math
import random
import traceback
from pathlib import Path
from collections import Counter, defaultdict
from fractions import Fraction

import numpy as np

HAS_PYMATGEN = False
HAS_SKLEARN = False

_pymatgen = None
_sklearn_modules = None
_model_cache = {}

DATABASE_DIR = Path(__file__).resolve().parent / "database"
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
MODEL_DIR = Path(__file__).resolve().parent / "models"

UPLOAD_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

LAYER_TYPES = ["XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6", "M6", "M7", "T"]

MAIN_LAYER_TYPES = {"XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6"}
M_LAYER_TYPES = {"M6", "M7"}
X_LAYER_TYPES = {"XO", "XO2", "XO3", "X", "XBO3", "XB3O6"}


def _ensure_pymatgen():
    global HAS_PYMATGEN, _pymatgen
    if _pymatgen is not None:
        return _pymatgen
    try:
        from pymatgen.core import Structure, Lattice, Element
        from pymatgen.io.cif import CifParser
        _pymatgen = {"Structure": Structure, "Lattice": Lattice, "CifParser": CifParser, "Element": Element}
        HAS_PYMATGEN = True
    except ImportError:
        HAS_PYMATGEN = False
        _pymatgen = {}
    return _pymatgen


def _ensure_sklearn():
    global HAS_SKLEARN, _sklearn_modules
    if _sklearn_modules is not None:
        return _sklearn_modules
    try:
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        from sklearn.preprocessing import StandardScaler
        import joblib
        _sklearn_modules = {
            "DecisionTreeClassifier": DecisionTreeClassifier,
            "RandomForestClassifier": RandomForestClassifier,
            "GradientBoostingClassifier": GradientBoostingClassifier,
            "KNeighborsClassifier": KNeighborsClassifier,
            "train_test_split": train_test_split,
            "cross_val_score": cross_val_score,
            "accuracy_score": accuracy_score,
            "classification_report": classification_report,
            "confusion_matrix": confusion_matrix,
            "StandardScaler": StandardScaler,
            "joblib": joblib,
        }
        HAS_SKLEARN = True
    except ImportError:
        HAS_SKLEARN = False
        _sklearn_modules = {}
    return _sklearn_modules


def _rationalize(value, max_den=10000):
    f = Fraction(value).limit_denominator(max_den)
    return f


def _infer_axis_grid(values, max_den=10000, max_grid=100):
    vals = sorted(set(float(v) % 1.0 for v in values))
    if not vals:
        return 1
    fracs = [_rationalize(v, max_den) for v in vals]
    dens = [f.denominator for f in fracs]
    if not dens:
        return 1
    grid = dens[0]
    for d in dens[1:]:
        grid = math.lcm(grid, d)
        if grid > max_grid:
            return max_grid
    return max(1, min(grid, max_grid))


def infer_grid(sites, max_den=10000):
    xs = [p[0] % 1.0 for p in sites]
    ys = [p[1] % 1.0 for p in sites]
    gx = _infer_axis_grid(xs, max_den)
    gy = _infer_axis_grid(ys, max_den)
    return gx, gy


def _frac_diff(a, b):
    d = abs((a % 1.0) - (b % 1.0))
    return min(d, 1.0 - d)


def _group_atoms_by_axis(atom_sites, axis="z", tol=0.02):
    if not atom_sites:
        return []
    coords = sorted(float(s[axis]) % 1.0 for s in atom_sites)
    clusters = []
    curr = [coords[0]]
    for v in coords[1:]:
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
    groups = [[] for _ in centers]
    for s in atom_sites:
        z = float(s[axis]) % 1.0
        best_i = 0
        best_d = _frac_diff(z, centers[0])
        for i in range(1, len(centers)):
            d = _frac_diff(z, centers[i])
            if d < best_d:
                best_d = d
                best_i = i
        if best_d <= tol:
            groups[best_i].append(s)
        else:
            centers.append(z)
            groups.append([s])
    return sorted(zip(centers, groups), key=lambda x: x[0])


def _choose_layer_axis_and_tol(cif_data):
    lattice = cif_data.get("lattice", {}) if cif_data else {}
    atom_sites = cif_data.get("atom_sites", []) if cif_data else []
    n_atoms = len(atom_sites)
    if n_atoms == 0:
        return "z", 0.02

    axis_len_key = {"x": "a", "y": "b", "z": "c"}
    axes = ["z", "y", "x"]

    def axis_tol(axis):
        L = lattice.get(axis_len_key[axis], 0) or 0
        if L and L > 0:
            return min(0.05, max(0.002, 0.5 / float(L)))
        return 0.02

    best = ("z", axis_tol("z"), -1e9)
    for axis in axes:
        tol = axis_tol(axis)
        grouped = _group_atoms_by_axis(atom_sites, axis=axis, tol=tol)
        n_layers = len(grouped)
        if n_layers <= 1:
            score = -1e9
        else:
            compression = (n_atoms - n_layers) / max(n_atoms, 1)
            if n_layers > n_atoms * 0.9:
                compression -= 1.0
            pattern = []
            for _, layer_atoms in grouped:
                has_o = any(a.get("element") == "O" for a in layer_atoms)
                pattern.append(has_o)
            switches = 0
            for i in range(1, len(pattern)):
                if pattern[i] != pattern[i - 1]:
                    switches += 1
            alternating = switches / max(len(pattern) - 1, 1)
            score = compression + 0.2 * alternating - 0.002 * n_layers
        if score > best[2]:
            best = (axis, tol, score)
    return best[0], best[1]


def _plane_coords(layer_atoms, axis):
    if axis == "x":
        return [(s["y"], s["z"]) for s in layer_atoms]
    if axis == "y":
        return [(s["x"], s["z"]) for s in layer_atoms]
    return [(s["x"], s["y"]) for s in layer_atoms]


def parse_cif_text(cif_text):
    pmg = _ensure_pymatgen()
    if not pmg:
        return None
    try:
        from io import StringIO
        parser = pmg["CifParser"](StringIO(cif_text))
        structures = parser.parse_structures(primitive=False)
        if not structures:
            return None
        struct = structures[0]
        lattice = struct.lattice
        atom_sites = []
        for site in struct:
            atom_sites.append({
                "element": site.specie.symbol,
                "x": round(float(site.frac_coords[0]), 8),
                "y": round(float(site.frac_coords[1]), 8),
                "z": round(float(site.frac_coords[2]), 8),
            })
        return {
            "lattice": {
                "a": round(float(lattice.a), 6),
                "b": round(float(lattice.b), 6),
                "c": round(float(lattice.c), 6),
                "alpha": round(float(lattice.alpha), 4),
                "beta": round(float(lattice.beta), 4),
                "gamma": round(float(lattice.gamma), 4),
            },
            "atom_sites": atom_sites,
            "formula": struct.composition.reduced_formula,
            "space_group": None,
        }
    except Exception:
        pass
    return None


def parse_cif_file(cif_path):
    try:
        text = Path(cif_path).read_text(encoding="utf-8", errors="ignore")
        return parse_cif_text(text)
    except Exception:
        return None


def extract_features(cif_data):
    if not cif_data or "atom_sites" not in cif_data:
        return None

    lattice = cif_data.get("lattice", {})
    atom_sites = cif_data.get("atom_sites", [])

    if not atom_sites:
        return None

    a = lattice.get("a", 0)
    b = lattice.get("b", 0)
    c = lattice.get("c", 0)
    alpha = lattice.get("alpha", 90)
    beta = lattice.get("beta", 90)
    gamma = lattice.get("gamma", 90)

    elements = [s["element"] for s in atom_sites]
    elem_counts = Counter(elements)
    total_atoms = len(atom_sites)

    layer_axis, z_tol = _choose_layer_axis_and_tol(cif_data)
    z_groups = _group_atoms_by_axis(atom_sites, axis=layer_axis, tol=z_tol)
    zs = [round(z, 4) for z, _ in z_groups]
    n_z_layers = len(zs)

    z_spacings = []
    for i in range(len(zs)):
        if i + 1 < len(zs):
            z_spacings.append(round(zs[i + 1] - zs[i], 4))
        else:
            z_spacings.append(round(1.0 - zs[i] + zs[0], 4))

    z_spacing_std = float(np.std(z_spacings)) if z_spacings else 0
    z_spacing_mean = float(np.mean(z_spacings)) if z_spacings else 0
    z_spacing_max = max(z_spacings) if z_spacings else 0
    z_spacing_min = min(z_spacings) if z_spacings else 0
    z_spacing_range = z_spacing_max - z_spacing_min if z_spacings else 0
    z_spacing_cv = z_spacing_std / z_spacing_mean if z_spacing_mean > 0 else 0

    layer_atom_counts = []
    layer_o_ratios = []
    layer_compositions = []
    layer_types_list = []
    for z_val, layer_atoms in z_groups:
        layer_atom_counts.append(len(layer_atoms))
        layer_o = sum(1 for s in layer_atoms if s["element"] == "O")
        layer_o_ratios.append(layer_o / len(layer_atoms) if layer_atoms else 0)
        layer_elems = Counter(s["element"] for s in layer_atoms)
        layer_compositions.append(layer_elems)

        has_o = "O" in layer_elems
        o_count = layer_elems.get("O", 0)
        non_o = {e: c for e, c in layer_elems.items() if e != "O"}
        non_o_total = sum(non_o.values())
        x_to_o = (non_o_total / o_count) if o_count > 0 else None

        try:
            gx, gy = infer_grid(_plane_coords(layer_atoms, layer_axis))
        except Exception:
            gx, gy = 1, 1
        gx = min(gx, 100)
        gy = min(gy, 100)

        if has_o:
            if x_to_o is not None and abs(x_to_o - 1.0) < 0.15:
                ltype = "XO"
            elif x_to_o is not None and abs(x_to_o - 0.5) < 0.15:
                ltype = "XO2"
            elif x_to_o is not None and abs(x_to_o - 1.0 / 3.0) < 0.1:
                ltype = "XO3"
            else:
                ltype = "XO3"
        else:
            if "B" in non_o:
                if x_to_o is not None and abs(x_to_o - 1.0 / 3.0) < 0.15:
                    ltype = "XBO3"
                elif non_o_total > 0 and list(non_o.keys())[0] in non_o:
                    b_ratio = non_o.get("B", 0) / non_o_total
                    if b_ratio > 0.5:
                        ltype = "BO3"
                    else:
                        ltype = "XBO3"
                else:
                    ltype = "BO3"
            elif non_o_total > 0 and len(non_o) == 1:
                cation_name = list(non_o.keys())[0]
                if cation_name in ("Si", "Ge", "P", "Al"):
                    ltype = "T"
                elif non_o_total == gx * gy:
                    ltype = "M7"
                elif non_o_total == gx * gy * 2 // 3:
                    ltype = "M6"
                else:
                    ltype = "M7"
            else:
                ltype = "M7"
        layer_types_list.append(ltype)

    layer_atom_std = float(np.std(layer_atom_counts)) if layer_atom_counts else 0
    layer_atom_mean = float(np.mean(layer_atom_counts)) if layer_atom_counts else 0
    layer_atom_cv = layer_atom_std / layer_atom_mean if layer_atom_mean > 0 else 0
    layer_atom_max = max(layer_atom_counts) if layer_atom_counts else 0
    layer_atom_min = min(layer_atom_counts) if layer_atom_counts else 0
    layer_atom_range = layer_atom_max - layer_atom_min

    layer_o_ratio_mean = float(np.mean(layer_o_ratios)) if layer_o_ratios else 0
    layer_o_ratio_std = float(np.std(layer_o_ratios)) if layer_o_ratios else 0
    layer_o_ratio_max = max(layer_o_ratios) if layer_o_ratios else 0
    layer_o_ratio_min = min(layer_o_ratios) if layer_o_ratios else 0

    n_pure_metal_layers = 0
    n_pure_oxygen_layers = 0
    n_mixed_layers = 0
    n_metal_oxygen_layers = 0
    for lc in layer_compositions:
        has_metal = any(e != "O" for e in lc)
        has_oxygen = "O" in lc
        if has_metal and not has_oxygen:
            n_pure_metal_layers += 1
        elif has_oxygen and not has_metal:
            n_pure_oxygen_layers += 1
        elif has_metal and has_oxygen:
            n_metal_oxygen_layers += 1
        else:
            n_mixed_layers += 1

    metal_layer_ratio = n_pure_metal_layers / n_z_layers if n_z_layers > 0 else 0
    oxygen_layer_ratio = n_pure_oxygen_layers / n_z_layers if n_z_layers > 0 else 0
    mixed_layer_ratio = n_metal_oxygen_layers / n_z_layers if n_z_layers > 0 else 0

    alternating_score = 0
    if len(layer_compositions) >= 2:
        switches = 0
        for i in range(1, len(layer_compositions)):
            prev_has_o = "O" in layer_compositions[i - 1]
            curr_has_o = "O" in layer_compositions[i]
            if prev_has_o != curr_has_o:
                switches += 1
        alternating_score = switches / (len(layer_compositions) - 1) if len(layer_compositions) > 1 else 0

    try:
        gx, gy = infer_grid(_plane_coords(atom_sites, layer_axis))
    except Exception:
        gx, gy = 1, 1
    gx = min(gx, 100)
    gy = min(gy, 100)

    is_hexagonal = abs(gamma - 120) < 5 or abs(gamma - 60) < 5
    is_cubic = abs(alpha - 90) < 2 and abs(beta - 90) < 2 and abs(gamma - 90) < 2

    b_over_a = b / a if a > 0 else 1
    c_over_a = c / a if a > 0 else 1

    cation_sizes = []
    non_o_elements = {e: c for e, c in elem_counts.items() if e != "O"}
    pmg = _ensure_pymatgen()
    if pmg:
        Element = pmg["Element"]
        for e, cnt in non_o_elements.items():
            try:
                el = Element(e)
                if el.average_cation_radius and el.average_cation_radius > 0:
                    cation_sizes.append((el.average_cation_radius, cnt))
            except Exception:
                pass

    avg_cation_radius = sum(r * c for r, c in cation_sizes) / sum(c for _, c in cation_sizes) if cation_sizes else 0
    radius_range = (max(r for r, _ in cation_sizes) - min(r for r, _ in cation_sizes)) if len(cation_sizes) > 1 else 0

    z_layer_pattern = []
    for lc in layer_compositions:
        has_o = "O" in lc
        n_elems = len(lc)
        z_layer_pattern.append((has_o, n_elems))

    repeat_len = 1
    for rl in range(1, len(z_layer_pattern) // 2 + 1):
        if len(z_layer_pattern) % rl == 0:
            pattern = z_layer_pattern[:rl]
            is_repeat = all(z_layer_pattern[i] == pattern[i % rl] for i in range(len(z_layer_pattern)))
            if is_repeat and rl < len(z_layer_pattern):
                repeat_len = rl
                break

    n_xo_layers = sum(1 for t in layer_types_list if t == "XO")
    n_xo2_layers = sum(1 for t in layer_types_list if t == "XO2")
    n_xo3_layers = sum(1 for t in layer_types_list if t == "XO3")
    n_x_layers = sum(1 for t in layer_types_list if t == "X")
    n_xbo3_layers = sum(1 for t in layer_types_list if t == "XBO3")
    n_bo3_layers = sum(1 for t in layer_types_list if t == "BO3")
    n_xb3o6_layers = sum(1 for t in layer_types_list if t == "XB3O6")
    n_m6_layers = sum(1 for t in layer_types_list if t == "M6")
    n_m7_layers = sum(1 for t in layer_types_list if t == "M7")
    n_t_layers = sum(1 for t in layer_types_list if t == "T")
    n_main_layers = n_xo_layers + n_xo2_layers + n_xo3_layers + n_x_layers + n_xbo3_layers + n_bo3_layers + n_xb3o6_layers
    n_m_layers = n_m6_layers + n_m7_layers

    layer_type_seq = "-".join(layer_types_list)

    has_xo = int(n_xo_layers > 0)
    has_xo2 = int(n_xo2_layers > 0)
    has_xo3 = int(n_xo3_layers > 0)
    has_x = int(n_x_layers > 0)
    has_xbo3 = int(n_xbo3_layers > 0)
    has_bo3 = int(n_bo3_layers > 0)
    has_xb3o6 = int(n_xb3o6_layers > 0)
    has_m6 = int(n_m6_layers > 0)
    has_m7 = int(n_m7_layers > 0)
    has_t = int(n_t_layers > 0)

    xo3_m7_pairs = 0
    for i in range(len(layer_types_list) - 1):
        if (layer_types_list[i] == "XO3" and layer_types_list[i + 1] == "M7") or \
           (layer_types_list[i] == "M7" and layer_types_list[i + 1] == "XO3"):
            xo3_m7_pairs += 1

    xo3_t_pairs = 0
    for i in range(len(layer_types_list) - 1):
        if (layer_types_list[i] == "XO3" and layer_types_list[i + 1] == "T") or \
           (layer_types_list[i] == "T" and layer_types_list[i + 1] == "XO3"):
            xo3_t_pairs += 1

    xo_t_pairs = 0
    for i in range(len(layer_types_list) - 1):
        if (layer_types_list[i] == "XO" and layer_types_list[i + 1] == "T") or \
           (layer_types_list[i] == "T" and layer_types_list[i + 1] == "XO"):
            xo_t_pairs += 1

    xo2_t_pairs = 0
    for i in range(len(layer_types_list) - 1):
        if (layer_types_list[i] == "XO2" and layer_types_list[i + 1] == "T") or \
           (layer_types_list[i] == "T" and layer_types_list[i + 1] == "XO2"):
            xo2_t_pairs += 1

    main_to_m_ratio = n_main_layers / max(n_m_layers, 1)
    main_to_t_ratio = n_main_layers / max(n_t_layers, 1)
    m_to_t_ratio = n_m_layers / max(n_t_layers, 1)

    o_count_total = elem_counts.get("O", 0)
    non_o_count_total = total_atoms - o_count_total
    o_to_non_o_ratio = o_count_total / max(non_o_count_total, 1)

    n_distinct_layer_types = len(set(layer_types_list))

    features = {
        "n_z_layers": n_z_layers,
        "z_spacing_mean": round(z_spacing_mean, 6),
        "z_spacing_std": round(z_spacing_std, 6),
        "z_spacing_max": round(z_spacing_max, 6),
        "z_spacing_min": round(z_spacing_min, 6),
        "z_spacing_range": round(z_spacing_range, 6),
        "z_spacing_cv": round(z_spacing_cv, 6),
        "layer_atom_mean": round(layer_atom_mean, 2),
        "layer_atom_std": round(layer_atom_std, 2),
        "layer_atom_cv": round(layer_atom_cv, 4),
        "layer_atom_range": layer_atom_range,
        "layer_o_ratio_mean": round(layer_o_ratio_mean, 4),
        "layer_o_ratio_std": round(layer_o_ratio_std, 4),
        "layer_o_ratio_max": round(layer_o_ratio_max, 4),
        "layer_o_ratio_min": round(layer_o_ratio_min, 4),
        "n_pure_metal_layers": n_pure_metal_layers,
        "n_pure_oxygen_layers": n_pure_oxygen_layers,
        "n_metal_oxygen_layers": n_metal_oxygen_layers,
        "metal_layer_ratio": round(metal_layer_ratio, 4),
        "oxygen_layer_ratio": round(oxygen_layer_ratio, 4),
        "mixed_layer_ratio": round(mixed_layer_ratio, 4),
        "alternating_score": round(alternating_score, 4),
        "layer_repeat_len": repeat_len,
        "grid_x": gx,
        "grid_y": gy,
        "is_hexagonal": int(is_hexagonal),
        "is_cubic": int(is_cubic),
        "b_over_a": round(b_over_a, 4),
        "c_over_a": round(c_over_a, 4),
        "alpha": round(alpha, 2),
        "gamma": round(gamma, 2),
        "avg_cation_radius": round(avg_cation_radius, 4),
        "radius_range": round(radius_range, 4),
        "n_xo_layers": n_xo_layers,
        "n_xo2_layers": n_xo2_layers,
        "n_xo3_layers": n_xo3_layers,
        "n_x_layers": n_x_layers,
        "n_xbo3_layers": n_xbo3_layers,
        "n_bo3_layers": n_bo3_layers,
        "n_xb3o6_layers": n_xb3o6_layers,
        "n_m6_layers": n_m6_layers,
        "n_m7_layers": n_m7_layers,
        "n_t_layers": n_t_layers,
        "n_main_layers": n_main_layers,
        "n_m_layers": n_m_layers,
        "has_xo": has_xo,
        "has_xo2": has_xo2,
        "has_xo3": has_xo3,
        "has_x": has_x,
        "has_xbo3": has_xbo3,
        "has_bo3": has_bo3,
        "has_xb3o6": has_xb3o6,
        "has_m6": has_m6,
        "has_m7": has_m7,
        "has_t": has_t,
        "xo3_m7_pairs": xo3_m7_pairs,
        "xo3_t_pairs": xo3_t_pairs,
        "xo_t_pairs": xo_t_pairs,
        "xo2_t_pairs": xo2_t_pairs,
        "main_to_m_ratio": round(main_to_m_ratio, 4),
        "main_to_t_ratio": round(main_to_t_ratio, 4),
        "m_to_t_ratio": round(m_to_t_ratio, 4),
        "o_to_non_o_ratio": round(o_to_non_o_ratio, 4),
        "n_distinct_layer_types": n_distinct_layer_types,
        "layer_type_seq": layer_type_seq,
    }

    return features


def extract_layer_features(cif_data):
    if not cif_data or "atom_sites" not in cif_data:
        return None

    atom_sites = cif_data.get("atom_sites", [])
    lattice = cif_data.get("lattice", {})

    if not atom_sites:
        return None

    layer_infos = []
    layer_axis, z_tol = _choose_layer_axis_and_tol(cif_data)
    for z_val, layer_atoms in _group_atoms_by_axis(atom_sites, axis=layer_axis, tol=z_tol):
        elements_in_layer = Counter(s["element"] for s in layer_atoms)
        has_o = "O" in elements_in_layer
        o_count = elements_in_layer.get("O", 0)
        non_o = {e: c for e, c in elements_in_layer.items() if e != "O"}
        non_o_total = sum(non_o.values())

        x_to_o = (non_o_total / o_count) if o_count > 0 else None

        try:
            gx, gy = infer_grid(_plane_coords(layer_atoms, layer_axis))
        except Exception:
            gx, gy = 1, 1
        gx = min(gx, 100)
        gy = min(gy, 100)

        layer_type = "unknown"
        if has_o:
            if abs(x_to_o - 1.0) < 0.15:
                layer_type = "XO"
            elif abs(x_to_o - 0.5) < 0.15:
                layer_type = "XO2"
            elif abs(x_to_o - 1.0 / 3.0) < 0.1:
                layer_type = "XO3"
            elif o_count == 0 and non_o_total > 0:
                layer_type = "X"
            else:
                layer_type = "XO3"
        else:
            if non_o_total > 0 and len(non_o) == 1:
                cation_name = list(non_o.keys())[0]
                if cation_name in ("Si", "Ge", "P", "Al"):
                    layer_type = "T"
                elif non_o_total == gx * gy or non_o_total == gx * gy * 2 // 3:
                    if non_o_total == gx * gy:
                        layer_type = "M7"
                    else:
                        layer_type = "M6"
                else:
                    layer_type = "M7"
            elif "B" in non_o:
                if x_to_o is not None and abs(x_to_o - 1.0 / 3.0) < 0.15:
                    layer_type = "XBO3"
                else:
                    layer_type = "BO3"
            else:
                layer_type = "M7"

        layer_infos.append({
            "z": round(z_val, 4),
            "n_atoms": len(layer_atoms),
            "elements": dict(elements_in_layer),
            "has_oxygen": has_o,
            "x_to_o_ratio": (round(x_to_o, 4) if x_to_o is not None else None),
            "grid_x": gx,
            "grid_y": gy,
            "predicted_type": layer_type,
        })

    return layer_infos


def scan_database_cifs(data_dir=None):
    if data_dir is None:
        data_dir = DATABASE_DIR
    data_dir = Path(data_dir)

    samples = []
    seen_filenames = set()

    cif_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir() and any(d.glob("*.cif"))])

    for cif_dir in cif_dirs:
        dir_name = cif_dir.name

        if dir_name.startswith("Raw_Proto_"):
            label = dir_name.replace("Raw_Proto_", "")
            source = "raw"
        elif dir_name.startswith("Verified_Proto_"):
            label = dir_name.replace("Verified_Proto_", "")
            source = "verified"
        else:
            label = dir_name
            source = "direct"

        proto_path = data_dir / f"Proto_{label}.json"
        expanded_modes = []
        if proto_path.exists():
            try:
                with open(proto_path, "r", encoding="utf-8") as f:
                    proto_data = json.load(f)
                expanded_modes = proto_data.get("topology_theory", {}).get("expanded_modes", [])
            except Exception:
                pass

        for cif_path in sorted(cif_dir.glob("*.cif")):
            fname = cif_path.name
            if fname in seen_filenames:
                continue
            seen_filenames.add(fname)

            cif_data = parse_cif_file(cif_path)
            if not cif_data:
                continue
            features = extract_features(cif_data)
            if not features:
                continue
            layer_features = extract_layer_features(cif_data)

            sample = {
                "filename": fname,
                "topology": label,
                "formula": cif_data.get("formula", ""),
                "space_group": cif_data.get("space_group", ""),
                "features": features,
                "layer_analysis": layer_features,
                "expanded_modes": expanded_modes,
                "source": source,
            }
            samples.append(sample)

    return samples


def get_layer_type_labels(samples):
    labels = {}
    for s in samples:
        topo = s["topology"]
        modes = s.get("expanded_modes", [])
        if modes:
            main_modes = [m for m in modes if m in MAIN_LAYER_TYPES]
            if main_modes:
                labels[topo] = main_modes[0]
            else:
                labels[topo] = modes[0] if modes else "unknown"
        else:
            parts = topo.split("-")
            main_parts = [p for p in parts if p in MAIN_LAYER_TYPES]
            labels[topo] = main_parts[0] if main_parts else "unknown"
    return labels


MODE_LIST = ["XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6", "M6", "M7", "T"]
MODE_TO_IDX = {m: i for i, m in enumerate(MODE_LIST)}
SHIFT_TO_IDX = {"A": 0, "B": 1, "C": 2}
IDX_TO_SHIFT = {0: "A", 1: "B", 2: "C"}

MAIN_MODES = {"XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6"}
X_MODES_SET = {"XO", "XO2", "XO3", "X", "XBO3", "XB3O6"}
M_MODES_SET = {"M6", "M7"}

STACK_SEQUENCES = ["ABC", "AB", "ACB", "AAB", "ABB", "AA", "ABCA", "ABCAB", "ABCB"]

STACKING_FEATURE_NAMES = [
    "current_mode",
    "is_main_layer",
    "is_x_layer",
    "is_m_layer",
    "is_t_layer",
    "prev_mode",
    "next_mode",
    "prev_is_main",
    "next_is_main",
    "prev_is_xb3o6",
    "next_is_xb3o6",
    "lower_main_shift",
    "upper_main_shift",
    "between_xb3o6",
    "n_main_in_seq",
    "n_x_in_seq",
    "seq_len",
    "x_layer_position",
    "prev_x_shift",
]


def _is_valid_layer_sequence(modes):
    if not modes:
        return False
    has_main = any(m in MAIN_MODES for m in modes)
    if not has_main:
        return False
    for i, m in enumerate(modes):
        if m in M_MODES_SET:
            left = modes[(i - 1) % len(modes)]
            right = modes[(i + 1) % len(modes)]
            if left not in MAIN_MODES and right not in MAIN_MODES:
                return False
    return True


def _generate_layer_sequences():
    import itertools
    main_pool = ["XO3", "XO2", "XO", "XBO3", "XB3O6", "BO3", "X"]
    m_pool = ["M7", "M6"]
    sequences = []

    for n_main in range(2, 6):
        for main_combo in itertools.combinations_with_replacement(main_pool, n_main):
            for perm in set(itertools.permutations(main_combo)):
                for n_m in range(0, min(3, n_main)):
                    for m_positions in itertools.combinations(range(1, len(perm)), n_m):
                        modes = list(perm)
                        offset = 0
                        for pos in m_positions:
                            m_type = m_pool[np.random.randint(0, len(m_pool))]
                            modes.insert(pos + offset, m_type)
                            offset += 1
                        if _is_valid_layer_sequence(modes):
                            sequences.append(tuple(modes))

    unique = list(set(sequences))
    return unique


def _extract_features_for_layer(layer_modes, shift_sequence, idx, gen):
    n = len(layer_modes)
    mode = layer_modes[idx]
    prev_mode = layer_modes[(idx - 1) % n]
    next_mode = layer_modes[(idx + 1) % n]

    is_main = 1 if mode in MAIN_MODES else 0
    is_x = 1 if mode in X_MODES_SET else 0
    is_m = 1 if mode in M_MODES_SET else 0
    is_t = 1 if mode == "T" else 0

    prev_is_main = 1 if prev_mode in MAIN_MODES else 0
    next_is_main = 1 if next_mode in MAIN_MODES else 0
    prev_is_xb3o6 = 1 if prev_mode == "XB3O6" else 0
    next_is_xb3o6 = 1 if next_mode == "XB3O6" else 0

    lower_main_shift = -1
    upper_main_shift = -1
    search = (idx - 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in MAIN_MODES:
            lower_main_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search - 1) % n
        steps += 1

    search = (idx + 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in MAIN_MODES:
            upper_main_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search + 1) % n
        steps += 1

    between_xb3o6 = 0
    if mode in M_MODES_SET:
        try:
            between_xb3o6 = 1 if gen.is_m_layer_between_xb3o6(idx, layer_modes) else 0
        except Exception:
            between_xb3o6 = 0

    n_main_in_seq = sum(1 for m in layer_modes if m in MAIN_MODES)
    n_x_in_seq = sum(1 for m in layer_modes if m in X_MODES_SET)
    seq_len = n

    x_layer_position = 0
    for k in range(idx):
        if layer_modes[k] in X_MODES_SET:
            x_layer_position += 1
    if mode not in X_MODES_SET:
        x_layer_position = -1

    prev_x_shift = -1
    search = (idx - 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in X_MODES_SET and shift_sequence[search] is not None:
            prev_x_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search - 1) % n
        steps += 1

    return [
        MODE_TO_IDX.get(mode, 0),
        is_main,
        is_x,
        is_m,
        is_t,
        MODE_TO_IDX.get(prev_mode, 0),
        MODE_TO_IDX.get(next_mode, 0),
        prev_is_main,
        next_is_main,
        prev_is_xb3o6,
        next_is_xb3o6,
        lower_main_shift,
        upper_main_shift,
        between_xb3o6,
        n_main_in_seq,
        n_x_in_seq,
        seq_len,
        x_layer_position,
        prev_x_shift,
    ]


def _generate_stacking_training_data(max_sequences=500):
    from layer_generator import LayeredXOGenerator
    gen = LayeredXOGenerator(enable_t=True)
    sequences = _generate_layer_sequences()

    if len(sequences) > max_sequences:
        indices = np.random.choice(len(sequences), max_sequences, replace=False)
        sequences = [sequences[i] for i in indices]

    X_data = []
    y_data = []

    for layer_modes in sequences:
        layer_modes = list(layer_modes)
        n_x = sum(1 for m in layer_modes if m in X_MODES_SET)
        if n_x == 0:
            continue

        for stack_seq in STACK_SEQUENCES:
            try:
                shift_seq, _ = gen.build_full_shift_sequence_without_T(layer_modes, stack_seq)

                layer_angles = [0.0] * len(layer_modes)
                layer_dxs = [0.0] * len(layer_modes)
                layer_dys = [0.0] * len(layer_modes)
                alphas = [1.0] * sum(1 for m in layer_modes if m in MAIN_MODES)
                z_seq, _ = gen.build_z_sequence_without_T(layer_modes, alphas)

                if gen.enable_t:
                    result = gen.insert_T_layers(
                        layer_modes, shift_seq, z_seq, layer_angles, layer_dxs, layer_dys
                    )
                    final_modes = result[0]
                    final_shifts = result[1]
                else:
                    final_modes = layer_modes
                    final_shifts = shift_seq

                for i in range(len(final_modes)):
                    features = _extract_features_for_layer(final_modes, final_shifts, i, gen)
                    label = SHIFT_TO_IDX.get(final_shifts[i], -1)
                    if label >= 0:
                        X_data.append(features)
                        y_data.append(label)

            except Exception:
                continue

    return np.array(X_data), np.array(y_data)


def train_decision_tree(samples=None, test_ratio=0.2, max_depth=10, random_state=42,
                        model_type="stacking_dt", n_iterations=1, cv_folds=5,
                        progress_callback=None, data_dir=None, max_sequences=500):
    sk = _ensure_sklearn()
    if not sk:
        return {"success": False, "error": "scikit-learn未安装，请运行: pip install scikit-learn"}

    try:
        from layer_generator import LayeredXOGenerator
    except ImportError:
        return {"success": False, "error": "layer_generator模块未找到，无法生成训练数据"}

    if progress_callback:
        progress_callback({
            "phase": "generating_data",
            "message": "正在使用LayeredXOGenerator生成堆垛训练数据...",
        })

    X, y = _generate_stacking_training_data(max_sequences=max_sequences)

    if len(X) < 100:
        return {"success": False, "error": f"生成的训练样本不足({len(X)})，至少需要100个样本"}

    n_classes = len(set(y))
    class_counts = Counter(y.tolist())
    min_class_count = min(class_counts.values())

    if progress_callback:
        progress_callback({
            "phase": "data_ready",
            "n_samples": len(X),
            "n_features": X.shape[1],
            "n_classes": n_classes,
            "class_distribution": {IDX_TO_SHIFT.get(int(k), str(k)): v for k, v in class_counts.items()},
        })

    train_test_split = sk["train_test_split"]
    cross_val_score = sk["cross_val_score"]
    accuracy_score = sk["accuracy_score"]
    classification_report = sk["classification_report"]
    confusion_matrix = sk["confusion_matrix"]
    DecisionTreeClassifier = sk["DecisionTreeClassifier"]
    joblib = sk["joblib"]

    actual_test_ratio = max(0.1, min(0.5, test_ratio))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=actual_test_ratio, random_state=random_state, stratify=y
    )

    if progress_callback:
        progress_callback({
            "phase": "training",
            "message": "正在训练堆垛预测决策树...",
            "n_train": len(X_train),
            "n_test": len(X_test),
        })

    depths = [5, 8, 10, 12, 15] if max_depth is None else [max_depth]
    best_overall = None
    best_overall_score = -1
    all_results = []

    for depth in depths:
        for criterion in ["gini", "entropy"]:
            for msl in [2, 5, 10]:
                for mss in [2, 5, 10]:
                    try:
                        clf = DecisionTreeClassifier(
                            max_depth=depth,
                            criterion=criterion,
                            min_samples_leaf=msl,
                            min_samples_split=mss,
                            random_state=random_state,
                        )
                        clf.fit(X_train, y_train)
                        y_pred = clf.predict(X_test)
                        test_acc = accuracy_score(y_test, y_pred)
                        train_acc = accuracy_score(y_train, clf.predict(X_train))

                        cv_mean = round(float(test_acc), 4)
                        cv_std = 0.0
                        if cv_folds >= 2:
                            try:
                                cv_n = min(cv_folds, min_class_count)
                                cv_scores = cross_val_score(clf, X, y, cv=cv_n, scoring="accuracy")
                                cv_mean = round(float(cv_scores.mean()), 4)
                                cv_std = round(float(cv_scores.std()), 4)
                            except Exception:
                                pass

                        overfit = train_acc - test_acc

                        composite = cv_mean - cv_std * 0.3 - max(0, overfit - 0.05) * 2.0

                        all_results.append({
                            "max_depth": depth,
                            "criterion": criterion,
                            "min_samples_leaf": msl,
                            "min_samples_split": mss,
                            "test_accuracy": round(float(test_acc), 4),
                            "train_accuracy": round(float(train_acc), 4),
                            "overfit": round(float(overfit), 4),
                            "cv_mean": cv_mean,
                            "cv_std": cv_std,
                        })

                        if composite > best_overall_score:
                            best_overall_score = composite
                            best_overall = {
                                "clf": clf,
                                "test_accuracy": round(float(test_acc), 4),
                                "train_accuracy": round(float(train_acc), 4),
                                "overfit": round(float(overfit), 4),
                                "cv_mean": cv_mean,
                                "cv_std": cv_std,
                                "max_depth": depth,
                                "criterion": criterion,
                                "min_samples_leaf": msl,
                                "min_samples_split": mss,
                            }
                    except Exception:
                        continue

    if best_overall is None:
        return {"success": False, "error": "所有参数组合训练失败"}

    if progress_callback:
        progress_callback({"phase": "finalizing", "message": "正在保存模型..."})

    best_clf = best_overall["clf"]
    y_pred_final = best_clf.predict(X_test)

    model_id = f"stacking_dt_{random.randint(10000, 99999)}"
    model_path = MODEL_DIR / f"{model_id}.pkl"
    joblib.dump({
        "model": best_clf,
        "scaler": None,
        "needs_scaling": False,
        "feature_keys": STACKING_FEATURE_NAMES,
        "model_type": "stacking_dt",
        "label_map": IDX_TO_SHIFT,
    }, model_path)

    feature_importances = []
    if hasattr(best_clf, "feature_importances_"):
        fi = dict(zip(STACKING_FEATURE_NAMES, best_clf.feature_importances_.tolist()))
        feature_importances = sorted(fi.items(), key=lambda x: x[1], reverse=True)[:20]

    y_test_labels = [IDX_TO_SHIFT.get(int(l), str(l)) for l in y_test]
    y_pred_labels = [IDX_TO_SHIFT.get(int(l), str(l)) for l in y_pred_final]

    report = classification_report(y_test_labels, y_pred_labels, output_dict=True, zero_division=0)

    cm = confusion_matrix(y_test, y_pred_final)
    class_labels = ["A", "B", "C"]
    cm_list = cm.tolist()
    cm_data = {"labels": class_labels, "matrix": cm_list}

    _model_cache.pop(model_id, None)

    return {
        "success": True,
        "model_id": model_id,
        "model_type": "stacking_dt",
        "best_params": {
            "model_type": "stacking_dt",
            "model_name": f"堆垛预测决策树(d={best_overall['max_depth']},{best_overall['criterion'][:3]},msl={best_overall['min_samples_leaf']},mss={best_overall['min_samples_split']})",
            "test_accuracy": best_overall["test_accuracy"],
            "train_accuracy": best_overall["train_accuracy"],
            "overfit": best_overall["overfit"],
            "cv_mean": best_overall["cv_mean"],
            "cv_std": best_overall["cv_std"],
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_classes": n_classes,
            "max_depth": best_overall["max_depth"],
            "criterion": best_overall["criterion"],
            "min_samples_leaf": best_overall["min_samples_leaf"],
            "min_samples_split": best_overall["min_samples_split"],
        },
        "feature_importances": feature_importances,
        "classification_report": report,
        "confusion_matrix": cm_data,
        "n_configs_tested": len(all_results),
        "feature_keys": STACKING_FEATURE_NAMES,
        "n_total_samples": len(X),
        "n_valid_samples": len(X),
        "class_distribution": {IDX_TO_SHIFT.get(int(k), str(k)): v for k, v in class_counts.items()},
        "test_ratio": actual_test_ratio,
        "training_data_source": "LayeredXOGenerator规则生成",
    }


def _load_model(model_id):
    if model_id in _model_cache:
        return _model_cache[model_id]

    sk = _ensure_sklearn()
    if not sk:
        return None

    model_path = MODEL_DIR / f"{model_id}.pkl"
    if not model_path.exists():
        return None

    try:
        saved = sk["joblib"].load(model_path)
        _model_cache[model_id] = saved
        if len(_model_cache) > 5:
            oldest_key = next(iter(_model_cache))
            del _model_cache[oldest_key]
        return saved
    except Exception:
        return None


def predict_stacking(model_id, layer_modes, stack_sequence="ABC"):
    model_path = MODEL_DIR / f"{model_id}.pkl"
    if not model_path.exists():
        return {"success": False, "error": f"模型不存在: {model_id}"}

    saved = _load_model(model_id)
    if saved is None:
        return {"success": False, "error": "模型加载失败"}

    if isinstance(saved, dict):
        clf = saved["model"]
        label_map = saved.get("label_map", IDX_TO_SHIFT)
    else:
        clf = saved
        label_map = IDX_TO_SHIFT

    try:
        from layer_generator import LayeredXOGenerator
    except ImportError:
        return {"success": False, "error": "layer_generator模块未找到"}

    gen = LayeredXOGenerator(enable_t=True)

    try:
        shift_seq, _ = gen.build_full_shift_sequence_without_T(layer_modes, stack_sequence)

        layer_angles = [0.0] * len(layer_modes)
        layer_dxs = [0.0] * len(layer_modes)
        layer_dys = [0.0] * len(layer_modes)
        alphas = [1.0] * sum(1 for m in layer_modes if m in MAIN_MODES)
        z_seq, _ = gen.build_z_sequence_without_T(layer_modes, alphas)

        if gen.enable_t:
            result = gen.insert_T_layers(
                layer_modes, shift_seq, z_seq, layer_angles, layer_dxs, layer_dys
            )
            final_modes = result[0]
            final_shifts = result[1]
        else:
            final_modes = layer_modes
            final_shifts = shift_seq
    except Exception as e:
        return {"success": False, "error": f"层序列处理失败: {str(e)}"}

    predictions = []
    rule_shifts = []
    correct = 0

    for i in range(len(final_modes)):
        features = _extract_features_for_layer(final_modes, final_shifts, i, gen)
        pred_label = int(clf.predict([features])[0])
        pred_shift = label_map.get(pred_label, str(pred_label))
        rule_shift = final_shifts[i]
        is_correct = pred_shift == rule_shift
        if is_correct:
            correct += 1

        proba_dict = {}
        if hasattr(clf, "predict_proba"):
            try:
                proba = clf.predict_proba([features])[0]
                classes = clf.classes_.tolist()
                for cls_idx, prob in zip(classes, proba):
                    cls_name = label_map.get(int(cls_idx), str(cls_idx))
                    proba_dict[cls_name] = round(float(prob), 4)
            except Exception:
                pass

        predictions.append({
            "layer_index": i,
            "mode": final_modes[i],
            "rule_shift": rule_shift,
            "predicted_shift": pred_shift,
            "confidence": max(proba_dict.values()) if proba_dict else 0,
            "probabilities": proba_dict,
            "correct": is_correct,
        })
        rule_shifts.append(rule_shift)

    accuracy = correct / len(final_modes) if final_modes else 0

    return {
        "success": True,
        "model_id": model_id,
        "input_modes": layer_modes,
        "input_stack_sequence": stack_sequence,
        "expanded_modes": final_modes,
        "rule_shifts": rule_shifts,
        "predictions": predictions,
        "accuracy": round(accuracy, 4),
        "n_correct": correct,
        "n_total": len(final_modes),
    }


def predict_stacking_from_cif(model_id, cif_data):
    model_path = MODEL_DIR / f"{model_id}.pkl"
    if not model_path.exists():
        return {"success": False, "error": f"模型不存在: {model_id}"}

    saved = _load_model(model_id)
    if saved is None:
        return {"success": False, "error": "模型加载失败"}

    layer_features = extract_layer_features(cif_data)
    if not layer_features:
        return {"success": False, "error": "无法从CIF数据中提取层信息"}

    layer_modes = []
    for lf in layer_features:
        ltype = lf.get("predicted_type", "unknown")
        if ltype in MODE_LIST:
            layer_modes.append(ltype)
        else:
            layer_modes.append("XO3")

    if not layer_modes:
        return {"success": False, "error": "未能识别任何层模式"}

    result = predict_stacking(model_id, layer_modes, "ABC")
    result["layer_analysis"] = layer_features
    result["detected_modes"] = layer_modes

    return result


def list_models():
    models = []
    for model_path in MODEL_DIR.glob("*_*.pkl"):
        model_id = model_path.stem
        meta_path = MODEL_DIR / f"{model_id}_meta.json"
        meta = {}
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
            except Exception:
                pass
        models.append({
            "model_id": model_id,
            "created": meta.get("created", ""),
            "test_accuracy": meta.get("test_accuracy", 0),
            "n_samples": meta.get("n_samples", 0),
            "n_classes": meta.get("n_classes", 0),
        })
    return sorted(models, key=lambda x: x.get("test_accuracy", 0), reverse=True)


def save_model_meta(model_id, train_result):
    meta_path = MODEL_DIR / f"{model_id}_meta.json"
    meta = {
        "model_id": model_id,
        "created": str(Path(MODEL_DIR / f"{model_id}.pkl").stat().st_mtime),
        "test_accuracy": train_result.get("best_params", {}).get("test_accuracy", 0),
        "train_accuracy": train_result.get("best_params", {}).get("train_accuracy", 0),
        "n_samples": train_result.get("n_valid_samples", 0),
        "n_classes": train_result.get("n_classes", 0),
        "best_params": train_result.get("best_params", {}),
        "feature_importances": train_result.get("feature_importances", []),
        "class_distribution": train_result.get("class_distribution", {}),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def delete_model(model_id):
    _model_cache.pop(model_id, None)
    deleted = False
    for ext in [".pkl", "_meta.json"]:
        p = MODEL_DIR / f"{model_id}{ext}"
        if p.exists():
            p.unlink()
            deleted = True
    return deleted
