import paramiko
import os
import json
import time
import tarfile
import tempfile

HOST = '118.31.164.41'
USER = 'root'
PASS = 'Aa123456'
REMOTE = '/opt/CGCPT'
LOCAL_BASE = r'd:\Projects\CGCPT-Server'

print(f"连接云服务器 {HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(3):
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=15)
        print("  连接成功!")
        break
    except Exception as e:
        print(f"  尝试 {attempt+1}/3 失败: {e}")
        if attempt == 2:
            print("\n无法连接云服务器，请检查密码是否正确")
            exit(1)
        time.sleep(2)

sftp = ssh.open_sftp()

def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace').strip(), stderr.read().decode('utf-8', errors='replace').strip()

print("\n[1/5] 上传前端...")
dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_fe.tar.gz')
with tarfile.open(tmp_tar, 'w:gz') as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
sftp.put(tmp_tar, f'{REMOTE}/fe.tar.gz')
run(f'rm -rf {REMOTE}/root/CGCPT/* && cd {REMOTE}/root/CGCPT && tar xzf {REMOTE}/fe.tar.gz && rm {REMOTE}/fe.tar.gz')
os.remove(tmp_tar)
print("  OK")

print("\n[2/5] 上传后端代码...")
sftp.put(os.path.join(LOCAL_BASE, 'stacking_analyzer.py'), f'{REMOTE}/backend/stacking_analyzer.py')
sftp.put(os.path.join(LOCAL_BASE, 'api_server.py'), f'{REMOTE}/backend/api_server.py')
print("  OK")

print("\n[3/5] 上传模型...")
sftp.put(os.path.join(LOCAL_BASE, 'models', 'gb_97393.pkl'), f'{REMOTE}/backend/models/gb_97393.pkl')
print("  OK")

print("\n[4/5] 重启服务...")
run('systemctl restart cgcpt', timeout=30)
time.sleep(3)

print("\n[5/5] 验证...")
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/CGCPT/')
print(f"  前端: HTTP {out}")
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/CGCPT/api/stacking/models')
print(f"  API: HTTP {out}")

out, _ = run('curl -s http://127.0.0.1/CGCPT/api/stacking/models')
try:
    data = json.loads(out)
    models = data.get('models', [])
    print(f"  模型: {len(models)} 个")
    for m in models:
        print(f"    {m['model_id']}: acc={m['test_accuracy']}, type={m['model_type']}")
except:
    print(f"  {out[:300]}")

# Test prediction
print("\n测试预测API...")
test_dir = os.path.join(LOCAL_BASE, 'test_cifs')
test_files = [f for f in os.listdir(test_dir) if f.endswith('.cif')][:3]
for tf in test_files:
    cif_text = open(os.path.join(test_dir, tf), 'r', encoding='utf-8', errors='ignore').read()
    import base64
    b64 = base64.b64encode(cif_text.encode('utf-8')).decode()
    cmd = f'''curl -s -X POST http://127.0.0.1/CGCPT/api/stacking/predict -H "Content-Type: application/json" -d '{{"model_id":"gb_97393","cif_text":"{b64[:2000]}{"..." if len(b64)>2000 else ""}"}}' '''
    # Too long for curl, use python instead
    sftp.put(os.path.join(test_dir, tf), f'/tmp/{tf}')
    out, _ = run(f'''cd /opt/CGCPT/backend && /opt/CGCPT/venv/bin/python -c "
import stacking_analyzer
cif = open('/tmp/{tf}', 'r').read()
parsed = stacking_analyzer.parse_cif_text(cif)
if parsed:
    result = stacking_analyzer.predict_stacking('gb_97393', parsed)
    print(f'{tf}: predicted={{result.get(\\\"predicted_topology\\\",\\\"?\\\")}}, confidence={{result.get(\\\"confidence\\\",0):.2%}}')
else:
    print('{tf}: parse failed')
" 2>&1''', timeout=60)
    print(f"  {out}")

sftp.close()
ssh.close()
print(f"\n✅ 部署完成! http://{HOST}/CGCPT/")
