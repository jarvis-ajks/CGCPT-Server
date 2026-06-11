import paramiko
import os
import time

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"
REMOTE_DIR = "/archive/jarvisajks/cgcpt-stacking"
LOCAL_BASE = r"d:\Projects\CGCPT-Server"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)
sftp = ssh.open_sftp()


def run(cmd, timeout=600):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("上传更新后的脚本...")
for fname in ["stacking_analyzer.py", "train_oneclick.py", "predict_one.py"]:
    local = os.path.join(LOCAL_BASE, fname)
    sftp.put(local, f"{REMOTE_DIR}/{fname}")
    print(f"  {fname} OK")
sftp.close()

VENV = f"{REMOTE_DIR}/venv"

print("\n运行完整训练(5轮迭代, 5折CV)...")
t0 = time.time()
cmd = f"cd {REMOTE_DIR} && {VENV}/bin/python train_oneclick.py --data {REMOTE_DIR}/data --iterations 5 --cv-folds 5 2>&1"
out, err = run(cmd, timeout=1800)
elapsed = time.time() - t0

print(out[-4000:] if len(out) > 4000 else out)

print(f"\n总耗时: {elapsed:.1f}s")
ssh.close()
