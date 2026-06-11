#!/usr/bin/env python3
"""
CGCPT 堆垛特征识别 - 一键训练脚本
用法:
  python train_oneclick.py                          # 使用默认database/目录
  python train_oneclick.py --data /path/to/cifs     # 指定数据目录
  python train_oneclick.py --data /path/to/cifs --test-ratio 0.2 --iterations 5 --model-type auto
  python train_oneclick.py --data /path/to/cifs --quick              # 快速模式(1轮迭代)
"""
import sys
import os
import argparse
import time
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stacking_analyzer


def main():
    parser = argparse.ArgumentParser(description="CGCPT 堆垛特征识别 - 一键训练")
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="CIF数据目录路径(每个子文件夹=一个类别，文件夹内放CIF文件)",
    )
    parser.add_argument("--test-ratio", type=float, default=0.2, help="测试集比例(默认0.2=20%%)")
    parser.add_argument("--iterations", type=int, default=3, help="迭代轮数/随机种子数(默认3)")
    parser.add_argument("--cv-folds", type=int, default=5, help="交叉验证折数(默认5)")
    parser.add_argument(
        "--model-type",
        type=str,
        default="auto",
        choices=["auto", "dt", "rf", "knn", "gb"],
        help="模型类型: auto=全部对比, dt=决策树, rf=随机森林, knn=KNN, gb=梯度提升",
    )
    parser.add_argument("--max-depth", type=int, default=None, help="决策树最大深度(默认自动搜索)")
    parser.add_argument("--quick", action="store_true", help="快速模式: 1轮迭代, 3折CV")
    parser.add_argument("--output", type=str, default=None, help="结果输出JSON文件路径(默认不保存)")
    args = parser.parse_args()

    if args.quick:
        args.iterations = 1
        args.cv_folds = 3

    data_dir = args.data
    if data_dir is None:
        data_dir = str(stacking_analyzer.DATABASE_DIR)

    print("=" * 70)
    print("  CGCPT 堆垛特征识别 - 一键训练")
    print("=" * 70)
    print(f"  数据目录: {data_dir}")
    print(f"  测试集比例: {args.test_ratio*100:.0f}%")
    print(f"  迭代轮数: {args.iterations}")
    print(f"  交叉验证: {args.cv_folds}折")
    print(f"  模型类型: {args.model_type}")
    print("=" * 70)

    print("\n[1/3] 扫描数据目录...")
    t0 = time.time()
    samples = stacking_analyzer.scan_database_cifs(data_dir)
    scan_time = time.time() - t0

    if not samples:
        print(f"\n❌ 错误: 在 {data_dir} 中没有找到CIF文件!")
        print("   请确保目录结构为:")
        print("   data_dir/")
        print("     ├── 类别A/")
        print("     │   ├── file1.cif")
        print("     │   └── file2.cif")
        print("     ├── 类别B/")
        print("     │   ├── file3.cif")
        print("     │   └── file4.cif")
        print("     └── ...")
        sys.exit(1)

    topo_counts = {}
    for s in samples:
        topo_counts[s["topology"]] = topo_counts.get(s["topology"], 0) + 1

    print(f"  找到 {len(samples)} 个样本 (耗时 {scan_time:.1f}s)")
    print(f"  类别分布 ({len(topo_counts)} 个类别):")
    for topo, cnt in sorted(topo_counts.items(), key=lambda x: -x[1]):
        pct = cnt / len(samples) * 100
        bar = "█" * int(pct / 2) + "░" * (25 - int(pct / 2))
        print(f"    {topo:>40s}: {cnt:>5d} ({pct:>5.1f}%) {bar}")

    min_count = min(topo_counts.values())
    if min_count < 3:
        print(f"\n❌ 错误: 有类别样本数不足3个，无法进行分层训练")
        for topo, cnt in topo_counts.items():
            if cnt < 3:
                print(f"   {topo}: 只有 {cnt} 个样本")
        sys.exit(1)

    print(f"\n[2/3] 开始训练...")
    print(f"  每个类别按 {args.test_ratio*100:.0f}% 比例分层抽样为测试集")
    print()

    t0 = time.time()

    def on_progress(info):
        phase = info.get("phase", "")
        if phase == "init":
            print(
                f"  初始化: {info.get('n_samples',0)} 样本, "
                f"{info.get('n_classes',0)} 类, "
                f"{info.get('total_steps',0)} 步待测"
            )
        elif phase == "training":
            idx = info.get("config_idx", 0)
            total = info.get("total_steps", 0)
            pct = idx / total * 100 if total > 0 else 0
            bar_len = 30
            filled = int(bar_len * idx / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_len - filled)
            print(
                f"\r  [{bar}] {pct:5.1f}% | "
                f"迭代{info.get('iteration','?')}/{info.get('n_iterations','?')} | "
                f"{info.get('current_model','?')[:30]} | "
                f"acc={info.get('current_acc',0):.4f} | "
                f"最佳={info.get('best_acc_so_far',0):.4f}",
                end="",
                flush=True,
            )
        elif phase == "finalizing":
            print(f"\n  生成最终模型...")

    result = stacking_analyzer.train_decision_tree(
        samples,
        test_ratio=args.test_ratio,
        max_depth=args.max_depth,
        model_type=args.model_type,
        n_iterations=args.iterations,
        cv_folds=args.cv_folds,
        progress_callback=on_progress,
        data_dir=data_dir,
    )
    train_time = time.time() - t0

    if not result.get("success"):
        print(f"\n❌ 训练失败: {result.get('error', '未知错误')}")
        sys.exit(1)

    bp = result["best_params"]
    print(f"\n\n[3/3] 训练结果 (耗时 {train_time:.1f}s)")
    print("=" * 70)
    print(f"  模型ID:     {result['model_id']}")
    print(f"  模型类型:   {bp['model_type'].upper()} - {bp['model_name']}")
    print(f"  ────────────────────────────────────────")
    print(f"  测试集准确率: {bp['test_accuracy']*100:.2f}%")
    print(f"  训练集准确率: {bp['train_accuracy']*100:.2f}%")
    print(f"  交叉验证:     {bp['cv_mean']*100:.2f}% ± {bp['cv_std']*100:.2f}%")
    print(f"  ────────────────────────────────────────")
    print(f"  训练/测试:    {bp['n_train']}/{bp['n_test']}")
    print(f"  类别数:       {bp['n_classes']}")
    print(f"  最优种子:     {bp['seed']}")
    print(f"  有效样本:     {result['n_valid_samples']}")
    print(f"  测试配置数:   {result['n_configs_tested']}")

    if result.get("model_comparison"):
        print(f"\n  模型对比:")
        print(f"  {'模型':>6s} | {'最佳准确率':>10s} | {'平均准确率':>10s} | {'测试次数':>8s}")
        print(f"  {'─'*6}─┼─{'─'*10}─┼─{'─'*10}─┼─{'─'*8}")
        for mt, info in sorted(result["model_comparison"].items(), key=lambda x: -x[1]["avg_acc"]):
            print(
                f"  {mt:>6s} | {info['best_acc']*100:>9.2f}% | {info['avg_acc']*100:>9.2f}% | {info['count']:>8d}"
            )

    if result.get("feature_importances"):
        print(f"\n  特征重要性 Top 10:")
        for i, (name, imp) in enumerate(result["feature_importances"][:10]):
            bar_len = int(imp * 50)
            bar = "█" * bar_len
            print(f"    {i+1:>2d}. {name:<25s} {imp*100:>6.2f}% {bar}")

    if result.get("confusion_matrix"):
        cm = result["confusion_matrix"]
        labels = cm["labels"]
        print(f"\n  混淆矩阵:")
        hdr_label = "真实\\预测"
        header = f"  {hdr_label:>30s} | " + " | ".join(f"{l[:12]:>12s}" for l in labels)
        print(header)
        sep = "─" * 30
        print(f"  {sep}─┼─{'─'*14}┼" * 1)
        for i, row in enumerate(cm["matrix"]):
            row_str = " | ".join(f"{v:>12d}" for v in row)
            print(f"  {labels[i][:30]:>30s} | {row_str}")

    print(f"\n{'='*70}")
    acc = bp["test_accuracy"]
    if acc >= 0.95:
        print(f"  ✅ 准确率 {acc*100:.2f}% - 达标 (>=95%)")
    elif acc >= 0.90:
        print(f"  ⚠️  准确率 {acc*100:.2f}% - 接近目标 (90-95%)")
        print(f"     建议: 增加迭代轮数(--iterations 5)或尝试不同模型(--model-type gb)")
    elif acc >= 0.80:
        print(f"  ⚠️  准确率 {acc*100:.2f}% - 需要改进 (80-90%)")
        print(f"     建议: 增加数据量、调整特征、增加迭代轮数")
    else:
        print(f"  ❌ 准确率 {acc*100:.2f}% - 未达标 (<80%)")
        print(f"     建议: 检查数据质量、增加样本量、调整分类粒度")
    print(f"{'='*70}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n  结果已保存到: {output_path}")

    print(f"\n  模型文件: {stacking_analyzer.MODEL_DIR / result['model_id']}.pkl")
    print(f"  可用于预测: python predict_one.py --model {result['model_id']} --cif test.cif")
    return 0


if __name__ == "__main__":
    sys.exit(main())
