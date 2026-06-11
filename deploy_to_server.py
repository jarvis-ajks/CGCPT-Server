"""
CGCPT 堆垛识别 - 一键部署到远程服务器
用法: python deploy_to_server.py
"""

import paramiko
import os
import sys
import time

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"
REMOTE_DIR = "/home/jarvisajks/cgcpt-stacking"

LOCAL_BASE = os.path.dirname(os.path.abspath(__file__))

FILES_TO_UPLOAD = [
    "stacking_analyzer.py",
    "train_oneclick.py",
    "predict_one.py",
    "setup_server.sh",
]

print("=" * 60)
print("  CGCPT 堆垛识别 - 远程部署")
print("=" * 60)
print(f"  服务器: {USER}@{HOST}")
print(f"  远程目录: {REMOTE_DIR}")
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("[1/4] 连接服务器...")
try:
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    print("  ✅ 连接成功!")
except Exception as e:
    print(f"  ❌ 连接失败: {e}")
    print(f"  请检查: 1)服务器IP 2)账号密码 3)网络连通性")
    sys.exit(1)

sftp = ssh.open_sftp()


def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("\n[2/4] 创建远程目录...")
run(f"mkdir -p {REMOTE_DIR}/data {REMOTE_DIR}/models")
print(f"  {REMOTE_DIR}/")
print(f"  {REMOTE_DIR}/data/     ← 放CIF数据")
print(f"  {REMOTE_DIR}/models/   ← 训练模型")

print("\n[3/4] 上传文件...")
for fname in FILES_TO_UPLOAD:
    local_path = os.path.join(LOCAL_BASE, fname)
    remote_path = f"{REMOTE_DIR}/{fname}"
    if os.path.exists(local_path):
        sftp.put(local_path, remote_path)
        print(f"  ✅ {fname}")
    else:
        print(f"  ⚠️  {fname} 不存在，跳过")

print("\n[4/4] 配置环境...")
out, err = run("python3 --version 2>&1")
print(f"  Python: {out}")

out, err = run(f'test -d {REMOTE_DIR}/venv && echo "exists" || echo "not_found"')
if out == "not_found":
    print("  创建虚拟环境...")
    run(f"python3 -m venv {REMOTE_DIR}/venv")
    print("  ✅ 虚拟环境已创建")
else:
    print("  虚拟环境已存在")

print("  安装依赖(可能需要几分钟)...")
out, err = run(
    f"{REMOTE_DIR}/venv/bin/pip install --upgrade pip pymatgen scikit-learn joblib numpy 2>&1 | tail -3",
    timeout=600,
)
print(f"  {out}")

run(f"chmod +x {REMOTE_DIR}/setup_server.sh")

print("\n验证安装...")
out, err = run(
    f"cd {REMOTE_DIR} && venv/bin/python -c \"import stacking_analyzer; print(f'pymatgen={stacking_analyzer.HAS_PYMATGEN}, sklearn={stacking_analyzer.HAS_SKLEARN}')\" 2>&1"
)
print(f"  {out}")

print("\n" + "=" * 60)
print("  ✅ 部署完成!")
print("=" * 60)
print(
    f"""
  下一步:
  1. 将CIF数据上传到服务器:
     scp -r /path/to/XO_cifs/ {USER}@{HOST}:{REMOTE_DIR}/data/XO/
     scp -r /path/to/XO2_cifs/ {USER}@{HOST}:{REMOTE_DIR}/data/XO2/

  2. SSH登录服务器:
     ssh {USER}@{HOST}

  3. 运行训练:
     cd {REMOTE_DIR}
     ./venv/bin/python train_oneclick.py --data ./data --quick     # 快速测试
     ./venv/bin/python train_oneclick.py --data ./data              # 完整训练

  4. 预测:
     ./venv/bin/python predict_one.py --list-models
     ./venv/bin/python predict_one.py --model MODEL_ID --cif test.cif
"""
)

sftp.close()
ssh.close()
