# -*- coding: utf-8 -*-
"""
train_stacking_dt.py — 基于密堆积层状结构堆垛规则的决策树训练脚本

功能：
1. 利用 LayeredXOGenerator 的确定性堆垛逻辑，批量生成训练样本
2. 提取每层的上下文特征（层模式、相邻层信息、相邻主层堆垛等）
3. 训练 DecisionTreeClassifier 预测堆垛标签 (A/B/C)
4. 输出评估报告、特征重要性、决策树可视化
"""

import sys
import os
import itertools
import numpy as np

from sklearn.tree import DecisionTreeClassifier, export_text, export_graphviz
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    from layer_generator import LayeredXOGenerator
except ImportError:
    from stack_main import LayeredXOGenerator

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

MODE_LIST = ["XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6", "M6", "M7", "T"]
MODE_TO_IDX = {m: i for i, m in enumerate(MODE_LIST)}
SHIFT_TO_IDX = {"A": 0, "B": 1, "C": 2}
IDX_TO_SHIFT = {0: "A", 1: "B", 2: "C"}

MAIN_MODES = {"XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6"}
X_MODES = {"XO", "XO2", "XO3", "X", "XBO3", "XB3O6"}
M_MODES = {"M6", "M7"}

STACK_SEQUENCES = ["ABC", "AB", "ACB", "AAB", "ABB", "AA", "ABCA", "ABCAB", "ABCB"]


def is_valid_layer_sequence(modes):
    if not modes:
        return False
    has_main = any(m in MAIN_MODES for m in modes)
    if not has_main:
        return False
    for i, m in enumerate(modes):
        if m in M_MODES:
            left = modes[(i - 1) % len(modes)]
            right = modes[(i + 1) % len(modes)]
            if left not in MAIN_MODES and right not in MAIN_MODES:
                return False
    return True


def generate_layer_sequences():
    main_pool = ["XO3", "XO2", "XO", "XBO3", "XB3O6", "BO3", "X"]
    m_pool = ["M7", "M6"]
    sequences = []

    for n_main in range(2, 6):
        for main_combo in itertools.combinations_with_replacement(main_pool, n_main):
            for perm in set(itertools.permutations(main_combo)):
                for n_m in range(0, min(3, n_main)):
                    for m_positions in itertools.combinations(range(1, len(perm)), n_m):
                        modes = list(perm)
                        offset = 0
                        for pos in m_positions:
                            m_type = m_pool[np.random.randint(0, len(m_pool))]
                            modes.insert(pos + offset, m_type)
                            offset += 1
                        if is_valid_layer_sequence(modes):
                            sequences.append(tuple(modes))

    unique = list(set(sequences))
    return unique


def extract_features_for_layer(layer_modes, shift_sequence, idx, gen):
    n = len(layer_modes)
    mode = layer_modes[idx]
    prev_mode = layer_modes[(idx - 1) % n]
    next_mode = layer_modes[(idx + 1) % n]

    is_main = 1 if mode in MAIN_MODES else 0
    is_x = 1 if mode in X_MODES else 0
    is_m = 1 if mode in M_MODES else 0
    is_t = 1 if mode == "T" else 0

    prev_is_main = 1 if prev_mode in MAIN_MODES else 0
    next_is_main = 1 if next_mode in MAIN_MODES else 0
    prev_is_xb3o6 = 1 if prev_mode == "XB3O6" else 0
    next_is_xb3o6 = 1 if next_mode == "XB3O6" else 0

    lower_main_shift = -1
    upper_main_shift = -1
    search = (idx - 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in MAIN_MODES:
            lower_main_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search - 1) % n
        steps += 1

    search = (idx + 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in MAIN_MODES:
            upper_main_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search + 1) % n
        steps += 1

    between_xb3o6 = 0
    if mode in M_MODES:
        try:
            between_xb3o6 = 1 if gen.is_m_layer_between_xb3o6(idx, layer_modes) else 0
        except Exception:
            between_xb3o6 = 0

    n_main_in_seq = sum(1 for m in layer_modes if m in MAIN_MODES)
    n_x_in_seq = sum(1 for m in layer_modes if m in X_MODES)
    seq_len = n

    x_layer_position = 0
    for k in range(idx):
        if layer_modes[k] in X_MODES:
            x_layer_position += 1
    if mode not in X_MODES:
        x_layer_position = -1

    prev_x_shift = -1
    search = (idx - 1) % n
    steps = 0
    while steps < n:
        if layer_modes[search] in X_MODES and shift_sequence[search] is not None:
            prev_x_shift = SHIFT_TO_IDX.get(shift_sequence[search], -1)
            break
        search = (search - 1) % n
        steps += 1

    return [
        MODE_TO_IDX.get(mode, 0),
        is_main,
        is_x,
        is_m,
        is_t,
        MODE_TO_IDX.get(prev_mode, 0),
        MODE_TO_IDX.get(next_mode, 0),
        prev_is_main,
        next_is_main,
        prev_is_xb3o6,
        next_is_xb3o6,
        lower_main_shift,
        upper_main_shift,
        between_xb3o6,
        n_main_in_seq,
        n_x_in_seq,
        seq_len,
        x_layer_position,
        prev_x_shift,
    ]


