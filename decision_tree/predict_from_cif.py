#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""根据 CIF 文件路径预测单个晶体结构的层状堆垛结果。

运行方式：
    python decision_tree/predict_from_cif.py path/to/file.cif
    python decision_tree/predict_from_cif.py path/to/file.cif --stack ABC
    python decision_tree/predict_from_cif.py path/to/file.cif --json

这个脚本一次只处理一个 CIF 文件。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import joblib
except ImportError as exc:  # pragma: no cover
    raise SystemExit("缺少 joblib，请先安装依赖。") from exc


# 将仓库根目录加入模块搜索路径，确保能导入根目录下的 stacking_analyzer.py
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from stacking_analyzer import extract_layer_features
from train_stacking_dt import predict_stacking


OUTPUT_DIR = Path(__file__).resolve().parent
MODEL_PATH = OUTPUT_DIR / "stacking_dt_model.joblib"


def _parse_cif_manual(cif_path: Path) -> Optional[dict[str, Any]]:
    """使用手写兜底方式解析 CIF 文件。"""
    try:
        text = cif_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    lattice: dict[str, float] = {}
    for key, tag in [
        ("a", "_cell_length_a"),
        ("b", "_cell_length_b"),
        ("c", "_cell_length_c"),
        ("alpha", "_cell_angle_alpha"),
        ("beta", "_cell_angle_beta"),
        ("gamma", "_cell_angle_gamma"),
    ]:
        m = re.search(rf"{tag}\s+([-\d.]+)", text)
        if m:
            try:
                lattice[key] = float(m.group(1))
            except ValueError:
                pass

    sg_match = re.search(r"_symmetry_space_group_name_H-M\s+['\"]?([^'\"]+)['\"]?", text)
    space_group = sg_match.group(1).strip() if sg_match else None

    formula_match = re.search(r"_chemical_formula_structural\s+(\S+)", text)
    formula = formula_match.group(1).strip() if formula_match else ""
    if not formula:
        formula_match2 = re.search(r"_chemical_formula_sum\s+['\"]?([^'\"]+)['\"]?", text)
        formula = formula_match2.group(1).strip() if formula_match2 else ""

    atom_sites: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line != "loop_":
            i += 1
            continue

        tags: list[str] = []
        i += 1
        while i < len(lines) and lines[i].strip().startswith("_"):
            tags.append(lines[i].strip().split()[0])
            i += 1

        if not tags or "_atom_site_fract_x" not in tags:
            continue

        tag_idx = {tag: idx for idx, tag in enumerate(tags)}
        while i < len(lines):
            dl = lines[i].strip()
            if not dl or dl.startswith("_") or dl == "loop_":
                break

            parts = dl.split()
            if len(parts) >= len(tags):
                try:
                    elem = parts[tag_idx.get("_atom_site_type_symbol", tag_idx.get("_atom_site_label", 0))]
                    elem_match = re.match(r"[A-Z][a-z]?", elem)
                    element = elem_match.group(0) if elem_match else elem
                    fx = float(parts[tag_idx["_atom_site_fract_x"]])
                    fy = float(parts[tag_idx["_atom_site_fract_y"]])
                    fz = float(parts[tag_idx["_atom_site_fract_z"]])
                    atom_sites.append(
                        {
                            "element": element,
                            "x": round(fx, 8),
                            "y": round(fy, 8),
                            "z": round(fz, 8),
                        }
                    )
                except (ValueError, IndexError, KeyError):
                    pass
            i += 1

    return {
        "lattice": lattice,
        "atom_sites": atom_sites,
        "formula": formula,
        "space_group": space_group,
    }


def parse_cif_file(cif_path: Path) -> Optional[dict[str, Any]]:
    """优先使用 pymatgen 解析，失败后回退到手写解析。"""
    try:
        from pymatgen.core import Structure

        structure = Structure.from_file(str(cif_path))
        lattice = structure.lattice
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
            "formula": structure.composition.reduced_formula,
            "space_group": None,
        }
    except Exception:
        return _parse_cif_manual(cif_path)


def load_model():
    """加载本地模型；如果没有模型则返回 None。"""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def predict_from_cif_file(cif_path: Path, stack_sequence: str = "ABC") -> dict[str, Any]:
    """从单个 CIF 文件直接预测决策树堆垛结果。"""
    cif_data = parse_cif_file(cif_path)
    if not cif_data:
        return {"success": False, "error": f"无法解析 CIF 文件：{cif_path}"}

    layer_features = extract_layer_features(cif_data)
    if not layer_features:
        return {"success": False, "error": "无法从 CIF 文件中提取层信息"}

    # 把每一层映射成模型需要的层类型。
    layer_modes = []
    for item in layer_features:
        layer_mode = item.get("predicted_type", "XO3")
        layer_modes.append(layer_mode if layer_mode else "XO3")

    clf = load_model()
    if clf is None:
        return {"success": False, "error": f"本地没有模型：{MODEL_PATH}"}

    predictions = predict_stacking(clf, layer_modes, stack_sequence)

    return {
        "success": True,
        "cif_path": str(cif_path),
        "formula": cif_data.get("formula", ""),
        "space_group": cif_data.get("space_group", ""),
        "lattice": cif_data.get("lattice", {}),
        "n_atoms": len(cif_data.get("atom_sites", [])),
        "layer_analysis": layer_features,
        "detected_modes": layer_modes,
        "predictions": predictions,
        "stack_sequence": stack_sequence,
        "model_path": str(MODEL_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 CIF 文件预测决策树堆垛结果。")
    parser.add_argument("cif_path", type=Path, help="CIF 文件路径")
    parser.add_argument(
        "--stack",
        default="ABC",
        help="堆垛序列文本，默认是 ABC",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    args = parser.parse_args()

    result = predict_from_cif_file(cif_path=args.cif_path, stack_sequence=args.stack)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("success") else 1

    if not result.get("success"):
        print(f"预测失败：{result.get('error', '未知错误')}")
        return 1

    print("预测成功")
    print(f"  CIF 文件：{result['cif_path']}")
    print(f"  化学式：{result.get('formula', '')}")
    print(f"  空间群：{result.get('space_group', '')}")
    print(f"  原子数：{result.get('n_atoms', 0)}")
    print(f"  识别到的层类型：{result.get('detected_modes', [])}")
    print(f"  预测堆垛序列：{result.get('stack_sequence', '')}")
    print("  每层预测结果：")
    predicted_shifts = result.get("predictions", [])
    detected_modes = result.get("detected_modes", [])
    for i, pred_shift in enumerate(predicted_shifts):
        mode = detected_modes[i] if i < len(detected_modes) else "unknown"
        print(f"    第 {i} 层 | 模式 {mode} | 预测堆垛 {pred_shift}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())