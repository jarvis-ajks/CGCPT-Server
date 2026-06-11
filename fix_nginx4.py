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
        print(out.strip()[:5000])
    if err.strip():
        print("[stderr]", err.strip()[:2000])


sftp = ssh.open_sftp()

print("=== 1. Read full config ===")
with sftp.open("/etc/nginx/sites-available/ai-website", "r") as f:
    config = f.read().decode("utf-8")

print("=== 2. Check the global static file location ===")
lines = config.split("\n")
for i, line in enumerate(lines):
    if "js|css|png" in line or (i > 240 and i < 260):
        print(f"  Line {i+1}: {line}")

print()
print("=== 3. Fix: Add ^~ prefix to CGCPT locations for priority ===")
old = """    location /CGCPT {
        root /opt/CGCPT/root;
        index index.html;
        try_files $uri $uri/ /CGCPT/index.html;
    }"""

new = """    location ^~ /CGCPT/ {
        root /opt/CGCPT/root;
        index index.html;
        try_files $uri $uri/ /CGCPT/index.html;
    }

    location ^~ /CGCPT/assets/ {
        root /opt/CGCPT/root;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }"""

config = config.replace(old, new)

with sftp.open("/etc/nginx/sites-available/ai-website", "w") as f:
    f.write(config)

run("nginx -t")
run("systemctl reload nginx")

import time

time.sleep(2)

print()
print("=== 4. Test all resources ===")
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
    'curl -s -o /dev/null -w "SPA route: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/materials'
)
run('curl -s -o /dev/null -w "API: %{http_code}" http://127.0.0.1/CGCPT/api/stats')

sftp.close()
ssh.close()
