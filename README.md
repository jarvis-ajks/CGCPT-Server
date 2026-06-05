# CGCPT-Server

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/cgcpt/cgcpt-server)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)

**CGCPT** (Crystallographic Classification of Perovskite Topology) — 钙钛矿型晶体结构堆垛拓扑分类与预测系统

---

## 项目概述 / Overview

CGCPT 是一个面向钙钛矿型 (Perovskite-type) 晶体材料的**结构堆垛拓扑分类与智能预测平台**。系统基于层状堆垛理论，将钙钛矿衍生结构分解为 XO₃、XO₂、XO 等主层与 M7、M6、T 等辅助层的组合，实现从 CIF 文件到拓扑原型的自动分类，并利用机器学习模型（决策树、集成学习）进行堆垛序列预测。

本系统旨在为材料科学研究人员提供一套完整的工具链，涵盖晶体结构解析、拓扑分类、结构生成、堆垛预测与拓扑验证等核心功能。

### 科学背景 / Scientific Background

钙钛矿型材料 (ABX₃) 是最重要的功能材料家族之一，涵盖铁电体、超导体、催化剂、光伏材料等。其衍生结构通过层状堆垛 (layer stacking) 产生丰富的拓扑变体：

- **XO₃ 层**：钙钛矿型 (111) 面，每个 X 配位 3 个 O
- **XO₂ 层**：CdI₂ 型层，每个 X 配位 2 个 O
- **XO 层**：岩盐型 (100) 面，X 与 O 交替排列
- **M7/M6 层**：M 阳离子插入层（全占位 / 2/3 占位）
- **T 层**：四面体阳离子插入层

不同层类型的堆垛组合形成了多种拓扑原型，目前已识别 6 种基本拓扑类型，涵盖 2400+ 实际化合物。

---

## 核心特性 / Key Features

- **CIF 文件解析** — 支持 pymatgen 解析与手动正则解析双模式，兼容各种 CIF 格式
- **拓扑分类引擎** — 基于层状堆垛理论，自动识别 6 种拓扑原型
- **结构生成器** — 可视化配置层模式、堆垛序列、旋转角度等参数，实时生成晶体结构
- **3D 晶体可视化** — 基于 Three.js / React Three Fiber 的交互式 3D 晶体结构查看器
- **堆垛预测 (ML)** — 决策树 + 集成学习模型，支持训练、预测、批量预测
- **自我迭代优化** — 误差分析驱动的自动特征工程 + 贝叶斯超参优化
- **拓扑验证** — 基于 StructureMatcher 的结构匹配验证
- **配位环境分析** — 自动识别 X-O 配位多面体环境
- **原胞分析** — 自动提取原胞、Wyckoff 位置签名
- **插件系统** — CGCPTPlugin SDK，支持自定义算法注册与执行
- **材料导入** — 批量 CIF 上传、自动拓扑分类、预览确认
- **数据库管理** — MySQL + SQLAlchemy ORM，支持文件系统迁移
- **任务队列** — Celery + Redis 异步任务执行
- **RESTful API** — 完整的 API 接口，支持缓存与分页

---

## 系统架构 / Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     前端 Frontend (React 19)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │Dashboard │ │Materials │ │Generator │ │ Stacking ML      │    │
│  │  统计面板 │ │  材料浏览 │ │ 结构生成  │ │  堆垛识别/训练    │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │         3D Crystal Viewer (Three.js / R3F / Drei)        │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTP/REST (Vite Dev Proxy / Nginx)
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                   后端 Backend (Flask + Gunicorn)                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │api_server  │ │stack_main  │ │stacking_   │ │verify_      │  │
│  │  API 路由   │ │ 结构生成器  │ │analyzer    │ │topology     │  │
│  │  缓存/分页  │ │LayeredXOGen│ │ ML 训练/预测│ │ 拓扑验证     │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │models      │ │task_worker │ │self_       │ │cgcpt_plugin │  │
│  │ SQLAlchemy │ │ Celery     │ │improver    │ │ 插件 SDK     │  │
│  │ ORM 模型   │ │ 任务队列    │ │ 自我优化    │ │ 算法注册     │  │
│  └────────────┘ └────────────┘ └────────────┘ └─────────────┘  │
└──────────┬───────────────┬──────────────────┬────────────────────┘
           │               │                  │
           ↓               ↓                  ↓
    ┌────────────┐  ┌────────────┐    ┌──────────────┐
    │   MySQL    │  │   Redis    │    │  File System  │
    │  结构化数据 │  │  任务队列   │    │  CIF 数据库   │
    │  ORM 存储  │  │  缓存      │    │  模型文件     │
    └────────────┘  └────────────┘    └──────────────┘
