import os
import search_mp
import verify_topology

# =====================================================================
# 说明：每次切换研究对象，只需修改这里的参数，不要动底层代码！
# =====================================================================

CONFIG = {
    # 1. 您的 Materials Project 秘钥
    "api_key": "WI5JaLAqWrkp0TmxVPP5qQXVCfDVKOvd",  # 请填入您的真实 Key

    # 2. 本次研究的拓扑配比与阳离子限制
    "target_formula": "ABO3",
    "required_elements": {"Na", "K", "Rb", "Cs", "Mg", "Ca", "Sr", "Ba", "Sc", "Y"},

    # 3. 本次使用的最高对称性标准尺 (Cif 文件路径)
    "template_cif": "database/primitive_BaTiO3.cif",

    # 4. 本次课题/原型的统一命名 (将自动用于创建文件夹)
    "project_name": "Proto_XO3-M7-XO3-M7-XO3-XO3"
}


# =====================================================================

def main():
    # 自动推导文件夹路径，绝不混淆
    raw_dir = os.path.join("database", f"Raw_{CONFIG['project_name']}")
    verified_dir = os.path.join("database", f"Verified_{CONFIG['project_name']}")

    print(f"启动高通量筛选流水线: 项目 [{CONFIG['project_name']}]")

    # 阶段 1：自动调用开采模块
    # 如果您已经下载过了，只想重新跑比对，可以把下面这行注释掉
    search_mp.search_and_download_materials(
        api_key=CONFIG["api_key"],
        target_formula=CONFIG["target_formula"],
        required_elements=CONFIG["required_elements"],
        output_dir=raw_dir
    )

    # 阶段 2：自动调用质检模块
    verify_topology.run_verification(
        template_cif=CONFIG["template_cif"],
        raw_dir=raw_dir,
        verified_dir=verified_dir
    )


if __name__ == "__main__":
    main()