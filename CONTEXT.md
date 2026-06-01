# CGCPT 项目完整上下文文档

> 生成时间: 2026-05-20
> 用途: 交接给其他 Agent 继续开发/运维

---

## 一、项目概述

**CGCPT** (Crystallographic Classification of Perovskite Topology) 是一个晶体材料分类与拓扑分析平台。

- **项目类型**: 全栈 Web 应用（React 前端 + Flask 后端）
- **本地路径**: `D:\Projects\CGCPT-Server\`
- **服务器**: 阿里云 ECS (Ubuntu)
- **域名**: `cgcpt.ink` (通过 Cloudflare DNS)

---

## 二、技术栈

### 前端 (`web/`)
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.x | UI 框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 8.x | 构建工具 |
| Tailwind CSS v4 | 4.x | 样式框架 |
| React Router v7 | 7.x | 路由管理 |
| Three.js / R3F / Drei | latest | 3D 晶体可视化 |
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
| Nginx | 反向代理 + 静态文件服务 + Brotli/Gzip 压缩 |
| Fail2ban | SSH 暴力破解防护 |
| systemd | 服务管理 (cgcpt.service) |
| Cloudflare | CDN + DNS (可选) |

---

## 三、服务器信息

```
IP: 118.31.164.41
用户: root
SSH 方式: 密钥认证 (ed25519)
私钥位置: D:\Projects\CGCPT-Server\id_ed25519
```

### SSH 连接方式
```bash
# 密钥登录 (推荐)
ssh -i D:\Projects\CGCPT-Server\id_ed25519 root@118.31.164.41

# SSH 配置: PermitRootLogin prohibit-password, MaxAuthTries=3, LoginGraceTime=30
# 注意: 密码登录已被禁用，仅允许密钥认证 root
```

### 关键路径 (服务器上)
| 路径 | 说明 |
|------|------|
| `/opt/CGCPT/` | 项目根目录 |
| `/opt/CGCPT/api_server.py` | Flask API 主文件 |
| `/opt/CGCPT/gunicorn.conf.py` | Gunicorn 配置 |
| `/opt/CGCPT/database/` | CIF 文件数据库 (~2460 个材料) |
| `/opt/CGCPT/root/CGCPT/` | Nginx 静态文件目录 (前端构建产物) |
| `/opt/CGCPT/watchdog.sh` | 健康看门狗脚本 |
| `/opt/CGCPT/venv/` | Python 虚拟环境 |
| `/etc/nginx/sites-available/ai-website` | Nginx 站点配置 |
| `/etc/systemd/system/cgcpt.service` | Systemd 服务文件 |

### 端口分配
| 端口 | 服务 | 监听地址 |
|------|------|----------|
| 80 | Nginx (HTTP) | 0.0.0.0 |
| 22 | SSH | 0.0.0.0 |
| 5001 | Gunicorn (API) | 127.0.0.1 |
| 3306 | MySQL | 127.0.0.1 |
| 6379 | Redis | 127.0.0.0 |

---

## 四、项目结构

```
D:\Projects\CGCPT-Server\
├── api_server.py              # Flask API 主入口 (~1725 行)
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
│   │   │   └── three/
│   │   │       ├── CrystalViewer.tsx  # 3D 晶体查看器 (懒加载!)
│   │   │       └── elementData.ts    # 元素数据 (颜色/半径/信息)
│   │   └── pages/
│   │       ├── Dashboard.tsx          # 仪表盘 (含周期表热力图)
│   │       ├── MaterialsBrowser.tsx   # 材料浏览
│   │       ├── MaterialDetail.tsx     # 材料详情 (含 CrystalViewer)
│   │       ├── PrototypesBrowser.tsx  # 原型浏览
│   │       ├── PrototypeDetail.tsx    # 原型详情 (含 CrystalViewer)
│   │       ├── StructureGenerator.tsx # 结构生成器 (含 2 处 CrystalViewer)
│   │       ├── StackingRecognizer.tsx # 堆垛识别
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
├── id_ed25519                 # SSH 私钥 (重要!)
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

