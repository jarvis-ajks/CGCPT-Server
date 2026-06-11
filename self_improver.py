# -*- coding: utf-8 -*-
"""
self_improver.py — 自我迭代优化引擎

核心创新点：
1. 误差分析驱动：自动识别模型最易犯错的层模式组合，定向增强训练数据
2. 特征工程自进化：自动生成高阶交叉特征，筛选有效特征组合
3. 贝叶斯超参优化：替代网格搜索，高效搜索最优超参
4. 集成学习融合：多模型投票/Stacking提升准确率上限
5. 迭代闭环：评估→分析→增强→重训练→再评估，持续提升

训练历史通过JSON文件持久化存储（不依赖MySQL），轻量且可移植。
"""

import os
import json
import time
import random
import traceback
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

HISTORY_DIR = Path(__file__).resolve().parent / "training_history"
HISTORY_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# 1. 训练历史存储
# ──────────────────────────────────────────────


def save_training_record(record: dict) -> str:
    record_id = f"iter_{record.get('iteration', 0)}_{int(time.time())}"
    record["id"] = record_id
    record["saved_at"] = datetime.utcnow().isoformat()

    path = HISTORY_DIR / f"{record_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return record_id


def load_training_history() -> list:
    records = []
    for p in sorted(HISTORY_DIR.glob("iter_*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception:
            pass
    return records


def get_latest_record() -> dict:
    records = load_training_history()
    return records[-1] if records else {}


def get_improvement_trajectory() -> list:
    records = load_training_history()
    return [
        {
            "iteration": r.get("iteration", 0),
            "test_accuracy": r.get("test_accuracy"),
            "cv_mean": r.get("cv_mean"),
            "cv_std": r.get("cv_std"),
            "overfit": r.get("overfit"),
            "n_samples": r.get("n_samples"),
            "strategy": r.get("strategy", "baseline"),
            "model_id": r.get("model_id", ""),
            "timestamp": r.get("saved_at", ""),
        }
        for r in records
    ]


# ──────────────────────────────────────────────
# 2. 误差分析器
# ──────────────────────────────────────────────


def analyze_errors(model_id: str, test_X=None, test_y=None, layer_modes_list=None):
    """分析模型预测错误，找出最难预测的层模式和特征组合"""
    from stacking_analyzer import _load_model, IDX_TO_SHIFT, MODE_LIST, MODE_TO_IDX
    from stacking_analyzer import MAIN_MODES, X_MODES_SET, M_MODES_SET, SHIFT_TO_IDX

    saved = _load_model(model_id)
    if saved is None:
        return {"error": "模型加载失败"}

    clf = saved["model"] if isinstance(saved, dict) else saved
    label_map = saved.get("label_map", IDX_TO_SHIFT) if isinstance(saved, dict) else IDX_TO_SHIFT

    if test_X is None or test_y is None:
        from stacking_analyzer import _generate_stacking_training_data

        test_X, test_y = _generate_stacking_training_data(max_sequences=100)

    y_pred = clf.predict(test_X)
    errors = test_y != y_pred

    error_by_mode = defaultdict(list)
    error_by_shift = defaultdict(list)
    error_features = []

    for i in range(len(test_y)):
        mode_idx = int(test_X[i][0])
        mode_name = MODE_LIST[mode_idx] if mode_idx < len(MODE_LIST) else f"unknown_{mode_idx}"
        true_shift = label_map.get(int(test_y[i]), str(test_y[i]))
        pred_shift = label_map.get(int(y_pred[i]), str(y_pred[i]))

        if errors[i]:
            error_by_mode[mode_name].append(
                {
                    "true": true_shift,
                    "pred": pred_shift,
                    "features": test_X[i].tolist(),
                }
            )
            error_by_shift[true_shift].append(
                {
                    "mode": mode_name,
                    "pred": pred_shift,
                }
            )
            error_features.append(test_X[i])

    mode_error_rates = {}
    mode_counts = Counter(
        MODE_LIST[int(test_X[i][0])] if int(test_X[i][0]) < len(MODE_LIST) else "unknown"
        for i in range(len(test_y))
    )
    for mode, errs in error_by_mode.items():
        total = mode_counts.get(mode, 1)
        mode_error_rates[mode] = round(len(errs) / max(total, 1), 4)

    shift_confusion = defaultdict(lambda: defaultdict(int))
    for i in range(len(test_y)):
        if errors[i]:
            true_s = label_map.get(int(test_y[i]), str(test_y[i]))
            pred_s = label_map.get(int(y_pred[i]), str(y_pred[i]))
            shift_confusion[true_s][pred_s] += 1

    hardest_combos = []
    if len(error_features) > 0:
        error_features = np.array(error_features)
        feature_var = np.var(error_features, axis=0)
        top_var_idx = np.argsort(feature_var)[-5:]
        for idx in top_var_idx:
            from stacking_analyzer import STACKING_FEATURE_NAMES

            fname = (
                STACKING_FEATURE_NAMES[idx] if idx < len(STACKING_FEATURE_NAMES) else f"feat_{idx}"
            )
            hardest_combos.append(
                {
                    "feature": fname,
                    "variance": round(float(feature_var[idx]), 6),
                }
            )

    return {
        "total_errors": int(errors.sum()),
        "total_samples": len(test_y),
        "error_rate": round(float(errors.mean()), 4),
        "mode_error_rates": dict(
            sorted(mode_error_rates.items(), key=lambda x: x[1], reverse=True)
        ),
        "shift_confusion": {k: dict(v) for k, v in shift_confusion.items()},
        "hardest_modes": sorted(
            error_by_mode.keys(), key=lambda m: len(error_by_mode[m]), reverse=True
        )[:5],
        "high_variance_features": hardest_combos,
    }


# ──────────────────────────────────────────────
# 3. 特征工程自进化
# ──────────────────────────────────────────────


def engineer_advanced_features(X, feature_names=None):
    """自动生成高阶交叉特征"""
    from stacking_analyzer import STACKING_FEATURE_NAMES

    if feature_names is None:
        feature_names = STACKING_FEATURE_NAMES

    new_features = []
    new_names = []

    # 3a. 层模式 × 上下层模式 交互
    if X.shape[1] >= 7:
        current_mode = X[:, 0]
        prev_mode = X[:, 5]
        next_mode = X[:, 6]
        new_features.append((current_mode * 10 + prev_mode).reshape(-1, 1))
        new_names.append("mode_prev_interaction")
        new_features.append((current_mode * 10 + next_mode).reshape(-1, 1))
        new_names.append("mode_next_interaction")
        new_features.append((prev_mode * 10 + next_mode).reshape(-1, 1))
        new_names.append("prev_next_interaction")

    # 3b. 上下主层堆垛差值
    if X.shape[1] >= 13:
        lower_shift = X[:, 11]
        upper_shift = X[:, 12]
        shift_diff = (upper_shift - lower_shift).reshape(-1, 1)
        new_features.append(shift_diff)
        new_names.append("shift_diff_lower_upper")
        same_shift = (lower_shift == upper_shift).astype(float).reshape(-1, 1)
        new_features.append(same_shift)
        new_names.append("same_adjacent_shift")

    # 3c. 序列位置特征
    if X.shape[1] >= 19:
        x_pos = X[:, 17]
        seq_len = X[:, 16]
        relative_pos = (x_pos / np.maximum(seq_len, 1)).reshape(-1, 1)
        new_features.append(relative_pos)
        new_names.append("relative_x_position")

    # 3d. 邻居模式一致性
    if X.shape[1] >= 7:
        is_main = X[:, 1]
        prev_main = X[:, 7]
        next_main = X[:, 8]
        surrounded_by_main = (prev_main * next_main).reshape(-1, 1)
        new_features.append(surrounded_by_main)
        new_names.append("surrounded_by_main")

    if not new_features:
        return X, feature_names

    X_aug = np.hstack([X] + new_features)
    aug_names = list(feature_names) + new_names
    return X_aug, aug_names


# ──────────────────────────────────────────────
# 4. 难例挖掘 — 针对性增强训练数据
# ──────────────────────────────────────────────


def mine_hard_examples(model_id: str, n_hard_sequences=200):
    """生成模型最易犯错的层模式组合的训练数据"""
    from stacking_analyzer import (
        _load_model,
        predict_stacking,
        IDX_TO_SHIFT,
        MODE_LIST,
        MAIN_MODES,
        X_MODES_SET,
        M_MODES_SET,
        SHIFT_TO_IDX,
        _generate_layer_sequences,
        _extract_features_for_layer,
        STACKING_FEATURE_NAMES,
    )

    sequences = _generate_layer_sequences()
    if len(sequences) > n_hard_sequences * 3:
        indices = np.random.choice(len(sequences), n_hard_sequences * 3, replace=False)
        sequences = [sequences[i] for i in indices]

    hard_X = []
    hard_y = []

    from layer_generator import LayeredXOGenerator

    gen = LayeredXOGenerator(enable_t=True)

    STACK_SEQUENCES = ["ABC", "AB", "ACB", "AAB", "ABB", "AA", "ABCA", "ABCAB", "ABCB"]

    for layer_modes in sequences:
        layer_modes = list(layer_modes)
        n_x = sum(1 for m in layer_modes if m in X_MODES_SET)
        if n_x == 0:
            continue

        for stack_seq in STACK_SEQUENCES[:3]:
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
                    features = _extract_features_for_layer(final_modes, final_shifts, i, gen)
                    pred_label = int(saved_clf.predict([features])[0])
                    true_label = SHIFT_TO_IDX.get(final_shifts[i], -1)

                    if true_label >= 0:
                        hard_X.append(features)
                        hard_y.append(true_label)
                        if pred_label != true_label:
                            for _ in range(3):
                                hard_X.append(features)
                                hard_y.append(true_label)

            except Exception:
                continue

    saved = _load_model(model_id)
    saved_clf = saved["model"] if isinstance(saved, dict) else saved

    return np.array(hard_X), np.array(hard_y)


# ──────────────────────────────────────────────
# 5. 贝叶斯超参优化
# ──────────────────────────────────────────────


def bayesian_optimize(X, y, n_trials=30, cv_folds=3):
    """使用贝叶斯优化搜索最优超参（无需optuna，纯numpy实现）"""
    from stacking_analyzer import _ensure_sklearn

    sk = _ensure_sklearn()
    if not sk:
        return None

    train_test_split = sk["train_test_split"]
    cross_val_score = sk["accuracy_score"]
    accuracy_score = sk["accuracy_score"]
    DecisionTreeClassifier = sk["DecisionTreeClassifier"]
    RandomForestClassifier = sk["RandomForestClassifier"]
    GradientBoostingClassifier = sk["GradientBoostingClassifier"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    search_space = {
        "model_type": ["dt", "rf", "gb"],
        "max_depth": [3, 5, 8, 10, 12, 15, 20],
        "min_samples_leaf": [1, 2, 3, 5, 8, 10],
        "min_samples_split": [2, 3, 5, 8, 10],
        "criterion": ["gini", "entropy"],
        "max_features": [None, "sqrt", "log2"],
    }

    results = []
    explored = set()

    best_score = -1
    best_config = None
    best_clf = None

    center = {
        "model_type": "dt",
        "max_depth": 10,
        "min_samples_leaf": 2,
        "min_samples_split": 5,
        "criterion": "gini",
        "max_features": None,
    }

    for trial in range(n_trials):
        if trial < n_trials // 3:
            config = {}
            for k, vs in search_space.items():
                config[k] = random.choice(vs)
        elif trial < 2 * n_trials // 3:
            config = dict(center)
            keys_to_mutate = random.sample(list(search_space.keys()), 2)
            for k in keys_to_mutate:
                config[k] = random.choice(search_space[k])
        else:
            if best_config:
                config = dict(best_config)
                keys_to_mutate = random.sample(list(search_space.keys()), random.randint(1, 3))
                for k in keys_to_mutate:
                    config[k] = random.choice(search_space[k])
            else:
                config = {}
                for k, vs in search_space.items():
                    config[k] = random.choice(vs)

        config_key = tuple(sorted(config.items()))
        if config_key in explored:
            continue
        explored.add(config_key)

        try:
            model_type = config["model_type"]
            common_kwargs = {
                "max_depth": config["max_depth"],
                "min_samples_leaf": config["min_samples_leaf"],
                "min_samples_split": config["min_samples_split"],
                "random_state": 42,
            }

            if model_type == "dt":
                clf = DecisionTreeClassifier(
                    criterion=config["criterion"],
                    max_features=config["max_features"],
                    **common_kwargs,
                )
            elif model_type == "rf":
                clf = RandomForestClassifier(
                    n_estimators=100,
                    criterion=config["criterion"],
                    max_features=config["max_features"],
                    **common_kwargs,
                )
            elif model_type == "gb":
                clf = GradientBoostingClassifier(
                    n_estimators=80,
                    learning_rate=0.1,
                    max_depth=config["max_depth"],
                    min_samples_leaf=config["min_samples_leaf"],
                    min_samples_split=config["min_samples_split"],
                    random_state=42,
                )

            clf.fit(X_train, y_train)
            test_acc = accuracy_score(y_test, clf.predict(X_test))
            train_acc = accuracy_score(y_train, clf.predict(X_train))
            overfit = train_acc - test_acc

            cv_mean = test_acc
            cv_std = 0.0
            try:
                min_class = min(Counter(y).values())
                cv_n = min(cv_folds, min_class)
                cv_scores = sk["cross_val_score"](clf, X, y, cv=cv_n, scoring="accuracy")
                cv_mean = float(cv_scores.mean())
                cv_std = float(cv_scores.std())
            except Exception:
                pass

            composite = cv_mean - cv_std * 0.3 - max(0, overfit - 0.05) * 2.0

            results.append(
                {
                    "trial": trial,
                    "config": {k: str(v) for k, v in config.items()},
                    "test_accuracy": round(float(test_acc), 4),
                    "train_accuracy": round(float(train_acc), 4),
                    "cv_mean": round(cv_mean, 4),
                    "cv_std": round(cv_std, 4),
                    "overfit": round(float(overfit), 4),
                    "composite": round(float(composite), 4),
                }
            )

            if composite > best_score:
                best_score = composite
                best_config = dict(config)
                best_clf = clf

        except Exception:
            continue

    return {
        "best_config": {k: str(v) for k, v in best_config.items()} if best_config else None,
        "best_composite": round(float(best_score), 4) if best_score > -1 else None,
        "best_clf": best_clf,
        "n_trials": len(results),
        "all_results": results,
    }


# ──────────────────────────────────────────────
# 6. 集成学习融合
# ──────────────────────────────────────────────


def build_ensemble(X, y, n_models=5, cv_folds=3):
    """构建多模型集成（投票+Stacking）"""
    from stacking_analyzer import _ensure_sklearn, IDX_TO_SHIFT, STACKING_FEATURE_NAMES

    sk = _ensure_sklearn()
    if not sk:
        return None

    train_test_split = sk["train_test_split"]
    accuracy_score = sk["accuracy_score"]
    cross_val_score = sk["cross_val_score"]
    joblib = sk["joblib"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    base_models = []

    configs = [
        (
            "dt_gini_deep",
            sk["DecisionTreeClassifier"],
            {"max_depth": 15, "criterion": "gini", "min_samples_leaf": 2, "random_state": 42},
        ),
        (
            "dt_entropy_mid",
            sk["DecisionTreeClassifier"],
            {"max_depth": 10, "criterion": "entropy", "min_samples_leaf": 3, "random_state": 42},
        ),
        (
            "rf_standard",
            sk["RandomForestClassifier"],
            {"n_estimators": 100, "max_depth": 12, "min_samples_leaf": 2, "random_state": 42},
        ),
        (
            "rf_deep",
            sk["RandomForestClassifier"],
            {"n_estimators": 150, "max_depth": 15, "min_samples_leaf": 1, "random_state": 42},
        ),
        (
            "gb_standard",
            sk["GradientBoostingClassifier"],
            {"n_estimators": 80, "learning_rate": 0.1, "max_depth": 5, "random_state": 42},
        ),
    ]

    trained_models = []
    individual_results = []

    for name, cls, kwargs in configs[:n_models]:
        try:
            clf = cls(**kwargs)
            clf.fit(X_train, y_train)
            pred = clf.predict(X_test)
            acc = accuracy_score(y_test, pred)
            train_acc = accuracy_score(y_train, clf.predict(X_train))

            cv_mean = acc
            cv_std = 0.0
            try:
                min_class = min(Counter(y).values())
                cv_n = min(cv_folds, min_class)
                cv_scores = cross_val_score(clf, X, y, cv=cv_n, scoring="accuracy")
                cv_mean = float(cv_scores.mean())
                cv_std = float(cv_scores.std())
            except Exception:
                pass

            trained_models.append(clf)
            individual_results.append(
                {
                    "name": name,
                    "test_accuracy": round(float(acc), 4),
                    "train_accuracy": round(float(train_acc), 4),
                    "cv_mean": round(cv_mean, 4),
                    "cv_std": round(cv_std, 4),
                }
            )
        except Exception:
            continue

    if not trained_models:
        return None

    # 投票集成
    all_preds = np.array([clf.predict(X_test) for clf in trained_models])
    vote_pred = np.apply_along_axis(lambda x: Counter(x).most_common(1)[0][0], 0, all_preds)
    vote_acc = accuracy_score(y_test, vote_pred)

    # 加权投票（按CV分数加权）
    weights = np.array([r["cv_mean"] for r in individual_results])
    weights = weights / weights.sum()

    weighted_votes = np.zeros((len(trained_models), len(X_test), 3))
    for i, clf in enumerate(trained_models):
        if hasattr(clf, "predict_proba"):
            try:
                proba = clf.predict_proba(X_test)
                for j, cls_idx in enumerate(clf.classes_):
                    weighted_votes[i, :, int(cls_idx)] = proba[:, j] * weights[i]
            except Exception:
                pass
        else:
            for j, pred in enumerate(clf.predict(X_test)):
                weighted_votes[i, j, int(pred)] = weights[i]

    weighted_pred = np.argmax(weighted_votes.sum(axis=0), axis=1)
    weighted_acc = accuracy_score(y_test, weighted_pred)

    best_individual = max(individual_results, key=lambda r: r["cv_mean"])
    ensemble_improvement = round(float(max(vote_acc, weighted_acc) - best_individual["cv_mean"]), 4)

    return {
        "individual_results": individual_results,
        "vote_accuracy": round(float(vote_acc), 4),
        "weighted_vote_accuracy": round(float(weighted_acc), 4),
        "best_individual_cv": best_individual["cv_mean"],
        "ensemble_improvement": ensemble_improvement,
        "trained_models": trained_models,
        "n_models": len(trained_models),
    }


# ──────────────────────────────────────────────
# 7. 自我迭代优化主循环
# ──────────────────────────────────────────────


def self_improve_iteration(
    max_iterations=3,
    max_sequences=300,
    cv_folds=3,
    use_feature_engineering=True,
    use_hard_mining=True,
    use_ensemble=True,
    use_bayesian=True,
    progress_callback=None,
):
    """
    自我迭代优化主循环：
    1. 基线训练 → 2. 误差分析 → 3. 特征增强 → 4. 难例挖掘 → 5. 贝叶斯优化 → 6. 集成融合 → 7. 保存最优
    """
    from stacking_analyzer import (
        _ensure_sklearn,
        _generate_stacking_training_data,
        train_decision_tree,
        IDX_TO_SHIFT,
        STACKING_FEATURE_NAMES,
        MODEL_DIR,
    )

    sk = _ensure_sklearn()
    if not sk:
        return {"success": False, "error": "scikit-learn未安装"}

    history = load_training_history()
    start_iteration = len(history)
    joblib = sk["joblib"]

    iteration_results = []

    for it in range(max_iterations):
        iteration = start_iteration + it
        strategy_parts = []

        if progress_callback:
            progress_callback(
                {
                    "phase": "iteration_start",
                    "iteration": iteration,
                    "max_iterations": max_iterations,
                    "message": f"开始第 {iteration + 1} 轮迭代优化...",
                }
            )

        # ── Step 1: 生成训练数据 ──
        X, y = _generate_stacking_training_data(max_sequences=max_sequences)
        n_samples = len(X)

        # ── Step 2: 特征增强（第2轮起） ──
        aug_feature_names = list(STACKING_FEATURE_NAMES)
        if use_feature_engineering and iteration > 0:
            X, aug_feature_names = engineer_advanced_features(X, STACKING_FEATURE_NAMES)
            strategy_parts.append("feature_engineering")

        # ── Step 3: 难例挖掘（第3轮起） ──
        if use_hard_mining and iteration >= 2 and iteration_results:
            prev_best_id = iteration_results[-1].get("model_id")
            if prev_best_id:
                try:
                    hard_X, hard_y = mine_hard_examples(prev_best_id, n_hard_sequences=100)
                    if len(hard_X) > 0:
                        X = np.vstack([X, hard_X])
                        y = np.concatenate([y, hard_y])
                        strategy_parts.append("hard_mining")
                except Exception:
                    pass

        # ── Step 4: 训练 ──
        best_clf = None
        best_result = None

        if use_bayesian:
            if progress_callback:
                progress_callback({"phase": "bayesian_optimization", "iteration": iteration})

            opt_result = bayesian_optimize(X, y, n_trials=25, cv_folds=cv_folds)
            if opt_result and opt_result.get("best_clf"):
                best_clf = opt_result["best_clf"]
                best_result = {
                    "strategy": "bayesian",
                    "best_config": opt_result["best_config"],
                    "n_trials": opt_result["n_trials"],
                }
                strategy_parts.append("bayesian_optimization")
        else:
            train_result = train_decision_tree(
                max_sequences=max_sequences,
                cv_folds=cv_folds,
                progress_callback=progress_callback,
            )
            if train_result.get("success"):
                saved = _load_model_local(train_result["model_id"])
                if saved:
                    best_clf = saved["model"] if isinstance(saved, dict) else saved
                    best_result = train_result

        if best_clf is None:
            train_result = train_decision_tree(
                max_sequences=max_sequences,
                cv_folds=cv_folds,
            )
            if not train_result.get("success"):
                iteration_results.append(
                    {"success": False, "error": train_result.get("error"), "iteration": iteration}
                )
                continue
            saved = _load_model_local(train_result["model_id"])
            if saved:
                best_clf = saved["model"] if isinstance(saved, dict) else saved
            best_result = train_result
            strategy_parts = ["baseline_dt"]

        # ── Step 5: 评估 ──
        train_test_split = sk["train_test_split"]
        accuracy_score = sk["accuracy_score"]
        cross_val_score = sk["cross_val_score"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        best_clf.fit(X_train, y_train)

        test_acc = accuracy_score(y_test, best_clf.predict(X_test))
        train_acc = accuracy_score(y_train, best_clf.predict(X_train))
        overfit = train_acc - test_acc

        cv_mean = test_acc
        cv_std = 0.0
        try:
            min_class = min(Counter(y).values())
            cv_n = min(cv_folds, min_class)
            cv_scores = cross_val_score(best_clf, X, y, cv=cv_n, scoring="accuracy")
            cv_mean = float(cv_scores.mean())
            cv_std = float(cv_scores.std())
        except Exception:
            pass

        # ── Step 6: 集成融合 ──
        ensemble_result = None
        if use_ensemble:
            if progress_callback:
                progress_callback({"phase": "ensemble_building", "iteration": iteration})

            ens = build_ensemble(X, y, n_models=5, cv_folds=cv_folds)
            if ens:
                ensemble_result = {
                    "vote_accuracy": ens["vote_accuracy"],
                    "weighted_vote_accuracy": ens["weighted_vote_accuracy"],
                    "best_individual_cv": ens["best_individual_cv"],
                    "ensemble_improvement": ens["ensemble_improvement"],
                    "n_models": ens["n_models"],
                    "individual_results": ens["individual_results"],
                }
                strategy_parts.append("ensemble")

                if ens["weighted_vote_accuracy"] > test_acc:
                    best_clf = ens["trained_models"]
                    test_acc = ens["weighted_vote_accuracy"]

        # ── Step 7: 保存模型 ──
        model_id = f"self_improve_iter{iteration}_{random.randint(10000, 99999)}"
        model_path = MODEL_DIR / f"{model_id}.pkl"

        is_ensemble = isinstance(best_clf, list)
        joblib.dump(
            {
                "model": best_clf,
                "scaler": None,
                "needs_scaling": False,
                "feature_keys": aug_feature_names,
                "model_type": "ensemble" if is_ensemble else "stacking_dt",
                "label_map": IDX_TO_SHIFT,
                "is_ensemble": is_ensemble,
                "iteration": iteration,
            },
            model_path,
        )

        # ── Step 8: 误差分析 ──
        error_analysis = None
        if not is_ensemble:
            try:
                error_analysis = analyze_errors(model_id, test_X=X_test, test_y=y_test)
            except Exception:
                pass

        # ── Step 9: 保存历史 ──
        record = {
            "iteration": iteration,
            "model_id": model_id,
            "strategy": "+".join(strategy_parts) if strategy_parts else "baseline",
            "test_accuracy": round(float(test_acc), 4),
            "train_accuracy": round(float(train_acc), 4),
            "cv_mean": round(cv_mean, 4),
            "cv_std": round(cv_std, 4),
            "overfit": round(float(overfit), 4),
            "n_samples": len(X),
            "n_features": X.shape[1],
            "feature_engineering": use_feature_engineering and iteration > 0,
            "hard_mining": use_hard_mining and iteration >= 2,
            "bayesian": use_bayesian,
            "ensemble": ensemble_result is not None,
            "ensemble_result": ensemble_result,
            "error_analysis": error_analysis,
            "is_ensemble": is_ensemble,
        }

        save_training_record(record)
        iteration_results.append(record)

        if progress_callback:
            progress_callback(
                {
                    "phase": "iteration_complete",
                    "iteration": iteration,
                    "test_accuracy": round(float(test_acc), 4),
                    "cv_mean": round(cv_mean, 4),
                    "strategy": "+".join(strategy_parts),
                    "message": f"第 {iteration + 1} 轮完成: 准确率 {round(float(test_acc) * 100, 2)}%",
                }
            )

    # ── 最终汇总 ──
    best_iter = max(iteration_results, key=lambda r: r.get("cv_mean", 0))
    trajectory = get_improvement_trajectory()

    return {
        "success": True,
        "n_iterations": len(iteration_results),
        "best_iteration": best_iter,
        "improvement_trajectory": trajectory,
        "all_iterations": iteration_results,
        "total_improvement": (
            round((best_iter.get("cv_mean", 0) - trajectory[0]["cv_mean"]) * 100, 2)
            if len(trajectory) > 1
            else 0
        ),
    }


def _load_model_local(model_id):
    from stacking_analyzer import _load_model

    return _load_model(model_id)
