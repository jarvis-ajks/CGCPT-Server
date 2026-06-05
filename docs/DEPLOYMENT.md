# CGCPT 部署指南

> 本文档详细描述 CGCPT 系统的各种部署方式，从本地开发到生产环境。

---

## 目录

- [系统要求](#系统要求)
- [本地开发部署](#本地开发部署)
- [生产部署（Gunicorn + Nginx）](#生产部署gunicorn--nginx)
- [Docker 部署](#docker-部署)
- [云服务器部署](#云服务器部署)
- [数据库配置](#数据库配置)
- [SSL 配置](#ssl-配置)
- [性能调优](#性能调优)
- [监控与维护](#监控与维护)

---

## 系统要求

### 最低配置

| 组件 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 4 GB |
| 磁盘 | 20 GB SSD |
| 操作系统 | Ubuntu 22.04 LTS / CentOS 8+ / Debian 12+ |

### 推荐配置

| 组件 | 要求 |
|------|------|
| CPU | 4 核+ |
| 内存 | 8 GB+ |
| 磁盘 | 50 GB SSD |
| 操作系统 | Ubuntu 22.04 LTS |

### 软件依赖

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| MySQL | 8.0+ | 结构化数据存储（可选） |
| Redis | 7.0+ | 任务队列 + 缓存（可选） |
| Nginx | 1.24+ | 反向代理 + 静态文件 |
| Gunicorn | 21+ | WSGI 服务器 |

### Python 依赖

```
flask
flask-cors
numpy
pymatgen
gunicorn
sqlalchemy
pymysql
celery
redis
scikit-learn
joblib
psutil
```

---

## 本地开发部署

### 1. 后端

```bash
# 克隆项目
git clone https://github.com/cgcpt/cgcpt-server.git
cd cgcpt-server

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 启动 Flask 开发服务器
python api_server.py
# 运行在 http://localhost:5000
# 自动加载 database/ 目录下的 CIF 文件
```

### 2. 前端

```bash
cd web

# 安装依赖
npm install

# 启动 Vite 开发服务器
npm run dev
# 运行在 http://localhost:5173
# API 请求自动代理到 http://localhost:5000
```

### 3. 可选服务

```bash
# MySQL（如需数据库功能）
sudo systemctl start mysql
mysql -u root -p -e "CREATE DATABASE cgcpt CHARACTER SET utf8mb4;"

# Redis（如需任务队列）
sudo systemctl start redis
```

---

## 生产部署（Gunicorn + Nginx）

### 1. 服务器初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y python3 python3-pip python3-venv \
  nginx mysql-server redis-server \
  build-essential python3-dev

# 安装 Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. 部署后端

```bash
# 创建项目目录
sudo mkdir -p /opt/CGCPT
sudo chown $USER:$USER /opt/CGCPT

# 上传项目文件（从本地）
scp -r api_server.py stack_main.py stacking_analyzer.py \
  verify_topology.py models.py task_worker.py task_engine.py \
  self_improver.py cgcpt_plugin.py data_tools.py \
  gunicorn.conf.py requirements.txt database/ plugins/ \
  user@server:/opt/CGCPT/

# 在服务器上
cd /opt/CGCPT

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn pymysql celery redis scikit-learn joblib psutil
```

### 3. 配置 Gunicorn

编辑 `/opt/CGCPT/gunicorn.conf.py`：

```python
bind = "0.0.0.0:5001"
workers = 2              # 推荐: (2 × CPU核心) + 1
worker_class = "gthread"
threads = 4              # 每 Worker 线程数
timeout = 300            # 结构生成可能耗时较长
keepalive = 5
preload_app = False
max_requests = 500       # Worker 自动重启，防止内存泄漏
max_requests_jitter = 50
graceful_timeout = 30
worker_tmp_dir = "/dev/shm"
loglevel = "info"
accesslog = "-"
errorlog = "-"
```

### 4. 配置 Systemd 服务

创建 `/etc/systemd/system/cgcpt.service`：

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
Environment=CGCPT_DB_URL=mysql+pymysql://cgcpt:YOUR_PASSWORD@127.0.0.1:3306/cgcpt?charset=utf8mb4

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable cgcpt
sudo systemctl start cgcpt
sudo systemctl status cgcpt
```

### 5. 构建并部署前端

```bash
# 本地构建
cd web
npm install
npm run build

# 上传构建产物到服务器
scp -r dist/* user@server:/opt/CGCPT/root/CGCPT/
```

### 6. 配置 Nginx

创建 `/etc/nginx/sites-available/cgcpt`：

```nginx
server {
    listen 80;
    server_name cgcpt.ink www.cgcpt.ink;

    # 安全响应头
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # 前端静态文件
    location /CGCPT/ {
        alias /opt/CGCPT/root/CGCPT/;
        try_files $uri $uri/ /CGCPT/index.html;
    }

    # Health 端点关闭 access log
    location = /CGCPT/api/health {
        proxy_pass http://127.0.0.1:5001/api/health;
        access_log off;
    }

    # API 代理
    location /CGCPT/api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # 静态资源长期缓存
    location ~* /CGCPT/assets/.*\.(js|css|png|jpg|svg|ico|woff2?)$ {
        alias /opt/CGCPT/root/CGCPT/;
        rewrite ^/CGCPT/assets/(.*)$ /assets/$1 break;
        expires 365d;
        add_header Cache-Control "public, immutable";
    }

    # Brotli 压缩（需安装 ngx_brotli 模块）
    # brotli on;
    # brotli_comp_level 6;
    # brotli_types text/plain text/css application/json application/javascript text/xml image/svg+xml;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/plain text/css application/json application/javascript text/xml image/svg+xml;
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/cgcpt /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /opt/CGCPT

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    gunicorn pymysql celery redis scikit-learn joblib psutil

# 复制项目文件
COPY api_server.py stack_main.py stacking_analyzer.py \
    verify_topology.py models.py task_worker.py task_engine.py \
    self_improver.py cgcpt_plugin.py data_tools.py \
    gunicorn.conf.py ./
COPY database/ database/
COPY plugins/ plugins/

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["gunicorn", "--config", "gunicorn.conf.py", "api_server:app"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "5001:5001"
    environment:
      - CGCPT_DB_URL=mysql+pymysql://cgcpt:cgcpt_password@db:3306/cgcpt?charset=utf8mb4
      - CELERY_BROKER=redis://redis:6379/0
      - CELERY_BACKEND=redis://redis:6379/1
    depends_on:
      - db
      - redis
    volumes:
      - ./database:/opt/CGCPT/database
      - ./models:/opt/CGCPT/models
    restart: always

  worker:
    build: .
    command: celery -A task_worker.celery_app worker --loglevel=info
    environment:
      - CGCPT_DB_URL=mysql+pymysql://cgcpt:cgcpt_password@db:3306/cgcpt?charset=utf8mb4
      - CELERY_BROKER=redis://redis:6379/0
      - CELERY_BACKEND=redis://redis:6379/1
    depends_on:
      - db
      - redis
    volumes:
      - ./database:/opt/CGCPT/database
      - ./models:/opt/CGCPT/models
    restart: always

  nginx:
    image: nginx:1.24-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./web/dist:/opt/CGCPT/root/CGCPT
    depends_on:
      - api
    restart: always

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=cgcpt
      - MYSQL_USER=cgcpt
      - MYSQL_PASSWORD=cgcpt_password
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

volumes:
  mysql_data:
  redis_data:
```

### 3. 启动

```bash
# 构建前端
cd web && npm install && npm run build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 执行数据库迁移
docker-compose exec api python -c "from models import init_db; init_db()"
docker-compose exec api curl -X POST http://localhost:5001/api/db/migrate
```

---

## 云服务器部署

### 阿里云 ECS 部署

#### 1. 创建 ECS 实例

- 规格：ecs.c6.large（2C4G）或更高
- 镜像：Ubuntu 22.04 LTS
- 磁盘：40 GB SSD
- 安全组：开放 80、443、22 端口

#### 2. DNS 配置

在 Cloudflare 或阿里云 DNS 添加：

```
A    cgcpt.ink        →  服务器IP
A    www.cgcpt.ink    →  服务器IP
```

#### 3. 部署步骤

```bash
# SSH 登录
ssh root@YOUR_SERVER_IP

# 按照生产部署步骤操作
# ...
```

#### 4. Cloudflare CDN 配置（可选）

- 开启代理（橙色云朵）
- SSL 模式：Full (Strict)
- 开启 Brotli 压缩
- 缓存规则：静态资源缓存，API 不缓存

---

## 数据库配置

### MySQL 安装与配置

```bash
# 安装 MySQL
sudo apt install -y mysql-server

# 安全初始化
sudo mysql_secure_installation

# 创建数据库和用户
sudo mysql -u root -p
```

```sql
CREATE DATABASE cgcpt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cgcpt'@'localhost' IDENTIFIED BY 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON cgcpt.* TO 'cgcpt'@'localhost';
FLUSH PRIVILEGES;
```

### MySQL 性能调优

编辑 `/etc/mysql/mysql.conf.d/cgcpt.cnf`：

```ini
[mysqld]
# 连接配置
max_connections = 100
wait_timeout = 600

# InnoDB 配置
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_method = O_DIRECT

# 字符集
character_set_server = utf8mb4
collation_server = utf8mb4_unicode_ci
```

### 数据库迁移

```bash
# 从文件系统迁移到 MySQL
curl -X POST http://localhost:5001/api/db/migrate

# 或使用部署脚本
python deploy_server.py
```

### 数据备份

```bash
# MySQL 备份
mysqldump -u cgcpt -p cgcpt > backup_$(date +%Y%m%d).sql

# 使用内置工具
python data_tools.py backup
```

---

## SSL 配置

### 使用 Let's Encrypt（推荐）

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d cgcpt.ink -d www.cgcpt.ink

# 自动续期（Certbot 自动添加 cron）
sudo certbot renew --dry-run
```

### 手动 SSL 配置

编辑 Nginx 配置：

```nginx
server {
    listen 443 ssl http2;
    server_name cgcpt.ink www.cgcpt.ink;

    ssl_certificate /etc/letsencrypt/live/cgcpt.ink/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cgcpt.ink/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # ... 其他 location 配置同上
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name cgcpt.ink www.cgcpt.ink;
    return 301 https://$host$request_uri;
}
```

### Cloudflare SSL

如使用 Cloudflare CDN：

1. SSL/TLS 模式设为 **Full (Strict)**
2. 安装 Cloudflare Origin 证书到服务器
3. Nginx 配置使用 Origin 证书路径

---

## 性能调优

### Gunicorn 调优

```python
# gunicorn.conf.py

# Worker 数量：推荐 (2 × CPU核心) + 1
import multiprocessing
workers = multiprocessing.cpu_count() * 2 + 1

# 线程数
threads = 4

# Worker 类型
worker_class = "gthread"

# 超时（结构生成可能耗时较长）
timeout = 300

# 内存泄漏防护
max_requests = 500
max_requests_jitter = 50

# Worker 临时目录（使用内存文件系统）
worker_tmp_dir = "/dev/shm"
```

### Nginx 调优

```nginx
# 全局配置 /etc/nginx/nginx.conf

worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # 连接优化
    keepalive_timeout 65;
    keepalive_requests 100;

    # 缓冲
    client_body_buffer_size 16K;
    client_header_buffer_size 1k;
    client_max_body_size 50m;  # 允许上传较大 CIF 文件

    # 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript text/xml image/svg+xml;

    # 开启 Brotli（需安装模块）
    # brotli on;
    # brotli_comp_level 6;
}
```

### API 缓存策略

系统内置内存级缓存：

| 端点 | 缓存时间 | 说明 |
|------|----------|------|
| `/api/stats` | 120s | 统计数据 |
| `/api/prototypes` | 300s | 原型列表 |
| `/api/elements` | 300s | 元素列表 |
| `/api/classifications` | 300s | 分类数据 |
| `/api/health` | no-cache | 健康检查 |
| `/api/stacking/*` | no-store | 预测结果 |

### 前端优化

- **代码分割**：Three.js (~909KB) 懒加载
- **路由懒加载**：所有页面组件 `React.lazy()`
- **鼠标悬停预加载**：Sidebar `onMouseEnter` 触发
- **静态资源缓存**：365 天 + immutable
- **Brotli/Gzip 压缩**：JS/CSS/JSON/SVG

---

## 监控与维护

### 健康看门狗

创建 `/opt/CGCPT/watchdog.sh`：

```bash
#!/bin/bash
# CGCPT Health Watchdog

LOG="/var/log/cgcpt_watchdog.log"
MAX_LOG_SIZE=1048576  # 1MB

# 日志轮转
if [ -f "$LOG" ] && [ $(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null) -gt $MAX_LOG_SIZE ]; then
    truncate -s 0 "$LOG"
fi

# 检查 API 健康状态
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/api/health)

if [ "$HEALTH" != "200" ]; then
    echo "$(date): API unhealthy (HTTP $HEALTH), restarting..." >> "$LOG"
    systemctl restart cgcpt
fi

# 检查内存使用
MEM_PERCENT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_PERCENT" -gt 90 ]; then
    echo "$(date): High memory usage ($MEM_PERCENT%), restarting..." >> "$LOG"
    systemctl restart cgcpt
fi
```

```bash
# 添加到 crontab
chmod +x /opt/CGCPT/watchdog.sh
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/CGCPT/watchdog.sh") | crontab -
```

### 日志轮转

创建 `/etc/logrotate.d/cgcpt-nginx`：

```
/var/log/nginx/access.log /var/log/nginx/error.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
```

创建 `/etc/logrotate.d/cgcpt-app`：

```
/var/log/cgcpt_watchdog.log {
    daily
    rotate 5
    copytruncate
    missingok
    notifempty
}
```

### 常用运维命令

```bash
# 服务管理
sudo systemctl start cgcpt        # 启动
sudo systemctl stop cgcpt         # 停止
sudo systemctl restart cgcpt      # 重启
sudo systemctl status cgcpt       # 状态

# 日志查看
journalctl -u cgcpt -f            # 实时 API 日志
journalctl -u cgcpt --since today # 今日日志
tail -f /var/log/nginx/access.log # Nginx 访问日志
tail -f /var/log/nginx/error.log  # Nginx 错误日志

# Nginx
sudo nginx -t                     # 测试配置
sudo systemctl reload nginx       # 重载配置

# 数据库
python data_tools.py backup       # 备份
python data_tools.py export materials  # 导出

# 健康检查
curl http://localhost:5001/api/health
curl http://localhost/CGCPT/api/health
```

### 安全加固

```bash
# SSH 加固
sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sudo sed -i 's/#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# 安装 Fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 防火墙
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
