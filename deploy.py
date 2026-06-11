import paramiko
import os
import sys

HOST = "118.31.164.41"
USER = "root"
KEY_PATH = r"D:\Projects\CGCPT-Server\id_ed25519"
LOCAL_DIST = r"d:\Projects\CGCPT-Server\web\dist"
REMOTE_ROOT = "/opt/CGCPT/root/CGCPT"
LOCAL_API = r"D:\Projects\CGCPT-Server\api_server.py"
REMOTE_API = "/opt/CGCPT/api_server.py"


def run_cmd(ssh, cmd, desc=""):
    print(f"\n{'='*60}")
    print(f"▶ 执行命令: {desc or cmd}")
    print(f"{'='*60}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(f"[STDERR] {err}")
    print(f"[退出码] {rc}")
    return out, err, rc


def sftp_upload(sftp, local_path, remote_path):
    print(f"  上传: {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)


def upload_dir(sftp, local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir).replace("\\", "/")
        if rel_path == ".":
            current_remote = remote_dir
        else:
            current_remote = remote_dir.rstrip("/") + "/" + rel_path
        try:
            sftp.mkdir(current_remote)
        except Exception:
            pass
        for f in files:
            local_file = os.path.join(root, f)
            remote_file = current_remote + "/" + f
            sftp_upload(sftp, local_file, remote_file)


def main():
    print("=" * 60)
    print("  CGCPT 部署脚本 - 开始")
    print(f"  目标服务器: {HOST}")
    print("=" * 60)

    key = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, pkey=key, timeout=15)
    sftp = ssh.open_sftp()
    print("\n✅ SSH连接成功!")

    # ========== Part 1: Deploy Frontend ==========
    print("\n" + "=" * 60)
    print("  📦 Part 1: 部署前端文件")
    print("=" * 60)

    run_cmd(ssh, f"rm -rf {REMOTE_ROOT}/assets/ {REMOTE_ROOT}/index.html", "清理旧前端文件")

    print(f"\n开始上传前端文件: {LOCAL_DIST} -> {REMOTE_ROOT}")
    upload_dir(sftp, LOCAL_DIST, REMOTE_ROOT)
    print("\n✅ 前端文件上传完成!")

    out, _, _ = run_cmd(ssh, f"ls -la {REMOTE_ROOT}/assets/DataImport*", "验证 DataImport 资源")

    # ========== Part 2: Deploy Backend ==========
    print("\n" + "=" * 60)
    print("  📦 Part 2: 部署后端文件")
    print("=" * 60)

    sftp_upload(sftp, LOCAL_API, REMOTE_API)
    print("\n✅ api_server.py 上传完成!")

    run_cmd(ssh, "systemctl restart cgcpt", "重启 cgcpt 服务")
    import time

    time.sleep(2)

    # ========== Part 3: Verify ==========
    print("\n" + "=" * 60)
    print("  🔍 Part 3: 验证部署结果")
    print("=" * 60)

    run_cmd(
        ssh, "curl -s http://localhost/CGCPT/api/health | python3 -m json.tool", "检查 API 健康状态"
    )
    run_cmd(
        ssh,
        "curl -s -X POST http://localhost/CGCPT/api/import/preview 2>&1 | head -5",
        "测试 import/preview 端点",
    )
    run_cmd(ssh, f"ls {REMOTE_ROOT}/assets/DataImport*", "确认 DataImport 资源存在")
    run_cmd(ssh, "systemctl status cgcpt --no-pager | head -8", "检查服务运行状态")

    sftp.close()
    ssh.close()
    print("\n" + "=" * 60)
    print("  ✅ 全部部署任务完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
