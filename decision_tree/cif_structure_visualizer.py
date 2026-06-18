#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""根据 CIF 文件路径可视化晶体结构。

运行方式：
    python decision_tree/cif_structure_visualizer.py path/to/file.cif
    python decision_tree/cif_structure_visualizer.py path/to/file.cif --output structure.png
    python decision_tree/cif_structure_visualizer.py path/to/file.cif --show

脚本会尝试使用 pymatgen 解析 CIF，并绘制：
    - 晶胞边界
    - 原子的笛卡尔坐标位置
    - 原子标签
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt

try:
    from pymatgen.core import Structure
except ImportError as exc:  # pragma: no cover - import guard
    raise SystemExit(
        "pymatgen is required for CIF visualization. Install it with `pip install pymatgen`."
    ) from exc


def load_structure(cif_path: Path) -> Structure:
    """从 CIF 文件读取 pymatgen Structure 对象。"""
    if not cif_path.exists():
        raise FileNotFoundError(f"CIF file not found: {cif_path}")
    if not cif_path.is_file():
        raise IsADirectoryError(f"Expected a file path, got a directory: {cif_path}")

    return Structure.from_file(str(cif_path))


def structure_summary(structure: Structure) -> Dict[str, object]:
    """返回一个适合打印或序列化的结构摘要。"""
    lattice = structure.lattice
    return {
        "formula": structure.composition.reduced_formula,
        "num_sites": len(structure),
        "species": [str(el) for el in structure.symbol_set],
        "lattice": {
            "a": round(float(lattice.a), 6),
            "b": round(float(lattice.b), 6),
            "c": round(float(lattice.c), 6),
            "alpha": round(float(lattice.alpha), 4),
            "beta": round(float(lattice.beta), 4),
            "gamma": round(float(lattice.gamma), 4),
        },
    }


def _cell_edges(cart_vertices: List[List[float]]) -> List[List[List[float]]]:
    """根据晶胞 8 个顶点生成 12 条边。"""
    idx_pairs = [
        (0, 1),
        (0, 2),
        (0, 4),
        (1, 3),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 6),
        (5, 7),
        (6, 7),
    ]
    return [[cart_vertices[i], cart_vertices[j]] for i, j in idx_pairs]


def visualize_structure(
    structure: Structure,
    output_path: Optional[Path] = None,
    show: bool = False,
    title: Optional[str] = None,
) -> Path:
    """绘制晶体结构的三维可视化图。"""
    lattice = structure.lattice
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    frac_vertices = [
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1],
    ]
    cart_vertices = [lattice.get_cartesian_coords(v) for v in frac_vertices]
    for start, end in _cell_edges(cart_vertices):
        xs = [start[0], end[0]]
        ys = [start[1], end[1]]
        zs = [start[2], end[2]]
        ax.plot(xs, ys, zs, color="#1f77b4", linewidth=1.4, alpha=0.9)

    species = [site.specie.symbol for site in structure]
    coords = [site.coords for site in structure]
    unique_species = sorted(set(species))
    cmap = plt.get_cmap("tab20")
    color_map = {sp: cmap(i % 20) for i, sp in enumerate(unique_species)}

    for sp in unique_species:
        pts = [c for c, s in zip(coords, species) if s == sp]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        zs = [p[2] for p in pts]
        ax.scatter(xs, ys, zs, s=70, color=color_map[sp], label=sp, depthshade=True)

    # 只给一部分原子加标签，避免图面过于拥挤。
    for i, site in enumerate(structure[: min(len(structure), 30)]):
        x, y, z = site.coords
        ax.text(x, y, z, f"{site.specie.symbol}{i + 1}", fontsize=7)

    all_coords = coords + cart_vertices
    xs = [p[0] for p in all_coords]
    ys = [p[1] for p in all_coords]
    zs = [p[2] for p in all_coords]
    dx = max(xs) - min(xs) if xs else 1.0
    dy = max(ys) - min(ys) if ys else 1.0
    dz = max(zs) - min(zs) if zs else 1.0
    max_range = max(dx, dy, dz) * 0.55 or 1.0
    mid_x = (max(xs) + min(xs)) / 2 if xs else 0.0
    mid_y = (max(ys) + min(ys)) / 2 if ys else 0.0
    mid_z = (max(zs) + min(zs)) / 2 if zs else 0.0

    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("X (Angstrom)")
    ax.set_ylabel("Y (Angstrom)")
    ax.set_zlabel("Z (Angstrom)")
    ax.view_init(elev=18, azim=35)
    if title is None:
        title = f"{structure.composition.reduced_formula} crystal structure"
    ax.set_title(title)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    plt.tight_layout()

    if output_path is None:
        output_path = Path.cwd() / "cif_structure.png"
    output_path = output_path.resolve()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="可视化 CIF 晶体结构。")
    parser.add_argument("cif_path", type=Path, help="CIF 文件路径")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="输出图片路径，默认是 ./cif_structure.png",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="渲染完成后打开图形窗口",
    )
    args = parser.parse_args()

    structure = load_structure(args.cif_path)
    summary = structure_summary(structure)
    print("结构摘要：")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    output_path = visualize_structure(
        structure=structure,
        output_path=args.output,
        show=args.show,
        title=f"{args.cif_path.name} | {summary['formula']}",
    )
    print(f"已保存可视化图片：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())