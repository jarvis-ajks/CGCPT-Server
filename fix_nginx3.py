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

print("=== 1. Create directory structure for root directive ===")
run("mkdir -p /opt/CGCPT/root")
run("ln -sfn /opt/CGCPT/frontend /opt/CGCPT/root/CGCPT")
run("ls -la /opt/CGCPT/root/")
run("ls -la /opt/CGCPT/root/CGCPT/")

print()
print("=== 2. Update nginx config - use root instead of alias ===")
with sftp.open("/etc/nginx/sites-available/ai-website", "r") as f:
    config = f.read().decode("utf-8")

old_cgcpt = """    location /CGCPT/ {
        alias /opt/CGCPT/frontend/;
        index index.html;
    }

    location /CGCPT/assets/ {
        alias /opt/CGCPT/frontend/assets/;
    }

    location = /CGCPT {
        return 301 /CGCPT/;
    }"""

new_cgcpt = """    location /CGCPT {
        root /opt/CGCPT/root;
        index index.html;
        try_files $uri $uri/ /CGCPT/index.html;
    }"""

config = config.replace(old_cgcpt, new_cgcpt)

with sftp.open("/etc/nginx/sites-available/ai-website", "w") as f:
    f.write(config)

run("nginx -t")
run("systemctl reload nginx")

import time

time.sleep(2)

print()
print("=== 3. Test all resources ===")
run('curl -s -o /dev/null -w "Page: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/')
run(
    'curl -s -o /dev/null -w "JS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-CfCqO3cC.js'
)
run(
    'curl -s -o /dev/null -w "CSS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-BqpHRU_p.css'
)
run(
    'curl -s -o /dev/null -w "SVG: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/favicon.svg'
)
run(
    'curl -s -o /dev/null -w "Icons: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/icons.svg'
)
run(
    'curl -s -o /dev/null -w "SPA route: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/materials'
)

sftp.close()
ssh.close()
