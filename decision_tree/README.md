# CGCPT 堆垛预测决策树

## 概述

本模块使用 **决策树 (Decision Tree)** 对密堆积层状晶体结构中的原子堆垛方式进行预测。训练数据由 `LayeredXOGenerator` 的确定性堆垛规则自动生成，决策树从中学习层模式、相邻层关系与堆垛标签 (A/B/C) 之间的映射规律。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `train_stacking_dt.py` | 训练脚本：数据生成、特征提取、模型训练、评估与预测 |
| `stacking_dt_rules.txt` | 完整的决策树规则文本（可读的 if-else 分支） |
| `stacking_dt_visualization.png` | 决策树可视化图（彩色树状图） |
| `stacking_dt_info.json` | 模型元信息：准确率、特征重要性、树深度等 |
| `README.md` | 本文档 |

---

## 堆垛预测问题定义

### 输入（特征）

对于层状结构中的每一层，提取以下 19 维特征向量：

| # | 特征名 | 类型 | 说明 |
|---|--------|------|------|
| 1 | `current_mode` | 离散 (0-9) | 当前层模式编号：XO=0, XO2=1, XO3=2, X=3, XBO3=4, BO3=5, XB3O6=6, M6=7, M7=8, T=9 |
| 2 | `is_main_layer` | 二值 (0/1) | 当前层是否为主层（XO/XO2/XO3/X/XBO3/BO3/XB3O6） |
| 3 | `is_x_layer` | 二值 (0/1) | 当前层是否为含 X 原子的主层 |
| 4 | `is_m_layer` | 二值 (0/1) | 当前层是否为 M6/M7 间隙层 |
| 5 | `is_t_layer` | 二值 (0/1) | 当前层是否为 T 四面体间隙层 |
| 6 | `prev_mode` | 离散 (0-9) | 前一层模式编号 |
| 7 | `next_mode` | 离散 (0-9) | 后一层模式编号 |
| 8 | `prev_is_main` | 二值 (0/1) | 前一层是否为主层 |
| 9 | `next_is_main` | 二值 (0/1) | 后一层是否为主层 |
| 10 | `prev_is_xb3o6` | 二值 (0/1) | 前一层是否为 XB3O6 |
| 11 | `next_is_xb3o6` | 二值 (0/1) | 后一层是否为 XB3O6 |
| 12 | `lower_main_shift` | 离散 (0/1/2/-1) | 下方最近主层的堆垛标签（A=0, B=1, C=2，未知=-1） |
| 13 | `upper_main_shift` | 离散 (0/1/2/-1) | 上方最近主层的堆垛标签 |
| 14 | `between_xb3o6` | 二值 (0/1) | M 层是否夹在两个 XB3O6 层之间 |
| 15 | `n_main_in_seq` | 整数 | 序列中主层的总数 |
| 16 | `n_x_in_seq` | 整数 | 序列中 X 层的总数 |
| 17 | `seq_len` | 整数 | 序列总层数 |
| 18 | `x_layer_position` | 整数 (-1/0/1/2/...) | 当前层在 X 层序列中的位置（非 X 层为 -1） |
| 19 | `prev_x_shift` | 离散 (0/1/2/-1) | 前一个 X 层的堆垛标签 |

### 输出（标签）

堆垛标签，取值为 A (0)、B (1)、C (2)。

---

## 训练过程

### 1. 训练数据生成

训练数据并非来自实验测量，而是由 `LayeredXOGenerator` 的确定性规则批量生成：

1. **层序列枚举**：从 7 种主层模式 + 2 种 M 层模式中，枚举长度 2~5 的合法组合（M 层必须夹在两个主层之间），生成约 500 种不同的层序列
2. **堆叠序列遍历**：对每个层序列，遍历 9 种 ABC 堆叠序列（ABC, AB, ACB, AAB, ABB, AA, ABCA, ABCAB, ABCB）
3. **规则计算**：调用 `build_full_shift_sequence_without_T()` 和 `insert_T_layers()` 计算每层的确定性堆垛标签
4. **特征提取**：对每一层提取 19 维特征向量

最终生成约 37,000 个样本，按 80%/20% 划分训练集和测试集。

### 2. 决策树训练

使用 scikit-learn 的 `DecisionTreeClassifier`，参数如下：

| 参数 | 值 | 说明 |
|------|------|------|
| `max_depth` | 10 | 限制树的最大深度，防止过拟合 |
| `min_samples_leaf` | 5 | 叶子节点最少样本数，提高泛化能力 |
| `random_state` | 42 | 随机种子，确保可复现 |

训练过程采用 **CART 算法**（Classification and Regression Trees）：
- 在每个节点，遍历所有特征和所有可能的分裂阈值
- 选择使 **基尼不纯度 (Gini Impurity)** 下降最大的分裂方式
- 递归分裂直到满足停止条件（最大深度或最小叶子样本数）

### 3. 评估方法

- **5 折交叉验证**：在训练集上进行 5 折交叉验证，评估模型泛化能力
- **测试集评估**：在 20% 的留出测试集上计算准确率、分类报告和混淆矩阵

