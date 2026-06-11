import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stacking_analyzer

print("=" * 60)
print("CGCPT 堆垛识别 - 训练测试")
print("=" * 60)

print("\n[1/3] 扫描数据库CIF文件...")
t0 = time.time()
samples = stacking_analyzer.scan_database_cifs()
scan_time = time.time() - t0
print(f"  找到 {len(samples)} 个样本 (耗时 {scan_time:.1f}s)")

if not samples:
    print("ERROR: 没有找到CIF文件！")
    sys.exit(1)

topo_counts = {}
for s in samples:
    topo_counts[s["topology"]] = topo_counts.get(s["topology"], 0) + 1
print(f"  拓扑类型分布:")
for topo, cnt in sorted(topo_counts.items(), key=lambda x: -x[1]):
    print(f"    {topo}: {cnt}")

print("\n[2/3] 开始训练 (auto模式, 3轮迭代, 5折CV)...")
t0 = time.time()

progress_log = []


def on_progress(info):
    phase = info.get("phase", "")
    if phase == "init":
        print(
            f"  初始化: {info.get('n_samples',0)} 样本, {info.get('n_classes',0)} 类, {info.get('total_steps',0)} 步"
        )
    elif phase == "training":
        idx = info.get("config_idx", 0)
        total = info.get("total_steps", 0)
        if idx % 50 == 0 or idx == total:
            print(
                f"  进度: {idx}/{total} | 迭代 {info.get('iteration','?')}/{info.get('n_iterations','?')} | 当前: {info.get('current_model','?')} acc={info.get('current_acc',0):.4f} | 最佳: {info.get('best_acc_so_far',0):.4f}"
            )
    elif phase == "finalizing":
        print(f"  生成最终模型...")


result = stacking_analyzer.train_decision_tree(
    samples,
    test_ratio=0.2,
    model_type="auto",
    n_iterations=3,
    cv_folds=5,
    progress_callback=on_progress,
)
train_time = time.time() - t0

print(f"\n  训练耗时: {train_time:.1f}s")

if not result.get("success"):
    print(f"\n训练失败: {result.get('error', '未知错误')}")
    sys.exit(1)

bp = result["best_params"]
print(f"\n[3/3] 训练结果:")
print(f"  模型ID: {result['model_id']}")
print(f"  模型类型: {bp['model_type']} - {bp['model_name']}")
print(f"  测试集准确率: {bp['test_accuracy']*100:.2f}%")
print(f"  训练集准确率: {bp['train_accuracy']*100:.2f}%")
print(f"  交叉验证: {bp['cv_mean']*100:.2f}% ± {bp['cv_std']*100:.2f}%")
print(f"  训练/测试: {bp['n_train']}/{bp['n_test']}")
print(f"  最优种子: {bp['seed']}")
print(f"  有效样本: {result['n_valid_samples']}")
print(f"  类别数: {bp.get('n_classes', 'N/A')}")
print(f"  测试配置数: {result['n_configs_tested']}")

if result.get("model_comparison"):
    print(f"\n  模型对比:")
    for mt, info in sorted(result["model_comparison"].items(), key=lambda x: -x[1]["avg_acc"]):
        print(
            f"    {mt}: 最佳={info['best_acc']*100:.2f}% 平均={info['avg_acc']*100:.2f}% ({info['count']}次)"
        )

if result.get("feature_importances"):
    print(f"\n  特征重要性 Top 5:")
    for name, imp in result["feature_importances"][:5]:
        print(f"    {name}: {imp*100:.2f}%")

if result.get("confusion_matrix"):
    cm = result["confusion_matrix"]
    print(f"\n  混淆矩阵标签: {cm['labels']}")
    for i, row in enumerate(cm["matrix"]):
        print(f"    {cm['labels'][i]:>30s}: {row}")

print(f"\n{'='*60}")
print(f"最终准确率: {bp['test_accuracy']*100:.2f}%")
if bp["test_accuracy"] >= 0.95:
    print("✅ 准确率达标 (>=95%)")
elif bp["test_accuracy"] >= 0.90:
    print("⚠️ 准确率接近目标 (90-95%)，可尝试增加迭代次数")
else:
    print("❌ 准确率未达标 (<90%)，需要调整参数或增加数据")
print(f"{'='*60}")
