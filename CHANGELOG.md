# 更新日志 / Changelog

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
