import paramiko
import os
import sys
import time

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"
LOCAL_BASE = r"d:\Projects\CGCPT-Server"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print(f"连接 {USER}@{HOST}...")
ssh.connect(HOST, username=USER, password=PASS, timeout=30)
print("连接成功!")


def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


out, _ = run("echo $HOME && pwd && ls -la")
print(f"Home: {out}")

home_dir = run("echo $HOME")[0].strip()
remote_dir = f"{home_dir}/cgcpt-stacking"

print(f"\n创建目录 {remote_dir}...")
out, err = run(f"mkdir -p {remote_dir}/data {remote_dir}/models && ls -la {remote_dir}")
print(out if out else f"err: {err}")

print("\n上传文件(通过SFTP cat方式)...")
files = ["stacking_analyzer.py", "train_oneclick.py", "predict_one.py"]
for fname in files:
    local = os.path.join(LOCAL_BASE, fname)
    if not os.path.exists(local):
        print(f"  {fname} 不存在!")
        continue
    remote = f"{remote_dir}/{fname}"
    try:
        sftp = ssh.open_sftp()
        sftp.put(local, remote)
        sftp.close()
        print(f"  {fname} OK")
    except Exception as e:
        print(f"  SFTP put failed ({e}), trying scp...")
        out, err = run(f"cat > {remote} << 'HEREDOC_END'\nHEREDOC_END")
        with open(local, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        import base64

        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        out, err = run(f'echo "{b64}" | base64 -d > {remote}', timeout=60)
        if err:
            print(f"  base64方式也失败: {err[:100]}")
        else:
            print(f"  {fname} OK (base64)")

print("\n验证文件...")
out, _ = run(f"ls -la {remote_dir}/")
print(out)

print("\n配置Python环境...")
out, _ = run(f'test -d {remote_dir}/venv && echo "exists" || echo "create"')
if out.strip() == "create":
    print("  创建虚拟环境...")
    out, err = run(f"python3 -m venv {remote_dir}/venv 2>&1")
    print(f"  {'OK' if not err else err[:200]}")
else:
    print("  虚拟环境已存在")

print("  安装依赖...")
out, err = run(f"{remote_dir}/venv/bin/pip install --upgrade pip 2>&1 | tail -2", timeout=120)
print(f"  pip: {out}")
out, err = run(
    f"{remote_dir}/venv/bin/pip install pymatgen scikit-learn joblib numpy 2>&1 | tail -3",
    timeout=600,
)
print(f"  依赖: {out}")

print("\n验证...")
out, err = run(
    f"cd {remote_dir} && venv/bin/python -c \"import stacking_analyzer; print('pymatgen=', stacking_analyzer.HAS_PYMATGEN, 'sklearn=', stacking_analyzer.HAS_SKLEARN)\" 2>&1"
)
print(f"  {out}")
if err:
    print(f"  err: {err[:300]}")

ssh.close()
print("\n部署完成!")
