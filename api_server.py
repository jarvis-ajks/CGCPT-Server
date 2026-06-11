import json
import logging
import math
import os
import re
import sys
import time
import tempfile
import threading
import queue as queue_mod
from pathlib import Path
from collections import defaultdict
from typing import Any, Optional

from flask import Flask, request, jsonify, Response, make_response
from flask_cors import CORS

from config import (
    ADMIN_USER,
    ADMIN_PASS,
    SECRET_KEY,
    HOST,
    PORT,
    DEBUG,
    DATABASE_DIR as CFG_DATABASE_DIR,
    CORS_ORIGINS,
)
from logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload
CORS(app, origins=CORS_ORIGINS.split(",") if CORS_ORIGINS else ["*"])

_start_time = time.time()

DATABASE_DIR = (
    CFG_DATABASE_DIR if CFG_DATABASE_DIR else Path(__file__).resolve().parent / "database"
)

prototypes_index = {}
materials_index = {}
topology_to_materials = defaultdict(list)
element_to_materials = defaultdict(set)
space_group_to_materials = defaultdict(list)
formula_to_materials = defaultdict(list)
all_elements = set()
_indexes_built = False
_index_build_time = 0


class _TTLCache:
    """Thread-safe TTL cache for API responses."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache and key in self._expiry:
                if time.time() < self._expiry[key]:
                    return self._cache[key]
                del self._cache[key]
                del self._expiry[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        with self._lock:
            self._cache[key] = value
            self._expiry[key] = time.time() + ttl

    def invalidate(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._cache.pop(key, None)
                self._expiry.pop(key, None)

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()
            self._expiry.clear()


_api_cache = _TTLCache()


def _sanitize_json_value(value: Any) -> Any:
    """Sanitize JSON values by replacing non-finite floats with None.

    Recursively processes dicts, lists, and tuples to ensure all values
    are JSON-serializable (no NaN or Infinity).

    Args:
        value: The value to sanitize.

    Returns:
        The sanitized value with non-finite floats replaced by None.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _sanitize_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize_json_value(v) for v in value]
    return value


def _get_stack_main() -> Any:
    """Import and return the LayeredXOGenerator class from stack_main.

    Returns:
        The LayeredXOGenerator class, or None if import fails.
    """
    try:
        from stack_main import LayeredXOGenerator

        return LayeredXOGenerator
    except ImportError:
        return None


def _get_pymatgen_structure() -> Any:
    """Import and return the pymatgen Structure class.

    Returns:
        The Structure class, or None if import fails.
    """
    try:
        from pymatgen.core import Structure

        return Structure
    except ImportError:
        return None


def _get_pymatgen_cifparser() -> Any:
    """Import and return the pymatgen CifParser class.

    Returns:
        The CifParser class, or None if import fails.
    """
    try:
        from pymatgen.io.cif import CifParser

        return CifParser
    except ImportError:
        return None


def _get_spacegroup_analyzer() -> Any:
    """Import and return the pymatgen SpacegroupAnalyzer class.

    Returns:
        The SpacegroupAnalyzer class, or None if import fails.
    """
    try:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        return SpacegroupAnalyzer
    except ImportError:
        return None


def _get_verify_topology() -> Any:
    """Import and return the verify_topology module.

    Returns:
        The verify_topology module, or None if import fails.
    """
    try:
        import verify_topology

        return verify_topology
    except ImportError:
        return None


def _get_stacking_analyzer() -> Any:
    """Import and return the stacking_analyzer module.

    Returns:
        The stacking_analyzer module, or None if import fails.
    """
    try:
        import stacking_analyzer

        return stacking_analyzer
    except ImportError:
        return None


def parse_cif_file(cif_path: Path) -> Optional[dict]:
    """Parse a CIF file using pymatgen with manual fallback.

    Args:
        cif_path: Path to the CIF file.

    Returns:
        Dictionary with lattice, atom_sites, formula, space_group or None if parsing fails.
    """
    CifParser = _get_pymatgen_cifparser()
    if CifParser:
        try:
            parser = CifParser(str(cif_path))
            structures = parser.parse_structures(primitive=False)
            if not structures:
                return None
            struct = structures[0]
            lattice = struct.lattice
            atom_sites = []
            for site in struct:
                atom_sites.append(
                    {
                        "element": site.specie.symbol,
                        "x": round(float(site.frac_coords[0]), 8),
                        "y": round(float(site.frac_coords[1]), 8),
                        "z": round(float(site.frac_coords[2]), 8),
                    }
                )
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
            logger.debug(
                "pymatgen CIF parse failed for %s, falling back to manual parser", cif_path
            )

    return parse_cif_file_manual(cif_path)


def parse_cif_file_manual(cif_path: Path) -> Optional[dict]:
    """Parse a CIF file using a manual regex-based parser.

    Args:
        cif_path: Path to the CIF file.

    Returns:
        Dictionary with lattice, atom_sites, formula, space_group or None if parsing fails.
    """
    try:
        text = cif_path.read_text(encoding="utf-8", errors="ignore")
        lattice = {}
        for key, tag in [
            ("a", "_cell_length_a"),
            ("b", "_cell_length_b"),
            ("c", "_cell_length_c"),
            ("alpha", "_cell_angle_alpha"),
            ("beta", "_cell_angle_beta"),
            ("gamma", "_cell_angle_gamma"),
        ]:
            m = re.search(rf"{tag}\s+([\d.]+)", text)
            if m:
                lattice[key] = float(m.group(1))

        sg_match = re.search(r"_symmetry_space_group_name_H-M\s+['\"]?([^'\"]+)['\"]?", text)
        space_group = sg_match.group(1).strip() if sg_match else None

        formula_match = re.search(r"_chemical_formula_structural\s+(\S+)", text)
        formula = formula_match.group(1).strip() if formula_match else ""

        atom_sites = []
        lines = text.splitlines()
        in_loop = False
        loop_tags = []
        data_start = -1
        tag_idx = {}

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("loop_"):
                in_loop = True
                loop_tags = []
                data_start = -1
                tag_idx = {}
                i += 1
                continue

            if in_loop:
                if line.startswith("_"):
                    loop_tags.append(line.split()[0])
                    i += 1
                    continue
                elif loop_tags and not line.startswith("_"):
                    if "_atom_site_fract_x" in loop_tags:
                        for ti, t in enumerate(loop_tags):
                            tag_idx[t] = ti
                        data_start = i
                        while i < len(lines):
                            dl = lines[i].strip()
                            if not dl or dl.startswith("_") or dl.startswith("loop_"):
                                break
                            parts = dl.split()
                            if len(parts) >= len(loop_tags):
                                try:
                                    elem = parts[
                                        tag_idx.get(
                                            "_atom_site_type_symbol",
                                            tag_idx.get("_atom_site_label", 0),
                                        )
                                    ]
                                    elem = re.match(r"[A-Z][a-z]?", elem)
                                    elem = elem.group(0) if elem else parts[0]
                                    fx = float(parts[tag_idx["_atom_site_fract_x"]])
                                    fy = float(parts[tag_idx["_atom_site_fract_y"]])
                                    fz = float(parts[tag_idx["_atom_site_fract_z"]])
                                    atom_sites.append(
                                        {
                                            "element": elem,
                                            "x": round(fx, 8),
                                            "y": round(fy, 8),
                                            "z": round(fz, 8),
                                        }
                                    )
                                except (ValueError, IndexError, KeyError):
                                    pass
                            i += 1
                        in_loop = False
                        continue
                    else:
                        in_loop = False
                        continue
                else:
                    in_loop = False
                    i += 1
                    continue
            i += 1

        return {
            "lattice": lattice,
            "atom_sites": atom_sites,
            "formula": formula,
            "space_group": space_group,
        }
    except Exception:
        return None


def parse_cif_filename(filename: str) -> tuple[str, str, str]:
    """Parse a CIF filename to extract material_id, formula, and space_group.

    Args:
        filename: The CIF filename to parse.

    Returns:
        A tuple of (material_id, formula, space_group).
    """
    stem = Path(filename).stem
    mp_match = re.search(r"(mp-\d+)", stem)
    material_id = mp_match.group(1) if mp_match else stem

    parts = stem.split("_")
    formula = parts[0] if len(parts) >= 1 else stem
    space_group = parts[1] if len(parts) >= 2 else ""

    return material_id, formula, space_group


def extract_elements_from_formula(formula: str) -> list[str]:
    """Extract element symbols from a chemical formula string.

    Args:
        formula: Chemical formula string (e.g., 'BaMgSi2O6').

    Returns:
        List of element symbols found in the formula.
    """
    return [m.group(0) for m in re.finditer(r"[A-Z][a-z]?", formula)]


def build_indexes() -> None:
    """Build in-memory indexes from the filesystem database.

    Scans the DATABASE_DIR for prototype JSON files and CIF directories,
    populating prototypes_index, materials_index, and various lookup maps.
    Only runs once; subsequent calls are no-ops.
    """
    global prototypes_index, materials_index, topology_to_materials
    global element_to_materials, space_group_to_materials
    global formula_to_materials, all_elements, _indexes_built, _index_build_time

    if _indexes_built:
        return
    _indexes_built = True
    _t0 = time.time()

    for json_path in DATABASE_DIR.glob("Proto_*.json"):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            proto_id = json_path.stem.replace("Proto_", "")
            prototypes_index[proto_id] = {
                "id": proto_id,
                "data": data,
                "json_path": str(json_path),
            }
        except Exception:
            logger.warning("Failed to load prototype %s", json_path)

    cif_dirs = list(DATABASE_DIR.glob("Raw_Proto_*")) + list(DATABASE_DIR.glob("Verified_Proto_*"))
    for cif_dir in cif_dirs:
        dir_name = cif_dir.name
        is_verified = dir_name.startswith("Verified_")
        proto_key = dir_name.replace("Raw_Proto_", "").replace("Verified_Proto_", "")

        for cif_file in cif_dir.glob("*.cif"):
            material_id, formula, space_group = parse_cif_filename(cif_file.name)
            elements = extract_elements_from_formula(formula)

            mat_entry = {
                "material_id": material_id,
                "formula": formula,
                "space_group": space_group,
                "elements": elements,
                "topology": proto_key,
                "verified": is_verified,
                "cif_path": str(cif_file),
                "directory": dir_name,
            }

            materials_index[material_id] = mat_entry
            topology_to_materials[proto_key].append(material_id)
            space_group_to_materials[space_group].append(material_id)
            formula_to_materials[formula].append(material_id)
            for el in elements:
                element_to_materials[el].add(material_id)
                all_elements.add(el)

    for el in element_to_materials:
        element_to_materials[el] = element_to_materials[el]

    _index_build_time = time.time() - _t0
    logger.info(
        "Indexed %d prototypes, %d materials in %.2fs",
        len(prototypes_index),
        len(materials_index),
        _index_build_time,
    )


def _parse_generate_body(body: dict) -> tuple[Optional[dict], Optional[str]]:
    """Parse and validate the request body for structure generation endpoints.

    Args:
        body: The JSON request body dictionary.

    Returns:
        A tuple of (params_dict, None) on success, or (None, error_message) on failure.
    """
    x_element = body.get("x_element", "Ba")
    o_element = body.get("o_element", "O")
    m_element = body.get("m_element", "Mg")
    t_element = body.get("t_element", "Si")
    b_element = body.get("b_element", "B")
    target_xo_distance = float(body.get("target_xo_distance", 2.77648))
    nx = int(body.get("nx", 3))
    ny = int(body.get("ny", 3))
    enable_t = bool(body.get("enable_t", True))

    layer_modes = body.get("layer_modes", [])
    layer_alphas = body.get("layer_alphas", [])
    stack_sequence = body.get("stack_sequence", "ABC")
    layer_angles = body.get("layer_angles", [])
    layer_dxs = body.get("layer_dxs", [])
    layer_dys = body.get("layer_dys", [])

    if not layer_modes:
        return None, "layer_modes is required"

    if not layer_alphas:
        main_count = sum(
            1
            for mode in layer_modes
            if mode.upper() in ("XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6")
        )
        layer_alphas = [1.0] * main_count

    if len(layer_angles) < len(layer_modes):
        layer_angles = layer_angles + [0.0] * (len(layer_modes) - len(layer_angles))
    if len(layer_dxs) < len(layer_modes):
        layer_dxs = layer_dxs + [0.0] * (len(layer_modes) - len(layer_dxs))
    if len(layer_dys) < len(layer_modes):
        layer_dys = layer_dys + [0.0] * (len(layer_modes) - len(layer_dys))

    params = {
        "x_element": x_element,
        "o_element": o_element,
        "m_element": m_element,
        "t_element": t_element,
        "b_element": b_element,
        "target_xo_distance": target_xo_distance,
        "nx": nx,
        "ny": ny,
        "enable_t": enable_t,
        "layer_modes": layer_modes,
        "layer_alphas": layer_alphas,
        "stack_sequence": stack_sequence,
        "layer_angles": layer_angles,
        "layer_dxs": layer_dxs,
        "layer_dys": layer_dys,
    }
    return params, None


