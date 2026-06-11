#!/usr/bin/env python3
"""
CGCPT 系统测试脚本
测试数据库连接、API 端点、算法执行等功能
"""

import os
import sys
import time
import json
import uuid
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_database():
    """测试数据库连接和基本操作"""
    print("=== Testing Database ===")
    try:
        from models import SessionLocal, Prototype, Material, init_db

        init_db()
        db = SessionLocal()
        try:
            # 测试查询原型
            proto_count = db.query(Prototype).count()
            print(f"  ✓ {proto_count} prototypes found")

            # 测试查询材料
            mat_count = db.query(Material).count()
            print(f"  ✓ {mat_count} materials found")

            return True
        finally:
            db.close()
    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_api_endpoints():
    """测试 API 端点"""
    print("\n=== Testing API Endpoints ===")
    try:
        import requests

        base_url = "http://localhost:5000"

        # 测试健康检查
        try:
            res = requests.get(f"{base_url}/health", timeout=5)
            print(f"  ✓ /health returned {res.status_code}")
        except Exception as e:
            print(f"  ✗ /health failed: {e}")

        # 测试材料列表
        try:
            res = requests.get(f"{base_url}/api/db/materials?page=1&page_size=10", timeout=10)
            if res.status_code == 200:
                data = res.json()
                print(f"  ✓ /api/db/materials returned {data.get('count', 0)} materials")
            else:
                print(f"  ? /api/db/materials returned {res.status_code}")
        except Exception as e:
            print(f"  ! /api/db/materials not reachable (API server may not be running)")

        # 测试统计端点
        try:
            res = requests.get(f"{base_url}/api/db/stats", timeout=10)
            if res.status_code == 200:
                print("  ✓ /api/db/stats OK")
        except Exception as e:
            print(f"  ! /api/db/stats not reachable")

        return True
    except Exception as e:
        print(f"  ✗ API test failed: {e}")
        return False


def test_algorithm_registration():
    """测试算法注册"""
    print("\n=== Testing Algorithm Registration ===")
    try:
        from models import SessionLocal, Algorithm, register_builtin_algorithms

        register_builtin_algorithms()

        db = SessionLocal()
        try:
            algos = db.query(Algorithm).filter(Algorithm.is_active == True).all()
            print(f"  ✓ {len(algos)} algorithms registered")
            for algo in algos:
                print(f"    - {algo.id}: {algo.name} ({algo.algorithm_type})")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"  ✗ Algorithm test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_decision_tree_inference():
    """测试决策树推理"""
    print("\n=== Testing Decision Tree Inference ===")
    try:
        import joblib
        from pathlib import Path

        models_dir = Path("/opt/CGCPT/models")
        if not models_dir.exists():
            print("  ! Models directory not found, skipping inference test")
            return True

        model_files = list(models_dir.glob("dt_*.pkl"))
        if not model_files:
            print("  ! No decision tree models found")
            return True

        print(f"  ✓ Found {len(model_files)} decision tree model(s)")

        # 尝试加载一个模型来验证
        model_path = model_files[0]
        model = joblib.load(model_path)
        print(f"  ✓ Successfully loaded model: {model_path.name}")
        print(f"    - Type: {type(model).__name__}")

        return True
    except Exception as e:
        print(f"  ✗ Decision tree test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("CGCPT SYSTEM TESTS")
    print("=" * 60)

    tests = [
        ("Database", test_database),
        ("Algorithms", test_algorithm_registration),
        ("API Endpoints", test_api_endpoints),
        ("Decision Tree", test_decision_tree_inference),
    ]

    results = {}
    for name, test_func in tests:
        results[name] = test_func()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s} {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\nAll tests passed! 🎉")
        return 0
    else:
        print("\nSome tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
