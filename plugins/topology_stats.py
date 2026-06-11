"""
示例插件: 批量拓扑统计
演示查询数据库并生成统计报告的插件
"""

from typing import Dict, Any

from cgcpt_plugin import CGCPTPlugin, PluginContext, cgcpt_algorithm


@cgcpt_algorithm(
    id="topology_stats",
    name="拓扑统计报告",
    algorithm_type="prediction",
    description="查询数据库中所有拓扑分类的统计信息，生成结构化报告",
    version="1.0.0",
    input_schema={
        "type": "object",
        "properties": {
            "crystal_system": {
                "type": "string",
                "description": "按晶系筛选（可选）",
            },
            "include_materials": {
                "type": "boolean",
                "description": "是否包含材料列表",
                "default": False,
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "total_prototypes": {"type": "integer"},
            "total_materials": {"type": "integer"},
            "topology_breakdown": {"type": "object"},
        },
    },
)
class TopologyStats(CGCPTPlugin):

    def execute(self, ctx: PluginContext) -> Dict[str, Any]:
        crystal_system = ctx.get("crystal_system")
        include_materials = ctx.get("include_materials", False)

        ctx.update_progress(0.2, "查询原型数据")
        prototypes = ctx.query_prototypes(crystal_system=crystal_system)

        ctx.update_progress(0.5, "统计材料数据")
        topology_breakdown = {}
        total_materials = 0

        for proto in prototypes:
            topo_id = proto["id"]
            materials = ctx.query_materials(topology_id=topo_id, limit=1000)
            count = len(materials)
            total_materials += count

            entry = {
                "prototype_id": proto["prototype_id"],
                "ideal_space_group": proto["ideal_space_group"],
                "crystal_system": proto["crystal_system"],
                "materials_count": count,
            }
            if include_materials:
                entry["materials"] = materials[:20]

            topology_breakdown[topo_id] = entry
            ctx.update_progress(
                0.5 + 0.4 * (len(topology_breakdown) / max(len(prototypes), 1)), f"统计 {topo_id}"
            )

        ctx.update_progress(1.0, "完成")

        return {
            "success": True,
            "total_prototypes": len(prototypes),
            "total_materials": total_materials,
            "topology_breakdown": topology_breakdown,
        }