def _build_structure_from_params(params: dict) -> tuple:
    """Build a layered structure from the given parameters.

    Args:
        params: Dictionary of generation parameters from _parse_generate_body.

    Returns:
        A tuple of (LayeredXOGenerator instance, build_structure result tuple).

    Raises:
        RuntimeError: If stack_main module is not available.
    """
    LayeredXOGenerator = _get_stack_main()
    if LayeredXOGenerator is None:
        raise RuntimeError("stack_main模块未安装，无法生成结构")

    gen = LayeredXOGenerator(
        x_element=params["x_element"],
        o_element=params["o_element"],
        m_element=params["m_element"],
        t_element=params["t_element"],
        b_element=params["b_element"],
        target_xo_distance=params["target_xo_distance"],
        nx=params["nx"],
        ny=params["ny"],
        enable_t=params["enable_t"],
    )

    result = gen.build_structure(
        params["layer_modes"],
        params["layer_alphas"],
        params["stack_sequence"],
        params["layer_angles"],
        params["layer_dxs"],
        params["layer_dys"],
    )

    return gen, result


def _extract_structure_info(gen: Any, result: tuple) -> dict:
    """Extract detailed structure information from a generation result.

    Args:
        gen: The LayeredXOGenerator instance.
        result: The result tuple from gen.build_structure().

    Returns:
        Dictionary with formula, lattice, atom_sites, atom_counts, topology,
        space_group, structure, gen, and result keys.
    """
    structure = result[0]
    exact_flag = result[1]
    base_len = result[2]
    expanded_modes = result[6]
    expanded_shifts = result[7]
    expanded_zs = result[8]
    main_shift_sequence = result[9]
    expanded_angles = result[10]
    expanded_dxs = result[11]
    expanded_dys = result[12]
    ref_mode = result[13]

    info = gen.analyze_structure(structure)

    atom_sites = []
    for site in structure:
        atom_sites.append(
            {
                "element": site.specie.symbol,
                "x": round(float(site.frac_coords[0]), 8),
                "y": round(float(site.frac_coords[1]), 8),
                "z": round(float(site.frac_coords[2]), 8),
            }
        )

    lattice_info = {
        "a": round(float(info["a"]), 6),
        "b": round(float(info["b"]), 6),
        "c": round(float(info["c"]), 6),
        "alpha": 90.0,
        "beta": 90.0,
        "gamma": 60.0,
    }

    space_group_info = {}
    SpacegroupAnalyzer = _get_spacegroup_analyzer()
    if SpacegroupAnalyzer:
        try:
            sga = SpacegroupAnalyzer(structure, symprec=1e-3)
            space_group_info = {
                "symbol": sga.get_space_group_symbol(),
                "number": sga.get_space_group_number(),
                "crystal_system": sga.get_crystal_system(),
            }
        except Exception:
            logger.debug("Space group analysis failed")

    topology_info = {
        "expanded_modes": expanded_modes,
        "expanded_shifts": expanded_shifts,
        "expanded_zs": [round(float(z), 8) for z in expanded_zs],
        "main_shift_sequence": main_shift_sequence,
        "reference_grid": ref_mode,
        "exact_flag": exact_flag,
        "base_length": round(float(base_len), 6),
    }

    atom_counts = {
        "x_count": info["x_count"],
        "o_count": info["o_count"],
        "m_count": info["m_count"],
        "t_count": info["t_count"],
        "b_count": info["b_count"],
    }

    return {
        "structure": structure,
        "gen": gen,
        "result": result,
        "formula": info["formula"],
        "lattice": lattice_info,
        "atom_sites": atom_sites,
        "atom_counts": atom_counts,
        "topology": topology_info,
        "space_group": space_group_info,
    }


def _get_layer_data(gen: Any, result: tuple) -> list[dict]:
    """Extract per-layer atom data for 2D plotting.

    Args:
        gen: The LayeredXOGenerator instance.
        result: The result tuple from gen.build_structure().

    Returns:
        List of layer dictionaries with mode, shift, z, theta, dx, dy, grid coords, and atoms.
    """
    layer_data = gen.get_layer_atoms_for_plot(
        result[6],
        result[7],
        result[8],
        result[10],
        result[11],
        result[12],
        result[2],
        result[0].lattice,
    )
    serialized = []
    for layer in layer_data:
        atoms_serialized = []
        for elem, fx, fy in layer["atoms"]:
            atoms_serialized.append(
                {
                    "element": elem,
                    "fx": round(float(fx), 8),
                    "fy": round(float(fy), 8),
                }
            )
        serialized.append(
            {
                "mode": layer["mode"],
                "shift": layer["shift"],
                "z": round(float(layer["z"]), 8),
                "theta": float(layer["theta"]),
                "dx": float(layer["dx"]),
                "dy": float(layer["dy"]),
                "grid_x": layer["grid_x"],
                "grid_y": layer["grid_y"],
                "atoms": atoms_serialized,
            }
        )
    return serialized


def _get_primitive_analysis(structure: Any) -> dict:
    """Analyze the primitive cell of a structure.

    Args:
        structure: A pymatgen Structure object.

    Returns:
        Dictionary with primitive cell info and wyckoff_signature, or error key on failure.
    """
    SpacegroupAnalyzer = _get_spacegroup_analyzer()
    if not SpacegroupAnalyzer:
        return {"error": "pymatgen SpacegroupAnalyzer not available"}

    try:
        sga = SpacegroupAnalyzer(structure, symprec=1e-3)
        primitive = sga.get_primitive_standard_structure()

        prim_atom_sites = []
        for site in primitive:
            prim_atom_sites.append(
                {
                    "element": site.specie.symbol,
                    "x": round(float(site.frac_coords[0]), 8),
                    "y": round(float(site.frac_coords[1]), 8),
                    "z": round(float(site.frac_coords[2]), 8),
                }
            )

        prim_lattice = primitive.lattice
        prim_lattice_info = {
            "a": round(float(prim_lattice.a), 6),
            "b": round(float(prim_lattice.b), 6),
            "c": round(float(prim_lattice.c), 6),
            "alpha": round(float(prim_lattice.alpha), 4),
            "beta": round(float(prim_lattice.beta), 4),
            "gamma": round(float(prim_lattice.gamma), 4),
        }

        try:
            sga_prim = SpacegroupAnalyzer(primitive, symprec=1e-3)
            space_group = sga_prim.get_space_group_symbol()
            space_group_number = sga_prim.get_space_group_number()
        except Exception:
            logger.debug("Space group analysis failed")
            space_group = None
            space_group_number = None

        unique_sites = {}
        for site in primitive:
            elem = site.specie.symbol
            if elem not in unique_sites:
                unique_sites[elem] = 0
            unique_sites[elem] += 1

        is_neutral = False
        try:
            is_neutral = len(primitive.composition.oxi_state_guesses()) > 0
        except Exception:
            pass

        wyckoff_sig = {}
        try:
            dataset = sga.get_symmetry_dataset()
            if dataset and "wyckoffs" in dataset:
                wyckoffs_list = dataset["wyckoffs"]
                for idx, site in enumerate(structure):
                    elem = site.specie.symbol
                    w_letter = wyckoffs_list[idx]
                    if elem not in wyckoff_sig:
                        wyckoff_sig[elem] = set()
                    wyckoff_sig[elem].add(w_letter)
                wyckoff_sig = {k: ", ".join(sorted(v)) for k, v in wyckoff_sig.items()}
        except Exception:
            logger.debug("Wyckoff analysis failed")

        return {
            "primitive": {
                "atom_sites": prim_atom_sites,
                "lattice": prim_lattice_info,
                "formula": primitive.composition.reduced_formula,
                "space_group": space_group,
                "space_group_number": space_group_number,
                "unique_sites": unique_sites,
                "is_neutral": is_neutral,
            },
            "wyckoff_signature": wyckoff_sig,
        }
    except Exception as e:
        return {"error": str(e)}


def _get_coordination_analysis(
    structure: Any, x_element: str, o_element: str, cutoff_radius: Optional[float] = None
) -> dict:
    """Analyze coordination environments of X atoms with O neighbors.

    Args:
        structure: A pymatgen Structure object.
        x_element: Symbol of the X (cation) element.
        o_element: Symbol of the O (anion) element.
        cutoff_radius: Distance cutoff for neighbor search. Defaults to 2.77648 * 1.35.

    Returns:
        Dictionary with environments list containing coordination numbers and neighbor details.
    """
    if cutoff_radius is None:
        cutoff_radius = 2.77648 * 1.35

    try:
        import numpy as np

        x_sites = [site for site in structure if site.specie.symbol == x_element]
        if not x_sites:
            return {"environments": [], "message": f"结构中未找到 {x_element} 原子"}

        env_dict = {}
        for site in x_sites:
            neighbors = structure.get_neighbors(site, r=cutoff_radius)
            o_neighbors = [nn for nn in neighbors if nn.specie.symbol == o_element]
            cn = len(o_neighbors)
            if cn > 0 and cn not in env_dict:
                env_dict[cn] = (site, o_neighbors)

        environments = []
        for cn in sorted(env_dict.keys()):
            center_site, o_neighbors = env_dict[cn]
            neighbor_list = []
            for nn in o_neighbors:
                dx = nn.coords[0] - center_site.coords[0]
                dy = nn.coords[1] - center_site.coords[1]
                dz = nn.coords[2] - center_site.coords[2]
                dist = float(np.linalg.norm([dx, dy, dz]))
                neighbor_list.append(
                    {
                        "element": nn.specie.symbol,
                        "dx": round(float(dx), 6),
                        "dy": round(float(dy), 6),
                        "dz": round(float(dz), 6),
                        "distance": round(dist, 6),
                    }
                )

            environments.append(
                {
                    "cn": cn,
                    "center": {
                        "element": center_site.specie.symbol,
                        "x": round(float(center_site.frac_coords[0]), 8),
                        "y": round(float(center_site.frac_coords[1]), 8),
                        "z": round(float(center_site.frac_coords[2]), 8),
                    },
                    "neighbors": neighbor_list,
                }
            )

        return {"environments": environments}
    except Exception as e:
        return {"environments": [], "error": str(e)}


