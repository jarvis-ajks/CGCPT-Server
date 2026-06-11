"""
通过校园网服务器中转部署到云服务器
本机 → 校园网服务器(10.21.22.100) → 云服务器(118.31.164.41)
"""

import paramiko
import os
import json
import time
import tarfile
import tempfile
import base64

LOCAL_BASE = r"d:\Projects\CGCPT-Server"
CAMPUS_HOST = "10.21.22.100"
CAMPUS_USER = "jarvisajks"
CAMPUS_PASS = "Jarvis666"
CLOUD_HOST = "118.31.164.41"
CLOUD_USER = "root"
CLOUD_PASS = "Aa123456"
CLOUD_REMOTE = "/opt/CGCPT"

print("连接校园网服务器...")
campus = paramiko.SSHClient()
campus.set_missing_host_key_policy(paramiko.AutoAddPolicy())
campus.connect(CAMPUS_HOST, username=CAMPUS_USER, password=CAMPUS_PASS, timeout=30)
campus_sftp = campus.open_sftp()
print("  OK")


def campus_run(cmd, timeout=600):
    stdin, stdout, stderr = campus.exec_command(cmd, timeout=timeout)
    return (
        stdout.read().decode("utf-8", errors="replace").strip(),
        stderr.read().decode("utf-8", errors="replace").strip(),
    )


# Upload a helper script to campus server that will relay to cloud
print("\n[1/7] 上传中转脚本到校园网服务器...")
relay_script = (
    '''
import paramiko, sys, os, json, time, base64

CLOUD_HOST = "'''
    + CLOUD_HOST
    + '''"
CLOUD_USER = "'''
    + CLOUD_USER
    + '''"
CLOUD_PASS = "'''
    + CLOUD_PASS
    + '''"
CLOUD_REMOTE = "'''
    + CLOUD_REMOTE
    + """"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {CLOUD_HOST}...")
ssh.connect(CLOUD_HOST, username=CLOUD_USER, password=CLOUD_PASS, timeout=30)
sftp = ssh.open_sftp()
print("Connected!")

def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip(), stderr.read().decode("utf-8", errors="replace").strip()

# Upload frontend
print("Uploading frontend...")
sftp.put("/archive/jarvisajks/cgcpt-relay/frontend.tar.gz", f"{CLOUD_REMOTE}/frontend.tar.gz")
out, err = run(f"rm -rf {CLOUD_REMOTE}/root/CGCPT/* && cd {CLOUD_REMOTE}/root/CGCPT && tar xzf {CLOUD_REMOTE}/frontend.tar.gz && rm {CLOUD_REMOTE}/frontend.tar.gz")
print(f"  Frontend: {out if out else 'OK'}")

# Upload stacking_analyzer
print("Uploading stacking_analyzer.py...")
sftp.put("/archive/jarvisajks/cgcpt-relay/stacking_analyzer.py", f"{CLOUD_REMOTE}/backend/stacking_analyzer.py")
print("  OK")

# Upload api_server
print("Uploading api_server.py...")
sftp.put("/archive/jarvisajks/cgcpt-relay/api_server.py", f"{CLOUD_REMOTE}/backend/api_server.py")
print("  OK")

# Upload model
print("Uploading model...")
sftp.put("/archive/jarvisajks/cgcpt-relay/gb_97393.pkl", f"{CLOUD_REMOTE}/backend/models/gb_97393.pkl")
print("  OK")

# Upload test CIFs
print("Uploading test CIFs...")
out, _ = run(f"mkdir -p {CLOUD_REMOTE}/backend/test_cifs")
for f in os.listdir("/archive/jarvisajks/cgcpt-relay/test_cifs"):
    if f.endswith(".cif"):
        sftp.put(f"/archive/jarvisajks/cgcpt-relay/test_cifs/{f}", f"{CLOUD_REMOTE}/backend/test_cifs/{f}")
        print(f"  {f}")

# Restart
print("Restarting service...")
run("systemctl restart cgcpt", timeout=30)
time.sleep(3)

# Verify
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/CGCPT/')
print(f"Frontend: HTTP {out}")
out, _ = run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/CGCPT/api/stacking/models')
print(f"API: HTTP {out}")

out, _ = run('curl -s http://127.0.0.1/CGCPT/api/stacking/models')
try:
    data = json.loads(out)
    models = data.get("models", [])
    print(f"Models: {len(models)}")
    for m in models:
        print(f"  {m['model_id']}: acc={m['test_accuracy']}, type={m['model_type']}")
except:
    print(f"Models response: {out[:200]}")

# Test prediction
print("\\nTesting prediction API...")
test_cifs = [f for f in os.listdir("/archive/jarvisajks/cgcpt-relay/test_cifs") if f.endswith(".cif")]
for tf in test_cifs[:3]:
    with open(f"/archive/jarvisajks/cgcpt-relay/test_cifs/{tf}", "r") as f:
        cif_text = f.read()
    b64 = base64.b64encode(cif_text.encode()).decode()
    import urllib.request
    req = urllib.request.Request(
        f"http://127.0.0.1/CGCPT/api/stacking/predict",
        data=json.dumps({"model_id": "gb_97393", "cif_text": cif_text}).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        pred = result.get("predicted_topology", "?")
        conf = result.get("confidence", 0)
        print(f"  {tf}: predicted={pred}, confidence={conf:.2%}")
    except Exception as e:
        print(f"  {tf}: error - {e}")

sftp.close()
ssh.close()
print("\\nDone!")
"""
)

