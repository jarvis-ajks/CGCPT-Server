#!/bin/bash
set -e

echo "=== CGCPT Server Setup Script ==="
echo "Optimized for 2-core 2GB server"

echo ""
echo "=== Step 1: System optimization ==="
if ! swapon --show | grep -q cgcpt; then
    fallocate -l 2G /swapfile_cgcpt 2>/dev/null || dd if=/dev/zero of=/swapfile_cgcpt bs=1M count=2048
    chmod 600 /swapfile_cgcpt
    mkswap /swapfile_cgcpt
    swapon /swapfile_cgcpt
    grep -q 'swapfile_cgcpt' /etc/fstab || echo '/swapfile_cgcpt none swap sw 0 0' >> /etc/fstab
    echo "Swap created"
else
    echo "Swap already exists"
fi
sysctl -w vm.swappiness=30
sysctl -w vm.vfs_cache_pressure=50
grep -q 'vm.swappiness=30' /etc/sysctl.conf || echo 'vm.swappiness=30' >> /etc/sysctl.conf
grep -q 'vm.vfs_cache_pressure=50' /etc/sysctl.conf || echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
free -h

echo ""
echo "=== Step 2: Install dependencies ==="
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx

echo ""
echo "=== Step 3: Create venv + install Python packages ==="
cd /opt/CGCPT
test -d venv || python3 -m venv venv
venv/bin/pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
venv/bin/pip install flask flask-cors gunicorn gevent numpy scikit-learn pymatgen -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

echo ""
echo "=== Step 4: Create systemd service ==="
cat > /etc/systemd/system/cgcpt.service << 'EOF'
[Unit]
Description=CGCPT API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/CGCPT
ExecStart=/opt/CGCPT/venv/bin/gunicorn -c gunicorn.conf.py api_server:app
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/CGCPT
Environment=MALLOC_ARENA_MAX=2
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable cgcpt

echo ""
echo "=== Step 5: Configure nginx ==="
cat > /etc/nginx/sites-available/cgcpt << 'EOF'
server {
    listen 80;
    server_name _;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    location / {
        root /opt/CGCPT/web/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    client_max_body_size 20M;
}
EOF
ln -sf /etc/nginx/sites-available/cgcpt /etc/nginx/sites-enabled/cgcpt
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx

echo ""
echo "=== Step 6: Start services ==="
systemctl restart cgcpt
sleep 3
systemctl status cgcpt --no-pager -l | head -15
systemctl restart nginx
sleep 2

echo ""
echo "=== Step 7: Verify ==="
sleep 3
curl -s http://localhost:5001/api/stats | python3 -m json.tool | head -20
echo ""
curl -s http://localhost/api/stats | python3 -m json.tool | head -5

echo ""
echo "=== Done! ==="
echo "Access your CGCPT platform at http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Useful commands:"
echo "  systemctl status cgcpt    - Check API server status"
echo "  systemctl restart cgcpt   - Restart API server"
echo "  journalctl -u cgcpt -f   - View API server logs"
echo "  free -h                   - Check memory usage"