FEATURE_NAMES = [
    "current_mode",
    "is_main_layer",
    "is_x_layer",
    "is_m_layer",
    "is_t_layer",
    "prev_mode",
    "next_mode",
    "prev_is_main",
    "next_is_main",
    "prev_is_xb3o6",
    "next_is_xb3o6",
    "lower_main_shift",
    "upper_main_shift",
    "between_xb3o6",
    "n_main_in_seq",
    "n_x_in_seq",
    "seq_len",
    "x_layer_position",
    "prev_x_shift",
]


def generate_training_data(max_sequences=500):
    gen = LayeredXOGenerator(enable_t=True)
    sequences = generate_layer_sequences()

    if len(sequences) > max_sequences:
        indices = np.random.choice(len(sequences), max_sequences, replace=False)
        sequences = [sequences[i] for i in indices]

    X_data = []
    y_data = []

    for layer_modes in sequences:
        layer_modes = list(layer_modes)
        n_x = sum(1 for m in layer_modes if m in X_MODES)
        if n_x == 0:
            continue

        for stack_seq in STACK_SEQUENCES:
            try:
                shift_seq, _ = gen.build_full_shift_sequence_without_T(layer_modes, stack_seq)

                layer_angles = [0.0] * len(layer_modes)
                layer_dxs = [0.0] * len(layer_modes)
                layer_dys = [0.0] * len(layer_modes)
                alphas = [1.0] * sum(1 for m in layer_modes if m in MAIN_MODES)
                z_seq, _ = gen.build_z_sequence_without_T(layer_modes, alphas)

                if gen.enable_t:
                    result = gen.insert_T_layers(
                        layer_modes, shift_seq, z_seq, layer_angles, layer_dxs, layer_dys
                    )
                    final_modes = result[0]
                    final_shifts = result[1]
                else:
                    final_modes = layer_modes
                    final_shifts = shift_seq

                for i in range(len(final_modes)):
                    features = extract_features_for_layer(final_modes, final_shifts, i, gen)
                    label = SHIFT_TO_IDX.get(final_shifts[i], -1)
                    if label >= 0:
                        X_data.append(features)
                        y_data.append(label)

            except Exception:
                continue

    return np.array(X_data), np.array(y_data)


