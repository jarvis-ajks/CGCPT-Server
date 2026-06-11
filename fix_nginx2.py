import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("118.31.164.41", username="root", password="Aa123456", timeout=30)


def run(cmd):
    print(f"$ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if out.strip():
        print(out.strip()[:3000])
    if err.strip():
        print("[stderr]", err.strip()[:1000])


sftp = ssh.open_sftp()

print("=== 1. Create symlink so root directive works ===")
run("ln -sfn /opt/CGCPT/frontend /opt/CGCPT/root/CGCPT")

print()
print("=== 2. Debug: test alias directly ===")
run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/CGCPT/index.html')
run("curl -s http://127.0.0.1/CGCPT/index.html | head -c 200")

print()
print("=== 3. Update nginx config with root + symlink approach ===")
with sftp.open("/etc/nginx/sites-available/ai-website", "r") as f:
    config = f.read().decode("utf-8")

old_cgcpt = """    location /CGCPT/assets/ {
        alias /opt/CGCPT/frontend/assets/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /CGCPT/ {
        alias /opt/CGCPT/frontend/;
        index index.html;
        try_files $uri $uri/ /CGCPT/index.html;
    }

    location = /CGCPT {
        return 301 /CGCPT/;
    }"""

new_cgcpt = """    location /CGCPT/ {
        alias /opt/CGCPT/frontend/;
        index index.html;
    }

    location /CGCPT/assets/ {
        alias /opt/CGCPT/frontend/assets/;
    }

    location = /CGCPT {
        return 301 /CGCPT/;
    }"""

config = config.replace(old_cgcpt, new_cgcpt)

with sftp.open("/etc/nginx/sites-available/ai-website", "w") as f:
    f.write(config)

run("nginx -t")
run("systemctl reload nginx")

import time

time.sleep(2)

print()
print("=== 4. Test after fix ===")
run('curl -s -o /dev/null -w "index.html: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/')
run(
    'curl -s -o /dev/null -w "JS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-CfCqO3cC.js'
)
run(
    'curl -s -o /dev/null -w "CSS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-BqpHRU_p.css'
)
run(
    'curl -s -o /dev/null -w "SVG: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/favicon.svg'
)

sftp.close()
ssh.close()
