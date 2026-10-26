# CGCPT 项目完整上下文文档

> 生成时间: 2026-05-20
> 用途: 交接给其他 Agent 继续开发/运维

---

## 一、项目概述

**CGCPT** (Crystallographic Classification of Perovskite Topology) 是一个晶体材料分类与拓扑分析平台。

- **项目类型**: 全栈 Web 应用（React 前端 + Flask 后端）
- **本地路径**: `C:\Users\21051\Projects\CGCPT-Server\`
- **服务器**: 阿里云 ECS (Ubuntu)
- **域名**: `zsxw.asia`（Caddy 自动 HTTPS，CGCPT 挂载在 `/CGCPT/`）

---

## 二、技术栈

### 前端 (`web/`)
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.x | UI 框架 |
| TypeScript | 6.x | 类型安全 |
| Vite | 8.x | 构建工具 |
| Tailwind CSS v4 | 4.x | 样式框架 |
| React Router v7 | 7.x | 路由管理 |
| @materialsproject/mp-react-components | 0.5.2 | 3D 晶体可视化（MP 官方 CrystalToolkitScene） |
| crystal_toolkit (Python) | 2026.7.20 | 场景 JSON 生成 |
| Recharts | 2.x | 图表库 (Dashboard) |
| Lucide React | latest | 图标库 |

### 后端 (根目录)
| 技术 | 用途 |
|------|------|
| Python 3.12 | 运行时 |
| Flask | Web 框架 |
| Gunicorn | WSGI 服务器 |
| PyMatgen | 晶体结构解析 |
| scikit-learn | ML 模型 (堆垛识别) |

### 服务器基础设施
| 组件 | 详情 |
|------|------|
| Caddy | 反向代理 + 静态文件服务 + Brotli/Gzip 压缩 (`/opt/caddy/Caddyfile`, `projects.caddy`) |
| Fail2ban | SSH 暴力破解防护 |
| systemd | 服务管理 (`projects-cgcpt`, `projects-cgcpt-worker`, `projects-cgcpt-scene`) |
| Cloudflare | CDN + DNS (可选) |

---

## 三、服务器信息

```
IP: 118.31.164.41
用户: root
SSH 方式: 密钥认证 (ed25519)
私钥: ~/.ssh/win21051（Windows 上 ssh 配置别名 aliyun）
```

### SSH 连接方式
```bash
# 密钥登录（仓库根目录不再存放私钥）
ssh aliyun            # ~/.ssh/config 中 Host aliyun
# 等价于: ssh -i ~/.ssh/win21051 root@118.31.164.41

