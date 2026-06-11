import paramiko
import os
import sys
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


print("重新上传修复后的脚本...")
for fname in ["train_oneclick.py", "stacking_analyzer.py", "predict_one.py"]:
    local = os.path.join(LOCAL_BASE, fname)
    sftp.put(local, f"{REMOTE_DIR}/{fname}")
    print(f"  {fname} OK")

sftp.close()

VENV = f"{REMOTE_DIR}/venv"

print("\n运行训练(快速模式)...")
t0 = time.time()
cmd = (
    f"cd {REMOTE_DIR} && {VENV}/bin/python train_oneclick.py --data {REMOTE_DIR}/data --quick 2>&1"
)
out, err = run(cmd, timeout=600)
elapsed = time.time() - t0

print(out[-3000:] if len(out) > 3000 else out)
if err and "UserWarning" not in err:
    print(f"\nstderr: {err[-300:]}")

print(f"\n总耗时: {elapsed:.1f}s")
ssh.close()
