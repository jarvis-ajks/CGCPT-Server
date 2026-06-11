import os
import shutil
import warnings
from pymatgen.core import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher

warnings.filterwarnings("ignore")


def standardize_and_strip(struct, template_sorted_els):
    comp = struct.composition.fractional_composition
    sorted_items = sorted(comp.items(), key=lambda x: x[1], reverse=True)
    test_sorted_els = [str(item[0]) for item in sorted_items]

    if len(test_sorted_els) != len(template_sorted_els):
        return None

    mapping = {test_sorted_els[i]: template_sorted_els[i] for i in range(len(template_sorted_els))}
    struct_copy = struct.copy()
    struct_copy.replace_species(mapping)

    anion = template_sorted_els[0]
    struct_copy.remove_species([anion])
    return struct_copy


def run_verification(template_cif, raw_dir, verified_dir):
    print("\n========== 阶段 2：拓扑指纹提纯 ==========")
    os.makedirs(verified_dir, exist_ok=True)

    matcher = StructureMatcher(
        ltol=0.3, stol=0.8, angle_tol=15.0, primitive_cell=True, scale=True, attempt_supercell=True
    )

    try:
        base_struct = Structure.from_file(template_cif)
        base_comp = base_struct.composition.fractional_composition
        base_sorted_items = sorted(base_comp.items(), key=lambda x: x[1], reverse=True)
        template_sorted_els = [str(item[0]) for item in base_sorted_items]

        anion = template_sorted_els[0]
        base_struct.remove_species([anion])
        print(f"   📐 模板 {template_cif} 已准备，使用骨架: {template_sorted_els[1:]}")
    except Exception as e:
        print(f"❌ 无法加载模板文件: {e}")
        return

    count = 0
    all_files = [f for f in os.listdir(raw_dir) if f.endswith(".cif")]
    print(f"   🔍 正在对 {len(all_files)} 个结构进行超胞与骨架比对...")

    for filename in all_files:
        filepath = os.path.join(raw_dir, filename)
        try:
            test_struct = Structure.from_file(filepath)
            standardized_test = standardize_and_strip(test_struct, template_sorted_els)

            if standardized_test is None:
                continue

            if matcher.fit(base_struct, standardized_test):
                shutil.copy(filepath, os.path.join(verified_dir, filename))
                count += 1
        except:
            continue

    print(f"🎉 质检完毕！提取出真正同构的基质: {count} 个")
    print(f"📁 最终名单路径: {verified_dir}/")
