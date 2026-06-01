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
    print(f'  $ {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        for line in out.strip().split('\n')[:20]:
            print(f'    {line}')
    if err.strip() and 'WARNING' not in err:
        for line in err.strip().split('\n')[:5]:
            print(f'    [stderr] {line}')
    return out, err

print('=== Step 1: Pack and upload new frontend ===')
dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
if os.path.isdir(dist_dir):
    tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_frontend_new.tar.gz')
    print(f'  Creating tar.gz...')
    with tarfile.open(tmp_tar, 'w:gz') as tar:
        for item in os.listdir(dist_dir):
            tar.add(os.path.join(dist_dir, item), arcname=item)
    tar_size = os.path.getsize(tmp_tar) / (1024 * 1024)
    print(f'  Archive size: {tar_size:.1f} MB')
    print(f'  Uploading...')
    sftp.put(tmp_tar, f'{REMOTE_BASE}/frontend_new.tar.gz')
    print(f'  Clearing old frontend and extracting...')
    run(f'rm -rf {REMOTE_BASE}/root/CGCPT/*')
    run(f'cd {REMOTE_BASE}/root/CGCPT && tar xzf {REMOTE_BASE}/frontend_new.tar.gz && rm {REMOTE_BASE}/frontend_new.tar.gz')
    os.remove(tmp_tar)
    print('  Frontend updated!')
else:
    print('  ERROR: dist directory not found!')

print()
print('=== Step 2: Verify ===')
time.sleep(2)
run('curl -s -o /dev/null -w "Page: %{http_code}" http://127.0.0.1/CGCPT/')
run('curl -s -o /dev/null -w "JS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-_UHI_a-C.js')
run('curl -s -o /dev/null -w "CSS: %{http_code} %{size_download}" http://127.0.0.1/CGCPT/assets/index-BqpHRU_p.css')
run('curl -s -o /dev/null -w "API: %{http_code}" http://127.0.0.1/CGCPT/api/stats')

sftp.close()
ssh.close()
print('\n=== DEPLOYMENT COMPLETE ===')
print(f'Access: http://{HOST}/CGCPT/')