campus_run(f"mkdir -p /archive/jarvisajks/cgcpt-relay/test_cifs")
relay_path = "/archive/jarvisajks/cgcpt-relay/relay_deploy.py"
with campus_sftp.open(relay_path, "w") as f:
    f.write(relay_script)
print("  OK")

# Upload files to campus server for relay
print("\n[2/7] 上传前端到校园网服务器...")
dist_dir = os.path.join(LOCAL_BASE, "web", "dist")
tmp_tar = os.path.join(tempfile.gettempdir(), "frontend.tar.gz")
with tarfile.open(tmp_tar, "w:gz") as tar:
    for item in os.listdir(dist_dir):
        tar.add(os.path.join(dist_dir, item), arcname=item)
campus_sftp.put(tmp_tar, "/archive/jarvisajks/cgcpt-relay/frontend.tar.gz")
os.remove(tmp_tar)
print("  OK")

print("\n[3/7] 上传stacking_analyzer.py...")
campus_sftp.put(
    os.path.join(LOCAL_BASE, "stacking_analyzer.py"),
    "/archive/jarvisajks/cgcpt-relay/stacking_analyzer.py",
)
print("  OK")

print("\n[4/7] 上传api_server.py...")
campus_sftp.put(
    os.path.join(LOCAL_BASE, "api_server.py"), "/archive/jarvisajks/cgcpt-relay/api_server.py"
)
print("  OK")

print("\n[5/7] 上传模型...")
campus_sftp.put(
    os.path.join(LOCAL_BASE, "models", "gb_97393.pkl"),
    "/archive/jarvisajks/cgcpt-relay/gb_97393.pkl",
)
print("  OK")

print("\n[6/7] 上传测试CIF文件...")
test_dir = os.path.join(LOCAL_BASE, "test_cifs")
for tf in os.listdir(test_dir):
    if tf.endswith(".cif"):
        campus_sftp.put(
            os.path.join(test_dir, tf), f"/archive/jarvisajks/cgcpt-relay/test_cifs/{tf}"
        )
        print(f"  {tf}")

# Ensure paramiko is installed on campus server
print("\n[7/7] 在校园网服务器上执行中转部署...")
out, _ = campus_run(
    '/archive/jarvisajks/cgcpt-stacking/venv/bin/python -c "import paramiko; print(paramiko.__version__)" 2>&1'
)
if "module" in out.lower() or not out:
    print("  安装paramiko到校园网服务器...")
    campus_run(
        "/archive/jarvisajks/cgcpt-stacking/venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com paramiko 2>&1 | tail -3",
        timeout=120,
    )

print("  执行中转部署脚本...")
out, err = campus_run(
    "/archive/jarvisajks/cgcpt-stacking/venv/bin/python /archive/jarvisajks/cgcpt-relay/relay_deploy.py 2>&1",
    timeout=600,
)
print(out[-3000:] if len(out) > 3000 else out)
if err and "UserWarning" not in err:
    print(f"stderr: {err[-500:]}")

campus_sftp.close()
campus.close()
print(f"\n✅ 部署完成! http://{CLOUD_HOST}/CGCPT/")
