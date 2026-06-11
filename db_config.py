# db_config.py

prototype_document = {
    # 1. 堆积与拓扑逻辑 (Stacking & Topology) - 【已修正】
    # 这里的键值对，应该直接对应您 LayeredXOGenerator 类中使用的参数和输出结果
    "topology_theory": {
        "prototype_id": "Glaserite-Trigonal",
        # 对应您主程序中的 layer_modes 参数 (比如您理论中的抽象多面体节点)
        "layer_modes": ["XO3", "M7", "XO3", "XO2"],  # 假设钾芒硝在您的理论中对应这种拓扑节点组合
        # 对应您主程序中的层间平移/堆叠逻辑 (stack_label 或 sequence)
        "stack_labels": ["A", "B", "C"],
        # 对应您 get_reference_grid_sites_for_layer 等函数中可能用到的网格基准
        "reference_grid": "M7_base",
    },
    # 2. 结构原型 (Prototype Crystallography) - 保持不变
    "prototype_crystallography": {
        "ideal_space_group": "P-3m1",
        "space_group_number": 164,
        "crystal_system": "Trigonal",
        "is_neutral": True,
        "wyckoff_signature": {"K": "1a, 2d", "Na": "1b", "S": "2d", "O": "2d, 6i"},
    },
    # 3. 实际化合物 (Real Crystals) - 保持不变
    "real_compounds": [
        {
            "formula": "K3Na(SO4)2",
            "mineral_name": "Aphthitalite",
            "source_id": "mp-4850",
            "rmsd_to_ideal": 0.0,
            "properties": {"is_luminescent_host": True},
        }
    ],
}

if __name__ == "__main__":
    import json

    with open("glaserite_test.json", "w", encoding="utf-8") as f:
        json.dump(prototype_document, f, indent=4, ensure_ascii=False)
    print("钾芒硝结构原型数据库测试文件已生成！")
