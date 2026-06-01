import paramiko
import os
import tarfile
import tempfile
import time

HOST = '118.31.164.41'
USER = 'root'
PASS = 'Aa123456'
REMOTE_BASE = '/opt/CGCPT'
LOCAL_BASE = r'd:\Projects\CGCPT-Server'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)
sftp = ssh.open_sftp()

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out.strip(), err.strip()

dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_frontend_v3.tar.gz')
with tarfile.open(tmp_tar, 'w:gz') as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
tar_size = os.path.getsize(tmp_tar) / (1024 * 1024)
print(f'Archive: {tar_size:.1f} MB')

sftp.put(tmp_tar, f'{REMOTE_BASE}/frontend_v3.tar.gz')
run(f'rm -rf {REMOTE_BASE}/root/CGCPT/*')
run(f'cd {REMOTE_BASE}/root/CGCPT && tar xzf {REMOTE_BASE}/frontend_v3.tar.gz && rm {REMOTE_BASE}/frontend_v3.tar.gz')
os.remove(tmp_tar)
print('Frontend deployed!')

sftp.put(os.path.join(LOCAL_BASE, 'stacking_analyzer.py'), f'{REMOTE_BASE}/backend/stacking_analyzer.py')
print('stacking_analyzer.py uploaded!')

sftp.put(os.path.join(LOCAL_BASE, 'api_server.py'), f'{REMOTE_BASE}/backend/api_server.py')
print('api_server.py uploaded!')

out, err = run('/opt/CGCPT/venv/bin/pip install scikit-learn joblib 2>&1 | tail -5', timeout=300)
print(f'scikit-learn install: {out}')

run(f'mkdir -p {REMOTE_BASE}/backend/uploads {REMOTE_BASE}/backend/models')
print('Created uploads/ and models/ directories!')

nginx_conf = """server {
    listen 80;
    server_name _;

    location /CGCPT/ {
        alias /opt/CGCPT/root/CGCPT/;
        try_files $uri $uri/ /CGCPT/index.html;
    }

    location /CGCPT/api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }
}"""

run(f"cat > /etc/nginx/conf.d/cgcpt.conf << 'NGINX_EOF'\n{nginx_conf}\nNGINX_EOF")
print('Nginx config updated (SSE support: proxy_buffering off)!')

run('nginx -t && nginx -s reload', timeout=30)
print('Nginx reloaded!')

run('systemctl restart cgcpt', timeout=30)
print('Service restarted!')

time.sleep(3)

tests = [
    ('Page', f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1/CGCPT/'),
    ('API', f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1/CGCPT/api/stats'),
    ('API-Stats', f'curl -s http://127.0.0.1/CGCPT/api/stats | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\\"Materials: {{d[\\\\"total_materials\\\\"]}}, SpaceGroups: {{d.get(\\\\"unique_space_groups\\\\",0)}}\\")"'),
]

for name, cmd in tests:
    out, err = run(cmd)
    print(f'  {name}: {out}')
    if err and name != 'API-Stats':
        print(f'    err: {err[:200]}')

sftp.close()
ssh.close()
print(f'\nDone! http://{HOST}/CGCPT/')
