"""Crystal Toolkit scene service (Materials Project viewer payloads).

Thin HTTP wrapper around the upstream `crystal_toolkit` package: the JSON
returned here is what the Materials Project React viewer expects, and is built
with the same pipeline as `crystal_toolkit.components.StructureMoleculeComponent`
(CrystalNN bonds, VESTA colours, uniform radii, image atoms, compass axes).
No rendering logic lives in this file.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

import numpy as np
from flask import Flask, jsonify, request
from pymatgen.analysis.graphs import StructureGraph
from pymatgen.analysis.local_env import CrystalNN
from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifParser, CifWriter

import crystal_toolkit.renderables.lattice  # noqa: F401  (patches Lattice._axes_from_lattice)
import crystal_toolkit.renderables.structuregraph  # noqa: F401  (patches StructureGraph.get_scene)
from crystal_toolkit.core.legend import Legend

app = Flask(__name__)

LATTICE_KEYS = ("a", "b", "c", "alpha", "beta", "gamma")

# Mirrors crystal_toolkit.components.structure.DEFAULTS for structures.
COLOR_SCHEME = "VESTA"
RADIUS_SCHEME = "uniform"
DRAW_IMAGE_ATOMS = True
BONDED_SITES_OUTSIDE_UNIT_CELL = False
HIDE_INCOMPLETE_BONDS = True
SHOW_COMPASS = True


def _structure_from_cif(cif_text: str) -> Structure:
    """Parse the first structure out of CIF text (Materials Project semantics)."""
    structures = CifParser(StringIO(cif_text)).parse_structures(primitive=False)
    if not structures:
        raise ValueError("CIF文件解析失败")
    return structures[0]


def _structure_from_spec(spec: dict[str, Any]) -> Structure:
    """Build a pymatgen Structure from the JSON shape used by the frontend.

    `lattice` carries cell parameters in angstrom/degree; `atoms` carries
    fractional coordinates, matching `api_server` CIF parsing output.
    """
    lattice_data = spec.get("lattice") or {}
    atoms = spec.get("atoms") or []
    if not atoms:
        raise ValueError("结构数据为空")

    missing = [key for key in LATTICE_KEYS if lattice_data.get(key) is None]
    if missing:
        raise ValueError(f"晶格参数缺失: {', '.join(missing)}")

    lattice = Lattice.from_parameters(*(float(lattice_data[key]) for key in LATTICE_KEYS))
    species = [str(atom.get("element", "")) for atom in atoms]
    if any(not element for element in species):
        raise ValueError("原子缺少元素符号")
    coords = [
        [float(atom.get("x", 0.0)), float(atom.get("y", 0.0)), float(atom.get("z", 0.0))]
        for atom in atoms
    ]
    return Structure(lattice, species, coords, coords_are_cartesian=False)


def _normalise_fractional_coords(structure: Structure) -> Structure:
    """Keep fractional coordinates in [0, 1), as StructureMoleculeComponent does."""
    frac = structure.frac_coords
    if np.all((frac >= 0) & (frac < 1)):
        return structure
    return Structure(
        structure.lattice,
        structure.species,
        np.mod(frac, 1),
        site_properties=structure.site_properties,
    )


def _jsonable(value: Any) -> Any:
    """Convert numpy scalars/arrays so Flask can serialise the scene dict."""
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _structure_scene(structure: Structure) -> dict[str, Any]:
    """Replicate StructureMoleculeComponent.get_scene_and_legend for structures."""
    structure = _normalise_fractional_coords(structure)

    graph_factory = getattr(StructureGraph, "from_local_env_strategy", None) or getattr(
        StructureGraph, "with_local_env_strategy"
    )
    graph = graph_factory(structure, CrystalNN())

    legend = Legend(structure, color_scheme=COLOR_SCHEME, radius_scheme=RADIUS_SCHEME)
    scene = graph.get_scene(
        draw_image_atoms=DRAW_IMAGE_ATOMS,
        bonded_sites_outside_unit_cell=BONDED_SITES_OUTSIDE_UNIT_CELL,
        hide_incomplete_edges=HIDE_INCOMPLETE_BONDS,
        explicitly_calculate_polyhedra_hull=False,
        group_by_site_property=None,
        legend=legend,
    )
    scene.name = "StructureMoleculeComponentScene"

    axes = structure.lattice._axes_from_lattice()
    axes.visible = SHOW_COMPASS
    scene.contents.append(axes)

    return _jsonable(scene.to_json())


@app.post("/scene")
def scene():
    """Return an official scene, or symmetry-expanded P1 CIF for comparison."""
    payload = request.get_json(force=True, silent=True) or {}
    cif_text = payload.get("cif_text") or ""
    spec = payload.get("structure") or {}
    if not cif_text and not spec:
        return jsonify({"error": "请提供CIF文本或结构数据"}), 400
    try:
        structure = _structure_from_cif(cif_text) if cif_text else _structure_from_spec(spec)
        if payload.get("output") == "cif":
            structure = _normalise_fractional_coords(structure)
            structure.relabel_sites()
            return jsonify({
                "cif_text": str(CifWriter(structure, symprec=None, significant_figures=12)),
                "site_count": len(structure),
            })
        return jsonify(_structure_scene(structure))
    except Exception as exc:  # surfaced to the viewer as an error payload
        return jsonify({"error": str(exc)}), 400


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=18108)
