#!/usr/bin/env python3
import paramiko
import os
import sys
import time

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
REMOTE = "/opt/CGCPT"

local_base = os.path.dirname(os.path.abspath(__file__))


def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASS, timeout=30)
    return client


def run(client, cmd, timeout=300):
    print(f"  > {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="ignore")
    err = stderr.read().decode("utf-8", errors="ignore")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().split("\n")[:10]:
            print(f"    {line}")
    if err.strip() and code != 0:
        for line in err.strip().split("\n")[:5]:
            print(f"    ERR: {line}")
    return code, out, err


def upload_file(sftp, local, remote):
    os.makedirs(os.path.dirname(local), exist_ok=True)
    try:
        sftp.stat(os.path.dirname(remote))
    except FileNotFoundError:
        parts = remote.split("/")
        path = ""
        for p in parts[:-1]:
            path += "/" + p if path else "/" + p
            try:
                sftp.stat(path)
            except FileNotFoundError:
                sftp.mkdir(path)
    sftp.put(local, remote)
    print(f"  uploaded: {os.path.basename(local)} -> {remote}")


def upload_dir(sftp, local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        for f in files:
            local_path = os.path.join(root, f)
            rel = os.path.relpath(local_path, local_dir)
            remote_path = f"{remote_dir}/{rel.replace(os.sep, '/')}"
            upload_file(sftp, local_path, remote_path)


def main():
    print(f"Connecting to {HOST}...")
    client = ssh_connect()
    sftp = client.open_sftp()
    print("Connected!")

    print("\n=== Step 1: System optimization (swap + limits) ===")
    run(
        client,
        "swapon --show | grep -q cgcpt && echo 'swap exists' || (fallocate -l 2G /swapfile_cgcpt && chmod 600 /swapfile_cgcpt && mkswap /swapfile_cgcpt && swapon /swapfile_cgcpt && echo '/swapfile_cgcpt none swap sw 0 0' >> /etc/fstab && echo 'swap created')",
    )
    run(client, "sysctl vm.swappiness=30")
    run(client, "sysctl vm.vfs_cache_pressure=50")
    run(
        client,
        "grep -q 'vm.swappiness' /etc/sysctl.conf && sed -i 's/vm.swappiness=.*/vm.swappiness=30/' /etc/sysctl.conf || echo 'vm.swappiness=30' >> /etc/sysctl.conf",
    )
    run(
        client,
        "grep -q 'vm.vfs_cache_pressure' /etc/sysctl.conf && sed -i 's/vm.vfs_cache_pressure=.*/vm.vfs_cache_pressure=50/' /etc/sysctl.conf || echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf",
    )
    run(client, "free -h")

    print("\n=== Step 2: Install Python + pip ===")
    run(
        client,
        "which python3 || (apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv)",
        timeout=600,
    )
    run(client, "python3 --version")

    print("\n=== Step 3: Create venv + install deps ===")
    run(client, f"mkdir -p {REMOTE}")
    run(client, f"test -d {REMOTE}/venv || python3 -m venv {REMOTE}/venv")
    run(
        client,
        f"{REMOTE}/venv/bin/pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com",
        timeout=120,
    )
    run(
        client,
        f"{REMOTE}/venv/bin/pip install flask flask-cors gunicorn gevent numpy scikit-learn pymatgen -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com",
        timeout=600,
    )

    print("\n=== Step 4: Deploy backend code ===")
    backend_files = [
        "api_server.py",
        "stacking_analyzer.py",
        "stack_main.py",
        "verify_topology.py",
        "gunicorn.conf.py",
    ]
    for f in backend_files:
        local_path = os.path.join(local_base, f)
        if os.path.exists(local_path):
            upload_file(sftp, local_path, f"{REMOTE}/{f}")
        else:
            print(f"  SKIP (not found): {f}")

    print("\n=== Step 5: Deploy database ===")
    db_dir = os.path.join(local_base, "database")
    if os.path.exists(db_dir):
        print("  Uploading database (this may take a while)...")
        upload_dir(sftp, db_dir, f"{REMOTE}/database")
    else:
        print("  SKIP: database directory not found locally")

    print("\n=== Step 6: Deploy model ===")
    models_dir = os.path.join(local_base, "models")
    if os.path.exists(models_dir):
        run(client, f"mkdir -p {REMOTE}/models")
        for f in os.listdir(models_dir):
            local_path = os.path.join(models_dir, f)
            if os.path.isfile(local_path):
                upload_file(sftp, local_path, f"{REMOTE}/models/{f}")
    else:
        run(client, f"mkdir -p {REMOTE}/models")
        print("  No local models directory, creating empty models dir on server")

    print("\n=== Step 7: Deploy test CIF files ===")
    test_dir = os.path.join(local_base, "test_cifs")
    if os.path.exists(test_dir):
        run(client, f"mkdir -p {REMOTE}/test_cifs")
        for f in os.listdir(test_dir):
            local_path = os.path.join(test_dir, f)
            if os.path.isfile(local_path):
                upload_file(sftp, local_path, f"{REMOTE}/test_cifs/{f}")

    print("\n=== Step 8: Deploy frontend ===")
    web_dist = os.path.join(local_base, "web", "dist")
    if os.path.exists(web_dist):
        print("  Uploading frontend build...")
        upload_dir(sftp, web_dist, f"{REMOTE}/web/dist")
    else:
        print("  No frontend build found, will build on server or skip")

    print("\n=== Step 9: Create systemd service ===")
    service_content = f"""[Unit]
Description=CGCPT API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={REMOTE}
ExecStart={REMOTE}/venv/bin/gunicorn -c gunicorn.conf.py api_server:app
Restart=always
RestartSec=10
Environment=PYTHONPATH={REMOTE}
Environment=MALLOC_ARENA_MAX=2
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
"""
    with open(os.path.join(local_base, "_cgcpt.service"), "w") as f:
        f.write(service_content)
    upload_file(
        sftp, os.path.join(local_base, "_cgcpt.service"), "/etc/systemd/system/cgcpt.service"
    )
    run(client, "systemctl daemon-reload")
    run(client, "systemctl enable cgcpt")

    print("\n=== Step 10: Create nginx config ===")
    nginx_conf = """server {
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
"""
    with open(os.path.join(local_base, "_cgcpt_nginx"), "w") as f:
        f.write(nginx_conf)
    upload_file(sftp, os.path.join(local_base, "_cgcpt_nginx"), "/etc/nginx/sites-available/cgcpt")
    run(client, "which nginx || (apt-get update -qq && apt-get install -y -qq nginx)", timeout=300)
    run(client, "ln -sf /etc/nginx/sites-available/cgcpt /etc/nginx/sites-enabled/cgcpt")
    run(client, "rm -f /etc/nginx/sites-enabled/default")
    run(client, "nginx -t && systemctl enable nginx")

    print("\n=== Step 11: Restart services ===")
    run(client, "systemctl restart cgcpt")
    time.sleep(3)
    run(client, "systemctl status cgcpt --no-pager -l | head -20")
    run(client, "systemctl restart nginx")
    time.sleep(2)
    run(client, "systemctl status nginx --no-pager -l | head -10")

    print("\n=== Step 12: Verify ===")
    run(client, "sleep 3 && curl -s http://localhost:5001/api/stats | head -200")
    run(client, "curl -s http://localhost/api/stats | head -200")

    print("\n=== Cleanup temp files ===")
    for f in ["_cgcpt.service", "_cgcpt_nginx"]:
        p = os.path.join(local_base, f)
        if os.path.exists(p):
            os.remove(p)

    sftp.close()
    client.close()
    print(f"\nDeployment complete! Access at http://{HOST}")


if __name__ == "__main__":
    main()