### 4. 模型性能

| 指标 | 值 |
|------|------|
| 测试集准确率 | ~85% |
| 5 折交叉验证准确率 | ~87% |
| 决策树深度 | 10 |
| 叶子节点数 | ~217 |

---

## 分支分配过程

决策树通过自顶向下的递归分裂来分配分支。以下描述模型学到的核心分支逻辑：

### 第一级分裂：`x_layer_position`

决策树首先根据 **X 层在序列中的位置** 进行分裂：

- **x_layer_position ≤ 0.5**（第一个 X 层或非 X 层）
  - 进入左子树，进一步根据 `is_x_layer` 判断：
    - 若为 X 层 → 预测为 **A**（序列中第一个 X 层总是 A）
    - 若为非 X 层（M/T 层）→ 进入 M/T 层推断逻辑

- **x_layer_position > 0.5**（第 2、3、4... 个 X 层）
  - 进入右子树，根据 `prev_x_shift` 和 `upper_main_shift` 推断当前堆垛

### M 层推断分支

当当前层为 M6/M7 间隙层时，决策树学到的规则与理论规则完全一致：

```
若 lower_main_shift == upper_main_shift:
    → M 层堆垛 = lower_main_shift（与两侧主层相同）
若 lower_main_shift ≠ upper_main_shift:
    → M 层堆垛 = 第三个标签（A+B→C, B+C→A, A+C→B）
```

具体分支路径：
- `lower_main_shift ≤ 1.5` 且 `upper_main_shift ≤ 0.5`：
  - `lower_main_shift ≤ 0.5` → 上下都是 A → 预测 **A**
  - `lower_main_shift > 0.5` → 下方 B 上方 A → 预测 **C**
- `lower_main_shift > 1.5` 且 `upper_main_shift ≤ 0.5`：下方 C 上方 A → 预测 **B**
- 以此类推...

### T 层推断分支

T 层的推断逻辑与 M 层类似：
- 若左右层堆垛相同 → T 层堆垛相同
- 若左右层堆垛不同 → T 层取第三个标签

### 主层推断分支

主层的堆垛由 ABC 序列位置决定，决策树通过以下特征组合来推断：
1. `x_layer_position`：确定当前 X 层在序列中的位置
2. `prev_x_shift`：前一个 X 层的堆垛标签
3. `n_x_in_seq`：序列中 X 层总数（影响序列循环方式）
4. `next_is_xb3o6`：是否相邻 XB3O6 层（影响使用普通/特殊平移向量）

---

## 特征重要性

| 排名 | 特征 | 重要性 | 物理含义 |
|------|------|--------|----------|
| 1 | `upper_main_shift` | 0.336 | 上方主层堆垛，决定 M/T 层推断的关键输入 |
| 2 | `prev_x_shift` | 0.189 | 前一个 X 层堆垛，决定 ABC 序列推进方向 |
| 3 | `x_layer_position` | 0.124 | X 层在序列中的位置，决定 ABC 循环到哪个字母 |
| 4 | `is_x_layer` | 0.080 | 是否 X 层，区分主层与间隙层的推断逻辑 |
| 5 | `current_mode` | 0.075 | 当前层模式，影响 XB3O6 特殊规则 |
| 6 | `lower_main_shift` | 0.065 | 下方主层堆垛，M/T 层推断的另一关键输入 |
| 7 | `is_main_layer` | 0.051 | 是否主层，区分两类推断逻辑的入口 |
| 8 | `next_mode` | 0.032 | 后一层模式，辅助判断上下文 |

前 3 个特征累计贡献了 **65%** 的重要性，说明堆垛预测的核心逻辑集中在：**上方主层堆垛 + 前一个 X 层堆垛 + X 层位置**。

---

## 使用方法

### 训练模型

```bash
cd decision_tree
python train_stacking_dt.py
```

训练完成后将生成/更新：
- `stacking_dt_rules.txt` — 决策树规则文本
- `stacking_dt_visualization.png` — 可视化图
- `stacking_dt_info.json` — 模型元信息

### 在代码中调用预测

```python
from train_stacking_dt import train_and_evaluate, predict_stacking

# 训练
clf, acc = train_and_evaluate()

# 对自定义层序列预测堆垛
layer_modes = ["XO3", "M7", "XO3", "M7", "XO2"]
predictions = predict_stacking(clf, layer_modes, "ABC")
```

---

## 局限性与改进方向

1. **训练数据来源**：当前训练数据完全由规则生成，决策树本质上是在学习规则的近似表达。若需预测规则未覆盖的新型堆垛模式，需引入实验数据
2. **特征泄漏风险**：`lower_main_shift` 和 `upper_main_shift` 在实际预测中可能不可用（需要已知相邻层堆垛）。未来可考虑仅使用层模式等先验特征
3. **模型可替代性**：由于规则是确定性的，决策树的准确率上限 < 100%（受限于特征表达力）。可尝试随机森林或梯度提升树提升准确率
4. **序列位置编码**：当前 `x_layer_position` 为整数编码，未考虑循环序列的周期性。引入周期编码（如 sin/cos）可能改善长序列预测
