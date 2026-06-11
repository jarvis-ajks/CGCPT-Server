#!/usr/bin/env python3
"""
在服务器上执行完整的部署和迁移脚本
"""

import os
import sys
import time
import subprocess
from pathlib import Path


def run(cmd: str, cwd: str = "/opt/CGCPT") -> tuple[int, str, str]:
    """运行系统命令"""
    print(f"$ {cmd}")
    proc = subprocess.Popen(
        cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = proc.communicate()
    if stdout:
        print(stdout.strip())
    if stderr:
        print("STDERR:", stderr.strip())
    return proc.returncode, stdout, stderr


def main():
    print("=" * 70)
    print("  CGCPT 完整部署和迁移脚本")
    print("=" * 70)

    os.chdir("/opt/CGCPT")
    print(f"\n当前目录: {os.getcwd()}")

    # 1. 检查文件完整性
    print("\n[1] 检查项目文件完整性...")
    files = [
        "api_server.py",
        "models.py",
        "task_worker.py",
        "stacking_analyzer.py",
        "requirements.txt",
    ]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        print(f"✗ 缺少文件: {missing}")
    else:
        print("✓ 所有核心文件齐全")

    # 2. 检查 venv 和依赖
    print("\n[2] 检查 Python 环境和依赖...")
    venv = Path("/opt/CGCPT/venv")
    if not venv.exists():
        print("✗ 虚拟环境不存在，正在创建...")
        run("python3 -m venv venv")
    else:
        print("✓ 虚拟环境存在")

    # 3. 数据库迁移
    print("\n" + "=" * 70)
    print("  开始数据库迁移...")
    print("=" * 70)

    migrate_code = """
import sys
sys.path.insert(0, "/opt/CGCPT")

from models import init_db, SessionLocal, migrate_from_filesystem
from models import Prototype, Material, Algorithm, Task, ModelArtifact
from task_worker import register_builtin_algorithms

print("✓ 模块导入成功")

print("\\n初始化数据库表...")
init_db()
print("✓ 表创建成功")

print("\\n注册内置算法...")
db = SessionLocal()
try:
    register_builtin_algorithms(db)
    print("✓ 算法注册成功")

    print("\\n当前数据库统计（迁移前）:")
    print(f"  Prototype: {db.query(Prototype).count()}")
    print(f"  Material: {db.query(Material).count()}")
    print(f"  Algorithm: {db.query(Algorithm).filter_by(is_active=True).count()}")
    print(f"  Task: {db.query(Task).count()}")

    print("\\n执行文件系统迁移...")
    result = migrate_from_filesystem(db)
    print("\\n迁移结果:")
    print(f"  导入 Prototype: {result.get('imported_prototypes', 0)}")
    print(f"  导入 Material: {result.get('imported_materials', 0)}")
    print(f"  错误数: {result.get('total_errors', 0)}")

    print("\\n当前数据库统计（迁移后）:")
    print(f"  Prototype: {db.query(Prototype).count()}")
    print(f"  Material: {db.query(Material).count()}")
    print(f"  Algorithm: {db.query(Algorithm).filter_by(is_active=True).count()}")
    print(f"  Model: {db.query(ModelArtifact).filter_by(is_active=True).count()}")
    print(f"  Task: {db.query(Task).count()}")

    print("\\n" + "=" * 70)
    print("  迁移成功！")
    print("=" * 70)
finally:
    db.close()
"""

    run(f'/opt/CGCPT/venv/bin/python3 -c "{migrate_code}"')

    # 4. 重启服务
    print("\n" + "=" * 70)
    print("  重启服务...")
    print("=" * 70)

    print("\n重启 API 服务 (cgcpt)...")
    run("systemctl restart cgcpt")
    time.sleep(2)
    run("systemctl status cgcpt --no-pager | head -8")

    print("\n重启 Celery Worker (cgcpt-worker)...")
    run("systemctl restart cgcpt-worker")
    time.sleep(2)
    run("systemctl status cgcpt-worker --no-pager | head -8")

    # 5. 健康检查
    print("\n" + "=" * 70)
    print("  健康检查...")
    print("=" * 70)

    time.sleep(2)
    print("\n直接访问 API (5001 端口)...")
    run(
        "curl -s http://127.0.0.1:5000/api/health | python3 -m json.tool 2>/dev/null || "
        "curl -s http://127.0.0.1:5001/api/health | python3 -m json.tool"
    )

    print("\n访问数据库状态 API...")
    run(
        "curl -s http://127.0.0.1:5000/api/db/status | python3 -m json.tool 2>/dev/null || "
        "curl -s http://127.0.0.1:5001/api/db/status | python3 -m json.tool"
    )

    print("\n访问算法列表...")
    run(
        "curl -s http://127.0.0.1:5000/api/algorithms | python3 -m json.tool 2>/dev/null || "
        "curl -s http://127.0.0.1:5001/api/algorithms | python3 -m json.tool"
    )

    print("\n" + "=" * 70)
    print("  全部完成！🎉")
    print("=" * 70)
    print("\n下一步：在浏览器中访问：")
    print("  http://你的服务器IP/CGCPT/")
    print("  http://你的服务器IP/CGCPT/algorithms")


if __name__ == "__main__":
    main()
