# CGCPT 系统架构与 API 文档

## 目录

1. [系统架构](#系统架构)
2. [数据库设计](#数据库设计)
3. [API 端点参考](#api-端点参考)
4. [算法注册与执行](#算法注册与执行)
5. [外部算法对接](#外部算法对接)
6. [部署指南](#部署指南)

---

## 系统架构

### 组件概览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React)                          │
│  - Dashboard (统计、任务、材料管理)                           │
│  - Algorithm Manager (算法注册与执行)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   后端 API (Flask)                          │
│  - /api/* 端点                                              │
│  - 数据库 ORM (SQLAlchemy)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ↓              ↓              ↓
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   MySQL DB   │ │  Redis   │ │  Celery      │
│  - Materials │ │  Queue   │ │  Worker      │
│  - Prototypes│ │  Cache   │ │  (算法执行)   │
│  - Tasks     │ └──────────┘ └──────────────┘
│  - Algorithms│
└──────────────┘
```

### 目录结构

```
/opt/CGCPT/
├── api_server.py           # Flask 后端主程序
├── models.py               # SQLAlchemy ORM 模型与迁移
├── task_worker.py          # Celery 任务队列 worker
├── task_engine.py          # 任务执行引擎增强
├── db_api.py               # 数据库 API 增强
├── data_tools.py           # 数据备份与导出工具
├── test_system.py          # 系统测试脚本
├── deploy_server.py        # 服务器部署脚本
├── stacking_analyzer.py    # 堆叠分析与决策树
├── config.py               # 配置文件
├── requirements.txt        # Python 依赖
├── venv/                   # Python 虚拟环境
├── web/                    # React 前端
│   └── src/
│       ├── App.tsx
│       └── pages/
│           ├── AlgorithmManager.tsx
│           └── Dashboard.tsx
├── database/               # 旧文件系统存储
├── models/                 # 训练好的模型文件
├── backups/                # 数据库备份
└── exports/                # 数据导出
```

---

## 数据库设计

### 表结构

#### `prototypes` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(64) | 主键，原型 ID |
| prototype_id | String | 原型标识符 |
| expanded_modes | String | 扩展模式 |
| reference_grid | JSON | 参考网格 |
| ideal_space_group | String | 理想空间群 |
| space_group_number | Integer | 空间群号 |
| crystal_system | String | 晶系 |
| is_neutral | Boolean | 是否中性 |
| topology_data | JSON | 拓扑数据 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### `materials` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(64) | 主键 |
| formula | String | 化学式 |
| space_group | String | 空间群 |
| topology_id | String | 外键 → prototypes.id |
| elements | JSON | 元素列表 |
| lattice_a/b/c | Float | 晶格参数 |
| lattice_alpha/beta/gamma | Float | 晶格角度 |
| n_atoms | Integer | 原子数 |
| is_verified | Boolean | 是否已验证 |
| source | String | 来源 |
| cif_path | String | CIF 文件路径 |
| cif_content | Text | CIF 内容 |
| metadata_json | JSON | 元数据 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### `algorithms` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(64) | 主键，算法 ID |
| name | String | 显示名称 |
| description | Text | 描述 |
| algorithm_type | String | 类型 (training/prediction/generation/validation/import) |
| entry_point | String | 入口点 (module.function) |
| input_schema | JSON | 输入 JSON Schema |
| output_schema | JSON | 输出 JSON Schema |
| default_config | JSON | 默认配置 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### `tasks` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(64) | 主键，任务 ID |
| algorithm_id | String | 外键 → algorithms.id |
| status | String | 状态 (pending/running/completed/failed) |
| input_data | JSON | 输入参数 |
| output_data | JSON | 输出结果 |
| error_message | Text | 错误信息 |
| progress | Float | 进度 (0-1) |
| progress_message | String | 进度信息 |
| celery_task_id | String | Celery 任务 ID |
| created_at | DateTime | 创建时间 |
| started_at | DateTime | 开始时间 |
| completed_at | DateTime | 完成时间 |

#### `model_artifacts` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(64) | 主键 |
| algorithm_id | String | 外键 → algorithms.id |
| task_id | String | 外键 → tasks.id |
| name | String | 模型名称 |
| model_type | String | 模型类型 |
| metrics | JSON | 评估指标 |
| feature_keys | JSON | 特征键 |
| file_path | String | 模型文件路径 |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

---

## API 端点参考

### 健康检查

```
GET /health
```

响应:
```json
{
  "status": "ok",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

### 算法管理

#### 列出所有算法

```
GET /api/algorithms
```

响应:
```json
{
  "success": true,
  "algorithms": [
    {
      "id": "stacking_train",
      "name": "Train Decision Tree",
      "algorithm_type": "training",
      "is_active": true,
      "created_at": "..."
    }
  ],
  "count": 5
}
```

#### 注册新算法

```
POST /api/algorithms
Content-Type: application/json
```

请求体:
```json
{
  "id": "my_custom_algo",
  "name": "My Algorithm",
  "description": "Does cool things",
  "algorithm_type": "prediction",
  "entry_point": "mymodule.my_function",
  "input_schema": {
    "type": "object",
    "properties": {
      "param1": {"type": "number"}
    }
  },
  "default_config": {"param1": 0.5},
  "is_active": true
}
```

#### 获取算法详情

```
GET /api/algorithms/:id
```

### 任务管理

#### 提交新任务

```
POST /api/tasks
Content-Type: application/json
```

请求体:
```json
{
  "algorithm_id": "stacking_train",
  "input_data": {
    "test_ratio": 0.2,
    "max_depth": 10
  }
}
```

响应:
```json
{
  "success": true,
  "task_id": "uuid-task-id-1234"
}
```

#### 列出任务

```
GET /api/tasks?status=running&limit=20
```

查询参数:
- `status`: 可选，状态过滤
- `algorithm_id`: 可选，算法过滤
- `limit`: 可选，返回数量限制

#### 获取任务详情

```
GET /api/tasks/:id
```

#### 取消任务

```
POST /api/tasks/:id/cancel
```

### 数据库查询

#### 列出原型

```
GET /api/db/prototypes?crystal_system=cubic
```

#### 获取原型详情

```
GET /api/db/prototypes/:id
```

#### 列出材料 (支持分页和筛选)

```
GET /api/db/materials?page=1&page_size=50&topology_id=...&space_group=...&is_verified=true&formula=...&source=...
```

查询参数:
- `page`: 页码 (默认 1)
- `page_size`: 每页数量 (默认 50, 最大 100)
- `topology_id`: 拓扑 ID 筛选
- `space_group`: 空间群筛选
- `is_verified`: 是否验证 (true/false)
- `formula`: 化学式模糊搜索
- `source`: 来源筛选
- `sort_by`: 排序字段 (formula/topology_id/n_atoms/created_at)
- `sort_dir`: 排序方向 (asc/desc)

响应:
```json
{
  "success": true,
  "materials": [...],
  "total": 2460,
  "page": 1,
  "page_size": 50,
  "total_pages": 50
}
```

#### 获取材料详情

```
GET /api/db/materials/:id
```

#### 删除材料

```
DELETE /api/db/materials/:id
```

#### 批量更新材料

```
POST /api/db/materials/batch
Content-Type: application/json
```

请求体:
```json
{
  "action": "verify",
  "updates": [{"material_id": "..."}, ...]
}
```

或:
```json
{
  "action": "update",
  "updates": [
    {
      "material_id": "...",
      "topology_id": "...",
      "is_verified": true
    }
  ]
}
```

#### 获取系统统计

```
GET /api/db/stats
```

响应:
```json
{
  "success": true,
  "materials": {"total": 2460, "verified": 1234, "raw": 1226},
  "prototypes": 6,
  "topology_counts": {"p1": 1000, ...},
  "space_group_counts": {"P1": 500, ...},
  "tasks": {"pending": 5, "running": 2, "completed": 100, "failed": 3, "total": 110},
  "algorithms": 5,
  "models": 3
}
```

---

## 算法注册与执行

### 内置算法

系统内置了以下 5 个算法:

1. `stacking_train` - 训练决策树模型
2. `stacking_predict` - 使用决策树预测
3. `material_generator` - 材料生成 (占位)
4. `material_validator` - 材料验证 (占位)
5. `material_importer` - 材料导入 (占位)

### 自定义算法开发

#### 步骤 1: 实现算法函数

在 `/opt/CGCPT/` 目录下创建或编辑 Python 模块:

```python
# mymodule.py
import time
import random

def my_algorithm(param1: float = 0.5, param2: str = "default"):
    """
    我的自定义算法

    Args:
        param1: 示例数值参数
        param2: 示例字符串参数

    Returns:
        dict: 算法结果
    """
    # 算法核心逻辑
    time.sleep(2)

    result = {
        "success": True,
        "score": random.random() * param1,
        "message": f"Processed with param2={param2}",
        "timestamp": time.time()
    }

    return result
```

#### 步骤 2: 注册算法

通过 API 注册:

```bash
curl -X POST http://localhost:5000/api/algorithms \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my_algorithm",
    "name": "My Algorithm",
    "description": "Does something cool",
    "algorithm_type": "prediction",
    "entry_point": "mymodule.my_algorithm",
    "default_config": {
      "param1": 0.5,
      "param2": "hello"
    },
    "is_active": true
  }'
```

或通过前端 Dashboard 页面注册。

#### 步骤 3: 执行算法

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm_id": "my_algorithm",
    "input_data": {
      "param1": 1.0,
      "param2": "test"
    }
  }'
```

---

## 外部算法对接

### 方案概述

对于独立开发的外部算法，有两种集成方式:

1. **函数级集成** - 算法作为 Python 函数，注册到系统中 (推荐)
2. **HTTP API 集成** - 算法作为独立服务，通过 HTTP 调用

### 方案 1: 函数级集成 (推荐)

#### 优点
- 简单，无需额外部署
- 共享数据库连接
- 任务队列原生支持
- 更好的错误处理和日志

#### 示例:

```python
# external_algo.py (你的独立算法文件)

def analyze_structure(cif_content: str, params: dict = None):
    """
    外部算法的主函数

    Args:
        cif_content: CIF 文件内容
        params: 算法参数字典

    Returns:
        dict: 结果字典
    """
    from pymatgen.io.cif import CifParser
    from pymatgen.core import Structure

    # 解析 CIF
    parser = CifParser.from_string(cif_content)
    structure = parser.get_structures()[0]

    # 算法核心逻辑
    result = {
        "formula": structure.composition.reduced_formula,
        "volume": structure.volume,
        "density": structure.density,
        "is_stable": structure.volume > 100,
        "custom_score": 0.85
    }

    return result

# (可选) 如果需要保存结果到数据库
def save_result_to_db(db_session, material_id: str, result: dict):
    from models import Material
    mat = db_session.query(Material).filter_by(id=material_id).first()
    if mat:
        mat.metadata_json = result
        mat.is_verified = True
        db_session.commit()
```

#### 注册到 CGCPT:

```bash
# 1. 上传 external_algo.py 到 /opt/CGCPT/
# 2. 注册算法
curl -X POST http://localhost:5000/api/algorithms \
  -H "Content-Type: application/json" \
  -d '{
    "id": "external_analyzer",
    "name": "External Structure Analyzer",
    "description": "Uses external algorithm to analyze structures",
    "algorithm_type": "prediction",
    "entry_point": "external_algo.analyze_structure",
    "default_config": {},
    "is_active": true
  }'
```

#### 执行任务并自动归类:

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm_id": "external_analyzer",
    "input_data": {
      "cif_content": "... CIF content here ...",
      "material_id": "optional-existing-id"
    }
  }'
```

### 方案 2: HTTP API 集成

如果外部算法已经是一个独立的 Web 服务:

```python
# 在 CGCPT 端创建包装函数
# external_api_wrapper.py

import requests

def call_external_api(cif_content: str, api_url: str = "http://external-service:8000/analyze"):
    """调用外部 HTTP API"""
    response = requests.post(
        api_url,
        json={"cif": cif_content},
        timeout=300
    )
    response.raise_for_status()
    return response.json()
```

然后注册 `external_api_wrapper.call_external_api` 函数。

---

## 部署指南

### 完整部署步骤

#### 步骤 1: 上传文件到服务器

在服务器 `/opt/CGCPT/` 目录下放置以下文件:
- `models.py`
- `task_worker.py`
- `task_engine.py`
- `db_api.py`
- `api_server.py`
- `stacking_analyzer.py`
- `config.py`
- `data_tools.py`
- `test_system.py`
- `deploy_server.py`
- `requirements.txt`
- `web/` (前端构建产物)
- `database/` (可选，用于迁移)

#### 步骤 2: 执行一键部署

```bash
cd /opt/CGCPT
./venv/bin/python3 deploy_server.py
```

部署脚本会自动执行:
1. ✅ 环境检查 (Python, MySQL, Redis)
2. ✅ 依赖安装
3. ✅ 数据库表初始化
4. ✅ 内置算法注册
5. ✅ 从文件系统迁移数据
6. ✅ 重启 API 服务
7. ✅ 重启 Celery Worker
8. ✅ 健康检查

#### 步骤 3: 验证部署

```bash
# 运行系统测试
./venv/bin/python3 test_system.py

# 检查服务状态
systemctl status cgcpt-api
systemctl status cgcpt-worker

# 查看日志
tail -f /opt/CGCPT/logs/worker.log
tail -f /opt/CGCPT/logs/api.log
```

### 常用管理命令

```bash
# 备份数据
./venv/bin/python3 data_tools.py backup

# 导出材料
./venv/bin/python3 data_tools.py export materials

# 手动重启服务
systemctl restart cgcpt-api
systemctl restart cgcpt-worker
```

---

## 附录

### A. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | mysql+pymysql://... | 数据库连接 |
| REDIS_URL | redis://localhost:6379/0 | Redis 连接 |
| FLASK_ENV | production | Flask 环境 |
| UPLOAD_DIR | /opt/CGCPT/uploads | 上传目录 |

### B. 故障排除

#### 问题: Celery 任务不执行

检查:
```bash
systemctl status cgcpt-worker
tail -f /opt/CGCPT/logs/worker.log
redis-cli ping
```

#### 问题: 数据库迁移外键错误

修复: 已在 `models.py` 中处理，先禁用外键约束再导入。

---

**文档版本**: 2.0
**最后更新**: 2025-01
