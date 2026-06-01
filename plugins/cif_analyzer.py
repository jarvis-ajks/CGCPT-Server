"""
示例插件: CIF 结构分析器
演示如何使用 CGCPT Plugin SDK 开发算法插件

使用方式:
  1. 将此文件放到 /opt/CGCPT/plugins/ 目录
  2. 启动时自动发现，或通过 API 注册
  3. 通过 POST /api/plugins/cif_analyzer/execute 执行
"""

import re
from typing import Dict, Any, List

from cgcpt_plugin import CGCPTPlugin, PluginContext, cgcpt_algorithm


@cgcpt_algorithm(
    id="cif_analyzer",
    name="CIF 结构分析器",
    algorithm_type="prediction",
    description="解析 CIF 文件内容，提取晶格参数、原子坐标、化学式等信息，并自动归类到数据库",
    version="1.0.0",
    input_schema={
        "type": "object",
        "properties": {
            "cif_content": {
                "type": "string",
                "description": "CIF 文件内容",
            },
            "material_id": {
                "type": "string",
                "description": "材料ID（可选，不提供则自动生成）",
            },
            "topology_id": {
                "type": "string",
                "description": "指定拓扑分类ID（可选）",
            },
            "save_to_db": {
                "type": "boolean",
                "description": "是否保存到数据库",
                "default": True,
            },
        },
        "required": ["cif_content"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "formula": {"type": "string"},
            "space_group": {"type": "string"},
            "lattice": {"type": "object"},
            "n_atoms": {"type": "integer"},
            "elements": {"type": "array"},
        },
    },
    default_config={
        "save_to_db": True,
    },
)
class CIFAnalyzer(CGCPTPlugin):

    def execute(self, ctx: PluginContext) -> Dict[str, Any]:
        cif_content = ctx.get_cif()
        ctx.update_progress(0.1, "解析 CIF 内容")

        parsed = self._parse_cif(cif_content)
        if not parsed:
            return {"success": False, "error": "无法解析 CIF 内容"}

        ctx.update_progress(0.5, "提取结构信息")

        formula = parsed.get("formula", "Unknown")
        space_group = parsed.get("space_group", "P1")
        lattice = parsed.get("lattice", {})
        elements = parsed.get("elements", [])
        atom_sites = parsed.get("atom_sites", [])

        ctx.update_progress(0.7, "分析完成")

        save_to_db = ctx.get("save_to_db", True)
        material_id = ctx.get("material_id", f"algo_{formula}_{space_group}".replace(" ", "_"))
        topology_id = ctx.get("topology_id", "")

        saved = False
        if save_to_db and topology_id:
            saved = ctx.save_material(
                material_id=material_id,
                formula=formula,
                space_group=space_group,
                topology_id=topology_id,
                elements=elements,
                lattice=lattice,
                cif_content=cif_content,
                is_verified=False,
                source="cif_analyzer",
                metadata={"atom_sites": atom_sites[:50]},
                n_atoms=len(atom_sites),
            )

        ctx.update_progress(1.0, "完成")

        return {
            "success": True,
            "material_id": material_id,
            "formula": formula,
            "space_group": space_group,
            "lattice": lattice,
            "elements": elements,
            "n_atoms": len(atom_sites),
            "saved_to_db": saved,
        }

    def _parse_cif(self, content: str) -> Dict[str, Any]:
        lattice = {}
        for key, tag in [
            ("a", "_cell_length_a"),
            ("b", "_cell_length_b"),
            ("c", "_cell_length_c"),
            ("alpha", "_cell_angle_alpha"),
            ("beta", "_cell_angle_beta"),
            ("gamma", "_cell_angle_gamma"),
        ]:
            m = re.search(rf"{tag}\s+([\d.]+)", content)
            if m:
                lattice[key] = float(m.group(1))

        sg_match = re.search(r"_symmetry_space_group_name_H-M\s+['\"]?([^'\"]+)['\"]?", content)
        space_group = sg_match.group(1).strip() if sg_match else "P1"

        formula_match = re.search(r"_chemical_formula_structural\s+(\S+)", content)
        formula = formula_match.group(1).strip() if formula_match else ""

        if not formula:
            formula_match2 = re.search(r"_chemical_formula_sum\s+['\"]?([^'\"]+)['\"]?", content)
            formula = formula_match2.group(1).strip() if formula_match2 else "Unknown"

        elements = []
        atom_sites = []
        lines = content.splitlines()
        in_loop = False
        loop_tags = []
        tag_idx = {}
        data_start = -1

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("loop_"):
                in_loop = True
                loop_tags = []
                tag_idx = {}
                data_start = -1
                i += 1
                continue

            if in_loop:
                if line.startswith("_"):
                    loop_tags.append(line.split()[0])
                    tag_idx[line.split()[0]] = len(loop_tags) - 1
                    i += 1
                    continue
                elif loop_tags and data_start == -1:
                    data_start = i

                if "_atom_site_label" in tag_idx and data_start >= 0:
                    if not line or line.startswith("loop_") or line.startswith("_"):
                        in_loop = False
                        continue
                    parts = line.split()
                    if len(parts) >= len(loop_tags):
                        label_idx = tag_idx.get("_atom_site_label", -1)
                        x_idx = tag_idx.get("_atom_site_fract_x", -1)
                        y_idx = tag_idx.get("_atom_site_fract_y", -1)
                        z_idx = tag_idx.get("_atom_site_fract_z", -1)

                        if label_idx >= 0:
                            label = parts[label_idx]
                            element = re.match(r"([A-Z][a-z]?)", label)
                            el = element.group(1) if element else label
                            if el not in elements:
                                elements.append(el)
                            site = {"element": el}
                            if x_idx >= 0:
                                try:
                                    site["x"] = float(re.match(r"([\d.]+)", parts[x_idx]).group(1))
                                except (ValueError, AttributeError):
                                    pass
                            if y_idx >= 0:
                                try:
                                    site["y"] = float(re.match(r"([\d.]+)", parts[y_idx]).group(1))
                                except (ValueError, AttributeError):
                                    pass
                            if z_idx >= 0:
                                try:
                                    site["z"] = float(re.match(r"([\d.]+)", parts[z_idx]).group(1))
                                except (ValueError, AttributeError):
                                    pass
                            atom_sites.append(site)
            i += 1

        return {
            "lattice": lattice,
            "space_group": space_group,
            "formula": formula,
            "elements": elements,
            "atom_sites": atom_sites,
        }