def train_and_evaluate():
    print("=" * 60)
    print("  CGCPT 堆垛预测决策树训练")
    print("=" * 60)

    print("\n[1/4] 生成训练数据...")
    X, y = generate_training_data(max_sequences=500)
    print(f"  总样本数: {len(X)}")
    print(f"  特征维度: {X.shape[1]}")
    print(f"  标签分布: A={sum(y == 0)}, B={sum(y == 1)}, C={sum(y == 2)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  训练集: {len(X_train)}, 测试集: {len(X_test)}")

    print("\n[2/4] 训练决策树...")
    clf = DecisionTreeClassifier(max_depth=10, min_samples_leaf=5, random_state=42)
    clf.fit(X_train, y_train)

    cv_scores = cross_val_score(clf, X_train, y_train, cv=5, scoring="accuracy")
    print(f"  5折交叉验证准确率: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    print("\n[3/4] 测试集评估...")
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"  测试集准确率: {acc:.4f}")
    print("\n  分类报告:")
    print(classification_report(y_test, y_pred, target_names=["A", "B", "C"]))
    print("  混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"    {'':>6} {'Pred_A':>7} {'Pred_B':>7} {'Pred_C':>7}")
    for i, row in enumerate(cm):
        print(f"    {'Real_' + IDX_TO_SHIFT[i]:>6} {row[0]:>7} {row[1]:>7} {row[2]:>7}")

    print("\n  特征重要性排序:")
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i, idx in enumerate(indices):
        if importances[idx] > 0:
            print(f"    {i + 1}. {FEATURE_NAMES[idx]:>20s}: {importances[idx]:.4f}")

    print("\n[4/4] 输出决策树规则...")
    tree_text = export_text(clf, feature_names=FEATURE_NAMES, max_depth=6)
    print(tree_text[:3000])
    if len(tree_text) > 3000:
        print("  ... (已截断，完整规则已保存至 stacking_dt_rules.txt)")

    with open(os.path.join(OUTPUT_DIR, "stacking_dt_rules.txt"), "w", encoding="utf-8") as f:
        f.write(tree_text)
    print("  完整决策树规则已保存: stacking_dt_rules.txt")

    plt.figure(figsize=(24, 14))
    from sklearn.tree import plot_tree
    plot_tree(
        clf,
        feature_names=FEATURE_NAMES,
        class_names=["A", "B", "C"],
        filled=True,
        rounded=True,
        fontsize=7,
        max_depth=6,
    )
    plt.title("CGCPT Stacking Prediction Decision Tree", fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "stacking_dt_visualization.png"), dpi=150)
    print("  决策树可视化已保存: stacking_dt_visualization.png")

    import json
    model_info = {
        "model_type": "DecisionTreeClassifier",
        "max_depth": int(clf.get_depth()),
        "n_leaves": int(clf.get_n_leaves()),
        "n_features": int(X.shape[1]),
        "feature_names": FEATURE_NAMES,
        "test_accuracy": float(acc),
        "cv_accuracy_mean": float(cv_scores.mean()),
        "cv_accuracy_std": float(cv_scores.std()),
        "feature_importances": {
            FEATURE_NAMES[i]: float(importances[i]) for i in range(len(importances))
        },
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
    }
    with open(os.path.join(OUTPUT_DIR, "stacking_dt_info.json"), "w", encoding="utf-8") as f:
        json.dump(model_info, f, indent=2, ensure_ascii=False)
    print("  模型信息已保存: stacking_dt_info.json")

    print("\n" + "=" * 60)
    print("  训练完成！")
    print("=" * 60)

    return clf, acc


def predict_stacking(clf, layer_modes, stack_sequence_text="ABC"):
    gen = LayeredXOGenerator(enable_t=True)
    shift_seq, _ = gen.build_full_shift_sequence_without_T(layer_modes, stack_sequence_text)

    layer_angles = [0.0] * len(layer_modes)
    layer_dxs = [0.0] * len(layer_modes)
    layer_dys = [0.0] * len(layer_modes)
    alphas = [1.0] * sum(1 for m in layer_modes if m in MAIN_MODES)
    z_seq, _ = gen.build_z_sequence_without_T(layer_modes, alphas)

    if gen.enable_t:
        result = gen.insert_T_layers(
            layer_modes, shift_seq, z_seq, layer_angles, layer_dxs, layer_dys
        )
        final_modes = result[0]
        final_shifts = result[1]
    else:
        final_modes = layer_modes
        final_shifts = shift_seq

    predictions = []
    for i in range(len(final_modes)):
        features = extract_features_for_layer(final_modes, final_shifts, i, gen)
        pred = clf.predict([features])[0]
        predictions.append(IDX_TO_SHIFT[pred])

    print("\n预测结果 vs 规则结果:")
    print(f"  {'层序号':>6} {'模式':>8} {'规则堆垛':>8} {'预测堆垛':>8} {'匹配':>6}")
    correct = 0
    for i in range(len(final_modes)):
        rule_shift = final_shifts[i]
        pred_shift = predictions[i]
        match = "✓" if rule_shift == pred_shift else "✗"
        if rule_shift == pred_shift:
            correct += 1
        print(f"  {i:>6} {final_modes[i]:>8} {rule_shift:>8} {pred_shift:>8} {match:>6}")
    print(f"  准确率: {correct}/{len(final_modes)} = {correct / len(final_modes):.2%}")

    return predictions


if __name__ == "__main__":
    clf, acc = train_and_evaluate()

    print("\n\n===== 示例预测 =====")
    test_modes = ["XO3", "M7", "XO3", "M7", "XO2"]
    print(f"层模式: {test_modes}")
    predict_stacking(clf, test_modes, "ABC")

    test_modes2 = ["XBO3", "M7", "XB3O6", "M7", "XBO3"]
    print(f"\n层模式: {test_modes2}")
    predict_stacking(clf, test_modes2, "ABC")
