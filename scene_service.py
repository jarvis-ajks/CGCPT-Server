"""Crystal Toolkit scene service (Materials Project viewer payloads).

Thin HTTP wrapper around the upstream `crystal_toolkit` package: the JSON
returned here is exactly what the Materials Project React viewer
(`CrystalToolkitScene`) expects. No rendering logic lives in this file.

Run next to the API server (separate process, separate memory budget):

    gunicorn --workers 1 --worker-class sync --bind 127.0.0.1:18108 \
        --timeout 90 --graceful-timeout 10 scene_service:app
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from flask import Flask, jsonify, request
from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifParser

from crystal_toolkit.renderables.structure import get_structure_scene

app = Flask(__name__)

LATTICE_KEYS = ("a", "b", "c", "alpha", "beta", "gamma")


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


@app.post("/scene")
def scene():
    """Return the Materials Project scene JSON for a CIF or a structure spec."""
    payload = request.get_json(force=True, silent=True) or {}
    cif_text = payload.get("cif_text") or ""
    spec = payload.get("structure") or {}
    if not cif_text and not spec:
        return jsonify({"error": "请提供CIF文本或结构数据"}), 400
    try:
        structure = _structure_from_cif(cif_text) if cif_text else _structure_from_spec(spec)
        return jsonify(get_structure_scene(structure).to_json())
    except Exception as exc:  # surfaced to the viewer as an error payload
        return jsonify({"error": str(exc)}), 400


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=18108)
