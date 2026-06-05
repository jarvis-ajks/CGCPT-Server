# CGCPT API 文档

> 版本：1.0.0 | 基础路径：`/api`

本文档详细描述 CGCPT 系统的所有 RESTful API 端点。

---

## 目录

- [健康检查](#健康检查)
- [统计与元素](#统计与元素)
- [原型管理](#原型管理)
- [材料管理](#材料管理)
- [搜索](#搜索)
- [分类](#分类)
- [层类型](#层类型)
- [结构生成](#结构生成)
- [拓扑验证](#拓扑验证)
- [材料导入](#材料导入)
- [堆垛分析](#堆垛分析)
- [数据库管理](#数据库管理)
- [算法管理](#算法管理)
- [任务管理](#任务管理)
- [模型管理](#模型管理)
- [插件系统](#插件系统)
- [认证](#认证)
- [通用错误格式](#通用错误格式)

---

## 健康检查

### GET /api/health

健康检查端点，返回系统运行状态。

**请求参数**：无

**响应示例**：

```json
{
  "status": "ok",
  "uptime_seconds": 86400.5,
  "indexes_built": true,
  "index_build_time_ms": 1500,
  "n_prototypes": 6,
  "n_materials": 2460,
  "memory": {
    "total_mb": 16384,
    "used_mb": 2048,
    "percent": 12.5
  }
}
```

**缓存**：`no-cache`

---

## 统计与元素

### GET /api/stats

获取系统统计数据。

**请求参数**：无

**响应示例**：

```json
{
  "total_materials": 2460,
  "verified_materials": 1234,
  "raw_materials": 1226,
  "unique_formulas": 800,
  "unique_space_groups": 45,
  "unique_topologies": 6,
  "unique_elements": 52,
  "topology_stats": {
    "XO3-M7-XO3-M7-XO3-M7-XO3": {
      "total": 1200,
      "verified": 600,
      "raw": 600
    }
  },
  "space_group_stats": {
    "Pm-3m": 500,
    "Pnma": 300
  },
  "element_counts": {
    "Ba": 150,
    "Ca": 120
  }
}
```

**缓存**：120s 内存缓存

---

### GET /api/elements

获取元素列表及对应材料数量。

**请求参数**：无

**响应示例**：

```json
{
  "elements": [
    { "symbol": "Ba", "materials_count": 150 },
    { "symbol": "Ca", "materials_count": 120 },
    { "symbol": "Sr", "materials_count": 95 }
  ],
  "total": 52
}
```

**缓存**：300s 内存缓存

---

## 原型管理

### GET /api/prototypes

获取拓扑原型列表。

**请求参数**：无

**响应示例**：

```json
{
  "prototypes": [
    {
      "id": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
      "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "reference_grid": "M7_base",
      "ideal_space_group": "Pm-3m",
      "space_group_number": 221,
      "crystal_system": "cubic",
      "is_neutral": true,
      "real_compounds_count": 5,
      "raw_materials_count": 1200,
      "verified_materials_count": 600
    }
  ],
  "total": 6
}
```

**缓存**：300s 内存缓存

---

### GET /api/prototypes/{proto_id}

获取指定原型详情。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `proto_id` | string | 原型 ID |

**响应示例**：

```json
{
  "id": "XO3-M7-XO3-M7-XO3-M7-XO3",
  "topology_theory": {
    "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
    "layer_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
    "stack_labels": ["A", "B", "C"],
    "reference_grid": "M7_base"
  },
  "prototype_crystallography": {
    "ideal_space_group": "Pm-3m",
    "space_group_number": 221,
    "crystal_system": "cubic",
    "is_neutral": true,
    "wyckoff_signature": { "Ba": "1a", "Ti": "1b", "O": "3c" }
  },
  "real_compounds": [
    {
      "formula": "BaTiO3",
      "mineral_name": "Perovskite",
      "source_id": "mp-2998",
      "rmsd_to_ideal": 0.0
    }
  ],
  "raw_materials": [
    {
      "material_id": "BaTiO3_Pm-3m_mp-2998",
      "formula": "BaTiO3",
      "space_group": "Pm-3m",
      "verified": false
    }
  ],
  "verified_materials": [
    {
      "material_id": "BaTiO3_Pm-3m_mp-2998",
      "formula": "BaTiO3",
      "space_group": "Pm-3m",
      "cif_file": "BaTiO3_Pm-3m_mp-2998.cif"
    }
  ]
}
```

**错误响应**：

```json
{ "error": "Prototype 'XXX' not found" }
```

---

## 材料管理

### GET /api/materials

获取材料列表，支持分页和多维筛选。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `topology` | string | - | 按拓扑 ID 筛选 |
| `elements` | string | - | 按元素筛选，逗号分隔，如 `Ba,Ti,O` |
| `space_group` | string | - | 按空间群筛选 |
| `formula` | string | - | 按化学式筛选 |
| `page` | int | 1 | 页码 |
| `per_page` | int | 20 | 每页数量（最大 100） |

**请求示例**：

```
GET /api/materials?elements=Ba,Ti&page=1&per_page=10
```

**响应示例**：

```json
{
  "materials": [
    {
      "material_id": "BaTiO3_Pm-3m_mp-2998",
      "formula": "BaTiO3",
      "space_group": "Pm-3m",
      "elements": ["Ba", "Ti", "O"],
      "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "verified": false
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 10,
  "total_pages": 2
}
```

---

### GET /api/materials/{material_id}

获取材料详情，包含 CIF 解析数据。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `material_id` | string | 材料 ID |

**响应示例**：

```json
{
  "material_id": "BaTiO3_Pm-3m_mp-2998",
  "formula": "BaTiO3",
  "space_group": "Pm-3m",
  "elements": ["Ba", "Ti", "O"],
  "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
  "verified": false,
  "directory": "Raw_Proto_XO3-M7-XO3-M7-XO3-M7-XO3",
  "cif_file": "BaTiO3_Pm-3m_mp-2998.cif",
  "cif_data": {
    "lattice": {
      "a": 4.0357,
      "b": 4.0357,
      "c": 4.0357,
      "alpha": 90.0,
      "beta": 90.0,
      "gamma": 90.0
    },
    "atom_sites": [
      { "element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0 },
      { "element": "Ti", "x": 0.5, "y": 0.5, "z": 0.5 },
      { "element": "O", "x": 0.5, "y": 0.5, "z": 0.0 }
    ],
    "formula": "BaTiO3",
    "space_group": "Pm-3m"
  }
}
```

---

### GET /api/materials/{material_id}/cif

下载材料的原始 CIF 文件。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `material_id` | string | 材料 ID |

**响应**：`text/plain`，Content-Disposition 为 inline

---

## 搜索

### GET /api/search

模糊搜索材料。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `q` | string | **必填** | 搜索关键词 |
| `limit` | int | 20 | 返回数量（最大 100） |

**搜索优先级**：
1. 化学式完全匹配（100 分）
2. 化学式包含（80 分）
3. 元素完全匹配（60 分）
4. 元素包含（40 分）
5. 空间群匹配（30 分）
6. ID 包含（20 分）

**请求示例**：

```
GET /api/search?q=BaTi&limit=5
```

**响应示例**：

```json
{
  "query": "BaTi",
  "results": [
    {
      "material_id": "BaTiO3_Pm-3m_mp-2998",
      "formula": "BaTiO3",
      "space_group": "Pm-3m",
      "elements": ["Ba", "Ti", "O"],
      "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "verified": false,
      "score": 80
    }
  ],
  "total": 5
}
```

---

## 分类

### GET /api/classifications

获取按拓扑、组成、空间群的分类数据。

**请求参数**：无

**响应示例**：

```json
{
  "by_topology": {
    "XO3-M7-XO3-M7-XO3-M7-XO3": {
      "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
      "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "ideal_space_group": "Pm-3m",
      "crystal_system": "cubic",
      "materials_count": 1200,
      "verified_count": 600
    }
  },
  "by_composition": {
    "BaTiO3": [
      {
        "material_id": "BaTiO3_Pm-3m_mp-2998",
        "space_group": "Pm-3m",
        "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
        "verified": false
      }
    ]
  },
  "by_space_group": {
    "Pm-3m": [
      {
        "material_id": "BaTiO3_Pm-3m_mp-2998",
        "formula": "BaTiO3",
        "topology": "XO3-M7-XO3-M7-XO3-M7-XO3"
      }
    ]
  }
}
```

**缓存**：300s 内存缓存

---

## 层类型

### GET /api/lattice-types

获取所有层类型信息。

**请求参数**：无

**响应示例**：

```json
{
  "lattice_types": [
    {
      "mode": "XO3",
      "description": "XO3层：每个X配位3个O的钙钛矿型(111)面，最常见的主层",
      "base_length_formula": "2 × d",
      "is_main_layer": true,
      "is_x_layer": true,
      "is_m_layer": false
    },
    {
      "mode": "M7",
      "description": "M7层：全占位M阳离子层，格点由相邻主层X原子网格决定",
      "base_length_formula": "继承相邻主层",
      "is_main_layer": false,
      "is_x_layer": false,
      "is_m_layer": true
    }
  ],
  "total": 10
}
```

---

## 结构生成

所有结构生成端点共享以下请求体参数：

**通用请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x_element` | string | `"Ba"` | X 位元素 |
| `o_element` | string | `"O"` | O 位元素 |
| `m_element` | string | `"Mg"` | M 位元素 |
| `t_element` | string | `"Si"` | T 位元素 |
| `b_element` | string | `"B"` | B 位元素 |
| `target_xo_distance` | float | `2.77648` | X-O 目标键长 |
| `nx` | int | `3` | X 方向超胞倍数 |
| `ny` | int | `3` | Y 方向超胞倍数 |
| `enable_t` | bool | `true` | 是否启用 T 层 |
| `layer_modes` | string[] | **必填** | 层模式列表，如 `["XO3", "M7", "XO3"]` |
| `layer_alphas` | float[] | `[]` | 层 alpha 参数 |
| `stack_sequence` | string | `"ABC"` | 堆垛序列 |
| `layer_angles` | float[] | `[]` | 各层旋转角度 |
| `layer_dxs` | float[] | `[]` | 各层 X 偏移 |
| `layer_dys` | float[] | `[]` | 各层 Y 偏移 |

---

### POST /api/generate

基础结构生成。

**请求示例**：

```json
{
  "x_element": "Ba",
  "o_element": "O",
  "m_element": "Ti",
  "layer_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
  "stack_sequence": "ABC"
}
```

**响应示例**：

```json
{
  "success": true,
  "formula": "Ba7Ti6O21",
  "lattice": {
    "a": 8.329,
    "b": 8.329,
    "c": 16.658,
    "alpha": 90.0,
    "beta": 90.0,
    "gamma": 60.0
  },
  "atom_sites": [
    { "element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0 }
  ],
  "atom_counts": {
    "x_count": 7,
    "o_count": 21,
    "m_count": 6,
    "t_count": 0,
    "b_count": 0
  },
  "topology": {
    "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
    "expanded_shifts": ["A", "B", "C", "A", "B", "C", "A"],
    "expanded_zs": [0.0, 0.143, 0.286, 0.429, 0.571, 0.714, 0.857],
    "main_shift_sequence": "ABC",
    "reference_grid": "M7_base",
    "exact_flag": true,
    "base_length": 8.329
  },
  "space_group": {
    "symbol": "Pm-3m",
    "number": 221,
    "crystal_system": "cubic"
  },
  "layer_data": [
    {
      "mode": "XO3",
      "shift": "A",
      "z": 0.0,
      "theta": 0.0,
      "dx": 0.0,
      "dy": 0.0,
      "grid_x": 3,
      "grid_y": 3,
      "atoms": [
        { "element": "Ba", "fx": 0.0, "fy": 0.0 },
        { "element": "O", "fx": 0.5, "fy": 0.0 }
      ]
    }
  ]
}
```

---

### POST /api/generate/layer-data

仅生成层数据（用于 2D 层可视化）。

**请求参数**：同通用参数

**响应示例**：

```json
{
  "success": true,
  "layer_data": [
    {
      "mode": "XO3",
      "shift": "A",
      "z": 0.0,
      "theta": 0.0,
      "dx": 0.0,
      "dy": 0.0,
      "grid_x": 3,
      "grid_y": 3,
      "atoms": [
        { "element": "Ba", "fx": 0.0, "fy": 0.0 }
      ]
    }
  ]
}
```

---

### POST /api/generate/primitive

生成结构并分析原胞。

**请求参数**：同通用参数

**响应示例**：

```json
{
  "success": true,
  "supercell": {
    "atom_sites": [],
    "lattice": {},
    "formula": "BaTiO3"
  },
  "primitive": {
    "atom_sites": [],
    "lattice": { "a": 4.035, "b": 4.035, "c": 4.035, "alpha": 90, "beta": 90, "gamma": 90 },
    "formula": "BaTiO3",
    "space_group": "Pm-3m",
    "space_group_number": 221,
    "unique_sites": { "Ba": 1, "Ti": 1, "O": 3 },
    "is_neutral": true
  },
  "wyckoff_signature": { "Ba": "1a", "Ti": "1b", "O": "3c" }
}
```

---

### POST /api/generate/coordination

生成结构并分析配位环境。

**额外请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cutoff_radius` | float | `2.77648 × 1.35` | 配位截断半径 |

**响应示例**：

```json
{
  "success": true,
  "environments": [
    {
      "cn": 12,
      "center": { "element": "Ba", "x": 0.0, "y": 0.0, "z": 0.0 },
      "neighbors": [
        { "element": "O", "dx": 2.018, "dy": 0.0, "dz": 0.0, "distance": 2.018 }
      ]
    }
  ]
}
```

---

### POST /api/generate/prototype

生成结构并提取原型文档。

**请求参数**：同通用参数

**响应示例**：

```json
{
  "success": true,
  "topology_theory": {
    "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-M7_base",
    "input_main_shifts": "ABC",
    "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
    "expanded_shifts": ["A", "B", "C", "A", "B", "C", "A"],
    "reference_grid": "M7_base"
  },
  "prototype_crystallography": {
    "ideal_space_group": "Pm-3m",
    "space_group_number": 221,
    "crystal_system": "cubic",
    "is_neutral": true,
    "wyckoff_signature": { "Ba": "1a", "Ti": "1b", "O": "3c" }
  },
  "real_compounds": []
}
```

---

### POST /api/generate/full

完整分析（结构 + 层数据 + 原胞 + 配位 + 原型）。

**请求参数**：通用参数 + `cutoff_radius`

**响应**：合并上述所有端点的响应字段。

---

## 拓扑验证

### POST /api/verify-topology

验证材料与模板结构的拓扑匹配。

**请求体**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `template_cif_path` | string | **必填**，模板 CIF 文件路径 |
| `test_material_ids` | string[] | **必填**，待验证材料 ID 列表 |

**请求示例**：

```json
{
  "template_cif_path": "/opt/CGCPT/database/Verified_Proto_XO3-M7-XO3-M7-XO3-M7-XO3/BaTiO3_Pm-3m_mp-2998.cif",
  "test_material_ids": ["BaTiO3_Amm2_mp-5777", "BaTiO3_P4mm_mp-5986"]
}
```

**响应示例**：

```json
{
  "matches": [
    { "material_id": "BaTiO3_Amm2_mp-5777", "is_match": true },
    { "material_id": "BaTiO3_P4mm_mp-5986", "is_match": true }
  ]
}
```

---

## 材料导入

### POST /api/import/preview

预览待导入的 CIF 文件。

**请求**：`multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `files` | File[] | CIF 文件列表 |
| `topology` | string | 可选，指定拓扑分类 |

**响应示例**：

```json
{
  "success": true,
  "results": [
    {
      "filename": "BaZrO3.cif",
      "material_id": "BaZrO3",
      "formula": "BaZrO3",
      "space_group": "Pm-3m",
      "elements": ["Ba", "Zr", "O"],
      "n_atoms": 5,
      "lattice": { "a": 4.19, "b": 4.19, "c": 4.19, "alpha": 90, "beta": 90, "gamma": 90 },
      "existing": false,
      "suggested_topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "confidence": 0.85,
      "assigned_topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "cif_preview": "data_BaZrO3\n_cell_length_a  4.19..."
    }
  ],
  "available_topologies": ["XO3-M7-XO3-M7-XO3-M7-XO3", "..."],
  "total_files": 1,
  "parsed": 1,
  "errors": 0
}
```

---

### POST /api/import

执行材料导入。

**请求体**：

```json
{
  "items": [
    {
      "material_id": "BaZrO3",
      "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "cif_content": "data_BaZrO3\n...",
      "formula": "BaZrO3",
      "space_group": "Pm-3m",
      "elements": ["Ba", "Zr", "O"]
    }
  ]
}
```

**响应示例**：

```json
{
  "success": true,
  "imported": [
    {
      "material_id": "BaZrO3",
      "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "path": "Raw_Proto_XO3-M7-XO3-M7-XO3-M7-XO3/BaZrO3.cif"
    }
  ],
  "skipped": [],
  "errors": [],
  "total_new": 1,
  "total_materials_now": 2461
}
```

---

### GET /api/import/templates

获取导入模板列表（即所有可用拓扑原型）。

**响应示例**：

```json
{
  "templates": [
    {
      "id": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
      "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "ideal_space_group": "Pm-3m",
      "crystal_system": "cubic",
      "materials_count": 1200
    }
  ],
  "total": 6
}
```

---

## 堆垛分析

### POST /api/stacking/scan

扫描数据库中的 CIF 文件，提取特征。

**请求体**：无（空 JSON 或省略）

**响应示例**：

```json
{
  "success": true,
  "n_samples": 2460,
  "samples": [
    {
      "filename": "BaTiO3_Pm-3m_mp-2998.cif",
      "topology": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "formula": "BaTiO3",
      "source": "raw",
      "n_features": 42
    }
  ]
}
```

---

### POST /api/stacking/train

训练堆垛识别决策树模型。

**请求体**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `test_ratio` | float | 0.2 | 测试集比例（0.05~0.5） |
| `max_depth` | int/null | null | 决策树最大深度 |
| `random_state` | int | 42 | 随机种子 |
| `model_type` | string | `"auto"` | 模型类型 |
| `n_iterations` | int | 5 | 迭代次数 |
| `cv_folds` | int | 5 | 交叉验证折数 |
| `max_sequences` | int | 500 | 最大序列数 |

**请求示例**：

```json
{
  "test_ratio": 0.2,
  "cv_folds": 5,
  "max_sequences": 500
}
```

**响应示例**：

```json
{
  "success": true,
  "model_id": "dt_20260605_120000",
  "accuracy": 0.92,
  "cv_score": 0.89,
  "n_samples": 500,
  "n_features": 42,
  "classification_report": { ... },
  "confusion_matrix": [ ... ]
}
```

---

### POST /api/stacking/train/stream

流式训练进度（Server-Sent Events）。

**请求参数**：同 `/api/stacking/train`

**响应**：`text/event-stream`

```
event: progress
data: {"iteration": 1, "phase": "scanning", "progress": 0.2}

event: progress
data: {"iteration": 1, "phase": "training", "progress": 0.6}

event: result
data: {"success": true, "model_id": "dt_20260605_120000", "accuracy": 0.92}
```

---

### POST /api/stacking/predict

使用训练好的模型预测堆垛序列。

**请求体**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model_id` | string | **必填**，模型 ID |
| `layer_modes` | string[] | 层模式列表（与 cif_text 二选一） |
| `stack_sequence` | string | 堆垛序列，默认 `"ABC"` |
| `cif_text` | string | CIF 文件文本（与 layer_modes 二选一） |

**请求示例**：

```json
{
  "model_id": "dt_20260605_120000",
  "layer_modes": ["XO3", "M7", "XO3", "M7", "XO3"],
  "stack_sequence": "ABC"
}
```

**响应示例**：

```json
{
  "success": true,
  "predictions": ["A", "B", "C", "A", "B"],
  "accuracy": 1.0,
  "n_correct": 5,
  "n_total": 5,
  "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3"]
}
```

---

### POST /api/stacking/analyze

分析 CIF 文本，提取特征。

**请求体**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `cif_text` | string | **必填**，CIF 文件文本 |

**响应示例**：

```json
{
  "success": true,
  "formula": "BaTiO3",
  "space_group": "Pm-3m",
  "lattice": { "a": 4.035, "b": 4.035, "c": 4.035 },
  "n_atoms": 5,
  "features": { "n_layers": 7, "c_ratio": 2.0, ... },
  "layer_analysis": { ... }
}
```

---

### POST /api/stacking/upload

上传 CIF 文件进行分析。

**请求**：`multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | **必填**，CIF 文件 |

**响应**：同 `/api/stacking/analyze`，额外包含 `filename` 和 `cif_text`

---

### POST /api/stacking/batch_predict

批量预测多个层序列。

**请求体**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model_id` | string | **必填**，模型 ID |
| `layer_sequences` | array | 层序列列表，每个元素为 string[] 或逗号分隔的 string |
| `stack_sequence` | string | 堆垛序列，默认 `"ABC"` |

**响应示例**：

```json
{
  "success": true,
  "model_id": "dt_20260605_120000",
  "n_sequences": 10,
  "overall_accuracy": 0.85,
  "total_correct": 42,
  "total_layers": 50,
  "results": [
    {
      "layer_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "accuracy": 1.0,
      "n_correct": 7,
      "n_total": 7,
      "predictions": ["A", "B", "C", "A", "B", "C", "A"]
    }
  ]
}
```

---

### GET /api/stacking/models

列出所有堆垛模型。

**响应示例**：

```json
{
  "success": true,
  "models": [
    {
      "model_id": "dt_20260605_120000",
      "model_type": "decision_tree",
      "accuracy": 0.92,
      "created_at": "2026-06-05T12:00:00",
      "is_active": true
    }
  ]
}
```

---

### DELETE /api/stacking/models/{model_id}

删除指定堆垛模型。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model_id` | string | 模型 ID |

**响应示例**：

```json
{
  "success": true,
  "model_id": "dt_20260605_120000"
}
```

---

### POST /api/stacking/self_improve

执行自我迭代优化。

**请求体**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_iterations` | int | 3 | 最大迭代次数 |
| `max_sequences` | int | 300 | 最大序列数 |
| `cv_folds` | int | 3 | 交叉验证折数 |
| `use_feature_engineering` | bool | true | 启用特征工程 |
| `use_hard_mining` | bool | true | 启用困难样本挖掘 |
| `use_ensemble` | bool | true | 启用集成学习 |
| `use_bayesian` | bool | true | 启用贝叶斯优化 |

**响应示例**：

```json
{
  "success": true,
  "iterations": 3,
  "best_accuracy": 0.95,
  "improvement": 0.03,
  "history": [ ... ]
}
```

---

### GET /api/stacking/improvement_history

获取自我优化历史。

**响应示例**：

```json
{
  "success": true,
  "trajectory": [
    { "iteration": 1, "accuracy": 0.89, "timestamp": "..." },
    { "iteration": 2, "accuracy": 0.92, "timestamp": "..." },
    { "iteration": 3, "accuracy": 0.95, "timestamp": "..." }
  ],
  "n_iterations": 3
}
```

---

### GET /api/stacking/error_analysis/{model_id}

获取指定模型的误差分析。

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model_id` | string | 模型 ID |

**响应示例**：

```json
{
  "success": true,
  "model_id": "dt_20260605_120000",
  "total_errors": 15,
  "error_patterns": [
    { "pattern": "XO3-M7-XO3", "count": 5, "common_mistake": "XO3-M6-XO3" }
  ],
  "hard_samples": [ ... ]
}
```

---

## 数据库管理

### GET /api/db/status

获取数据库状态概览。

**响应示例**：

```json
{
  "success": true,
  "prototypes": 6,
  "materials": 2460,
  "algorithms": 5,
  "tasks_total": 110,
  "tasks_pending": 5,
  "tasks_running": 2,
  "tasks_completed": 100,
  "tasks_failed": 3,
  "models": 3
}
```

---

### POST /api/db/migrate

从文件系统迁移数据到数据库。

**请求体**：无

**响应示例**：

```json
{
  "success": true,
  "imported_prototypes": 6,
  "imported_materials": 2460,
  "errors": [],
  "total_errors": 0
}
```

---

### GET /api/db/prototypes

从数据库查询原型列表。

**查询参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `crystal_system` | string | 按晶系筛选 |

**响应示例**：

```json
{
  "success": true,
  "prototypes": [
    {
      "id": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
      "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
      "ideal_space_group": "Pm-3m",
      "space_group_number": 221,
      "crystal_system": "cubic",
      "is_neutral": true,
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 6
}
```

---

### GET /api/db/prototypes/{prototype_id}

获取数据库中原型详情。

**响应示例**：

```json
{
  "success": true,
  "prototype": {
    "id": "XO3-M7-XO3-M7-XO3-M7-XO3",
    "prototype_id": "XO3-M7-XO3-M7-XO3-M7-XO3-ABC",
    "expanded_modes": ["XO3", "M7", "XO3", "M7", "XO3", "M7", "XO3"],
    "reference_grid": "M7_base",
    "ideal_space_group": "Pm-3m",
    "space_group_number": 221,
    "crystal_system": "cubic",
    "is_neutral": true,
    "topology_data": { ... },
    "materials_count": 1200,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": "2026-01-01T00:00:00"
  }
}
```

---

### GET /api/db/materials

从数据库查询材料列表（支持分页、排序、筛选）。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `topology_id` | string | - | 按拓扑 ID 筛选 |
| `space_group` | string | - | 按空间群筛选 |
| `is_verified` | string | - | `"true"` / `"false"` |
| `formula` | string | - | 化学式模糊搜索 |
| `source` | string | - | 按来源筛选 |
| `page` | int | 1 | 页码 |
| `page_size` | int | 50 | 每页数量（最大 100） |
| `sort_by` | string | `"created_at"` | 排序字段：formula / topology_id / n_atoms / created_at |
| `sort_dir` | string | `"desc"` | 排序方向：asc / desc |

**响应示例**：

```json
{
  "success": true,
  "materials": [
    {
      "id": "BaTiO3_Pm-3m_mp-2998",
      "formula": "BaTiO3",
      "space_group": "Pm-3m",
      "topology_id": "XO3-M7-XO3-M7-XO3-M7-XO3",
      "elements": ["Ba", "Ti", "O"],
      "lattice_a": 4.0357,
      "lattice_b": 4.0357,
      "lattice_c": 4.0357,
      "lattice_alpha": 90.0,
      "lattice_beta": 90.0,
      "lattice_gamma": 90.0,
      "n_atoms": 5,
      "is_verified": false,
      "source": "raw",
      "cif_path": "Raw_Proto_XO3-M7-XO3-M7-XO3-M7-XO3/BaTiO3_Pm-3m_mp-2998.cif",
      "created_at": "2026-01-01T00:00:00",
      "updated_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 2460,
  "page": 1,
  "page_size": 50,
  "total_pages": 50
}
```

---

### GET /api/db/materials/{material_id}

获取数据库中材料详情。

**响应**：包含 `cif_content` 和 `metadata_json` 字段的完整材料信息。

---

### DELETE /api/db/materials/{material_id}

删除数据库中的材料。

**需要认证**：否

**响应示例**：

```json
{ "success": true, "message": "Material xxx deleted" }
```

---

### POST /api/db/materials/batch

批量更新材料。

**请求体**：

```json
{
  "action": "verify",
  "updates": [
    { "material_id": "BaTiO3_Pm-3m_mp-2998" }
  ]
}
```

支持的 `action`：
- `"verify"` — 标记为已验证
- `"unverify"` — 取消验证
- `"update"` — 更新指定字段（topology_id / formula / space_group / is_verified / metadata_json）

**响应示例**：

```json
{ "success": true, "updated": 5 }
```

---

### GET /api/db/stats

获取数据库详细统计。

**响应示例**：

```json
{
  "success": true,
  "materials": { "total": 2460, "verified": 1234, "raw": 1226 },
  "prototypes": 6,
  "topology_counts": { "XO3-M7-XO3-M7-XO3-M7-XO3": 1200 },
  "space_group_counts": { "Pm-3m": 500 },
  "tasks": { "pending": 5, "running": 2, "completed": 100, "failed": 3, "total": 110 },
  "algorithms": 5,
  "models": 3
}
```

---

## 算法管理

### GET /api/algorithms

列出所有活跃算法。

**响应示例**：

```json
{
  "success": true,
  "algorithms": [
    {
      "id": "stacking_train",
      "name": "堆垛识别训练",
      "description": "从数据库CIF文件训练决策树模型",
      "version": "1.0.0",
      "algorithm_type": "training",
      "entry_point": "stacking_analyzer.train_decision_tree",
      "input_schema": { ... },
      "output_schema": { ... },
      "default_config": { ... }
    }
  ],
  "total": 5
}
```

---

### POST /api/algorithms

注册新算法。

**请求体**：

```json
{
  "id": "my_algorithm",
  "name": "My Algorithm",
  "description": "自定义算法描述",
  "algorithm_type": "prediction",
  "entry_point": "mymodule.my_function",
  "input_schema": { "type": "object", "properties": { ... } },
  "output_schema": { "type": "object", "properties": { ... } },
  "default_config": { "param1": 0.5 }
}
```

**响应示例**：

```json
{ "success": true, "algorithm_id": "my_algorithm" }
```

---

### DELETE /api/algorithms/{algo_id}

停用算法（软删除）。

**响应示例**：

```json
{ "success": true }
```

---

## 任务管理

### POST /api/tasks

提交新任务。

**请求体**：

```json
{
  "algorithm_id": "stacking_train",
  "input_data": {
    "test_ratio": 0.2,
    "cv_folds": 5
  }
}
```

**响应示例**：

```json
{ "success": true, "task_id": "uuid-task-id-1234" }
```

---

### GET /api/tasks

列出任务。

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | - | 状态筛选：pending / running / completed / failed |
| `algorithm_id` | string | - | 算法筛选 |
| `limit` | int | 50 | 返回数量（最大 200） |

**响应示例**：

```json
{
  "success": true,
  "tasks": [
    {
      "task_id": "uuid-task-id-1234",
      "algorithm_id": "stacking_train",
      "status": "completed",
      "progress": 1.0,
      "progress_message": "Training complete",
      "error_message": null,
      "created_at": "2026-06-05T12:00:00",
      "started_at": "2026-06-05T12:00:01",
      "completed_at": "2026-06-05T12:05:00"
    }
  ],
  "total": 1
}
```

---

### GET /api/tasks/{task_id}

获取任务详情。

**响应示例**：

```json
{
  "success": true,
  "task_id": "uuid-task-id-1234",
  "status": "completed",
  "progress": 1.0,
  "output_data": { ... }
}
```

---

## 模型管理

### GET /api/models

列出所有模型。

**响应示例**：

```json
{
  "success": true,
  "models": [
    {
      "id": "dt_20260605_120000",
      "name": "Decision Tree v1",
      "model_type": "decision_tree",
      "metrics": { "accuracy": 0.92, "n_features": 42 },
      "feature_keys": ["n_layers", "c_ratio", ...],
      "file_path": "/opt/CGCPT/models/dt_20260605_120000.pkl",
      "is_active": true,
      "created_at": "2026-06-05T12:00:00"
    }
  ]
}
```

---

### POST /api/models/upload

上传模型文件（需管理员认证）。

**请求**：`multipart/form-data`

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | File | **必填**，模型文件（.pkl） |
| `name` | string | 模型名称 |
| `model_type` | string | 模型类型，默认 `"decision_tree"` |
| `model_id` | string | 模型 ID |
| `description` | string | 描述 |

**认证**：`Authorization: Bearer <token>`

**响应示例**：

```json
{
  "success": true,
  "model_id": "uploaded_abc12345",
  "model_class": "DecisionTreeClassifier",
  "file_path": "/opt/CGCPT/models/dt_uploaded_abc12345.pkl",
  "metrics": { "n_features": 42, "n_nodes": 150, "n_classes": 7 }
}
```

---

### DELETE /api/models/{model_id}

删除模型（需管理员认证）。

---

### POST /api/models/{model_id}/activate

激活模型（同类型其他模型自动停用，需管理员认证）。

---

## 插件系统

### GET /api/plugins

列出所有活跃插件。

**响应**：同 `/api/algorithms`

---

### POST /api/plugins

注册插件。

**请求体**：

```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "entry_point": "plugins.my_plugin.execute",
  "algorithm_type": "prediction",
  "description": "插件描述",
  "input_schema": { ... },
  "output_schema": { ... }
}
```

**必填字段**：`id`, `name`, `entry_point`

---

### DELETE /api/plugins/{algo_id}

停用插件。

---

### POST /api/plugins/{algo_id}/execute

执行插件（提交任务）。

**请求体**：

```json
{
  "input_data": { "param1": "value1" }
}
```

**响应**：

```json
{ "success": true, "task_id": "uuid-task-id" }
```

---

### POST /api/plugins/discover

发现插件目录中的插件。

**请求体**（可选）：

```json
{ "plugin_dir": "/opt/CGCPT/plugins" }
```

**响应示例**：

```json
{
  "success": true,
  "discovered": ["cif_analyzer", "topology_stats"],
  "count": 2
}
```

---

### GET /api/plugins/discovered

列出已发现但未注册的插件。

---

### POST /api/plugins/register-all

注册所有已发现的插件。

**响应示例**：

```json
{
  "success": true,
  "registered": ["cif_analyzer", "topology_stats"],
  "count": 2
}
```

---

## 认证

### POST /api/auth/login

管理员登录。

**请求体**：

```json
{
  "username": "admin",
  "password": "123"
}
```

**响应示例**：

```json
{
  "success": true,
  "token": "YWRtaW46MTIz"
}
```

**错误响应**（401）：

```json
{
  "success": false,
  "error": "用户名或密码错误"
}
```

---

### GET /api/auth/check

验证 Token 有效性。

**请求头**：`Authorization: Bearer <token>`

**响应示例**：

```json
{ "success": true, "user": "admin" }
```

**错误响应**（401）：

```json
{ "success": false, "error": "未授权" }
```

---

## 通用错误格式

所有 API 在出错时返回统一格式：

```json
{
  "error": "错误描述信息",
  "traceback": "详细堆栈（仅开发模式）"
}
```

常见 HTTP 状态码：

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 501 | 功能未实现（模块未安装） |
