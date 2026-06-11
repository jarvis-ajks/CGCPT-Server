#!/usr/bin/env python3
"""
CGCPT 插件验证与测试工具

用法:
  python plugin_tool.py discover          # 发现所有插件
  python plugin_tool.py validate <file>   # 验证插件文件
  python plugin_tool.py test <id>         # 测试执行插件
  python plugin_tool.py register <id>     # 注册插件到数据库
  python plugin_tool.py list              # 列出已注册插件
"""

import os
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def cmd_discover(args):
    from cgcpt_plugin import discover_plugins

    plugins = discover_plugins(args.plugin_dir)
    if not plugins:
        print("未发现任何插件")
        return
    print(f"发现 {len(plugins)} 个插件:\n")
    for p in plugins:
        print(f"  ID:   {p['id']}")
        print(f"  名称: {p['name']}")
        print(f"  类型: {p['algorithm_type']}")
        print(f"  版本: {p['version']}")
        print(f"  入口: {p['entry_point']}")
        print(f"  描述: {p['description'][:80]}")
        print()


def cmd_validate(args):
    from cgcpt_plugin import validate_plugin_class, _PLUGIN_REGISTRY
    import importlib.util

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"文件不存在: {file_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location(file_path.stem, str(file_path))
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"导入失败: {e}")
        sys.exit(1)

    found_classes = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and hasattr(attr, "algorithm_id") and attr.algorithm_id:
            found_classes.append(attr)

    if not found_classes:
        print("未找到有效的插件类（需使用 @cgcpt_algorithm 装饰器或设置 algorithm_id）")
        sys.exit(1)

    all_valid = True
    for cls in found_classes:
        errors = validate_plugin_class(cls)
        if errors:
            print(f"插件 {cls.algorithm_id} 验证失败:")
            for e in errors:
                print(f"  - {e}")
            all_valid = False
        else:
            print(f"插件 {cls.algorithm_id} ({cls.algorithm_name}) 验证通过")

    sys.exit(0 if all_valid else 1)


def cmd_test(args):
    from cgcpt_plugin import discover_plugins, instantiate_plugin

    discover_plugins(args.plugin_dir)

    plugin = instantiate_plugin(args.plugin_id)
    if not plugin:
        print(f"未找到插件: {args.plugin_id}")
        sys.exit(1)

    input_data = {}
    if args.input:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            print("输入参数 JSON 格式错误")
            sys.exit(1)

    print(f"测试执行插件: {plugin.algorithm_id}")
    print(f"输入: {json.dumps(input_data, ensure_ascii=False, indent=2)}")
    print()

    result = plugin.run(input_data, task_id="test_001")
    print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    if result.get("success"):
        print("\n执行成功!")
    else:
        print(f"\n执行失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def cmd_register(args):
    from cgcpt_plugin import discover_plugins, instantiate_plugin
    from task_worker import register_external_algorithm

    discover_plugins(args.plugin_dir)

    plugin = instantiate_plugin(args.plugin_id)
    if not plugin:
        print(f"未找到插件: {args.plugin_id}")
        sys.exit(1)

    definition = plugin.get_definition()
    algo_id = register_external_algorithm(definition)
    print(f"已注册插件: {algo_id}")


def cmd_list(args):
    from models import SessionLocal, Algorithm

    db = SessionLocal()
    try:
        algos = db.query(Algorithm).all()
        if not algos:
            print("数据库中无已注册算法")
            return
        print(f"已注册 {len(algos)} 个算法:\n")
        for a in algos:
            status = "活跃" if a.is_active else "停用"
            print(f"  [{status}] {a.id} - {a.name} ({a.algorithm_type}) v{a.version}")
            print(f"         入口: {a.entry_point}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="CGCPT 插件工具")
    parser.add_argument("--plugin-dir", default=None, help="插件目录路径")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("discover", help="发现所有插件")

    validate_parser = subparsers.add_parser("validate", help="验证插件文件")
    validate_parser.add_argument("file", help="插件 Python 文件路径")

    test_parser = subparsers.add_parser("test", help="测试执行插件")
    test_parser.add_argument("plugin_id", help="插件 ID")
    test_parser.add_argument("--input", default="{}", help="输入参数 JSON")

    register_parser = subparsers.add_parser("register", help="注册插件到数据库")
    register_parser.add_argument("plugin_id", help="插件 ID")

    subparsers.add_parser("list", help="列出已注册算法")

    args = parser.parse_args()

    commands = {
        "discover": cmd_discover,
        "validate": cmd_validate,
        "test": cmd_test,
        "register": cmd_register,
        "list": cmd_list,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
