import os
import csv
from mp_api.client import MPRester


# 注意这里：函数现在有了4个接收参数的“接口”
def search_and_download_materials(api_key, target_formula, required_elements, output_dir):
    print("\n========== 阶段 1：云端矿石开采 ==========")
    os.makedirs(output_dir, exist_ok=True)

    try:
        with MPRester(api_key) as mpr:
            print(f"🔍 正在全库检索 {target_formula} 构型并拉取结构...")
            results = mpr.materials.summary.search(
                formula=target_formula,
                exclude_elements=["H"],
                fields=["material_id", "formula_pretty", "symmetry", "energy_above_hull", "elements", "structure"]
            )

            # 本地精筛阳离子
            filtered_results = []
            for doc in results:
                elem_strs = [str(e) for e in doc.elements]
                if any(atom in elem_strs for atom in required_elements):
                    filtered_results.append(doc)

            sorted_results = sorted(filtered_results, key=lambda x: x.energy_above_hull)
            print(f"✅ 检索成功！锁定 {len(sorted_results)} 个候选结构。")

            # 导出数据
            csv_path = os.path.join(output_dir, "summary_info.csv")
            with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["排名", "化学式", "MP_ID", "空间群", "Ehull", "元素"])

                for i, doc in enumerate(sorted_results):
                    formula = doc.formula_pretty
                    mp_id = doc.material_id
                    sg = doc.symmetry.symbol
                    ehull = doc.energy_above_hull
                    elements_str = "-".join([str(e) for e in doc.elements])

                    writer.writerow([i + 1, formula, mp_id, sg, round(ehull, 4), elements_str])

                    safe_sg = sg.replace("/", "_")
                    cif_filepath = os.path.join(output_dir, f"{formula}_{safe_sg}_{mp_id}.cif")
                    if doc.structure:
                        doc.structure.to(fmt="cif", filename=cif_filepath)

            print(f"💎 CIF 文件已全部存入: {output_dir}/")
    except Exception as e:
        print(f"❌ 开采失败: {e}")