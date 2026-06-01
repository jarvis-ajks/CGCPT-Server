import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('118.31.164.41', username='root', password='Aa123456', timeout=30)

def run(cmd):
    print(f'$ {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out.strip()[:3000])
    if err.strip():
        print('[stderr]', err.strip()[:1000])

sftp = ssh.open_sftp()

print('=== 1. Check current frontend directory structure ===')
run('ls -la /opt/CGCPT/frontend/')
run('ls -la /opt/CGCPT/frontend/assets/')

print()
print('=== 2. Check current nginx config ===')
run('grep -A 30 "CGCPT" /etc/nginx/sites-available/ai-website')

print()
print('=== 3. Fix nginx config - use root instead of alias ===')
with sftp.open('/etc/nginx/sites-available/ai-website', 'r') as f:
    config = f.read().decode('utf-8')

old_cgcpt = """    location /CGCPT/api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;
    }

    location /CGCPT/ {
        alias /opt/CGCPT/frontend/;
        try_files $uri $uri/ /CGCPT/index.html;
    }"""

new_cgcpt = """    location /CGCPT/api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;
    }

    location /CGCPT/assets/ {
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

config = config.replace(old_cgcpt, new_cgcpt)

with sftp.open('/etc/nginx/sites-available/ai-website', 'w') as f:
    f.write(config)

print('  Config updated!')

print()
print('=== 4. Test nginx config ===')
run('nginx -t')

print()
print('=== 5. Reload nginx ===')
run('systemctl reload nginx')

import time
time.sleep(2)

print()
print('=== 6. Test static assets ===')
run('curl -s -o /dev/null -w "JS: %{http_code} %{size_download} bytes" http://118.31.164.41/CGCPT/assets/index-CfCqO3cC.js')
run('curl -s -o /dev/null -w "CSS: %{http_code} %{size_download} bytes" http://118.31.164.41/CGCPT/assets/index-BqpHRU_p.css')
run('curl -s -o /dev/null -w "SVG: %{http_code} %{size_download} bytes" http://118.31.164.41/CGCPT/favicon.svg')
run('curl -s -o /dev/null -w "Page: %{http_code} %{size_download} bytes" http://118.31.164.41/CGCPT/')

print()
print('=== 7. Test API ===')
run('curl -s http://118.31.164.41/CGCPT/api/stats | head -c 200')
run('curl -s http://118.31.164.41/CGCPT/api/prototypes | head -c 200')

sftp.close()
ssh.close()