# SSH 配置: PermitRootLogin prohibit-password, MaxAuthTries=3, LoginGraceTime=30
# 注意: 密码登录已禁用（旧脚本里的明文密码已失效），仅允许密钥认证 root
```

### 关键路径 (服务器上)
| 路径 | 说明 |
|------|------|
| `/opt/projects/cgcpt/` | 后端项目根目录 |
| `/opt/projects/cgcpt/api_server.py` | Flask API 主文件 |
| `/opt/projects/cgcpt/scene_service.py` | Materials Project 场景 JSON 服务 |
| `/opt/projects/cgcpt/.venv/` | Python 虚拟环境 |
| `/opt/projects/cgcpt/data/cgcpt.db` | SQLite 数据库 |
| `/opt/projects/cgcpt/database/` | CIF 文件数据库 (~2460 个材料) |
| `/opt/projects/cgcpt-web/` | 前端构建产物 (Caddy 静态目录) |
| `/opt/caddy/projects.caddy` | CGCPT 路由 (Caddyfile 通过 `import projects` 引入) |
| `/etc/systemd/system/projects-cgcpt*.service` | Systemd 服务文件 |
| `/var/log/projects/cgcpt*.log` | 服务日志 |

### 端口分配
| 端口 | 服务 | 监听地址 |
|------|------|----------|
| 80/443 | Caddy | 0.0.0.0 |
| 22 | SSH | 0.0.0.0 |
| 18020 | Gunicorn (API) | 127.0.0.1 |
| 18108 | Gunicorn (Crystal Toolkit scene) | 127.0.0.1 |
| 3306 | MySQL (其他项目共用) | 127.0.0.1 |
| 6379 | Redis | 127.0.0.1 |

### 服务启停
三个 unit 均为 `is-enabled=static`，**不会随系统启动**：

```bash
systemctl start projects-cgcpt projects-cgcpt-worker projects-cgcpt-scene
systemctl stop projects-cgcpt-scene   # 释放 ~358MB 内存（3D 区域将不可用）
```

---

## 四、项目结构

```
<repo>/
├── api_server.py              # Flask API 主入口
├── scene_service.py           # Materials Project 场景 JSON 服务
├── stack_main.py              # 结构生成核心模块 (LayeredXOGenerator)
├── stacking_analyzer.py       # 堆垛识别模块 (ML 模型训练/预测)
├── verify_topology.py         # 拓扑验证模块
│
├── web/                       # React 前端
│   ├── src/
│   │   ├── App.tsx           # 路由配置 + 路由预加载 (preloadRoute)
│   │   ├── main.tsx          # 入口
│   │   ├── api/client.ts     # API 客户端 (fetch 封装)
│   │   ├── types/index.ts    # TypeScript 类型定义
│   │   ├── components/
│   │   │   ├── Layout.tsx    # 主布局 (Outlet)
│   │   │   ├── Sidebar.tsx   # 侧边导航 (含 hover 预加载)
│   │   │   ├── Header.tsx    # 页头
│   │   │   ├── ErrorBoundary.tsx  # 错误边界
│   │   │   ├── ElementPicker.tsx # 元素选择器
│   │   │   └── mp/
│   │   │       ├── CrystalScene.tsx  # MP 场景查看器封装 (懒加载!)
│   │   │       └── CrystalScene.css  # 上游组件所需样式
│   │   └── pages/
│   │       ├── Dashboard.tsx          # 仪表盘 (含周期表热力图)
│   │       ├── MaterialsBrowser.tsx   # 材料浏览
│   │       ├── MaterialDetail.tsx     # 材料详情 (含 CrystalScene)
│   │       ├── PrototypesBrowser.tsx  # 原型浏览
│   │       ├── PrototypeDetail.tsx    # 原型详情 (含 CrystalScene)
│   │       ├── StructureGenerator.tsx # 结构生成器 (含 2 处 CrystalScene)
│   │       ├── StackingRecognizer.tsx # 堆垛识别 (上传结果含 CrystalScene)
│   │       ├── MaterialsCompare.tsx   # 材料对比
│   │       ├── ClassificationBrowser.tsx # 分类浏览
│   │       ├── SearchResults.tsx      # 搜索结果
│   │       ├── TopologyVerify.tsx     # 拓扑验证
│   │       ├── Favorites.tsx          # 收藏夹
│   │       ├── RecentBrowse.tsx       # 最近浏览
│   │       ├── AdvancedSearch.tsx     # 高级搜索
│   │       └── NotFound.tsx           # 404
│   ├── vite.config.ts          # Vite 配置 (chunk 分割)
│   ├── package.json
│   └── dist/                   # 构建产物 (部署目标)
│
├── database/                  # 数据库目录
│   ├── Proto_*.json           # 原型元数据 JSON (6 个原型)
│   ├── Raw_Proto_*/           # 原始 CIF 文件 (按拓扑分组)
│   └── Verified_Proto_*/      # 已验证 CIF 文件
│
└── *_*.py                     # 临时调试脚本 (可忽略)
```

---

## 五、前端路由与懒加载策略

所有页面组件均使用 `React.lazy()` 懒加载。路由预加载在 Sidebar 的 `onMouseEnter` 时触发。

```typescript
// App.tsx - 预加载映射表
const _preloadMap = {
  '/materials': () => import('./pages/MaterialsBrowser'),
  '/prototypes': () => import('./pages/PrototypesBrowser'),
  '/generate': () => import('./pages/StructureGenerator'),
  '/stacking': () => import('./pages/StackingRecognizer'),
  '/classify': () => import('./pages/ClassificationBrowser'),
  '/compare': () => import('./pages/MaterialsCompare'),
  '/advanced-search': () => import('./pages/AdvancedSearch'),
}
export function preloadRoute(path: string) { ... }
```

**CrystalScene（Materials Project 查看器）特殊处理**: 在 MaterialDetail、PrototypeDetail、StructureGenerator、StackingRecognizer 中使用 `lazy(() => import('../components/mp/CrystalScene'))` + `<Suspense>` 包裹，MP 组件与 three.js（~5.3MB chunk）仅在出现结构时加载。

- 组件只负责取数：`POST /CGCPT/api/structure/scene`（`{cif_text}` 或 `{structure:{lattice,atoms}}`），把返回 JSON 原样交给 `<CrystalToolkitScene data={scene} />`
- 尺寸与官方 `StructureMoleculeComponent.layout(size="500px")` 对齐：白色方块最大
  500×500（`min(容器宽度, 500)`，窄屏自适应），`sceneSize` 传像素值；全屏时按视口重算
- 相机使用上游默认值（`cameraAxis='z'`, `cameraPosition='back'`, `defaultZoom=0.8`,
  `zoomToFit2D=false`），并按官方 `default_scene_settings` 传
  `{extractAxis: true, secondaryObjectView: false, renderer: 'webgl'}`
- 场景内容 = 官方管线：CrystalNN 键连、VESTA 配色、uniform 半径、镜像原子、
  compass axes、unit cell、polyhedra
- 样式：上游 `dist` 不含 CSS，按 Bulma 约定编写。`web/scripts/build-scene-css.mjs` 将
  Bulma 0.9.4 + 组件 `.css`/`.less` 前缀 `.cgcpt-scene` 生成 `scene-vendor.css`，
  因此按钮/下拉/全屏/tooltip 与上游一致，且不会污染 Tailwind UI；
  修改后执行 `npm run build:scene-css`
- 查看器区域为白底，画布本身透明（上游 `transparentBackground`）
- **不要启用 `StrictMode`**：MP 0.5.2 在开发模式的挂载探测中会在 `Scene.onDestroy` 抛错并清空组件树；`main.tsx` 已注明
- `ViewerSwitcher` 默认 MP，另有 MatterViz / Megane / CifVis / crystvis-js /
  3Dmol.js / WEAS 六个独立对比引擎，均按需加载；不要将其称为 MP 一致模式。
- 对比输入通过同一路由携带 `output:"cif"`，由 pymatgen 展开成 P1，唯一标签、
  `[0,1)` 分数坐标；原始 CIF 和已有默认 scene 响应不变。
- 前端构建需 Node 24+、Svelte 5 与 Vite Svelte 插件（`css:"injected"`），
  `svelte-widgets` override 为 npm `1.10.0`，避免浮动 Git 依赖。
- 验收基准是公开 Crystal Toolkit 默认行为；尚未验证 MP 官网当前页面逐像素一致。

---

## 六、Vite 构建配置

```typescript
// vite.config.ts - chunk 分割策略
build: {
  target: 'es2020',
  cssCodeSplit: true,
  rollupOptions: {
    output: {
      manualChunks(id) {
        if (!id.includes('node_modules')) return
        if (id.includes('recharts')) return 'vendor-recharts'                              // ~364KB
        if (id.includes('lucide-react')) return 'vendor-lucide'                            // ~22KB
        if (id.includes('react-dom') || id.includes('react-router')) return 'vendor-react' // ~224KB
        if (id.includes('/react/')) return 'vendor-react'
      },
    },
  },
},
base: '/CGCPT/',
define: { global: 'globalThis' },          // MP 及其 CommonJS 依赖需要
resolve: {
  dedupe: ['react', 'react-dom', 'react-is'], // 必须单份 React，否则 React #321
  alias: [/* react / react-dom / jsx-runtime 指向 web/node_modules */],
},
server: {
  proxy: {
    '/CGCPT/api/structure/scene': { target: 'http://127.0.0.1:18108', rewrite: () => '/scene' },
    '/CGCPT/api': { target: 'http://localhost:5000' },
  },
},
```

**当前构建产物大小**:
- `CrystalScene-*.js`: ~5.3MB（MP + three.js，懒加载，按需下载）
- `vendor-recharts-*.js`: 364KB（Dashboard 使用时加载）
- `vendor-react-*.js`: 224KB
- `StructureGenerator-*.js`: 40KB
- 各页面 JS: 10-33KB each
- CSS: 77KB + `CrystalScene.css` 2KB

---

## 七、后端 API 端点一览

### 基础 URL: `/api/`

> 例外：`POST /api/structure/scene` 由独立的 `scene_service.py` 提供（Caddy 直接转发到
> `127.0.0.1:18108`，前缀改写为 `/scene`），不经过 `api_server.py`；
> 该端点接受 `{"cif_text": "..."}` 或 `{"structure": {"lattice": {...}, "atoms": [...]}}`，
> 默认返回 Materials Project 场景 JSON；额外传入 `output:"cif"` 则返回
> `{"cif_text":"...","site_count":N}`，供对比引擎使用，详见 `docs/API.md`。

| 方法 | 路径 | 缓存 | 说明 |
|------|------|------|------|
| GET | `/health` | no-cache | 健康检查 (access_log off) |
| GET | `/stats` | **120s 内存缓存** | 统计数据 |
| GET | `/prototypes` | **300s 内存缓存** | 原型列表 |
| GET | `/prototypes/<id>` | - | 原型详情 |
| GET | `/materials` | - | 材料列表 (支持分页+筛选) |
| GET | `/materials/<id>` | - | 材料详情 (含 CIF 解析) |
| GET | `/materials/<id>/cif` | - | 下载原始 CIF |
| GET | `/search?q=` | - | 搜索材料 |
| GET | `/elements` | **300s 内存缓存** | 元素列表 |
| GET | `/classifications` | **300s 内存缓存** | 分类数据 |
| GET | `/lattice-types` | - | 层类型信息 |
| POST | `/generate` | - | 结构生成 (基础) |
| POST | `/generate/full` | - | 完整分析 (结构+原胞+配位+原型) |
| POST | `/generate/primitive` | - | 原胞分析 |
| POST | `/generate/coordination` | - | 配位环境分析 |
| POST | `/generate/layer-data` | - | 层数据 |
| POST | `/generate/prototype` | - | 原型文档 |
| POST | `/verify-topology` | - | 拓扑验证 |
| POST | `/stacking/train` | - | 训练堆垛模型 |
| POST | `/stacking/train/stream` | SSE | 流式训练进度 |
| POST | `/stacking/predict` | - | 堆垛预测 |
| POST | `/stacking/upload` | - | 上传 CIF 分析 |
| GET | `/stacking/models` | - | 列出模型 |
| DELETE | `/stacking/models/<id>` | - | 删除模型 |
| POST | `/stacking/analyze` | - | 分析 CIF |
| POST | `/stacking/batch_predict` | - | 批量预测 |

### API 缓存机制 (内存级)
```python
_api_cache = {}         # {cache_key: data}
_api_cache_ttl = {}     # {cache_key: expiry_timestamp}

