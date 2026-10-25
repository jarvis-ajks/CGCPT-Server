"""Deploy CGCPT-Server to cloud server - step by step with long timeouts."""
import paramiko
import time
import sys

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
APP_DIR = "/opt/CGCPT"


def run(ssh, cmd, timeout=600):
    """Execute command on remote server with long timeout."""
    print(f"  > {cmd[:150]}...")
    sys.stdout.flush()
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        lines = out.strip().split("\n")
        for line in lines[-15:]:
            print(f"    {line}")
    if err.strip() and code != 0:
        lines = err.strip().split("\n")
        for line in lines[-5:]:
            print(f"    ERR: {line}")
    print(f"    [exit: {code}]")
    sys.stdout.flush()
    return out, err, code


def main():
    print(f"Connecting to {HOST}...")
    sys.stdout.flush()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(HOST, port=22, username=USER, password=PASS, timeout=60, banner_timeout=60, auth_timeout=60)
        print("Connected!\n")
        sys.stdout.flush()

        # Step 1: System update
        print("=" * 60)
        print("Step 1: System update")
        print("=" * 60)
        run(ssh, "apt-get update -qq 2>&1 | tail -3", timeout=120)
        print()

        # Step 2: Install packages one by one
        print("=" * 60)
        print("Step 2: Install packages")
        print("=" * 60)
        packages = ["python3", "python3-pip", "python3-venv", "git", "nginx", "mysql-server", "libopenblas-dev"]
        for pkg in packages:
            run(ssh, f"apt-get install -y -qq {pkg} 2>&1 | tail -3", timeout=300)
        print()

        # Step 3: Configure MySQL
        print("=" * 60)
        print("Step 3: Configure MySQL")
        print("=" * 60)
        run(ssh, "systemctl start mysql && systemctl enable mysql", timeout=30)
        run(ssh, "mysql -u root -e \"CREATE DATABASE IF NOT EXISTS cgcpt DEFAULT CHARACTER SET utf8mb4;\"", timeout=30)
        run(ssh, "mysql -u root -e \"CREATE USER IF NOT EXISTS 'cgcpt'@'localhost' IDENTIFIED BY 'cgcpt2024';\"", timeout=30)
        run(ssh, "mysql -u root -e \"GRANT ALL ON cgcpt.* TO 'cgcpt'@'localhost'; FLUSH PRIVILEGES;\"", timeout=30)
        print()

        # Step 4: Clone from GitHub
        print("=" * 60)
        print("Step 4: Clone from GitHub")
        print("=" * 60)
        run(ssh, f"rm -rf {APP_DIR}", timeout=30)
        run(ssh, f"git clone https://github.com/jarvis-ajks/CGCPT-Server.git {APP_DIR} 2>&1 | tail -5", timeout=120)
        print()

        # Step 5: Setup Python venv
        print("=" * 60)
        print("Step 5: Setup Python environment")
        print("=" * 60)
        run(ssh, f"python3 -m venv {APP_DIR}/venv", timeout=60)
        run(ssh, f"{APP_DIR}/venv/bin/pip install --upgrade pip -q", timeout=60)
        run(ssh, f"{APP_DIR}/venv/bin/pip install -r {APP_DIR}/requirements.txt 2>&1 | tail -10", timeout=600)
        print()

        # Step 6: Configure environment
        print("=" * 60)
        print("Step 6: Configure environment")
        print("=" * 60)
        run(ssh, f"cat > {APP_DIR}/.env << 'EOF'\nCGCPT_DB_URL=mysql+pymysql://cgcpt:cgcpt2024@localhost/cgcpt\nCGCPT_HOST=0.0.0.0\nCGCPT_PORT=5000\nCGCPT_DEBUG=false\nCGCPT_SECRET_KEY=cgcpt-prod-2024\nCGCPT_ADMIN_USER=admin\nCGCPT_ADMIN_PASS=cgcpt2024admin\nCGCPT_CORS_ORIGINS=*\nCGCPT_LOG_LEVEL=INFO\nEOF", timeout=10)
        print()

        # Step 7: Initialize database
        print("=" * 60)
        print("Step 7: Initialize database")
        print("=" * 60)
        run(ssh, f"""cd {APP_DIR} && {APP_DIR}/venv/bin/python3 -c "
import os
os.environ['CGCPT_DB_URL']='mysql+pymysql://cgcpt:cgcpt2024@localhost/cgcpt'
from models import init_db, SessionLocal, migrate_from_filesystem
init_db()
print('DB tables created')
result = migrate_from_filesystem(SessionLocal())
print('Imported:', result.get('imported_prototypes', 0), 'prototypes,', result.get('imported_materials', 0), 'materials')
" 2>&1""", timeout=300)
        print()

        # Step 8: Build frontend
        print("=" * 60)
        print("Step 8: Build frontend")
        print("=" * 60)
        run(ssh, "which node || (curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && apt-get install -y nodejs) 2>&1 | tail -5", timeout=300)
        run(ssh, f"cd {APP_DIR}/web && npm install 2>&1 | tail -5", timeout=300)
        run(ssh, f"cd {APP_DIR}/web && npm run build 2>&1 | tail -10", timeout=300)
        print()

        # Step 9: Configure Gunicorn
        print("=" * 60)
        print("Step 9: Configure Gunicorn service")
        print("=" * 60)
        run(ssh, f"cat > /etc/systemd/system/cgcpt.service << 'EOF'\n[Unit]\nDescription=CGCPT Gunicorn Server\nAfter=network.target mysql.service\n\n[Service]\nUser=root\nWorkingDirectory={APP_DIR}\nEnvironmentFile={APP_DIR}/.env\nExecStart={APP_DIR}/venv/bin/gunicorn api_server:app -c gunicorn.conf.py -b 0.0.0.0:5000\nRestart=always\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\nEOF", timeout=10)
        run(ssh, "systemctl daemon-reload", timeout=10)
        run(ssh, "systemctl enable cgcpt", timeout=10)
        run(ssh, "systemctl restart cgcpt", timeout=30)
        time.sleep(3)
        run(ssh, "systemctl status cgcpt --no-pager 2>&1 | head -15", timeout=10)
        print()

        # Step 10: Configure Nginx
        print("=" * 60)
        print("Step 10: Configure Nginx")
        print("=" * 60)
        run(ssh, f"cat > /etc/nginx/sites-available/cgcpt << 'EOF'\nserver {{\n    listen 80;\n    server_name _;\n    client_max_body_size 50M;\n\n    location /CGCPT/ {{\n        alias {APP_DIR}/web/dist/;\n        try_files \\$uri \\$uri/ /CGCPT/index.html;\n    }}\n\n    location /CGCPT/assets/ {{\n        alias {APP_DIR}/web/dist/assets/;\n        expires 30d;\n    }}\n\n    location /api/ {{\n        proxy_pass http://127.0.0.1:5000/api/;\n        proxy_set_header Host \\$host;\n        proxy_set_header X-Real-IP \\$remote_addr;\n        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;\n        proxy_buffering off;\n        proxy_read_timeout 300s;\n    }}\n\n    location = / {{\n        return 302 /CGCPT/;\n    }}\n}}\nEOF", timeout=10)
        run(ssh, "rm -f /etc/nginx/sites-enabled/default", timeout=5)
        run(ssh, "ln -sf /etc/nginx/sites-available/cgcpt /etc/nginx/sites-enabled/cgcpt", timeout=5)
        run(ssh, "nginx -t 2>&1", timeout=10)
        run(ssh, "systemctl restart nginx && systemctl enable nginx", timeout=10)
        print()

        # Step 11: Verify
        print("=" * 60)
        print("Step 11: Verify all services")
        print("=" * 60)
        time.sleep(5)
        run(ssh, "curl -s http://localhost/api/health 2>&1", timeout=15)
        run(ssh, "curl -s http://localhost/api/stats 2>&1 | python3 -m json.tool 2>&1 | head -10", timeout=15)
        run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost/CGCPT/ 2>&1", timeout=15)
        print()

        # Step 12: Firewall
        print("=" * 60)
        print("Step 12: Configure firewall")
        print("=" * 60)
        run(ssh, "ufw allow 22/tcp 2>&1 | tail -1", timeout=10)
        run(ssh, "ufw allow 80/tcp 2>&1 | tail -1", timeout=10)
        run(ssh, "ufw allow 443/tcp 2>&1 | tail -1", timeout=10)
        run(ssh, "echo 'y' | ufw enable 2>&1 | tail -1", timeout=10)
        print()

        print("=" * 60)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print(f"  Frontend: http://{HOST}/CGCPT/")
        print(f"  API:      http://{HOST}/api/health")
        sys.stdout.flush()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