```

---

## 快速开始 / Quick Start

### 环境要求 / Prerequisites

- Python 3.10+
- Node.js 18+
- MySQL 8.0+ (可选，默认使用文件系统)
- Redis 7.0+ (可选，任务队列需要)

### 后端启动 / Backend Setup

```bash
# 1. 克隆项目
git clone https://github.com/cgcpt/cgcpt-server.git
cd cgcpt-server

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动开发服务器
python api_server.py
# 服务运行在 http://localhost:5000
```

### 前端启动 / Frontend Setup

```bash
# 1. 进入前端目录
cd web

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
# 前端运行在 http://localhost:5173，自动代理 API 到 :5000
```

### 生产构建 / Production Build

```bash
# 前端构建
cd web && npm run build
# 产物输出到 web/dist/

# 后端使用 Gunicorn
gunicorn --config gunicorn.conf.py api_server:app
```

---

## API 概览 / API Overview

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/stats` | 系统统计数据 |
| GET | `/api/elements` | 元素列表及材料计数 |
| GET | `/api/prototypes` | 拓扑原型列表 |
| GET | `/api/prototypes/<id>` | 原型详情 |
| GET | `/api/materials` | 材料列表（分页+筛选） |
| GET | `/api/materials/<id>` | 材料详情（含 CIF 解析） |
| GET | `/api/materials/<id>/cif` | 下载原始 CIF 文件 |
| GET | `/api/search` | 搜索材料 |
| GET | `/api/classifications` | 分类数据（按拓扑/组成/空间群） |
| GET | `/api/lattice-types` | 层类型信息 |
| POST | `/api/generate` | 基础结构生成 |
| POST | `/api/generate/layer-data` | 层数据生成 |
| POST | `/api/generate/primitive` | 原胞分析 |
| POST | `/api/generate/coordination` | 配位环境分析 |
| POST | `/api/generate/prototype` | 原型文档生成 |
| POST | `/api/generate/full` | 完整分析（结构+原胞+配位+原型） |
| POST | `/api/verify-topology` | 拓扑验证 |
| POST | `/api/import/preview` | 导入预览 |
| POST | `/api/import` | 执行导入 |
| GET | `/api/import/templates` | 导入模板列表 |
| POST | `/api/stacking/scan` | 扫描数据库 CIF |
| POST | `/api/stacking/train` | 训练堆垛模型 |
| POST | `/api/stacking/train/stream` | 流式训练进度 (SSE) |
| POST | `/api/stacking/predict` | 堆垛预测 |
| POST | `/api/stacking/analyze` | 分析 CIF 文本 |
| POST | `/api/stacking/upload` | 上传 CIF 分析 |
| POST | `/api/stacking/batch_predict` | 批量预测 |
| GET | `/api/stacking/models` | 列出堆垛模型 |
| DELETE | `/api/stacking/models/<id>` | 删除堆垛模型 |
| POST | `/api/stacking/self_improve` | 自我迭代优化 |
| GET | `/api/stacking/improvement_history` | 优化历史 |
| GET | `/api/stacking/error_analysis/<id>` | 误差分析 |
| GET | `/api/db/status` | 数据库状态 |
| POST | `/api/db/migrate` | 从文件系统迁移 |
| GET | `/api/db/prototypes` | 数据库原型列表 |
| GET | `/api/db/prototypes/<id>` | 数据库原型详情 |
| GET | `/api/db/materials` | 数据库材料列表（分页+排序+筛选） |
| GET | `/api/db/materials/<id>` | 数据库材料详情 |
| DELETE | `/api/db/materials/<id>` | 删除材料 |
| POST | `/api/db/materials/batch` | 批量更新材料 |
| GET | `/api/db/stats` | 数据库详细统计 |
| GET | `/api/algorithms` | 算法列表 |
| POST | `/api/algorithms` | 注册算法 |
| DELETE | `/api/algorithms/<id>` | 停用算法 |
| POST | `/api/tasks` | 提交任务 |
| GET | `/api/tasks` | 任务列表 |
| GET | `/api/tasks/<id>` | 任务详情 |
| GET | `/api/models` | 模型列表 |
| POST | `/api/models/upload` | 上传模型（需认证） |
| DELETE | `/api/models/<id>` | 删除模型（需认证） |
| POST | `/api/models/<id>/activate` | 激活模型（需认证） |
| GET | `/api/plugins` | 插件列表 |
| POST | `/api/plugins` | 注册插件 |
| DELETE | `/api/plugins/<id>` | 停用插件 |
| POST | `/api/plugins/<id>/execute` | 执行插件 |
| POST | `/api/plugins/discover` | 发现插件 |
| GET | `/api/plugins/discovered` | 已发现插件 |
| POST | `/api/plugins/register-all` | 注册所有已发现插件 |
| POST | `/api/auth/login` | 登录认证 |
| GET | `/api/auth/check` | 验证 Token |

