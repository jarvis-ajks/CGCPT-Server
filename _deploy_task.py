import paramiko
import os
import tarfile
import tempfile
import time

HOST = '118.31.164.41'
USER = 'root'
PASS = 'ZS1029384756!'
REMOTE = '/opt/CGCPT'
LOCAL_BASE = r'd:\Projects\CGCPT-Server'

print('=' * 60)
print('  CGCPT 部署到远程服务器')
print('=' * 60)

# Connect
print(f'\n[连接] {USER}@{HOST}...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for attempt in range(3):
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=15)
        print('  连接成功!')
        break
    except Exception as e:
        print(f'  尝试 {attempt+1}/3 失败: {e}')
        if attempt == 2:
            print('无法连接服务器!')
            exit(1)
        time.sleep(2)

sftp = ssh.open_sftp()

def run(cmd, timeout=600):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out.strip(), err.strip()

# Step 1: Upload files
print('\n[1/5] 上传文件...')

for fname in ['self_improver.py', 'api_server.py', 'stacking_analyzer.py']:
    local_path = os.path.join(LOCAL_BASE, fname)
    remote_path = f'{REMOTE}/{fname}'
    print(f'  上传 {fname}...', end=' ', flush=True)
    sftp.put(local_path, remote_path)
    print('OK')

# Upload frontend dist as tar
print('  打包前端构建产物...', end=' ', flush=True)
dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_frontend.tar.gz')
with tarfile.open(tmp_tar, 'w:gz') as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
tar_size = os.path.getsize(tmp_tar) / (1024 * 1024)
print(f'{tar_size:.1f} MB')

print('  上传前端包...', end=' ', flush=True)
sftp.put(tmp_tar, f'{REMOTE}/frontend.tar.gz')
print('OK')
os.remove(tmp_tar)

print('  解压前端文件...', end=' ', flush=True)
out, err = run(f'mkdir -p {REMOTE}/web/dist && cd {REMOTE}/web/dist && tar xzf {REMOTE}/frontend.tar.gz && rm {REMOTE}/frontend.tar.gz')
print('OK')

print('  所有文件上传完成!')

# Step 2: Create training history directory
print('\n[2/5] 创建训练历史目录...')
out, err = run(f'mkdir -p {REMOTE}/training_history')
out2, err2 = run(f'ls -la {REMOTE}/training_history')
print(f'  {out2}')

# Step 3: Run self-improvement test
print('\n[3/5] 运行自我迭代优化测试 (max_iterations=2, max_sequences=150, cv_folds=3)...')

# Write the test script to a temp file and upload it
test_script = r'''
import sys
sys.path.insert(0, '.')
from self_improver import self_improve_iteration
result = self_improve_iteration(max_iterations=2, max_sequences=150, cv_folds=3, use_ensemble=False)
if result.get('success'):
    print('SUCCESS! Iterations:', result['n_iterations'])
    print('Best CV:', result['best_iteration'].get('cv_mean'))
    print('Best Strategy:', result['best_iteration'].get('strategy'))
    print('Improvement:', result.get('total_improvement'), '%')
else:
    print('FAILED:', result.get('error'))
'''

local_test_script = os.path.join(tempfile.gettempdir(), '_test_improve.py')
with open(local_test_script, 'w', encoding='utf-8') as f:
    f.write(test_script)

sftp.put(local_test_script, f'{REMOTE}/_test_improve.py')
os.remove(local_test_script)

out, err = run(f'cd {REMOTE} && /opt/CGCPT/venv/bin/python {REMOTE}/_test_improve.py', timeout=600)
print('  --- 输出 ---')
print(out)
if err:
    print('  --- 错误 ---')
    print(err[:2000])

# Cleanup test script
run(f'rm -f {REMOTE}/_test_improve.py')

# Step 4: Restart service
print('\n[4/5] 重启服务...')
out, err = run('systemctl restart cgcpt', timeout=30)
print(f'  systemctl restart: out=[{out}], err=[{err}]')
time.sleep(3)
out, err = run('systemctl is-active cgcpt')
print(f'  服务状态: {out}')

# Step 5: Verify API
print('\n[5/5] 验证新API...')
out, err = run('curl -s http://localhost:5001/CGCPT/api/stacking/improvement_history | python3 -m json.tool')
print('  --- API响应 ---')
print(out[:3000])
if err:
    print('  --- 错误 ---')
    print(err[:1000])

sftp.close()
ssh.close()
print('\n' + '=' * 60)
print('  部署完成!')
print('=' * 60)
