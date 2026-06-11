import paramiko
import os
import tarfile
import tempfile
import time
from pathlib import Path

HOST = "10.21.22.100"
USER = "jarvisajks"
PASS = "Jarvis666"
REMOTE_DIR = "/archive/jarvisajks/cgcpt-stacking"
LOCAL_DB = r"d:\Projects\CGCPT-Server\database"

print("打包CIF数据...")
tmp_tar = os.path.join(tempfile.gettempdir(), "cgcpt_cif_data.tar.gz")

with tarfile.open(tmp_tar, "w:gz") as tar:
    db_path = Path(LOCAL_DB)
    for item in sorted(db_path.iterdir()):
        if item.is_dir() and any(item.glob("*.cif")):
            tar.add(str(item), arcname=item.name)

tar_size = os.path.getsize(tmp_tar) / (1024 * 1024)
print(f"  压缩包: {tar_size:.1f} MB")

print(f"\n连接服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=30)
sftp = ssh.open_sftp()


def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return out.strip(), err.strip()


print("上传压缩包...")
t0 = time.time()
sftp.put(tmp_tar, f"{REMOTE_DIR}/cif_data.tar.gz")
upload_time = time.time() - t0
print(f"  上传完成 ({upload_time:.1f}s)")

print("解压...")
out, err = run(
    f"cd {REMOTE_DIR}/data && tar xzf {REMOTE_DIR}/cif_data.tar.gz && rm {REMOTE_DIR}/cif_data.tar.gz"
)
print(f"  解压完成")

out, _ = run(f"ls -la {REMOTE_DIR}/data/")
print(f"\n数据目录:\n{out}")

out, _ = run(f'find {REMOTE_DIR}/data -name "*.cif" -type f | wc -l')
print(f"\nCIF文件总数: {out}")

out, _ = run(f"find {REMOTE_DIR}/data -maxdepth 1 -type d | sort")
print(f"类别文件夹:\n{out}")

for d in out.split("\n"):
    d = d.strip()
    if not d or d == REMOTE_DIR + "/data":
        continue
    dirname = os.path.basename(d)
    count_out, _ = run(f'find {d} -name "*.cif" -type f | wc -l')
    print(f"  {dirname}: {count_out} CIFs")

os.remove(tmp_tar)
sftp.close()
ssh.close()
print("\n数据上传完成!")