> 详细 API 文档请参阅 [docs/API.md](docs/API.md)

---

## 配置参考 / Configuration Reference

### 环境变量 / Environment Variables

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CGCPT_DB_URL` | `mysql+pymysql://root@127.0.0.1:3306/cgcpt?charset=utf8mb4` | MySQL 数据库连接 |
| `CELERY_BROKER` | `redis://127.0.0.1:6379/0` | Celery Broker |
| `CELERY_BACKEND` | `redis://127.0.0.1:6379/1` | Celery 结果后端 |
| `FLASK_ENV` | `production` | Flask 运行环境 |

### Gunicorn 配置 (`gunicorn.conf.py`)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `bind` | `0.0.0.0:5001` | 监听地址 |
| `workers` | 1 | Worker 进程数 |
| `worker_class` | `gthread` | Worker 类型 |
| `threads` | 2 | 每 Worker 线程数 |
| `timeout` | 300 | 请求超时 (秒) |
| `max_requests` | 500 | Worker 自动重启请求数 |

### 前端配置 (`web/vite.config.ts`)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `base` | `/CGCPT/` | 部署基础路径 |
| `build.target` | `es2020` | 构建目标 |
| `proxy` | `:5001` | API 代理目标 |

---

## 项目结构 / Project Structure

```
CGCPT-Server/
├── api_server.py              # Flask API 主入口
├── stack_main.py              # 结构生成核心模块 (LayeredXOGenerator)
├── stacking_analyzer.py       # 堆垛识别模块 (ML 训练/预测)
├── verify_topology.py         # 拓扑验证模块
├── models.py                  # SQLAlchemy ORM 模型
├── task_worker.py             # Celery 任务队列 Worker
├── task_engine.py             # 任务执行引擎
├── self_improver.py           # 自我迭代优化引擎
├── cgcpt_plugin.py            # 插件 SDK
├── data_tools.py              # 数据备份与导出
├── gunicorn.conf.py           # Gunicorn 配置
├── requirements.txt           # Python 依赖
│
├── web/                       # React 前端
│   ├── src/
│   │   ├── App.tsx            # 路由配置
│   │   ├── api/client.ts      # API 客户端
│   │   ├── types/index.ts     # TypeScript 类型
│   │   ├── components/        # 通用组件
│   │   │   ├── three/
│   │   │   │   └── CrystalViewer.tsx  # 3D 晶体查看器
│   │   │   └── ...
│   │   └── pages/             # 页面组件
│   │       ├── Dashboard.tsx
│   │       ├── MaterialsBrowser.tsx
│   │       ├── StructureGenerator.tsx
│   │       ├── StackingRecognizer.tsx
│   │       └── ...
│   ├── vite.config.ts
│   └── package.json
│
├── database/                  # CIF 文件数据库
│   ├── Proto_*.json           # 原型元数据
│   ├── Raw_Proto_*/           # 原始 CIF 文件
│   └── Verified_Proto_*/      # 已验证 CIF 文件
│
├── models/                    # 训练好的 ML 模型
├── plugins/                   # 插件目录
├── training_history/          # 训练历史记录
└── docs/                      # 文档
    ├── API.md
    └── DEPLOYMENT.md
```

---

## 贡献指南 / Contributing

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情，包括代码规范、Git 工作流和 PR 流程。

---

## 引用信息 / Citation

如果您在学术研究中使用了本系统，请引用：

```bibtex
@software{cgcpt2026,
  title     = {CGCPT: Crystallographic Classification of Perovskite Topology},
  author    = {CGCPT Team},
  year      = {2026},
  url       = {https://cgcpt.ink},
  note      = {Crystal structure stacking topology classification and prediction system}
}
```

---

## 许可证 / License

本项目基于 [MIT License](LICENSE) 开源。

---

## 联系方式 / Contact

- 项目主页：[https://cgcpt.ink](https://cgcpt.ink)
- 问题反馈：[GitHub Issues](https://github.com/cgcpt/cgcpt-server/issues)
- 邮箱：cgcpt@example.com