def _get_prototype_doc(structure: Any, result: tuple) -> dict:
    """Generate a prototype document from a structure and generation result.

    Args:
        structure: A pymatgen Structure object.
        result: The result tuple from gen.build_structure().

    Returns:
        Dictionary with topology_theory, prototype_crystallography, and real_compounds keys,
        or an error key on failure.
    """
    SpacegroupAnalyzer = _get_spacegroup_analyzer()
    if not SpacegroupAnalyzer:
        return {"error": "SpacegroupAnalyzer not available"}

    try:
        expanded_modes = result[6]
        expanded_shifts = result[7]
        main_shift_sequence = result[9]
        ref_grid = result[13]

        sga = SpacegroupAnalyzer(structure, symprec=1e-3)
        dataset = sga.get_symmetry_dataset()

        wyckoff_sig = {}
        if dataset and "wyckoffs" in dataset:
            wyckoffs_list = dataset["wyckoffs"]
            for idx, site in enumerate(structure):
                elem = site.specie.symbol
                w_letter = wyckoffs_list[idx]
                if elem not in wyckoff_sig:
                    wyckoff_sig[elem] = set()
                wyckoff_sig[elem].add(w_letter)

        prototype_id = f"{'-'.join(expanded_modes)}-{ref_grid}"
        doc = {
            "topology_theory": {
                "prototype_id": prototype_id,
                "input_main_shifts": main_shift_sequence,
                "expanded_modes": expanded_modes,
                "expanded_shifts": expanded_shifts,
                "reference_grid": ref_grid,
            },
            "prototype_crystallography": {
                "ideal_space_group": sga.get_space_group_symbol(),
                "space_group_number": sga.get_space_group_number(),
                "crystal_system": sga.get_crystal_system(),
                "is_neutral": len(structure.composition.oxi_state_guesses()) > 0,
                "wyckoff_signature": {k: ", ".join(sorted(v)) for k, v in wyckoff_sig.items()},
            },
            "real_compounds": [],
        }

        return doc
    except Exception:
        logger.debug("Prototype doc generation failed")
        return {"error": "Prototype doc generation failed"}


LAYER_TYPE_INFO = [
    {
        "mode": "XO",
        "description": "XO层：X与O交替排列的岩盐型(100)面，X和O各占一半格点",
        "base_length_formula": "d (X-O键长)",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "XO2",
        "description": "XO2层：每个X配位2个O的层状结构，类似CdI2型",
        "base_length_formula": "√3 × d",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "XO3",
        "description": "XO3层：每个X配位3个O的钙钛矿型(111)面，最常见的主层",
        "base_length_formula": "2 × d",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "X",
        "description": "X层：纯X原子层，仅含X阳离子",
        "base_length_formula": "2 × d",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "XBO3",
        "description": "XBO3层：X与BO3基团共面层，X和B各占一个子格点",
        "base_length_formula": "2 × d",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "BO3",
        "description": "BO3层：仅含BO3基团的层，无X阳离子",
        "base_length_formula": "2 × d",
        "is_main_layer": True,
        "is_x_layer": False,
        "is_m_layer": False,
    },
    {
        "mode": "XB3O6",
        "description": "XB3O6层：X与B3O6超结构共面层，使用7倍特殊ABC平移",
        "base_length_formula": "2 × d",
        "is_main_layer": True,
        "is_x_layer": True,
        "is_m_layer": False,
    },
    {
        "mode": "M6",
        "description": "M6层：由M7层删除1/3格点得到的M阳离子层，2/3占位",
        "base_length_formula": "继承相邻主层",
        "is_main_layer": False,
        "is_x_layer": False,
        "is_m_layer": True,
    },
    {
        "mode": "M7",
        "description": "M7层：全占位M阳离子层，格点由相邻主层X原子网格决定",
        "base_length_formula": "继承相邻主层",
        "is_main_layer": False,
        "is_x_layer": False,
        "is_m_layer": True,
    },
    {
        "mode": "T",
        "description": "T层：四面体阳离子层，插入于XO3与XO层之间",
        "base_length_formula": "继承相邻主层",
        "is_main_layer": False,
        "is_x_layer": False,
        "is_m_layer": False,
    },
]


# Rate limiting storage (in-memory, per-process)
_rate_limit_store: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100  # per window


@app.before_request
def check_rate_limit():
    """Simple in-memory rate limiting. Disabled in testing mode."""
    if app.config.get("TESTING"):
        return None
    if not request.path.startswith("/api/"):
        return None
    client_ip = request.remote_addr or "unknown"
    now = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return jsonify({"error": "Rate limit exceeded"}), 429
    _rate_limit_store[client_ip].append(now)
    return None


@app.route("/api/prototypes", methods=["GET"])
def list_prototypes() -> Response:
    """List all prototypes with summary information.

    Returns:
        JSON response with prototypes list and total count.
    """
    build_indexes()
    cached = _api_cache.get("prototypes_list")
    if cached is not None:
        return jsonify(cached)
    results = []
    for proto_id, proto in prototypes_index.items():
        data = proto["data"]
        topo = data.get("topology_theory", {})
        crystal = data.get("prototype_crystallography", {})
        real_compounds = data.get("real_compounds", [])

        raw_count = len(topology_to_materials.get(proto_id, []))
        verified_dir = DATABASE_DIR / f"Verified_Proto_{proto_id}"
        verified_count = 0
        if verified_dir.exists():
            verified_count = len(list(verified_dir.glob("*.cif")))

        results.append(
            {
                "id": proto_id,
                "prototype_id": topo.get("prototype_id", ""),
                "expanded_modes": topo.get("expanded_modes", []),
                "reference_grid": topo.get("reference_grid", ""),
                "ideal_space_group": crystal.get("ideal_space_group", ""),
                "space_group_number": crystal.get("space_group_number", None),
                "crystal_system": crystal.get("crystal_system", ""),
                "is_neutral": crystal.get("is_neutral", None),
                "real_compounds_count": len(real_compounds),
                "raw_materials_count": raw_count,
                "verified_materials_count": verified_count,
            }
        )

    resp = {"prototypes": results, "total": len(results)}
    _api_cache.set("prototypes_list", resp, 300)
    return jsonify(resp)


@app.route("/api/prototypes/<proto_id>", methods=["GET"])
def get_prototype(proto_id: str) -> Response:
    """Get detailed information for a specific prototype.

    Args:
        proto_id: The prototype identifier.

    Returns:
        JSON response with prototype details, raw materials, and verified materials.
    """
    build_indexes()
    if proto_id not in prototypes_index:
        return jsonify({"error": f"Prototype '{proto_id}' not found"}), 404

    proto = prototypes_index[proto_id]
    data = proto["data"]

    mat_ids = topology_to_materials.get(proto_id, [])
    materials = []
    for mid in mat_ids:
        if mid in materials_index:
            m = materials_index[mid]
            materials.append(
                {
                    "material_id": m["material_id"],
                    "formula": m["formula"],
                    "space_group": m["space_group"],
                    "verified": m["verified"],
                }
            )

    verified_dir = DATABASE_DIR / f"Verified_Proto_{proto_id}"
    verified_materials = []
    if verified_dir.exists():
        for cif_file in verified_dir.glob("*.cif"):
            material_id, formula, sg = parse_cif_filename(cif_file.name)
            verified_materials.append(
                {
                    "material_id": material_id,
                    "formula": formula,
                    "space_group": sg,
                    "cif_file": cif_file.name,
                }
            )

    return jsonify(
        {
            "id": proto_id,
            "topology_theory": data.get("topology_theory", {}),
            "prototype_crystallography": data.get("prototype_crystallography", {}),
            "real_compounds": data.get("real_compounds", []),
            "raw_materials": materials,
            "verified_materials": verified_materials,
        }
    )