**CrystalViewer 特殊处理**: 在 MaterialDetail、PrototypeDetail、StructureGenerator 中使用 `lazy(() => import(...))` + `<Suspense>` 包裹，Three.js (909KB) 仅在需要时加载。

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
        if (id.includes('three') || id.includes('@react-three')) return 'vendor-three'   // ~909KB
        if (id.includes('recharts')) return 'vendor-recharts'                              // ~364KB
        if (id.includes('lucide-react')) return 'vendor-lucide'                           // ~22KB
        if (id.includes('react-dom') || id.includes('react-router')) return 'vendor-react' // ~224KB
        if (id.includes('/react/')) return 'vendor-react'
      },
    },
  },
},
base: '/CGCPT/',
```

**当前构建产物大小**:
- `vendor-three-B9nyAaMl.js`: 909KB (懒加载)
- `vendor-recharts-IKSEBQ13.js`: 364KB (Dashboard 使用时加载)
- `vendor-react-BNPw1I5t.js`: 224KB
- `StructureGenerator-B-KJaKgu.js`: 40KB
- `CrystalViewer-9teT14lV.js`: 26KB (懒加载)
- 各页面 JS: 10-33KB each
- CSS: 72KB

---

## 七、后端 API 端点一览

### 基础 URL: `/api/`

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

## 八、Nginx 配置要点

**配置文件**: `/etc/nginx/sites-available/ai-website`

关键配置:
```nginx
server {
    listen 80;
    server_name cgcpt.ink www.cgcpt.ink;

    # 安全响应头
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location /CGCPT/ {
        alias /opt/CGCPT/root/CGCPT/;
        try_files $uri $uri/ /CGCPT/index.html;
    }

    # Health 端点关闭 access log
    location = /CGCPT/api/health {
        proxy_pass http://127.0.0.1:5001/api/health;
        access_log off;
    }

    location /CGCPT/api/ {
        proxy_pass http://127.0.0.1:5001/api/;
    }

    # 静态资源长期缓存 + Brotli 压缩
    location ~* \.(js|css|png|jpg|svg|ico|woff2?)$ {
        expires 365d;
        add_header Cache-Control "public, immutable";
        add_header Pragma public;
    }

    # Brotli 压缩 (已安装 ngx_brotli 模块)
    brotli on;
    brotli_comp_level 6;
    brotli_types text/plain text/css application/json application/javascript text/xml image/svg+xml;
}
```

**注意**: 已删除冲突的 `/etc/nginx/conf.d/cgcpt.conf` 和 `/etc/nginx/sites-available/cgcpt`，这些文件曾导致 ai-website server block 被忽略。

---

## 九、Systemd 服务管理

**服务文件**: `/etc/systemd/system/cgcpt.service`
```ini
[Unit]
Description=CGCPT API Server
After=network.target mysql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/CGCPT
ExecStart=/opt/CGCPT/venv/bin/python3 -m gunicorn \
    --config gunicorn.conf.py api_server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

常用命令:
```bash
systemctl start/restart/status/reload cgcpt
journalctl -u cgcpt -f  # 实时日志
```

Gunicorn 配置 (`gunicorn.conf.py`):
```python
bind = '0.0.0.0:5001'
workers = 2
worker_class = 'gthread'
threads = 2
timeout = 120
keepalive = 5
accesslog = '-'    # stdout → journalctl
errorlog = '-'
loglevel = 'info'
```

---

## 十、监控与自动化

### 健康看门狗 (`/opt/CGCPT/watchdog.sh`)
- 每 5 分钟执行 (crontab)
- 检查 API 是否响应
- 检查内存使用率 (>90% 自动重启)
- 日志自动轮转 (>1MB 截断)

### Logrotate 配置
| 文件 | 轮转周期 | 保留天数 |
|------|----------|----------|
| `/etc/logrotate.d/cgcpt-nginx` | 每天 | 7天 (压缩) |
| `/etc/logrotate.d/cgcpt-app` | 每天 | 5天 (copytruncate) |

### Crontab (root)
```
*/5 * * * * /opt/CGCPT/watchdog.sh
```

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

### 前端部署
```bash
# 本地构建
cd web && npm run build

# 上传到服务器 (SFTP)
# 清除旧文件:
rm -rf /opt/CGCPT/root/CGCPT/assets/ /opt/CGCPT/root/CGCPT/index.html
# 上传新文件:
#   index.html → /opt/CGCPT/root/CGCPT/index.html
#   assets/* → /opt/CGCPT/root/CGCPT/assets/
```

### 后端部署
```bash
# 上传 api_server.py 到 /opt/CGCPT/api_server.py
systemctl restart cgcpt
```

### 验证部署
```bash
curl -sI http://localhost/CGCPT/                    # 检查安全头
curl -s http://localhost/CGCPT/api/health            # 检查 API
curl -sI http://localhost/CGCPT/assets/vendor-three-*.js  # 检查缓存头
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

1. **临时脚本过多**: 根目录有大量 `_*.py` 调试脚本，建议清理或移至 `_archive/`
2. **密码可能泄露**: root 密码曾在多个脚本中出现，建议更换
3. **MySQL/Redis**: 服务器上有 MySQL(3306) 和 Redis(6379)，但当前应用未使用它们（全部使用文件系统存储）
4. **Cloudflare CDN**: 域名已接入 Cloudflare，但当前主要直接访问 IP 或使用非标准端口
5. **HTTPS**: 当前仅 HTTP (80)，未配置 SSL 证书

---

## 十五、开发命令速查

```bash
# 前端
cd web
npm run dev          # 开发服务器 (proxy to :5001)
npm run build        # 生产构建
npm run preview      # 预览生产构建

# 后端 (服务器上)
cd /opt/CGCPT
source venv/bin/activate
python api_server.py  # 直接运行 (debug mode, port 5000)
systemctl restart cgcpt  # 生产模式 (gunicorn, port 5001)

# Nginx
nginx -t             # 测试配置
systemctl reload nginx  # 重载配置
journalctl -u nginx -f  # 实时日志

# 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
journalctl -u cgcpt -f
cat /var/log/cgcpt_watchdog.log
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