def _get_cached(key):   # 检查是否过期
def _cached_json(key, data, ttl=300):  # 写入缓存
```
缓存端点: stats(120s), prototypes(300s), elements(300s), classifications(300s)

---

## 八、Caddy 路由要点

**配置文件**: `/opt/caddy/Caddyfile`（顶部 `import /opt/caddy/projects.caddy`）

CGCPT 使用路径前缀挂载，静态文件与两个后端分离：

```caddyfile
handle /CGCPT { redir * /CGCPT/ 308 }

# Materials Project 场景服务（必须在 api 通配之前命中）
handle /CGCPT/api/structure/scene {
    rewrite * /scene
    reverse_proxy 127.0.0.1:18108
}

handle /CGCPT/api/* {
    uri strip_prefix /CGCPT
    reverse_proxy 127.0.0.1:18020
}

handle_path /CGCPT/* {
    encode zstd gzip
    root * /opt/projects/cgcpt-web
    try_files {path} {path}/ /index.html
    file_server
    header /assets/* Cache-Control "public, max-age=31536000, immutable"
    header /index.html Cache-Control "no-cache"
}
```

**注意**:
- 小写 `/cgcpt/*` 同样配置了一份（旧链接兼容）
- 历史上残留的 18 个 `handle /CGCPT…` 旧块（指向 18019/18020）已清理；不要再添加重复块，否则会抢在正确路由之前命中
- 修改后必须 `caddy validate --config /opt/caddy/Caddyfile` 再 reload

---

## 九、Systemd 服务管理

**服务文件**: `/etc/systemd/system/projects-cgcpt{,-worker,-scene}.service`

| Unit | 作用 | 端口 | 内存上限 |
|------|------|------|----------|
| `projects-cgcpt` | Flask API (gunicorn, 1 worker × 2 threads) | 18020 | 448M |
| `projects-cgcpt-worker` | Celery worker | - | 384M |
| `projects-cgcpt-scene` | Crystal Toolkit 场景 JSON 服务 | 18108 | 560M |

三者均为 `Restart=no`、`is-enabled=static`，**不随系统启动**。

常用命令:
```bash
systemctl start projects-cgcpt projects-cgcpt-worker projects-cgcpt-scene
systemctl restart projects-cgcpt projects-cgcpt-scene
systemctl status projects-cgcpt-scene
journalctl -u projects-cgcpt-scene -f
tail -f /var/log/projects/cgcpt.log
```

宿主内存偏紧时，`projects-cgcpt-scene` 是唯一大头（导入 dash/plotly/matplotlib 所致），
`systemctl stop projects-cgcpt-scene` 可释放约 358MB，3D 区域不可用、其余功能不受影响。

---

## 十、监控与自动化

- 目前**没有** watchdog/crontab 自动拉起；服务异常需手动 `systemctl start`
- 日志写入 `/var/log/projects/cgcpt.log`、`cgcpt-worker.log`（systemd `append:` 重定向）
- 健康检查：`GET /CGCPT/api/health`（API）、`GET /healthz`（场景服务，仅本机）

---

## 十一、安全状态

### 已完成的安全加固
- [x] 清除挖矿木马 `/dev/shm/w.sh` (参数: astats/netai/kstats/ssh 2 ranges)
- [x] 清除恶意 crontab 条目 (@reboot + 每小时执行)
- [x] SSH 密钥认证 (ed25519)
- [x] `PermitRootLogin prohibit-password` (仅密钥)
- [x] `MaxAuthTries 3`
- [x] Fail2ban 运行中
- [x] `/dev/shm/` 已清空
- [x] authorized_keys 为空 (无未授权密钥)

### 待关注
- [ ] 建议更换 root 密码 (密码可能已泄露给攻击者)
- [ ] 检查阿里云安全组规则
- [ ] 定期检查 crontab 和 /dev/shm/

---

## 十二、部署流程

生产环境用 Caddy + 三个 systemd 服务，仓库里的 `nginx/`、`docker-compose.yml` 仅作备选部署方式。

### 前端部署
```bash
# 本地构建（产物在 web/dist）
cd web && npm run build

# 上传到服务器静态目录
rsync -av --delete web/dist/ aliyun:/opt/projects/cgcpt-web/
```

### 后端部署
```bash
# 源码目录
rsync -av --exclude .venv --exclude node_modules api_server.py scene_service.py \
    aliyun:/opt/projects/cgcpt/

# 场景服务依赖只在首次/升级时安装
ssh aliyun '/opt/projects/cgcpt/.venv/bin/pip install -r /opt/projects/cgcpt/requirements.txt'

systemctl restart projects-cgcpt projects-cgcpt-scene
```

### Caddy 路由（`/opt/caddy/projects.caddy`）
```caddyfile
handle /CGCPT/api/structure/scene {
    rewrite * /scene
    reverse_proxy 127.0.0.1:18108
}
handle /CGCPT/api/* {
    uri strip_prefix /CGCPT
    reverse_proxy 127.0.0.1:18020
}
handle_path /CGCPT/* {
    encode zstd gzip
    root * /opt/projects/cgcpt-web
    try_files {path} {path}/ /index.html
    file_server
}
```
修改后必须 `caddy validate --config /opt/caddy/Caddyfile` 再 `systemctl reload caddy`。

### 验证部署
```bash
curl -s  https://zsxw.asia/CGCPT/api/health               # API
curl -s -X POST https://zsxw.asia/CGCPT/api/structure/scene \
     -H 'Content-Type: application/json' \
     -d '{"structure":{"lattice":{"a":4.6,"b":4.6,"c":4.6,"alpha":90,"beta":90,"gamma":90},"atoms":[{"element":"Cs","x":0,"y":0,"z":0}]}}'
curl -sI http://localhost/CGCPT/                           # 前端
curl -s  http://127.0.0.1:18108/healthz                    # 场景服务（服务器本机）
```

---

## 十三、数据库概览

| 指标 | 数值 |
|------|------|
| 总材料数 | 2460 |
| 原型数 | 6 |
| 数据格式 | CIF (Crystallographic Information File) |
| 存储方式 | 文件系统 (按拓扑分组目录) |

### 目录命名规范
- `Raw_Proto_<topology_id>/` — 原始材料
- `Verified_Proto_<topology_id>/` — 已验证材料
- `Proto_<topology_id>.json` — 原型元数据

### 6 种拓扑原型
1. XO3-M7-XO3-M7-XO3-M7-XO3
2. XO-T-XO3-M7-XO3-M7-XO3-T-XO-T-XO3-M7-XO3-T-XO3
3. XO2-T-XO3-M7-XO3-T-XO2-T-XO3-M7-XO3-T-XO3
4. XO-T-XO3-M7-XO3-T-XO2-T-XO3
5. XO3-M7-XO3-T-XO2-T-XO3
6. XO-T-XO3-M7-XO3-T-XO3 (推测)

---

## 十四、已知问题与技术债务

1. **临时脚本过多**: 根目录有大量 `_*.py` 调试脚本（含失效的明文密码与 `D:\` 路径），建议清理或移至 `_archive/`
2. **密码已轮换**: 旧脚本里的 root 密码已失效，服务器仅允许密钥认证（`ssh aliyun`）
3. **MySQL/Redis**: 服务器上有 MySQL(3306) 和 Redis(6379) 供其他项目使用；CGCPT 当前使用 SQLite（`/opt/projects/cgcpt/data/cgcpt.db`）
4. **反向代理**: 生产使用 Caddy（`zsxw.asia/CGCPT/`），仓库内的 `nginx/` 配置仅作 Docker 部署备选
5. **HTTPS**: Caddy 自动签发证书；内网回源/健康检查仍可能走 HTTP

---

## 十五、开发命令速查

```bash
# 前端
cd web
npm run dev          # 开发服务器 (API → :5000, 场景 → :18108)
npm run build        # 生产构建
npm run preview      # 预览生产构建

# 后端 (本地)
python api_server.py                 # 直接运行 (debug, port 5000)
gunicorn scene_service:app -b 127.0.0.1:18108   # 场景服务

# 后端 (服务器)
ssh aliyun
systemctl restart projects-cgcpt projects-cgcpt-scene
tail -f /var/log/projects/cgcpt.log

# Caddy
caddy validate --config /opt/caddy/Caddyfile
systemctl reload caddy
```

---

## Suggested Skills (建议后续 Agent 加载的技能)

| 场景 | 技能名 |
|------|--------|
| 继续前端优化/新功能 | `web-dev`, `frontend-design` |
| UI 组件开发 | `web-artifacts-builder` |
| 性能诊断 | `diagnose` |
| 测试驱动开发 | `tdd` |
| 文档编写 | `doc-coauthoring` |
| 创建新技能 | `skill-creator` |
| 代码审查 | `triage` |
| 架构改进 | `improve-codebase-architecture` |