@app.route("/api/materials", methods=["GET"])
def list_materials() -> Response:
    """List materials with optional filtering and pagination.

    Supports filtering by topology, elements, space_group, and formula.
    Results are paginated.

    Returns:
        JSON response with materials list, total, page, per_page, and total_pages.
    """
    build_indexes()
    topology = request.args.get("topology", "").strip()
    elements_param = request.args.get("elements", "").strip()
    space_group = request.args.get("space_group", "").strip()
    formula = request.args.get("formula", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))

    candidate_ids = set(materials_index.keys())

    if topology:
        topo_ids = set(topology_to_materials.get(topology, []))
        candidate_ids &= topo_ids

    if elements_param:
        requested_elements = [e.strip() for e in elements_param.split(",") if e.strip()]
        for el in requested_elements:
            el_ids = element_to_materials.get(el, set())
            candidate_ids &= el_ids

    if space_group:
        sg_ids = set(space_group_to_materials.get(space_group, []))
        candidate_ids &= sg_ids

    if formula:
        f_ids = set(formula_to_materials.get(formula, []))
        candidate_ids &= f_ids

    sorted_ids = sorted(candidate_ids)
    total = len(sorted_ids)
    start = (page - 1) * per_page
    end = start + per_page
    page_ids = sorted_ids[start:end]

    results = []
    for mid in page_ids:
        m = materials_index[mid]
        results.append(
            {
                "material_id": m["material_id"],
                "formula": m["formula"],
                "space_group": m["space_group"],
                "elements": m["elements"],
                "topology": m["topology"],
                "verified": m["verified"],
            }
        )

    return jsonify(
        {
            "materials": results,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    )


@app.route("/api/materials/<material_id>", methods=["GET"])
def get_material(material_id: str) -> Response:
    """Get detailed information for a specific material.

    Args:
        material_id: The material identifier.

    Returns:
        JSON response with material details and CIF data.
    """
    build_indexes()
    if material_id not in materials_index:
        return jsonify({"error": f"Material '{material_id}' not found"}), 404

    m = materials_index[material_id]
    cif_path = Path(m["cif_path"])
    cif_data = None
    if cif_path.exists():
        cif_data = parse_cif_file(cif_path)

    return jsonify(
        {
            "material_id": m["material_id"],
            "formula": m["formula"],
            "space_group": m["space_group"],
            "elements": m["elements"],
            "topology": m["topology"],
            "verified": m["verified"],
            "directory": m["directory"],
            "cif_file": cif_path.name,
            "cif_data": cif_data,
        }
    )


@app.route("/api/materials/<material_id>/cif", methods=["GET"])
def get_material_cif(material_id: str) -> Response:
    """Download the CIF file for a specific material.

    Args:
        material_id: The material identifier.

    Returns:
        Plain text response with CIF file content.
    """
    build_indexes()
    if material_id not in materials_index:
        return jsonify({"error": f"Material '{material_id}' not found"}), 404

    m = materials_index[material_id]
    cif_path = Path(m["cif_path"])
    if not cif_path.exists():
        return jsonify({"error": "CIF file not found on disk"}), 404

    try:
        cif_text = cif_path.read_text(encoding="utf-8", errors="ignore")
        return Response(
            cif_text,
            mimetype="text/plain",
            headers={"Content-Disposition": f"inline; filename={cif_path.name}"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_structure() -> Response:
    """Generate a layered structure from input parameters.

    Returns:
        JSON response with formula, lattice, atom_sites, topology, space_group, and layer_data.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    try:
        gen, result = _build_structure_from_params(params)
        info = _extract_structure_info(gen, result)
        layer_data = _get_layer_data(gen, result)

        response = {
            "success": True,
            "formula": info["formula"],
            "lattice": info["lattice"],
            "atom_sites": info["atom_sites"],
            "atom_counts": info["atom_counts"],
            "topology": info["topology"],
            "space_group": info["space_group"],
            "layer_data": layer_data,
        }
        return jsonify(response)

    except Exception as e:
        logger.error("generate_structure failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate/layer-data", methods=["POST"])
def generate_layer_data() -> Response:
    """Generate layer data for a layered structure.

    Returns:
        JSON response with layer_data for 2D plotting.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    try:
        gen, result = _build_structure_from_params(params)
        layer_data = _get_layer_data(gen, result)
        return jsonify({"success": True, "layer_data": layer_data})
    except Exception as e:
        logger.error("generate_layer_data failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate/primitive", methods=["POST"])
def generate_primitive() -> Response:
    """Generate primitive cell analysis for a layered structure.

    Returns:
        JSON response with supercell data and primitive cell analysis.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    try:
        gen, result = _build_structure_from_params(params)
        info = _extract_structure_info(gen, result)
        structure = info["structure"]

        supercell_data = {
            "atom_sites": info["atom_sites"],
            "lattice": info["lattice"],
            "formula": info["formula"],
        }

        prim_analysis = _get_primitive_analysis(structure)

        response = {
            "success": True,
            "supercell": supercell_data,
        }
        if "error" in prim_analysis:
            response["primitive"] = None
            response["primitive_error"] = prim_analysis["error"]
        else:
            response["primitive"] = prim_analysis["primitive"]
            response["wyckoff_signature"] = prim_analysis["wyckoff_signature"]

        return jsonify(response)
    except Exception as e:
        logger.error("generate_primitive failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate/coordination", methods=["POST"])
def generate_coordination() -> Response:
    """Generate coordination environment analysis for a layered structure.

    Returns:
        JSON response with coordination environments for X-O pairs.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    cutoff_radius = body.get("cutoff_radius", None)
    if cutoff_radius is not None:
        cutoff_radius = float(cutoff_radius)

    try:
        gen, result = _build_structure_from_params(params)
        info = _extract_structure_info(gen, result)
        structure = info["structure"]

        coord_result = _get_coordination_analysis(
            structure,
            params["x_element"],
            params["o_element"],
            cutoff_radius,
        )

        return jsonify({"success": True, **coord_result})
    except Exception as e:
        logger.error("generate_coordination failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate/prototype", methods=["POST"])
def generate_prototype() -> Response:
    """Generate prototype document for a layered structure.

    Returns:
        JSON response with topology_theory and prototype_crystallography.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    try:
        gen, result = _build_structure_from_params(params)
        info = _extract_structure_info(gen, result)
        structure = info["structure"]

        proto_doc = _get_prototype_doc(structure, result)

        if "error" in proto_doc:
            return jsonify({"success": False, "error": proto_doc["error"]}), 400

        return jsonify({"success": True, **proto_doc})
    except Exception as e:
        logger.error("generate_prototype failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/verify-topology", methods=["POST"])
def verify_topology_endpoint() -> Response:
    """Verify topology by comparing a template CIF against test materials.

    Returns:
        JSON response with match results for each test material.
    """
    verify_topology = _get_verify_topology()
    if not verify_topology:
        return jsonify({"error": "verify_topology module not available"}), 501

    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    template_cif_path = body.get("template_cif_path", "")
    test_material_ids = body.get("test_material_ids", [])

    if not template_cif_path:
        return jsonify({"error": "template_cif_path is required"}), 400
    if not test_material_ids:
        return jsonify({"error": "test_material_ids is required"}), 400

    template_path = Path(template_cif_path)
    if not template_path.exists():
        return jsonify({"error": f"Template CIF file not found: {template_cif_path}"}), 404

    try:
        from pymatgen.core import Structure as PmgStructure
        from pymatgen.analysis.structure_matcher import StructureMatcher

        matcher = StructureMatcher(
            ltol=0.3,
            stol=0.8,
            angle_tol=15.0,
            primitive_cell=True,
            scale=True,
            attempt_supercell=True,
        )

        base_struct = PmgStructure.from_file(str(template_path))
        base_comp = base_struct.composition.fractional_composition
        base_sorted_items = sorted(base_comp.items(), key=lambda x: x[1], reverse=True)
        template_sorted_els = [str(item[0]) for item in base_sorted_items]

        anion = template_sorted_els[0]
        base_struct.remove_species([anion])

        matches = []
        for mid in test_material_ids:
            if mid not in materials_index:
                matches.append(
                    {"material_id": mid, "is_match": False, "error": "material not found"}
                )
                continue

            cif_path = Path(materials_index[mid]["cif_path"])
            if not cif_path.exists():
                matches.append(
                    {"material_id": mid, "is_match": False, "error": "CIF file not found"}
                )
                continue

            try:
                test_struct = PmgStructure.from_file(str(cif_path))
                standardized_test = verify_topology.standardize_and_strip(
                    test_struct, template_sorted_els
                )

                if standardized_test is None:
                    matches.append(
                        {"material_id": mid, "is_match": False, "error": "composition mismatch"}
                    )
                    continue

                is_match = matcher.fit(base_struct, standardized_test)
                matches.append({"material_id": mid, "is_match": is_match})
            except Exception as e:
                matches.append({"material_id": mid, "is_match": False, "error": str(e)})

        return jsonify({"matches": matches})
    except Exception as e:
        logger.error("verify_topology_endpoint failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/generate/full", methods=["POST"])
def generate_full() -> Response:
    """Generate a full analysis including structure, primitive, coordination, and prototype.

    Returns:
        JSON response with all analysis results combined.
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    params, err = _parse_generate_body(body)
    if err:
        return jsonify({"error": err}), 400

    cutoff_radius = body.get("cutoff_radius", None)
    if cutoff_radius is not None:
        cutoff_radius = float(cutoff_radius)

    try:
        gen, result = _build_structure_from_params(params)
        info = _extract_structure_info(gen, result)
        structure = info["structure"]

        layer_data = _get_layer_data(gen, result)

        prim_analysis = _get_primitive_analysis(structure)

        coord_result = _get_coordination_analysis(
            structure,
            params["x_element"],
            params["o_element"],
            cutoff_radius,
        )

        proto_doc = _get_prototype_doc(structure, result)

        response = {
            "success": True,
            "formula": info["formula"],
            "lattice": info["lattice"],
            "atom_sites": info["atom_sites"],
            "atom_counts": info["atom_counts"],
            "topology": info["topology"],
            "space_group": info["space_group"],
            "layer_data": layer_data,
            "coordination": coord_result,
        }

        if "error" in prim_analysis:
            response["primitive"] = None
            response["primitive_error"] = prim_analysis["error"]
        else:
            response["primitive"] = prim_analysis["primitive"]
            response["wyckoff_signature"] = prim_analysis["wyckoff_signature"]

        if "error" in proto_doc:
            response["prototype"] = None
            response["prototype_error"] = proto_doc["error"]
        else:
            response["prototype"] = proto_doc

        return jsonify(response)
    except Exception as e:
        logger.error("generate_full failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route("/api/lattice-types", methods=["GET"])
def get_lattice_types() -> Response:
    """Get available lattice/layer type definitions.

    Returns:
        JSON response with lattice_types list and total count.
    """
    return jsonify({"lattice_types": LAYER_TYPE_INFO, "total": len(LAYER_TYPE_INFO)})


@app.route("/api/classifications", methods=["GET"])
def get_classifications() -> Response:
    """Get materials classified by topology, composition, and space group.

    Returns:
        JSON response with by_topology, by_composition, and by_space_group dicts.
    """
    build_indexes()
    cached = _api_cache.get("classifications")
    if cached is not None:
        return jsonify(cached)
    by_topology = {}
    for proto_id in prototypes_index:
        proto = prototypes_index[proto_id]
        data = proto["data"]
        topo = data.get("topology_theory", {})
        crystal = data.get("prototype_crystallography", {})

        mat_ids = topology_to_materials.get(proto_id, [])
        verified_dir = DATABASE_DIR / f"Verified_Proto_{proto_id}"
        verified_count = len(list(verified_dir.glob("*.cif"))) if verified_dir.exists() else 0

        by_topology[proto_id] = {
            "prototype_id": topo.get("prototype_id", ""),
            "expanded_modes": topo.get("expanded_modes", []),
            "ideal_space_group": crystal.get("ideal_space_group", ""),
            "crystal_system": crystal.get("crystal_system", ""),
            "materials_count": len(mat_ids),
            "verified_count": verified_count,
        }

    by_composition = defaultdict(list)
    for mid, m in materials_index.items():
        by_composition[m["formula"]].append(
            {
                "material_id": m["material_id"],
                "space_group": m["space_group"],
                "topology": m["topology"],
                "verified": m["verified"],
            }
        )

    by_space_group = defaultdict(list)
    for mid, m in materials_index.items():
        by_space_group[m["space_group"]].append(
            {
                "material_id": m["material_id"],
                "formula": m["formula"],
                "topology": m["topology"],
            }
        )

    resp = {
        "by_topology": by_topology,
        "by_composition": dict(by_composition),
        "by_space_group": dict(by_space_group),
    }
    _api_cache.set("classifications", resp, 300)
    return jsonify(resp)


@app.route("/api/search", methods=["GET"])
def search_materials() -> Response:
    """Search materials by query string matching formula, elements, space group, or ID.

    Returns:
        JSON response with query, results list, and total count.
    """
    build_indexes()
    q = request.args.get("q", "").strip()
    # Input validation: limit length and strip dangerous characters
    if len(q) > 200:
        return (
            jsonify({"error": "Query parameter 'q' exceeds maximum length of 200 characters"}),
            400,
        )
    q = re.sub(r"[<>'\";\\]", "", q)
    limit = min(100, max(1, int(request.args.get("limit", 20))))

    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    results = []
    q_lower = q.lower()

    for mid, m in materials_index.items():
        score = 0
        if q_lower == m["formula"].lower():
            score = 100
        elif q_lower in m["formula"].lower():
            score = 80
        elif any(q_lower == el.lower() for el in m["elements"]):
            score = 60
        elif any(q_lower in el.lower() for el in m["elements"]):
            score = 40
        elif q_lower in m["space_group"].lower():
            score = 30
        elif q_lower in mid.lower():
            score = 20

        if score > 0:
            results.append((score, m))

    results.sort(key=lambda x: (-x[0], x[1]["material_id"]))
    results = results[:limit]

    return jsonify(
        {
            "query": q,
            "results": [
                {
                    "material_id": m["material_id"],
                    "formula": m["formula"],
                    "space_group": m["space_group"],
                    "elements": m["elements"],
                    "topology": m["topology"],
                    "verified": m["verified"],
                    "score": score,
                }
                for score, m in results
            ],
            "total": len(results),
        }
    )


@app.route("/api/stats", methods=["GET"])
def get_stats() -> Response:
    """Get database statistics including material counts and distributions.

    Returns:
        JSON response with total_materials, verified/raw counts, topology/space_group/element stats.
    """
    build_indexes()
    cached = _api_cache.get("stats")
    if cached is not None:
        return jsonify(cached)
    total_materials = len(materials_index)
    verified_count = sum(1 for m in materials_index.values() if m["verified"])
    raw_count = total_materials - verified_count

    unique_formulas = len(set(m["formula"] for m in materials_index.values()))
    unique_space_groups = len(set(m["space_group"] for m in materials_index.values()))
    unique_topologies = len(prototypes_index)

    topology_stats = {}
    for proto_id in prototypes_index:
        mat_ids = topology_to_materials.get(proto_id, [])
        verified_dir = DATABASE_DIR / f"Verified_Proto_{proto_id}"
        vc = len(list(verified_dir.glob("*.cif"))) if verified_dir.exists() else 0
        topology_stats[proto_id] = {
            "total": len(mat_ids),
            "verified": vc,
            "raw": len(mat_ids) - vc,
        }

    space_group_stats = {}
    for sg, mids in space_group_to_materials.items():
        if sg:
            space_group_stats[sg] = len(mids)
    space_group_stats = dict(sorted(space_group_stats.items(), key=lambda x: -x[1]))

    element_counts = {}
    for el, mids in element_to_materials.items():
        element_counts[el] = len(mids)

    resp = {
        "total_materials": total_materials,
        "verified_materials": verified_count,
        "raw_materials": raw_count,
        "unique_formulas": unique_formulas,
        "unique_space_groups": unique_space_groups,
        "unique_topologies": unique_topologies,
        "unique_elements": len(all_elements),
        "topology_stats": topology_stats,
        "space_group_stats": space_group_stats,
        "element_counts": dict(sorted(element_counts.items(), key=lambda x: -x[1])),
    }
    _api_cache.set("stats", resp, 120)
    return jsonify(resp)


@app.route("/api/elements", methods=["GET"])
def get_elements() -> Response:
    """Get all elements with their material counts.

    Returns:
        JSON response with elements list (sorted by count) and total count.
    """
    build_indexes()
    cached = _api_cache.get("elements")
    if cached is not None:
        return jsonify(cached)
    element_counts = {}
    for el, mids in element_to_materials.items():
        element_counts[el] = len(mids)

    sorted_elements = sorted(element_counts.items(), key=lambda x: -x[1])
    resp = {
        "elements": [{"symbol": el, "materials_count": count} for el, count in sorted_elements],
        "total": len(sorted_elements),
    }
    _api_cache.set("elements", resp, 300)
    return jsonify(resp)


@app.route("/api/db/status", methods=["GET"])
def db_status() -> Response:
    """Get database status summary.

    Returns:
        JSON response with counts of prototypes, materials, algorithms, tasks, and models.
    """
    try:
        from models import SessionLocal, Prototype, Material, Algorithm, Task, ModelArtifact

        db = SessionLocal()
        try:
            return jsonify(
                {
                    "success": True,
                    "prototypes": db.query(Prototype).count(),
                    "materials": db.query(Material).count(),
                    "algorithms": db.query(Algorithm).filter_by(is_active=True).count(),
                    "tasks_total": db.query(Task).count(),
                    "tasks_pending": db.query(Task).filter_by(status="pending").count(),
                    "tasks_running": db.query(Task).filter_by(status="running").count(),
                    "tasks_completed": db.query(Task).filter_by(status="completed").count(),
                    "tasks_failed": db.query(Task).filter_by(status="failed").count(),
                    "models": db.query(ModelArtifact).filter_by(is_active=True).count(),
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/migrate", methods=["POST"])
def db_migrate() -> Response:
    """Migrate filesystem data into the database.

    Returns:
        JSON response with migration results.
    """
    try:
        from models import SessionLocal, init_db, migrate_from_filesystem

        init_db()
        db = SessionLocal()
        try:
            result = migrate_from_filesystem(db)
            return jsonify({"success": True, **result})
        finally:
            db.close()
    except Exception as e:
        logger.error("db_migrate failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/algorithms", methods=["GET"])
def list_algorithms() -> Response:
    """List all active algorithms.

    Returns:
        JSON response with algorithms list and total count.
    """
    try:
        from models import SessionLocal, Algorithm

        db = SessionLocal()
        try:
            algos = db.query(Algorithm).filter_by(is_active=True).all()
            return jsonify(
                {
                    "success": True,
                    "algorithms": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "description": a.description,
                            "version": a.version,
                            "algorithm_type": a.algorithm_type,
                            "entry_point": a.entry_point,
                            "input_schema": a.input_schema,
                            "output_schema": a.output_schema,
                            "default_config": a.default_config,
                        }
                        for a in algos
                    ],
                    "total": len(algos),
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/algorithms", methods=["POST"])
def register_algorithm() -> Response:
    """Register a new algorithm.

    Returns:
        JSON response with the new algorithm_id.
    """
    try:
        from models import SessionLocal
        from task_worker import register_external_algorithm

        data = request.get_json(force=True)
        algo_id = register_external_algorithm(data)
        return jsonify({"success": True, "algorithm_id": algo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/algorithms/<algo_id>", methods=["DELETE"])
def deactivate_algorithm(algo_id: str) -> Response:
    """Deactivate an algorithm by setting is_active to False.

    Args:
        algo_id: The algorithm identifier.

    Returns:
        JSON response indicating success or failure.
    """
    try:
        from models import SessionLocal, Algorithm

        db = SessionLocal()
        try:
            algo = db.query(Algorithm).filter_by(id=algo_id).first()
            if not algo:
                return jsonify({"success": False, "error": "Algorithm not found"}), 404
            algo.is_active = False
            db.commit()
            return jsonify({"success": True})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/tasks", methods=["POST"])
def create_task() -> Response:
    """Create a new task for an algorithm.

    Returns:
        JSON response with the new task_id.
    """
    try:
        from task_worker import submit_task

        data = request.get_json(force=True)
        algorithm_id = data.get("algorithm_id")
        input_data = data.get("input_data", {})
        if not algorithm_id:
            return jsonify({"success": False, "error": "algorithm_id is required"}), 400
        task_id = submit_task(algorithm_id, input_data)
        return jsonify({"success": True, "task_id": task_id})
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str) -> Response:
    """Get the status of a specific task.

    Args:
        task_id: The task identifier.

    Returns:
        JSON response with task status details.
    """
    try:
        from task_worker import get_task_status

        result = get_task_status(task_id)
        if "error" in result and result.get("error") == "Task not found":
            return jsonify({"success": False, "error": "Task not found"}), 404
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/tasks", methods=["GET"])
def list_tasks() -> Response:
    """List tasks with optional filtering by status and algorithm_id.

    Returns:
        JSON response with tasks list and total count.
    """
    try:
        from models import SessionLocal, Task, Algorithm

        db = SessionLocal()
        try:
            status_filter = request.args.get("status")
            algo_filter = request.args.get("algorithm_id")
            limit = min(int(request.args.get("limit", 50)), 200)

            query = db.query(Task)
            if status_filter:
                query = query.filter_by(status=status_filter)
            if algo_filter:
                query = query.filter_by(algorithm_id=algo_filter)
            query = query.order_by(Task.created_at.desc()).limit(limit)

            tasks = query.all()
            return jsonify(
                {
                    "success": True,
                    "tasks": [
                        {
                            "task_id": t.id,
                            "algorithm_id": t.algorithm_id,
                            "status": t.status,
                            "progress": t.progress,
                            "progress_message": t.progress_message,
                            "error_message": t.error_message,
                            "created_at": t.created_at.isoformat() if t.created_at else None,
                            "started_at": t.started_at.isoformat() if t.started_at else None,
                            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                        }
                        for t in tasks
                    ],
                    "total": len(tasks),
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/models", methods=["GET"])
def list_models_db() -> Response:
    """List all active model artifacts.

    Returns:
        JSON response with models list and total count.
    """
    try:
        from models import SessionLocal, ModelArtifact

        db = SessionLocal()
        try:
            models = db.query(ModelArtifact).filter_by(is_active=True).all()
            return jsonify(
                {
                    "success": True,
                    "models": [
                        {
                            "id": m.id,
                            "algorithm_id": m.algorithm_id,
                            "name": m.name,
                            "model_type": m.model_type,
                            "metrics": m.metrics,
                            "feature_keys": m.feature_keys,
                            "created_at": m.created_at.isoformat() if m.created_at else None,
                        }
                        for m in models
                    ],
                    "total": len(models),
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/prototypes", methods=["GET"])
def db_list_prototypes() -> Response:
    """List prototypes from the database with optional crystal_system filter.

    Returns:
        JSON response with prototypes list and total count.
    """
    try:
        from models import SessionLocal, Prototype

        db = SessionLocal()
        try:
            query = db.query(Prototype)
            crystal_system = request.args.get("crystal_system")
            if crystal_system:
                query = query.filter_by(crystal_system=crystal_system)
            prototypes = query.all()
            return jsonify(
                {
                    "success": True,
                    "prototypes": [
                        {
                            "id": p.id,
                            "prototype_id": p.prototype_id,
                            "expanded_modes": p.expanded_modes,
                            "ideal_space_group": p.ideal_space_group,
                            "space_group_number": p.space_group_number,
                            "crystal_system": p.crystal_system,
                            "is_neutral": p.is_neutral,
                            "created_at": p.created_at.isoformat() if p.created_at else None,
                            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                        }
                        for p in prototypes
                    ],
                    "total": len(prototypes),
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/prototypes/<prototype_id>", methods=["GET"])
def db_get_prototype(prototype_id: str) -> Response:
    """Get detailed information for a specific database prototype.

    Args:
        prototype_id: The prototype identifier.

    Returns:
        JSON response with prototype details and materials count.
    """
    try:
        from models import SessionLocal, Prototype, Material

        db = SessionLocal()
        try:
            proto = db.query(Prototype).filter_by(id=prototype_id).first()
            if not proto:
                return jsonify({"success": False, "error": "Prototype not found"}), 404
            materials_count = db.query(Material).filter_by(topology_id=prototype_id).count()
            return jsonify(
                {
                    "success": True,
                    "prototype": {
                        "id": proto.id,
                        "prototype_id": proto.prototype_id,
                        "expanded_modes": proto.expanded_modes,
                        "reference_grid": proto.reference_grid,
                        "ideal_space_group": proto.ideal_space_group,
                        "space_group_number": proto.space_group_number,
                        "crystal_system": proto.crystal_system,
                        "is_neutral": proto.is_neutral,
                        "topology_data": proto.topology_data,
                        "materials_count": materials_count,
                        "created_at": proto.created_at.isoformat() if proto.created_at else None,
                        "updated_at": proto.updated_at.isoformat() if proto.updated_at else None,
                    },
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/materials", methods=["GET"])
def db_list_materials() -> Response:
    """List materials from the database with filtering and pagination.

    Supports filtering by topology_id, space_group, is_verified, formula, and source.
    Results are paginated and sortable.

    Returns:
        JSON response with materials list, total, page, page_size, and total_pages.
    """
    try:
        from models import SessionLocal, Material

        db = SessionLocal()
        try:
            query = db.query(Material)
            topology_id = request.args.get("topology_id")
            if topology_id:
                query = query.filter_by(topology_id=topology_id)
            space_group = request.args.get("space_group")
            if space_group:
                query = query.filter_by(space_group=space_group)
            is_verified = request.args.get("is_verified")
            if is_verified is not None:
                query = query.filter_by(is_verified=is_verified.lower() == "true")
            formula = request.args.get("formula")
            if formula:
                formula = formula.strip()[:100]  # Limit length
                formula = re.sub(r"[;%\\_]", "", formula)  # Remove dangerous chars for LIKE
                query = query.filter(Material.formula.like(f"%{formula}%"))
            source = request.args.get("source")
            if source:
                query = query.filter_by(source=source)

            page = max(1, int(request.args.get("page", 1)))
            page_size = min(100, int(request.args.get("page_size", 50)))
            offset = (page - 1) * page_size

            sort_by = request.args.get("sort_by", "created_at")
            sort_dir = request.args.get("sort_dir", "desc")
            sort_col_map = {
                "formula": Material.formula,
                "topology_id": Material.topology_id,
                "n_atoms": Material.n_atoms,
                "created_at": Material.created_at,
            }
            sort_col = sort_col_map.get(sort_by, Material.created_at)
            if sort_dir == "desc":
                query = query.order_by(sort_col.desc())
            else:
                query = query.order_by(sort_col.asc())

            total = query.count()
            materials = query.offset(offset).limit(page_size).all()
            return jsonify(
                {
                    "success": True,
                    "materials": [
                        {
                            "id": m.id,
                            "formula": m.formula,
                            "space_group": m.space_group,
                            "topology_id": m.topology_id,
                            "elements": m.elements,
                            "lattice_a": m.lattice_a,
                            "lattice_b": m.lattice_b,
                            "lattice_c": m.lattice_c,
                            "lattice_alpha": m.lattice_alpha,
                            "lattice_beta": m.lattice_beta,
                            "lattice_gamma": m.lattice_gamma,
                            "n_atoms": m.n_atoms,
                            "is_verified": m.is_verified,
                            "source": m.source,
                            "cif_path": m.cif_path,
                            "created_at": m.created_at.isoformat() if m.created_at else None,
                            "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                        }
                        for m in materials
                    ],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/materials/<material_id>", methods=["GET"])
def db_get_material(material_id: str) -> Response:
    """Get detailed information for a specific database material.

    Args:
        material_id: The material identifier.

    Returns:
        JSON response with material details including CIF content and metadata.
    """
    try:
        from models import SessionLocal, Material

        db = SessionLocal()
        try:
            mat = db.query(Material).filter_by(id=material_id).first()
            if not mat:
                return jsonify({"success": False, "error": "Material not found"}), 404
            return jsonify(
                {
                    "success": True,
                    "material": {
                        "id": mat.id,
                        "formula": mat.formula,
                        "space_group": mat.space_group,
                        "topology_id": mat.topology_id,
                        "elements": mat.elements,
                        "lattice_a": mat.lattice_a,
                        "lattice_b": mat.lattice_b,
                        "lattice_c": mat.lattice_c,
                        "lattice_alpha": mat.lattice_alpha,
                        "lattice_beta": mat.lattice_beta,
                        "lattice_gamma": mat.lattice_gamma,
                        "n_atoms": mat.n_atoms,
                        "is_verified": mat.is_verified,
                        "source": mat.source,
                        "cif_path": mat.cif_path,
                        "cif_content": mat.cif_content,
                        "metadata_json": mat.metadata_json,
                        "created_at": mat.created_at.isoformat() if mat.created_at else None,
                        "updated_at": mat.updated_at.isoformat() if mat.updated_at else None,
                    },
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/materials/<material_id>", methods=["DELETE"])
def db_delete_material(material_id: str) -> Response:
    """Delete a material from the database.

    Args:
        material_id: The material identifier.

    Returns:
        JSON response indicating success or failure.
    """
    try:
        from models import SessionLocal, Material

        db = SessionLocal()
        try:
            mat = db.query(Material).filter_by(id=material_id).first()
            if not mat:
                return jsonify({"success": False, "error": "Material not found"}), 404
            db.delete(mat)
            db.commit()
            return jsonify({"success": True, "message": f"Material {material_id} deleted"})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/materials/batch", methods=["POST"])
def db_batch_update_materials() -> Response:
    """Batch update materials (verify, unverify, or update fields).

    Returns:
        JSON response with the number of updated records.
    """
    try:
        from models import SessionLocal, Material

        db = SessionLocal()
        try:
            data = request.get_json(force=True)
            updates = data.get("updates", [])
            action = data.get("action", "verify")
            updated = 0
            for update in updates:
                mat_id = update.get("material_id")
                mat = db.query(Material).filter_by(id=mat_id).first()
                if not mat:
                    continue
                if action == "verify":
                    mat.is_verified = True
                elif action == "unverify":
                    mat.is_verified = False
                elif action == "update":
                    if "topology_id" in update:
                        mat.topology_id = update["topology_id"]
                    if "formula" in update:
                        mat.formula = update["formula"]
                    if "space_group" in update:
                        mat.space_group = update["space_group"]
                    if "is_verified" in update:
                        mat.is_verified = update["is_verified"]
                    if "metadata_json" in update:
                        mat.metadata_json = update["metadata_json"]
                updated += 1
            db.commit()
            return jsonify({"success": True, "updated": updated})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/stats", methods=["GET"])
def db_detailed_stats() -> Response:
    """Get detailed database statistics.

    Returns:
        JSON response with materials, prototypes, topology, space group, tasks, algorithms, and models stats.
    """
    try:
        from models import SessionLocal, Prototype, Material, Algorithm, Task, ModelArtifact

        db = SessionLocal()
        try:
            total_prototypes = db.query(Prototype).count()
            total_materials = db.query(Material).count()
            verified_materials = db.query(Material).filter_by(is_verified=True).count()
            raw_materials = total_materials - verified_materials

            topology_counts = {}
            for (topo_id,) in db.query(Material.topology_id).distinct().all():
                if topo_id:
                    topology_counts[topo_id] = (
                        db.query(Material).filter_by(topology_id=topo_id).count()
                    )

            sg_counts = {}
            for (sg,) in db.query(Material.space_group).distinct().all():
                if sg:
                    sg_counts[sg] = db.query(Material).filter_by(space_group=sg).count()

            pending = db.query(Task).filter_by(status="pending").count()
            running = db.query(Task).filter_by(status="running").count()
            completed = db.query(Task).filter_by(status="completed").count()
            failed = db.query(Task).filter_by(status="failed").count()
            active_algos = db.query(Algorithm).filter_by(is_active=True).count()
            total_models = db.query(ModelArtifact).filter_by(is_active=True).count()

            return jsonify(
                {
                    "success": True,
                    "materials": {
                        "total": total_materials,
                        "verified": verified_materials,
                        "raw": raw_materials,
                    },
                    "prototypes": total_prototypes,
                    "topology_counts": topology_counts,
                    "space_group_counts": sg_counts,
                    "tasks": {
                        "pending": pending,
                        "running": running,
                        "completed": completed,
                        "failed": failed,
                        "total": pending + running + completed + failed,
                    },
                    "algorithms": active_algos,
                    "models": total_models,
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins", methods=["GET"])
def list_plugins() -> Response:
    """List all active plugins (algorithms).

    Returns:
        JSON response with plugins list.
    """
    try:
        from models import SessionLocal, Algorithm

        db = SessionLocal()
        try:
            algos = db.query(Algorithm).filter(Algorithm.is_active == True).all()
            return jsonify(
                {
                    "success": True,
                    "plugins": [
                        {
                            "id": a.id,
                            "name": a.name,
                            "description": a.description,
                            "algorithm_type": a.algorithm_type,
                            "entry_point": a.entry_point,
                            "input_schema": a.input_schema,
                            "output_schema": a.output_schema,
                            "default_config": a.default_config,
                            "version": a.version,
                        }
                        for a in algos
                    ],
                }
            )
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins", methods=["POST"])
def register_plugin() -> Response:
    """Register a new plugin (algorithm).

    Returns:
        JSON response with the new algorithm_id.
    """
    try:
        from task_worker import register_external_algorithm

        data = request.get_json(force=True)
        required = ["id", "name", "entry_point"]
        for r in required:
            if r not in data:
                return jsonify({"success": False, "error": f"Missing required field: {r}"}), 400
        algo_id = register_external_algorithm(data)
        return jsonify({"success": True, "algorithm_id": algo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins/<algo_id>", methods=["DELETE"])
def deactivate_plugin(algo_id: str) -> Response:
    """Deactivate a plugin by setting is_active to False.

    Args:
        algo_id: The plugin/algorithm identifier.

    Returns:
        JSON response indicating success or failure.
    """
    try:
        from models import SessionLocal, Algorithm

        db = SessionLocal()
        try:
            algo = db.query(Algorithm).filter_by(id=algo_id).first()
            if not algo:
                return jsonify({"success": False, "error": "Plugin not found"}), 404
            algo.is_active = False
            db.commit()
            return jsonify({"success": True})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins/<algo_id>/execute", methods=["POST"])
def execute_plugin(algo_id: str) -> Response:
    """Execute a plugin by submitting a task.

    Args:
        algo_id: The plugin/algorithm identifier.

    Returns:
        JSON response with the task_id.
    """
    try:
        from task_worker import submit_task

        data = request.get_json(force=True) or {}
        input_data = data.get("input_data", data)
        task_id = submit_task(algo_id, input_data)
        return jsonify({"success": True, "task_id": task_id})
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins/discover", methods=["POST"])
def discover_plugins_route() -> Response:
    """Discover available plugins.

    Returns:
        JSON response with discovered plugins list and count.
    """
    try:
        from cgcpt_plugin import discover_plugins

        plugin_dir = request.get_json(force=True).get("plugin_dir") if request.is_json else None
        discovered = discover_plugins(plugin_dir)
        return jsonify({"success": True, "discovered": discovered, "count": len(discovered)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins/discovered", methods=["GET"])
def list_discovered_plugins() -> Response:
    """List all discovered plugins from the registry.

    Returns:
        JSON response with plugins list and count.
    """
    try:
        from cgcpt_plugin import get_plugin_registry

        registry = get_plugin_registry()
        return jsonify(
            {
                "success": True,
                "plugins": [info["definition"] for info in registry.values()],
                "count": len(registry),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/plugins/register-all", methods=["POST"])
def register_all_discovered() -> Response:
    """Register all discovered plugins.

    Returns:
        JSON response with registered plugin IDs and count.
    """
    try:
        from cgcpt_plugin import discover_plugins, get_plugin_registry
        from task_worker import register_external_algorithm

        discover_plugins()
        registry = get_plugin_registry()
        registered = []
        for algo_id, info in registry.items():
            try:
                register_external_algorithm(info["definition"])
                registered.append(algo_id)
            except Exception as e:
                registered.append(f"{algo_id}: ERROR - {e}")
        return jsonify({"success": True, "registered": registered, "count": len(registered)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ADMIN_USER and ADMIN_PASS are now imported from config module


def check_auth(request: Any) -> bool:
    """Check if the request has valid admin authentication.

    Supports Bearer token (base64-encoded user:password).

    Args:
        request: The Flask request object.

    Returns:
        True if authentication succeeds, False otherwise.
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            import base64

            decoded = base64.b64decode(token).decode("utf-8")
            if ":" in decoded:
                user, pwd = decoded.split(":", 1)
                return user == ADMIN_USER and pwd == ADMIN_PASS
        except Exception:
            pass
    return False


@app.route("/api/auth/login", methods=["POST"])
def auth_login() -> Response:
    """Authenticate and return a Bearer token.

    Returns:
        JSON response with success status and token.
    """
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")
    if username == ADMIN_USER and password == ADMIN_PASS:
        import base64

        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "error": "用户名或密码错误"}), 401


@app.route("/api/auth/check", methods=["GET"])
def auth_check() -> Response:
    """Check if the current request is authenticated.

    Returns:
        JSON response with authentication status.
    """
    if check_auth(request):
        return jsonify({"success": True, "user": ADMIN_USER})
    return jsonify({"success": False, "error": "未授权"}), 401


@app.route("/api/models/upload", methods=["POST"])
def upload_model() -> Response:
    """Upload a model artifact file.

    Requires admin authentication. Validates the model file and stores metadata in the database.

    Returns:
        JSON response with model_id, model_class, file_path, and metrics.
    """
    if not check_auth(request):
        return jsonify({"success": False, "error": "需要管理员权限"}), 401
    try:
        import joblib
        import uuid as _uuid
        from models import SessionLocal, ModelArtifact

        if "file" not in request.files:
            return jsonify({"success": False, "error": "未找到上传文件"}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"success": False, "error": "文件名为空"}), 400

        model_name = request.form.get("name", f.filename)
        model_type = request.form.get("model_type", "decision_tree")
        description = request.form.get("description", "")

        models_dir = Path("/opt/CGCPT/models")
        models_dir.mkdir(exist_ok=True)

        model_id = request.form.get("model_id", f"uploaded_{_uuid.uuid4().hex[:8]}")
        safe_name = re.sub(r"[^\w\-.]", "_", model_id)
        save_path = models_dir / f"dt_{safe_name}.pkl"

        f.save(str(save_path))

        try:
            model = joblib.load(save_path)
            model_class = type(model).__name__
        except Exception as e:
            os.remove(save_path)
            return jsonify({"success": False, "error": f"模型文件无效: {e}"}), 400

        metrics = {}
        if hasattr(model, "n_features_in_"):
            metrics["n_features"] = int(model.n_features_in_)
        if hasattr(model, "tree_"):
            metrics["n_nodes"] = int(model.tree_.node_count)
            metrics["max_depth_actual"] = int(model.tree_.max_depth)
        if hasattr(model, "classes_"):
            metrics["n_classes"] = len(model.classes_)
            metrics["classes"] = [str(c) for c in model.classes_]

        db = SessionLocal()
        try:
            existing = db.query(ModelArtifact).filter_by(id=model_id).first()
            if existing:
                existing.name = model_name
                existing.model_type = model_type
                existing.metrics = metrics
                existing.file_path = str(save_path)
                existing.is_active = True
                db.commit()
            else:
                artifact = ModelArtifact(
                    id=model_id,
                    algorithm_id="stacking_predict",
                    task_id="",
                    name=model_name,
                    model_type=model_type,
                    metrics=metrics,
                    file_path=str(save_path),
                    is_active=True,
                )
                db.add(artifact)
                db.commit()
        finally:
            db.close()

        return jsonify(
            {
                "success": True,
                "model_id": model_id,
                "model_class": model_class,
                "file_path": str(save_path),
                "metrics": metrics,
            }
        )
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/models/<model_id>", methods=["DELETE"])
def delete_model(model_id: str) -> Response:
    """Delete a model artifact and its file.

    Args:
        model_id: The model identifier.

    Returns:
        JSON response indicating success or failure.
    """
    if not check_auth(request):
        return jsonify({"success": False, "error": "需要管理员权限"}), 401
    try:
        from models import SessionLocal, ModelArtifact

        db = SessionLocal()
        try:
            artifact = db.query(ModelArtifact).filter_by(id=model_id).first()
            if not artifact:
                return jsonify({"success": False, "error": "模型不存在"}), 404
            if artifact.file_path and os.path.exists(artifact.file_path):
                os.remove(artifact.file_path)
            db.delete(artifact)
            db.commit()
            return jsonify({"success": True})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/models/<model_id>/activate", methods=["POST"])
def activate_model(model_id: str) -> Response:
    """Activate a model artifact, deactivating others of the same type.

    Args:
        model_id: The model identifier.

    Returns:
        JSON response indicating success or failure.
    """
    if not check_auth(request):
        return jsonify({"success": False, "error": "需要管理员权限"}), 401
    try:
        from models import SessionLocal, ModelArtifact

        db = SessionLocal()
        try:
            artifact = db.query(ModelArtifact).filter_by(id=model_id).first()
            if not artifact:
                return jsonify({"success": False, "error": "模型不存在"}), 404
            same_type = (
                db.query(ModelArtifact)
                .filter_by(model_type=artifact.model_type, is_active=True)
                .all()
            )
            for a in same_type:
                a.is_active = False
            artifact.is_active = True
            db.commit()
            return jsonify({"success": True})
        finally:
            db.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.errorhandler(404)
def not_found(e: Any) -> Response:
    """Handle 404 Not Found errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e: Any) -> Response:
    """Handle 405 Method Not Allowed errors."""
    return jsonify({"error": "Method not allowed"}), 405


@app.route("/api/stacking/scan", methods=["POST"])
def stacking_scan() -> Response:
    """Scan database CIFs for stacking analysis.

    Returns:
        JSON response with scanned samples and count.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        samples = sa.scan_database_cifs()
        return jsonify(
            {
                "success": True,
                "n_samples": len(samples),
                "samples": [
                    {
                        "filename": s["filename"],
                        "topology": s["topology"],
                        "formula": s["formula"],
                        "source": s["source"],
                        "n_features": len(s["features"]),
                    }
                    for s in samples
                ],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/train", methods=["POST"])
def stacking_train() -> Response:
    """Train a stacking prediction model.

    Returns:
        JSON response with training results.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        body = request.get_json(force=True) if request.is_json else {}
        test_ratio = float(body.get("test_ratio", 0.2))
        max_depth = body.get("max_depth", None)
        random_state = int(body.get("random_state", 42))
        model_type = body.get("model_type", "auto")
        n_iterations = int(body.get("n_iterations", 5))
        cv_folds = int(body.get("cv_folds", 5))

        max_sequences = int(body.get("max_sequences", 500))

        test_ratio = max(0.05, min(0.5, test_ratio))

        result = sa.train_decision_tree(
            test_ratio=test_ratio,
            max_depth=max_depth,
            random_state=random_state,
            cv_folds=cv_folds,
            max_sequences=max_sequences,
        )

        if result.get("success") and result.get("model_id"):
            sa.save_model_meta(result["model_id"], result)

        return jsonify(result)
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/train/stream", methods=["POST"])
def stacking_train_stream() -> Response:
    """Train a stacking model with SSE progress events.

    Returns:
        Server-Sent Events stream with progress, result, and error events.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500

    body = request.get_json(force=True) if request.is_json else {}
    test_ratio = float(body.get("test_ratio", 0.2))
    max_depth = body.get("max_depth", None)
    random_state = int(body.get("random_state", 42))
    model_type = body.get("model_type", "auto")
    n_iterations = int(body.get("n_iterations", 5))
    cv_folds = int(body.get("cv_folds", 5))
    max_sequences = int(body.get("max_sequences", 500))
    test_ratio = max(0.05, min(0.5, test_ratio))

    ev_queue = queue_mod.Queue()

    def on_progress(info: dict) -> None:
        ev_queue.put(("progress", info))

    def run_training() -> None:
        try:
            result = sa.train_decision_tree(
                test_ratio=test_ratio,
                max_depth=max_depth,
                random_state=random_state,
                cv_folds=cv_folds,
                max_sequences=max_sequences,
                progress_callback=on_progress,
            )
            if result.get("success") and result.get("model_id"):
                sa.save_model_meta(result["model_id"], result)
            ev_queue.put(("result", result))
        except Exception as e:
            logger.error("Exception occurred", exc_info=True)
            ev_queue.put(("error", str(e)))
        finally:
            ev_queue.put(None)

    t = threading.Thread(target=run_training, daemon=True)
    t.start()

    def generate():
        while True:
            item = ev_queue.get(timeout=300)
            if item is None:
                break
            kind, data = item
            if kind == "progress":
                yield f"event: progress\ndata: {json.dumps(_sanitize_json_value(data), ensure_ascii=False, allow_nan=False)}\n\n"
            elif kind == "result":
                yield f"event: result\ndata: {json.dumps(_sanitize_json_value(data), ensure_ascii=False, allow_nan=False)}\n\n"
            elif kind == "error":
                yield f"event: error\ndata: {json.dumps(_sanitize_json_value({'error': data}), ensure_ascii=False, allow_nan=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/stacking/predict", methods=["POST"])
def stacking_predict() -> Response:
    """Predict stacking sequence using a trained model.

    Returns:
        JSON response with prediction results.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        body = request.get_json(force=True) if request.is_json else {}
        model_id = body.get("model_id", "")
        layer_modes = body.get("layer_modes", [])
        stack_sequence = body.get("stack_sequence", "ABC")
        cif_text = body.get("cif_text", "")

        if not model_id:
            return jsonify({"success": False, "error": "请指定模型ID"})

        if layer_modes:
            if isinstance(layer_modes, str):
                layer_modes = [m.strip() for m in layer_modes.split(",") if m.strip()]
            result = sa.predict_stacking(model_id, layer_modes, stack_sequence)
        elif cif_text:
            cif_data = sa.parse_cif_text(cif_text)
            if not cif_data:
                return jsonify({"success": False, "error": "CIF文件解析失败"})
            result = sa.predict_stacking_from_cif(model_id, cif_data)
        else:
            return jsonify({"success": False, "error": "请提供layer_modes或cif_text"})

        return jsonify(_sanitize_json_value(result))
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/upload", methods=["POST"])
def stacking_upload() -> Response:
    """Upload a CIF file for stacking analysis.

    Returns:
        JSON response with parsed CIF data, features, and layer analysis.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "未找到上传文件"})
        f = request.files["file"]
        if not f.filename.endswith(".cif"):
            return jsonify({"success": False, "error": "仅支持CIF文件"})

        cif_text = f.read().decode("utf-8", errors="ignore")
        cif_data = sa.parse_cif_text(cif_text)
        if not cif_data:
            return jsonify({"success": False, "error": "CIF文件解析失败"})

        features = sa.extract_features(cif_data)
        layer_features = sa.extract_layer_features(cif_data)

        return jsonify(
            _sanitize_json_value(
                {
                    "success": True,
                    "filename": f.filename,
                    "formula": cif_data.get("formula", ""),
                    "space_group": cif_data.get("space_group", ""),
                    "lattice": cif_data.get("lattice", {}),
                    "n_atoms": len(cif_data.get("atom_sites", [])),
                    "features": features,
                    "layer_analysis": layer_features,
                    "cif_text": cif_text,
                }
            )
        )
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/models", methods=["GET"])
def stacking_models() -> Response:
    """List available stacking models.

    Returns:
        JSON response with models list.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        models = sa.list_models()
        return jsonify({"success": True, "models": models})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/models/<model_id>", methods=["DELETE"])
def stacking_delete_model(model_id: str) -> Response:
    """Delete a stacking model.

    Args:
        model_id: The model identifier.

    Returns:
        JSON response indicating success or failure.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        deleted = sa.delete_model(model_id)
        return jsonify({"success": deleted, "model_id": model_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/self_improve", methods=["POST"])
def stacking_self_improve() -> Response:
    """Run self-improvement iterations on stacking models.

    Returns:
        JSON response with improvement results.
    """
    try:
        import self_improver as si
    except ImportError:
        return jsonify({"success": False, "error": "self_improver模块未找到"}), 500
    try:
        body = request.get_json(force=True) if request.is_json else {}
        max_iterations = int(body.get("max_iterations", 3))
        max_sequences = int(body.get("max_sequences", 300))
        cv_folds = int(body.get("cv_folds", 3))
        use_feature_engineering = body.get("use_feature_engineering", True)
        use_hard_mining = body.get("use_hard_mining", True)
        use_ensemble = body.get("use_ensemble", True)
        use_bayesian = body.get("use_bayesian", True)

        result = si.self_improve_iteration(
            max_iterations=max_iterations,
            max_sequences=max_sequences,
            cv_folds=cv_folds,
            use_feature_engineering=use_feature_engineering,
            use_hard_mining=use_hard_mining,
            use_ensemble=use_ensemble,
            use_bayesian=use_bayesian,
        )
        return jsonify(_sanitize_json_value(result))
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/improvement_history", methods=["GET"])
def stacking_improvement_history() -> Response:
    """Get the improvement trajectory history.

    Returns:
        JSON response with trajectory data and iteration count.
    """
    try:
        import self_improver as si

        trajectory = si.get_improvement_trajectory()
        return jsonify({"success": True, "trajectory": trajectory, "n_iterations": len(trajectory)})
    except ImportError:
        return jsonify({"success": False, "error": "self_improver模块未找到"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/error_analysis/<model_id>", methods=["GET"])
def stacking_error_analysis(model_id: str) -> Response:
    """Analyze prediction errors for a specific model.

    Args:
        model_id: The model identifier.

    Returns:
        JSON response with error analysis results.
    """
    try:
        import self_improver as si

        result = si.analyze_errors(model_id)
        return jsonify(_sanitize_json_value(result))
    except ImportError:
        return jsonify({"success": False, "error": "self_improver模块未找到"}), 500
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/analyze", methods=["POST"])
def stacking_analyze() -> Response:
    """Analyze a CIF text for stacking features.

    Returns:
        JSON response with formula, space_group, lattice, features, and layer_analysis.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        body = request.get_json(force=True)
        cif_text = body.get("cif_text", "")

        if not cif_text:
            return jsonify({"success": False, "error": "请提供CIF文本"})

        cif_data = sa.parse_cif_text(cif_text)
        if not cif_data:
            return jsonify({"success": False, "error": "CIF文件解析失败"})

        features = sa.extract_features(cif_data)
        layer_features = sa.extract_layer_features(cif_data)

        return jsonify(
            _sanitize_json_value(
                {
                    "success": True,
                    "formula": cif_data.get("formula", ""),
                    "space_group": cif_data.get("space_group", ""),
                    "lattice": cif_data.get("lattice", {}),
                    "n_atoms": len(cif_data.get("atom_sites", [])),
                    "features": features,
                    "layer_analysis": layer_features,
                }
            )
        )
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/stacking/batch_predict", methods=["POST"])
def stacking_batch_predict() -> Response:
    """Batch predict stacking sequences using a trained model.

    Returns:
        JSON response with per-sequence predictions and overall accuracy.
    """
    sa = _get_stacking_analyzer()
    if not sa:
        return jsonify({"success": False, "error": "stacking_analyzer模块未加载"}), 500
    try:
        body = request.get_json(force=True) if request.is_json else {}
        model_id = body.get("model_id", "")
        layer_sequences = body.get("layer_sequences", [])
        stack_sequence = body.get("stack_sequence", "ABC")

        if not model_id:
            return jsonify({"success": False, "error": "请指定模型ID"})

        model_path = sa.MODEL_DIR / f"{model_id}.pkl"
        if not model_path.exists():
            return jsonify({"success": False, "error": f"模型不存在: {model_id}"})

        if not layer_sequences:
            layer_sequences = [
                ["XO3", "M7", "XO3", "M7", "XO3", "XO3"],
                ["XO3", "M7", "XO3", "M7", "XO3"],
                ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
                ["XO3", "XO3", "XO3"],
                ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
                ["XBO3", "M7", "XBO3", "M7", "XBO3"],
                ["XB3O6", "M7", "XB3O6"],
                ["XO2", "M7", "XO2", "M7", "XO2"],
                ["XO3", "M6", "XO3", "M6", "XO3"],
                ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
            ]

        results = []
        total_correct = 0
        total_layers = 0

        for seq in layer_sequences:
            if isinstance(seq, str):
                seq = [m.strip() for m in seq.split(",") if m.strip()]
            pred = sa.predict_stacking(model_id, seq, stack_sequence)
            if pred.get("success"):
                total_correct += pred.get("n_correct", 0)
                total_layers += pred.get("n_total", 0)
                results.append(
                    {
                        "layer_modes": seq,
                        "expanded_modes": pred.get("expanded_modes", []),
                        "accuracy": pred.get("accuracy", 0),
                        "n_correct": pred.get("n_correct", 0),
                        "n_total": pred.get("n_total", 0),
                        "predictions": pred.get("predictions", []),
                    }
                )
            else:
                results.append(
                    {
                        "layer_modes": seq,
                        "error": pred.get("error", "预测失败"),
                    }
                )

        overall_accuracy = round(total_correct / total_layers, 4) if total_layers > 0 else 0

        return jsonify(
            _sanitize_json_value(
                {
                    "success": True,
                    "model_id": model_id,
                    "n_sequences": len(results),
                    "overall_accuracy": overall_accuracy,
                    "total_correct": total_correct,
                    "total_layers": total_layers,
                    "results": results,
                }
            )
        )
    except Exception as e:
        logger.error("Exception occurred", exc_info=True)
        return jsonify({"success": False, "error": str(e)})


def _auto_classify_topology(atom_sites: list[dict], lattice: dict) -> tuple[Optional[str], float]:
    """Automatically classify the topology of a structure based on atom sites and lattice.

    Uses heuristics based on X/O ratios, number of distinct layers, and lattice parameters
    to suggest a likely topology.

    Args:
        atom_sites: List of atom site dictionaries with element and fractional coordinates.
        lattice: Dictionary with lattice parameters (a, b, c, alpha, beta, gamma).

    Returns:
        A tuple of (suggested_topology_string, confidence_score).
    """
    if not atom_sites or len(atom_sites) < 3:
        return None, 0.0

    elements = [a["element"] for a in atom_sites]
    unique_elements = list(set(elements))
    element_counts = {}
    for el in elements:
        element_counts[el] = element_counts.get(el, 0) + 1
    total_atoms = len(atom_sites)

    z_coords = sorted([a["z"] for a in atom_sites])
    n_distinct_layers = len(set(round(z, 2) for z in z_coords))

    c_ratio = (
        lattice["c"] / (lattice["a"] + lattice["b"]) / 2
        if (lattice["a"] + lattice["b"]) > 0
        else 1.0
    )
    has_o = "O" in element_counts
    x_candidates = [
        el
        for el, cnt in element_counts.items()
        if el not in ("O", "F", "Cl", "Br", "I") and cnt >= 3
    ]
    m_candidates = [el for el in element_counts if el not in ("O", "F", "Cl", "Br", "I")]
    o_count = element_counts.get("O", 0)
    x_count = sum(element_counts.get(el, 0) for el in x_candidates)

    scores = {}

    a = lattice["a"]
    b = lattice["b"]
    is_hex_like = abs(a - b) / max(a, b) < 0.05 if max(a, b) > 0 else False

    if has_o and x_candidates:
        xo_ratio = o_count / max(x_count, 1)
        if 2.5 <= xo_ratio <= 4.0 and n_distinct_layers >= 5:
            scores["XO3-M7-XO3-M7-XO3-M7-XO3"] = 0.85
        elif 2.8 <= xo_ratio <= 4.5 and n_distinct_layers >= 7:
            scores["XO-T-XO3-M7-XO3-M7-XO3-T-XO-T-XO3-M7-XO3-T-XO3"] = 0.80
        elif 1.5 <= xo_ratio <= 3.0 and n_distinct_layers >= 5:
            scores["XO2-T-XO3-M7-XO3-T-XO2-T-XO3-M7-XO3-T-XO3"] = 0.75
        elif 2.0 <= xo_ratio <= 4.0 and n_distinct_layers >= 4:
            scores["XO3-M7-XO3-T-XO2-T-XO3"] = 0.70
        elif 1.0 <= xo_ratio <= 3.0 and n_distinct_layers >= 3:
            scores["XO-T-XO3-M7-XO3-T-XO3"] = 0.65

    if is_hex_like and has_o and c_ratio > 2.0:
        for key in scores:
            scores[key] += 0.05

    if not scores:
        if has_o and n_distinct_layers >= 3:
            scores["XO3-M7-XO3-M7-XO3-M7-XO3"] = 0.40
        else:
            scores["XO3-M7-XO3-M7-XO3-M7-XO3"] = 0.20

    best = max(scores, key=scores.get)
    return best, round(scores[best], 3)


@app.route("/api/import/preview", methods=["POST"])
def import_preview() -> Response:
    """Preview CIF files before import.

    Parses uploaded CIF files and returns material info, suggested topology,
    and conflict detection without actually importing.

    Returns:
        JSON response with preview results for each file.
    """
    build_indexes()
    try:
        if "files" not in request.files:
            return jsonify({"success": False, "error": "No files uploaded"}), 400

        files = request.files.getlist("files")
        results = []
        target_topology = request.form.get("topology", "").strip()

        for f in files:
            if not f.filename or not f.filename.lower().endswith(".cif"):
                results.append({"filename": f.filename, "error": "Only .cif files are supported"})
                continue

            cif_text = f.read().decode("utf-8", errors="ignore")

            with tempfile.NamedTemporaryFile(suffix=".cif", delete=False, mode="w") as tmp:
                tmp.write(cif_text)
                tmp_path = Path(tmp.name)

            try:
                cif_data = parse_cif_file(tmp_path)
            except Exception as e:
                cif_data = None
            finally:
                os.unlink(tmp_path)

            if not cif_data:
                results.append({"filename": f.filename, "error": "Failed to parse CIF file"})
                continue

            atom_sites = cif_data.get("atom_sites", [])
            lattice = cif_data.get("lattice", {})
            formula = cif_data.get("formula", "")
            space_group = cif_data.get("space_group", "")

            elements_in_formula = (
                extract_elements_from_formula(formula)
                if formula
                else list(set(a["element"] for a in atom_sites))
            )
            material_id_stem = Path(f.filename).stem
            mp_match = re.search(r"(mp-\d+)", material_id_stem)
            material_id = mp_match.group(1) if mp_match else material_id_stem

            existing = material_id in materials_index
            suggested_topo, confidence = _auto_classify_topology(atom_sites, lattice)
            final_topo = target_topology or suggested_topo

            results.append(
                {
                    "filename": f.filename,
                    "material_id": material_id,
                    "formula": formula,
                    "space_group": space_group,
                    "elements": elements_in_formula,
                    "n_atoms": len(atom_sites),
                    "lattice": lattice,
                    "existing": existing,
                    "suggested_topology": suggested_topo,
                    "confidence": confidence,
                    "assigned_topology": final_topo,
                    "cif_preview": cif_text[:500] + ("..." if len(cif_text) > 500 else ""),
                }
            )

        all_protos = list(prototypes_index.keys())
        return jsonify(
            {
                "success": True,
                "results": results,
                "available_topologies": all_protos,
                "total_files": len(files),
                "parsed": sum(1 for r in results if "error" not in r),
                "errors": sum(1 for r in results if "error" in r),
            }
        )
    except Exception as e:
        logger.error("import_preview failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/import", methods=["POST"])
def import_materials() -> Response:
    """Import materials from preview data.

    Writes CIF files to the database directory and updates in-memory indexes.
    Invalidates relevant API caches.

    Returns:
        JSON response with imported, skipped, and error lists.
    """
    global _indexes_built
    build_indexes()
    try:
        body = request.get_json(force=True) if request.is_json else {}
        items = body.get("items", [])

        if not items:
            return jsonify({"success": False, "error": "No items to import"}), 400

        imported = []
        skipped = []
        errors = []

        for item in items:
            material_id = item.get("material_id", "")
            topology = item.get("topology", "").strip()
            cif_content = item.get("cif_content", "")

            if not material_id or not topology or not cif_content:
                errors.append({"material_id": material_id, "reason": "Missing required fields"})
                continue

            if material_id in materials_index:
                skipped.append(material_id)
                continue

            proto_dir = DATABASE_DIR / f"Raw_Proto_{topology}"
            proto_dir.mkdir(parents=True, exist_ok=True)

            formula = item.get("formula", "")
            space_group = item.get("space_group", "")
            elements = item.get("elements", [])
            safe_filename = re.sub(r"[^\w\-.]", "_", material_id)
            if not safe_filename.endswith(".cif"):
                safe_filename += ".cif"
            cif_path = proto_dir / safe_filename

            if cif_path.exists():
                skipped.append(material_id)
                continue

            cif_path.write_text(cif_content, encoding="utf-8")

            mat_entry = {
                "material_id": material_id,
                "formula": formula,
                "space_group": space_group,
                "elements": elements,
                "topology": topology,
                "verified": False,
                "cif_path": str(cif_path),
                "directory": f"Raw_Proto_{topology}",
            }
            materials_index[material_id] = mat_entry
            topology_to_materials[topology].append(material_id)
            space_group_to_materials[space_group].append(material_id)
            formula_to_materials[formula].append(material_id)
            for el in elements:
                element_to_materials.setdefault(el, set()).add(material_id)
                all_elements.add(el)

            imported.append(
                {
                    "material_id": material_id,
                    "topology": topology,
                    "path": str(cif_path.relative_to(DATABASE_DIR)),
                }
            )

        _api_cache.invalidate("prototypes_list", "stats", "classifications", "elements")

        return jsonify(
            {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "total_new": len(imported),
                "total_materials_now": len(materials_index),
            }
        )
    except Exception as e:
        logger.error("import_materials failed: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/import/templates", methods=["GET"])
def import_templates() -> Response:
    """Get available import templates (prototypes).

    Returns:
        JSON response with templates list and total count.
    """
    templates = []
    for proto_id, proto in prototypes_index.items():
        data = proto["data"]
        topo = data.get("topology_theory", {})
        crystal = data.get("prototype_crystallography", {})
        mat_ids = topology_to_materials.get(proto_id, [])
        templates.append(
            {
                "id": proto_id,
                "prototype_id": topo.get("prototype_id", ""),
                "expanded_modes": topo.get("expanded_modes", []),
                "ideal_space_group": crystal.get("ideal_space_group", ""),
                "crystal_system": crystal.get("crystal_system", ""),
                "materials_count": len(mat_ids),
            }
        )
    return jsonify({"templates": templates, "total": len(templates)})


@app.errorhandler(500)
def internal_error(e: Any) -> Response:
    """Handle 500 Internal Server Error."""
    return jsonify({"error": "Internal server error"}), 500


@app.route("/api/health", methods=["GET"])
def health_check() -> Response:
    """Health check endpoint.

    Returns:
        JSON response with status, uptime, index info, and memory usage.
    """
    uptime = time.time() - _start_time
    try:
        import psutil

        mem = psutil.virtual_memory()
        mem_info = {
            "total_mb": round(mem.total / 1048576),
            "used_mb": round(mem.used / 1048576),
            "percent": mem.percent,
        }
    except ImportError:
        mem_info = None
    return jsonify(
        {
            "status": "ok",
            "uptime_seconds": round(uptime, 1),
            "indexes_built": _indexes_built,
            "index_build_time_ms": round(_index_build_time * 1000, 0),
            "n_prototypes": len(prototypes_index),
            "n_materials": len(materials_index),
            "memory": mem_info,
        }
    )


@app.after_request
def add_cache_headers(response: Response) -> Response:
    """Add cache control and API version headers to responses.

    Args:
        response: The Flask response object.

    Returns:
        The modified response with appropriate headers.
    """
    response.headers["X-API-Version"] = "1.0.0"
    if request.path.startswith("/api/health"):
        response.headers["Cache-Control"] = "no-cache"
    elif (
        request.path.startswith("/api/stats")
        or request.path.startswith("/api/elements")
        or request.path.startswith("/api/lattice-types")
    ):
        response.headers["Cache-Control"] = "public, max-age=60"
    elif request.path.startswith("/api/prototypes") and request.method == "GET":
        response.headers["Cache-Control"] = "public, max-age=300"
    elif request.path.startswith("/api/stacking/predict") or request.path.startswith(
        "/api/stacking/analyze"
    ):
        response.headers["Cache-Control"] = "no-store"
    return response


build_indexes()

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
