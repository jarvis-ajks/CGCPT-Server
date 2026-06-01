import paramiko
import os
import time
import tarfile
import tempfile

LOCAL_BASE = r'd:\Projects\CGCPT-Server'
CAMPUS_HOST = '10.21.22.100'
CAMPUS_USER = 'jarvisajks'
CAMPUS_PASS = 'Jarvis666'
CLOUD_HOST = '118.31.164.41'
CLOUD_USER = 'root'
CLOUD_PASS = 'ZS1029384756!'
CLOUD_REMOTE = '/opt/CGCPT'

print(f"Connecting to campus server...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=15)
print("  Connected!")
campus_sftp = campus.open_sftp()

def campus_run(cmd, timeout=300):
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

print("\nCreating frontend tar.gz...")
dist_dir = os.path.join(LOCAL_BASE, 'web', 'dist')
tmp_tar = os.path.join(tempfile.gettempdir(), 'cgcpt_fe_deploy.tar.gz')
with tarfile.open(tmp_tar, 'w:gz') as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
tar_size = os.path.getsize(tmp_tar) / 1024
print(f'  Archive size: {tar_size:.1f} KB')

print("\nUploading to campus server...")
campus_sftp.put(tmp_tar, '/archive/jarvisajks/cgcpt_fe_deploy.tar.gz')
print('  Uploaded!')
os.remove(tmp_tar)

print("\nCreating relay deploy script...")
relay_script = '''
import paramiko
import os
import time
import sys

CLOUD_HOST = "''' + CLOUD_HOST + '''"
CLOUD_USER = "''' + CLOUD_USER + '''"
CLOUD_PASS = "''' + CLOUD_PASS + '''"
CLOUD_REMOTE = "''' + CLOUD_REMOTE + '''"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

connected = False
for attempt in range(3):
    try:
        print(f"Attempt {attempt+1}/3...")
        ssh.connect(CLOUD_HOST, port=22, username=CLOUD_USER, password=CLOUD_PASS, timeout=60, banner_timeout=300, auth_timeout=120)
        print("  Connected!")
        connected = True
        break
    except Exception as e:
        print(f"  Failed: {type(e).__name__}: {str(e)[:200]}")
        if attempt < 2:
            time.sleep(30)

if not connected:
    print("FAILED: Cannot connect to cloud server!")
    sys.exit(1)

sftp = ssh.open_sftp()

def run(cmd, timeout=120):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        for line in out.split("\\n")[:100]:
            print(f"    {line}")
    if err:
        for line in err.split("\\n")[:30]:
            print(f"    [stderr] {line}")
    return out, err

print("\\n[1/4] Uploading frontend...")
sftp.put("/archive/jarvisajks/cgcpt_fe_deploy.tar.gz", f"{CLOUD_REMOTE}/fe_deploy.tar.gz")
print("  Uploaded!")

print("\\n[2/4] Extracting...")
run(f"rm -rf {CLOUD_REMOTE}/root/CGCPT/*")
run(f"cd {CLOUD_REMOTE}/root/CGCPT && tar xzf {CLOUD_REMOTE}/fe_deploy.tar.gz && rm {CLOUD_REMOTE}/fe_deploy.tar.gz")
print("  Extracted!")

print("\\n[3/4] Verifying files...")
run(f"ls -la {CLOUD_REMOTE}/root/CGCPT/")
run(f"ls -la {CLOUD_REMOTE}/root/CGCPT/assets/")

print("\\n[4/4] Testing...")
print("  === Main page ===")
run("curl -sI http://localhost/CGCPT/")

print("  === Asset ===")
run("curl -sI http://localhost/CGCPT/assets/vendor-three-B9nyAaMl.js")

print("  === API ===")
run("curl -s http://localhost/CGCPT/api/health | head -c 200")

print("  === Brotli ===")
out, _ = run('curl -sI -H "Accept-Encoding: br" http://localhost/CGCPT/assets/vendor-three-*.js 2>&1 | grep -i "content-encoding"')
brotli_result = out if out else "No content-encoding header found"
print(f"  Brotli: {brotli_result}")

sftp.close()
ssh.close()
print("\\nDEPLOY COMPLETE!")
'''

relay_path = '/archive/jarvisajks/relay_fe_deploy_final.py'
with campus_sftp.open(relay_path, 'w') as f:
    f.write(relay_script)
print('  Script uploaded!')

print("\nRunning relay script in background with nohup...")
out, err = campus_run(
    f'nohup /archive/jarvisajks/cgcpt-stacking/venv/bin/python /archive/jarvisajks/relay_fe_deploy_final.py '
    f'> /archive/jarvisajks/deploy_output.log 2>&1 & echo "PID=$!"',
    timeout=30
)
print(f'  Started: {out}')

print("\nWaiting for deployment to complete (checking log every 30s)...")
log_file = '/archive/jarvisajks/deploy_output.log'
max_wait = 600
start_time = time.time()

while time.time() - start_time < max_wait:
    time.sleep(30)
    elapsed = int(time.time() - start_time)
    
    try:
        with campus_sftp.open(log_file, 'r') as f:
            content = f.read().decode('utf-8', errors='replace')
        
        if 'DEPLOY COMPLETE' in content:
            print(f"\n  Deployment completed after {elapsed}s!")
            print("\n=== Full deployment log ===")
            print(content)
            break
        elif 'FAILED' in content:
            print(f"\n  Deployment FAILED after {elapsed}s!")
            print("\n=== Full deployment log ===")
            print(content)
            break
        else:
            lines = content.strip().split('\n')
            last_lines = lines[-3:] if len(lines) >= 3 else lines
            print(f"  [{elapsed}s] Last output: {chr(10).join(last_lines)}")
    except Exception as e:
        print(f"  [{elapsed}s] Error reading log: {e}")
else:
    print(f"\n  Timeout after {max_wait}s!")
    try:
        with campus_sftp.open(log_file, 'r') as f:
            content = f.read().decode('utf-8', errors='replace')
        print("\n=== Partial deployment log ===")
        print(content[-3000:])
    except:
        pass

campus_sftp.close()
campus.close()
print(f"\nDone! http://{CLOUD_HOST}/CGCPT/")
