import paramiko
import os
import time
import tarfile
import tempfile

HOST = "118.31.164.41"
USER = "root"
PASS = "ZS1029384756!"
REMOTE_BASE = "/opt/CGCPT"
LOCAL_BASE = r"d:\Projects\CGCPT-Server"

print(f"Connecting to {HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

connected = False
for attempt in range(3):
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=15)
        print("  Connected!")
        connected = True
        break
    except Exception as e:
        print(f"  Attempt {attempt+1}/3 failed: {e}")
        if attempt == 2:
            print("Cannot connect to server!")
            exit(1)
        time.sleep(2)

sftp = ssh.open_sftp()


def run(cmd, timeout=120):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        for line in out.split("\n")[:50]:
            print(f"    {line}")
    if err:
        for line in err.split("\n")[:20]:
            print(f"    [stderr] {line}")
    return out, err


print("\n[1/3] Uploading frontend...")
dist_dir = os.path.join(LOCAL_BASE, "web", "dist")
tmp_tar = os.path.join(tempfile.gettempdir(), "cgcpt_fe_deploy.tar.gz")
with tarfile.open(tmp_tar, "w:gz") as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
tar_size = os.path.getsize(tmp_tar) / 1024
print(f"  Archive size: {tar_size:.1f} KB")

sftp.put(tmp_tar, f"{REMOTE_BASE}/fe_deploy.tar.gz")
print("  Uploaded tar.gz")

run(f"rm -rf {REMOTE_BASE}/root/CGCPT/*")
run(
    f"cd {REMOTE_BASE}/root/CGCPT && tar xzf {REMOTE_BASE}/fe_deploy.tar.gz && rm {REMOTE_BASE}/fe_deploy.tar.gz"
)
print("  Extracted on server")

os.remove(tmp_tar)

print("\n[2/3] Verifying file deployment...")
run(f"ls -la {REMOTE_BASE}/root/CGCPT/")
run(f"ls -la {REMOTE_BASE}/root/CGCPT/assets/")

print("\n[3/3] Testing deployment...")
out, _ = run("curl -sI http://localhost/CGCPT/")
print(f"  Main page headers:\n{out}")

js_file = "vendor-three-B9nyAaMl.js"
out, _ = run(f"curl -sI http://localhost/CGCPT/assets/{js_file}")
print(f"  Asset headers ({js_file}):\n{out}")

out, _ = run("curl -s http://localhost/CGCPT/api/health | head -c 200")
print(f"  API health: {out}")

print("\n[4/4] Testing Brotli compression...")
out, _ = run(
    f'curl -sI -H "Accept-Encoding: br" http://localhost/CGCPT/assets/vendor-three-*.js 2>&1 | grep -i "content-encoding"'
)
print(f'  Brotli: {out if out else "No content-encoding header found"}')

sftp.close()
ssh.close()
print(f"\nDeployment complete! http://{HOST}/CGCPT/")
