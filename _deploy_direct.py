import paramiko
import os
import time
import tarfile
import tempfile

LOCAL_BASE = r"d:\Projects\CGCPT-Server"
CLOUD_HOST = "118.31.164.41"
CLOUD_USER = "root"
CLOUD_PASS = "ZS1029384756!"
CLOUD_REMOTE = "/opt/CGCPT"

print(f"Connecting to {CLOUD_HOST}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

for attempt in range(3):
    try:
        ssh.connect(
            CLOUD_HOST,
            port=22,
            username=CLOUD_USER,
            password=CLOUD_PASS,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
        print("  Connected!")
        break
    except Exception as e:
        print(f"  Attempt {attempt+1}/3 failed: {type(e).__name__}: {e}")
        if attempt == 2:
            print("Cannot connect!")
            exit(1)
        time.sleep(3)

sftp = ssh.open_sftp()


def run(cmd, timeout=120):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        for line in out.split("\n")[:100]:
            print(f"    {line}")
    if err:
        for line in err.split("\n")[:30]:
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

sftp.put(tmp_tar, f"{CLOUD_REMOTE}/fe_deploy.tar.gz")
print("  Uploaded tar.gz")

run(f"rm -rf {CLOUD_REMOTE}/root/CGCPT/*")
run(
    f"cd {CLOUD_REMOTE}/root/CGCPT && tar xzf {CLOUD_REMOTE}/fe_deploy.tar.gz && rm {CLOUD_REMOTE}/fe_deploy.tar.gz"
)
print("  Extracted on server")
os.remove(tmp_tar)

print("\n[2/3] Verifying files...")
run(f"ls -la {CLOUD_REMOTE}/root/CGCPT/")
run(f"ls -la {CLOUD_REMOTE}/root/CGCPT/assets/")

print("\n[3/3] Testing deployment...")
print("  === Main page headers ===")
run("curl -sI http://localhost/CGCPT/")

print("  === Asset headers ===")
run("curl -sI http://localhost/CGCPT/assets/vendor-three-B9nyAaMl.js")

print("  === API health ===")
run("curl -s http://localhost/CGCPT/api/health | head -c 200")

print("  === Brotli compression ===")
out, _ = run(
    'curl -sI -H "Accept-Encoding: br" http://localhost/CGCPT/assets/vendor-three-*.js 2>&1 | grep -i "content-encoding"'
)
brotli_result = out if out else "No content-encoding header found"
print(f"  Brotli result: {brotli_result}")

sftp.close()
ssh.close()
print(f"\nDeployment complete! http://{CLOUD_HOST}/CGCPT/")
