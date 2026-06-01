"""
在校园网服务器(10.21.22.100)上部署CGCPT Web服务
因为云服务器密码已改，暂时用校园网服务器
"""
import paramiko
import os
import json
import time
import tarfile
import tempfile

CAMPUS_HOST = '10.21.22.100'
CAMPUS_USER = 'jarvisajks'
CAMPUS_PASS = 'Jarvis666'
LOCAL_BASE = r'd:\Projects\CGCPT-Server'
REMOTE = '/archive/jarvisajks/cgcpt-web'

print("连接校园网服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=30)
sftp = ssh.open_sftp()
print("  OK")

def run(cmd, timeout=600):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace').strip(), stderr.read().decode('utf-8', errors='replace').strip()

# Setup directories
print("\n[1/8] 创建目录结构...")
run(f'mkdir -p {REMOTE}/backend/models {REMOTE}/backend/uploads {REMOTE}/frontend {REMOTE}/data')
print("  OK")

# Upload frontend
print("\n[2/8] 上传前端...")
dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_fe.tar.gz')
with tarfile.open(tmp_tar, 'w:gz') as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
sftp.put(tmp_tar, f'{REMOTE}/frontend.tar.gz')
run(f'rm -rf {REMOTE}/frontend/* && cd {REMOTE}/frontend && tar xzf {REMOTE}/frontend.tar.gz && rm {REMOTE}/frontend.tar.gz')
os.remove(tmp_tar)
print("  OK")

# Upload backend code
print("\n[3/8] 上传后端代码...")
sftp.put(os.path.join(LOCAL_BASE, 'stacking_analyzer.py'), f'{REMOTE}/backend/stacking_analyzer.py')
sftp.put(os.path.join(LOCAL_BASE, 'api_server.py'), f'{REMOTE}/backend/api_server.py')
sftp.put(os.path.join(LOCAL_BASE, 'stack_main.py'), f'{REMOTE}/backend/stack_main.py')
sftp.put(os.path.join(LOCAL_BASE, 'verify_topology.py'), f'{REMOTE}/backend/verify_topology.py')
print("  OK")

# Upload model
print("\n[4/8] 上传模型...")
sftp.put(os.path.join(LOCAL_BASE, 'models', 'gb_97393.pkl'), f'{REMOTE}/backend/models/gb_97393.pkl')
print("  OK")

# Upload database
print("\n[5/8] 上传数据库...")
db_dir = os.path.join(LOCAL_BASE, 'database')
tmp_db = os.path.join(tempfile.gettempdir(), 'cgcpt_db.tar.gz')
with tarfile.open(tmp_db, 'w:gz') as tar:
    for item in os.listdir(db_dir):
        tar.add(os.path.join(db_dir, item), arcname=item)
sftp.put(tmp_db, f'{REMOTE}/db.tar.gz')
run(f'cd {REMOTE}/data && tar xzf {REMOTE}/db.tar.gz && rm {REMOTE}/db.tar.gz')
os.remove(tmp_db)
print("  OK")

# Upload test CIFs
print("\n[6/8] 上传测试CIF文件...")
run(f'mkdir -p {REMOTE}/backend/test_cifs')
test_dir = os.path.join(LOCAL_BASE, 'test_cifs')
for tf in os.listdir(test_dir):
    if tf.endswith('.cif'):
        sftp.put(os.path.join(test_dir, tf), f'{REMOTE}/backend/test_cifs/{tf}')
print("  OK")

# Setup Python venv
print("\n[7/8] 配置Python环境...")
out, _ = run(f'test -d {REMOTE}/venv && echo "exists" || echo "create"')
if 'create' in out:
    run(f'python3 -m venv {REMOTE}/venv')
    print("  虚拟环境已创建")

run(f'{REMOTE}/venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com flask flask-cors gunicorn pymatgen scikit-learn joblib numpy 2>&1 | tail -3', timeout=600)
print("  依赖安装完成")

# Create gunicorn config and start script
print("\n[8/8] 创建启动脚本...")
start_script = f'''#!/bin/bash
cd {REMOTE}/backend
export PYTHONPATH="{REMOTE}/backend:$PYTHONPATH"
export DATABASE_DIR="{REMOTE}/data"
export MODEL_DIR="{REMOTE}/backend/models"
export UPLOAD_DIR="{REMOTE}/backend/uploads"
export PORT=5001

# Kill existing
pkill -f "gunicorn.*cgcpt" 2>/dev/null
sleep 1

# Start
nohup {REMOTE}/venv/bin/gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300 --chdir {REMOTE}/backend api_server:app > {REMOTE}/gunicorn.log 2>&1 &
echo "Server started on port $PORT"
sleep 2
curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:$PORT/api/stats
'''
with sftp.open(f'{REMOTE}/start.sh', 'w') as f:
    f.write(start_script)
run(f'chmod +x {REMOTE}/start.sh')

# Create nginx config
nginx_conf = f'''server {{
    listen 8080;
    server_name _;

    location /CGCPT/ {{
        alias {REMOTE}/frontend/;
        try_files $uri $uri/ /CGCPT/index.html;
    }}

    location /CGCPT/api/ {{
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }}
}}'''

with sftp.open(f'{REMOTE}/nginx.conf', 'w') as f:
    f.write(nginx_conf)

# Start the server
print("\n启动后端服务...")
out, err = run(f'bash {REMOTE}/start.sh 2>&1', timeout=30)
print(f"  {out}")

# Test API
print("\n验证API...")
out, _ = run('curl -s http://127.0.0.1:5001/api/stats | head -c 200')
print(f"  Stats API: {out[:100]}...")

out, _ = run('curl -s http://127.0.0.1:5001/api/stacking/models')
try:
    data = json.loads(out)
    models = data.get('models', [])
    print(f"  模型: {len(models)} 个")
    for m in models:
        print(f"    {m['model_id']}: acc={m['test_accuracy']}, type={m['model_type']}")
except:
    print(f"  {out[:200]}")

# Test prediction
print("\n测试预测...")
test_files = [f for f in os.listdir(test_dir) if f.endswith('.cif')][:3]
for tf in test_files:
    sftp.put(os.path.join(test_dir, tf), f'/tmp/{tf}')
    out, _ = run(f'''cd {REMOTE}/backend && {REMOTE}/venv/bin/python -c "
import sys
sys.path.insert(0, '.')
import stacking_analyzer
stacking_analyzer.DATABASE_DIR = stacking_analyzer.Path('{REMOTE}/data')
stacking_analyzer.MODEL_DIR = stacking_analyzer.Path('{REMOTE}/backend/models')
cif = open('/tmp/{tf}', 'r').read()
parsed = stacking_analyzer.parse_cif_text(cif)
if parsed:
    result = stacking_analyzer.predict_stacking('gb_97393', parsed)
    print(f'{tf}: predicted={{result.get(\"predicted_topology\",\"?\")}}, confidence={{result.get(\"confidence\",0):.2%}}')
else:
    print('{tf}: parse failed')
" 2>&1''', timeout=60)
    print(f"  {out}")

sftp.close()
ssh.close()
print(f"\n✅ 部署完成!")
print(f"  后端API: http://{CAMPUS_HOST}:5001/api/")
print(f"  如果配置nginx: http://{CAMPUS_HOST}:8080/CGCPT/")
