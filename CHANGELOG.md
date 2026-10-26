# 更新日志 / Changelog

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 变更 / Changed

- **可切换的 CIF 对比查看器**
  - 保留 Materials Project 为默认模式，加入 MatterViz、Megane、CifVis、
    crystvis-js、3Dmol.js、WEAS；切换时卸载旧实例，第三方模式明确标注非 MP 显示
  - scene 服务新增 `output:"cif"`，使用同一 pymatgen 解析逻辑展开 P1 CIF，
    规范分数坐标并使位点标签唯一，避免对称等价原子丢失或标签冲突；
    原默认场景 JSON 协议不变
  - 新增 Svelte 构建支持，前端要求 Node 24+，锁定依赖并将浮动的
    `svelte-widgets` Git 来源改为 npm `1.10.0`
  - 查看器样式与旧库全局事件隔离，构建发布引擎许可与 CifVis 源码地址
  - MP 的尺寸观察依赖升级至 `use-resize-observer@9.1.0`，修复切换后的残留回调；
    为 crystvis 的 `load-bmfont` 添加局部 Buffer 构建接线，不污染全局
  - 一致性验收基准明确为公开 Crystal Toolkit 默认行为，不宣称官网当前页面逐像素一致

- **三维结构查看器改用 Materials Project 官方组件**
  - 前端删除自研 three.js 查看器（`web/src/components/three/`），改为
    `@materialsproject/mp-react-components@0.5.2` 的 `CrystalToolkitScene`，
    与 materialsproject.org 页面使用同一套渲染代码
  - 新增 `web/src/components/mp/CrystalScene.tsx`：统一封装加载/错误/尺寸，
    材料详情、原型详情、材料对比、结构生成器、堆垛识别上传分析全部接入
  - 前端依赖移除 `three` / `@react-three/fiber` / `@react-three/drei`，
    新增 `react-is@19`；`vite.config.ts` 增加 `global` 定义、React 单一实例
    alias/dedupe（否则触发 React #321 invalid hook）
  - `main.tsx` 关闭 `StrictMode`：MP 0.5.2 在开发模式的挂载探测中会在
    `Scene.onDestroy` 抛错并清空组件树（生产构建不受影响）

- **查看器样式与 Materials Project 对齐**
  - 上游组件不自带构建后的 CSS（dist 无样式），且按 Bulma 编写；新增
    `web/scripts/build-scene-css.mjs` 把 Bulma 0.9.4 + 组件自带的
    `.css`/`.less` 统一前缀 `.cgcpt-scene` 后生成
    `web/src/components/mp/scene-vendor.css`（约 254KB，随查看器懒加载）
  - 查看器区域改为白底、Bulma 字号/字体，按钮、下拉菜单、全屏弹层、
    tooltip、设置面板均使用上游原生样式（此前是手写的近似样式）
  - 全屏时按视口重新计算 `sceneSize`（约 `min(95vw, 95vh-48)`），关闭后还原
  - 重新生成：`cd web && npm run build:scene-css`

- **新增 Crystal Toolkit 场景服务**
  - `scene_service.py`：`POST /scene`，接受 `cif_text` 或
    `{structure: {lattice, atoms}}`
  - 场景生成与 `crystal_toolkit` 官方 `StructureMoleculeComponent` 完全一致：
    `StructureGraph.from_local_env_strategy(..., CrystalNN())` 生成键连，
    VESTA 配色 / uniform 半径 / 绘制周期镜像原子 / 追加 compass axes，
    再 `scene.to_json()` —— 输出含 `atoms, bonds, polyhedra, magmoms,
    unit_cell, axes`
  - 前端按官方 `default_scene_settings` 传入
    `{extractAxis: true, secondaryObjectView: false}`，compass 进入内嵌坐标轴，
    不参与相机取景
  - 独立进程运行（gunicorn，`127.0.0.1:18108`）；前端请求
    `/CGCPT/api/structure/scene` 由反向代理直连该服务
  - 部署配置同步：`requirements.txt` 增加 `crystal-toolkit==2026.7.20`，
    Dockerfile/compose 增加 `cgcpt-scene` 容器，nginx 增加 scene upstream 与路由，
    Vite 开发代理与 `local_dev_server.py` 增加 scene 转发

---

## [1.0.0] - 2026-06-05

### 新增 / Added

- **核心功能**
  - CIF 文件解析引擎（pymatgen + 手动正则双模式）
  - 6 种钙钛矿拓扑原型分类系统
  - 层状结构生成器 (LayeredXOGenerator)
  - 拓扑验证模块 (StructureMatcher)
  - 配位环境分析
  - 原胞分析 + Wyckoff 位置签名

- **机器学习**
  - 堆垛序列识别决策树模型
  - 自我迭代优化引擎（误差分析 + 特征工程 + 贝叶斯超参）
  - 集成学习融合
  - 流式训练进度 (SSE)
  - 批量预测

- **API 服务**
  - 40+ RESTful API 端点
  - 内存级缓存机制（stats 120s, prototypes/elements/classifications 300s）
  - 分页 + 多维筛选
  - 模糊搜索（按化学式/元素/空间群/ID）
  - CORS 支持

- **前端界面**
  - Dashboard 统计面板（含周期表热力图）
  - 材料浏览器 + 详情页
  - 原型浏览器 + 详情页
  - 结构生成器（可视化配置 + 3D 预览）
  - 堆垛识别器（训练/预测/分析）
  - 分类浏览器
  - 材料对比
  - 高级搜索
  - 3D 晶体结构查看器 (Three.js / R3F / Drei)
  - 路由懒加载 + 鼠标悬停预加载

- **数据管理**
  - SQLAlchemy ORM 模型（Prototype, Material, Algorithm, Task, ModelArtifact）
  - MySQL 数据库支持
  - 文件系统到数据库迁移
  - 批量 CIF 导入（预览 + 自动拓扑分类）
  - 数据备份与导出工具

- **任务系统**
  - Celery + Redis 异步任务队列
  - 内置 5 个算法（训练/预测/生成/验证/导入）
  - 任务进度追踪

- **插件系统**
  - CGCPTPlugin SDK（基类 + 装饰器 + 上下文）
  - 插件自动发现与注册
  - 外部算法对接框架

- **认证**
  - Bearer Token 认证
  - 管理员权限控制

- **部署**
  - Gunicorn WSGI 服务器
  - Nginx 反向代理 + Brotli 压缩
  - Systemd 服务管理
  - 健康看门狗 (Crontab)
  - 日志轮转 (Logrotate)

- **数据库**
  - 2400+ 钙钛矿型化合物 CIF 文件
  - 6 种拓扑原型元数据
  - Raw / Verified 双级验证体系

---

## 版本说明 / Version Notes

- **[1.0.0]** — 首个正式发布版本，包含完整的分类、预测、生成、验证功能链
