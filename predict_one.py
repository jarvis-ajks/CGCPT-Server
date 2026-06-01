#!/usr/bin/env python3
"""
CGCPT 堆垛特征识别 - 单文件预测
用法:
  python predict_one.py --model MODEL_ID --cif file.cif
  python predict_one.py --model MODEL_ID --cif-text "_symmetry..."
  python predict_one.py --list-models
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stacking_analyzer


def main():
    parser = argparse.ArgumentParser(description="CGCPT 堆垛特征预测")
    parser.add_argument("--model", type=str, default=None, help="模型ID")
    parser.add_argument("--cif", type=str, default=None, help="CIF文件路径")
    parser.add_argument("--cif-text", type=str, default=None, help="CIF文本内容")
    parser.add_argument("--list-models", action="store_true", help="列出可用模型")
    args = parser.parse_args()

    if args.list_models:
        models = stacking_analyzer.list_models()
        if not models:
            print("暂无可用模型，请先运行 train_oneclick.py 训练")
            return 0
        print(f"可用模型 ({len(models)} 个):")
        for m in models:
            print(f"  {m['model_id']}: 准确率={m['test_accuracy']*100:.1f}%, "
                  f"样本={m['n_samples']}, 类别={m['n_classes']}")
        return 0

    if not args.model:
        print("请指定模型ID (--model MODEL_ID)")
        print("使用 --list-models 查看可用模型")
        return 1

    cif_text = args.cif_text
    if args.cif:
        with open(args.cif, 'r', encoding='utf-8', errors='ignore') as f:
            cif_text = f.read()

    if not cif_text:
        print("请提供CIF文件 (--cif file.cif) 或CIF文本 (--cif-text '...')")
        return 1

    cif_data = stacking_analyzer.parse_cif_text(cif_text)
    if not cif_data:
        print("CIF文件解析失败，请检查格式")
        return 1

    result = stacking_analyzer.predict_stacking(args.model, cif_data)
    if not result.get('success'):
        print(f"预测失败: {result.get('error', '未知错误')}")
        return 1

    print("=" * 50)
    print("  堆垛特征预测结果")
    print("=" * 50)
    print(f"  预测拓扑: {result['predicted_topology']}")
    print(f"  置信度:   {result['confidence']*100:.1f}%")

    if result.get('top_predictions'):
        print(f"\n  Top 预测:")
        for topo, prob in result['top_predictions']:
            bar = "█" * int(prob * 30)
            print(f"    {topo:<40s} {prob*100:>6.1f}% {bar}")

    if result.get('layer_analysis'):
        print(f"\n  层分析 ({len(result['layer_analysis'])} 层):")
        for i, layer in enumerate(result['layer_analysis']):
            elems = ", ".join(f"{e}:{c}" for e, c in layer['elements'].items())
            print(f"    层{i+1}: z={layer['z']:.3f} 类型={layer['predicted_type']} "
                  f"({elems})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
